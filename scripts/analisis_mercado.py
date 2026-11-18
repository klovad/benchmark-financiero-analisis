"""Análisis del mercado de captaciones y colocaciones: corre todos los modelos y guarda
resultados en salidas/mercado/ (CSV + resultados.json para el informe HTML).

    uv run python scripts/analisis_mercado.py              # usa los paneles en caché
    uv run python scripts/analisis_mercado.py --refrescar  # vuelve a consultar la base
    uv run python scripts/analisis_mercado.py --entidad PICHINCHA   # plan de acción para otra

Metodología y referencias: docs/analisis_mercado.md.
"""

from __future__ import annotations

import argparse
import json
import warnings

import numpy as np
import pandas as pd

from benchmark_analisis import (
    balance,
    demanda,
    explorador,
    liderazgo,
    mercado,
    segmentacion,
    sustitucion,
)
from benchmark_analisis.db import RAIZ, consulta
from benchmark_analisis.paneles import panel
from benchmark_analisis.tasas import series_semanales

warnings.filterwarnings("ignore")
SALIDA = RAIZ / "salidas" / "mercado"
GRUPOS_TASA = liderazgo.COMPETIDORES + ["OTROS BANCOS", "COOP SEGMENTO 1", "COOP SEGMENTO 2"]


def _registro(df: pd.DataFrame, redondeo: int = 4) -> list[dict]:
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_datetime64_any_dtype(d[c]):
            d[c] = d[c].dt.strftime("%Y-%m-%d")
    return json.loads(d.round(redondeo).to_json(orient="records", force_ascii=False))


def main(entidad: str, refrescar: bool) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    r: dict = {"entidad": entidad}

    print("1/7 paneles")
    saldos = panel("saldos_canton", refrescar=refrescar)
    indic = panel("indicadores_entidad", refrescar=refrescar)
    capt = panel("tasas_captacion_semanal", refrescar=refrescar)
    canton_mes = panel("tasas_canton_mensual", refrescar=refrescar)
    corte_saldos = int(saldos["anio_mes"].max())
    r["cortes"] = {"saldos": corte_saldos, "tasas_semana": str(capt["fecha"].max()),
                   "balance": int(indic["anio_mes"].max())}
    conc = consulta("SELECT * FROM marts.vw_conciliacion_resumen WHERE fecha_id = "
                    "(SELECT MAX(fecha_id) FROM marts.fact_saldo_cartera)")
    r["conciliacion"] = _registro(conc)

    print("2/7 mercado agregado")
    tipos = ["BANCO PRIVADO", "COOPERATIVA", "MUTUALISTA", "BANCO PUBLICO"]
    agg = (saldos[saldos["tipo_entidad"].isin(tipos)]
           .groupby(["anio_mes", "tipo_entidad"])[["cartera", "depositos", "dep_plazo", "dep_vista"]]
           .sum().reset_index())
    agg.to_csv(SALIDA / "mercado_por_tipo.csv", index=False)
    r["mercado_por_tipo"] = _registro(agg, 0)
    bancos = saldos[saldos["tipo_entidad"] == "BANCO PRIVADO"]
    cuotas = []
    for m in ["cartera", "depositos", "dep_plazo"]:
        u = bancos.groupby(["anio_mes", "entidad_codigo"])[m].sum().unstack()
        sh = u.div(u.sum(axis=1), axis=0)
        sh = sh.loc[:, sh.iloc[-1].sort_values(ascending=False).index[:8]]
        cuotas.append(sh.stack().rename("cuota").reset_index().assign(medida=m))
    cuotas = pd.concat(cuotas)
    cuotas.to_csv(SALIDA / "cuotas_bancos.csv", index=False)
    r["cuotas_bancos"] = _registro(cuotas)

    print("3/7 tasas y liderazgo")
    w = series_semanales(capt)
    w.to_csv(SALIDA / "tasa_plazo_ajustada_semanal.csv")
    mensual = w[GRUPOS_TASA].resample("ME").mean()
    r["tasas_mensuales"] = _registro(mensual.reset_index(names="mes"), 3)
    ciclo = liderazgo.fechas_ciclo(w, GRUPOS_TASA)
    ciclo.to_csv(SALIDA / "ciclo_tasas.csv", index=False)
    r["ciclo"] = _registro(ciclo, 2)
    grupos_resp = liderazgo.COMPETIDORES + ["OTROS BANCOS", "COOP SEGMENTO 1"]
    R, base, N = liderazgo.matriz_respuesta(w.loc["2017":], grupos_resp)
    R.to_csv(SALIDA / "matriz_respuesta.csv")
    r["matriz_respuesta"] = {"grupos": grupos_resp, "p": _nan_a_none(R.values),
                             "n": _nan_a_none(N.values), "base": base["probabilidad_base"].round(3).tolist()}
    r["indice_liderazgo"] = liderazgo.indice_liderazgo(R).round(3).to_dict()
    ecm = liderazgo.correccion_error(w, GRUPOS_TASA, frecuencia="ME")
    ecm.to_csv(SALIDA / "correccion_error.csv", index=False)
    r["correccion_error"] = _registro(ecm, 3)

    print("4/7 anticipación de movimientos")
    capt = capt.assign(fecha=pd.to_datetime(capt["fecha_id"].astype(str), format="%Y%m%d"))
    flujos = capt.pivot_table(index="fecha", columns="entidad_codigo", values="monto", aggfunc="sum")
    bal = balance.indicadores_rezagados(indic, rezago_meses=1)
    D = liderazgo.dataset_movimientos(w, flujos, balance=bal)
    modelos, evals, con_balance = {}, {}, {}
    for obj, nombre in [("y_sube", "sube"), ("y_baja", "baja")]:
        ev = liderazgo.evaluar_anticipacion(D, obj, variables=liderazgo._variables(D, sin_balance=True))
        evals[nombre] = _registro(ev, 3)
        modelos[nombre] = liderazgo.modelo_anticipacion(D, obj, variables=liderazgo._variables(D, sin_balance=True))
        comp = liderazgo.comparar_con_balance(D, obj)
        con_balance[nombre] = {"tabla": _registro(comp["tabla"], 3),
                               "auc_media_sin": comp["auc_media_sin"], "auc_media_con": comp["auc_media_con"],
                               "diferencia": comp["diferencia"], "ic90": comp["ic90"],
                               "coeficientes": liderazgo.coeficientes_balance(D, obj).round(3).to_dict()}
    pred = liderazgo.predecir_ultima_semana(D, modelos)
    pred.to_csv(SALIDA / "prediccion_movimientos.csv", index=False)
    r["anticipacion"] = {"evaluacion": evals, "prediccion": _registro(pred, 3),
                         "coeficientes": {k: v[3].round(3).to_dict() for k, v in modelos.items()},
                         "con_balance": con_balance}

    print("5/7 sustitución bancos-cooperativas y demanda por cantón")
    M = sustitucion.serie_mensual(w, capt, saldos)
    M.to_csv(SALIDA / "bancos_vs_coops_mensual.csv")
    r["sustitucion"] = {
        "flujos": _sin_resumen(sustitucion.modelo_flujos(M)),
        "saldos": _sin_resumen(sustitucion.modelo_saldos(M)),
        "serie": _registro(M.reset_index(names="mes")[
            ["mes", "tasa_bancos", "tasa_coop_s1", "spread", "cuota_coop_flujo", "cuota_coop_saldo"]], 4),
    }
    logits = {}
    for prod in ["DEP_PLAZO", "CONSUMO", "MICROCRÉDITO", "PRODUCTIVO"]:
        d = demanda.preparar(canton_mes, prod)
        for anidado in (True, False):
            res = demanda.estimar(d, prod, anidado=anidado)
            logits[f"{prod}|{res.especificacion}"] = _resultado_logit(res)
    dep = demanda.preparar(canton_mes, "DEP_PLAZO")
    hetero = {}
    for nombre, mascara in {
        "cooperativas": dep["nido"] == "COOPERATIVAS",
        "bancos_grandes": dep["entidad_codigo"].isin(liderazgo.GRANDES[:4]),
        **{b.lower(): dep["entidad_codigo"] == b for b in liderazgo.GRANDES},
    }.items():
        res = demanda.estimar(dep, "DEP_PLAZO", anidado=False, interacciones={nombre: mascara})
        hetero[nombre] = {"alpha_resto": res.coeficientes["tasa"],
                          "diferencia": res.coeficientes[f"tasa_x_{nombre}"],
                          "se_diferencia": res.errores[f"tasa_x_{nombre}"]}
    disciplina = {}
    for rezago in (1, 3):
        bal_r = balance.indicadores_rezagados(indic, rezago_meses=rezago)
        for por_nido in (False, True):
            d, cols = demanda.agregar_balance(dep, bal_r, balance.VARIABLES, por_nido=por_nido)
            sin = demanda.estimar(d, "DEP_PLAZO", anidado=False)
            con = demanda.estimar(d, "DEP_PLAZO", anidado=False, exogenas=cols)
            disciplina[f"rezago{rezago}|{'por_nido' if por_nido else 'conjunto'}"] = {
                "n": con.n, "entidades": con.entidades,
                "alpha_sin_balance": sin.alpha, "alpha_con_balance": con.alpha,
                "se_alpha_con_balance": con.errores["tasa"],
                "coeficientes": {c: con.coeficientes[c] for c in cols},
                "errores": {c: con.errores[c] for c in cols}}
    r["demanda"] = {"modelos": logits, "heterogeneidad": hetero, "disciplina": disciplina}
    techo = consulta((RAIZ / "sql" / "colocaciones_cerca_techo.sql").read_text(encoding="utf-8"),
                     desde=20250101)
    r["techos"] = _registro(techo, 3)

    print("6/7 cantones y segmentación de entidades")
    ind_c = mercado.indicadores_canton(saldos, canton_mes)
    cl, sil = mercado.clusters_canton(ind_c)
    cl.to_csv(SALIDA / "cantones_cluster.csv", index=False)
    perfil = cl.groupby("cluster").agg(
        cantones=("canton", "size"), depositos=("depositos", "sum"), cartera=("cartera", "sum"),
        crec_depositos=("crec_depositos", "median"), crec_cartera=("crec_cartera", "median"),
        cartera_depositos=("cartera_depositos", "median"), cuota_coop=("cuota_coop_depositos", "median"),
        avance_coop_pp=("avance_coop_depositos_pp", "median"), hhi=("hhi_depositos", "median"),
        morosidad=("morosidad", "median"), peso_micro=("peso_micro", "median"),
        bancos=("bancos", "median"), spread_coop_banco=("spread_coop_banco", "median"),
        ejemplos=("canton", lambda v: ", ".join(v.head(6)))).reset_index()
    r["clusters_canton"] = {"perfil": _registro(perfil, 3), "silueta": _registro(sil, 3)}
    r["cantones"] = _registro(cl[["canton", "provincia", "region", "cluster", "depositos", "cartera",
                                  "crec_depositos", "crec_cartera", "cartera_depositos",
                                  "cuota_coop_depositos", "avance_coop_depositos_pp",
                                  "hhi_depositos", "bancos", "morosidad", "spread_coop_banco"]], 4)
    ent = segmentacion.universo(segmentacion.tabla_entidades(indic, saldos, corte_saldos))
    ce, sil_e, Z = segmentacion.agrupar(ent)
    ce.to_csv(SALIDA / "entidades_cluster.csv")
    perfil_e = ce.groupby("cluster")[segmentacion.VARIABLES_MODELO + segmentacion.VARIABLES_DESEMPENO].median()
    perfil_e["entidades"] = ce.groupby("cluster").size()
    perfil_e["activo_total"] = ce.groupby("cluster")["activo"].sum()
    perfil_e["miembros"] = ce.groupby("cluster").apply(
        lambda g: ", ".join(_nombre_corto(n) for n in g.sort_values("activo", ascending=False)["entidad"].head(8)))
    r["clusters_entidad"] = {"perfil": _registro(perfil_e.reset_index(), 3), "silueta": _registro(sil_e, 3),
                             "entidades": _registro(ce.reset_index()[["entidad_codigo", "entidad", "tipo_entidad", "cluster", "activo"] + segmentacion.VARIABLES_MODELO + segmentacion.VARIABLES_DESEMPENO], 4)}

    print(f"7/7 plan de acción {entidad}")
    pares = segmentacion.pares_cercanos(Z, entidad) if entidad in Z.index else pd.Series(dtype=float)
    r["accion"] = plan_accion(entidad, saldos, ce, pares, cl, dep, logits, hetero, pred, R, ecm,
                              r["demanda"]["disciplina"])
    print("extra: datos del explorador interactivo")
    r["explorador"] = datos_explorador(saldos, indic, w, D, dep, cl, ce, logits, hetero, refrescar)
    (SALIDA / "resultados.json").write_text(json.dumps(r, ensure_ascii=False, default=_json), encoding="utf-8")
    print(f"listo: {SALIDA / 'resultados.json'}")


def datos_explorador(saldos, indic, w, D, dep, cl, ce, logits, hetero, refrescar=False) -> dict:
    """Series y tablas granulares para filtrar en el informe (ver `explorador.py`)."""
    coloc = panel("tasas_colocacion_semanal", refrescar=refrescar)
    techos = consulta((RAIZ / "sql" / "techos_segmento_mensual.sql").read_text(encoding="utf-8"),
                      desde=20150101)
    entidades_mes, catalogo = explorador.entidades_mes(saldos)
    for codigo, fila in ce[["entidad", "tipo_entidad"]].iterrows():
        catalogo.setdefault(codigo, {"nombre": explorador.nombre_corto(fila["entidad"]),
                                     "tipo": fila["tipo_entidad"]})
    # Entidades del simulador: bancos competidores + 4 cooperativas con más captación a plazo.
    ult = sorted(dep["anio_mes"].unique())[-6:]
    coops = (dep[(dep["anio_mes"].isin(ult)) & (dep["nido"] == "COOPERATIVAS")]
             .groupby("entidad_codigo")["monto"].sum().nlargest(4).index.tolist())
    sim_ent = liderazgo.COMPETIDORES + coops
    base = logits["DEP_PLAZO|logit simple"]["coeficientes"]["tasa"]
    alphas = {"_base": base}
    for e in sim_ent:
        clave = e.lower() if e.lower() in hetero else ("cooperativas" if e in coops else None)
        alphas[e] = base + (hetero[clave]["diferencia"] if clave else 0.0)
    for e in coops:
        if e not in catalogo:
            n = dep.loc[dep["entidad_codigo"] == e, "entidad_codigo"].iloc[0]
            catalogo[e] = {"nombre": n, "tipo": "COOPERATIVA"}
    return {
        "catalogo": catalogo,
        "saldos_provincia": explorador.saldos_provincia(saldos),
        "entidades_mes": entidades_mes,
        "tasas_pasivas": explorador.tasas_pasivas_mensuales(w),
        "tasas_activas": explorador.tasas_activas(coloc),
        "techos": explorador.columnar(techos, 3),
        "predicciones_oos": explorador.predicciones_fuera_de_muestra(
            D, liderazgo._variables(D, sin_balance=True)),
        "simulador": explorador.insumos_simulador(dep, saldos, sim_ent, alphas, cl),
        "oportunidades": explorador.oportunidades_varias(saldos, cl, liderazgo.COMPETIDORES),
        "trayectorias": explorador.trayectorias(indic, list(ce.index)),
    }


def plan_accion(entidad, saldos, ce, pares, cl, dep, logits, hetero, pred, R, ecm, disciplina) -> dict:
    """Todo lo que la entidad necesita para actuar: posición frente a pares, cantones con
    brecha, simulación de tasa y vigilancia de competidores."""
    out: dict = {"pares": {k: round(v, 3) for k, v in pares.items()}}
    disc = disciplina.get("rezago1|por_nido")
    if disc:
        # Equivalencia mora ↔ tasa: cuántos pp de tasa compensan 1 pp más de mora.
        b_mora = disc["coeficientes"].get("morosidad_bancos")
        out["mora_equivalente_pp"] = None if b_mora is None else -b_mora / disc["alpha_con_balance"]
    if entidad in ce.index:
        cols = segmentacion.VARIABLES_DESEMPENO
        grupo = ce.loc[list(pares.index) + [entidad], cols]
        out["vs_pares"] = _registro(grupo.reset_index().rename(columns={"index": "entidad_codigo"}), 4)
    opp = {}
    for m in ["depositos", "cartera"]:
        o = mercado.oportunidades_entidad(saldos, cl, entidad, m)
        o.to_csv(SALIDA / f"oportunidades_{entidad.lower()}_{m}.csv", index=False)
        opp[m] = {"total_usd": float(o["potencial_usd"].sum()),
                  "top": _registro(o.head(20), 4)}
    out["oportunidades"] = opp
    alpha = logits["DEP_PLAZO|logit simple"]["coeficientes"]["tasa"]
    extra = hetero.get(entidad.lower(), {}).get("diferencia", 0.0)
    a_ent = alpha + extra
    sims = {}
    for bp in (25, 50):
        s = demanda.simular_todos(dep, entidad, bp / 100, a_ent, sigma=0.0)
        gana = s[s["entidad_codigo"] == entidad]["cambio_monto"].sum()
        quien = (s[s["entidad_codigo"] != entidad].groupby(["entidad_codigo", "tipo_entidad"])
                 ["cambio_monto"].sum().sort_values().head(10).reset_index())
        por_tipo = s[s["entidad_codigo"] != entidad].groupby("tipo_entidad")["cambio_monto"].sum()
        por_canton = (s[s["entidad_codigo"] == entidad].groupby("canton")["cambio_monto"].sum()
                      .sort_values(ascending=False).head(10))
        sims[str(bp)] = {"gana_mensual_usd": float(gana), "de_quien": _registro(quien, 0),
                         "por_tipo": por_tipo.round(0).to_dict(),
                         "por_canton": por_canton.round(0).to_dict()}
    base_mes = dep[dep["anio_mes"].isin(sorted(dep["anio_mes"].unique())[-6:])]
    propio = base_mes[base_mes["entidad_codigo"] == entidad]
    plazo_medio = float((propio["plazo_medio_dias"] * propio["monto"]).sum() / propio["monto"].sum())
    corte = saldos["anio_mes"].max()
    saldo_plazo = float(saldos[(saldos["anio_mes"] == corte) & (saldos["entidad_codigo"] == entidad)]["dep_plazo"].sum())
    tasa_actual = float((propio["tasa"] * propio["monto"]).sum() / propio["monto"].sum())
    for bp, s in sims.items():
        # Saldo adicional en estado estacionario ≈ flujo mensual adicional × plazo medio en
        # meses (cada depósito nuevo permanece ~plazo_medio). Costo anual: el saldo que ya se
        # tiene se re-precia (subida × saldo actual, al renovarse) y el nuevo paga la tasa nueva.
        sube = int(bp) / 10_000
        saldo_extra = s["gana_mensual_usd"] * plazo_medio / 30
        costo_extra = sube * saldo_plazo + (tasa_actual / 100 + sube) * saldo_extra
        s["saldo_adicional_usd"] = saldo_extra
        s["costo_anual_adicional_usd"] = costo_extra
        s["costo_marginal_pct"] = 100 * costo_extra / saldo_extra if saldo_extra else None
    # Escenario focalizado: +0,50 pp solo en los 10 cantones con mayor potencial de depósitos
    # donde la entidad ya capta y su brecha es >= 2 pp (excluye plazas donde ya está en su
    # objetivo), re-preciando solo el saldo de esos cantones.
    top = [c for c in opp["depositos"]["top"] if c["presente"] and c["brecha_pp"] >= 2][:10]
    cantones_foco = [c["canton"] for c in top]
    s = demanda.simular_todos(dep[dep["canton"].isin(cantones_foco)], entidad, 0.50, a_ent)
    gana = float(s[s["entidad_codigo"] == entidad]["cambio_monto"].sum())
    saldo_foco = float(saldos[(saldos["anio_mes"] == corte) & (saldos["entidad_codigo"] == entidad)
                              & saldos["canton"].isin(cantones_foco)]["dep_plazo"].sum())
    extra = gana * plazo_medio / 30
    costo = 0.005 * saldo_foco + (tasa_actual / 100 + 0.005) * extra
    sims["50_focalizado"] = {"cantones": cantones_foco, "gana_mensual_usd": gana,
                             "saldo_plazo_cantones": saldo_foco, "saldo_adicional_usd": extra,
                             "costo_anual_adicional_usd": costo,
                             "costo_marginal_pct": 100 * costo / extra if extra else None,
                             "por_tipo": s[s["entidad_codigo"] != entidad].groupby("tipo_entidad")["cambio_monto"].sum().round(0).to_dict()}
    out["simulacion"] = {"alpha": a_ent, "flujo_mensual_base": float(propio["monto"].sum() / 6),
                         "plazo_medio_dias": plazo_medio, "saldo_plazo_actual": saldo_plazo,
                         "tasa_actual": tasa_actual, "escenarios": sims}
    if entidad in R.index:
        out["lo_siguen"] = R.loc[entidad].dropna().round(3).to_dict()
        out["sigue_a"] = R[entidad].dropna().round(3).to_dict()
    out["competidores_proximas_semanas"] = _registro(pred[pred["banco"] != entidad], 3)
    return out


def _resultado_logit(res) -> dict:
    return {"especificacion": res.especificacion, "coeficientes": res.coeficientes,
            "errores": res.errores, "primera_etapa_f": res.primera_etapa_f, "n": res.n,
            "entidades": res.entidades, "mercados": res.mercados}


def _sin_resumen(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "resumen"}


def _nan_a_none(a: np.ndarray) -> list:
    return [[None if pd.isna(v) else round(float(v), 3) for v in fila] for fila in a]


def _nombre_corto(n: str) -> str:
    n = n.replace("COOPERATIVA DE AHORRO Y CREDITO", "COAC").replace("BP ", "")
    n = n.replace("ASOCIACION MUTUALISTA DE AHORRO Y CREDITO PARA LA VIVIENDA", "MUT.")
    return n.split(" LIMITADA")[0].split(" LTDA")[0].strip().title()


def _json(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.strftime("%Y-%m-%d")
    return str(o)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entidad", default="GUAYAQUIL", help="entidad_codigo para el plan de acción")
    p.add_argument("--refrescar", action="store_true", help="volver a consultar la base")
    a = p.parse_args()
    main(a.entidad, a.refrescar)

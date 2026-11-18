"""Datos granulares para el informe interactivo (filtros por provincia, entidad, producto,
simulador en el navegador).

Todo sale de los mismos paneles y modelos del análisis; acá solo se agrega y se da forma
compacta (formato columnar: {columna: [valores]}) para que el HTML siga siendo un único
archivo liviano.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from benchmark_analisis import liderazgo, mercado
from benchmark_analisis.tasas import grupo_comparacion

TIPOS = ["BANCO PRIVADO", "COOPERATIVA", "MUTUALISTA", "BANCO PUBLICO"]
SEGMENTOS_CREDITO = ["CONSUMO", "PRODUCTIVO", "MICROCRÉDITO", "INMOBILIARIO"]


def columnar(df: pd.DataFrame, redondeo: int = 4) -> dict:
    out = {}
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_float_dtype(s):
            out[c] = [None if pd.isna(v) else v for v in s.round(redondeo).tolist()]
        else:
            out[c] = [None if (isinstance(v, float) and np.isnan(v)) else v for v in s.tolist()]
    return out


def nombre_corto(n: str) -> str:
    n = n.replace("COOPERATIVA DE AHORRO Y CREDITO", "").replace("BP ", "").replace("BANCO ", "")
    n = n.replace("ASOCIACION MUTUALISTA DE AHORRO Y CREDITO PARA LA VIVIENDA", "Mut.")
    n = n.split(" LIMITADA")[0].split(" LTDA")[0].split(" S.A.")[0].strip(" ,.")
    return n.title()


def saldos_provincia(saldos: pd.DataFrame) -> dict:
    """Mes × provincia × tipo de entidad: cartera, mora, depósitos (total, plazo, vista)."""
    s = saldos[saldos["tipo_entidad"].isin(TIPOS) & (saldos["canton"] != "NACIONAL")]
    g = (s.groupby(["anio_mes", "provincia", "region", "tipo_entidad"], as_index=False)
         [["cartera", "cartera_improductiva", "depositos", "dep_plazo", "dep_vista"]].sum())
    return columnar(g, 0)


def entidades_mes(saldos: pd.DataFrame, n_coops: int = 15) -> tuple[dict, dict]:
    """Mes × entidad (bancos privados, mutualistas, públicos y las `n_coops` cooperativas
    más grandes por depósitos) y catálogo {codigo: {nombre, tipo}}."""
    s = saldos[saldos["tipo_entidad"].isin(TIPOS)]
    corte = s["anio_mes"].max()
    coops = (s[(s["tipo_entidad"] == "COOPERATIVA") & (s["anio_mes"] == corte)]
             .groupby("entidad_codigo")["depositos"].sum().nlargest(n_coops).index)
    sel = s[(s["tipo_entidad"] != "COOPERATIVA") | s["entidad_codigo"].isin(coops)]
    g = (sel.groupby(["anio_mes", "entidad_codigo"], as_index=False)
         [["cartera", "cartera_improductiva", "depositos", "dep_plazo", "dep_vista"]].sum())
    cat = (sel[["entidad_codigo", "entidad", "tipo_entidad"]].drop_duplicates("entidad_codigo")
           .set_index("entidad_codigo"))
    catalogo = {k: {"nombre": nombre_corto(v["entidad"]), "tipo": v["tipo_entidad"]}
                for k, v in cat.iterrows()}
    return columnar(g, 0), catalogo


def tasas_activas(coloc: pd.DataFrame, desde: int = 2015) -> dict:
    """Mes × grupo de comparación × segmento: tasa activa ponderada por monto y monto.
    Promedio simple ponderado dentro del segmento (sin ajuste por subsegmento)."""
    t = coloc[coloc["segmento"].isin(SEGMENTOS_CREDITO) & (coloc["fecha_id"] // 10000 >= desde)].copy()
    t["grupo"] = grupo_comparacion(t["tipo_entidad"], t["entidad_codigo"], t["segmento_semana"])
    t["anio_mes"] = t["fecha_id"] // 100
    t["_tw"] = t["tasa"] * t["monto"]
    g = t.groupby(["anio_mes", "grupo", "segmento"], as_index=False)[["_tw", "monto"]].sum()
    g["tasa"] = g.pop("_tw") / g["monto"]
    return columnar(g, 3)


def tasas_pasivas_mensuales(w: pd.DataFrame, desde: str = "2015") -> dict:
    m = w.loc[desde:].resample("ME").mean()
    m.index = m.index.strftime("%Y-%m")
    return columnar(m.reset_index(names="mes"), 3)


def predicciones_fuera_de_muestra(D: pd.DataFrame, variables: list[str]) -> dict:
    """Probabilidades fuera de muestra (ventana expansiva) de subir y bajar, por banco y
    semana, con lo que efectivamente pasó (y)."""
    partes = []
    for obj, nombre in [("y_sube", "sube"), ("y_baja", "baja")]:
        _, t = liderazgo.evaluar_anticipacion(D, obj, variables=variables, con_predicciones=True)
        partes.append(t.rename(columns={"p": f"p_{nombre}", "y": f"y_{nombre}"}).reset_index(names="fecha")
                      .set_index(["fecha", "banco"]))
    out = partes[0].join(partes[1], how="outer").reset_index()
    out["fecha"] = out["fecha"].dt.strftime("%Y-%m-%d")
    return columnar(out, 3)


def insumos_simulador(dep: pd.DataFrame, saldos: pd.DataFrame, entidades: list[str],
                      alphas: dict[str, float], cantones_cluster: pd.DataFrame,
                      meses: int = 6) -> dict:
    """Por entidad y cantón (promedio mensual de los últimos `meses`): flujo total del
    cantón, flujo de la entidad y de cada competidor agregado. Con eso el navegador aplica
    el logit simple en forma cerrada:
        g = exp(alpha × Δtasa);  s' = s g / (1 − s + s g);  rival_k' = rival_k / (1 − s + s g)
    También: saldo a plazo de la entidad por cantón (para el re-precio), brecha de
    penetración (para el escenario focalizado), plazo medio y tasa actual."""
    ult = sorted(dep["anio_mes"].unique())[-meses:]
    d = dep[dep["anio_mes"].isin(ult)]
    rivales = liderazgo.COMPETIDORES
    d = d.assign(rival=np.where(d["entidad_codigo"].isin(rivales), d["entidad_codigo"],
                       np.where(d["tipo_entidad"] == "BANCO PRIVADO", "OTROS BANCOS",
                       np.where(d["tipo_entidad"] == "COOPERATIVA", "COOPERATIVAS", "OTROS"))))
    corte = saldos["anio_mes"].max()
    s_act = saldos[saldos["anio_mes"] == corte]
    out = {"rivales": rivales + ["OTROS BANCOS", "COOPERATIVAS", "OTROS"], "entidades": {}}
    for e in entidades:
        propio = d[d["entidad_codigo"] == e]
        if propio.empty:
            continue
        cantones = propio["canton"].unique()
        sub = d[d["canton"].isin(cantones)]
        tot = sub.groupby("canton")["monto"].sum() / meses
        mio = propio.groupby("canton")["monto"].sum() / meses
        riv = (sub[sub["entidad_codigo"] != e].groupby(["canton", "rival"])["monto"].sum() / meses
               ).unstack(fill_value=0).reindex(columns=out["rivales"], fill_value=0)
        prov = sub.drop_duplicates("canton").set_index("canton")["provincia"]
        saldo_c = s_act[s_act["entidad_codigo"] == e].groupby("canton")["dep_plazo"].sum()
        opp = mercado.oportunidades_entidad(saldos, cantones_cluster, e, "depositos").set_index("canton")
        reg = cantones_cluster.set_index("canton")["region"]
        filas = pd.DataFrame({
            "canton": tot.index, "provincia": prov.reindex(tot.index).values,
            "region": reg.reindex(tot.index).values, "total": tot.values,
            "propio": mio.reindex(tot.index).fillna(0).values,
            "saldo_plazo": saldo_c.reindex(tot.index).fillna(0).values,
            "brecha_pp": opp["brecha_pp"].reindex(tot.index).values,
        })
        out["entidades"][e] = {
            "alpha": alphas.get(e, alphas["_base"]),
            "plazo_medio_dias": float((propio["plazo_medio_dias"] * propio["monto"]).sum() / propio["monto"].sum()),
            "tasa_actual": float((propio["tasa"] * propio["monto"]).sum() / propio["monto"].sum()),
            "saldo_plazo_total": float(s_act[s_act["entidad_codigo"] == e]["dep_plazo"].sum()),
            "cantones": columnar(filas, 0),
            "rivales": [[round(v) for v in fila] for fila in riv.reindex(tot.index).to_numpy()],
        }
    return out


def oportunidades_varias(saldos: pd.DataFrame, cantones_cluster: pd.DataFrame,
                         entidades: list[str]) -> dict:
    out = {}
    for e in entidades:
        out[e] = {}
        for m in ["depositos", "cartera"]:
            o = mercado.oportunidades_entidad(saldos, cantones_cluster, e, m)
            o = o[["canton", "provincia", "region", "cluster", m, "cuota", "cuota_objetivo",
                   "brecha_pp", "potencial_usd", "presente"]].rename(columns={m: "mercado"})
            out[e][m] = columnar(o, 4)
    return out


def trayectorias(indicadores: pd.DataFrame, codigos: list[str]) -> dict:
    """Mes × entidad: mora, liquidez, solvencia, ROA, ROE, costo de fondeo (ratios)."""
    i = indicadores[indicadores["entidad_codigo"].isin(codigos)]
    i = i[["anio_mes", "entidad_codigo", "morosidad", "liquidez", "patrimonio_activo", "roa",
           "roe", "costo_fondeo"]].rename(columns={"patrimonio_activo": "solvencia"})
    return columnar(i.sort_values(["entidad_codigo", "anio_mes"]), 4)

"""Demanda de depósitos y crédito por cantón: logit anidado (Berry, 1994) con instrumentos.

Mercado = cantón × mes; producto = entidad; cantidad = monto nuevo del BCE (captaciones a
plazo o colocaciones de un segmento); precio = tasa efectiva ponderada. Nidos = tipo de
entidad (bancos privados / cooperativas / otros), que es la pregunta de sustitución entre
bancos y cooperativas (Adams, Brevoort y Kiser, 2007, J. Industrial Economics).

    ln s_jm = alpha * tasa_jm + sigma * ln s_{j|g,m} + gamma * ln(plazo_jm) + xi_jc + delta_m + e_jm

- `delta_m` (efecto fijo de mercado) absorbe el tamaño del mercado y la utilidad de la opción
  externa, así que las cuotas son "internas": se modela quién se lleva el flujo del cantón,
  no si el flujo total crece (supuesto razonable a horizonte mensual).
- `xi_jc` (efecto fijo entidad × cantón) absorbe marca, agencias y arraigo local: alpha se
  identifica con los cambios de tasa de la entidad en el tiempo, no con diferencias
  permanentes entre entidades.
- Endogeneidad: una entidad sube su tasa justo donde necesita fondos (shock de demanda
  correlacionado con el precio). Instrumentos: (i) tasa de la misma entidad en **otras
  provincias** el mismo mes (Hausman, 1996; Nevo, 2001), válida si los shocks locales no
  son nacionales; (ii) ln del número de rivales del nido y del mercado (Berry, 1994; Berry,
  Levinsohn y Pakes, 1995) para la cuota dentro del nido.
- `alpha` > 0 en depósitos (más tasa atrae), < 0 en crédito (más tasa espanta).
- `sigma` en [0, 1): cuánto más se sustituye dentro del nido que entre nidos. Cerca de 1:
  bancos y cooperativas son mercados casi separados; cerca de 0: el cliente compara todos.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyhdfe
from linearmodels.iv import IV2SLS

NIDOS = {"BANCO PRIVADO": "BANCOS", "COOPERATIVA": "COOPERATIVAS"}


def preparar(t: pd.DataFrame, producto: str, monto_minimo: float = 5_000) -> pd.DataFrame:
    """Cuotas, nidos e instrumentos para un producto del panel `tasas_canton_mensual`."""
    d = t[(t["producto"] == producto) & (t["canton"] != "NACIONAL")
          & (t["monto"] >= monto_minimo) & t["tasa"].notna() & (t["tasa"] > 0)].copy()
    d["nido"] = d["tipo_entidad"].map(NIDOS).fillna("OTROS")
    d["mercado"] = d["anio_mes"].astype(str) + "|" + d["canton_id"].astype(str)
    tot = d.groupby("mercado")["monto"].transform("sum")
    tot_g = d.groupby(["mercado", "nido"])["monto"].transform("sum")
    d["s"] = d["monto"] / tot
    d["s_g"] = d["monto"] / tot_g
    n = d.groupby("mercado")["entidad_codigo"].transform("size")
    d = d[n >= 2].copy()
    d["ln_s"] = np.log(d["s"])
    d["ln_s_g"] = np.log(d["s_g"])
    d["ln_plazo"] = np.log1p(d["plazo_medio_dias"].fillna(0))
    # Instrumento de Hausman: tasa media ponderada de la entidad en otras provincias.
    d["_tw"] = d["tasa"] * d["monto"]
    ent_mes = d.groupby(["entidad_codigo", "anio_mes"])[["_tw", "monto"]].transform("sum")
    ent_prov = d.groupby(["entidad_codigo", "anio_mes", "provincia"])[["_tw", "monto"]].transform("sum")
    fuera = ent_mes - ent_prov
    d["z_hausman"] = fuera["_tw"] / fuera["monto"].replace(0, np.nan)
    d["z_rivales_nido"] = np.log(d.groupby(["mercado", "nido"])["entidad_codigo"].transform("size"))
    d["z_rivales_mercado"] = np.log(d.groupby("mercado")["entidad_codigo"].transform("size"))
    d = d.drop(columns="_tw")
    return d.dropna(subset=["z_hausman"])


def instrumentos_rivales(d: pd.DataFrame) -> pd.DataFrame:
    """Instrumentos tipo BLP: media del instrumento de Hausman de los rivales del mismo
    nido y de los otros nidos en el mercado (sus costos/condiciones nacionales desplazan
    la cuota dentro del nido sin depender del shock local de la entidad)."""
    d = d.copy()
    g = d.groupby(["mercado", "nido"])["z_hausman"].agg(["sum", "size"])
    d = d.join(g.rename(columns={"sum": "_zs", "size": "_zn"}), on=["mercado", "nido"])
    m = d.groupby("mercado")["z_hausman"].agg(["sum", "size"])
    d = d.join(m.rename(columns={"sum": "_ms", "size": "_mn"}), on="mercado")
    d["z_rivales_nido_tasa"] = ((d["_zs"] - d["z_hausman"]) / (d["_zn"] - 1)).where(d["_zn"] > 1)
    d["z_rivales_otro_tasa"] = ((d["_ms"] - d["_zs"]) / (d["_mn"] - d["_zn"])).where(d["_mn"] > d["_zn"])
    d["z_rivales_nido_tasa"] = d["z_rivales_nido_tasa"].fillna(d["z_hausman"])
    d["z_rivales_otro_tasa"] = d["z_rivales_otro_tasa"].fillna(d["z_hausman"])
    return d.drop(columns=["_zs", "_zn", "_ms", "_mn"])


@dataclass
class ResultadoLogit:
    producto: str
    especificacion: str
    coeficientes: dict
    errores: dict
    primera_etapa_f: dict
    n: int
    entidades: int
    mercados: int
    resumen: str

    @property
    def alpha(self) -> float:
        return self.coeficientes["tasa"]

    @property
    def sigma(self) -> float:
        return self.coeficientes.get("ln_s_g", 0.0)


def agregar_balance(d: pd.DataFrame, balance: pd.DataFrame, variables: list[str],
                    por_nido: bool = True) -> tuple[pd.DataFrame, list[str]]:
    """Une mora, liquidez y solvencia (ya rezagadas, `balance.indicadores_rezagados`) al
    panel de demanda por `anio_mes` = `anio_mes_uso`, y descarta entidades sin balance
    (banca pública, cooperativas S4-S5). Con `por_nido` crea una columna por variable y
    nido (bancos / cooperativas / otros): ¿reacciona distinto el depositante de cada uno?
    Devuelve (panel, columnas exógenas a pasar a `estimar`)."""
    b = balance[["entidad_codigo", "anio_mes_uso"] + variables].rename(columns={"anio_mes_uso": "anio_mes"})
    out = d.merge(b, on=["entidad_codigo", "anio_mes"], how="inner")
    if not por_nido:
        return out, variables
    cols = []
    for v in variables:
        for nido in out["nido"].unique():
            c = f"{v}_{nido.lower()}"
            out[c] = out[v] * (out["nido"] == nido)
            cols.append(c)
    return out, cols


def estimar(d: pd.DataFrame, producto: str, anidado: bool = True,
            interacciones: dict[str, pd.Series] | None = None,
            exogenas: list[str] | None = None) -> ResultadoLogit:
    """2SLS con efectos fijos entidad×cantón (marca y red local) y mercado (cantón×mes)
    absorbidos con pyhdfe; errores agrupados por entidad.

    `anidado=False` estima el logit simple (sigma = 0). `interacciones` = {nombre: máscara
    booleana}: agrega tasa×máscara (instrumentada con z_hausman×máscara) para medir si la
    sensibilidad de un grupo o de una entidad difiere del resto. `exogenas`: controles
    adicionales tratados como exógenos (p. ej. mora, liquidez y solvencia rezagadas)."""
    d = instrumentos_rivales(d)
    d["entidad_canton"] = d["entidad_codigo"] + "|" + d["canton_id"].astype(str)
    endog, inst = ["tasa"], ["z_hausman"]
    if anidado:
        endog.append("ln_s_g")
        inst += ["z_rivales_nido", "z_rivales_nido_tasa", "z_rivales_otro_tasa"]
    for nombre, mascara in (interacciones or {}).items():
        d[f"tasa_x_{nombre}"] = d["tasa"] * mascara.reindex(d.index).astype(float)
        d[f"z_x_{nombre}"] = d["z_hausman"] * mascara.reindex(d.index).astype(float)
        endog.append(f"tasa_x_{nombre}")
        inst.append(f"z_x_{nombre}")
    ids = np.column_stack([pd.factorize(d["entidad_canton"])[0], pd.factorize(d["mercado"])[0]])
    alg = pyhdfe.create(ids, drop_singletons=True)
    exog = ["ln_plazo"] + list(exogenas or [])
    cols = ["ln_s"] + exog + endog + inst
    keep = ~alg.singleton_indices if alg.singleton_indices is not None else np.ones(len(d), bool)
    r = pd.DataFrame(alg.residualize(d[cols].to_numpy(float)), columns=cols)
    clusters = pd.factorize(d["entidad_codigo"].to_numpy()[keep])[0]
    fit = IV2SLS(r["ln_s"], r[exog], r[endog], r[inst]).fit(
        cov_type="clustered", clusters=clusters)
    fe = fit.first_stage.diagnostics["f.stat"].to_dict()
    return ResultadoLogit(
        producto=producto,
        especificacion="logit anidado" if anidado else "logit simple",
        coeficientes={k: float(v) for k, v in fit.params.items()},
        errores={k: float(v) for k, v in fit.std_errors.items()},
        primera_etapa_f={k: float(v) for k, v in fe.items()},
        n=int(keep.sum()), entidades=d["entidad_codigo"].nunique(),
        mercados=d["mercado"].nunique(), resumen=str(fit.summary),
    )


def cuotas_logit_anidado(delta: np.ndarray, nido: np.ndarray, sigma: float) -> np.ndarray:
    """Cuotas internas del logit anidado dada la utilidad media `delta` (sin opción externa)."""
    out = np.empty_like(delta, dtype=float)
    ivs = {}
    for g in np.unique(nido):
        m = nido == g
        e = np.exp((delta[m] - delta[m].max()) / (1 - sigma))
        ivs[g] = (e, m, delta[m].max())
    # D_g^(1-sigma) con el máximo restado para estabilidad numérica
    log_dg = {g: np.log(e.sum()) * (1 - sigma) + mx for g, (e, m, mx) in ivs.items()}
    mx = max(log_dg.values())
    den = sum(np.exp(v - mx) for v in log_dg.values())
    for g, (e, m, _) in ivs.items():
        out[m] = (e / e.sum()) * np.exp(log_dg[g] - mx) / den
    return out


def simular(mercado: pd.DataFrame, entidad: str, delta_tasa_pp: float,
            alpha: float, sigma: float) -> pd.DataFrame:
    """Efecto de que `entidad` mueva su tasa `delta_tasa_pp` en un mercado (cantón × mes).

    Recupera la utilidad media de las cuotas observadas (inversión de Berry: delta_j =
    ln s_j − sigma ln s_{j|g}, normalizando la opción externa a 0), aplica el cambio y
    devuelve el monto que gana o pierde cada competidor con el flujo total fijo."""
    m = mercado.copy()
    delta = (m["ln_s"] - sigma * m["ln_s_g"]).to_numpy()
    base = cuotas_logit_anidado(delta, m["nido"].to_numpy(), sigma)
    nuevo = delta.copy()
    es = (m["entidad_codigo"] == entidad).to_numpy()
    nuevo[es] += alpha * delta_tasa_pp
    s1 = cuotas_logit_anidado(nuevo, m["nido"].to_numpy(), sigma)
    total = m["monto"].sum()
    m["cuota_base"] = base
    m["cuota_nueva"] = s1
    m["cambio_monto"] = (s1 - base) * total
    return m[["entidad_codigo", "tipo_entidad", "nido", "monto", "tasa", "cuota_base",
              "cuota_nueva", "cambio_monto"]]


def simular_todos(d: pd.DataFrame, entidad: str, delta_tasa_pp: float, alpha: float,
                  sigma: float = 0.0, meses: int = 6) -> pd.DataFrame:
    """Aplica `simular` en cada cantón donde `entidad` captó en los últimos `meses` meses
    y devuelve el cambio mensual promedio de monto por cantón y competidor."""
    ult = sorted(d["anio_mes"].unique())[-meses:]
    partes = []
    for mercado, m in d[d["anio_mes"].isin(ult)].groupby("mercado"):
        if (m["entidad_codigo"] == entidad).any():
            r = simular(m, entidad, delta_tasa_pp, alpha, sigma)
            r["canton"] = m["canton"].iloc[0]
            r["anio_mes"] = m["anio_mes"].iloc[0]
            partes.append(r)
    out = pd.concat(partes)
    out["cambio_monto"] /= len(ult)
    return out


def elasticidades(d: pd.DataFrame, alpha: float, sigma: float) -> pd.DataFrame:
    """Elasticidad propia y cruzadas (Berry, 1994) por observación, con cuotas internas:
    propia   = alpha * r_j * (1/(1-sigma) - sigma/(1-sigma) * s_{j|g} - s_j)
    mismo nido (efecto de r_j sobre un rival k del nido) = -alpha * r_j * (sigma/(1-sigma) * s_{j|g} + s_j)
    otro nido = -alpha * r_j * s_j"""
    r, s, sg = d["tasa"], d["s"], d["s_g"]
    out = d[["entidad_codigo", "tipo_entidad", "nido", "anio_mes", "canton", "monto"]].copy()
    out["elasticidad_propia"] = alpha * r * (1 / (1 - sigma) - sigma / (1 - sigma) * sg - s)
    out["elasticidad_cruzada_mismo_nido"] = -alpha * r * (sigma / (1 - sigma) * sg + s)
    out["elasticidad_cruzada_otro_nido"] = -alpha * r * s
    return out

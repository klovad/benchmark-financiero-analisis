"""Mercado por cantón: indicadores, clustering de cantones y oportunidades por entidad.

Fuente de saldos: CAPCOL + SEPS (`panel_saldos_canton`), sin el cantón NACIONAL (no es un
mercado geográfico). Fuente de tasas locales: flujos BCE (`panel_tasas_canton_mensual`).

Advertencia de lectura: los depósitos se reportan en el cantón de la agencia que los capta;
las matrices (Quito, Guayaquil) concentran depósitos corporativos e institucionales, así
que su tamaño está inflado frente al ahorro de los hogares del cantón.

Oportunidad para una entidad (metodología "fair share" o índice de penetración, estándar
en geomarketing bancario; ver Nguyen, 2019, AEJ: Applied, sobre la localidad de los
mercados de crédito): en cada cantón se compara la cuota de la entidad con la que logra
en cantones del mismo cluster (percentil 75 de sus cuotas allí). La brecha × el tamaño
del mercado es el monto potencial si se acercara a su propio desempeño en mercados
parecidos. No es una proyección de demanda: es dónde la entidad rinde por debajo de sí
misma.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

TIPOS_MERCADO = ["BANCO PRIVADO", "COOPERATIVA", "MUTUALISTA", "BANCO PUBLICO"]


def indicadores_canton(saldos: pd.DataFrame, tasas: pd.DataFrame | None = None,
                       corte: int | None = None, meses_crecimiento: int = 36) -> pd.DataFrame:
    """Una fila por cantón con tamaño, crecimiento, estructura competitiva y tasas locales."""
    s = saldos[(saldos["canton"] != "NACIONAL") & saldos["tipo_entidad"].isin(TIPOS_MERCADO)]
    corte = corte or int(s["anio_mes"].max())
    anio, mes = divmod(corte, 100)
    p = pd.Period(year=anio, month=mes, freq="M") - meses_crecimiento
    base = p.year * 100 + p.month
    claves = ["canton_id", "canton", "provincia", "region"]
    act = s[s["anio_mes"] == corte]
    ant = s[s["anio_mes"] == base]

    out = act.groupby(claves)[["cartera", "depositos", "dep_plazo", "dep_vista",
                               "cartera_improductiva", "clientes_dep", "cartera_consumo",
                               "cartera_micro", "cartera_productivo"]].sum()
    prev = ant.groupby(claves)[["cartera", "depositos"]].sum()
    años = meses_crecimiento / 12
    out["crec_cartera"] = (out["cartera"] / prev["cartera"]) ** (1 / años) - 1
    out["crec_depositos"] = (out["depositos"] / prev["depositos"]) ** (1 / años) - 1
    out["cartera_depositos"] = out["cartera"] / out["depositos"]
    out["morosidad"] = out["cartera_improductiva"] / out["cartera"]
    out["dep_por_cliente"] = out["depositos"] / out["clientes_dep"]
    out["peso_micro"] = out["cartera_micro"] / out["cartera"]
    out["peso_consumo"] = out["cartera_consumo"] / out["cartera"]

    por_tipo = act.groupby(claves + ["tipo_entidad"])[["cartera", "depositos"]].sum()
    for m in ["cartera", "depositos"]:
        u = por_tipo[m].unstack("tipo_entidad").fillna(0)
        out[f"cuota_coop_{m}"] = u.get("COOPERATIVA", 0) / u.sum(axis=1)
        u0 = ant.groupby(claves + ["tipo_entidad"])[m].sum().unstack("tipo_entidad").fillna(0)
        cuota0 = u0.get("COOPERATIVA", 0) / u0.sum(axis=1)
        out[f"avance_coop_{m}_pp"] = (out[f"cuota_coop_{m}"] - cuota0) * 100

    ent = act.groupby(claves + ["entidad_codigo"])["depositos"].sum()
    cuotas = ent / ent.groupby(level=claves).transform("sum")
    out["hhi_depositos"] = (cuotas ** 2).groupby(level=claves).sum() * 10_000
    out["entidades"] = ent[ent > 0].groupby(level=claves).size()
    out["bancos"] = act[act["tipo_entidad"] == "BANCO PRIVADO"].groupby(claves)["entidad_codigo"].nunique()
    out["bancos"] = out["bancos"].fillna(0)

    if tasas is not None:
        t = tasas[(tasas["producto"] == "DEP_PLAZO") & (tasas["anio_mes"] > base + 200)
                  & (tasas["canton"] != "NACIONAL")].copy()
        t["_tw"] = t["tasa"] * t["monto"]
        g = t.groupby(["canton_id", "tipo_entidad"])[["_tw", "monto"]].sum()
        r = (g["_tw"] / g["monto"]).unstack("tipo_entidad")
        out = out.join(r.rename(columns={"BANCO PRIVADO": "tasa_plazo_bancos",
                                         "COOPERATIVA": "tasa_plazo_coops"})[
            ["tasa_plazo_bancos", "tasa_plazo_coops"]], on="canton_id")
        out["spread_coop_banco"] = out["tasa_plazo_coops"] - out["tasa_plazo_bancos"]
    return out.reset_index()


# Probadas varias combinaciones (con HHI, morosidad, n.º de bancos, crecimiento de cartera):
# todas dan silueta 0,18-0,25. Los cantones son un continuo; el clustering es una
# segmentación práctica para comparar "mercados parecidos", no grupos naturales.
VARIABLES_CLUSTER = ["log_depositos", "cuota_coop_depositos", "peso_micro",
                     "cartera_depositos", "crec_depositos"]


def clusters_canton(ind: pd.DataFrame, k: int | None = 5, minimo_depositos: float = 2e7,
                    semilla: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """K-means sobre variables estandarizadas (log tamaño, crecimiento, estructura).
    Si `k` es None se elige entre 4 y 8 por silueta. Por defecto solo cantones con al menos
    USD 20 M de depósitos (los menores tienen cuotas muy ruidosas). Devuelve (indicadores
    con cluster, tabla de siluetas)."""
    d = ind[ind["depositos"] >= minimo_depositos].copy()
    d["log_depositos"] = np.log(d["depositos"])
    X = d[VARIABLES_CLUSTER].replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median()).clip(X.quantile(0.02), X.quantile(0.98), axis=1)
    Z = StandardScaler().fit_transform(X)
    sil = []
    for kk in range(4, 9):
        lab = KMeans(kk, n_init=20, random_state=semilla).fit_predict(Z)
        sil.append((kk, silhouette_score(Z, lab)))
    sil = pd.DataFrame(sil, columns=["k", "silueta"])
    k = k or int(sil.loc[sil["silueta"].idxmax(), "k"])
    km = KMeans(k, n_init=50, random_state=semilla).fit(Z)
    d["cluster"] = km.labels_
    # Ordenar clusters por tamaño medio para que la numeración sea estable y legible.
    orden = d.groupby("cluster")["log_depositos"].mean().sort_values(ascending=False).index
    d["cluster"] = d["cluster"].map({c: i + 1 for i, c in enumerate(orden)})
    return d, sil


def oportunidades_entidad(saldos: pd.DataFrame, cantones: pd.DataFrame, entidad: str,
                          medida: str = "depositos", percentil: float = 0.75,
                          minimo_grupo: int = 5) -> pd.DataFrame:
    """Brecha de cuota de `entidad` en cada cantón frente al percentil `percentil` de sus
    propias cuotas en cantones del mismo cluster **y región** (una marca costeña no rinde
    igual en la Sierra; comparar sin región confunde arraigo regional con oportunidad).
    Si el grupo cluster × región tiene menos de `minimo_grupo` cantones, se usa el cluster.
    Monto potencial = brecha × mercado."""
    corte = int(saldos["anio_mes"].max())
    act = saldos[(saldos["anio_mes"] == corte) & saldos["tipo_entidad"].isin(TIPOS_MERCADO)]
    mio = act[act["entidad_codigo"] == entidad].groupby("canton_id")[medida].sum()
    d = cantones[["canton_id", "canton", "provincia", "region", "cluster", medida]].copy()
    d["saldo_entidad"] = d["canton_id"].map(mio).fillna(0)
    d["cuota"] = d["saldo_entidad"] / d[medida]
    por_region = d.groupby(["cluster", "region"])["cuota"]
    objetivo = por_region.transform(lambda c: c.quantile(percentil))
    n = por_region.transform("size")
    respaldo = d.groupby("cluster")["cuota"].transform(lambda c: c.quantile(percentil))
    d["cuota_objetivo"] = objetivo.where(n >= minimo_grupo, respaldo)
    d["brecha_pp"] = (d["cuota_objetivo"] - d["cuota"]).clip(lower=0) * 100
    d["potencial_usd"] = d["brecha_pp"] / 100 * d[medida]
    d["presente"] = d["saldo_entidad"] > 0
    return d.sort_values("potencial_usd", ascending=False)

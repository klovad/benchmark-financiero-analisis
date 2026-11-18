"""Segmentación de entidades por modelo de negocio (clustering).

Siguiendo a Roengpitya, Tarashev y Tsatsaronis (2014, BIS Quarterly Review, "Bank
business models") y Ayadi et al. (2011+, Banking Business Models Monitor): variables de
estructura de balance que la entidad **elige** (mezcla de cartera, fondeo, liquidez,
tamaño, alcance geográfico), no de resultado; ROA, morosidad y costo quedan fuera del
clustering y se usan después para comparar el desempeño entre grupos. Así el grupo dice
"a qué se dedica" y el desempeño se evalúa contra pares reales (Amel y Rhoades, 1988,
"Strategic groups in banking", REStat).

Universo: bancos privados, cooperativas segmento 1 y mutualistas con balance en el corte.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

VARIABLES_MODELO = [
    "log_activo", "cartera_activo", "depositos_pasivo", "peso_plazo", "peso_consumo",
    "peso_micro", "peso_productivo", "peso_vivienda", "liquidez_activo", "cantones_hhi",
]
VARIABLES_DESEMPENO = ["roa", "roe", "morosidad", "gasto_operativo_activo", "costo_fondeo",
                       "rendimiento_activo", "patrimonio_activo", "crec_cartera_12m",
                       "crec_depositos_12m"]


def tabla_entidades(indicadores: pd.DataFrame, saldos: pd.DataFrame, corte: int) -> pd.DataFrame:
    """Variables de modelo de negocio y de desempeño por entidad al `corte` (anio_mes)."""
    ind = indicadores[indicadores["anio_mes"] == corte].set_index("entidad_codigo")
    s = saldos[saldos["anio_mes"] == corte]
    mix = s.groupby("entidad_codigo")[["cartera", "cartera_consumo", "cartera_micro",
                                       "cartera_productivo", "cartera_vivienda",
                                       "depositos", "dep_plazo"]].sum()
    por_canton = s.groupby(["entidad_codigo", "canton"])["cartera"].sum()
    cuota = por_canton / por_canton.groupby(level=0).transform("sum")
    hhi = (cuota ** 2).groupby(level=0).sum()

    hace12 = (pd.Period(year=corte // 100, month=corte % 100, freq="M") - 12)
    s12 = saldos[saldos["anio_mes"] == hace12.year * 100 + hace12.month]
    base = s12.groupby("entidad_codigo")[["cartera", "depositos"]].sum()

    d = pd.DataFrame(index=ind.index)
    d["entidad"] = ind["entidad"]
    d["tipo_entidad"] = ind["tipo_entidad"]
    d["segmento_entidad"] = ind["segmento_entidad"]
    d["activo"] = ind["activo"]
    d["log_activo"] = np.log(ind["activo"])
    d["cartera_activo"] = ind["cartera_bruta"] / ind["activo"]
    d["depositos_pasivo"] = ind["depositos"] / ind["pasivo"]
    d["liquidez_activo"] = ind["fondos_disponibles"] / ind["activo"]
    d["peso_plazo"] = mix["dep_plazo"] / mix["depositos"]
    for seg in ["consumo", "micro", "productivo", "vivienda"]:
        d[f"peso_{seg}"] = mix[f"cartera_{seg}"].fillna(0) / mix["cartera"]
    d["cantones_hhi"] = hhi
    for c in ["roa", "roe", "morosidad", "gasto_operativo_activo", "costo_fondeo",
              "rendimiento_activo", "patrimonio_activo"]:
        d[c] = ind[c]
    d["crec_cartera_12m"] = mix["cartera"] / base["cartera"] - 1
    d["crec_depositos_12m"] = mix["depositos"] / base["depositos"] - 1
    return d


def universo(d: pd.DataFrame, activo_minimo: float = 1e8) -> pd.DataFrame:
    """Bancos privados, cooperativas S1 y mutualistas con activo >= `activo_minimo`."""
    m = ((d["tipo_entidad"] == "BANCO PRIVADO")
         | ((d["tipo_entidad"] == "COOPERATIVA") & (d["segmento_entidad"] == "SEGMENTO 1"))
         | (d["tipo_entidad"] == "MUTUALISTA"))
    return d[m & (d["activo"] >= activo_minimo)].dropna(subset=VARIABLES_MODELO)


def agrupar(d: pd.DataFrame, k: int | None = None, semilla: int = 7, tolerancia: float = 0.01):
    """Ward jerárquico para elegir k (silueta 3-8) y K-means inicializado en los
    centroides de Ward para refinar. Devuelve (tabla con cluster, siluetas, Z estandarizada).

    Elección de k por parsimonia: el menor k cuya silueta está a `tolerancia` o menos del
    máximo. Con el máximo estricto, k saltaba entre 4 y 5 de un mes a otro (siluetas 0,368
    vs. 0,372 con el corte 2026-09) y los grupos del informe cambiaban sin que cambiara el
    mercado."""
    X = d[VARIABLES_MODELO].clip(d[VARIABLES_MODELO].quantile(0.02),
                                 d[VARIABLES_MODELO].quantile(0.98), axis=1)
    Z = StandardScaler().fit_transform(X)
    L = linkage(Z, method="ward")
    sil = pd.DataFrame([(kk, silhouette_score(Z, fcluster(L, kk, "maxclust")))
                        for kk in range(3, 9)], columns=["k", "silueta"])
    k = k or int(sil.loc[sil["silueta"] >= sil["silueta"].max() - tolerancia, "k"].min())
    ward = fcluster(L, k, "maxclust")
    centros = np.vstack([Z[ward == c].mean(axis=0) for c in np.unique(ward)])
    km = KMeans(k, init=centros, n_init=1, random_state=semilla).fit(Z)
    out = d.copy()
    out["cluster"] = km.labels_ + 1
    return out, sil, pd.DataFrame(Z, index=d.index, columns=VARIABLES_MODELO)


def pares_cercanos(Z: pd.DataFrame, entidad: str, n: int = 8) -> pd.Series:
    """Las `n` entidades más parecidas a `entidad` (distancia euclídea en variables
    estandarizadas de modelo de negocio)."""
    dist = np.sqrt(((Z - Z.loc[entidad]) ** 2).sum(axis=1)).drop(entidad)
    return dist.sort_values().head(n)

"""Series de tasas comparables entre entidades a partir de los flujos semanales del BCE.

Problema: la tasa ponderada de una entidad mezcla plazos; si una semana capta más a 360
días, su tasa "sube" sin haber cambiado precios. Se corrige con un modelo hedónico

    tasa[e, b, t] = mu[e, t] + beta[b] + error        (ponderado por monto)

con efecto fijo de banda de plazo `beta[b]` (o de segmento de crédito en colocaciones)
y efecto fijo entidad×semana `mu[e, t]`. `mu` es la tasa de la entidad a mezcla de plazos
constante: es la serie que se usa para comparar, detectar movimientos y medir liderazgo.
Mismo enfoque que los índices de precios hedónicos (Triplett, 2006, OECD Handbook on
Hedonic Indexes) aplicado a tasas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Grupos de comparación: bancos grandes uno a uno, el resto agregado por tipo/segmento.
BANCOS_FOCO = [
    "PICHINCHA", "GUAYAQUIL", "PACIFICO", "PRODUBANCO", "INTERNACIONAL", "BOLIVARIANO",
    "AUSTRO", "DINERS", "GENERAL_RUMINAHUI", "MACHALA", "LOJA", "SOLIDARIO", "PROCREDIT",
]


def efecto_fijo_hedonico(df: pd.DataFrame, celda: str, caracteristica: str,
                         valor: str = "tasa", peso: str = "monto", iteraciones: int = 30) -> pd.Series:
    """Estima beta[caracteristica] en valor = mu[celda] + beta[caracteristica] por
    proyecciones alternadas ponderadas (equivale a MCO ponderado con dos efectos fijos).
    Normalización: beta ponderado por monto suma cero."""
    d = df[[celda, caracteristica, valor, peso]].dropna()
    w = d[peso].to_numpy()
    y = d[valor].to_numpy()
    c_idx, _ = pd.factorize(d[celda])
    k_idx, k_cat = pd.factorize(d[caracteristica])
    beta = np.zeros(len(k_cat))
    for _ in range(iteraciones):
        r = y - beta[k_idx]
        mu = np.bincount(c_idx, w * r) / np.bincount(c_idx, w)
        r = y - mu[c_idx]
        beta_nuevo = np.bincount(k_idx, w * r) / np.bincount(k_idx, w)
        beta_nuevo -= np.average(beta_nuevo[k_idx], weights=w)
        if np.max(np.abs(beta_nuevo - beta)) < 1e-8:
            beta = beta_nuevo
            break
        beta = beta_nuevo
    return pd.Series(beta, index=k_cat, name="efecto_fijo")


def tasa_ajustada(df: pd.DataFrame, caracteristica: str, grupo: str = "entidad_codigo",
                  tiempo: str = "fecha_id") -> pd.DataFrame:
    """Tasa a mezcla constante por grupo × tiempo: promedio ponderado de (tasa − beta).

    `df` trae una fila por grupo × tiempo × característica con `tasa` y `monto`. El efecto
    fijo se estima por separado para cada `tipo_entidad` si la columna existe, porque la
    prima por plazo de una cooperativa no es la de un banco."""
    partes = []
    claves = df["tipo_entidad"].unique() if "tipo_entidad" in df else [None]
    for tipo in claves:
        d = df if tipo is None else df[df["tipo_entidad"] == tipo]
        d = d.copy()
        d["_celda"] = d[grupo].astype(str) + "|" + d[tiempo].astype(str)
        beta = efecto_fijo_hedonico(d, "_celda", caracteristica)
        d["tasa_aj"] = d["tasa"] - d[caracteristica].map(beta)
        partes.append(d)
    d = pd.concat(partes)
    d["_tw"] = d["tasa_aj"] * d["monto"]
    out = d.groupby([grupo, tiempo], as_index=False).agg(
        _tw=("_tw", "sum"), monto=("monto", "sum"), operaciones=("operaciones", "sum"))
    out["tasa_aj"] = out.pop("_tw") / out["monto"]
    return out


def grupo_comparacion(fila_tipo: pd.Series, fila_codigo: pd.Series, fila_segmento: pd.Series) -> pd.Series:
    """Asigna cada entidad a su serie: banco foco por nombre; resto de bancos privados como
    'OTROS BANCOS'; cooperativas por segmento de esa semana ('COOP SEGMENTO 1'...);
    mutualistas y públicos agregados."""
    g = np.where(fila_codigo.isin(BANCOS_FOCO), fila_codigo,
         np.where(fila_tipo == "BANCO PRIVADO", "OTROS BANCOS",
         np.where(fila_tipo == "COOPERATIVA", "COOP " + fila_segmento.fillna("SIN SEGMENTO"),
                  fila_tipo)))
    return pd.Series(g, index=fila_tipo.index)


def series_semanales(tasas: pd.DataFrame, caracteristica: str = "plazo_codigo") -> pd.DataFrame:
    """Panel semanal ancho: columnas = grupos de comparación, valores = tasa ajustada.

    El ajuste se hace por entidad y luego se agrega al grupo ponderando por monto, para
    que un grupo (p. ej. cooperativas S1) no cambie de tasa solo porque esa semana captó
    más una cooperativa cara."""
    t = tasas.copy()
    t["grupo"] = grupo_comparacion(t["tipo_entidad"], t["entidad_codigo"], t["segmento_semana"])
    ent = tasa_ajustada(t, caracteristica)
    ent = ent.merge(t[["entidad_codigo", "fecha_id", "grupo"]].drop_duplicates(),
                    on=["entidad_codigo", "fecha_id"])
    ent["_tw"] = ent["tasa_aj"] * ent["monto"]
    g = ent.groupby(["fecha_id", "grupo"]).agg(_tw=("_tw", "sum"), monto=("monto", "sum"))
    g["tasa_aj"] = g["_tw"] / g["monto"]
    ancho = g["tasa_aj"].unstack("grupo")
    ancho.index = pd.to_datetime(ancho.index.astype(str), format="%Y%m%d")
    return ancho.sort_index()

"""Paneles de análisis extraídos de marts y guardados en caché como parquet en data/.

Cada panel es un archivo `sql/panel_<nombre>.sql`. La primera llamada consulta la base y
guarda `data/panel_<nombre>.parquet`; las siguientes leen el parquet (la base se
actualiza los lunes: pasar `refrescar=True` después de una carga del ETL).

Uso:
    from benchmark_analisis.paneles import panel
    saldos = panel("saldos_canton")
    tasas = panel("tasas_captacion_semanal", desde=20150101)
"""

from __future__ import annotations

import pandas as pd

from benchmark_analisis.db import RAIZ, consulta_archivo

DATA_DIR = RAIZ / "data"

# Parámetros por defecto de cada panel (los que no se pasen explícitamente).
PARAMETROS = {
    "tasas_captacion_semanal": {"desde": 20150101},
    "tasas_colocacion_semanal": {"desde": 20150101},
    "tasas_canton_mensual": {"desde": 20210101},
}


def panel(nombre: str, refrescar: bool = False, **params) -> pd.DataFrame:
    """Devuelve el panel `nombre` desde caché o desde la base."""
    params = {**PARAMETROS.get(nombre, {}), **params}
    sufijo = "".join(f"_{k}{v}" for k, v in sorted(params.items()))
    archivo = DATA_DIR / f"panel_{nombre}{sufijo}.parquet"
    if archivo.exists() and not refrescar:
        return pd.read_parquet(archivo)
    df = consulta_archivo(f"panel_{nombre}.sql", **params)
    for col in df.columns:
        if df[col].dtype == object and col not in _COLUMNAS_TEXTO:
            convertida = pd.to_numeric(df[col], errors="coerce")
            if convertida.notna().sum() == df[col].notna().sum():
                df[col] = convertida
    DATA_DIR.mkdir(exist_ok=True)
    df.to_parquet(archivo, index=False)
    return df


# Columnas de texto que no deben convertirse a número aunque parezcan (códigos).
_COLUMNAS_TEXTO = {
    "entidad_codigo", "entidad", "tipo_entidad", "segmento_entidad", "segmento_semana",
    "canton", "provincia", "region", "plazo_codigo", "segmento", "producto",
}

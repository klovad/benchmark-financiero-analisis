"""Conexión de solo lectura al data mart y helpers para traer DataFrames.

La configuración sale de `.env` en la raíz del repo (ver `.env.example`). Toda sesión se
abre con `default_transaction_read_only=on`, además de que el rol `analista` ya lo tiene
fijado en la base: ni un notebook con un error puede escribir.

Uso:
    from benchmark_analisis import consulta, consulta_archivo
    df = consulta("SELECT * FROM marts.dim_entidad WHERE tipo_entidad = :tipo", tipo="BANCO PRIVADO")
    df = consulta_archivo("cobertura.sql")
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine


def raiz_proyecto() -> Path:
    """Primer directorio desde el cwd hacia arriba con pyproject.toml (los notebooks corren
    desde notebooks/, los scripts desde la raíz)."""
    cwd = Path.cwd().resolve()
    for d in (cwd, *cwd.parents):
        if (d / "pyproject.toml").exists():
            return d
    return cwd


RAIZ = raiz_proyecto()
SQL_DIR = RAIZ / "sql"
load_dotenv(RAIZ / ".env")


@lru_cache(maxsize=1)
def motor() -> Engine:
    url = URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "analista"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "benchmark_cartera_depositos"),
    )
    return create_engine(
        url,
        connect_args={"options": "-c default_transaction_read_only=on"},
        pool_pre_ping=True,
    )


def consulta(sql: str, **params) -> pd.DataFrame:
    """Ejecuta un SELECT y devuelve un DataFrame. Parámetros con sintaxis `:nombre`."""
    with motor().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or None)


def consulta_archivo(nombre: str, **params) -> pd.DataFrame:
    """Igual que `consulta`, leyendo el SQL de sql/<nombre>."""
    return consulta((SQL_DIR / nombre).read_text(encoding="utf-8"), **params)

"""Copia a docs/referencia_etl/ la documentación del repo del ETL que sirve para analizar
(definiciones de tablas, métricas, glosario de cuentas, fuentes). La fuente de verdad es
el repo del ETL; estas copias solo evitan depender de tenerlo abierto.

    uv run python scripts/sincronizar_docs_etl.py

La ruta del ETL sale de ETL_REPO en .env (por defecto ../benchmark-bancos).
"""

from __future__ import annotations

import datetime
import os
import subprocess

from benchmark_analisis.db import RAIZ

DOCS = [
    "data_dictionary.md",
    "metricas_financieras.md",
    "glosario_cuentas.md",
    "indicadores_excel_bcos_coop.md",
    "fuentes_datos.md",
    "linaje_datos.md",
    "gobernanza_datos.md",
]


def main() -> None:
    etl = (RAIZ / os.getenv("ETL_REPO", "../benchmark-bancos")).resolve()
    origen = etl / "docs"
    if not origen.is_dir():
        raise SystemExit(f"No encuentro {origen}: revisar ETL_REPO en .env")
    try:
        commit = subprocess.run(
            ["git", "-C", str(etl), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "desconocido"
    destino = RAIZ / "docs" / "referencia_etl"
    destino.mkdir(parents=True, exist_ok=True)
    cabecera = (
        f"<!-- Copia de benchmark-bancos/docs (commit {commit}, "
        f"{datetime.date.today():%Y-%m-%d}). No editar acá: la fuente de verdad es el repo "
        "del ETL; actualizar con scripts/sincronizar_docs_etl.py. -->\n\n"
    )
    for nombre in DOCS:
        texto = (origen / nombre).read_text(encoding="utf-8")
        (destino / nombre).write_text(cabecera + texto, encoding="utf-8")
        print(f"copiado {nombre}")
    print(f"{len(DOCS)} documentos desde {etl.name}@{commit}")


if __name__ == "__main__":
    main()

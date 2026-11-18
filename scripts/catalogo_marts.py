"""Genera docs/catalogo_marts.md desde la base: tablas y vistas de marts, columnas, tipos,
filas aproximadas y rango de fecha_id. Correr después de cambios en el ETL:

    uv run python scripts/catalogo_marts.py
"""

from __future__ import annotations

import datetime

from sqlalchemy import text

from benchmark_analisis.db import RAIZ, motor

SALIDA = RAIZ / "docs" / "catalogo_marts.md"


def main() -> None:
    with motor().connect() as conn:
        objetos = conn.execute(
            text(
                """
                SELECT c.relname, CASE c.relkind WHEN 'v' THEN 'vista' ELSE 'tabla' END,
                       GREATEST(c.reltuples, 0)::bigint, obj_description(c.oid)
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'marts' AND c.relkind IN ('r', 'v', 'p')
                ORDER BY c.relkind DESC, c.relname
                """
            )
        ).all()
        lineas = [
            "# Catálogo de `marts` (generado)",
            "",
            (
                f"Generado por `scripts/catalogo_marts.py` el {datetime.date.today():%Y-%m-%d}. "
                "No editar a mano: volver a correr el script. Semántica y advertencias en "
                "`docs/guia_modelo.md`; definiciones completas en `docs/referencia_etl/`."
            ),
            "",
            "| Objeto | Tipo | Filas (aprox.) | Rango fecha_id |",
            "|---|---|---|---|",
        ]
        detalle = []
        for nombre, tipo, filas, comentario in objetos:
            columnas = conn.execute(
                text(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'marts' AND table_name = :t
                    ORDER BY ordinal_position
                    """
                ),
                {"t": nombre},
            ).all()
            rango = ""
            if tipo == "tabla" and any(c[0] == "fecha_id" for c in columnas):
                desde, hasta = conn.execute(
                    text(f"SELECT min(fecha_id), max(fecha_id) FROM marts.{nombre}")
                ).one()
                rango = f"{desde} – {hasta}" if desde else "(vacía)"
            filas_txt = f"{filas:,}".replace(",", ".") if tipo == "tabla" else "—"
            lineas.append(f"| `{nombre}` | {tipo} | {filas_txt} | {rango} |")
            detalle += ["", f"### `marts.{nombre}` ({tipo})", ""]
            if comentario:
                detalle += [comentario, ""]
            detalle += ["| Columna | Tipo |", "|---|---|"]
            detalle += [f"| {c} | {t} |" for c, t in columnas]
    SALIDA.write_text("\n".join(lineas + ["", "## Columnas"] + detalle) + "\n", encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)} ({len(objetos)} objetos)")


if __name__ == "__main__":
    main()

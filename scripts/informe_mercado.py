"""Genera salidas/mercado/informe_mercado.html a partir de salidas/mercado/resultados.json
y del glosario docs/glosario_analisis.md (fuente única de términos e interpretación).

    uv run python scripts/analisis_mercado.py   # primero, calcula los resultados
    uv run python scripts/informe_mercado.py

El HTML es autocontenido (datos embebidos, sin librerías externas): se abre con doble
clic y se puede compartir como archivo.
"""

from __future__ import annotations

import json
import re

from benchmark_analisis.db import RAIZ

SALIDA = RAIZ / "salidas" / "mercado"
PLANTILLA = RAIZ / "scripts" / "plantillas" / "informe_mercado.html"
GLOSARIO = RAIZ / "docs" / "glosario_analisis.md"


def leer_glosario(texto: str) -> list[dict]:
    """Grupos (`## título`) con sus filas de tabla (término | qué es | cómo se lee)."""
    grupos: list[dict] = []
    for linea in texto.splitlines():
        if linea.startswith("## "):
            grupos.append({"grupo": linea[3:].strip(), "terminos": []})
            continue
        if not grupos or not linea.startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) != 3 or celdas[0] == "Término" or re.fullmatch(r"-+", celdas[0]):
            continue
        grupos[-1]["terminos"].append({"termino": celdas[0], "que_es": _plano(celdas[1]),
                                       "como_se_lee": _plano(celdas[2])})
    return [g for g in grupos if g["terminos"]]


def _plano(s: str) -> str:
    """Quita el marcado de código de markdown (el HTML lo muestra como texto)."""
    return s.replace("`", "")


def _embebible(obj) -> str:
    # </ dentro de un <script> cerraría la etiqueta: se escapa.
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def main() -> None:
    datos = json.loads((SALIDA / "resultados.json").read_text(encoding="utf-8"))
    glosario = leer_glosario(GLOSARIO.read_text(encoding="utf-8"))
    html = PLANTILLA.read_text(encoding="utf-8")
    html = html.replace("__DATOS__", _embebible(datos)).replace("__GLOSARIO__", _embebible(glosario))
    destino = SALIDA / "informe_mercado.html"
    destino.write_text(html, encoding="utf-8")
    print(f"informe: {destino} ({sum(len(g['terminos']) for g in glosario)} términos de glosario)")


if __name__ == "__main__":
    main()

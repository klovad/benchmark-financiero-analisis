# Cómo trabajar en este repo

## Antes de dar una cifra

1. Leer [`docs/guia_modelo.md`](docs/guia_modelo.md): granos, coberturas y las 15 reglas
   (mezcla de tipos de entidad, tasas ponderadas por monto, cantón `NACIONAL`,
   mutualistas, ids vs. `entidad_codigo`, etc.).
2. Columnas exactas en [`docs/catalogo_marts.md`](docs/catalogo_marts.md). Si parece
   desactualizado: `uv run python scripts/catalogo_marts.py`.
3. Definiciones, fórmulas de indicadores y cuentas contables en `docs/referencia_etl/`
   (copias de los docs del ETL; actualizar con `uv run python scripts/sincronizar_docs_etl.py`).
   Los indicadores financieros usan las fórmulas de `metricas_financieras.md`, sin variantes.
4. Verificar con datos reales: cruzar totales con `marts.vw_conciliacion_resumen` y con la
   cobertura (`sql/cobertura.sql`). Toda cifra lleva período, tipo de entidad y fuente.

## Dónde va cada cosa

| Qué | Dónde |
|---|---|
| Conexión | `from benchmark_analisis import consulta, consulta_archivo` (rol `analista`, solo lectura; credenciales en `.env`) |
| SQL reutilizable | `sql/*.sql`, con parámetros `:nombre` |
| Código compartido y modelos | `src/benchmark_analisis/` |
| Exploración | `notebooks/NN_tema.ipynb`, guardados sin salidas (`uv run nbstripout --install`) |
| Resultados (CSV, Excel, HTML, imágenes) | `salidas/` (no versionado) |
| Extracciones grandes y paneles en caché | `data/` (no versionado) |
| Términos e interpretación | `docs/glosario_analisis.md` (fuente única; el informe lo inserta) |

## Cambios al modelo de datos

Este repo nunca escribe en la base. Si un análisis necesita algo que `marts` no tiene (una
vista de indicador reutilizable, una dimensión, una columna), se anota en
[`docs/pedidos_al_etl.md`](docs/pedidos_al_etl.md) con el porqué y se implementa en el ETL
como migración. Los cálculos de un solo análisis sí viven aquí.

## Antes de un commit

- `uv run pytest` y `uv run ruff check .` sin errores.
- Documentación al día en el mismo cambio (README, `docs/`), incluidas las fechas de
  "Estado" y las cifras citadas si se refrescaron los datos.
- Nunca versionar `.env`, `data/` ni `salidas/`.

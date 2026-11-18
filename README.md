# benchmark-analisis

Análisis del mercado de depósitos y crédito del sistema financiero de Ecuador (bancos
privados y públicos, cooperativas, mutualistas): saldos y cuotas por cantón, tasas efectivas
semanales del BCE, sustitución bancos ↔ cooperativas, elasticidades de demanda, liderazgo y
anticipación de movimientos de tasa, oportunidades por ciudad, modelos de negocio y un plan
de acción para una entidad (por defecto Banco Guayaquil). El resultado es un informe HTML
interactivo con 13 capítulos, filtros y un simulador de tasas.

Este repo **solo lee** el data mart (`marts.*`, esquema estrella en Postgres) que construye
el ETL [benchmark-financiero](https://github.com/klovad/benchmark-financiero). La descarga,
la limpieza y el modelo de datos viven allá; aquí no se escribe en la base.

## Requisitos

| Qué | Versión | Para qué |
|---|---|---|
| [Git](https://git-scm.com/) | cualquiera | clonar los dos repos |
| [uv](https://docs.astral.sh/uv/) | ≥ 0.4 | entorno y dependencias (instala Python 3.12 solo) |
| PostgreSQL | 17 | la base del ETL (local o en Docker) |
| Base cargada por el ETL | — | ver su README: primera carga ≈ 70 min |

Los comandos están en PowerShell (Windows); en Linux/macOS son iguales salvo `Copy-Item`
(→ `cp`) y la ruta de `psql`.

## Replicar paso a paso

**1. Base de datos (repo del ETL).** Clonarlo **en una carpeta hermana llamada
`benchmark-bancos`** (es la ruta que asume `.env.example`; si se usa otra, cambiar
`ETL_REPO`), y seguir su Quickstart hasta tener la primera carga completa:

```powershell
git clone https://github.com/klovad/benchmark-financiero.git benchmark-bancos
```

**2. Rol de solo lectura** `analista` (una vez por servidor, como superusuario). Detalle y
solución de problemas en [`docs/acceso_datos.md`](docs/acceso_datos.md):

```powershell
cd benchmark-bancos
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -v app_db=benchmark_cartera_depositos -f sql/admin/rol_lectura.sql
cd ..
```

**3. Este repo.**

```powershell
git clone https://github.com/klovad/benchmark-financiero-analisis.git benchmark-analisis
cd benchmark-analisis
Copy-Item .env.example .env      # completar POSTGRES_PASSWORD con la del rol analista
uv sync                          # crea .venv con Python 3.12 y las dependencias exactas de uv.lock
uv run nbstripout --install      # opcional: guarda los notebooks sin salidas
```

**4. Verificar la conexión.** Debe imprimir `analista` y el número de entidades:

```powershell
uv run python -c "from benchmark_analisis import consulta; print(consulta('select current_user, count(*) from marts.dim_entidad group by 1'))"
uv run python -c "from benchmark_analisis import consulta_archivo; print(consulta_archivo('cobertura.sql'))"
```

**5. Correr el análisis y generar el informe.**

```powershell
uv run python scripts/analisis_mercado.py --refrescar   # primera vez: consulta la base y guarda paneles en data/ (~5 min)
uv run python scripts/informe_mercado.py                # salidas/mercado/informe_mercado.html
```

Las corridas siguientes, sin `--refrescar`, usan los paneles en caché (~2-3 min). Hay que
refrescar después de cada carga del ETL (corre los lunes). `--entidad PICHINCHA` (o
cualquier `entidad_codigo`) arma el plan de acción para otra entidad.

**6. Ver el informe.** Es un único HTML autocontenido (~3 MB, sin dependencias externas):
abrirlo con doble clic, o servirlo localmente:

```powershell
uv run python -m http.server 8765 --bind 127.0.0.1 --directory salidas/mercado
# http://127.0.0.1:8765/informe_mercado.html
```

**7. Pruebas y estilo.**

```powershell
uv run pytest
uv run ruff check .
```

Las pruebas usan datos sintéticos: no necesitan la base.

## Estructura

| Carpeta | Qué va |
|---|---|
| `docs/guia_modelo.md` | **Leer primero**: qué hay en `marts`, granos, coberturas y 15 reglas para no equivocarse |
| `docs/analisis_mercado.md` | Análisis de mercado: preguntas, modelos, resultados, límites y referencias académicas |
| `docs/glosario_analisis.md` | Glosario y guía de interpretación (pp, AUC, elasticidades, mora...). El informe lo incluye (capítulo 12) |
| `docs/catalogo_marts.md` | Tablas, vistas y columnas (generado: `scripts/catalogo_marts.py`) |
| `docs/referencia_etl/` | Copia de los docs del ETL: diccionario, métricas, glosario de cuentas, fuentes (`scripts/sincronizar_docs_etl.py`) |
| `docs/acceso_datos.md` | Rol `analista`, `.env` y problemas comunes |
| `docs/ideas_analisis.md` | Preguntas de análisis pendientes |
| `docs/pedidos_al_etl.md` | Lo que un análisis necesita y debe agregarse al modelo en el ETL |
| `sql/` | Consultas reutilizables (`:parametros`); las `panel_*.sql` alimentan los paneles en caché |
| `src/benchmark_analisis/` | Conexión (`consulta`, `consulta_archivo`), paneles en caché (`paneles.py`) y modelos: `tasas`, `balance`, `sustitucion`, `demanda`, `liderazgo`, `mercado`, `segmentacion`; `explorador` arma los datos del informe |
| `scripts/` | `analisis_mercado.py` (modelos → `salidas/mercado/`), `informe_mercado.py` (HTML, plantilla en `scripts/plantillas/`), utilidades de catálogo y docs |
| `notebooks/` | Exploración (`NN_tema.ipynb`) |
| `tests/` | Pruebas de los modelos con datos sintéticos |
| `salidas/`, `data/` | Resultados y paneles en caché (no versionados; se regeneran) |

## Datos disponibles (2026-11-13)

CAPCOL y SEPS (saldos por cantón) 2021-01 → 2026-09; BCE semanal 2008-01 → 2026-10;
Boletín (balance y resultados de bancos privados) y EEFF SEPS 2021-01 → 2026-09; tasas
referenciales 2009-07 → 2026-09. Detalle y coberturas por tipo de entidad en
`docs/guia_modelo.md`.

## Contribuir

Reglas de trabajo (solo lectura, dónde va cada cosa, cómo pedir cambios al modelo de datos):
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licencia

[MIT](LICENSE).

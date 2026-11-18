# Guía del modelo para análisis

Cómo leer `marts.*` sin equivocarse. El modelo lo construye y mantiene el repo
**benchmark-bancos** (ETL); este repo solo lee. Detalle completo de cada columna en
`docs/referencia_etl/data_dictionary.md`; lista viva de tablas y columnas en
`docs/catalogo_marts.md` (generado desde la base).

## 1. Qué hay

Sistema financiero de Ecuador, esquema estrella en Postgres. Estado al 2026-11-13:

| Tabla de hechos | Grano | Fuente | Entidades | Cobertura |
|---|---|---|---|---|
| `fact_saldo_cartera` | mes × entidad × cantón × segmento de crédito | CAPCOL (Superbancos) + SEPS | bancos privados y públicos, cooperativas S1-S3, mutualistas, 2 de segundo piso | 2021-01 → 2026-09 |
| `fact_saldo_depositos` | mes × entidad × cantón × categoría de depósito × plazo | CAPCOL + SEPS | ídem | 2021-01 → 2026-09 |
| `fact_colocaciones_cartera` | semana × entidad × subsegmento × plazo × cantón | BCE (tsa) | todo el sistema, incl. sociedades financieras y tarjetas (históricas) | 2008-01 → 2026-10 |
| `fact_captaciones_depositos` | semana × entidad × categoría × plazo × cantón | BCE (tsp) | ídem | 2008-01 → 2026-10 |
| `fact_balance` / `fact_pyg` | mes × entidad × cuenta contable | Boletín (Superbancos) + EEFF SEPS | bancos privados, cooperativas y mutualistas (hasta 2026-09). **Banca pública no tiene balance** | 2021-01 → |
| `fact_tasas_referenciales_*` | mes × segmento / instrumento / plazo (nivel sistema) | BCE `TasasHistorico` | — (techos y referenciales regulatorios) | 2009-07 → 2026-09 |

Dimensiones: `dim_entidad`, `dim_fecha`, `dim_canton` → `dim_provincia` (códigos INEC),
`dim_segmento_credito` ← `dim_subsegmento_credito`, `dim_categoria_deposito`, `dim_plazo`,
`dim_segmento_entidad`, `dim_cuenta_contable`.

Vistas listas para usar: cuota de mercado y HHI (`vw_cartera_market_share`,
`vw_cartera_hhi`, `vw_depositos_*`), indicadores contables (`vw_cartera_bruta`,
`vw_cartera_improductiva[_segmento]`, `vw_depositos_corto_plazo`, `vw_utilidad_acumulada`,
`vw_utilidad_anualizada`, `vw_activo_promedio_ytd`, `vw_patrimonio_promedio_ytd`,
`vw_pyg_total_gastos`), conciliación (`vw_conciliacion_saldos_balance`,
`vw_conciliacion_resumen`) y geografía (`vw_dim_canton_geografia`).

Actualización: el ETL corre solo los lunes 07:30. CAPCOL y SEPS publican con ~1 mes de
rezago (octubre 2026 se espera a fines de noviembre); BCE semanal, Boletín y
TasasHistorico van al día.

## 2. Reglas para no equivocarse

1. **Los hechos mezclan tipos de entidad.** Filtrar o agrupar siempre por
   `dim_entidad.tipo_entidad` (`BANCO PRIVADO`, `BANCO PUBLICO`, `COOPERATIVA`,
   `MUTUALISTA`, `ENTIDAD DE SEGUNDO PISO`, `SOCIEDAD FINANCIERA`, `TARJETAS DE CREDITO`)
   antes de sumar o comparar.
2. **Las vistas de cuota de mercado y HHI son sobre todo el sistema** (no filtran tipo de
   entidad). Para cuota entre pares, calcularla filtrando (ver `sql/cuota_mercado_cartera.sql`).
3. **Identificar entidades por `entidad_codigo`, no por `entidad_id`.** Los ids son llaves
   sustitutas: se renumeraron en la reconstrucción del 2026-10-10 y pueden volver a cambiar
   si la base se reconstruye. `entidad_codigo` es estable (`PICHINCHA`, `BCE_<ruc>`...).
4. **Tasas del BCE: siempre ponderadas por monto**, `SUM(tasa × monto_total) / SUM(monto_total)`,
   nunca promedio simple. `monto_total` y `numero_operaciones` sí son sumables.
5. **BCE incluye filas con cantón `NACIONAL`** (operaciones sin cantón). Son sumables y no se
   solapan con cantones reales: un total que excluya `NACIONAL` **subcuenta**. Para mapas,
   excluirlas solo en la vista geográfica y decirlo.
6. **Mutualistas: `fact_saldo_cartera` incluye cartera de vivienda vendida al fideicomiso**
   (VIS/VIP administrada), que no está en su balance. Para "cartera en balance" de
   mutualistas usar `fact_balance` (`vw_cartera_bruta`).
7. **Depósitos CAPCOL no cubren 5 subcuentas del grupo 21 del balance**: los depósitos por
   cantón de bancos quedan algo por debajo de la cuenta 21 (la conciliación tolera ±2 %).
   SEPS sí concilia casi exacto.
8. **SEPS no trae banda de plazo**: en `fact_saldo_depositos` sus filas tienen `plazo_id` NULL,
   también en depósitos a plazo.
9. **EEFF SEPS no carga saldos en cero**: un código de cuenta ausente para una entidad y mes
   equivale a 0.
10. **Cuentas contables (Catálogo Único)**: cartera bruta = `14` − `1499`; depósitos = `21`;
    PyG en `4*`/`5*`. Fórmulas de indicadores (morosidad, ROA, ROE, liquidez...) en
    `docs/referencia_etl/metricas_financieras.md`; no reinventarlas.
11. **Segmento de la entidad** (`dim_segmento_entidad`): en los hechos BCE es el de **esa
    semana** (una cooperativa cambia de segmento al crecer); `dim_entidad.segmento_entidad_id`
    es solo el último conocido. Valores: `SEGMENTO 1..5` (cooperativas), `SIN SEGMENTO`
    (cooperativas antes de 2015), `SEGMENTO 1 MUTUALISTA`, `BANCO GRANDE/MEDIANO/PEQUEÑO`,
    `BANCOS PUBLICOS`, `SOCIEDAD FINANCIERA`, `ADMINISTRADORA DE TARJETAS DE CREDITO`,
    `NO REPORTA AL BCE` (segundo piso).
12. **Segmento de crédito**: `fact_saldo_cartera` está al nivel grueso (`segmento_id`, 7
    valores); BCE al fino (`subsegmento_id`, 26 valores) que sube por
    `dim_subsegmento_credito.segmento_id`. La terminología cambió en 2022 (Comercial →
    Productivo, Vivienda → Inmobiliario): el catálogo ya los agrupa.
13. **Geografía**: `dim_canton` (+ `codigo_inec`, 4 dígitos) → `dim_provincia`
    (+ `codigo_inec`, 2 dígitos, `region`). Hay cantones homónimos en provincias distintas
    (Bolívar, Olmedo...): unir siempre por `canton_id`, nunca por nombre.
14. **Fechas**: `fecha_id` = `YYYYMMDD` entero. Mensuales al último día del mes; BCE en la
    fecha de la semana. `dim_fecha` trae `anio`, `mes`, `anio_mes`, `trimestre`,
    `nombre_mes` (español).
15. **Segundo piso** (CONAFIPS, Caja Central FINANCOOP) prestan a otras entidades, no al
    público: excluirlas de comparaciones de mercado salvo que el análisis sea sobre ellas.

## 3. Uniones típicas

```sql
-- saldo de cartera por entidad, provincia y segmento
SELECT d.anio_mes, e.entidad_codigo, e.entidad, e.tipo_entidad,
       p.provincia, sg.segmento, SUM(f.saldo_total) AS cartera,
       SUM(f.saldo_no_devenga_intereses + f.saldo_vencida) AS improductiva
FROM marts.fact_saldo_cartera f
JOIN marts.dim_fecha d            ON d.fecha_id = f.fecha_id
JOIN marts.dim_entidad e          ON e.entidad_id = f.entidad_id
LEFT JOIN marts.dim_canton c      ON c.canton_id = f.canton_id
LEFT JOIN marts.dim_provincia p   ON p.provincia_id = c.provincia_id
JOIN marts.dim_segmento_credito sg ON sg.segmento_id = f.segmento_id
WHERE e.tipo_entidad = 'BANCO PRIVADO'
GROUP BY 1, 2, 3, 4, 5, 6;
```

Más ejemplos en `sql/`. Para validar un número contra la contabilidad,
`marts.vw_conciliacion_saldos_balance` compara saldos por cantón con el balance por entidad
y mes.

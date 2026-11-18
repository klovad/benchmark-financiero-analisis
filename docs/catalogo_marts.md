# Catálogo de `marts` (generado)

Generado por `scripts/catalogo_marts.py` el 2026-10-11. No editar a mano: volver a correr el script. Semántica y advertencias en `docs/guia_modelo.md`; definiciones completas en `docs/referencia_etl/`.

| Objeto | Tipo | Filas (aprox.) | Rango fecha_id |
|---|---|---|---|
| `vw_activo_promedio_ytd` | vista | — |  |
| `vw_cartera_bruta` | vista | — |  |
| `vw_cartera_bruta_segmento` | vista | — |  |
| `vw_cartera_hhi` | vista | — |  |
| `vw_cartera_improductiva` | vista | — |  |
| `vw_cartera_improductiva_segmento` | vista | — |  |
| `vw_cartera_market_share` | vista | — |  |
| `vw_conciliacion_resumen` | vista | — |  |
| `vw_conciliacion_saldos_balance` | vista | — |  |
| `vw_depositos_corto_plazo` | vista | — |  |
| `vw_depositos_hhi` | vista | — |  |
| `vw_depositos_market_share` | vista | — |  |
| `vw_dim_canton_geografia` | vista | — |  |
| `vw_entidad_ruc_colisiones` | vista | — |  |
| `vw_patrimonio_promedio_ytd` | vista | — |  |
| `vw_pyg_total_gastos` | vista | — |  |
| `vw_utilidad_acumulada` | vista | — |  |
| `vw_utilidad_anualizada` | vista | — |  |
| `dim_canton` | tabla | 222 |  |
| `dim_categoria_deposito` | tabla | 0 |  |
| `dim_cuenta_contable` | tabla | 1.736 |  |
| `dim_entidad` | tabla | 442 |  |
| `dim_fecha` | tabla | 1.150 | 20080103 – 20260930 |
| `dim_plazo` | tabla | 0 |  |
| `dim_producto_cartera` | tabla | 0 |  |
| `dim_producto_deposito` | tabla | 0 |  |
| `dim_provincia` | tabla | 26 |  |
| `dim_segmento_credito` | tabla | 0 |  |
| `dim_segmento_entidad` | tabla | 0 |  |
| `dim_subsegmento_credito` | tabla | 26 |  |
| `fact_balance` | tabla | 5.366.488 | 20210131 – 20260930 |
| `fact_captaciones_depositos` | tabla | 3.157.052 | 20080103 – 20260924 |
| `fact_colocaciones_cartera` | tabla | 7.960.877 | 20080103 – 20260924 |
| `fact_pyg` | tabla | 1.226.067 | 20210131 – 20260930 |
| `fact_saldo_cartera` | tabla | 1.081.764 | 20210131 – 20260831 |
| `fact_saldo_depositos` | tabla | 730.171 | 20210131 – 20260831 |
| `fact_tasas_referenciales_cartera` | tabla | 2.583 | 20090731 – 20260930 |
| `fact_tasas_referenciales_depositos_instrumento` | tabla | 1.030 | 20090731 – 20260930 |
| `fact_tasas_referenciales_depositos_plazo` | tabla | 1.236 | 20090731 – 20260930 |
| `fact_tasas_referenciales_sistema` | tabla | 204 | 20090831 – 20260930 |

## Columnas

### `marts.vw_activo_promedio_ytd` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| activo_promedio_ytd | numeric |

### `marts.vw_cartera_bruta` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| cartera_bruta | numeric |

### `marts.vw_cartera_bruta_segmento` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| segmento | text |
| cartera_bruta_segmento | numeric |

### `marts.vw_cartera_hhi` (vista)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| fecha | date |
| hhi | numeric |

### `marts.vw_cartera_improductiva` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| cartera_improductiva | numeric |

### `marts.vw_cartera_improductiva_segmento` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| segmento | text |
| cartera_improductiva | numeric |

### `marts.vw_cartera_market_share` (vista)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| fecha | date |
| entidad | text |
| saldo_entidad | numeric |
| saldo_total_mes | numeric |
| market_share_pct | numeric |

### `marts.vw_conciliacion_resumen` (vista)

Resumen mensual de vw_conciliacion_saldos_balance por tipo de entidad y medida. Ver sql/39 y conciliacion.py.

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| tipo_entidad | text |
| medida | text |
| entidades | bigint |
| mediana_pct | double precision |
| dentro_05pct | numeric |
| dentro_2pct | numeric |
| diferencia_agregada_pct | numeric |

### `marts.vw_conciliacion_saldos_balance` (vista)

Saldos por cantón sumados por entidad × mes vs. cuentas contables (cartera: 14 - 1499; depósitos: 21). Ver sql/39.

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| entidad_id | integer |
| tipo_entidad | text |
| medida | text |
| saldo_reportado | numeric |
| saldo_contable | numeric |
| diferencia_pct | numeric |

### `marts.vw_depositos_corto_plazo` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| depositos_corto_plazo | numeric |

### `marts.vw_depositos_hhi` (vista)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| fecha | date |
| hhi | numeric |

### `marts.vw_depositos_market_share` (vista)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| fecha | date |
| entidad | text |
| saldo_entidad | numeric |
| saldo_total_mes | numeric |
| market_share_pct | numeric |

### `marts.vw_dim_canton_geografia` (vista)

| Columna | Tipo |
|---|---|
| canton_id | integer |
| canton | text |
| provincia_id | integer |
| provincia | text |
| region | text |
| estado_validacion | text |
| es_geografia_conocida | boolean |

### `marts.vw_entidad_ruc_colisiones` (vista)

| Columna | Tipo |
|---|---|
| ruc | text |
| entidad_id | integer |
| entidad_codigo | text |
| entidad | text |
| tipo_entidad | text |

### `marts.vw_patrimonio_promedio_ytd` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| patrimonio_promedio_ytd | numeric |

### `marts.vw_pyg_total_gastos` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| total_gastos | numeric |

### `marts.vw_utilidad_acumulada` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| ingresos | numeric |
| total_gastos | numeric |
| utilidad_acumulada | numeric |

### `marts.vw_utilidad_anualizada` (vista)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| fecha_id | integer |
| mes | integer |
| utilidad_acumulada | numeric |
| utilidad_anualizada | numeric |

### `marts.dim_canton` (tabla)

| Columna | Tipo |
|---|---|
| canton_id | integer |
| canton | text |
| provincia_id | integer |
| estado_validacion | text |
| codigo_inec | character |

### `marts.dim_categoria_deposito` (tabla)

| Columna | Tipo |
|---|---|
| categoria_deposito_id | integer |
| categoria | text |

### `marts.dim_cuenta_contable` (tabla)

| Columna | Tipo |
|---|---|
| cuenta_id | integer |
| reporte | text |
| codigo | text |
| cuenta | text |
| nivel | integer |
| codigo_padre | text |
| seccion | text |
| grupo_met | text |
| estado_validacion | text |

### `marts.dim_entidad` (tabla)

| Columna | Tipo |
|---|---|
| entidad_id | integer |
| entidad | text |
| entidad_codigo | text |
| tipo_entidad | text |
| ruc | text |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |
| segmento_entidad_id | integer |
| estado_validacion | text |

### `marts.dim_fecha` (tabla)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| fecha | date |
| anio | integer |
| mes | integer |
| trimestre | integer |
| nombre_mes | text |
| dia | integer |
| anio_mes | integer |

### `marts.dim_plazo` (tabla)

| Columna | Tipo |
|---|---|
| plazo_id | integer |
| dias_desde | integer |
| dias_hasta | integer |
| plazo_codigo | text |
| estado_validacion | text |

### `marts.dim_producto_cartera` (tabla)

| Columna | Tipo |
|---|---|
| producto_cartera_id | integer |
| tipo_credito | text |
| estado_cartera | text |

### `marts.dim_producto_deposito` (tabla)

| Columna | Tipo |
|---|---|
| producto_deposito_id | integer |
| tipo_deposito | text |

### `marts.dim_provincia` (tabla)

| Columna | Tipo |
|---|---|
| provincia_id | integer |
| provincia | text |
| region | text |
| codigo_inec | character |

### `marts.dim_segmento_credito` (tabla)

| Columna | Tipo |
|---|---|
| segmento_id | integer |
| segmento | text |

### `marts.dim_segmento_entidad` (tabla)

| Columna | Tipo |
|---|---|
| segmento_entidad_id | integer |
| tipo_segmento | text |

### `marts.dim_subsegmento_credito` (tabla)

| Columna | Tipo |
|---|---|
| subsegmento_id | integer |
| subsegmento | text |
| segmento_id | integer |

### `marts.fact_balance` (tabla)

| Columna | Tipo |
|---|---|
| fact_id | bigint |
| fecha_id | integer |
| entidad_id | integer |
| cuenta_id | integer |
| saldo_usd | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |

### `marts.fact_captaciones_depositos` (tabla)

| Columna | Tipo |
|---|---|
| fact_captaciones_depositos_id | bigint |
| fecha_id | integer |
| entidad_id | integer |
| categoria_deposito_id | integer |
| plazo_id | integer |
| monto_total | numeric |
| numero_operaciones | bigint |
| tasa_pasiva_efectiva | numeric |
| tasa_nominal | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |
| segmento_entidad_id | integer |
| canton_id | integer |

### `marts.fact_colocaciones_cartera` (tabla)

| Columna | Tipo |
|---|---|
| fact_colocaciones_cartera_id | bigint |
| fecha_id | integer |
| entidad_id | integer |
| subsegmento_id | integer |
| plazo_id | integer |
| monto_total | numeric |
| numero_operaciones | bigint |
| tasa_activa_efectiva | numeric |
| tasa_nominal | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |
| segmento_entidad_id | integer |
| canton_id | integer |

### `marts.fact_pyg` (tabla)

| Columna | Tipo |
|---|---|
| fact_id | bigint |
| fecha_id | integer |
| entidad_id | integer |
| cuenta_id | integer |
| valor_usd | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |

### `marts.fact_saldo_cartera` (tabla)

| Columna | Tipo |
|---|---|
| fact_saldo_cartera_id | bigint |
| fecha_id | integer |
| entidad_id | integer |
| canton_id | integer |
| segmento_id | integer |
| saldo_por_vencer | numeric |
| saldo_no_devenga_intereses | numeric |
| saldo_vencida | numeric |
| saldo_total | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |

### `marts.fact_saldo_depositos` (tabla)

| Columna | Tipo |
|---|---|
| fact_saldo_depositos_id | bigint |
| fecha_id | integer |
| entidad_id | integer |
| canton_id | integer |
| saldo | numeric |
| numero_clientes | bigint |
| numero_cuentas | bigint |
| categoria_deposito_id | integer |
| plazo_id | integer |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |

### `marts.fact_tasas_referenciales_cartera` (tabla)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| subsegmento_id | integer |
| tasa_activa_maxima | numeric |
| tasa_activa_referencial | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |

### `marts.fact_tasas_referenciales_depositos_instrumento` (tabla)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| categoria_deposito_id | integer |
| tasa_pasiva_promedio | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |

### `marts.fact_tasas_referenciales_depositos_plazo` (tabla)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| plazo_id | integer |
| tasa_pasiva_referencial | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |

### `marts.fact_tasas_referenciales_sistema` (tabla)

| Columna | Tipo |
|---|---|
| fecha_id | integer |
| tasa_pasiva_referencial_sistema | numeric |
| tasa_activa_referencial_sistema | numeric |
| tasa_legal | numeric |
| tasa_maxima_convencional | numeric |
| fecha_carga | timestamp with time zone |
| fecha_actualizacion | timestamp with time zone |

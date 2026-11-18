-- Flujos nuevos BCE por mes × entidad × cantón: depósitos a plazo (tasa pasiva) y
-- colocaciones por segmento de crédito (tasa activa). Base de los modelos de demanda
-- (logit anidado por cantón). Incluye el cantón 'NACIONAL' (regla 5); el modelo lo
-- excluye por nombre porque no es un mercado geográfico.
SELECT d.anio_mes, e.entidad_codigo, e.tipo_entidad, f.canton_id, cn.canton, pr.provincia,
       'DEP_PLAZO' AS producto,
       SUM(f.monto_total) AS monto,
       SUM(f.numero_operaciones) AS operaciones,
       SUM(f.tasa_pasiva_efectiva * f.monto_total) / NULLIF(SUM(f.monto_total), 0) AS tasa,
       SUM(f.monto_total * COALESCE(p.dias_desde, 0)) / NULLIF(SUM(f.monto_total), 0) AS plazo_medio_dias
FROM marts.fact_captaciones_depositos f
JOIN marts.dim_fecha d ON d.fecha_id = f.fecha_id
JOIN marts.dim_entidad e ON e.entidad_id = f.entidad_id
LEFT JOIN marts.dim_plazo p ON p.plazo_id = f.plazo_id
LEFT JOIN marts.dim_canton cn ON cn.canton_id = f.canton_id
LEFT JOIN marts.dim_provincia pr ON pr.provincia_id = cn.provincia_id
WHERE f.categoria_deposito_id = 9 AND f.fecha_id >= :desde AND f.monto_total > 0
GROUP BY 1, 2, 3, 4, 5, 6
UNION ALL
SELECT d.anio_mes, e.entidad_codigo, e.tipo_entidad, f.canton_id, cn.canton, pr.provincia,
       sg.segmento AS producto,
       SUM(f.monto_total), SUM(f.numero_operaciones),
       SUM(f.tasa_activa_efectiva * f.monto_total) / NULLIF(SUM(f.monto_total), 0),
       SUM(f.monto_total * COALESCE(p.dias_desde, 0)) / NULLIF(SUM(f.monto_total), 0)
FROM marts.fact_colocaciones_cartera f
JOIN marts.dim_fecha d ON d.fecha_id = f.fecha_id
JOIN marts.dim_entidad e ON e.entidad_id = f.entidad_id
JOIN marts.dim_subsegmento_credito ss ON ss.subsegmento_id = f.subsegmento_id
JOIN marts.dim_segmento_credito sg ON sg.segmento_id = ss.segmento_id
LEFT JOIN marts.dim_plazo p ON p.plazo_id = f.plazo_id
LEFT JOIN marts.dim_canton cn ON cn.canton_id = f.canton_id
LEFT JOIN marts.dim_provincia pr ON pr.provincia_id = cn.provincia_id
WHERE f.fecha_id >= :desde AND f.monto_total > 0
  AND sg.segmento IN ('PRODUCTIVO', 'CONSUMO', 'MICROCRÉDITO', 'INMOBILIARIO')
GROUP BY 1, 2, 3, 4, 5, 6, 7;

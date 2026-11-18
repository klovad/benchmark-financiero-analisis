-- Cobertura por tabla de hechos y tipo de entidad: primer y último corte, filas.
-- Útil al empezar cualquier análisis para saber hasta dónde llega cada fuente.
SELECT 'fact_saldo_cartera' AS tabla, e.tipo_entidad, min(f.fecha_id) AS desde, max(f.fecha_id) AS hasta, count(*) AS filas
FROM marts.fact_saldo_cartera f JOIN marts.dim_entidad e USING (entidad_id) GROUP BY 1, 2
UNION ALL
SELECT 'fact_saldo_depositos', e.tipo_entidad, min(f.fecha_id), max(f.fecha_id), count(*)
FROM marts.fact_saldo_depositos f JOIN marts.dim_entidad e USING (entidad_id) GROUP BY 1, 2
UNION ALL
SELECT 'fact_colocaciones_cartera', e.tipo_entidad, min(f.fecha_id), max(f.fecha_id), count(*)
FROM marts.fact_colocaciones_cartera f JOIN marts.dim_entidad e USING (entidad_id) GROUP BY 1, 2
UNION ALL
SELECT 'fact_captaciones_depositos', e.tipo_entidad, min(f.fecha_id), max(f.fecha_id), count(*)
FROM marts.fact_captaciones_depositos f JOIN marts.dim_entidad e USING (entidad_id) GROUP BY 1, 2
UNION ALL
SELECT 'fact_balance', e.tipo_entidad, min(f.fecha_id), max(f.fecha_id), count(*)
FROM marts.fact_balance f JOIN marts.dim_entidad e USING (entidad_id) GROUP BY 1, 2
UNION ALL
SELECT 'fact_pyg', e.tipo_entidad, min(f.fecha_id), max(f.fecha_id), count(*)
FROM marts.fact_pyg f JOIN marts.dim_entidad e USING (entidad_id) GROUP BY 1, 2
ORDER BY 1, 2;

-- Colocaciones nuevas (BCE semanal): semana × entidad × segmento de crédito, nacional
-- (incluye cantón NACIONAL, regla 5). Tasa efectiva ponderada por monto (regla 4).
SELECT f.fecha_id, d.fecha, e.entidad_codigo, e.entidad, e.tipo_entidad,
       MAX(se.tipo_segmento) AS segmento_semana,
       sg.segmento,
       SUM(f.monto_total) AS monto,
       SUM(f.numero_operaciones) AS operaciones,
       SUM(f.tasa_activa_efectiva * f.monto_total) / NULLIF(SUM(f.monto_total), 0) AS tasa
FROM marts.fact_colocaciones_cartera f
JOIN marts.dim_fecha d ON d.fecha_id = f.fecha_id
JOIN marts.dim_entidad e ON e.entidad_id = f.entidad_id
JOIN marts.dim_subsegmento_credito ss ON ss.subsegmento_id = f.subsegmento_id
JOIN marts.dim_segmento_credito sg ON sg.segmento_id = ss.segmento_id
LEFT JOIN marts.dim_segmento_entidad se ON se.segmento_entidad_id = f.segmento_entidad_id
WHERE f.fecha_id >= :desde
  AND f.monto_total > 0
GROUP BY f.fecha_id, d.fecha, e.entidad_codigo, e.entidad, e.tipo_entidad, sg.segmento;

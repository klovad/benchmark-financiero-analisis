-- Depósitos a plazo nuevos (BCE semanal): semana × entidad × banda de plazo, nacional
-- (incluye cantón NACIONAL, regla 5). Tasa efectiva ponderada por monto (regla 4).
-- Solo depósitos a plazo: ahorro y monetarios vienen agregados y casi no se mueven.
-- Segmento de la entidad: el de esa semana (regla 11).
SELECT f.fecha_id, d.fecha, e.entidad_codigo, e.entidad, e.tipo_entidad,
       MAX(se.tipo_segmento) AS segmento_semana,
       p.plazo_codigo, p.dias_desde,
       SUM(f.monto_total) AS monto,
       SUM(f.numero_operaciones) AS operaciones,
       SUM(f.tasa_pasiva_efectiva * f.monto_total) / NULLIF(SUM(f.monto_total), 0) AS tasa
FROM marts.fact_captaciones_depositos f
JOIN marts.dim_fecha d ON d.fecha_id = f.fecha_id
JOIN marts.dim_entidad e ON e.entidad_id = f.entidad_id
JOIN marts.dim_plazo p ON p.plazo_id = f.plazo_id
LEFT JOIN marts.dim_segmento_entidad se ON se.segmento_entidad_id = f.segmento_entidad_id
WHERE f.categoria_deposito_id = 9
  AND f.fecha_id >= :desde
  AND f.monto_total > 0
GROUP BY f.fecha_id, d.fecha, e.entidad_codigo, e.entidad, e.tipo_entidad, p.plazo_codigo, p.dias_desde;

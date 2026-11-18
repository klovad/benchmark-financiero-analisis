-- Tasa activa efectiva PONDERADA por monto, por mes, tipo de entidad y segmento de crédito.
-- BCE es semanal y por operación agregada: nunca promediar tasas en forma simple, siempre
-- SUM(tasa * monto) / SUM(monto).
SELECT d.anio_mes,
       e.tipo_entidad,
       sg.segmento,
       SUM(f.monto_total) AS monto,
       SUM(f.numero_operaciones) AS operaciones,
       SUM(f.tasa_activa_efectiva * f.monto_total) / NULLIF(SUM(f.monto_total), 0) AS tasa_efectiva_ponderada
FROM marts.fact_colocaciones_cartera f
JOIN marts.dim_fecha d ON d.fecha_id = f.fecha_id
JOIN marts.dim_entidad e ON e.entidad_id = f.entidad_id
JOIN marts.dim_subsegmento_credito ss ON ss.subsegmento_id = f.subsegmento_id
JOIN marts.dim_segmento_credito sg ON sg.segmento_id = ss.segmento_id
WHERE d.anio >= :desde_anio
GROUP BY d.anio_mes, e.tipo_entidad, sg.segmento
ORDER BY d.anio_mes, e.tipo_entidad, sg.segmento;

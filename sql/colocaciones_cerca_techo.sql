-- Qué parte de las colocaciones nuevas (BCE) se hace a menos de 1 pp de la tasa máxima
-- vigente del subsegmento, por segmento de crédito y tipo de entidad, desde :desde.
-- Si casi todo está pegado al techo, la tasa no es la variable con la que se compite.
WITH c AS (
    SELECT d.anio_mes, sg.segmento, f.subsegmento_id, e.tipo_entidad,
           f.monto_total AS monto, f.tasa_activa_efectiva AS tasa
    FROM marts.fact_colocaciones_cartera f
    JOIN marts.dim_fecha d ON d.fecha_id = f.fecha_id
    JOIN marts.dim_entidad e ON e.entidad_id = f.entidad_id
    JOIN marts.dim_subsegmento_credito ss ON ss.subsegmento_id = f.subsegmento_id
    JOIN marts.dim_segmento_credito sg ON sg.segmento_id = ss.segmento_id
    WHERE f.fecha_id >= :desde AND e.tipo_entidad IN ('BANCO PRIVADO', 'COOPERATIVA')
),
techo AS (
    SELECT d.anio_mes, t.subsegmento_id, t.tasa_activa_maxima
    FROM marts.fact_tasas_referenciales_cartera t
    JOIN marts.dim_fecha d ON d.fecha_id = t.fecha_id
)
SELECT c.segmento, c.tipo_entidad,
       SUM(c.monto) AS monto,
       SUM(c.tasa * c.monto) / SUM(c.monto) AS tasa_ponderada,
       SUM(t.tasa_activa_maxima * c.monto) FILTER (WHERE t.tasa_activa_maxima IS NOT NULL)
           / NULLIF(SUM(c.monto) FILTER (WHERE t.tasa_activa_maxima IS NOT NULL), 0) AS techo_ponderado,
       SUM(c.monto) FILTER (WHERE c.tasa >= t.tasa_activa_maxima - 1) / SUM(c.monto) AS cuota_a_1pp_del_techo,
       SUM(c.monto) FILTER (WHERE t.tasa_activa_maxima IS NOT NULL) / SUM(c.monto) AS cobertura_techo
FROM c
LEFT JOIN techo t ON t.anio_mes = c.anio_mes AND t.subsegmento_id = c.subsegmento_id
GROUP BY 1, 2
ORDER BY 1, 2;

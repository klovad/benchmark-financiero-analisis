-- Tasa máxima (techo regulatorio) por segmento de crédito y mes, ponderada por el monto
-- colocado por todo el sistema en cada subsegmento ese mes (los techos se fijan por
-- subsegmento). Para comparar en el informe la tasa de cada grupo contra su techo.
WITH coloc AS (
    SELECT d.anio_mes, f.subsegmento_id, SUM(f.monto_total) AS monto
    FROM marts.fact_colocaciones_cartera f
    JOIN marts.dim_fecha d ON d.fecha_id = f.fecha_id
    WHERE f.fecha_id >= :desde
    GROUP BY 1, 2
),
techo AS (
    SELECT d.anio_mes, t.subsegmento_id, t.tasa_activa_maxima
    FROM marts.fact_tasas_referenciales_cartera t
    JOIN marts.dim_fecha d ON d.fecha_id = t.fecha_id
    WHERE t.tasa_activa_maxima IS NOT NULL
)
SELECT c.anio_mes, sg.segmento,
       SUM(t.tasa_activa_maxima * c.monto) / NULLIF(SUM(c.monto), 0) AS techo
FROM coloc c
JOIN techo t ON t.anio_mes = c.anio_mes AND t.subsegmento_id = c.subsegmento_id
JOIN marts.dim_subsegmento_credito ss ON ss.subsegmento_id = c.subsegmento_id
JOIN marts.dim_segmento_credito sg ON sg.segmento_id = ss.segmento_id
WHERE sg.segmento IN ('CONSUMO', 'PRODUCTIVO', 'MICROCRÉDITO', 'INMOBILIARIO')
GROUP BY 1, 2
ORDER BY 1, 2;

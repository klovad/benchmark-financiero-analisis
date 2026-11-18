-- Cuota de mercado de cartera DENTRO de un tipo de entidad, por mes.
-- Parámetro :tipo_entidad (p. ej. 'BANCO PRIVADO', 'COOPERATIVA').
--
-- Ojo: marts.vw_cartera_market_share calcula la cuota sobre TODO el sistema (bancos,
-- cooperativas, mutualistas, públicos y segundo piso juntos). Para comparar entre pares
-- usar esta consulta.
WITH por_entidad AS (
    SELECT f.fecha_id, e.entidad_codigo, e.entidad, SUM(f.saldo_total) AS cartera
    FROM marts.fact_saldo_cartera f
    JOIN marts.dim_entidad e ON e.entidad_id = f.entidad_id
    WHERE e.tipo_entidad = :tipo_entidad
    GROUP BY f.fecha_id, e.entidad_codigo, e.entidad
)
SELECT fecha_id, entidad_codigo, entidad, cartera,
       cartera / NULLIF(SUM(cartera) OVER (PARTITION BY fecha_id), 0) AS cuota
FROM por_entidad
ORDER BY fecha_id, cartera DESC;

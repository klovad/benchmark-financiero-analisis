-- Panel mensual entidad × cantón: cartera (por segmento grueso y calidad) y depósitos
-- (vista / plazo / otros, con clientes). Fuente: CAPCOL + SEPS (fact_saldo_*).
-- Excluye segundo piso (regla 15). Mutualistas: cartera incluye la vendida al fideicomiso
-- (regla 6), sirve para cuota por cantón pero no para indicadores de balance.
-- Grupos de depósito: vista = ahorro, cuenta básica, monetarios (con y sin intereses),
-- a la vista (SEPS); plazo = depósitos a plazo; otros = garantía, IFIs, restringidos, por
-- confirmar.
WITH cartera AS (
    SELECT f.fecha_id, f.entidad_id, f.canton_id,
           SUM(f.saldo_total) AS cartera,
           SUM(f.saldo_no_devenga_intereses + f.saldo_vencida) AS cartera_improductiva,
           SUM(f.saldo_total) FILTER (WHERE sg.segmento = 'PRODUCTIVO') AS cartera_productivo,
           SUM(f.saldo_total) FILTER (WHERE sg.segmento = 'CONSUMO') AS cartera_consumo,
           SUM(f.saldo_total) FILTER (WHERE sg.segmento IN ('INMOBILIARIO', 'VIVIENDA DE INTERÉS PÚBLICO')) AS cartera_vivienda,
           SUM(f.saldo_total) FILTER (WHERE sg.segmento = 'MICROCRÉDITO') AS cartera_micro,
           SUM(f.saldo_total) FILTER (WHERE sg.segmento IN ('EDUCATIVO', 'INVERSIÓN PÚBLICA')) AS cartera_otros
    FROM marts.fact_saldo_cartera f
    JOIN marts.dim_segmento_credito sg ON sg.segmento_id = f.segmento_id
    GROUP BY 1, 2, 3
),
depositos AS (
    SELECT f.fecha_id, f.entidad_id, f.canton_id,
           SUM(f.saldo) AS depositos,
           SUM(f.saldo) FILTER (WHERE f.categoria_deposito_id IN (1, 2, 4, 5, 12, 13)) AS dep_vista,
           SUM(f.saldo) FILTER (WHERE f.categoria_deposito_id = 9) AS dep_plazo,
           SUM(f.numero_clientes) AS clientes_dep
    FROM marts.fact_saldo_depositos f
    GROUP BY 1, 2, 3
)
SELECT d.anio_mes, COALESCE(c.fecha_id, p.fecha_id) AS fecha_id,
       e.entidad_codigo, e.entidad, e.tipo_entidad, se.tipo_segmento AS segmento_entidad,
       COALESCE(c.canton_id, p.canton_id) AS canton_id, cn.canton, pr.provincia, pr.region,
       c.cartera, c.cartera_improductiva, c.cartera_productivo, c.cartera_consumo,
       c.cartera_vivienda, c.cartera_micro, c.cartera_otros,
       p.depositos, p.dep_vista, p.dep_plazo, p.clientes_dep
FROM cartera c
FULL JOIN depositos p
       ON p.fecha_id = c.fecha_id AND p.entidad_id = c.entidad_id AND p.canton_id = c.canton_id
JOIN marts.dim_entidad e ON e.entidad_id = COALESCE(c.entidad_id, p.entidad_id)
LEFT JOIN marts.dim_segmento_entidad se ON se.segmento_entidad_id = e.segmento_entidad_id
JOIN marts.dim_fecha d ON d.fecha_id = COALESCE(c.fecha_id, p.fecha_id)
LEFT JOIN marts.dim_canton cn ON cn.canton_id = COALESCE(c.canton_id, p.canton_id)
LEFT JOIN marts.dim_provincia pr ON pr.provincia_id = cn.provincia_id
WHERE e.tipo_entidad <> 'ENTIDAD DE SEGUNDO PISO';

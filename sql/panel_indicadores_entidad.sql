-- Indicadores contables por entidad × mes (bancos privados, cooperativas, mutualistas;
-- la banca pública no tiene balance). Construidos con los bloques del glosario
-- (docs/referencia_etl/glosario_cuentas.md), no con fórmulas propias:
--   morosidad    = vw_cartera_improductiva / vw_cartera_bruta
--   roa          = vw_utilidad_anualizada / vw_activo_promedio_ytd
--   roe          = vw_utilidad_anualizada / vw_patrimonio_promedio_ytd
--   liquidez     = fondos disponibles (11) / vw_depositos_corto_plazo
--   intermediacion = cartera bruta / depósitos (21)
-- PyG es acumulado del año: gasto operativo (45) e intereses causados (41) se anualizan
-- con 12/mes y se dividen por el activo promedio YTD.
-- Mutualistas: cartera bruta de balance no incluye la vendida al fideicomiso (regla 6).
WITH bal AS (
    SELECT f.entidad_id, f.fecha_id,
           SUM(f.saldo_usd) FILTER (WHERE cc.codigo = '1')  AS activo,
           SUM(f.saldo_usd) FILTER (WHERE cc.codigo = '11') AS fondos_disponibles,
           SUM(f.saldo_usd) FILTER (WHERE cc.codigo = '13') AS inversiones,
           SUM(f.saldo_usd) FILTER (WHERE cc.codigo = '2')  AS pasivo,
           SUM(f.saldo_usd) FILTER (WHERE cc.codigo = '21') AS depositos,
           SUM(f.saldo_usd) FILTER (WHERE cc.codigo = '26') AS obligaciones_financieras,
           SUM(f.saldo_usd) FILTER (WHERE cc.codigo = '3')  AS patrimonio
    FROM marts.fact_balance f
    JOIN marts.dim_cuenta_contable cc ON cc.cuenta_id = f.cuenta_id
    WHERE cc.reporte = 'BALANCE' AND cc.codigo IN ('1', '11', '13', '2', '21', '26', '3')
    GROUP BY 1, 2
),
pyg AS (
    SELECT f.entidad_id, f.fecha_id,
           SUM(f.valor_usd) FILTER (WHERE cc.codigo = '41') AS intereses_causados_ytd,
           SUM(f.valor_usd) FILTER (WHERE cc.codigo = '45') AS gastos_operacion_ytd,
           SUM(f.valor_usd) FILTER (WHERE cc.codigo = '51') AS intereses_ganados_ytd
    FROM marts.fact_pyg f
    JOIN marts.dim_cuenta_contable cc ON cc.cuenta_id = f.cuenta_id
    WHERE cc.codigo IN ('41', '45', '51')
    GROUP BY 1, 2
)
SELECT d.anio_mes, b.fecha_id, e.entidad_codigo, e.entidad, e.tipo_entidad,
       se.tipo_segmento AS segmento_entidad,
       b.activo, b.fondos_disponibles, b.inversiones, b.pasivo, b.depositos,
       b.obligaciones_financieras, b.patrimonio,
       cb.cartera_bruta, ci.cartera_improductiva, dcp.depositos_corto_plazo,
       ua.utilidad_anualizada, ap.activo_promedio_ytd, pp.patrimonio_promedio_ytd,
       ci.cartera_improductiva / NULLIF(cb.cartera_bruta, 0) AS morosidad,
       ua.utilidad_anualizada / NULLIF(ap.activo_promedio_ytd, 0) AS roa,
       ua.utilidad_anualizada / NULLIF(pp.patrimonio_promedio_ytd, 0) AS roe,
       b.fondos_disponibles / NULLIF(dcp.depositos_corto_plazo, 0) AS liquidez,
       cb.cartera_bruta / NULLIF(b.depositos, 0) AS intermediacion,
       b.patrimonio / NULLIF(b.activo, 0) AS patrimonio_activo,
       (py.gastos_operacion_ytd * 12.0 / d.mes) / NULLIF(ap.activo_promedio_ytd, 0) AS gasto_operativo_activo,
       (py.intereses_causados_ytd * 12.0 / d.mes) / NULLIF(b.pasivo, 0) AS costo_fondeo,
       (py.intereses_ganados_ytd * 12.0 / d.mes) / NULLIF(ap.activo_promedio_ytd, 0) AS rendimiento_activo
FROM bal b
JOIN marts.dim_entidad e ON e.entidad_id = b.entidad_id
LEFT JOIN marts.dim_segmento_entidad se ON se.segmento_entidad_id = e.segmento_entidad_id
JOIN marts.dim_fecha d ON d.fecha_id = b.fecha_id
LEFT JOIN pyg py ON py.entidad_id = b.entidad_id AND py.fecha_id = b.fecha_id
LEFT JOIN marts.vw_cartera_bruta cb ON cb.entidad_id = b.entidad_id AND cb.fecha_id = b.fecha_id
LEFT JOIN marts.vw_cartera_improductiva ci ON ci.entidad_id = b.entidad_id AND ci.fecha_id = b.fecha_id
LEFT JOIN marts.vw_depositos_corto_plazo dcp ON dcp.entidad_id = b.entidad_id AND dcp.fecha_id = b.fecha_id
LEFT JOIN marts.vw_utilidad_anualizada ua ON ua.entidad_id = b.entidad_id AND ua.fecha_id = b.fecha_id
LEFT JOIN marts.vw_activo_promedio_ytd ap ON ap.entidad_id = b.entidad_id AND ap.fecha_id = b.fecha_id
LEFT JOIN marts.vw_patrimonio_promedio_ytd pp ON pp.entidad_id = b.entidad_id AND pp.fecha_id = b.fecha_id
WHERE e.tipo_entidad IN ('BANCO PRIVADO', 'COOPERATIVA', 'MUTUALISTA');

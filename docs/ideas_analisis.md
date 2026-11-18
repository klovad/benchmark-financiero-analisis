# Ideas de análisis

Preguntas que el modelo ya permite responder, ordenadas de más directa a más elaborada.
Marcar con fecha y enlace al notebook cuando se haga una.

## Mercado y competencia
- **Cuota de mercado y concentración (HHI)** de cartera y depósitos por tipo de entidad,
  segmento de crédito, provincia y cantón; evolución 2021-2026. Ojo: las vistas `vw_*_hhi`
  son sobre todo el sistema; entre pares, calcular filtrando por `tipo_entidad`.
- **Avance de las cooperativas frente a los bancos** por cantón: dónde ganan participación.
  *Hecho 2026-10-11: `docs/analisis_mercado.md` (informe de mercado, sección 07).*
- **Mapa de oportunidades**: cantones con mucha captación y poca colocación (relación
  cartera/depósitos), o con crecimiento alto y pocos competidores. *Hecho 2026-10-11
  (clusters de cantones y brecha de penetración por entidad, `mercado.py`).* Pendiente:
  mapa coroplético por cantón y demanda potencial con población INEC.

## Benchmark entre pares
- Una entidad contra su grupo (banco grande/mediano/pequeño, cooperativa de su segmento):
  crecimiento de cartera y depósitos, morosidad por segmento, mezcla de productos.
- Indicadores financieros (ROA, ROE, eficiencia, liquidez, morosidad) desde
  `fact_balance`/`fact_pyg` con las fórmulas de `referencia_etl/metricas_financieras.md`.
- Rankings mensuales y su estabilidad.
- *Hecho 2026-10-11*: segmentación por modelo de negocio y pares por distancia
  (`segmentacion.py`), comparación de una entidad con sus pares en el plan de acción.

## Tasas
- Tasa efectiva ponderada por entidad y segmento (BCE semanal) contra la referencial y la
  máxima vigente (`fact_tasas_referenciales_cartera`): quién presta cerca del techo.
- Diferencial activa-pasiva por tipo de entidad.
- Serie larga 2008-2026: ciclos de tasas y cambios normativos (segmentación 2022).
- *Hecho 2026-10-11 (`docs/analisis_mercado.md`)*: tasas comparables por plazo, ciclo
  2022-2025, liderazgo y anticipación de movimientos, elasticidades por cantón, sustitución
  bancos ↔ cooperativas, techos en crédito.
- Pendiente: elasticidades de depósitos de ahorro/vista (el BCE no los trae por cantón);
  pass-through de tasas de EE. UU. a tasas locales (requiere serie externa).

## Riesgo
- Morosidad (`saldo_no_devenga_intereses + saldo_vencida`) por segmento, provincia y tipo
  de entidad; deterioro reciente.
- Concentración geográfica de la cartera de cada entidad.

## Calidad / validación
- Antes de publicar un número agregado, cruzarlo con `vw_conciliacion_resumen` del mismo
  mes y tipo de entidad.

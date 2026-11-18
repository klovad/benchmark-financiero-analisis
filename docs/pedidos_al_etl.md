# Pedidos al ETL

Lo que un análisis necesita y que debe agregarse al modelo en `benchmark-bancos` (como
migración `sql/NN`), no resolverse acá. Cada pedido: fecha, qué, para qué análisis y
estado. Al implementarlo en el ETL, marcarlo hecho y volver a generar
`docs/catalogo_marts.md`.

| Fecha | Pedido | Para qué | Estado |
|---|---|---|---|
| 2026-10-11 | Series externas mensuales: tasa de fondos federales y Treasury 1 año (FRED), riesgo país EMBI Ecuador, reservas/encaje del sistema en el BCE | Anticipar movimientos de tasas (`liderazgo.py`) y separar el ciclo de liquidez de la respuesta del depositante (`sustitucion.py`). Hoy el modelo solo ve tasas y flujos internos | Pendiente (requiere descarga: confirmar fuentes y tamaño) |
| 2026-10-11 | Población y empleo/ventas por cantón (INEC: proyecciones de población, Directorio de Empresas), unibles por `dim_canton.codigo_inec` | Pasar de "brecha frente a sí mismo" a demanda potencial por cantón (`mercado.py`); normalizar depósitos por habitante | Pendiente (requiere descarga) |
| 2026-10-11 | Vista `marts.vw_tasa_captacion_plazo_ajustada` (entidad × semana, tasa a mezcla de plazo constante) | La usan liderazgo, sustitución y el plan de acción; hoy se calcula en `tasas.py`. Solo si otro consumidor (Power BI) la necesita | Opcional |

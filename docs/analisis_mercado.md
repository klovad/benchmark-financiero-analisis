# Análisis de mercado: captaciones, colocaciones, tasas y plan de acción

Estado: 2026-11-13 (refresco; primera versión 2026-10-11). Saldos por cantón y balances
(bancos, cooperativas y mutualistas) hasta 2026-09, tasas BCE hasta la semana del
2026-10-29. Las cifras cambiaron poco frente a la versión de octubre: los resultados son
estables con un mes más de datos.

```powershell
uv run python scripts/analisis_mercado.py                # modelos -> salidas/mercado/*.csv + resultados.json (~2-3 min)
uv run python scripts/informe_mercado.py                 # informe HTML autocontenido
uv run python scripts/analisis_mercado.py --refrescar    # después de una carga del ETL (lunes; ~5 min)
uv run python scripts/analisis_mercado.py --entidad PICHINCHA   # plan de acción para otra entidad
```

Salida principal: `salidas/mercado/informe_mercado.html` (no versionado; se regenera). Es
un explorador autocontenido (~3 MB, sin librerías externas) organizado en capítulos, cada uno
con la pregunta, la respuesta corta con cifras y filtros para explorar:

| Capítulo | Qué se puede explorar |
|---|---|
| 01 Saldos y cuotas | Medida (depósitos, plazo, vista, cartera, mora), monto / participación / crecimiento, región y provincia; comparar hasta 6 entidades; ranking ordenable |
| 02 Tasas | Producto (depósitos a plazo o un segmento de crédito con su techo), período, entidades y grupos; línea de tiempo del ciclo 2022-2025 |
| 03 Bancos ↔ cooperativas | Calculadora: diferencial elegido → cuota de cooperativas en flujos y saldos y USD que migran; dispersión por etapa |
| 04 Liderazgo | Entidad: a quién arrastra y a quién sigue, matriz resaltada, índice y velocidad de ajuste |
| 05 Anticipar | Banco y señal: probabilidad fuera de muestra semana a semana contra los movimientos reales; probabilidades actuales; aporte del balance |
| 06 Elasticidades | α por entidad, calculadora de mora (pp → % de cuota, pp de tasa equivalentes, USD), modelos por producto, disciplina de mercado, techos |
| 07 Simulador | Entidad, cambio de tasa (−1,00 a +1,00 pp), alcance (país, cantones con brecha, región, provincia) y re-precio sí/no → flujo, saldo, costo y costo marginal; tendencia del saldo a plazo (36 meses de historia + proyección a 12/24/36 meses sin y con el cambio, respuesta inmediata o gradual con la vida media del capítulo 03); rivales y cantones |
| 08 Cantones | Ejes de la dispersión, región, provincia, tamaño, tipos de mercado; oportunidades de cualquier banco grande |
| 09 Modelos de negocio | Ejes, tipos, entidad destacada; trayectoria de mora, liquidez, solvencia, ROA, ROE o costo de fondeo con la mediana de su grupo |
| 10-12 | Plan de acción con enlaces a cada capítulo, método y glosario buscable |

Los datos granulares que usan los filtros (series por provincia y entidad, tasas activas,
predicciones fuera de muestra, insumos del simulador, oportunidades por banco,
trayectorias) los arma `src/benchmark_analisis/explorador.py`. El simulador aplica el logit
simple en forma cerrada en el navegador con el promedio de 6 meses por cantón; sus cifras
pueden diferir levemente del plan de acción, que simula mes a mes.
Términos, unidades y cómo leer cada indicador: `docs/glosario_analisis.md` (también
en el capítulo 12 del informe; se edita solo en el markdown).

## Preguntas y modelo que responde cada una

| Pregunta | Modelo | Código | Datos |
|---|---|---|---|
| ¿Cómo se mueven los saldos? | Descriptivo: saldos y cuotas por tipo de entidad y banco | `scripts/analisis_mercado.py` §2 | CAPCOL + SEPS, 2021-01 → 2026-09 |
| ¿Cómo comparar tasas entre entidades? | Índice hedónico: tasa = efecto entidad×semana + efecto banda de plazo (ponderado por monto) | `tasas.py` | BCE captaciones a plazo semanales, 2015 → |
| ¿Qué tan sensibles son los depósitos de los bancos a las cooperativas? | (a) logit de la cuota coop en flujos vs. diferencial, Newey-West; (b) corrección de error de la cuota en saldos | `sustitucion.py` | BCE semanal 2015 →; saldos 2021 → |
| ¿Cómo fluye el dinero cuando un banco mueve su tasa? | Logit / logit anidado (Berry, 1994) por cantón×mes con efectos fijos entidad×cantón y mercado; tasa instrumentada (Hausman / BLP); simulación con flujo total fijo | `demanda.py` | BCE flujos por cantón, 2021-01 → 2026-10 |
| ¿Quién lidera y quién sigue? | Fechas del ciclo, matriz de respuesta por eventos, corrección de error hacia la tasa de los pares | `liderazgo.py` | serie hedónica semanal |
| ¿Cómo anticipar a un competidor? | Logística (sube/baja ≥ 0,15 pp en 4 semanas), validación con ventana expansiva por año | `liderazgo.py` | ídem |
| ¿En qué ciudades hay oportunidad? | Indicadores por cantón + K-means; brecha de penetración de la entidad frente a su percentil 75 en cantones del mismo cluster y región | `mercado.py` | saldos por cantón |
| ¿Castiga el depositante la mora? ¿Anticipa el balance los movimientos de tasa? | Mora, liquidez y solvencia por entidad, rezagadas 1 mes (robustez: 3) como controles en el logit por cantón; segunda etapa sobre el modelo de anticipación | `balance.py`, `demanda.agregar_balance`, `liderazgo.comparar_con_balance` | Boletín + EEFF SEPS, 2021 → |
| ¿Con quién compararse? | Ward + K-means sobre estructura de balance (modelo de negocio); pares por distancia | `segmentacion.py` | balance + saldos |
| ¿Qué hace Banco Guayaquil? | Plan de acción: pares, brechas por cantón, simulación de tasa con costo marginal, vigilancia de competidores | `scripts/analisis_mercado.py::plan_accion` | todo lo anterior |

## Resultados principales

1. **Sustitución bancos ↔ cooperativas.** Por cada 1 pp de diferencial (coop S1 − bancos,
   a mezcla de plazo constante) la cuota de las cooperativas en las captaciones nuevas a
   plazo sube ≈ 3,3 pp (139 meses, 2015-2026, e.e. HAC). En saldos el ajuste tiene vida
   media ≈ 11 meses y el efecto de largo plazo es ≈ 2,9 pp de cuota, ≈ USD 1.300 M sobre
   un mercado a plazo de USD 44.800 M (bancos + cooperativas, 2026-09). Diferencial actual:
   ≈ 0,8 pp (oct 2026), más angosto que el ≈ 1,0 pp de septiembre.
2. **Ciclo de tasas.** La tasa a plazo de los bancos grandes pasó de 3,8 % (ene 2022) a
   8,6 % (may 2024) y 4,4 % (oct 2026); las cooperativas S1, de 7,3 % a 8,0 % y 5,2 %. En
   el pico el diferencial fue negativo y las cooperativas perdieron cuota en flujos.
   **Octubre 2026: posible giro al alza.** Pichincha subió primero (de 4,14 % a 4,49 %,
   media de 4 semanas, +0,35 pp), Pacífico lo siguió (+0,30 pp) y Produbanco en menor
   medida (+0,15 pp), justo el patrón líder-seguidor del punto 3.
3. **Liderazgo.** Pichincha y Guayaquil son los más seguidos: cuando mueven primero,
   los demás bancos grandes los siguen en 0-2 meses en ≈ 2/3 de los casos (Guayaquil →
   Bolivariano 86 %). Bolivariano e Internacional mueven seguido pero se les sigue menos.
   Las cooperativas S1 no ajustan a la tasa bancaria en el corto plazo (α ≈ 0).
   Guayaquil cierra la mitad de una brecha con sus pares en ≈ 1 mes; Pichincha en ≈ 2,4.
4. **Anticipación.** AUC fuera de muestra 0,76 (subidas) y 0,71 (bajadas). Un banco sube
   cuando el mercado viene subiendo y él quedó por debajo, más si Pichincha acaba de
   moverse; baja cuando está por encima del mercado y en niveles altos. Con datos al
   2026-10-29 la señal se invirtió frente a septiembre: probabilidad de subida 21-29 % en
   Guayaquil, Produbanco, Bolivariano, Internacional, Austro y Diners (frecuencia histórica
   23 %), y de bajada ≤ 17 % en todos.
5. **Elasticidades.** Depósitos a plazo: semi-elasticidad 0,077-0,098 por pp (MCO, VI
   logit simple y anidado; F de primera etapa > 100) → elasticidad ≈ 0,4-0,5, demanda
   inelástica. σ (anidamiento bancos/cooperativas) ≈ 0: en el margen el cliente compara
   ambos. Más sensibles: clientes de Pichincha y Produbanco; menos: Bolivariano. Crédito:
   la tasa no explica la cuota (coeficientes no significativos); 76 % del consumo bancario
   y 78 % del microcrédito bancario se colocan a ≤ 1 pp del techo (2025-2026).
6. **Banco Guayaquil.** +0,25 pp nacional ≈ +USD 15 M/mes de captación (77 % de otros
   bancos, 19 % de cooperativas) pero re-precia USD 3.500 M: costo marginal del fondeo
   nuevo ≈ 17 % anual. Incluso focalizado en 10 cantones con brecha, ≈ 16 %. Conclusión:
   pagar premio solo por dinero nuevo. Brechas de penetración: Machala, Portoviejo, Manta,
   Pasaje (Costa: 3-9 % de cuota vs. ≈ 19 % en plazas costeñas parecidas), luego Ambato,
   Loja, Latacunga, Ibarra. Potencial ≈ USD 1.170 M en depósitos y 1.110 M en cartera.
7. **Balance: mora, liquidez y solvencia** (2021-2026, 207 entidades con balance).
   - *Disciplina de mercado*: con la tasa controlada, 1 pp más de mora le quita a un banco
     ≈ 3,8 % de su cuota en captaciones nuevas a plazo (−4,8 % con rezago de 3 meses);
     equivale a ≈ 0,45 pp de tasa. Cooperativas: −1,2 % (p < 0,10); mutualistas: −9,5 %. La
     liquidez no tiene efecto (el depositante no la ve). La solvencia (patrimonio/activo)
     sale negativa por mecánica contable, no se interpreta. La semi-elasticidad a la tasa
     no cambia (0,088 → 0,085): el resultado de elasticidades es robusto.
   - *Anticipación*: agregar el balance sube la AUC media 2023-2026 de 0,671 a 0,694
     (subidas; IC 90 % de la diferencia −0,001 a 0,048) y de 0,682 a 0,693 (bajadas; −0,010
     a 0,031): mejora pequeña, no concluyente. Señal más clara: un banco cuya liquidez cayó
     en 3 meses tiende a subir su tasa; uno más líquido o mejor capitalizado que sus pares,
     a bajarla. Las predicciones del informe siguen usando el modelo base (más historia).
8. **Clusters.** Cantones: continuo (silueta ≈ 0,25), 5 segmentos prácticos. Entidades: 4
   modelos de negocio (silueta 0,37): banca universal (14 bancos), minorista
   consumo/micro (42 cooperativas S1 + 3 bancos + 1 mutualista), consumo de alto margen
   (Diners, Solidario, VisionFund), mutualistas de vivienda. Con el corte de septiembre
   5 grupos tuvieron casi la misma silueta (0,372 vs. 0,368): se elige el menor k a ≤ 0,01
   del máximo para que los grupos no cambien de un mes a otro. Pares de Guayaquil: Produbanco,
   Pichincha, Bolivariano, Pacífico, Internacional.

## Decisiones de método

- **Tasas comparables**: sin el ajuste por plazo, una entidad que capta más a 360 días
  "sube" su tasa sin cambiar precios. La prima de plazo se estima por tipo de entidad.
- **Mercado = cantón × mes, cuotas internas**: el efecto fijo de mercado absorbe el
  tamaño y la opción externa; se modela quién se lleva el flujo, no si el flujo crece.
- **Instrumentos**: tasa de la misma entidad en otras provincias (Hausman, 1996; Nevo,
  2001) y tasas/número de rivales (Berry, 1994; BLP, 1995). Con efectos fijos solo de
  entidad el instrumento no identificaba (α ≈ 0); con entidad×cantón sí y es estable.
- **Flujos BCE incluyen renovaciones**: la elasticidad de clientes nuevos es
  probablemente mayor que la estimada. Es una cota inferior para captar dinero nuevo.
- **Costo marginal del fondeo**: saldo adicional ≈ flujo adicional × plazo medio; costo =
  subida × saldo actual (al renovarse) + tasa nueva × saldo adicional (Monti-Klein).
- **Oportunidad por cantón**: brecha contra el desempeño de la propia entidad en
  mercados parecidos de la misma región (una marca costeña no rinde igual en la Sierra).
  No usa población ni actividad económica (no están en `marts`).
- **Balance rezagado**: el balance del mes m se usa desde m + 1 (publicación); se
  recorta al percentil 1-99 por tipo de entidad. Para anticipar se usan desvío frente a la
  mediana de los bancos y cambio a 3 meses (los niveles son casi colineales con el desvío).
  La comparación de AUC es en dos etapas porque el balance empieza en 2021 y el modelo
  base aprende desde 2016: entrenar ambos desde 2021 castigaba al base.
- **Liderazgo**: es precedencia temporal, no causalidad. Granger semanal se probó y fue
  ruidoso por composición; se prefirió la matriz por eventos mensuales y el ECM.

## Límites y siguientes pasos

- Variables externas que mejorarían la anticipación y la sustitución: tasa de los fondos
  federales / Treasuries, riesgo país (EMBI), liquidez del sistema (encaje, reservas en
  el BCE). Ver `docs/pedidos_al_etl.md`.
- Población y actividad por cantón (INEC) para pasar de "brecha frente a sí mismo" a
  "demanda potencial".
- Depósitos a la vista: el BCE los trae agregados a nivel nacional y casi sin variación
  de tasa; no se modelaron.
- Repetir la estimación de demanda por segmento de cooperativa (S1 vs. S2-S3) y por
  monto (minorista vs. institucional) cuando el BCE lo permita.

## Referencias

Adams, Brevoort y Kiser (2007), *J. Industrial Economics* 55(1) · Amel y Rhoades (1988),
*REStat* 70(4) · Berry (1994), *RAND J. Economics* 25(2) · Berry, Levinsohn y Pakes
(1995), *Econometrica* 63(4) · De Graeve, De Jonghe y Vander Vennet (2007), *J. Banking &
Finance* 31(1) · Dick (2008), *J. Banking & Finance* 32(8) · Drechsler, Savov y Schnabl
(2017), *QJE* 132(4) · Egan, Hortaçsu y Matvos (2017), *AER* 107(1) · Gambacorta (2008),
*European Economic Review* 52(5) · Hannan (2003), Federal Reserve FEDS 2003-06 · Hannan
y Berger (1991), *AER* 81(4) · Klein (1971), *JMCB* 3(2) · Maimbo y Henriquez Gallegos
(2014), World Bank WP 7070 · Martínez Pería y Schmukler (2001), *J. Finance* 56(3) ·
Nevo (2001), *Econometrica* 69(2) · Nguyen (2019), *AEJ: Applied* 11(1) · Roengpitya,
Tarashev y Tsatsaronis (2014), *BIS Quarterly Review*, diciembre.

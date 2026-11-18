# Glosario y guía de lectura del análisis de mercado

Qué significa cada término, unidad e indicador del informe de mercado
(`salidas/mercado/informe_mercado.html`, método en `docs/analisis_mercado.md`) y cómo se
lee. Este archivo es la **fuente única**: `scripts/informe_mercado.py` lo lee y lo muestra
en la sección "Glosario" del HTML. Para agregar o corregir un término, editar acá y
regenerar el informe.

Formato: cada `##` es un grupo; cada fila de tabla, un término. Columnas: término, qué es,
cómo se lee.

## Unidades

| Término | Qué es | Cómo se lee |
|---|---|---|
| pp (puntos porcentuales) | Diferencia aritmética entre dos porcentajes. | Si una tasa pasa de 4,50 % a 4,75 %, subió 0,25 pp (no "0,25 %", que sería un cambio relativo). Todos los cambios de tasa, cuotas y diferenciales del informe se expresan en pp. |
| % (cambio relativo) | Cambio en proporción al valor inicial. | "La cuota sube 9 %" con cuota inicial 10 % significa que pasa a ≈ 10,9 %, no a 19 %. |
| USD M / USD mil M | Millones y miles de millones de dólares. | USD 1,2 mil M = USD 1.200 millones. |
| Tasa efectiva anual | Tasa que incluye capitalización y cargos, anualizada; es la que reporta el BCE. | Todas las tasas del informe son efectivas anuales en porcentaje. |
| Crecimiento anual compuesto | Tasa constante que lleva del valor inicial al final: (final / inicial)^(1/años) − 1. | "10,6 % anual en 3 años" = el saldo creció como si aumentara 10,6 % cada año. |

## Fuentes y conceptos de datos

| Término | Qué es | Cómo se lee |
|---|---|---|
| CAPCOL | Reporte de Superbancos de saldos de cartera y captaciones por entidad, cantón y producto (bancos privados, públicos, mutualistas). | Base de los saldos por cantón de bancos. Concilia con el balance dentro de ±1-2 %. |
| SEPS | Superintendencia de Economía Popular y Solidaria: saldos por cantón y estados financieros de cooperativas (segmentos 1-3) y mutualistas. | Base de los saldos y balances de cooperativas. |
| BCE semanal | Reporte del Banco Central con el monto, número de operaciones y tasa efectiva de los créditos y depósitos a plazo **nuevos** de cada semana, por entidad y cantón. | Es la fuente de tasas y de flujos. Incluye renovaciones de depósitos. |
| Boletín / EEFF | Balance y estado de resultados mensuales (Superbancos para bancos; SEPS para cooperativas y mutualistas). | Fuente de mora, liquidez, solvencia, ROA. La banca pública no tiene balance en el data mart. |
| Saldo | Lo que hay a fin de mes (stock). | "Depósitos de USD 63 mil M" = dinero depositado a esa fecha. Se mueve lento. |
| Flujo / captaciones nuevas | Lo que entra en el período (operaciones nuevas y renovaciones). | Reacciona rápido a las tasas: primero se mueve el flujo y después, con meses de rezago, el saldo. |
| Depósitos (total) | Todas las categorías de depósito del público en CAPCOL / SEPS. | Incluye a la vista, a plazo y otros (restringidos, de instituciones financieras, garantía). |
| Depósitos a la vista | Ahorro, cuenta básica, monetarios (corrientes) con y sin intereses. | Dinero disponible en cualquier momento; casi no reacciona a la tasa. |
| Depósitos a plazo | Depósitos a plazo fijo (certificados) con vencimiento pactado. | El producto donde se compite en tasa; es el que modelamos. |
| Cartera bruta | Préstamos totales antes de restar provisiones (cuenta 14 − 1499 en balance; saldo total en CAPCOL). | Tamaño del negocio de crédito. |
| Cartera improductiva | Cartera que no devenga intereses más cartera vencida. | Numerador de la morosidad. |
| Cantón NACIONAL | Operaciones que el BCE no asigna a un cantón. | Cuentan en los totales nacionales pero se excluyen de los modelos por cantón. |
| Segmento de cooperativa (S1-S5) | Clasificación SEPS por tamaño de activos; S1 son las más grandes. | "Coop. S1" = cooperativas grandes, rival directo de los bancos en plazo. |
| Banco grande / mediano / pequeño | Clasificación de Superbancos por tamaño. | "Bancos grandes" en el informe = Pichincha, Guayaquil, Pacífico, Produbanco, Bolivariano e Internacional. |
| Techo regulatorio (tasa máxima) | Tasa activa máxima que fija el BCE por segmento de crédito. | Si casi todo el crédito se coloca cerca del techo, la tasa no sirve para competir. |
| Rezago | Desfase entre el período del dato y cuándo se usa. | "Balance rezagado 1 mes": en octubre se usa el balance de septiembre, que es lo que se conocía. |

## Indicadores de mercado

| Término | Qué es | Cómo se lee |
|---|---|---|
| Cuota de mercado | Saldo (o flujo) de una entidad / total del grupo comparado. | Siempre dice contra qué: "cuota entre bancos privados" no es lo mismo que "cuota del sistema". |
| HHI (índice de Herfindahl-Hirschman) | Suma de las cuotas al cuadrado × 10.000. | < 1.500 mercado competitivo; 1.500-2.500 moderadamente concentrado; > 2.500 concentrado. 10.000 = monopolio. |
| Cartera / depósitos | Crédito otorgado en el cantón / depósitos captados en él. | < 1: el ahorro local se presta en otro lado (posible demanda de crédito desatendida). > 1: se presta más de lo que se capta localmente. |
| Tasa a mezcla de plazo constante | Tasa de depósitos a plazo corregida por la composición de plazos (ajuste hedónico). | Permite comparar entidades y semanas: una entidad no "sube" su tasa solo porque esa semana captó más a 360 días. |
| Diferencial coop − banco (spread) | Tasa a plazo de cooperativas S1 menos la de los bancos, ambas a mezcla constante. | Positivo: las cooperativas pagan más (lo normal). Cuanto mayor, más dinero migra a cooperativas. |
| Avance de cooperativas (pp) | Cambio de la cuota de cooperativas en depósitos del cantón en 36 meses. | Positivo: las cooperativas ganan terreno a los bancos en ese cantón. |

## Indicadores de balance

| Término | Qué es | Cómo se lee |
|---|---|---|
| Morosidad (mora) | Cartera improductiva / cartera bruta. | Más baja es mejor. Bancos grandes ≈ 1-4 %; cooperativas S1 ≈ 5-8 %. |
| Liquidez | Fondos disponibles / depósitos de corto plazo. | Más alta = más colchón para retiros. Si cae rápido, el banco tiene incentivo a subir su tasa para captar. |
| Solvencia | Patrimonio / activo (aproximación; el índice regulatorio usa activos ponderados por riesgo). | Más alta = más capital propio por cada dólar de activo. |
| ROA | Utilidad anualizada / activo promedio del año. | Rentabilidad sobre activos; ≈ 1-2 % es bueno en banca. |
| ROE | Utilidad anualizada / patrimonio promedio del año. | Rentabilidad para el accionista; ≈ 12-20 % en bancos grandes. |
| Costo de fondeo | Intereses pagados anualizados / pasivo. | Cuánto le cuesta cada dólar de fondeo. Más bajo = ventaja competitiva. |
| Gasto operativo / activo | Gastos de operación anualizados / activo promedio. | Eficiencia: más bajo es más eficiente. |
| Rendimiento del activo | Intereses ganados anualizados / activo promedio. | Cuánto rinde el activo; alto en entidades de consumo y microcrédito. |
| Crecimiento 12 m | Variación de cartera o depósitos en los últimos 12 meses. | Compara la velocidad de expansión frente a pares. |
| Frente a pares (rel_) | Valor de la entidad menos la mediana de su tipo de entidad ese mes. | Positivo: está por encima de la mediana (más líquida, más mora, etc.). |
| Cambio 3 m (d3_) | Variación del indicador en los últimos 3 meses. | Capta tendencias recientes (p. ej. liquidez que se deteriora). |

## Modelos y estadística

| Término | Qué es | Cómo se lee |
|---|---|---|
| Logit de demanda (Berry, 1994) | Modelo que explica la cuota de cada entidad en un cantón y mes según su tasa y otras características. | Permite medir cuánto cambia la cuota cuando una entidad mueve su tasa y de quién sale el dinero. |
| Semi-elasticidad α | Cambio en el logaritmo de la cuota por 1 pp de tasa. | α = 0,09: si una entidad con cuota pequeña sube su tasa 1 pp, su cuota sube ≈ 9 % (de 10 % a ≈ 10,9 %). En depósitos α > 0; en crédito se espera α < 0. |
| Elasticidad | Cambio porcentual de la cuota por cambio porcentual de la tasa ≈ α × tasa × (1 − cuota). | < 1: demanda inelástica (subir la tasa atrae poco). Depósitos a plazo ≈ 0,4-0,5. |
| σ (parámetro de nido) | En el logit anidado, cuánto más se sustituye dentro del grupo (bancos o cooperativas) que entre grupos. | σ ≈ 0: el cliente compara bancos y cooperativas por igual. σ cerca de 1: son mercados separados. |
| Variables instrumentales (VI) | Técnica que usa una variable externa (la tasa de la misma entidad en otras provincias) para aislar el efecto de la tasa de los shocks locales. | Corrige el sesgo de que las entidades suben tasa justo donde pierden depósitos. |
| F de primera etapa | Fuerza del instrumento. | > 10 es aceptable; > 100, muy fuerte. |
| e.e. (error estándar) | Incertidumbre del coeficiente. | Coeficiente ± 2 e.e. ≈ intervalo de confianza al 95 %. |
| Estrellas (*, **, ***) | Significancia estadística. | *** p < 0,01; ** p < 0,05; * p < 0,10. Sin estrella: no se distingue de cero. |
| IC 90 % | Intervalo de confianza al 90 %. | Si incluye el cero, la diferencia no es concluyente. |
| Disciplina de mercado | Que los depositantes castiguen a las entidades riesgosas retirando fondos o exigiendo más tasa (Martínez Pería y Schmukler, 2001). | En el informe: efecto de 1 pp más de mora sobre la cuota de captaciones nuevas, con la tasa controlada. |
| Equivalencia mora ↔ tasa | Coeficiente de mora / α. | "1 pp de mora ≈ 0,46 pp de tasa": una entidad con 1 pp más de mora capta como si pagara 0,46 pp menos de tasa. |
| Modelo de corrección de error (ECM) | Modelo en que cada entidad corrige cada mes una parte de su brecha con la tasa de sus pares. | Separa el ajuste de corto plazo del equilibrio de largo plazo. |
| Ajuste mensual | Parte de la brecha con los pares que se cierra en un mes. | 48 %: cierra casi la mitad en un mes (sigue de cerca al mercado). ≈ 0 %: fija su tasa con otra lógica. |
| Vida media | Meses que tarda en cerrarse la mitad de una brecha. | Más corta = reacciona más rápido. |
| Traspaso 3 m | Parte de un movimiento del mercado que la entidad replica en 3 meses. | 90 %: replica casi todo; 15 %: casi no sigue al mercado. |
| Matriz de respuesta | Probabilidad de que la entidad de la columna mueva su tasa en la misma dirección en 0-2 meses después de que la de la fila movió primero. | Comparar con la "probabilidad base" (que se mueva en cualquier ventana): si es bastante mayor, la columna sigue a la fila. |
| Índice de liderazgo | Promedio de cuánto lo siguen menos promedio de cuánto sigue él, en pp. | Positivo: es más seguido que seguidor (líder). Negativo: seguidor. |
| AUC | Probabilidad de que el modelo asigne más riesgo a un caso que sí ocurrió que a uno que no. | 0,5 = azar; 0,6-0,7 = débil pero útil; 0,7-0,8 = aceptable; > 0,8 = bueno. |
| Fuera de muestra / ventana expansiva | El modelo se evalúa en un año que no vio al entrenarse, entrenando solo con años anteriores. | Mide lo que se puede anticipar de verdad, sin mirar el futuro. |
| Probabilidad de movimiento | Probabilidad estimada de que un banco suba (o baje) ≥ 0,15 pp su tasa a plazo en las próximas 4 semanas. | Compararla con la frecuencia histórica (≈ 23 % suben, ≈ 27 % bajan en cualquier ventana de 4 semanas). |
| Bootstrap | Remuestreo repetido de los datos (aquí, semanas completas) para medir incertidumbre. | Da el intervalo de la diferencia de AUC. |
| Cluster / K-means / Ward | Algoritmos que agrupan cantones o entidades parecidos según varias variables. | Los grupos sirven para comparar con pares parecidos; no son categorías oficiales. |
| Silueta | Qué tan separados están los grupos (−1 a 1). | > 0,5 grupos claros; 0,25-0,5 razonables; < 0,25 continuo (segmentación práctica). |

## Oportunidades y simulación

| Término | Qué es | Cómo se lee |
|---|---|---|
| Cuota objetivo | Percentil 75 de las cuotas que la propia entidad logra en cantones del mismo cluster y región. | Lo que ya consigue en mercados parecidos; no es una meta de demanda externa. |
| Brecha de penetración | Cuota objetivo − cuota actual, en pp (mínimo cero). | Grande = rinde por debajo de sí misma en ese cantón. |
| Potencial | Brecha × tamaño del mercado del cantón. | USD que tendría si alcanzara su cuota objetivo. No descuenta costos de expansión. |
| Simulación de tasa | Aplicar el modelo de demanda a cada cantón con la nueva tasa de la entidad, con el flujo total del cantón fijo. | Muestra cuánto capta de más y a quién se lo quita (bancos, cooperativas). |
| Saldo adicional (estado estable) | Flujo mensual adicional × plazo medio en meses. | Saldo extra que se sostiene cuando los depósitos nuevos se renuevan. |
| Costo marginal del fondeo nuevo | (Subida × saldo que ya tiene + tasa nueva × saldo adicional) / saldo adicional, anual. | Cuánto cuesta de verdad cada dólar nuevo si se re-precia todo el saldo. Compararlo con la tasa actual: si es mucho mayor, conviene pagar el premio solo por dinero nuevo. |

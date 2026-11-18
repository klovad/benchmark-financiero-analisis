"""Indicadores de balance por entidad listos para modelos: mora, liquidez y solvencia,
con el rezago con que se conocen.

- morosidad  = cartera improductiva / cartera bruta (vistas del glosario del ETL)
- liquidez   = fondos disponibles (11) / depósitos de corto plazo (vw_depositos_corto_plazo)
- solvencia  = patrimonio (3) / activo (1). Aproximación: el índice regulatorio de
  patrimonio técnico usa activos ponderados por riesgo, que no están en marts.

Rezago: el balance de un mes se publica en las semanas siguientes (Boletín de
Superbancos casi al día; EEFF SEPS con ~1 mes). Para no usar información que nadie
tenía, el balance del mes m se considera disponible desde el mes m + `rezago_meses`
(por defecto 1: en octubre se usa septiembre). En los modelos mensuales eso equivale a
usar el balance del mes anterior.

Valores extremos: se recortan a los percentiles 1-99 dentro de cada tipo de entidad
(hay cooperativas con liquidez > 400 % o patrimonio negativo). Todo en puntos
porcentuales (×100) para leer coeficientes por punto.

La banca pública no tiene balance en marts: queda fuera de cualquier modelo que use
estas variables.
"""

from __future__ import annotations

import pandas as pd

VARIABLES = ["morosidad", "liquidez", "solvencia"]


def indicadores_rezagados(indicadores: pd.DataFrame, rezago_meses: int = 1) -> pd.DataFrame:
    """Una fila por entidad × mes de uso (`anio_mes_uso`) con los tres indicadores en pp,
    sus cambios a 3 meses (`d3_*`) y su desvío frente a la mediana del mismo tipo de
    entidad en ese mes (`rel_*`)."""
    d = indicadores[["entidad_codigo", "tipo_entidad", "anio_mes", "morosidad", "liquidez",
                     "patrimonio_activo"]].rename(columns={"patrimonio_activo": "solvencia"}).copy()
    for v in VARIABLES:
        lim = d.groupby("tipo_entidad")[v].quantile([0.01, 0.99]).unstack()
        d[v] = d[v].clip(d["tipo_entidad"].map(lim[0.01]), d["tipo_entidad"].map(lim[0.99])) * 100
    d = d.sort_values(["entidad_codigo", "anio_mes"])
    for v in VARIABLES:
        d[f"d3_{v}"] = d.groupby("entidad_codigo")[v].diff(3)
        d[f"rel_{v}"] = d[v] - d.groupby(["tipo_entidad", "anio_mes"])[v].transform("median")
    periodo = pd.PeriodIndex.from_fields(year=d["anio_mes"] // 100, month=d["anio_mes"] % 100, freq="M")
    uso = periodo + rezago_meses
    d["anio_mes_uso"] = uso.year * 100 + uso.month
    return d.drop(columns=["anio_mes"])


def columnas(prefijos: tuple[str, ...] = ("", "d3_", "rel_")) -> list[str]:
    return [p + v for p in prefijos for v in VARIABLES]

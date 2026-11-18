"""Sensibilidad de los depósitos a plazo entre bancos privados y cooperativas.

Dos medidas complementarias, a nivel sistema:

1. **Flujos nuevos** (BCE semanal, 2015 →): cuota de las cooperativas en las captaciones
   a plazo de bancos + cooperativas, en logit, contra el diferencial de tasa (coop S1 −
   bancos, a mezcla de plazo constante) y una tendencia. Errores Newey-West.
2. **Saldos** (CAPCOL + SEPS, 2021 →): modelo de corrección de error de la cuota de las
   cooperativas en el saldo a plazo: Δcuota_t = c + b·spread_{t-1} + a·cuota_{t-1}.
   Cuota de equilibrio = −(c + b·spread)/a; vida media del ajuste = ln(0,5)/ln(1+a).

Referencias: Hannan (2003, FEDS 2003-06) encuentra que la presencia de cooperativas de
ahorro sube las tasas que pagan bancos en EE. UU.; Adams, Brevoort y Kiser (2007, JIE)
miden cuánto compiten bancos, thrifts y credit unions; Drechsler, Savov y Schnabl (2017,
QJE) muestran que el poder de mercado local en depósitos determina cuánto se traslada de
las tasas de mercado al depositante.

Limitación: es una relación de forma reducida. El diferencial no es aleatorio (los bancos
suben tasas cuando necesitan liquidez, como en 2023-2024), así que el coeficiente mezcla
la respuesta del depositante con el ciclo de liquidez. La estimación por cantón con
instrumentos (`demanda.py`) es la que aísla la respuesta al precio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from benchmark_analisis.liderazgo import GRANDES


def serie_mensual(w: pd.DataFrame, tasas_semanales: pd.DataFrame, saldos: pd.DataFrame) -> pd.DataFrame:
    """Tasas (bancos grandes + otros bancos vs coop S1), cuota coop en flujos y en saldos."""
    bancos = w[GRANDES + ["OTROS BANCOS"]].mean(axis=1)
    t = tasas_semanales
    g = np.where(t["tipo_entidad"] == "BANCO PRIVADO", "BANCOS",
         np.where(t["tipo_entidad"] == "COOPERATIVA", "COOPS", "OTROS"))
    fl = t.assign(g=g).pivot_table(index="fecha_id", columns="g", values="monto", aggfunc="sum")
    fl.index = pd.to_datetime(fl.index.astype(str), format="%Y%m%d")
    F = fl.resample("ME").sum()
    M = pd.DataFrame({"tasa_bancos": bancos, "tasa_coop_s1": w["COOP SEGMENTO 1"],
                      "tasa_coop_s2": w["COOP SEGMENTO 2"]}).resample("ME").mean()
    M["spread"] = M["tasa_coop_s1"] - M["tasa_bancos"]
    M["flujo_bancos"] = F["BANCOS"]
    M["flujo_coops"] = F["COOPS"]
    M["cuota_coop_flujo"] = F["COOPS"] / (F["COOPS"] + F["BANCOS"])
    st = saldos.groupby(["anio_mes", "tipo_entidad"])["dep_plazo"].sum().unstack()
    st.index = pd.to_datetime(st.index.astype(str), format="%Y%m") + pd.offsets.MonthEnd(0)
    M["saldo_plazo_bancos"] = st["BANCO PRIVADO"]
    M["saldo_plazo_coops"] = st["COOPERATIVA"]
    M["cuota_coop_saldo"] = st["COOPERATIVA"] / (st["COOPERATIVA"] + st["BANCO PRIVADO"])
    return M


def modelo_flujos(M: pd.DataFrame, desde: str = "2015") -> dict:
    d = M.dropna(subset=["cuota_coop_flujo", "spread"]).loc[desde:]
    y = np.log(d["cuota_coop_flujo"] / (1 - d["cuota_coop_flujo"]))
    X = sm.add_constant(pd.DataFrame({"spread": d["spread"],
                                      "tendencia_anual": np.arange(len(d)) / 12}, index=d.index))
    r = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    s = d["cuota_coop_flujo"].mean()
    ult12 = d.iloc[-12:]
    return {"const": r.params["const"], "tendencia_ultima": float(X["tendencia_anual"].iloc[-1]),
            "flujo_mensual_bancos_coops": float((ult12["flujo_bancos"] + ult12["flujo_coops"]).mean()),
            "coef_spread": r.params["spread"], "se_spread": r.bse["spread"],
            "coef_tendencia": r.params["tendencia_anual"],
            "pp_cuota_por_pp_spread": 100 * r.params["spread"] * s * (1 - s),
            "cuota_media": s, "n": int(r.nobs), "r2": r.rsquared, "desde": str(d.index.min().date()),
            "hasta": str(d.index.max().date()), "resumen": str(r.summary())}


def modelo_saldos(M: pd.DataFrame) -> dict:
    d = M.dropna(subset=["cuota_coop_saldo", "spread"]).copy()
    d["dcuota_pp"] = d["cuota_coop_saldo"].diff() * 100
    d["spread_l1"] = d["spread"].shift(1)
    d["cuota_l1_pp"] = d["cuota_coop_saldo"].shift(1) * 100
    d = d.dropna()
    r = sm.OLS(d["dcuota_pp"], sm.add_constant(d[["spread_l1", "cuota_l1_pp"]])).fit(
        cov_type="HAC", cov_kwds={"maxlags": 3})
    a, b = r.params["cuota_l1_pp"], r.params["spread_l1"]
    mercado = (M["saldo_plazo_bancos"] + M["saldo_plazo_coops"]).dropna().iloc[-1]
    return {"const": r.params["const"], "b_spread": b, "se_b": r.bse["spread_l1"], "a_ajuste": a, "se_a": r.bse["cuota_l1_pp"],
            "pp_largo_plazo_por_pp_spread": -b / a,
            "vida_media_meses": np.log(0.5) / np.log(1 + a) if -1 < a < 0 else np.nan,
            "usd_largo_plazo_por_pp_spread": -b / a / 100 * mercado,
            "mercado_plazo_usd": mercado, "n": int(r.nobs), "r2": r.rsquared,
            "resumen": str(r.summary())}

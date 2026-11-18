"""Pruebas de las piezas numéricas de los modelos con datos sintéticos (sin base)."""

import numpy as np
import pandas as pd

from benchmark_analisis.balance import indicadores_rezagados
from benchmark_analisis.demanda import cuotas_logit_anidado, simular
from benchmark_analisis.tasas import efecto_fijo_hedonico, tasa_ajustada


def test_hedonico_recupera_prima_por_plazo():
    rng = np.random.default_rng(0)
    prima = {"30": -1.0, "180": 0.0, "360": 1.5}
    filas = []
    for e in range(20):
        for t in range(30):
            mu = 5 + 0.1 * e + 0.05 * t
            for b, p in prima.items():
                filas.append((f"{e}|{t}", b, mu + p + rng.normal(0, 0.01), rng.uniform(1, 10)))
    d = pd.DataFrame(filas, columns=["celda", "banda", "tasa", "monto"])
    beta = efecto_fijo_hedonico(d, "celda", "banda")
    # Normalizado a media ponderada cero: comparar diferencias entre bandas.
    assert abs((beta["360"] - beta["30"]) - 2.5) < 0.01
    assert abs((beta["180"] - beta["30"]) - 1.0) < 0.01


def test_tasa_ajustada_no_cambia_por_mezcla_de_plazo():
    # Misma tasa por banda en dos semanas; solo cambia la mezcla de montos.
    d = pd.DataFrame({
        "entidad_codigo": ["A"] * 4 + ["B"] * 4,
        "fecha_id": [1, 1, 2, 2] * 2,
        "plazo_codigo": ["30", "360"] * 4,
        "tasa": [4.0, 6.0, 4.0, 6.0, 4.5, 6.5, 4.5, 6.5],
        "monto": [90, 10, 10, 90, 50, 50, 50, 50],
        "operaciones": 1,
    })
    t = tasa_ajustada(d, "plazo_codigo").set_index(["entidad_codigo", "fecha_id"])["tasa_aj"]
    assert abs(t[("A", 1)] - t[("A", 2)]) < 1e-6
    assert abs((t[("B", 1)] - t[("A", 1)]) - 0.5) < 1e-6


def test_logit_anidado_suma_uno_y_sigma_cero_es_softmax():
    delta = np.array([0.2, -0.1, 0.5, 0.0])
    nido = np.array(["B", "B", "C", "C"])
    s = cuotas_logit_anidado(delta, nido, 0.0)
    assert abs(s.sum() - 1) < 1e-12
    assert np.allclose(s, np.exp(delta) / np.exp(delta).sum())
    s2 = cuotas_logit_anidado(delta, nido, 0.6)
    assert abs(s2.sum() - 1) < 1e-12


def test_simular_reproduce_cuotas_y_conserva_el_flujo():
    m = pd.DataFrame({
        "entidad_codigo": ["A", "B", "C"], "tipo_entidad": ["BANCO PRIVADO", "BANCO PRIVADO", "COOPERATIVA"],
        "nido": ["BANCOS", "BANCOS", "COOPERATIVAS"], "monto": [50.0, 30.0, 20.0], "tasa": [5.0, 5.2, 7.0],
    })
    m["s"] = m["monto"] / m["monto"].sum()
    m["s_g"] = m["monto"] / m.groupby("nido")["monto"].transform("sum")
    m["ln_s"], m["ln_s_g"] = np.log(m["s"]), np.log(m["s_g"])
    for sigma in (0.0, 0.5):
        r = simular(m, "A", 0.5, alpha=0.1, sigma=sigma)
        assert np.allclose(r["cuota_base"], m["s"])
        assert abs(r["cambio_monto"].sum()) < 1e-6
        assert r.loc[r["entidad_codigo"] == "A", "cambio_monto"].item() > 0


def test_balance_rezagado_cruza_el_anio_y_queda_en_pp():
    meses = [202110, 202111, 202112, 202201]
    ind = pd.DataFrame({
        "entidad_codigo": "A", "tipo_entidad": "BANCO PRIVADO", "anio_mes": meses,
        "morosidad": [0.02, 0.021, 0.022, 0.03], "liquidez": 0.25, "patrimonio_activo": 0.1,
    })
    b = indicadores_rezagados(ind, rezago_meses=1).set_index("anio_mes_uso")
    assert list(b.index) == [202111, 202112, 202201, 202202]
    # el balance de diciembre se usa en enero; valores en puntos porcentuales
    assert abs(b.loc[202201, "morosidad"] - 2.2) < 0.05
    assert abs(b.loc[202202, "d3_morosidad"] - (b.loc[202202, "morosidad"] - b.loc[202111, "morosidad"])) < 1e-9

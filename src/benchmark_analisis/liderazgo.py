"""Liderazgo y anticipación de tasas pasivas entre entidades.

Entrada: panel semanal ancho de tasas a mezcla de plazo constante
(`tasas.series_semanales`), columnas = grupos de comparación.

Cuatro piezas, de lo descriptivo a lo predictivo:

1. `fechas_ciclo`: cuándo cada entidad empezó a subir y a bajar en el ciclo 2022-2025
   (fechado de puntos de giro, en la línea de Bry y Boschan, 1971, simplificado).
2. `matriz_respuesta`: probabilidad de que B mueva su tasa en la misma dirección en 0-2
   meses después de que A movió primero, contra la probabilidad base de B. Es la
   evidencia de "líder-seguidor" en precios (price leadership en oligopolio; para
   rigidez y asimetría de tasas bancarias, Hannan y Berger, 1991, AER).
3. `correccion_error`: modelo de corrección de error de cada entidad hacia la tasa de sus
   pares (De Graeve, De Jonghe y Vander Vennet, 2007, J. Banking & Finance; Gambacorta,
   2008, European Economic Review). `alpha` = velocidad con la que cierra su brecha con el
   mercado; cerca de 0 = fija su propio precio (o no compite en tasa).
4. `modelo_anticipacion`: logística que estima la probabilidad de que un competidor suba
   o baje >= `umbral` pp (0,15 por defecto) en las próximas `horizonte` semanas, evaluada con ventana
   expansiva año a año (sin mirar el futuro).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from benchmark_analisis.balance import columnas

GRANDES = ["PICHINCHA", "GUAYAQUIL", "PACIFICO", "PRODUBANCO", "BOLIVARIANO", "INTERNACIONAL"]
COMPETIDORES = GRANDES + ["AUSTRO", "DINERS"]


def suavizar(w: pd.DataFrame, semanas: int = 4) -> pd.DataFrame:
    return w.interpolate(limit=3).rolling(semanas, min_periods=semanas - 1).mean()


def fechas_ciclo(w: pd.DataFrame, grupos: list[str], umbral: float = 1.0) -> pd.DataFrame:
    """Piso 2021-22, fecha en que superó piso + `umbral` pp, pico 2023-25 y fecha en que
    bajó `umbral` pp desde el pico (media móvil de 8 semanas)."""
    m8 = w.interpolate(limit=3).rolling(8, min_periods=6).mean()
    filas = []
    for g in grupos:
        s = m8[g]
        piso = s.loc["2021-06":"2022-06"]
        t0 = piso.idxmin()
        sube = s.loc[t0:"2024-12"]
        cruce = sube[sube > piso.min() + umbral].index.min()
        pico = s.loc["2023-06":"2025-06"].idxmax()
        baja = s.loc[pico:]
        cruce_b = baja[baja < s[pico] - umbral].index.min()
        filas.append({"grupo": g, "piso": t0, "tasa_piso": piso.min(), "sube_desde": cruce,
                      "pico": pico, "tasa_pico": s[pico], "subida_pp": s[pico] - piso.min(),
                      "baja_desde": cruce_b, "tasa_actual": s.dropna().iloc[-1]})
    return pd.DataFrame(filas).sort_values("sube_desde")


def eventos_mensuales(w: pd.DataFrame, grupos: list[str], umbral: float = 0.20) -> pd.DataFrame:
    """+1 / -1 en los meses en que la tasa media mensual cambió >= `umbral` pp."""
    m = w[grupos].interpolate(limit=3).resample("ME").mean().diff()
    return (m.abs() >= umbral).astype(int) * np.sign(m)


def matriz_respuesta(w: pd.DataFrame, grupos: list[str], umbral: float = 0.20,
                     ventana: int = 3) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(P(B sigue | A movió primero), probabilidad base de B, n de eventos de A).
    'Movió primero' = B no se había movido en esa dirección en los 2 meses previos.
    `ventana` = meses t..t+ventana-1 en que se busca la respuesta de B."""
    ev = eventos_mensuales(w, grupos, umbral)
    R = pd.DataFrame(np.nan, index=grupos, columns=grupos)
    N = R.copy()
    base = pd.Series(index=grupos, dtype=float)
    for b in grupos:
        eb = ev[b].to_numpy()
        base[b] = np.mean([(eb[t:t + ventana] != 0).any() for t in range(len(eb) - ventana)])
    for a in grupos:
        ea = ev[a].to_numpy()
        for b in grupos:
            if a == b:
                continue
            eb = ev[b].to_numpy()
            hits = []
            for t in np.flatnonzero(ea):
                s = ea[t]
                if (eb[max(0, t - 2):t] == s).any():
                    continue
                hits.append((eb[t:t + ventana] == s).any())
            R.loc[a, b] = np.mean(hits) if hits else np.nan
            N.loc[a, b] = len(hits)
    return R, base.to_frame("probabilidad_base"), N


def indice_liderazgo(R: pd.DataFrame) -> pd.Series:
    """Cuánto lo siguen (media de su fila) menos cuánto sigue él (media de su columna)."""
    return (R.mean(axis=1) - R.mean(axis=0)).sort_values(ascending=False)


def correccion_error(w: pd.DataFrame, grupos: list[str], pares: list[str] = GRANDES,
                     desde: str = "2017", frecuencia: str = "W") -> pd.DataFrame:
    """Δr_i = c + alpha (r_i − r̄_pares)_{t-1} + Σ_k b_k Δr̄_pares_{t-k} + φ Δr_i_{t-1}.
    Errores HAC. `frecuencia` 'W' semanal o 'ME' mensual (menos ruido de composición)."""
    x = w.loc[desde:].interpolate(limit=3)
    if frecuencia != "W":
        x = x.resample(frecuencia).mean()
    filas = []
    for g in grupos:
        p = [b for b in pares if b != g]
        mk = x[p].mean(axis=1)
        df = pd.DataFrame({"dy": x[g].diff(), "brecha": (x[g] - mk).shift(1),
                           "dm0": mk.diff(), "dm1": mk.diff().shift(1),
                           "dm2": mk.diff().shift(2), "dy1": x[g].diff().shift(1)}).dropna()
        r = sm.OLS(df["dy"], sm.add_constant(df.drop(columns="dy"))).fit(
            cov_type="HAC", cov_kwds={"maxlags": 4})
        a = r.params["brecha"]
        filas.append({"grupo": g, "alpha": a, "t_alpha": r.tvalues["brecha"],
                      "vida_media": np.log(0.5) / np.log(1 + a) if -1 < a < 0 else np.nan,
                      "traspaso_corto": r.params[["dm0", "dm1", "dm2"]].sum(),
                      "brecha_media_2025": (x[g] - mk).loc["2025":].mean(),
                      "r2": r.rsquared})
    return pd.DataFrame(filas)


def dataset_movimientos(w: pd.DataFrame, flujos: pd.DataFrame | None = None,
                        bancos: list[str] = COMPETIDORES, horizonte: int = 4,
                        umbral: float = 0.15, desde: str = "2016",
                        balance: pd.DataFrame | None = None) -> pd.DataFrame:
    """Una fila por banco × semana con variables observables a esa fecha y objetivos
    y_sube / y_baja (cambio de la media de 4 semanas en `horizonte` semanas).

    `balance` (salida de `balance.indicadores_rezagados`) agrega mora, liquidez y
    solvencia del banco, ya rezagadas por publicación: la semana usa el balance cuyo
    `anio_mes_uso` es su mes. Un banco con poca liquidez tiene motivo para subir su tasa
    aunque el mercado no se mueva; uno con mora creciente, para pagar más por confianza
    (Martínez Pería y Schmukler, 2001)."""
    x = w.loc[desde:]
    s4 = suavizar(x)
    mk = s4[bancos].mean(axis=1)
    partes = []
    for b in bancos:
        f = pd.DataFrame(index=x.index)
        f["brecha_mercado"] = s4[b] - mk
        f["brecha_coop_s1"] = s4["COOP SEGMENTO 1"] - s4[b]
        f["nivel"] = s4[b]
        for L in (1, 4, 8, 13):
            f[f"cambio_propio_{L}s"] = s4[b] - s4[b].shift(L)
            f[f"cambio_mercado_{L}s"] = mk - mk.shift(L)
        for lider in ("PICHINCHA", "GUAYAQUIL"):
            f[f"cambio_{lider.lower()}_4s"] = 0.0 if lider == b else s4[lider] - s4[lider].shift(4)
        otros = [o for o in bancos if o != b]
        f["rivales_suben_4s"] = sum(((s4[o] - s4[o].shift(4)) > umbral).astype(int) for o in otros)
        f["rivales_bajan_4s"] = sum(((s4[o] - s4[o].shift(4)) < -umbral).astype(int) for o in otros)
        if flujos is not None and b in flujos:
            fl = flujos[b].reindex(x.index)
            f["flujo_4_vs_13s"] = np.log(fl.rolling(4).sum()) - np.log(fl.rolling(13).sum() / 13 * 4)
        fut = s4[b].shift(-horizonte) - s4[b]
        f["y_sube"] = (fut > umbral).astype(float).where(fut.notna())
        f["y_baja"] = (fut < -umbral).astype(float).where(fut.notna())
        f["banco"] = b
        if balance is not None:
            bb = balance[balance["entidad_codigo"] == b].set_index("anio_mes_uso")[columnas()]
            mes = pd.Series(x.index.year * 100 + x.index.month, index=x.index)
            f = f.join(bb.reindex(mes.to_numpy()).set_axis(x.index))
        partes.append(f)
    return pd.concat(partes)


# Para anticipar se usan el desvío frente a la mediana de los bancos y el cambio a 3 meses;
# los niveles quedan solo como dato descriptivo (son casi colineales con el desvío porque la
# mediana se mueve poco, y daban coeficientes de signo opuesto).
NIVELES_BALANCE = ["liquidez", "morosidad", "solvencia"]


def columnas_balance() -> list[str]:
    return columnas(("d3_", "rel_"))


def _variables(D: pd.DataFrame, sin_balance: bool = False) -> list[str]:
    excluir = {"y_sube", "y_baja", "banco", *NIVELES_BALANCE}
    if sin_balance:
        excluir |= set(columnas_balance())
    return [c for c in D.columns if c not in excluir]


def evaluar_anticipacion(D: pd.DataFrame, objetivo: str, desde_anio: int = 2020,
                         horizonte: int = 4, variables: list[str] | None = None,
                         con_predicciones: bool = False):
    """AUC fuera de muestra con ventana expansiva: entrena con años < a (dejando
    `horizonte` semanas de margen para no filtrar el objetivo) y evalúa en el año a.
    Con `con_predicciones` devuelve también las probabilidades fuera de muestra."""
    X = variables or _variables(D)
    datos = D.dropna(subset=X + [objetivo])
    filas, todas = [], []
    for anio in range(desde_anio, datos.index.year.max() + 1):
        corte = pd.Timestamp(f"{anio}-01-01") - pd.Timedelta(weeks=horizonte)
        tr, te = datos[datos.index < corte], datos[datos.index.year == anio]
        if te[objetivo].nunique() < 2:
            continue
        mu, sd = tr[X].mean(), tr[X].std()
        m = LogisticRegression(max_iter=3000, C=0.5).fit((tr[X] - mu) / sd, tr[objetivo])
        p = m.predict_proba((te[X] - mu) / sd)[:, 1]
        filas.append({"anio": anio, "auc": roc_auc_score(te[objetivo], p), "n": len(te),
                      "frecuencia": te[objetivo].mean()})
        todas.append(pd.DataFrame({"y": te[objetivo], "p": p, "banco": te["banco"]}))
    t = pd.concat(todas)
    filas.append({"anio": "total", "auc": roc_auc_score(t["y"], t["p"]), "n": len(t),
                  "frecuencia": t["y"].mean()})
    return (pd.DataFrame(filas), t) if con_predicciones else pd.DataFrame(filas)


def comparar_con_balance(D: pd.DataFrame, objetivo: str, desde_anio: int = 2023,
                         horizonte: int = 4, repeticiones: int = 500, semilla: int = 7) -> dict:
    """¿Agregan mora, liquidez y solvencia al modelo de anticipación?

    El balance existe desde 2021 y el modelo base aprende desde 2016: entrenar ambos solo
    desde 2021 castiga al base. Se compara en dos etapas, año a año (ventana expansiva):
      1. modelo base con toda la historia previa (sin balance);
      2. logística sobre las filas 2021+ previas con [logit del base] + variables de balance.
    Ambos se evalúan en las mismas filas del año. Se reporta la AUC por año, su promedio
    y el intervalo al 90 % de la diferencia por bootstrap de semanas completas (las filas
    de una misma semana están correlacionadas entre bancos)."""
    Xb, Xbal = _variables(D, sin_balance=True), columnas_balance()
    datos = D.dropna(subset=Xb + [objetivo])
    filas, pb, pa = [], [], []
    for anio in range(desde_anio, datos.index.year.max() + 1):
        corte = pd.Timestamp(f"{anio}-01-01") - pd.Timedelta(weeks=horizonte)
        tr, te = datos[datos.index < corte], datos[datos.index.year == anio].dropna(subset=Xbal)
        if te[objetivo].nunique() < 2:
            continue
        mu, sd = tr[Xb].mean(), tr[Xb].std()
        base = LogisticRegression(max_iter=3000, C=0.5).fit((tr[Xb] - mu) / sd, tr[objetivo])
        tr2 = tr.dropna(subset=Xbal)
        z_tr = base.decision_function((tr2[Xb] - mu) / sd)
        z_te = base.decision_function((te[Xb] - mu) / sd)
        mb, sb = tr2[Xbal].mean(), tr2[Xbal].std()
        A_tr = np.column_stack([z_tr, ((tr2[Xbal] - mb) / sb).to_numpy()])
        A_te = np.column_stack([z_te, ((te[Xbal] - mb) / sb).to_numpy()])
        ampl = LogisticRegression(max_iter=3000, C=0.5).fit(A_tr, tr2[objetivo])
        p0, p1 = 1 / (1 + np.exp(-z_te)), ampl.predict_proba(A_te)[:, 1]
        filas.append({"anio": anio, "n": len(te), "frecuencia": te[objetivo].mean(),
                      "auc_sin_balance": roc_auc_score(te[objetivo], p0),
                      "auc_con_balance": roc_auc_score(te[objetivo], p1)})
        pb.append(pd.DataFrame({"y": te[objetivo], "p": p0, "anio": anio}))
        pa.append(pd.DataFrame({"y": te[objetivo], "p": p1, "anio": anio}))
    tabla = pd.DataFrame(filas)
    pb, pa = pd.concat(pb), pd.concat(pa)

    def auc_media(t):
        return np.mean([roc_auc_score(g["y"], g["p"]) for _, g in t.groupby("anio") if g["y"].nunique() == 2])

    rng = np.random.default_rng(semilla)
    semanas = pb.index.unique()
    dif = []
    for _ in range(repeticiones):
        m = rng.choice(semanas, len(semanas), replace=True)
        dif.append(auc_media(pa.loc[m]) - auc_media(pb.loc[m]))
    return {"tabla": tabla,
            "auc_media_sin": float(tabla["auc_sin_balance"].mean()),
            "auc_media_con": float(tabla["auc_con_balance"].mean()),
            "diferencia": float(tabla["auc_con_balance"].mean() - tabla["auc_sin_balance"].mean()),
            "ic90": [float(np.quantile(dif, 0.05)), float(np.quantile(dif, 0.95))]}


def coeficientes_balance(D: pd.DataFrame, objetivo: str) -> pd.Series:
    """Coeficientes estandarizados de la segunda etapa (balance dado el logit del modelo
    base) con toda la muestra 2021+: cómo mueve cada variable de balance la probabilidad."""
    Xb, Xbal = _variables(D, sin_balance=True), columnas_balance()
    datos = D.dropna(subset=Xb + [objetivo])
    mu, sd = datos[Xb].mean(), datos[Xb].std()
    base = LogisticRegression(max_iter=3000, C=0.5).fit((datos[Xb] - mu) / sd, datos[objetivo])
    d2 = datos.dropna(subset=Xbal)
    # Índice = semana, repetido entre bancos: armar por posición, no con join.
    A = ((d2[Xbal] - d2[Xbal].mean()) / d2[Xbal].std()).reset_index(drop=True)
    A.insert(0, "logit_base", base.decision_function((d2[Xb] - mu) / sd))
    m = LogisticRegression(max_iter=3000, C=0.5).fit(A, d2[objetivo].to_numpy())
    return pd.Series(m.coef_[0], index=A.columns)


def modelo_anticipacion(D: pd.DataFrame, objetivo: str, variables: list[str] | None = None):
    """Ajusta la logística con toda la historia etiquetada. Devuelve (modelo, medias,
    desvíos, coeficientes estandarizados); las variables usadas son `medias.index`."""
    X = variables or _variables(D)
    datos = D.dropna(subset=X + [objetivo])
    mu, sd = datos[X].mean(), datos[X].std()
    m = LogisticRegression(max_iter=3000, C=0.5).fit((datos[X] - mu) / sd, datos[objetivo])
    coef = pd.Series(m.coef_[0], index=X).sort_values()
    return m, mu, sd, coef


def predecir_ultima_semana(D: pd.DataFrame, modelos: dict) -> pd.DataFrame:
    """Probabilidad de subida y bajada en las próximas semanas, por banco, con la última
    semana que tiene todas las variables (el objetivo aún no se conoce)."""
    X = sorted({c for (_, mu, _, _) in modelos.values() for c in mu.index})
    ult = D.dropna(subset=X)
    ult = ult[ult.index == ult.index.max()]
    extra = [c for c in ("liquidez", "morosidad", "solvencia") if c in ult]
    out = ult[["banco", "nivel", "brecha_mercado", "brecha_coop_s1"] + extra].copy()
    for nombre, (m, mu, sd, _) in modelos.items():
        out[f"p_{nombre}"] = m.predict_proba((ult[list(mu.index)] - mu) / sd)[:, 1]
    return out.reset_index(names="semana")

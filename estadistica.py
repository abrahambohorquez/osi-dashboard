"""
Las cuentas detrás de cada hoja de análisis: momentos y cero-inflación,
VIF, autocorrelación, el teorema de Frisch-Waugh-Lovell, y el índice de
Moran para autocorrelación espacial. Todo recibe un DataFrame y columnas
por nombre, así que funciona igual sobre los datos simulados que sobre
cualquier archivo que alguien suba.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.spatial import cKDTree
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.stattools import acf


def momentos(df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    filas = []
    for var in variables:
        x = df[var].dropna()
        if len(x) == 0:
            continue
        filas.append({
            "variable": var,
            "mean": x.mean(),
            "std dev": x.std(),
            "skew": stats.skew(x),
            "kurtosis": stats.kurtosis(x),
            "% zeros": float((x == 0).mean() * 100),
        })
    return pd.DataFrame(filas).set_index("variable")


def tabla_vif(df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    X = df[variables].dropna()
    X = X.loc[:, X.std() > 1e-9]
    if len(X) < 50 or X.shape[1] < 2:
        return pd.DataFrame()
    X_const = X.copy()
    X_const.insert(0, "const", 1.0)
    filas = []
    for i, col in enumerate(X.columns):
        vif = variance_inflation_factor(X_const.values, i + 1)
        filas.append({"variable": col, "VIF": vif})
    tabla = pd.DataFrame(filas).sort_values("VIF", ascending=False).reset_index(drop=True)

    def _lectura(v):
        if not np.isfinite(v) or v > 20:
            return "high, likely an exact identity with another variable"
        if v > 5:
            return "moderate, worth watching"
        return "no problem"

    tabla["reading"] = tabla["VIF"].apply(_lectura)
    return tabla


def autocorrelacion(serie: pd.Series, nlags: int = 72) -> np.ndarray:
    nlags = min(nlags, len(serie) - 1)
    return acf(serie.dropna(), nlags=nlags, fft=True)


def fwl(df: pd.DataFrame, y_col: str, x_col: str, controles: list[str]) -> dict:
    """Frisch-Waugh-Lovell: el efecto de x_col sobre y_col controlando por
    `controles`, construido de la forma que el teorema describe (no como
    atajo): se le quita a y_col y a x_col lo que los controles explican
    de cada uno, y se regresa el residuo de y_col contra el residuo de
    x_col. La pendiente de esa regresión es matemáticamente idéntica al
    coeficiente de x_col en una regresión múltiple con todo junto, pero
    verla así deja ver la mecánica: qué le queda a x_col después de que
    los controles se llevaron su parte.

    Devuelve tanto el coeficiente "ingenuo" (y_col ~ x_col solo, sin
    controlar nada) como el parcial, más los residuos para graficar.
    """
    cols = [y_col, x_col] + controles
    datos = df[cols].dropna()
    if len(datos) < max(30, len(controles) * 5):
        return {"n": len(datos), "suficiente": False}

    y = datos[y_col].to_numpy()
    x = datos[x_col].to_numpy()

    # coeficiente ingenuo: y ~ x, sin controlar nada
    X_ingenuo = sm.add_constant(x)
    modelo_ingenuo = sm.OLS(y, X_ingenuo).fit()
    coef_ingenuo = modelo_ingenuo.params[1]
    p_ingenuo = modelo_ingenuo.pvalues[1]

    if controles:
        C = sm.add_constant(datos[controles].to_numpy())
        resid_y = sm.OLS(y, C).fit().resid
        resid_x = sm.OLS(x, C).fit().resid
    else:
        resid_y = y - y.mean()
        resid_x = x - x.mean()

    X_parcial = sm.add_constant(resid_x)
    modelo_parcial = sm.OLS(resid_y, X_parcial).fit()
    coef_parcial = modelo_parcial.params[1]
    p_parcial = modelo_parcial.pvalues[1]

    return {
        "n": len(datos),
        "suficiente": True,
        "coef_ingenuo": coef_ingenuo,
        "p_ingenuo": p_ingenuo,
        "coef_parcial": coef_parcial,
        "p_parcial": p_parcial,
        "cambia_signo": np.sign(coef_ingenuo) != np.sign(coef_parcial) and abs(coef_ingenuo) > 1e-9 and abs(coef_parcial) > 1e-9,
        "resid_x": resid_x,
        "resid_y": resid_y,
    }


def morans_i(df: pd.DataFrame, variable: str, lat_col: str = "posicion_y", lon_col: str = "posicion_x",
             k: int = 5) -> dict | None:
    """Índice de Moran sobre el valor de `variable` por condado (un valor
    por condado, normalmente el pico de OSI), usando los k vecinos más
    cercanos como vecindario. Requiere columnas de posición; si no están,
    devuelve None en vez de fallar."""
    if lat_col not in df.columns or lon_col not in df.columns:
        return None

    agg_cols = {variable: "max", lat_col: "first", lon_col: "first"}
    if "fipsCode" not in df.columns:
        return None
    por_condado = df.groupby("fipsCode").agg(agg_cols).dropna()
    n = len(por_condado)
    if n < 8:
        return None

    x = por_condado[variable].to_numpy()
    coords = por_condado[[lon_col, lat_col]].to_numpy()
    xbar = x.mean()
    dx = x - xbar

    arbol = cKDTree(coords)
    k_efectivo = min(k + 1, n)
    _, vecinos = arbol.query(coords, k=k_efectivo)

    W = np.zeros((n, n))
    for i in range(n):
        for j in vecinos[i]:
            if j != i:
                W[i, j] = 1.0

    s0 = W.sum()
    if s0 == 0:
        return None
    numerador = 0.0
    for i in range(n):
        vecinos_i = np.where(W[i] > 0)[0]
        numerador += dx[i] * dx[vecinos_i].sum()
    denominador = (dx ** 2).sum()
    if denominador == 0:
        return None
    I = (n / s0) * (numerador / denominador)
    esperado = -1.0 / (n - 1)
    return {"I": float(I), "esperado_bajo_azar": esperado, "n_condados": n}

"""Distributions, moments and zero-inflation: the mathematical side of the EDA."""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import estadistica as est
import theme
import viz_patterns as vp

df = comp.preparar_hoja(dict(page_title="Distributions | OSI Analysis Desk", layout="wide"),
                        clave="dist")

comp.encabezado_pagina(
    "Distributions and zero-inflation",
    "The shape of the target decides the loss function, so it is worth measuring before anything "
    "is fitted. Severity is not approximately Gaussian: it is a point mass at zero with a long "
    "right tail, and the figures below quantify how far from Gaussian it actually is.",
)
comp.banner_datos_simulados()

variables = [v for v in ["osi", "N_t", "P_t", "gust"] if v in df.columns]
tabla = est.momentos(df, variables)

if "osi" in variables:
    fila_osi = tabla.loc["osi"]
    comp.hallazgo(
        f"Kurtosis {fila_osi['kurtosis']:.1f} and {fila_osi['% zeros']:.0f}% zeros rule out a "
        "plain squared error",
        f"OSI has a kurtosis of <b>{fila_osi['kurtosis']:.1f}</b> (a normal Gaussian bell would "
        f"have 0) and <b>{fila_osi['% zeros']:.0f}%</b> of its hours sit at exactly zero. A "
        "standard mean squared error gives the same weight to getting a zero right as to getting "
        "a peak right, so it treats a calm county as equally important as one in a full-blown "
        "emergency. That's why the team uses a Tweedie loss, built exactly for this shape of "
        "distribution.",
        tono="accent",
    )

comp.titulo_seccion("01", "Share of hours at exactly zero")
comp.entradilla(
    "The zero share quoted above, broken out by variable: each figure is the size of that "
    "variable's point mass at zero. Anything above roughly 40% is enough for an unweighted "
    "squared-error fit to spend most of its capacity reproducing calm hours. Gust sits at zero "
    "almost never, which is exactly why it stays useful as a predictor when the target does not "
    "move."
)
comp.fila_metricas([
    (var, f"{tabla.loc[var, '% zeros']:.1f}%", "of hours at exactly zero", "accent")
    for var in variables
])

st.write("")
comp.titulo_seccion("02", "Moments")
comp.entradilla(
    "Positive skew places the long tail on the high side; excess kurtosis above zero means more "
    "mass sits in rare extreme values than a Gaussian of the same variance would carry. Both are "
    "computed on the full column, zeros included."
)
st.dataframe(tabla.round(4), width="stretch")
comp.nota_fuente(
    "<b>Source:</b> sample moments of the active file, computed in <code>estadistica.momentos</code>. "
    "<b>Reference:</b> a Gaussian has skew 0 and excess kurtosis 0."
)

comp.titulo_seccion("03", "Marginal distribution")
col1, col2 = st.columns([2, 1])
with col1:
    variable_hist = st.selectbox("Variable to plot", variables, key="hist_var")
with col2:
    solo_positivos = st.checkbox("Only hours with a value greater than zero", value=True)

datos_hist = df[variable_hist].dropna()
if solo_positivos:
    datos_hist = datos_hist[datos_hist > 0]

fig = go.Figure()
fig.add_trace(go.Histogram(x=datos_hist, marker_color=theme.COLOR_POR_VARIABLE.get(variable_hist, theme.INK),
                            marker_line_color=theme.PANEL, marker_line_width=0.5, nbinsx=60))
theme.aplicar_tema(fig, altura=380)
fig.update_yaxes(title_text="number of hours")
comp.figura(fig, "1",
            f"Distribution of {variable_hist}"
            + (", hours at zero excluded" if solo_positivos else ", all hours"),
            fuente="<b>Note:</b> excluding zeros changes what is being described. With them, "
                   "this is the distribution of the region; without them, it is the "
                   "distribution of the event conditional on one having started.")

comp.titulo_seccion("04", "How the distribution changes through the event")
comp.entradilla(
    "The figure above is a single frozen shape for the whole window, which hides the thing that "
    "matters operationally: the distribution is not stationary. Splitting the window into phases "
    "and stacking one density per phase shows the collapse from a point mass at zero, out into a "
    "wide tail, and back again."
)
fig_ridge = vp.figura_ridgeline_fase(df, variable="osi", n_fases=8)
if fig_ridge is not None:
    comp.figura(fig_ridge, "2", "Severity distribution by phase of the event",
                fuente="<b>Method:</b> the window is split into eight equal phases and a kernel "
                       "density is drawn per phase. <b>Reading:</b> a narrow spike at the left "
                       "edge is a calm phase.")
else:
    st.info("Not enough hours in this file to build a phase ridgeline.")

comp.ver_tambien(["series", "corr", "models"])
comp.pie_sitio()

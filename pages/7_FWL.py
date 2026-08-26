"""Frisch-Waugh-Lovell: the effect of a variable on OSI, before and after
controlling for the rest. The missing piece of the EDA."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import estadistica as est
import theme

df = comp.preparar_hoja(dict(page_title="Frisch-Waugh-Lovell | OSI Analysis Desk",
                             layout="wide"), clave="fwl")

comp.encabezado_pagina(
    "Frisch-Waugh-Lovell",
    "A raw correlation between a weather field and severity can conceal an effect or invent one. "
    "The Frisch-Waugh-Lovell theorem recovers a predictor's own contribution by residualising it "
    "against the remaining controls first. Predictors whose sign flips under this treatment are "
    "the ones a naive importance ranking would have got backwards.",
)
comp.banner_datos_simulados()

st.markdown("""
<div class="finding tone-ink">
  <div class="flabel">What this means before the math</div>
  <p>
  Two things can move together without either one causing the other. Snow and gust often show up
  in the same winter storms: look at snow alone and it can look like a big driver of outages,
  when really both snow and outages are being driven by the same storm, and once you account for
  gust, snow's own extra contribution shrinks or disappears. Frisch-Waugh-Lovell is the formal way
  to ask "once I remove what the other variables already explain, what does this one variable
  still explain on its own." A variable whose effect survives that removal is a real, independent
  driver. One whose effect vanishes was mostly riding along with something else.
  </p>
</div>
""", unsafe_allow_html=True)

candidatas = [v for v in ["gust", "wind_speed_10m", "t2m", "d2m", "r2", "mslma", "sp",
                          "tp", "rain", "csnow", "blh", "soil_moist"] if v in df.columns]

if len(candidatas) < 3:
    st.warning("This file needs at least three weather variables to run this.")
    st.stop()


@st.cache_data(show_spinner=False)
def _buscar_default(datos: "pd.DataFrame", variables: tuple[str, ...]) -> str:
    """Scans a handful of combinations so the page opens showing the most
    interesting case, not some random variable. To make the comparison
    meaningful across variables with very different units (r2 in %,
    mslma in hPa, gust in mph), it standardizes each coefficient by
    multiplying it by x's standard deviation: that way the score measures
    "how much OSI moves per one standard deviation of change in x",
    comparable across variables. A variable only competes if its naive
    relationship was already statistically real (p < 0.05); otherwise any
    large change is just noise around a coefficient near zero, not a
    finding."""
    mejor = None
    mejor_score = -1.0
    for var in variables:
        controles = [v for v in variables if v != var][:3]
        r = est.fwl(datos, "osi", var, controles)
        if not r.get("suficiente") or r["p_ingenuo"] >= 0.05:
            continue
        desv_x = datos[var].std()
        efecto_ingenuo = r["coef_ingenuo"] * desv_x
        efecto_parcial = r["coef_parcial"] * desv_x
        score = abs(efecto_ingenuo - efecto_parcial)
        if r["cambia_signo"]:
            score *= 3
        if score > mejor_score:
            mejor_score = score
            mejor = var
    return mejor or variables[0]


var_default = _buscar_default(df, tuple(candidatas))

col1, col2 = st.columns(2)
with col1:
    variable_interes = st.selectbox(
        "Variable of interest", candidatas,
        index=candidatas.index(var_default),
        help="The variable whose effect on OSI you want to measure.",
    )
with col2:
    opciones_control = [v for v in candidatas if v != variable_interes]
    controles = st.multiselect(
        "Control for", opciones_control,
        default=opciones_control[: min(3, len(opciones_control))],
        help="The other variables whose effect gets removed first from osi and from the variable of interest.",
    )

resultado = est.fwl(df, "osi", variable_interes, controles)

if not resultado.get("suficiente"):
    st.warning("Not enough complete rows for this combination of variables.")
    st.stop()

st.write("")
tono_hallazgo = "warn" if resultado["cambia_signo"] else "accent"
cambio_pct = 100 * (resultado["coef_ingenuo"] - resultado["coef_parcial"]) / (abs(resultado["coef_ingenuo"]) + 1e-9)
if resultado["cambia_signo"]:
    nivel_fwl = "severe"
elif abs(cambio_pct) >= 50:
    nivel_fwl = "warning"
elif abs(cambio_pct) >= 20:
    nivel_fwl = "watch"
else:
    nivel_fwl = "calm"
if resultado["cambia_signo"]:
    texto = (
        f"The coefficient of <b>{variable_interes}</b> on OSI <b>flips sign</b> when controlling "
        f"for {', '.join(controles) if controles else 'the other variables'}: "
        f"naive = <b>{resultado['coef_ingenuo']:.5f}</b>, partial = "
        f"<b>{resultado['coef_parcial']:.5f}</b>. Without controlling, this variable appears to "
        "push OSI in one direction; after controlling, it pushes in the opposite one. That's "
        "exactly what the theorem is built to catch."
    )
else:
    texto = (
        f"The coefficient of <b>{variable_interes}</b> on OSI goes from "
        f"<b>{resultado['coef_ingenuo']:.5f}</b> (naive, controlling for nothing) to "
        f"<b>{resultado['coef_parcial']:.5f}</b> (partial, controlling for "
        f"{', '.join(controles) if controles else 'nothing'}). "
        f"That's a <b>{abs(cambio_pct):.0f}%</b> change in the size of the effect: a large part "
        "of what this variable seemed to explain is actually explained by the others, which move "
        "at the same time."
    )
comp.hallazgo(f"What the theorem found for this combination {comp.insignia_severidad(nivel_fwl)}",
             texto, tono=tono_hallazgo)

if resultado["cambia_signo"]:
    comp.hallazgo(
        "Business read",
        f"A policy built on the raw correlation of {variable_interes} with outages would target "
        "the wrong lever: it would look protective or harmful in exactly the wrong direction, "
        "because it was never isolating this variable's own effect to begin with.",
        tono="ok",
    )

comp.fila_metricas([
    ("naive coefficient", f"{resultado['coef_ingenuo']:.5f}", f"p = {resultado['p_ingenuo']:.4f}", "ink"),
    ("partial coefficient", f"{resultado['coef_parcial']:.5f}", f"p = {resultado['p_parcial']:.4f}", "accent"),
    ("rows used", f"{resultado['n']:,}", "no nulls in any of the variables", "ink"),
])

st.write("")
col_izq, col_der = st.columns(2, gap="large")
with col_izq:
    st.markdown("#### Before controlling")
    st.caption(f"Simple regression: osi against {variable_interes}, nothing else.")
    muestra = df[["osi", variable_interes]].dropna()
    if len(muestra) > 4000:
        muestra = muestra.sample(4000, random_state=0)
    fig_naive = go.Figure()
    fig_naive.add_trace(go.Scatter(x=muestra[variable_interes], y=muestra["osi"], mode="markers",
                                    marker=dict(color=theme.MUTED, size=5, opacity=0.35)))
    x_line = np.linspace(muestra[variable_interes].min(), muestra[variable_interes].max(), 50)
    y_line = resultado["coef_ingenuo"] * (x_line - muestra[variable_interes].mean()) + muestra["osi"].mean()
    fig_naive.add_trace(go.Scatter(x=x_line, y=y_line, mode="lines", line=dict(color=theme.WARN, width=2.5)))
    theme.aplicar_tema(fig_naive, altura=360)
    fig_naive.update_xaxes(title_text=variable_interes)
    fig_naive.update_yaxes(title_text="osi")
    fig_naive.update_layout(showlegend=False)
    comp.figura(fig_naive, "1", "Raw relationship, no controls",
                fuente="<b>Fit:</b> ordinary least squares of severity on the selected "
                       "predictor alone.")

with col_der:
    st.markdown("#### After controlling")
    st.caption("What's left of each variable once you remove what the controls already explained.")
    fig_parcial = go.Figure()
    fig_parcial.add_trace(go.Scatter(x=resultado["resid_x"], y=resultado["resid_y"], mode="markers",
                                      marker=dict(color=theme.ACCENT, size=5, opacity=0.45)))
    x_line2 = np.linspace(resultado["resid_x"].min(), resultado["resid_x"].max(), 50)
    y_line2 = resultado["coef_parcial"] * x_line2
    fig_parcial.add_trace(go.Scatter(x=x_line2, y=y_line2, mode="lines", line=dict(color=theme.INK, width=2.5)))
    theme.aplicar_tema(fig_parcial, altura=360)
    fig_parcial.update_xaxes(title_text=f"residual of {variable_interes}")
    fig_parcial.update_yaxes(title_text="residual of osi")
    fig_parcial.update_layout(showlegend=False)
    comp.figura(fig_parcial, "2", "Partial relationship, controls residualised out",
                fuente="<b>Method:</b> both severity and the predictor are regressed on the "
                       "control set; the residuals are then regressed against each other. The "
                       "slope shown is the partial coefficient.")

comp.pie_de_hoja(
    "How it's computed: regress osi against the controls and keep what's left over (the "
    "residual); do the same for the variable of interest against the same controls; then "
    "regress one residual against the other. The slope of that last regression is, by the "
    "theorem itself, identical to the coefficient of the variable of interest in a full multiple "
    "regression with everything together."
)

comp.ver_tambien(["corr", "hyst", "models"])
comp.pie_sitio()

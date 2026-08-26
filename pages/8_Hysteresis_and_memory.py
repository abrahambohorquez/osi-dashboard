"""The centerpiece of the project: how the first wave leaves a county less
sensitive to the second, and how much memory OSI has hour to hour."""
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

df = comp.preparar_hoja(dict(page_title="Hysteresis and memory | OSI Analysis Desk",
                             layout="wide"), clave="hyst")

comp.encabezado_pagina(
    "Hysteresis and memory",
    "The finding that most changed the submitted model's design: infrastructure damaged in the "
    "first wave cannot fail the same way in the second, so comparable wind produces a smaller "
    "response the second time. Measured here two ways, by comparing per-county wave peaks and by "
    "how far back severity stays autocorrelated.",
)
comp.banner_datos_simulados()

st.markdown("""
<div class="finding tone-ink">
  <div class="flabel">What this means before the math</div>
  <p>
  "Hysteresis" just means the system remembers what already happened to it, so the same input
  doesn't always produce the same output. Think of a tree that lost its weakest branches in the
  first storm: a second storm with the exact same wind speed knocks down fewer branches, not
  because the wind was gentler, but because the branches that would have fallen already fell. A
  power grid behaves the same way: the poles and lines that were going to fail under a given gust
  speed mostly already failed in the first wave, so the second wave, even at similar intensity,
  breaks less. A model that treats every hour as a fresh start, with no memory of what came
  before, will keep expecting the second wave to hit as hard as the first, and keep being wrong.
  </p>
</div>
""", unsafe_allow_html=True)

comp.titulo_seccion("01", "First wave's peak against second wave's peak, by county")
mitad = df["hour_idx"].max() // 2
ola1 = df[df["hour_idx"] <= mitad].groupby("fipsCode")["osi"].max()
ola2 = df[df["hour_idx"] > mitad].groupby("fipsCode")["osi"].max()
nombres = df.drop_duplicates("fipsCode").set_index("fipsCode")["countyName"]

comparacion = pd.DataFrame({"pico_ola1": ola1, "pico_ola2": ola2}).dropna()
comparacion["condado"] = nombres.reindex(comparacion.index)

if len(comparacion) > 2:
    correlacion = comparacion["pico_ola1"].corr(comparacion["pico_ola2"])
    razon = (comparacion["pico_ola2"] / comparacion["pico_ola1"].replace(0, np.nan)).median()

    if correlacion < 0.3:
        nivel_hysteresis = "severe"
    elif correlacion < 0.6:
        nivel_hysteresis = "warning"
    elif correlacion < 0.85:
        nivel_hysteresis = "watch"
    else:
        nivel_hysteresis = "calm"
    comp.hallazgo(
        f"What the comparison between waves shows {comp.insignia_severidad(nivel_hysteresis)}",
        f"The correlation between wave 1's peak and wave 2's peak, county by county, is "
        f"<b>{correlacion:.3f}</b>. If the two waves were interchangeable, that correlation would "
        f"be close to 1. At the median, a county only repeats <b>{razon:.2f}x</b> of its first "
        "peak in the second wave: evidence that infrastructure already hit responds "
        "differently, it doesn't just persist.",
        tono="accent",
    )

    comp.fila_metricas([
        ("correlation between peaks", f"{correlacion:.3f}", "the closer to 0, the less alike the waves are", "ink"),
        ("median wave2 / wave1", f"{razon:.2f}x", "a typical county repeats this much of its first peak", "accent"),
        ("counties compared", f"{len(comparacion)}", "with data in both halves of the window", "ink"),
    ])

    comp.hallazgo(
        "Business read",
        "Crew and parts allocation planned off the first wave's severity map will overstate what "
        "the second wave needs almost everywhere. A static resource plan built for \"the storm\" "
        "as one event, instead of wave by wave, is planning for a second hit that mostly doesn't "
        "happen at the same scale.",
        tono="ok",
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=comparacion["pico_ola1"], y=comparacion["pico_ola2"], mode="markers",
                              marker=dict(color=theme.ACCENT, size=9, opacity=0.75, line=dict(color="white", width=1)),
                              text=comparacion["condado"],
                              hovertemplate="%{text}<br>wave 1: %{x:.3f}<br>wave 2: %{y:.3f}<extra></extra>"))
    maximo = max(comparacion["pico_ola1"].max(), comparacion["pico_ola2"].max()) * 1.05
    fig.add_trace(go.Scatter(x=[0, maximo], y=[0, maximo], mode="lines",
                              line=dict(color=theme.MUTED, dash="dot", width=1.3),
                              name="same severity in both waves", showlegend=True))
    theme.aplicar_tema(fig, altura=440)
    fig.update_xaxes(title_text="peak OSI, first half of the window")
    fig.update_yaxes(title_text="peak OSI, second half of the window")
    comp.figura(fig, "1", "First-wave peak against second-wave peak, one point per county",
                fuente="<b>Reading:</b> points below the diagonal are counties that peaked "
                       "lower in the second wave than the first. <b>Caution:</b> the two "
                       "waves are not identical in forcing, so the gap is an upper bound on "
                       "the attenuation attributable to prior damage.")
    st.caption(
        "Points below the dotted line had a milder second wave than the first, hysteresis's "
        "signature. If every point fell on the line, the two waves would be interchangeable and "
        "persistence alone would be enough."
    )
else:
    st.warning("Not enough counties with data in both halves of the window to compare.")

comp.titulo_seccion("02", "OSI's memory: autocorrelation by lag")
st.write(
    "How similar OSI right now is to 1, 6, 24 or 48 hours ago. This is the number that defines "
    "strategy: while memory stays high, persistence is enough; once it drops close to zero, the "
    "weather has to decide."
)

serie_agregada = df.groupby("hour_idx")["osi"].mean()
valores_acf = est.autocorrelacion(serie_agregada, nlags=72)
n_lags = len(valores_acf) - 1

fig2 = go.Figure()
fig2.add_trace(go.Bar(x=list(range(n_lags + 1)), y=valores_acf, marker_color=theme.INK))
fig2.add_hline(y=0, line_color=theme.BORDER, line_width=1)
theme.aplicar_tema(fig2, altura=380)
fig2.update_xaxes(title_text="lag (hours)")
fig2.update_yaxes(title_text="correlation")
comp.figura(fig2, "2", "Autocorrelation of regional mean severity, by lag",
            fuente="<b>Reading:</b> the lag at which the function crosses into the confidence "
                   "band is the practical horizon over which the last observed state still "
                   "carries information. This is what makes an anchored forecast viable at "
                   "t+1h and t+6h and progressively less so at t+48h.")

metricas_rezago = []
for h in (1, 6, 24, 48):
    if h <= n_lags:
        metricas_rezago.append((f"lag {h}h", f"{valores_acf[h]:.3f}", "", "ink"))
if metricas_rezago:
    comp.fila_metricas(metricas_rezago)

comp.ver_tambien(["map", "fwl", "models"])
comp.pie_sitio()

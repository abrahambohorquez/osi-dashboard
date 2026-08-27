"""Correlations and multicollinearity between weather variables."""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import estadistica as est
import theme

df = comp.preparar_hoja(dict(page_title="Correlations | OSI Analysis Desk", layout="wide"),
                        clave="corr")

comp.encabezado_pagina(
    "Correlations and multicollinearity",
    "Several of the supplied weather fields are near-linear combinations of others, which is "
    "harmless for a tree ensemble's predictions and fatal for any reading of its variable "
    "importances. This page measures how much of that redundancy the file actually contains.",
)
comp.banner_datos_simulados()

candidatas = [v for v in ["gust", "wind_speed_10m", "t2m", "d2m", "r2", "mslma", "sp",
                          "tp", "rain", "csnow", "blh", "soil_moist", "osi"] if v in df.columns]

comp.titulo_seccion("01", "Correlation matrix")
comp.entradilla(
    "Pearson correlation across the weather predictors and severity, over all county-hours in "
    "the active file. Pairs close to +/-1 are the ones to check on the variance inflation table "
    "below; a strong correlation with severity is a starting point, not evidence of an "
    "independent effect."
)
corr = df[candidatas].corr()
fig = go.Figure(data=go.Heatmap(
    z=corr.values, x=corr.columns, y=corr.columns,
    colorscale=theme.DIVERGENTE, zmin=-1, zmax=1, colorbar=dict(title="r"),
))
theme.aplicar_tema(fig, altura=520)
fig.update_layout(xaxis=dict(tickangle=45))
comp.figura(fig, "1", "Pearson correlation, weather predictors and severity",
            fuente="<b>Source:</b> all county-hours of the active file. <b>Caution:</b> "
                   "wind direction is circular and must be encoded as sine and cosine before "
                   "any linear statistic is read from it.")

comp.titulo_seccion("02", "Variance inflation factor (VIF)")
st.write(
    "A high VIF on a variable means it can be predicted almost perfectly from the others: a "
    "sign of a hidden identity, not just a strong correlation."
)

variables_vif = [v for v in candidatas if v != "osi"]
tabla_vif = est.tabla_vif(df, variables_vif)

if not tabla_vif.empty:
    peor = tabla_vif.iloc[0]
    peor_vif_texto = "infinite" if peor["VIF"] == float("inf") else f"{peor['VIF']:.1f}"
    if peor["VIF"] > 20:
        comp.hallazgo(
            f"{peor['variable']} has a VIF of {peor_vif_texto}: likely a hidden identity",
            f"'<b>{peor['variable']}</b>' has the highest VIF in the table ({peor_vif_texto}). "
            "In the challenge's real data this happens because tp = rain + csnow and "
            "sdswrf = direct_rad + diffuse_rad are exact identities, not coincidences. It's worth "
            "checking whether the same relationship shows up here before leaving both variables "
            "loose in a linear model.",
            tono="warn",
            destacado=True,
        )
    st.dataframe(tabla_vif.round(2), width="stretch", hide_index=True)
    comp.hallazgo(
        "Where a redundant weather feed could be cut",
        "If a weather feed costs money or a monitoring contract charges per variable, a high-VIF "
        "pair is a place to cut: dropping the redundant one loses almost no predictive signal, "
        "because a model can already reconstruct it from the variable you kept.",
        tono="ok",
    )
else:
    st.warning("Not enough rows or variables with variation to compute VIF.")

comp.pie_de_hoja(
    "A decision tree (LightGBM, XGBoost) doesn't break with a high VIF the way a linear "
    "regression does, but it's still worth knowing which variables are redundant before "
    "interpreting which ones matter most."
)

comp.ver_tambien(["fwl", "dist", "series"])
comp.pie_sitio()

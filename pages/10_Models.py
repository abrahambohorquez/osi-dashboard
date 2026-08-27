"""Reserved space for the final models' results.

Once the team has v11_basic / V11-TailGuard settled (or whatever ends up being
submitted), this is where those results land: you can load a CSV with
predictions and compare it directly against the real osi in the loaded data,
without building anything new.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import theme

df = comp.preparar_hoja(dict(page_title="Model results | OSI Analysis Desk", layout="wide"),
                        clave="models")

comp.encabezado_pagina(
    "Model results",
    "No results are published on this page yet: variant selection is still open. The comparison "
    "machinery is in place, so uploading a predictions file with the columns listed below "
    "produces the horizon-by-horizon error breakdown without any further work.",
)

st.markdown("""
<div class="finding tone-accent">
  <div class="flabel">What lands here once variant selection closes</div>
  <p>
  RMSE and MAE by horizon (t+1h, t+6h, t+24h, t+48h) for each version tested.<br>
  The error breakdown by severity_tier, which is where the idea for V11-TailGuard came from.<br>
  The comparison of v11_basic against the version with the tail-correction layer.
  </p>
</div>
""", unsafe_allow_html=True)

comp.titulo_seccion("01", "Upload predictions to compare")
st.caption(
    "The file needs fipsCode, hour_idx (or timestamp_et), and a predicted_osi column. If the "
    "file loaded under Data & docs has the real osi for those same rows, the site computes "
    "the error directly."
)
archivo_pred = st.file_uploader("Predictions CSV", type=["csv"], key="pred_upload")

if archivo_pred is not None:
    try:
        pred = pd.read_csv(archivo_pred)
    except Exception as err:
        st.error(f"Couldn't read the file: {err}")
        pred = None

    if pred is not None:
        columnas_necesarias = {"fipsCode", "hour_idx", "predicted_osi"}
        if not columnas_necesarias.issubset(pred.columns):
            st.error(f"This file is missing columns: {columnas_necesarias - set(pred.columns)}")
        else:
            comparado = pred.merge(df[["fipsCode", "hour_idx", "osi"]], on=["fipsCode", "hour_idx"], how="inner")
            if comparado.empty:
                st.warning("No rows in common between the predictions and the currently loaded data.")
            else:
                comparado["error"] = comparado["predicted_osi"] - comparado["osi"]
                rmse = float(np.sqrt((comparado["error"] ** 2).mean()))
                mae = float(comparado["error"].abs().mean())

                comp.fila_metricas([
                    ("RMSE", f"{rmse:.5f}", "", "ok"),
                    ("MAE", f"{mae:.5f}", "", "ok"),
                    ("rows compared", f"{len(comparado):,}", "", "ink"),
                ])

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=comparado["osi"], y=comparado["predicted_osi"], mode="markers",
                                          marker=dict(color=theme.ACCENT, size=6, opacity=0.5)))
                maximo = max(comparado["osi"].max(), comparado["predicted_osi"].max()) * 1.05
                fig.add_trace(go.Scatter(x=[0, maximo], y=[0, maximo], mode="lines",
                                          line=dict(color=theme.MUTED, dash="dot")))
                theme.aplicar_tema(fig, altura=420)
                fig.update_xaxes(title_text="real osi")
                fig.update_yaxes(title_text="predicted osi")
                comp.figura(fig, "1", "Observed against predicted severity",
                            fuente="<b>Reference:</b> the diagonal is perfect agreement. "
                                   "Systematic departure below it at high values is tail "
                                   "underprediction, the failure mode this project is most "
                                   "concerned with.")
else:
    st.caption("No predictions file has been uploaded yet in this session.")

comp.ver_tambien(["dist", "hyst", "refs"])
comp.pie_sitio()

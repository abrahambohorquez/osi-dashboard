"""Page to upload your own file, or go back to the simulated data."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import schema
import theme

df = comp.preparar_hoja(dict(page_title="Load data | OSI Analysis Desk", layout="wide"),
                        clave="load")

comp.encabezado_pagina(
    "Load data",
    "Replace the synthetic sample with a record of your own. The file is validated against the "
    "column set every page depends on and rejected outright if anything is missing; partial "
    "files are not padded or imputed. An accepted upload becomes the input for the whole site "
    "until the session ends.",
)
comp.banner_datos_simulados()

st.markdown("""
<div class="finding tone-ink">
  <div class="flabel">Structurally similar to the challenge file, numerically unrelated to it</div>
  <p>
  A few numbers are shared between the simulated file and the real challenge on purpose: 216
  hours per county, an anchor at hour 71, and the OSI formula itself. Those aren't measurements
  from the real dataset, they're the challenge's own public rules, the same way "a chess board has
  64 squares" isn't a secret about any specific game. Reusing them doesn't leak anything.<br><br>
  Everything else, every county name, every coordinate, every weather value, every outage number,
  is generated from scratch by <code>simular_datos.py</code> with its own random storm physics.
  No cell in that file was read from, fitted to, or derived from <code>DM_Train.csv</code>. It's
  built to be structurally comparable (same columns, same kind of two-wave storm shape), not
  numerically related.
  </p>
</div>
""", unsafe_allow_html=True)

col_izq, col_der = st.columns([1.3, 1], gap="large")

with col_izq:
    st.markdown("#### Upload a file")
    st.caption(
        "This lasts only for your current browser session, on purpose: nothing you upload is "
        "saved to disk. If you refresh the page, open a new tab, or come back later, it resets "
        "to the simulated demo and you'll need to upload again."
    )
    archivo = st.file_uploader("CSV file", type=["csv"], label_visibility="collapsed")

    if archivo is not None:
        try:
            df_nuevo = pd.read_csv(archivo)
        except Exception as err:
            st.error(f"Couldn't read the file as CSV: {err}")
            df_nuevo = None

        if df_nuevo is not None:
            if "timestamp_et" in df_nuevo.columns:
                df_nuevo["timestamp_et"] = pd.to_datetime(df_nuevo["timestamp_et"], errors="coerce")
            df_nuevo = schema.derivar_hour_idx(df_nuevo)
            faltantes = schema.validar_columnas(df_nuevo)
            if faltantes:
                st.error("This file is missing columns the dashboard needs: " + ", ".join(faltantes))
            else:
                st.session_state.df = df_nuevo
                st.session_state.fuente = "propio"
                resumen = schema.resumen_condados(df_nuevo)
                st.success(
                    f"Loaded: {resumen['n_filas']:,} rows, {resumen['n_condados']} counties, "
                    f"states {', '.join(resumen['estados'])}."
                )
                st.rerun()

    st.write("")
    if st.button("Go back to simulated data", type="secondary"):
        st.session_state.df = schema.cargar_datos_simulados()
        st.session_state.fuente = "simulados"
        st.rerun()

with col_der:
    st.markdown("#### Columns required")
    st.caption("The file can have more columns than these, but not fewer.")
    st.code("\n".join(schema.COLUMNAS_REQUERIDAS), language="text")
    st.caption(
        "Optional, for extra pages: " + ", ".join(schema.COLUMNAS_OPCIONALES) +
        ". Without posicion_x / posicion_y, and without a real US fipsCode, the map page can't "
        "draw anything. If the file has no hour_idx but does have timestamp_et, it gets computed "
        "automatically (hours since the start of the file), no need to add it by hand."
    )

st.markdown('<hr class="thin">', unsafe_allow_html=True)
st.markdown("#### Preview of what's currently loaded")
resumen = schema.resumen_condados(df)
comp.fila_metricas([
    ("counties", str(resumen["n_condados"]), "in this file", "ink"),
    ("rows", f"{resumen['n_filas']:,}", "", "ink"),
    ("hours per county", str(resumen["n_horas"]), "", "ink"),
    ("active source", "simulated" if st.session_state.get("fuente") == "simulados" else "your own file", "", "accent"),
])
st.dataframe(df.head(200), width="stretch", height=360)

comp.nota_fuente(
    "<b>Retention:</b> uploads are held in Streamlit session state only. Nothing is written to "
    "disk, nothing is logged, and no challenge data is committed to this repository at any point."
)
comp.ver_tambien(["home", "map", "dist"])
comp.pie_sitio()

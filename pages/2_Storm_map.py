"""The storm map: real US counties and the 3D relief, both auto-playing,
plus a synced hour explorer. Formerly split across two pages (Storm map /
Cinematic view); merged into one once both pieces worked equally well, so
there's a single best version instead of two near-duplicates."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy.signal import argrelextrema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import estadistica as est
import geo_condados
import theme
import viz

df = comp.preparar_hoja(dict(page_title="Storm field analysis | OSI Analysis Desk",
                             layout="wide"), clave="map")

comp.encabezado_pagina(
    "Storm field analysis",
    "Severity across the four-state area for every hour of the window, drawn on Census county "
    "boundaries and, below, as a relief surface. Both animate through the window unattended. "
    "Rendering uses Plotly's built-in geometry, so no map service, token or account is required "
    "anywhere on this page.",
)
comp.banner_datos_simulados()

if not viz.tiene_posiciones_disponibles(df):
    st.warning(
        "This file doesn't include posicion_x / posicion_y, and its fipsCode values don't match "
        "real US counties either, so this page can't place anything on a plane. The rest of the "
        "dashboard still works. Files with real fipsCode get their position computed "
        "automatically from the real county's location, no extra columns needed."
    )
    st.stop()

tope_osi = max(float(df["osi"].max()), 1e-6)

variables_disponibles = [v for v in theme.ETIQUETAS_VARIABLE if v in df.columns]
col_ctrl1, col_ctrl2 = st.columns([1, 1])
with col_ctrl1:
    paso = st.selectbox("Show a frame every", [1, 2, 3, 4, 6], index=2,
                         format_func=lambda h: f"{h} hour{'s' if h > 1 else ''}")
with col_ctrl2:
    variable_mapa = st.selectbox("Field variable", variables_disponibles,
                                  index=variables_disponibles.index("osi") if "osi" in variables_disponibles else 0,
                                  format_func=lambda v: theme.ETIQUETAS_VARIABLE.get(v, v))

comp.titulo_seccion("01", "Severity on real county boundaries")

geo_real = geo_condados.obtener_geometrias() if geo_condados.hay_cache() else None
if geo_real is None:
    st.info(
        "The county boundary cache (data/condados_reales_reto.geojson) is missing or could "
        "not be read, so this map is skipped. The file ships with the repository; if it was "
        "deleted, regenerating it requires internet once. The relief below still works."
    )
else:
    n_match, n_condados_propios = geo_condados.cobertura(df, geo_real)
    tiene_geo_real = n_match >= 5
    if tiene_geo_real:
        st.write(
            f"This file's {n_match} counties have real US fipsCode values, so this is drawn on "
            "their actual county boundaries (Census TIGER/Line)."
        )
        df_mapa = df
        geo_cruzado = geo_condados.emparejar(df_mapa, geo_real)
    else:
        st.write(
            "This file's counties are simulated, so each one is assigned to a real county shape "
            "in Indiana, Ohio, Pennsylvania or West Virginia, just to give the severity a "
            "recognizable map to sit on. The named county is a borrowed shape, not a claim about "
            "what actually happened there; upload the real challenge file to see real counties "
            "with their real severity instead."
        )
        asignacion = geo_condados.asignar_condados_reales(df["fipsCode"].unique().tolist(), geo_real)
        df_mapa = df.copy()
        df_mapa["fipsCode"] = df_mapa["fipsCode"].map(asignacion)
        geo_cruzado = geo_condados.emparejar(df_mapa, geo_real)

    fig_geo = viz.figura_mapa_geografico(df_mapa, geo_cruzado, variable=variable_mapa, paso_horas=paso)
    if fig_geo is not None:
        comp.marco_figura("1", f"{theme.ETIQUETAS_VARIABLE.get(variable_mapa, variable_mapa)} "
                               "by county, animated through the window")
        comp.figura_autoreproducida(fig_geo, altura=760, duracion_ms=160)
        comp.nota_fuente(
            "<b>Boundaries:</b> US Census TIGER/Line county polygons, cached locally. "
            "<b>Fill scale:</b> the same five-category ramp as the severity ribbon; an orange "
            "county here sits on the orange step there."
        )
    else:
        st.info("Not enough distinct hours to animate this map at the current frame step.")

comp.titulo_seccion("02", "Severity as a relief surface")
comp.entradilla(
    "The same field, with severity mapped to height instead of fill. Vertical relief separates "
    "the two waves more clearly than color alone, because a moderate second peak stays visibly "
    "lower than a high first peak where two similar fills would not. The camera orbits "
    "continuously; the chart's own pause control stops it."
)

fig_anim = viz.figura_tormenta_3d(df, variable=variable_mapa, paso_horas=paso)
if fig_anim is None:
    st.info("Not enough distinct hours to animate at this frame step.")
else:
    comp.marco_figura("2", "The same field as a relief surface, camera orbiting")
    comp.figura_autoreproducida(fig_anim, altura=760, duracion_ms=140)
    comp.nota_fuente(
        "<b>Height and fill:</b> both encode the selected variable, deliberately, so the "
        "legend reads once for both maps. The wave call-outs below are located automatically "
        "as local maxima of the regional mean, not from a hard-coded date."
    )

serie_agg = df.groupby("hour_idx")["osi"].mean()
picos_idx = argrelextrema(serie_agg.values, np.greater_equal, order=6)[0]
picos_idx = [i for i in picos_idx if serie_agg.values[i] > serie_agg.values.mean()]
if picos_idx:
    horas_pico = serie_agg.index.to_numpy()[picos_idx]
    for i, h in enumerate(horas_pico[:2], start=1):
        n_activos = int((df[df["hour_idx"] == h]["osi"] > df["osi"].quantile(0.5)).sum())
        valor_pico = float(serie_agg.loc[h])
        # Un solo sitio decide que categoria corresponde a un OSI dado, para
        # que este aviso nunca discrepe de la cinta de la portada.
        nivel_ola = theme.nivel_para_osi(valor_pico)
        comp.banner_evento(
            f"{comp.insignia_severidad(nivel_ola)} WAVE {i} PEAK &middot; hour {int(h)} "
            f"&middot; regional mean OSI {valor_pico:.3f} "
            f"&middot; {n_activos} counties above the file median"
        )

espacial = est.morans_i(df, "osi") if "osi" in df.columns else None
if espacial is None:
    df_pico = df.copy()
    df_pico["osi_pico_condado"] = df_pico.groupby("fipsCode")["osi"].transform("max")
    espacial = est.morans_i(df_pico, "osi_pico_condado")
if espacial:
    agrupado = espacial["I"] > espacial["esperado_bajo_azar"] + 0.05
    tono_espacial = "accent" if agrupado else "ink"
    titulo_espacial = (
        f"Moran's I of {espacial['I']:.3f}: the storm moves, it does not strike at random"
        if agrupado else
        f"Moran's I of {espacial['I']:.3f}: little spatial clustering in this file"
    )
    comp.hallazgo(
        titulo_espacial,
        f"Each county's peak severity has a Moran's I of <b>{espacial['I']:.3f}</b>, against "
        f"{espacial['esperado_bajo_azar']:.3f} expected under pure chance. A value clearly above "
        "chance means neighboring counties resemble each other more than randomness would allow, "
        "which is what a weather system sweeping the region produces and what a model can exploit "
        "through spatial features.",
        tono=tono_espacial,
    )

comp.titulo_seccion("03", "Single-hour detail")
comp.entradilla(
    "Hold the field at one hour to read the county ranking behind it. The reference line on the "
    "right marks the selected hour against the regional mean, so an apparently severe hour that "
    "is really a local outlier is visible as such."
)

hora_sel = st.slider("Hour since the start of the window", int(df["hour_idx"].min()), int(df["hour_idx"].max()),
                      value=int(df["hour_idx"].median()), key="hora_explorador")

snap = df[df["hour_idx"] == hora_sel].copy()

col_tabla, col_curva = st.columns([1, 1.2], gap="large")
with col_tabla:
    st.markdown("**Hardest-hit counties this hour**")
    top = snap.sort_values("osi", ascending=False).head(8)[["countyName", "stateAbbr", "osi"]]
    top = top.rename(columns={"countyName": "county", "stateAbbr": "state", "osi": "OSI"})
    st.dataframe(top.round(4), width="stretch", hide_index=True, height=310)

with col_curva:
    ts = df.groupby("hour_idx")["osi"].mean()
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=ts.index, y=ts.values, mode="lines", line=dict(color=theme.INK, width=2),
                                fill="tozeroy", fillcolor="rgba(10,36,114,0.08)"))
    fig_ts.add_vline(x=hora_sel, line_color=theme.WARN, line_width=2)
    theme.aplicar_tema(fig_ts, altura=310)
    fig_ts.update_xaxes(title_text="hour index")
    fig_ts.update_yaxes(title_text=None)
    comp.figura(fig_ts, "3", "Regional mean OSI across the window, selected hour marked",
                fuente="<b>Source:</b> unweighted mean across all counties in the active file. "
                       "<b>Marker:</b> the hour selected above.")

comp.pie_de_hoja(
    "Moran's I uses a distance-decay weight matrix over county positions; References lists the "
    "source of the statistic. With simulated data, county shapes are borrowed real boundaries, "
    "labeled as such above the map."
)
comp.ver_tambien(["series", "patterns", "hyst"])
comp.pie_sitio()

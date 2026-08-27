"""Multivariate patterns: views that look at several variables and several
counties at once, instead of one variable or one county at a time."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import theme
import viz_patterns as vp

df = comp.preparar_hoja(dict(page_title="Multivariate patterns | OSI Analysis Desk",
                             layout="wide"), clave="patterns")

comp.encabezado_pagina(
    "Multivariate patterns",
    "Four views that read several variables and several counties at once, rather than one at a "
    "time: the county cloud in motion, which weather conditions co-occur, which counties share a "
    "trajectory, and how a gust band escalates into a severity band. All four are recomputed "
    "from the active file.",
)
comp.banner_datos_simulados()

comp.titulo_seccion("01", "County cloud in motion")
comp.entradilla(
    "Gust against severity, one marker per county, sized by customers tracked and colored by "
    "state, one frame per hour. What a single county's line chart cannot show is the shape of "
    "the whole cloud: whether the region moves together or splits, and whether the "
    "gust-to-severity relationship holds at the same slope throughout the window. Starts on its "
    "own; use the pause button on the chart to hold a frame."
)

fig_burbujas = vp.figura_burbujas_animada(df, paso_horas=3)
if fig_burbujas is not None:
    comp.marco_figura("1", "Gust against severity, by county, through the window")
    comp.figura_autoreproducida(fig_burbujas, altura=480, duracion_ms=450)
    comp.nota_fuente("<b>Source:</b> active file. <b>Marker size:</b> customersTracked. "
                     "<b>Color:</b> state.")
else:
    st.info("This file is missing one of gust, osi, customersTracked or stateAbbr.")

comp.titulo_seccion("02", "Parallel coordinates")
st.write(
    "Each line is one county-hour, threaded through every weather variable at once, colored by "
    "OSI. A single scatter plot can only ever show two variables against each other; this shows "
    "all of them together, so a combination of conditions, not just one variable in isolation, "
    "can stand out as the one that precedes severity."
)
variables_parcoords = ["gust", "wind_speed_10m", "mslma", "tp", "rain", "csnow", "soil_moist", "r2", "osi"]
fig_parcoords = vp.figura_coordenadas_paralelas(df, variables_parcoords, color_var="osi")
if fig_parcoords is not None:
    comp.figura(fig_parcoords, "2", "Parallel coordinates across weather predictors and severity",
                fuente="<b>Reading:</b> each line is one county-hour. Axis order is fixed; "
                       "crossing lines indicate an inverse relationship between adjacent axes.")
    st.caption(
        "Drag along any axis to filter to a range. Lines that stay bright (high OSI) across "
        "several axes at once are showing you a real combination, not a coincidence on one variable."
    )
else:
    st.info("Not enough weather columns in this file to draw parallel coordinates.")

comp.titulo_seccion("03", "Which counties behave alike")
st.write(
    "Counties reordered by a real hierarchical clustering of their hour-by-hour OSI profile "
    "(average-linkage, Euclidean distance), with the dendrogram alongside so the grouping is "
    "visible, not just claimed. Time is never reordered, only the counties: reading left to "
    "right still tells the story of the storm."
)
fig_heatmap = vp.figura_heatmap_agrupado(df, variable="osi")
if fig_heatmap is not None:
    comp.figura(fig_heatmap, "3", "Counties clustered by severity trajectory, with dendrogram",
                fuente="<b>Method:</b> average-linkage hierarchical clustering on each county's "
                       "hourly severity vector. <b>Note:</b> only rows are reordered; the time "
                       "axis is never sorted.")
    comp.hallazgo(
        "Counties that cluster together can share crews and stock",
        "Counties that cluster together on this chart are candidates for a shared operational "
        "plan: if their severity rises and falls together hour by hour, they can share a crew "
        "dispatch schedule or a regional stockpile of repair parts, instead of planning for each "
        "county in isolation.",
        tono="accent",
    )
else:
    st.info("Not enough counties or hours in this file to cluster.")

comp.titulo_seccion("04", "How a gust becomes a severity band")
st.write(
    "A Sankey diagram of the escalation path: gust intensity, into how fast new failures pile up "
    "(N_t), into the resulting OSI band. Each one alone is a chart already elsewhere in this "
    "dashboard; seeing them as one flow shows how the effect compounds instead of just correlating. "
    "Color is the same severity scale used everywhere else in the dashboard, calm to white, severe "
    "to red, so the flow visibly reddens left to right instead of three unrelated block colors."
)
fig_sankey = vp.figura_sankey_severidad(df)
if fig_sankey is not None:
    comp.figura(fig_sankey, "4", "Escalation from gust band to severity category",
                fuente="<b>Reading:</b> band widths are county-hour counts, not customers. "
                       "A wide flow into a low category means a gust band that mostly did not "
                       "translate into outages.")
    st.caption(
        "Hover a band or a link to see how many county-hours took that path. Bands are quantile "
        "cuts (roughly equal-sized groups) of gust, N_t and OSI in this specific file, not fixed "
        "thresholds, so the split adjusts to whatever is loaded."
    )
else:
    st.info("This file is missing gust, N_t or osi, so the flow can't be built.")

comp.pie_de_hoja(
    "All four views are computed live on whatever file is loaded, simulated or your own: the "
    "clusters, the quantile bands, and the bubble ranges are never fixed numbers from one "
    "specific dataset, they're recalculated from the active file every time."
)

comp.ver_tambien(["map", "corr", "hyst"])
comp.pie_sitio()

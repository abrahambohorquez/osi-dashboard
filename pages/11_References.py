"""Credits, acknowledgments, and the references behind the methods this
dashboard actually uses."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import theme

comp.preparar_hoja(dict(page_title="References | OSI Analysis Desk", layout="wide"),
                   clave="refs")

comp.encabezado_pagina(
    "References and credits",
    "Every statistical method computed anywhere on this site, with its primary source. A "
    "method appears here only if some page actually runs it.",
    con_datos=False,
)

comp.titulo_seccion("01", "Team")
st.markdown("""
<div class="card">
<p style="font-size:15px; line-height:1.9; margin:0;">
<b>Abraham Jesus Bohorquez Gomez</b><br>
<b>Paula Andrea Torres Prieto</b><br>
<b>Esteban Ladino Nieto</b><br>
<b>Juan Jose Murillo Aristizabal</b><br>
<span style="color:#6E8898;">Department of Industrial Engineering, Universidad de los Andes</span>
</p>
</div>
""", unsafe_allow_html=True)

st.write("")
comp.titulo_seccion("02", "The paper")
comp.cita("Forecasting Storm-Driven Outage Severity: A Regime-Gated Mixture of Experts Anchored on the Last Observed State")
st.write(
    "The Overfitters, submitted to the INFORMS 2026 Data Mining Society Data Challenge, September "
    "2026. This dashboard is the exploratory and explanatory companion to that paper: every "
    "statistic it computes (Moran's I, Frisch-Waugh-Lovell, VIF, hysteresis, the zero-inflation "
    "diagnostics) is the same method the paper describes, run live on whatever file is loaded here, "
    "not a copy of the paper's own numbers."
)

comp.titulo_seccion("03", "Acknowledgments")
st.write(
    "This project was carried out at Universidad de los Andes, in the Department of Industrial "
    "Engineering."
)

comp.titulo_seccion("04", "References")
st.write("One entry per method, each with a note on which page runs it.")

referencias = [
    ("Frisch, R. and Waugh, F. V. (1933).",
     "Partial Time Regressions as Compared with Individual Trends. <i>Econometrica</i>, 1(4), 387-401.",
     "The theorem behind the \"Frisch-Waugh-Lovell\" page: how a partial effect is recovered by "
     "residualizing and regressing residuals against each other."),
    ("Lovell, M. C. (1963).",
     "Seasonal Adjustment of Economic Time Series and Multiple Regression Analysis. "
     "<i>Journal of the American Statistical Association</i>, 58(304), 993-1010.",
     "The extension that gives the theorem its full name and its modern statement."),
    ("Moran, P. A. P. (1950).",
     "Notes on Continuous Stochastic Phenomena. <i>Biometrika</i>, 37(1/2), 17-23.",
     "The original definition of the spatial autocorrelation statistic (Moran's I) computed on "
     "the Storm field analysis and Multivariate patterns pages."),
    ("Lawrence Berkeley National Laboratory, LBNL-54365.",
     "Value of Service Reliability for Electric Utility Customers.",
     "The meta-analysis of real interruption-cost surveys behind the residential, commercial and "
     "industrial dollar rates used on the Costs page."),
    ("Bohorquez Gomez, A. J., Torres Prieto, P. A., Ladino Nieto, E., and Murillo Aristizabal, J. J. (2026).",
     "Forecasting Storm-Driven Outage Severity: A Regime-Gated Mixture of Experts Anchored on the "
     "Last Observed State. INFORMS 2026 Data Mining Society Data Challenge.",
     "The team's own paper: the OSI formula, the anchor-and-horizon setup, and the diagnostics "
     "this whole dashboard walks through in more depth."),
]

for autor, cita, nota in referencias:
    st.markdown(f"""
    <div style="margin:0 0 18px; padding:0 0 16px; border-bottom:1px solid {theme.BORDER};">
      <div style="font-size:14px; color:{theme.INK};"><b>{autor}</b> {cita}</div>
      <div style="font-size:12.5px; color:{theme.MUTED}; margin-top:5px;">{nota}</div>
    </div>
    """, unsafe_allow_html=True)

comp.pie_de_hoja(
    "This dashboard's own code (theme, components, statistics, the storm map, the simulated data "
    "generator) is original work built for this project, not adapted from a third-party template."
)

comp.titulo_seccion("05", "Design note")
comp.entradilla(
    "The visual language of this site borrows the publication conventions of United States "
    "weather agencies: the numbered categorical severity scale and its pastel fills follow the "
    "Storm Prediction Center's convective outlook; the advisory blocks and the all-capitals "
    "product headline follow National Hurricane Center text products; the utility strip, "
    "breadcrumb trail and grouped section index follow weather.gov office pages; the figure "
    "numbering and source lines follow the Insurance Information Institute's fact-statistic "
    "format. No agency seal, logo, wordmark or domain is reproduced, and nothing published here "
    "is an operational forecast."
)
comp.ver_tambien(["home", "models", "load"])
comp.pie_sitio()

"""Translates severity into an approximate dollar cost, broken down by
customer segment so the business impact is visible, not just a single
blended number."""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import components as comp
import schema
import theme

df = comp.preparar_hoja(dict(page_title="Cost estimate | OSI Analysis Desk", layout="wide"),
                        clave="costs")

comp.encabezado_pagina(
    "Estimated cost by customer segment",
    "Customer-hours without power, priced at published interruption-cost rates. Residential, "
    "commercial and industrial customers differ by more than an order of magnitude per "
    "outage-hour and hold very different shares of the grid, so they are kept separate rather "
    "than blended into a single figure. Treat the total as an order of magnitude, not an "
    "estimate of losses.",
)
comp.banner_datos_simulados()

if "P_t" not in df.columns or "customersTracked" not in df.columns:
    st.warning("This file doesn't include P_t or customersTracked, so cost can't be estimated.")
    st.stop()

st.markdown(f"""
<div class="finding tone-accent">
  <div class="flabel">One multiplication, summed over every county-hour</div>
  <p>
  For every county and every hour: <b>(customers without power) x (a dollar rate per
  customer-hour)</b> = the dollar cost of that one hour, for that one county. Add that up across
  every hour and every county in the window and you get the total on this page. That's the whole
  calculation; the rest of this page is about what dollar rate to use for which kind of customer,
  and being upfront that it's an estimate, not an invoice.
  </p>
</div>
""", unsafe_allow_html=True)

comp.titulo_seccion("01", "Where these numbers come from")
st.markdown(f"""
<div class="finding tone-ink">
  <div class="flabel">Sourcing</div>
  <p>
  Cost-per-customer-hour rates: <b>LBNL-54365</b> (Lawrence Berkeley National Laboratory,
  "Value of Service Reliability for Electric Utility Customers"), a meta-analysis of real
  utility interruption-cost surveys. Figures are reported in <b>2002 USD</b>, not adjusted for
  inflation by default.<br><br>
  Customer-mix split (what share of customersTracked is residential vs. commercial vs.
  industrial): the data doesn't report this per meter, so the page uses a stated, adjustable
  assumption based on typical US utility meter mixes (roughly 85-90% residential meters is the
  common industry figure). Move the sliders below to match a real utility's mix if you have one.
  </p>
</div>
""", unsafe_allow_html=True)

TARIFAS_2002 = {
    "residential": 3.00,
    "commercial": 1200.00,
    "industrial": 82000.00,
}
FACTOR_INFLACION_2026 = 1.9  # approximate, US CPI 2002 -> 2026, rounded for transparency

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    pct_residencial = st.slider("% residential meters", 0, 100, 88)
with col_b:
    max_comercial = 100 - pct_residencial
    pct_comercial = st.slider("% commercial meters", 0, max_comercial, min(11, max_comercial))
with col_c:
    pct_industrial = 100 - pct_residencial - pct_comercial
    st.metric("% industrial meters", f"{pct_industrial}%", help="Whatever is left after residential and commercial.")
with col_d:
    ajustar_inflacion = st.checkbox("Adjust to ~2026 USD", value=False,
                                    help=f"Multiplies 2002 rates by {FACTOR_INFLACION_2026}x, an approximate "
                                        "US CPI adjustment. Off by default so the number you see matches the "
                                        "source exactly.")

factor = FACTOR_INFLACION_2026 if ajustar_inflacion else 1.0
tarifas = {k: v * factor for k, v in TARIFAS_2002.items()}
mezcla = {"residential": pct_residencial / 100, "commercial": pct_comercial / 100, "industrial": pct_industrial / 100}

df_costo = df.copy()
sin_luz = df_costo["P_t"].fillna(0) * df_costo["customersTracked"]
for segmento, participacion in mezcla.items():
    df_costo[f"cost_{segmento}"] = sin_luz * participacion * tarifas[segmento]
df_costo["cost_total"] = sum(df_costo[f"cost_{s}"] for s in mezcla)

serie_por_segmento = {s: df_costo.groupby("hour_idx")[f"cost_{s}"].sum() for s in mezcla}
serie_total = df_costo.groupby("hour_idx")["cost_total"].sum()
total = float(serie_total.sum())
pico = float(serie_total.max())
hora_pico = int(serie_total.idxmax())

st.write("")
comp.titulo_seccion("02", "Total impact, split by segment")
cols = st.columns(4)
tonos = {"residential": "ink", "commercial": "accent", "industrial": "warn"}
for col, segmento in zip(cols[:3], mezcla):
    total_segmento = float(serie_por_segmento[segmento].sum())
    share = 100 * total_segmento / total if total > 0 else 0
    # Redondear 0.28% a "0%" bajo una cifra de 88 millones de dolares se
    # lee como un error, porque lo es: un analista escribe "<1%".
    share_texto = "<1" if 0 < share < 1 else f"{share:.0f}"
    col.markdown(f"""
    <div class="mcard tone-{tonos[segmento]}">
      <div class="lbl">{segmento}</div>
      <div class="val">${total_segmento:,.0f}</div>
      <div class="sub">{share_texto}% of total cost, {mezcla[segmento]*100:.0f}% of meters</div>
    </div>
    """, unsafe_allow_html=True)
cols[3].markdown(f"""
<div class="mcard tone-accent">
  <div class="lbl">total, whole window</div>
  <div class="val">${total:,.0f}</div>
  <div class="sub">worst hour: ${pico:,.0f} at hour {hora_pico}</div>
</div>
""", unsafe_allow_html=True)

industrial_share = float(serie_por_segmento["industrial"].sum()) / total * 100 if total > 0 else 0
industrial_meters = mezcla["industrial"] * 100
if industrial_share > industrial_meters * 2 and total > 0:
    comp.hallazgo(
        f"{industrial_meters:.0f}% of meters carry {industrial_share:.0f}% of the estimated cost",
        "A regional average OSI can look mild while a handful of large industrial accounts "
        "absorb most of the dollar impact. That concentration, not the blended total, is the "
        "operational story here, and it is why the page reports each segment separately.",
        tono="warn",
    )

fig = go.Figure()
colores_segmento = {"residential": theme.INK, "commercial": theme.ACCENT, "industrial": theme.WARN}
for segmento in mezcla:
    fig.add_trace(go.Scatter(x=serie_por_segmento[segmento].index, y=serie_por_segmento[segmento].values,
                              mode="lines", name=segmento, stackgroup="costo",
                              line=dict(width=1.5, color=colores_segmento[segmento])))
fig.add_vline(x=schema.ANCLA_H, line_dash="dash", line_color=theme.WARN, line_width=1.2)
theme.aplicar_tema(fig, altura=400)
fig.update_yaxes(title_text="USD per hour")
comp.figura(fig, "1", "Estimated cost per hour by segment, summed across counties",
            fuente="<b>Rates:</b> Lawrence Berkeley National Laboratory LBNL-54365, a "
                   "meta-analysis of utility interruption-cost surveys. <b>Caveat:</b> rates "
                   "are national averages applied uniformly; no regional or seasonal "
                   "adjustment is made.")

comp.titulo_seccion("03", "Costliest counties")
ranking = (df_costo.groupby(["fipsCode", "countyName"])[["cost_residential", "cost_commercial", "cost_industrial", "cost_total"]]
           .sum().reset_index().sort_values("cost_total", ascending=False).head(15))
ranking = ranking.rename(columns={"countyName": "county", "cost_residential": "residential (USD)",
                                  "cost_commercial": "commercial (USD)", "cost_industrial": "industrial (USD)",
                                  "cost_total": "total (USD)"})
st.dataframe(ranking[["county", "residential (USD)", "commercial (USD)", "industrial (USD)", "total (USD)"]].round(0),
            width="stretch", hide_index=True)

comp.pie_de_hoja(
    "Cost figures on this page are narrative context for the report, not a model performance "
    "metric. Model comparison still runs on RMSE, MAE and the asymmetric cost defined in "
    "validation. Rates are quoted in 2002 USD unless the inflation control above is used."
)

comp.ver_tambien(["map", "hyst", "refs"])
comp.pie_sitio()

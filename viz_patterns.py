"""New multivariate views: parallel coordinates, a hierarchically
clustered heatmap with a real dendrogram, a Sankey of how severity
escalates, and a Gapminder-style animated bubble scatter. Each one
answers a different question the simple time series and single-variable
charts elsewhere in the dashboard can't."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from scipy.cluster.hierarchy import linkage

import theme


def figura_coordenadas_paralelas(df: pd.DataFrame, variables: list[str], color_var: str = "osi",
                                 muestra_max: int = 3000) -> go.Figure | None:
    """Each line is one county-hour. Lines that share a path across
    several axes reveal a combination of conditions, not just a single
    variable, that tends to go with high severity."""
    variables = [v for v in variables if v in df.columns]
    if len(variables) < 3 or color_var not in df.columns:
        return None
    cols = list(dict.fromkeys(variables + [color_var]))
    datos = df[cols].dropna()
    if len(datos) > muestra_max:
        datos = datos.sample(muestra_max, random_state=0)
    if len(datos) < 20:
        return None
    p = theme.paleta()
    vmax = float(np.nanpercentile(datos[color_var], 99.5)) or 1e-6

    # theme.ETIQUETAS_VARIABLE's labels are written for a single axis title
    # (plenty of room); packed side by side as parcoords dimensions, eight
    # or nine of those full names collide into each other. Short forms only
    # for this chart, where horizontal room per axis is the scarce thing.
    etiquetas_cortas = {
        "gust": "gust (mph)", "wind_speed_10m": "wind (mph)", "mslma": "SLP (hPa)",
        "sp": "pressure (hPa)", "tp": "precip (mm)", "rain": "rain (mm)",
        "csnow": "snow (cm)", "soil_moist": "soil moist.", "r2": "humidity (%)",
        "blh": "blh (m)", "t2m": "temp (K)", "osi": "OSI",
    }

    def etiqueta_de(v):
        return etiquetas_cortas.get(v, theme.ETIQUETAS_VARIABLE.get(v, v))

    dimensiones = []
    for v in variables:
        dimensiones.append(dict(label=etiqueta_de(v), values=datos[v],
                                range=[float(datos[v].min()), float(datos[v].max())]))

    fig = go.Figure(go.Parcoords(
        line=dict(color=datos[color_var], colorscale=theme.ESCALA_TORMENTA, cmin=0, cmax=vmax,
                  showscale=True, colorbar=dict(title=etiqueta_de(color_var))),
        dimensions=dimensiones,
        labelfont=dict(size=11), tickfont=dict(size=9),
    ))
    fig.update_layout(
        paper_bgcolor=p["panel"], font=dict(family=theme.FONT_BODY, color=p["ink"], size=11),
        height=460, margin=dict(l=60, r=60, t=56, b=20),
    )
    return fig


def figura_heatmap_agrupado(df: pd.DataFrame, variable: str = "osi") -> go.Figure | None:
    """Counties reordered by a real hierarchical clustering of their
    hourly severity profile (average-linkage, Euclidean distance), with
    the dendrogram drawn alongside so the grouping is visible, not just
    asserted. Time (the x-axis) is never reordered, only the counties."""
    if not {"fipsCode", "hour_idx", variable}.issubset(df.columns):
        return None
    pivote = df.pivot_table(index="fipsCode", columns="hour_idx", values=variable, aggfunc="first").fillna(0)
    if pivote.shape[0] < 4:
        return None
    nombres_por_fips = df.drop_duplicates("fipsCode").set_index("fipsCode")["countyName"]
    nombres = nombres_por_fips.reindex(pivote.index).tolist()
    matriz = pivote.to_numpy()
    horas = pivote.columns.to_numpy()
    p = theme.paleta()

    dendro = ff.create_dendrogram(matriz, orientation="left", labels=nombres,
                                  linkagefun=lambda x: linkage(x, method="average"))
    orden_nombres = list(dendro.layout.yaxis.ticktext)
    tickvals = list(dendro.layout.yaxis.tickvals)
    idx_por_nombre = {n: i for i, n in enumerate(nombres)}
    idx_orden = [idx_por_nombre[n] for n in orden_nombres]
    z_reordenado = matriz[idx_orden, :]

    for tr in dendro.data:
        tr.update(xaxis="x2", line=dict(color=p["muted"], width=1.2))

    vmax = float(np.nanpercentile(matriz, 99.5)) or 1e-6
    etiqueta = theme.ETIQUETAS_VARIABLE.get(variable, variable)
    heat = go.Heatmap(z=z_reordenado, x=horas, y=tickvals, xaxis="x", yaxis="y2",
                      colorscale=theme.ESCALA_TORMENTA, zmin=0, zmax=vmax,
                      colorbar=dict(title=etiqueta, thickness=12, x=1.02))

    fig = go.Figure(data=list(dendro.data) + [heat])
    fig.update_layout(
        xaxis=dict(domain=[0.16, 1], anchor="y2", title="hour of the event",
                   gridcolor=p["grid"], linecolor=p["border"]),
        xaxis2=dict(domain=[0, 0.13], anchor="y", showticklabels=False, showgrid=False,
                    title="similarity", zeroline=False),
        yaxis=dict(domain=[0, 1], tickvals=tickvals, ticktext=orden_nombres, anchor="x2",
                   tickfont=dict(size=9, color=p["muted"])),
        yaxis2=dict(domain=[0, 1], tickvals=tickvals, ticktext=orden_nombres, anchor="x",
                    matches="y", showticklabels=False),
        paper_bgcolor=p["panel"], plot_bgcolor=p["panel"],
        font=dict(family=theme.FONT_BODY, color=p["ink"], size=12),
        height=max(480, 16 * len(nombres)), margin=dict(l=10, r=20, t=30, b=50), showlegend=False,
    )
    return fig


def figura_sankey_severidad(df: pd.DataFrame) -> go.Figure | None:
    """How a storm escalates: gust intensity flowing into how fast new
    failures pile up (N_t), flowing into the resulting OSI severity
    band. A flow diagram, not a chart per variable, so the compounding
    is visible in one image."""
    if not {"gust", "N_t", "osi"}.issubset(df.columns):
        return None
    datos = df[["gust", "N_t", "osi"]].dropna()
    if len(datos) < 50:
        return None
    p = theme.paleta()

    def bandas(x, etiquetas):
        try:
            return pd.qcut(x, len(etiquetas), labels=etiquetas, duplicates="drop")
        except ValueError:
            return pd.cut(x, len(etiquetas), labels=etiquetas)

    gust_b = bandas(datos["gust"], ["calm gust", "moderate gust", "strong gust"])
    n_b = bandas(datos["N_t"], ["few new failures", "many new failures"])
    osi_b = bandas(datos["osi"], ["low OSI", "medium OSI", "high OSI"])

    etapa1 = [f"{g}" for g in gust_b.cat.categories]
    etapa2 = [f"{n}" for n in n_b.cat.categories]
    etapa3 = [f"{o}" for o in osi_b.cat.categories]
    nodos = etapa1 + etapa2 + etapa3
    idx = {n: i for i, n in enumerate(nodos)}

    # every node gets a color from the same severity scale as the rest of the dashboard,
    # placed by its rank within its own stage (calm -> white, strong -> red), so the flow
    # visually reddens left to right instead of three flat, unrelated block colors
    def color_por_rango(etapas):
        colores = []
        for etapa in etapas:
            n = len(etapa)
            for i, _ in enumerate(etapa):
                t = i / max(n - 1, 1)
                colores.append(theme.color_escala_tormenta(t))
        return colores

    colores_rgb = color_por_rango([etapa1, etapa2, etapa3])
    colores_nodo = [f"rgb({r},{g},{b})" for r, g, b in colores_rgb]
    color_por_nombre = dict(zip(nodos, colores_rgb))

    flujo1 = pd.crosstab(gust_b, n_b)
    flujo2 = pd.crosstab(n_b, osi_b)

    source, target, value, color_link = [], [], [], []
    for a in flujo1.index:
        for b in flujo1.columns:
            v = int(flujo1.loc[a, b])
            if v > 0:
                source.append(idx[a]); target.append(idx[b]); value.append(v)
                r, g, bl = color_por_nombre[b]
                color_link.append(f"rgba({r},{g},{bl},0.45)")
    for a in flujo2.index:
        for b in flujo2.columns:
            v = int(flujo2.loc[a, b])
            if v > 0:
                source.append(idx[a]); target.append(idx[b]); value.append(v)
                r, g, bl = color_por_nombre[b]
                color_link.append(f"rgba({r},{g},{bl},0.45)")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=nodos, color=colores_nodo, pad=22, thickness=18,
                  line=dict(color=p["border"], width=0.5),
                  hovertemplate="%{label}<br>%{value} county-hours<extra></extra>"),
        link=dict(source=source, target=target, value=value, color=color_link,
                  hovertemplate="%{source.label} -> %{target.label}<br>%{value} county-hours<extra></extra>"),
    ))
    fig.update_layout(
        title=dict(text="How gust becomes severity: gust, to new-failure rate, to OSI band",
                   font=dict(family=theme.FONT_DISPLAY, size=15, color=p["ink"])),
        paper_bgcolor=p["panel"], font=dict(family=theme.FONT_BODY, color=p["ink"], size=13),
        height=440, margin=dict(l=10, r=10, t=60, b=10),
        annotations=[
            dict(text="gust intensity", x=0.02, y=1.08, xref="paper", yref="paper", showarrow=False,
                font=dict(family=theme.FONT_MONO, size=10.5, color=p["muted"])),
            dict(text="new-failure rate", x=0.5, y=1.08, xref="paper", yref="paper", showarrow=False,
                font=dict(family=theme.FONT_MONO, size=10.5, color=p["muted"])),
            dict(text="OSI band", x=0.98, y=1.08, xref="paper", yref="paper", showarrow=False,
                font=dict(family=theme.FONT_MONO, size=10.5, color=p["muted"])),
        ],
    )
    return fig


def figura_ridgeline_fase(df: pd.DataFrame, variable: str = "osi", n_fases: int = 8) -> go.Figure | None:
    """A ridgeline of the variable's distribution shape as the event
    progresses: the same static histogram elsewhere in the dashboard, but
    sliced into phases so the shift from all-zero calm to a spread-out
    storm tail, and back, is visible as a single image instead of a
    single frozen number like "% zeros"."""
    if not {"hour_idx", variable}.issubset(df.columns):
        return None
    horas = df["hour_idx"]
    bordes = np.linspace(horas.min(), horas.max(), n_fases + 1)
    p = theme.paleta()
    etiqueta = theme.ETIQUETAS_VARIABLE.get(variable, variable)

    fig = go.Figure()
    tope = float(df[variable].quantile(0.995)) or 1e-6
    for i in range(n_fases):
        h0, h1 = bordes[i], bordes[i + 1]
        corte = df[(horas >= h0) & (horas < h1 if i < n_fases - 1 else horas <= h1)][variable].dropna()
        if len(corte) < 5:
            continue
        t = i / max(n_fases - 1, 1)
        color = theme.color_escala_tormenta(t)
        fig.add_trace(go.Violin(
            x=corte.clip(upper=tope), line_color=f"rgb({color[0]},{color[1]},{color[2]})",
            fillcolor=f"rgba({color[0]},{color[1]},{color[2]},0.55)",
            name=f"hours {int(h0)}-{int(h1)}", orientation="h", side="positive", width=2.2,
            points=False, meanline_visible=True,
        ))
    fig.update_layout(
        paper_bgcolor=p["panel"], plot_bgcolor=p["panel"], font=dict(family=theme.FONT_BODY, color=p["ink"], size=12),
        title=dict(text=f"How {etiqueta}'s distribution shifts across the event",
                   font=dict(family=theme.FONT_DISPLAY, size=16, color=p["ink"])),
        height=430, margin=dict(l=110, r=30, t=50, b=40), showlegend=False,
        xaxis=dict(title=etiqueta, gridcolor=p["grid"], zerolinecolor=p["border"]),
        violingap=0.15,
    )
    return fig


def figura_burbujas_animada(df: pd.DataFrame, paso_horas: int = 3) -> go.Figure | None:
    """The Gapminder-style bubble view (gust vs. OSI, bubble size is
    customers tracked, color is state), as one figure with a frame per
    hour built in, not a page that re-renders itself every tick.

    An earlier version drove this with `st.session_state` + `st.rerun()`
    on a timer: because `st.rerun()` re-executes the *entire* page, every
    tick also rebuilt the parallel coordinates, the hierarchical
    clustering (a real scipy linkage, not cheap) and the Sankey below it,
    whether or not they had changed. That's what made the page feel slow
    and made it hard to follow: four charts redrawing on every tick, not
    just the one that was supposed to be animating. `px.scatter`'s own
    `animation_frame` builds every hour as a Plotly frame up front, same
    as the storm map's relief and county map, so the browser advances the
    animation with no round trip to the server at all."""
    necesarias = {"gust", "osi", "customersTracked", "stateAbbr", "hour_idx"}
    if not necesarias.issubset(df.columns):
        return None
    horas = np.sort(df["hour_idx"].unique())[::max(1, paso_horas)]
    if len(horas) < 2:
        return None
    recorte = df[df["hour_idx"].isin(horas)].copy()
    recorte["hour_idx"] = recorte["hour_idx"].astype(int)
    tope_gust = float(df["gust"].quantile(0.995)) or 1.0
    tope_osi = float(df["osi"].quantile(0.995)) or 1e-6

    fig = px.scatter(
        recorte, x="gust", y="osi", size="customersTracked", color="stateAbbr",
        hover_name="countyName", animation_frame="hour_idx",
        range_x=[0, tope_gust * 1.05], range_y=[-tope_osi * 0.05, tope_osi * 1.15],
        size_max=42,
    )
    fig.update_traces(marker=dict(line=dict(color="white", width=0.6), opacity=0.82))
    p = theme.paleta()
    fig.update_layout(
        paper_bgcolor=p["panel"], plot_bgcolor=p["panel"],
        font=dict(family=theme.FONT_BODY, color=p["ink"], size=13), height=480,
        margin=dict(l=56, r=24, t=40, b=48),
        legend=dict(bgcolor=p["panel"], bordercolor=p["border"], borderwidth=1),
    )
    eje = dict(gridcolor=p["grid"], zerolinecolor=p["border"], showline=True, linecolor=p["border"],
               tickfont=dict(color=p["muted"], size=11))
    fig.update_xaxes(title_text=theme.ETIQUETAS_VARIABLE.get("gust", "gust"), **eje)
    fig.update_yaxes(title_text="OSI", **eje)
    for frame in fig.frames:
        frame.layout = dict(xaxis=dict(range=[0, tope_gust * 1.05]),
                            yaxis=dict(range=[-tope_osi * 0.05, tope_osi * 1.15]))
    return fig

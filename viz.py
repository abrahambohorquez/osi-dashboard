"""
Constructores de figuras que comparte más de una hoja, sobre todo la
animación de la tormenta: un campo de severidad interpolado que barre el
mapa hora a hora, en versión plana (2D) y en versión de relieve (3D,
donde la altura también es severidad, no solo el color). Todo se arma con
frames nativos de Plotly, así que la animación corre en el navegador sin
recargar Streamlit cada vez que avanza una hora.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy.spatial import cKDTree

import theme


@st.cache_data(show_spinner=False)
def _geojson_y_centro(fips_tuple: tuple, _geo) -> tuple[dict, float, float]:
    """Geometría del mapa real: no cambia de un tick de reproducción al
    siguiente (solo cambia la severidad), así que se cachea por el
    conjunto de condados en vez de reconstruirse ~8 veces por segundo
    mientras el mapa se reproduce solo."""
    import warnings

    geo_propio = _geo.drop_duplicates("fipsCode")[["fipsCode", "geometry"]].copy()
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "id": str(fips), "geometry": geom.__geo_interface__}
            for fips, geom in zip(geo_propio["fipsCode"], geo_propio["geometry"])
        ],
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        centro_lat = float(geo_propio.geometry.centroid.y.mean())
        centro_lon = float(geo_propio.geometry.centroid.x.mean())
    return geojson, centro_lat, centro_lon


def _sigma_espacial(px: np.ndarray, py: np.ndarray) -> float:
    """Ancho del kernel: ~1.25x la distancia típica entre condados
    vecinos, para que los blobs se toquen sin aplanarse ni fragmentarse."""
    puntos = np.column_stack([px, py])
    if len(puntos) < 3:
        return 1.0
    arbol = cKDTree(puntos)
    d, _ = arbol.query(puntos, k=2)
    return float(np.median(d[:, 1]) * 1.25) or 1.0


def _campo_interpolado(px, py, val, gx, gy, sigma) -> np.ndarray:
    """Campo suave por ponderación gaussiana de distancia: cada punto de
    la malla es un promedio de los condados, pesado por exp(-d^2/2sigma^2).
    Da un frente continuo, sin los bordes en bloque que deja el vecino más
    cercano, y decae naturalmente donde no hay condados alrededor."""
    GX, GY = np.meshgrid(gx, gy)
    z = np.zeros_like(GX)
    peso_total = np.zeros_like(GX)
    dos_sig2 = 2.0 * sigma * sigma
    for xi, yi, vi in zip(px, py, val):
        w = np.exp(-((GX - xi) ** 2 + (GY - yi) ** 2) / dos_sig2)
        z += w * vi
        peso_total += w
    return z / np.where(peso_total < 1e-9, 1e-9, peso_total)


def _celdas_voronoi(px: np.ndarray, py: np.ndarray, x0: float, x1: float, y0: float, y1: float):
    """Parte el plano en una celda por condado (tipo Voronoi: cada punto
    del plano queda asignado al condado más cercano), recortada a la caja
    del mapa. Es lo que hace que el mapa simulado se vea como un mapa de
    verdad, con fronteras entre "condados", en vez de una mancha difusa
    sin bordes. Son fronteras inventadas, no administrativas: solo marcan
    cercanía en el plano ficticio de la demo."""
    from scipy.spatial import Voronoi
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    n = len(px)
    if n < 2:
        return []
    caja = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    ancho, alto = x1 - x0, y1 - y0
    lejos = max(ancho, alto) * 8
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    espejos = [(cx - lejos, cy - lejos), (cx + lejos, cy - lejos),
              (cx + lejos, cy + lejos), (cx - lejos, cy + lejos),
              (cx, cy - lejos), (cx, cy + lejos), (cx - lejos, cy), (cx + lejos, cy)]
    puntos = np.vstack([np.column_stack([px, py]), np.array(espejos)])
    vor = Voronoi(puntos)

    celdas = []
    for i in range(n):
        region_idx = vor.point_region[i]
        vertices_idx = vor.regions[region_idx]
        if not vertices_idx or -1 in vertices_idx:
            celdas.append(np.empty((0, 2)))
            continue
        poligono = Polygon(vor.vertices[vertices_idx])
        recortado = poligono.intersection(caja)
        if recortado.is_empty:
            celdas.append(np.empty((0, 2)))
        elif recortado.geom_type == "Polygon":
            celdas.append(np.array(recortado.exterior.coords))
        else:
            mas_grande = max(recortado.geoms, key=lambda g: g.area)
            celdas.append(np.array(mas_grande.exterior.coords))
    return celdas


def _con_posiciones(df: pd.DataFrame) -> pd.DataFrame | None:
    """El archivo real del reto no trae posicion_x/posicion_y (esas son
    invento de la simulación): si faltan pero hay fipsCode real, se
    calculan solas a partir del centroide real del condado (Census
    TIGER, lo mismo que usa el mapa geográfico), en vez de exigirle al
    usuario que agregue columnas inventadas a un archivo real. Devuelve
    None si de plano no hay ninguna forma de ubicar los condados."""
    if {"posicion_x", "posicion_y"}.issubset(df.columns):
        return df
    if "fipsCode" not in df.columns:
        return None
    import warnings

    import geo_condados

    if not geo_condados.hay_cache():
        return None
    geo = geo_condados.obtener_geometrias()
    fips_propios = set(df["fipsCode"].unique())
    geo_propio = geo[geo["fipsCode"].isin(fips_propios)].drop_duplicates("fipsCode")
    if len(geo_propio) < 3:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        centroides = geo_propio.geometry.centroid
    posiciones = pd.DataFrame({
        "fipsCode": geo_propio["fipsCode"].to_numpy(),
        "posicion_x": centroides.x.to_numpy(),
        "posicion_y": centroides.y.to_numpy(),
    })
    return df.merge(posiciones, on="fipsCode", how="inner")


def tiene_posiciones_disponibles(df: pd.DataFrame) -> bool:
    """Para que una hoja decida si vale la pena intentar el relieve/mapa
    plano antes de llamar a la figura: True si el archivo ya trae
    posicion_x/posicion_y, o si se pueden derivar de condados reales."""
    return _con_posiciones(df) is not None


def _preparar_malla(df: pd.DataFrame, variable: str, paso_horas: int, resolucion: int):
    """Lo que ambas figuras (2D y 3D) necesitan por igual: posiciones,
    malla, sigma, pivote de valores por hora, y el tope de color/escala."""
    horas = np.sort(df["hour_idx"].unique())[::max(1, paso_horas)]
    pos = df.groupby("fipsCode").agg(x=("posicion_x", "first"), y=("posicion_y", "first")).reset_index()
    px, py = pos["x"].to_numpy(), pos["y"].to_numpy()

    x0, x1 = float(px.min() - 0.3), float(px.max() + 0.3)
    y0, y1 = float(py.min() - 0.3), float(py.max() + 0.3)
    gx = np.linspace(x0, x1, resolucion)
    gy = np.linspace(y0, y1, max(6, int(resolucion * (y1 - y0) / max(x1 - x0, 1e-6))))
    sigma = _sigma_espacial(px, py)

    vmax = float(np.nanpercentile(df[variable], 99.5)) or 1e-6
    vmax = max(vmax, 1e-6)

    pivote = df.pivot_table(index="hour_idx", columns="fipsCode", values=variable, aggfunc="first")
    pivote = pivote.reindex(columns=pos["fipsCode"].to_numpy())
    agg = df.groupby("hour_idx")[variable].mean().reindex(np.sort(df["hour_idx"].unique()))

    return dict(horas=horas, pos=pos, px=px, py=py, x0=x0, x1=x1, y0=y0, y1=y1,
                gx=gx, gy=gy, sigma=sigma, vmax=vmax, pivote=pivote, agg=agg)


def figura_tormenta_2d(df: pd.DataFrame, variable: str = "osi", paso_horas: int = 2,
                       resolucion: int = 56) -> go.Figure | None:
    """Panel superior: campo de `variable` interpolado + un punto por
    condado, coloreado por el valor de esa hora. Panel inferior: promedio
    regional con un cursor que avanza con la animación, para saber en qué
    momento de las dos oleadas se está."""
    if not {"hour_idx", variable}.issubset(df.columns):
        return None
    df = _con_posiciones(df)
    if df is None:
        return None
    m = _preparar_malla(df, variable, paso_horas, resolucion)
    if len(m["horas"]) < 2:
        return None
    p = theme.paleta()
    etiqueta = theme.ETIQUETAS_VARIABLE.get(variable, variable)

    fig = make_subplots(rows=2, cols=1, row_heights=[0.78, 0.22], vertical_spacing=0.1,
                        subplot_titles=("", f"Regional average {etiqueta}: where we are in the event"))

    def frame_data(h):
        vals = np.nan_to_num(m["pivote"].loc[h].to_numpy(dtype=float), nan=0.0)
        z = _campo_interpolado(m["px"], m["py"], vals, m["gx"], m["gy"], m["sigma"])
        traces = [
            go.Heatmap(x=m["gx"], y=m["gy"], z=z, zmin=0, zmax=m["vmax"], colorscale=theme.ESCALA_TORMENTA,
                       showscale=True, colorbar=dict(title=etiqueta, thickness=12, len=0.66, y=0.62),
                       hoverinfo="skip", zsmooth="best"),
            go.Scatter(x=m["px"], y=m["py"], mode="markers",
                       marker=dict(size=9, color=vals, colorscale=theme.ESCALA_TORMENTA, cmin=0, cmax=m["vmax"],
                                   line=dict(width=0.8, color="rgba(255,255,255,0.75)"), showscale=False),
                       text=[f"{n}<br>{etiqueta}: {v:.4f}" for n, v in zip(m["pos"]["fipsCode"], vals)],
                       hoverinfo="text", name="counties"),
        ]
        return traces

    def cursor(h):
        return go.Scatter(x=[h, h], y=[0, float(m["agg"].max()) * 1.05], mode="lines",
                          line=dict(color=p["accent"], width=2), hoverinfo="skip", showlegend=False)

    h0 = m["horas"][0]
    for tr in frame_data(h0):
        fig.add_trace(tr, row=1, col=1)

    celdas = _celdas_voronoi(m["px"], m["py"], m["x0"], m["x1"], m["y0"], m["y1"])
    xs_borde, ys_borde = [], []
    for celda in celdas:
        if len(celda):
            xs_borde += list(celda[:, 0]) + [None]
            ys_borde += list(celda[:, 1]) + [None]
    fig.add_trace(go.Scatter(x=xs_borde, y=ys_borde, mode="lines",
                             line=dict(color="rgba(255,255,255,0.55)", width=1),
                             hoverinfo="skip", showlegend=False), row=1, col=1)

    fig.add_trace(go.Scatter(x=m["agg"].index, y=m["agg"].values, mode="lines",
                             line=dict(color=p["ink"], width=2), fill="tozeroy",
                             fillcolor="rgba(10,36,114,0.08)", showlegend=False), row=2, col=1)
    fig.add_trace(cursor(h0), row=2, col=1)

    frames = []
    for h in m["horas"]:
        datos = frame_data(h) + [cursor(h)]
        frames.append(go.Frame(data=datos, name=str(int(h)), traces=[0, 1, 4]))
    fig.frames = frames

    fig.update_xaxes(range=[m["x0"], m["x1"]], showgrid=False, zeroline=False, visible=False, row=1, col=1)
    fig.update_yaxes(range=[m["y0"], m["y1"]], showgrid=False, zeroline=False, visible=False,
                     scaleanchor="x", scaleratio=1, row=1, col=1)
    eje = dict(gridcolor=p["grid"], zerolinecolor=p["border"], showline=True, linecolor=p["border"],
               tickfont=dict(color=p["muted"], size=11))
    fig.update_xaxes(title="hour of the event", row=2, col=1, **eje)
    fig.update_yaxes(title=etiqueta, row=2, col=1, **eje)

    pasos = [dict(method="animate", label=f"{int(h)}",
                  args=[[str(int(h))], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                            transition=dict(duration=0))]) for h in m["horas"]]

    fig.update_layout(
        paper_bgcolor=p["panel"], plot_bgcolor=p["panel"], font=dict(family=theme.FONT_BODY, color=p["ink"], size=13),
        height=700, margin=dict(l=24, r=24, t=90, b=44),
        updatemenus=[dict(type="buttons", direction="left", x=0.0, y=1.18, xanchor="left", yanchor="top",
                          bgcolor=p["panel"], bordercolor=p["border"], borderwidth=1, pad=dict(l=8, r=8, t=5, b=5),
                          font=dict(size=12, color=p["ink"]),
                          buttons=[
                              dict(label="play", method="animate",
                                   args=[None, dict(frame=dict(duration=130, redraw=True), fromcurrent=True,
                                                    transition=dict(duration=50, easing="cubic-in-out"))]),
                              dict(label="pause", method="animate",
                                   args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
                          ])],
        sliders=[dict(active=0, x=0.14, len=0.84, y=1.185, pad=dict(t=0, b=0),
                      currentvalue=dict(prefix="hour ", font=dict(size=13, color=p["ink"])),
                      steps=pasos, bgcolor=p["border"], activebgcolor=p["accent"], bordercolor=p["border"],
                      font=dict(color=p["ink"]))],
    )
    for ann in fig.layout.annotations:
        ann.font.update(family=theme.FONT_DISPLAY, size=13.5, color=p["ink"])
    return fig


def figura_mapa_simulado_snapshot(df: pd.DataFrame, variable: str, hora_fija: int) -> go.Figure | None:
    """La foto de una hora exacta, pero para datos simulados: cada
    condado pintado como una celda propia (Voronoi, fronteras
    inventadas para la demo), no un punto suelto. Se ve como un mapa de
    verdad aunque las coordenadas sean ficticias."""
    if not {"posicion_x", "posicion_y", "hour_idx", variable}.issubset(df.columns):
        return None
    pos = df.groupby("fipsCode").agg(x=("posicion_x", "first"), y=("posicion_y", "first"),
                                     nombre=("countyName", "first")).reset_index()
    px, py = pos["x"].to_numpy(), pos["y"].to_numpy()
    x0, x1 = float(px.min() - 0.3), float(px.max() + 0.3)
    y0, y1 = float(py.min() - 0.3), float(py.max() + 0.3)
    celdas = _celdas_voronoi(px, py, x0, x1, y0, y1)

    corte = df[df["hour_idx"] == hora_fija].set_index("fipsCode")
    vmax = float(np.nanpercentile(df[variable], 99.5)) or 1e-6
    vmax = max(vmax, 1e-6)
    p = theme.paleta()
    etiqueta = theme.ETIQUETAS_VARIABLE.get(variable, variable)

    fig = go.Figure()
    for fips, nombre, celda in zip(pos["fipsCode"], pos["nombre"], celdas):
        if not len(celda) or fips not in corte.index:
            continue
        valor = float(corte.loc[fips, variable])
        color = theme.color_escala_tormenta(valor / vmax)
        fig.add_trace(go.Scatter(
            x=celda[:, 0], y=celda[:, 1], mode="lines", fill="toself",
            fillcolor=f"rgba({color[0]},{color[1]},{color[2]},0.88)",
            line=dict(color="rgba(255,255,255,0.6)", width=1),
            text=f"{nombre}<br>{etiqueta}: {valor:.4f}", hoverinfo="text", showlegend=False,
        ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(colorscale=theme.ESCALA_TORMENTA, cmin=0, cmax=vmax, showscale=True,
                    color=[0], colorbar=dict(title=etiqueta, thickness=12)),
        showlegend=False, hoverinfo="skip",
    ))
    theme.aplicar_tema(fig, titulo=f"Simulated map (artificial cells), hour {hora_fija}", altura=460)
    fig.update_xaxes(visible=False, range=[x0, x1])
    fig.update_yaxes(visible=False, range=[y0, y1], scaleanchor="x", scaleratio=1)
    fig.update_layout(paper_bgcolor=p["panel"], plot_bgcolor=p["panel"])
    return fig


def figura_mapa_geografico(df: pd.DataFrame, geo, variable: str = "osi",
                           paso_horas: int = 3, hora_fija: int | None = None) -> go.Figure | None:
    """La tormenta sobre el mapa real de condados (no una posición
    inventada): solo tiene sentido cuando fipsCode es un FIPS real y por
    lo tanto calza con las geometrías del Census. `geo` ya viene cruzado
    con el df activo (ver geo_condados.emparejar). Si `hora_fija` viene
    dado, no anima: congela esa sola hora, sin controles de reproducción
    (para la foto de una hora exacta)."""
    if geo is None or geo.empty or "fipsCode" not in df.columns:
        return None
    horas = np.sort(df["hour_idx"].unique())
    if hora_fija is None:
        horas = horas[::max(1, paso_horas)]
        if len(horas) < 2:
            return None
    p = theme.paleta()
    etiqueta = theme.ETIQUETAS_VARIABLE.get(variable, variable)

    geo_propio = geo.drop_duplicates("fipsCode")[["fipsCode", "geometry"]].copy()
    fips_validos = geo_propio["fipsCode"].to_numpy()
    geojson, centro_lat, centro_lon = _geojson_y_centro(tuple(sorted(fips_validos.tolist())), geo_propio)
    pivote = df.pivot_table(index="hour_idx", columns="fipsCode", values=variable, aggfunc="first")
    pivote = pivote.reindex(columns=fips_validos)
    vmax = float(np.nanpercentile(df[variable], 99.5)) or 1e-6
    vmax = max(vmax, 1e-6)

    def vals_de(h):
        return np.nan_to_num(pivote.loc[h].to_numpy(dtype=float), nan=0.0)

    v0 = vals_de(hora_fija if hora_fija is not None else horas[0])
    titulo = (f"{etiqueta}, hour {int(hora_fija)}" if hora_fija is not None
             else f"{etiqueta} over the real county map")
    fig = go.Figure(go.Choroplethmapbox(
        geojson=geojson, locations=[str(f) for f in fips_validos], z=v0,
        zmin=0, zmax=vmax, colorscale=theme.ESCALA_TORMENTA, marker_line_width=0.6,
        marker_line_color="rgba(255,255,255,0.6)", colorbar=dict(title=etiqueta, thickness=14),
        hovertext=[f"FIPS {f}<br>{etiqueta}: {v:.4f}" for f, v in zip(fips_validos, v0)],
        hoverinfo="text",
    ))
    fig.update_layout(
        mapbox=dict(style="carto-positron", center=dict(lat=centro_lat, lon=centro_lon), zoom=5.6),
        paper_bgcolor=p["panel"], font=dict(family=theme.FONT_BODY, color=p["ink"], size=13),
        height=680, margin=dict(l=0, r=0, t=64, b=10),
        title=dict(text=titulo, font=dict(family=theme.FONT_DISPLAY, size=28, color=p["ink"]),
                   x=0.5, xanchor="center"),
        uirevision="mapa-geografico-fijo",
    )

    if hora_fija is None:
        def hover_de(h, vals):
            return [f"FIPS {f}<br>{etiqueta}: {v:.4f}" for f, v in zip(fips_validos, vals)]

        fig.frames = [
            go.Frame(name=str(int(h)),
                     data=[go.Choroplethmapbox(z=(vals := vals_de(h)), hovertext=hover_de(h, vals))])
            for h in horas
        ]
        pasos = [dict(method="animate", label=f"{int(h)}",
                      args=[[str(int(h))], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                                transition=dict(duration=0))]) for h in horas]
        fig.update_layout(
            updatemenus=[dict(type="buttons", direction="left", x=0.0, y=1.05, xanchor="left", yanchor="top",
                              bgcolor=p["panel"], bordercolor=p["border"], borderwidth=1, pad=dict(l=8, r=8, t=5, b=5),
                              font=dict(size=12, color=p["ink"]),
                              buttons=[
                                  dict(label="play", method="animate",
                                       args=[None, dict(frame=dict(duration=160, redraw=True), fromcurrent=True,
                                                        transition=dict(duration=0))]),
                                  dict(label="pause", method="animate",
                                       args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
                              ])],
            sliders=[dict(active=0, x=0.16, len=0.82, y=1.04, pad=dict(t=0, b=0),
                          currentvalue=dict(prefix="hour ", font=dict(size=13, color=p["ink"])),
                          steps=pasos, bgcolor=p["border"], activebgcolor=p["accent"], bordercolor=p["border"],
                          font=dict(color=p["ink"]))],
        )
    return fig


def figura_tormenta_3d(df: pd.DataFrame, variable: str = "osi", paso_horas: int = 3,
                       resolucion: int = 34, orbitar: bool = True) -> go.Figure | None:
    """La misma idea que la 2D, pero la altura también codifica severidad,
    no solo el color: un relieve que sube donde la tormenta pega fuerte.
    La cámara gira despacio a lo largo de la animación para un efecto de
    sobrevuelo, no un plano fijo."""
    if not {"hour_idx", variable}.issubset(df.columns):
        return None
    df = _con_posiciones(df)
    if df is None:
        return None
    m = _preparar_malla(df, variable, paso_horas, resolucion)
    if len(m["horas"]) < 2:
        return None
    p = theme.paleta()
    etiqueta = theme.ETIQUETAS_VARIABLE.get(variable, variable)
    n_frames = len(m["horas"])

    def z_de(h):
        vals = np.nan_to_num(m["pivote"].loc[h].to_numpy(dtype=float), nan=0.0)
        return _campo_interpolado(m["px"], m["py"], vals, m["gx"], m["gy"], m["sigma"]), vals

    def camara(i):
        if not orbitar:
            return dict(eye=dict(x=1.55, y=-1.55, z=1.05))
        angulo = np.deg2rad(200 + 55 * (i / max(n_frames - 1, 1)))
        r = 2.1
        return dict(eye=dict(x=r * np.cos(angulo), y=r * np.sin(angulo), z=1.0))

    z0, vals0 = z_de(m["horas"][0])
    fig = go.Figure(
        data=[
            go.Surface(x=m["gx"], y=m["gy"], z=z0, colorscale=theme.ESCALA_TORMENTA, cmin=0, cmax=m["vmax"],
                       showscale=True, colorbar=dict(title=etiqueta, thickness=14, len=0.7),
                       lighting=dict(ambient=0.65, diffuse=0.6, specular=0.15, roughness=0.85),
                       contours=dict(z=dict(show=False))),
            go.Scatter3d(x=m["px"], y=m["py"], z=vals0 + m["vmax"] * 0.02, mode="markers",
                        marker=dict(size=4, color=vals0, colorscale=theme.ESCALA_TORMENTA, cmin=0, cmax=m["vmax"],
                                    line=dict(width=0.6, color="white")),
                        text=[f"{n}<br>{etiqueta}: {v:.4f}" for n, v in zip(m["pos"]["fipsCode"], vals0)],
                        hoverinfo="text", name="counties"),
        ],
    )

    frames = []
    for i, h in enumerate(m["horas"]):
        z, vals = z_de(h)
        frames.append(go.Frame(
            name=str(int(h)),
            data=[go.Surface(z=z), go.Scatter3d(z=vals + m["vmax"] * 0.02,
                                                 marker=dict(color=vals, cmin=0, cmax=m["vmax"]))],
            traces=[0, 1],
            layout=dict(scene_camera=camara(i)) if orbitar else None,
        ))
    fig.frames = frames

    pasos = [dict(method="animate", label=f"{int(h)}",
                  args=[[str(int(h))], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                            transition=dict(duration=0))]) for h in m["horas"]]

    fig.update_layout(
        paper_bgcolor=p["panel"], font=dict(family=theme.FONT_BODY, color=p["ink"], size=13),
        height=690, margin=dict(l=0, r=0, t=64, b=10),
        title=dict(text=f"{etiqueta} relief: the storm in three dimensions",
                   font=dict(family=theme.FONT_DISPLAY, size=22, color=p["ink"]),
                   x=0.5, xanchor="center"),
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            zaxis=dict(title=etiqueta, range=[0, m["vmax"] * 1.05], color=p["muted"],
                      gridcolor=p["grid"], backgroundcolor=p["panel"]),
            camera=camara(0), aspectmode="manual", aspectratio=dict(x=1.4, y=1, z=0.55),
            bgcolor=p["panel"],
        ),
        updatemenus=[dict(type="buttons", direction="left", x=0.0, y=1.06, xanchor="left", yanchor="top",
                          bgcolor=p["panel"], bordercolor=p["border"], borderwidth=1, pad=dict(l=8, r=8, t=5, b=5),
                          font=dict(size=12, color=p["ink"]),
                          buttons=[
                              dict(label="play", method="animate",
                                   args=[None, dict(frame=dict(duration=140, redraw=True), fromcurrent=True,
                                                    transition=dict(duration=0))]),
                              dict(label="pause", method="animate",
                                   args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
                          ])],
        sliders=[dict(active=0, x=0.16, len=0.82, y=1.05, pad=dict(t=0, b=0),
                      currentvalue=dict(prefix="hour ", font=dict(size=13, color=p["ink"])),
                      steps=pasos, bgcolor=p["border"], activebgcolor=p["accent"], bordercolor=p["border"],
                      font=dict(color=p["ink"]))],
    )
    return fig


def figura_relieve_una_hora(df: pd.DataFrame, variable: str, hora: float, angulo_grados: float,
                            paso_horas: int = 3, resolucion: int = 34) -> go.Figure | None:
    """One static frame of the 3D relief, for a server-driven autoplay
    loop (the page re-renders this every tick with the next hour and the
    next camera angle) instead of Plotly's own client-side animate/frames
    machinery. Trades a little smoothness for something that starts
    running on its own and never depends on the user finding a play
    button."""
    if not {"hour_idx", variable}.issubset(df.columns):
        return None
    df = _con_posiciones(df)
    if df is None:
        return None
    m = _preparar_malla(df, variable, paso_horas, resolucion)
    if len(m["horas"]) < 2:
        return None
    p = theme.paleta()
    etiqueta = theme.ETIQUETAS_VARIABLE.get(variable, variable)

    horas_disponibles = m["horas"]
    hora_usada = horas_disponibles[np.argmin(np.abs(horas_disponibles - hora))]
    vals = np.nan_to_num(m["pivote"].loc[hora_usada].to_numpy(dtype=float), nan=0.0)
    z = _campo_interpolado(m["px"], m["py"], vals, m["gx"], m["gy"], m["sigma"])

    angulo = np.deg2rad(angulo_grados)
    r = 2.1
    camara = dict(eye=dict(x=r * np.cos(angulo), y=r * np.sin(angulo), z=1.0))

    fig = go.Figure(data=[
        go.Surface(x=m["gx"], y=m["gy"], z=z, colorscale=theme.ESCALA_TORMENTA, cmin=0, cmax=m["vmax"],
                  showscale=True, colorbar=dict(title=etiqueta, thickness=14, len=0.7),
                  lighting=dict(ambient=0.65, diffuse=0.6, specular=0.15, roughness=0.85),
                  contours=dict(z=dict(show=False))),
        go.Scatter3d(x=m["px"], y=m["py"], z=vals + m["vmax"] * 0.02, mode="markers",
                    marker=dict(size=4, color=vals, colorscale=theme.ESCALA_TORMENTA, cmin=0, cmax=m["vmax"],
                                line=dict(width=0.6, color="white")),
                    text=[f"{n}<br>{etiqueta}: {v:.4f}" for n, v in zip(m["pos"]["fipsCode"], vals)],
                    hoverinfo="text", name="counties"),
    ])
    fig.update_layout(
        paper_bgcolor=p["panel"], font=dict(family=theme.FONT_BODY, color=p["ink"], size=13),
        height=680, margin=dict(l=0, r=0, t=64, b=10),
        title=dict(text=f"{etiqueta}, hour {int(hora_usada)}",
                   font=dict(family=theme.FONT_DISPLAY, size=28, color=p["ink"]), x=0.5, xanchor="center"),
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            zaxis=dict(title=etiqueta, range=[0, m["vmax"] * 1.05], color=p["muted"],
                      gridcolor=p["grid"], backgroundcolor=p["panel"]),
            camera=camara, aspectmode="manual", aspectratio=dict(x=1.4, y=1, z=0.55),
            bgcolor=p["panel"],
        ),
    )
    return fig, hora_usada, horas_disponibles


def capa_pydeck_columnas(df: pd.DataFrame, geo, hora: int, variable: str = "osi"):
    """Vista ejecutiva: cada condado real como una columna 3D que sube
    con la severidad de esa hora, sobre un mapa base de verdad (Carto,
    sin necesitar token). A diferencia de las otras figuras, esta no trae
    su propio play/pausa: se mueve con el control de hora que comparte el
    resto de la hoja (así todo el panel se mueve junto, no cada mapa por
    su lado). Solo tiene sentido con condados reales (geo ya viene
    cruzado por fipsCode == GEOID, ver geo_condados.emparejar)."""
    import warnings

    import pydeck as pdk

    if geo is None or geo.empty or "fipsCode" not in df.columns:
        return None
    corte = df[df["hour_idx"] == hora]
    if corte.empty:
        return None

    geo_hora = geo.drop_duplicates("fipsCode")[["fipsCode", "geometry"]].merge(
        corte[["fipsCode", variable, "countyName", "stateAbbr"]], on="fipsCode", how="inner"
    )
    if geo_hora.empty:
        return None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        geo_hora["lon"] = geo_hora["geometry"].centroid.x
        geo_hora["lat"] = geo_hora["geometry"].centroid.y

    vmax = float(np.nanpercentile(df[variable], 99.5)) or 1e-6
    vmax = max(vmax, 1e-6)
    geo_hora["valor"] = geo_hora[variable].fillna(0.0)
    geo_hora["elevacion"] = geo_hora["valor"] / vmax * 42000
    colores = [theme.color_escala_tormenta(v / vmax) for v in geo_hora["valor"]]
    geo_hora["r"] = [c[0] for c in colores]
    geo_hora["g"] = [c[1] for c in colores]
    geo_hora["b"] = [c[2] for c in colores]
    etiqueta = theme.ETIQUETAS_VARIABLE.get(variable, variable)
    geo_hora["texto_hover"] = (geo_hora["countyName"] + ", " + geo_hora["stateAbbr"] + ", " + etiqueta + ": "
                               + geo_hora["valor"].round(4).astype(str))

    capa = pdk.Layer(
        "ColumnLayer", data=geo_hora, get_position=["lon", "lat"], get_elevation="elevacion",
        elevation_scale=1, radius=5500, get_fill_color=["r", "g", "b", 210],
        pickable=True, auto_highlight=True, extruded=True,
    )
    vista = pdk.ViewState(latitude=float(geo_hora["lat"].mean()), longitude=float(geo_hora["lon"].mean()),
                         zoom=5.7, pitch=52, bearing=-8)
    return pdk.Deck(layers=[capa], initial_view_state=vista, map_style=None,
                    tooltip={"text": "{texto_hover}"})

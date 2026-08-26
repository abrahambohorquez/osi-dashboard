"""Mapa cinematográfico de la tormenta: Folium/Leaflet de verdad (mapa
real, con pan y zoom reales), cada condado como una capa que cambia de
color con la hora, más una capa de lluvia cayendo encima del mapa mismo
(canvas, no un adorno aparte del contenedor). Un solo bucle de
JavaScript mueve el color de cada condado y las gotas al mismo tiempo,
para que se sienta como una película del evento, no un slider suelto.

Con datos reales se dibuja sobre condados reales, con mapa base real
(CartoDB). Con datos simulados se usa el mismo mecanismo pero sobre un
plano simple (`crs="Simple"`, sin mapa base real, porque las posiciones
simuladas no son coordenadas geográficas de verdad) y las celdas
inventadas (Voronoi) en vez de condados administrativos."""
from __future__ import annotations

import json

import folium
import numpy as np
import pandas as pd

import theme


def _rgb_css(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]},{c[1]},{c[2]})"


def _control_y_lluvia(mapa: folium.Map, nombres_js: list[str], colores_por_hora: dict, horas: list[int],
                      titulo: str) -> None:
    """Agrega al mapa: el bucle que pinta cada condado con su color de la
    hora activa, los botones de reproducir/pausa, el rótulo de hora, y el
    canvas de lluvia, todo corriendo junto en el mismo timer."""
    mapa_id = mapa.get_name()
    datos_js = json.dumps(colores_por_hora)
    capas_js = json.dumps(nombres_js)
    horas_js = json.dumps([int(h) for h in horas])

    html = f"""
    <div id="barra_{mapa_id}" style="position:absolute; z-index:1200; top:10px; left:50px;
        background:rgba(10,15,28,0.82); color:#E7ECF7; padding:8px 14px; border-radius:10px;
        font-family:'IBM Plex Sans',system-ui,sans-serif; font-size:13px; display:flex;
        align-items:center; gap:10px; box-shadow:0 2px 10px rgba(0,0,0,.35);">
        <button id="btn_{mapa_id}" style="background:#C98A1F; color:#1A1300; border:none;
            border-radius:6px; padding:5px 12px; font-weight:700; cursor:pointer;">reproducir</button>
        <input id="rango_{mapa_id}" type="range" min="0" max="{len(horas) - 1}" value="0"
            style="width:220px;">
        <span id="rotulo_{mapa_id}" style="font-family:'IBM Plex Mono',monospace; min-width:110px;">
            {titulo}</span>
    </div>
    """

    script = f"""
    (function() {{
        var colores = {datos_js};
        var capas = {capas_js};
        var horas = {horas_js};
        var i = 0;
        var jugando = false;
        var timer = null;

        function hex(c) {{ return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')'; }}

        function pintar(idx) {{
            for (var k = 0; k < capas.length; k++) {{
                var nombre = capas[k];
                var capa = window[nombre];
                if (capa && colores[nombre] && colores[nombre][idx]) {{
                    var c = colores[nombre][idx];
                    capa.setStyle({{fillColor: hex(c), color: hex(c), fillOpacity: 0.82, weight: 1}});
                }}
            }}
            var rotulo = document.getElementById("rotulo_{mapa_id}");
            if (rotulo) rotulo.innerText = "hora " + horas[idx];
            var rango = document.getElementById("rango_{mapa_id}");
            if (rango) rango.value = idx;
        }}

        function avanzar() {{
            i = (i + 1) % horas.length;
            pintar(i);
        }}

        function iniciarControles() {{
            var boton = document.getElementById("btn_{mapa_id}");
            var rango = document.getElementById("rango_{mapa_id}");
            var capasListas = capas.length > 0 && capas.every(function(n) {{ return window[n]; }});
            if (!boton || !rango || !capasListas) {{ return setTimeout(iniciarControles, 80); }}
            boton.addEventListener("click", function() {{
                jugando = !jugando;
                boton.innerText = jugando ? "pausa" : "reproducir";
                if (jugando) {{
                    timer = setInterval(avanzar, 260);
                }} else {{
                    clearInterval(timer);
                }}
            }});
            rango.addEventListener("input", function() {{
                i = parseInt(rango.value, 10);
                pintar(i);
            }});
            pintar(0);
            jugando = true;
            boton.innerText = "pausa";
            timer = setInterval(avanzar, 260);
        }}
        iniciarControles();

        function iniciarLluvia() {{
            var contenedor = document.getElementById("{mapa_id}");
            if (!contenedor || !contenedor.querySelector(".leaflet-pane")) {{
                return setTimeout(iniciarLluvia, 80);
            }}
            if (contenedor.querySelector(".lluvia-canvas")) return;
            var canvas = document.createElement("canvas");
            canvas.className = "lluvia-canvas";
            canvas.style.position = "absolute";
            canvas.style.top = "0"; canvas.style.left = "0";
            canvas.style.width = "100%"; canvas.style.height = "100%";
            canvas.style.pointerEvents = "none";
            canvas.style.zIndex = 650;
            contenedor.style.position = "relative";
            contenedor.appendChild(canvas);
            var ctx = canvas.getContext("2d");
            function ajustar() {{
                canvas.width = contenedor.clientWidth;
                canvas.height = contenedor.clientHeight;
            }}
            ajustar();
            window.addEventListener("resize", ajustar);
            var gotas = [];
            var n = 260;
            for (var g = 0; g < n; g++) {{
                gotas.push({{
                    x: Math.random() * canvas.width, y: Math.random() * canvas.height,
                    len: 8 + Math.random() * 16, vel: 7 + Math.random() * 9, drift: 1.4,
                }});
            }}
            function paso() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.strokeStyle = "rgba(200,222,255,0.55)";
                ctx.lineWidth = 1.1;
                for (var k = 0; k < gotas.length; k++) {{
                    var got = gotas[k];
                    ctx.beginPath();
                    ctx.moveTo(got.x, got.y);
                    ctx.lineTo(got.x - got.drift * 2, got.y + got.len);
                    ctx.stroke();
                    got.x -= got.drift; got.y += got.vel;
                    if (got.y > canvas.height) {{ got.y = -got.len; got.x = Math.random() * canvas.width; }}
                    if (got.x < 0) {{ got.x = canvas.width; }}
                }}
                requestAnimationFrame(paso);
            }}
            requestAnimationFrame(paso);
        }}
        iniciarLluvia();
    }})();
    """
    mapa.get_root().html.add_child(folium.Element(html))
    mapa.get_root().script.add_child(folium.Element(script))


def mapa_folium_real(df: pd.DataFrame, geo, variable: str = "osi", paso_horas: int = 4) -> folium.Map | None:
    """Condados reales (Census), mapa base real, cada condado cambia de
    color con la hora, lluvia cayendo encima. Solo con fipsCode real.
    `geo` es el geodataframe crudo de geo_condados (sin cruzar con df:
    los nombres de condado salen de df, la geometría de geo, cada uno
    con sus propias columnas, para no chocar con sufijos de merge)."""
    import warnings

    if geo is None or geo.empty or "fipsCode" not in df.columns:
        return None
    horas = np.sort(df["hour_idx"].unique())[::max(1, paso_horas)]
    if len(horas) < 2:
        return None

    fips_propios = set(df["fipsCode"].unique())
    geo_propio = geo[geo["fipsCode"].isin(fips_propios)].drop_duplicates("fipsCode")[["fipsCode", "geometry"]].copy()
    nombres = df.drop_duplicates("fipsCode").set_index("fipsCode")[["countyName", "stateAbbr"]]
    geo_propio = geo_propio.merge(nombres, left_on="fipsCode", right_index=True, how="left")
    pivote = df.pivot_table(index="hour_idx", columns="fipsCode", values=variable, aggfunc="first")
    pivote = pivote.reindex(columns=geo_propio["fipsCode"].to_numpy())
    vmax = float(np.nanpercentile(df[variable], 99.5)) or 1e-6
    vmax = max(vmax, 1e-6)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        centro_lat = float(geo_propio.geometry.centroid.y.mean())
        centro_lon = float(geo_propio.geometry.centroid.x.mean())

    mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=6, tiles="CartoDB dark_matter",
                      zoom_control=True)

    nombres_js, colores_por_hora = [], {}
    for _, fila in geo_propio.iterrows():
        vals = np.nan_to_num(pivote[fila["fipsCode"]].reindex(horas).to_numpy(dtype=float), nan=0.0)
        color0 = theme.color_escala_tormenta(float(vals[0]) / vmax)
        capa = folium.GeoJson(
            fila["geometry"].__geo_interface__,
            style_function=lambda _f, c=color0: {"fillColor": _rgb_css(c), "color": _rgb_css(c),
                                                 "weight": 1, "fillOpacity": 0.82},
            tooltip=f"{fila['countyName']}, {fila['stateAbbr']}",
        )
        capa.add_to(mapa)
        nombre_js = capa.get_name()
        nombres_js.append(nombre_js)
        colores_por_hora[nombre_js] = [theme.color_escala_tormenta(float(v) / vmax) for v in vals]

    _control_y_lluvia(mapa, nombres_js, colores_por_hora, list(horas), titulo=f"hora {int(horas[0])}")
    return mapa


def mapa_folium_simulado(df: pd.DataFrame, variable: str = "osi", paso_horas: int = 2) -> folium.Map | None:
    """La misma idea, pero sobre el plano simulado (crs Simple, sin mapa
    base real porque las coordenadas son inventadas) y celdas Voronoi en
    vez de condados administrativos."""
    if not {"posicion_x", "posicion_y", "hour_idx", variable}.issubset(df.columns):
        return None
    import viz

    horas = np.sort(df["hour_idx"].unique())[::max(1, paso_horas)]
    if len(horas) < 2:
        return None

    pos = df.groupby("fipsCode").agg(x=("posicion_x", "first"), y=("posicion_y", "first"),
                                     nombre=("countyName", "first")).reset_index()
    px, py = pos["x"].to_numpy(), pos["y"].to_numpy()
    x0, x1 = float(px.min() - 0.3), float(px.max() + 0.3)
    y0, y1 = float(py.min() - 0.3), float(py.max() + 0.3)
    celdas = viz._celdas_voronoi(px, py, x0, x1, y0, y1)

    pivote = df.pivot_table(index="hour_idx", columns="fipsCode", values=variable, aggfunc="first")
    pivote = pivote.reindex(columns=pos["fipsCode"].to_numpy())
    vmax = float(np.nanpercentile(df[variable], 99.5)) or 1e-6
    vmax = max(vmax, 1e-6)

    escala = 40.0
    mapa = folium.Map(location=[0, 0], zoom_start=3, tiles=None, crs="Simple", zoom_control=True)
    folium.Rectangle(bounds=[[y0 * escala, x0 * escala], [y1 * escala, x1 * escala]],
                     color="#26314A", weight=1, fill=True, fill_color="#0A0F1C", fill_opacity=1).add_to(mapa)
    mapa.fit_bounds([[y0 * escala, x0 * escala], [y1 * escala, x1 * escala]])

    nombres_js, colores_por_hora = [], {}
    for i, (fips, nombre, celda) in enumerate(zip(pos["fipsCode"], pos["nombre"], celdas)):
        if not len(celda):
            continue
        anillo = [[pt[1] * escala, pt[0] * escala] for pt in celda]
        vals = np.nan_to_num(pivote[fips].reindex(horas).to_numpy(dtype=float), nan=0.0)
        color0 = theme.color_escala_tormenta(float(vals[0]) / vmax)
        capa = folium.Polygon(anillo, color=_rgb_css(color0), weight=1, fill=True,
                              fill_color=_rgb_css(color0), fill_opacity=0.82, tooltip=str(nombre))
        capa.add_to(mapa)
        nombre_js = capa.get_name()
        nombres_js.append(nombre_js)
        colores_por_hora[nombre_js] = [theme.color_escala_tormenta(float(v) / vmax) for v in vals]

    _control_y_lluvia(mapa, nombres_js, colores_por_hora, list(horas), titulo=f"hora {int(horas[0])}")
    return mapa

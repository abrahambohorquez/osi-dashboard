"""
El sistema visual del sitio: paleta, tipografía, escala de niveles, tema de
Plotly y el CSS compartido. Un único lugar de verdad.

Nota de dirección de arte
-------------------------
Esto no imita "un dashboard bonito": imita la gramática de publicación de una
agencia meteorológica estadounidense, que es una cosa bastante específica y
bastante distinta de una app. Lo que se tomó de cada referencia:

* spc.noaa.gov  -> la escala categórica numerada (1 MRGL ... 5 HIGH) con
  rellenos pastel y texto oscuro, siempre visible completa, y la densidad
  informativa: un producto muestra el nivel, el número, el umbral y la
  vigencia, no solo una palabra.
* nhc.noaa.gov  -> el "advisory": cabecera con nombre y número de producto,
  vitales en monoespaciada, titular en mayúsculas envuelto en puntos
  suspensivos (...OSI PEAKS DURING SECOND WAVE...), y la lista de estado
  actual en viñetas en vez de un párrafo.
* weather.gov   -> la estructura de sitio oficial: franja de utilidad, bloque
  de oficina/unidad sobre el H1, migas de pan en cada página, e índice de
  secciones agrupado (no pestañas planas).
* iii.org       -> el aire y el tono: una columna narrativa, párrafo de
  entradilla que explica y atribuye la fuente ANTES del gráfico, figuras
  numeradas, y bloque de "ver también" al final.

Ninguna insignia, sello ni marca ".gov" se reproduce: solo el lenguaje de
maquetación, color y tipografía. Es un proyecto estudiantil y la franja
superior lo dice de forma explícita.

Modo oscuro: como Streamlit reejecuta el script en cada interacción, no hace
falta CSS con variables ni JavaScript. `inyectar_estilos()` mira
`st.session_state.modo_oscuro` y escribe el bloque que toca; `aplicar_tema()`
hace lo mismo con las figuras.
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------
# Paleta. El azul y el rojo siguen siendo los tonos de bandera que usan
# NHC/NWS, pero ahora hay tres azules distintos y no uno: la franja de
# utilidad es casi negra, la cabecera es el azul institucional y la barra
# de secciones es un intermedio. Esa jerarquía de tres bandas es lo que
# hace que una cabecera lea como un sitio y no como una barra de app.
# ---------------------------------------------------------------------
INK = "#0A3161"          # azul institucional (cabecera, titulares)
INK_DEEP = "#041E42"     # franja de utilidad, casi negra
INK_MID = "#16406F"      # barra de secciones
INK_SOFT = "#33547E"     # texto de parrafo
PAPER = "#F4F4F2"
PANEL = "#FFFFFF"
BORDER = "#C9CDD2"
BORDER_SOFT = "#E6E8E6"
MUTED = "#5B6670"
ACCENT = "#9A6608"       # dorado de detalle (reglas, numeracion, enfasis)
ACCENT_SOFT = "#FBEFD9"
OK = "#1B7F4C"
OK_SOFT = "#E3F1E9"
ORANGE = "#B8480C"
ORANGE_SOFT = "#FBE4D5"
WARN = "#B31942"
WARN_SOFT = "#F7E0E6"
GRID = "#E4E6E8"

DARK_INK = "#E7ECF7"
DARK_INK_DEEP = "#05080F"
DARK_INK_MID = "#16233A"
DARK_INK_SOFT = "#B9C6E4"
DARK_PAPER = "#0A0F1C"
DARK_PANEL = "#121A2C"
DARK_BORDER = "#26314A"
DARK_BORDER_SOFT = "#1B2438"
DARK_MUTED = "#8B98B5"
DARK_ACCENT = "#E3A83A"
DARK_ACCENT_SOFT = "#3A2E14"
DARK_OK = "#4FAE85"
DARK_OK_SOFT = "#12251C"
DARK_ORANGE = "#E0834D"
DARK_ORANGE_SOFT = "#3A2412"
DARK_WARN = "#E08872"
DARK_WARN_SOFT = "#301712"
DARK_GRID = "#1E2740"

# Public Sans es la tipografia del U.S. Web Design System. Sin serif en
# ningun lado, a proposito. La monoespaciada no es decorativa: separa
# categoricamente el dato del texto, que es la convencion de los productos
# de texto de la NWS.
FONT_DISPLAY = "'Public Sans', system-ui, sans-serif"
FONT_BODY = "'Public Sans', system-ui, sans-serif"
FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace"

# ---------------------------------------------------------------------
# Escala categorica de severidad, cinco niveles.
#
# La gramatica viene del outlook convectivo del SPC: numero de categoria +
# abreviatura de cuatro letras + nombre largo + relleno pastel con texto
# oscuro. Los nombres son propios (el fenomeno es otro: severidad de
# interrupcion electrica, no riesgo convectivo), pero la forma es la misma,
# y por eso la cinta se lee como un producto y no como cuatro pastillas de
# colores. Los umbrales estan en OSI y se documentan en la propia cinta.
# ---------------------------------------------------------------------
NIVELES = [
    # clave, n, abrev, nombre, relleno, texto, borde, desde, hasta
    ("mnml", "1", "MNML", "Minimal", "#DCEEDC", "#1D4620", "#66A366", 0.00, 0.02),
    ("lmtd", "2", "LMTD", "Limited", "#FFE9A8", "#6B5200", "#E8B62E", 0.02, 0.08),
    ("elev", "3", "ELEV", "Elevated", "#FFD2AE", "#7A3A0C", "#E58A4B", 0.08, 0.20),
    ("majr", "4", "MAJR", "Major", "#F3B7B7", "#7A1620", "#D06868", 0.20, 0.35),
    ("extr", "5", "EXTR", "Extreme", "#EBC2EE", "#5B1466", "#C77FCE", 0.35, 9.99),
]

NIVEL_POR_CLAVE = {n[0]: n for n in NIVELES}

# Compatibilidad con las llamadas antiguas (calm / watch / warning / severe).
# Ninguna hoja se rompe si todavia usa el vocabulario anterior.
ALIAS_NIVEL = {
    "calm": "mnml", "watch": "lmtd", "warning": "elev",
    "severe": "majr", "extreme": "extr",
}


def normalizar_nivel(nivel: str) -> str:
    """Acepta tanto las claves nuevas (mnml/lmtd/elev/majr/extr) como el
    vocabulario antiguo (calm/watch/warning/severe) y devuelve siempre una
    clave nueva valida."""
    nivel = (nivel or "").lower()
    nivel = ALIAS_NIVEL.get(nivel, nivel)
    return nivel if nivel in NIVEL_POR_CLAVE else "mnml"


def nivel_para_osi(valor) -> str:
    """La categoria que corresponde a un valor de OSI. Un solo sitio decide
    esto, para que la cinta, la insignia y el titular nunca discrepen."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "mnml"
    for clave, _n, _a, _nom, _f, _t, _b, desde, hasta in NIVELES:
        if desde <= v < hasta:
            return clave
    return "extr"


def datos_nivel(nivel: str) -> dict:
    clave = normalizar_nivel(nivel)
    c, n, abrev, nombre, relleno, texto, borde, desde, hasta = NIVEL_POR_CLAVE[clave]
    return dict(clave=c, numero=n, abrev=abrev, nombre=nombre, relleno=relleno,
                texto=texto, borde=borde, desde=desde, hasta=hasta)


def rango_nivel(nivel: str) -> str:
    """El umbral del nivel escrito como se escribe en una leyenda
    ('0.08-0.20', '0.35+'). Va debajo de cada peldano de la cinta: densidad
    informativa en vez de una palabra suelta."""
    d = datos_nivel(nivel)
    if d["hasta"] >= 9:
        return f"{d['desde']:.2f}+"
    return f"{d['desde']:.2f}-{d['hasta']:.2f}"


COLOR_POR_VARIABLE = {
    "gust": "#B3271E",
    "wind_speed_10m": "#2471A3",
    "mslma": "#6C3483",
    "sp": "#8E44AD",
    "tp": "#117864",
    "rain": "#1ABC9C",
    "csnow": "#5DADE2",
    "soil_moist": "#7D6608",
    "r2": "#909497",
    "blh": "#AF601A",
    "t2m": "#CB4335",
    "osi": "#0A2472",
    "P_t": "#0A2472",
    "N_t": "#B3271E",
    "D_t": "#117864",
    "R_t": "#7D6608",
}

ETIQUETAS_VARIABLE = {
    "gust": "wind gust (mph)",
    "wind_speed_10m": "sustained wind (mph)",
    "mslma": "sea-level pressure (hPa)",
    "sp": "surface pressure (hPa)",
    "tp": "total precipitation (mm)",
    "rain": "rain (mm)",
    "csnow": "snow (cm)",
    "soil_moist": "soil moisture (m3/m3)",
    "r2": "relative humidity (%)",
    "blh": "boundary layer height (m)",
    "t2m": "temperature at 2m (K)",
    "osi": "OSI",
    "P_t": "P_t, share without power",
    "N_t": "N_t, new failures",
    "D_t": "D_t, 6h persistence",
    "R_t": "R_t, restoration",
}

DIVERGENTE = [[0, WARN], [0.5, "#FFFFFF"], [1, INK]]
SECUENCIAL_SEVERIDAD = [[0, "#EAF0FA"], [0.35, "#8FA9D6"], [0.7, ACCENT], [1, WARN]]

# La escala del campo de tormenta usa exactamente los rellenos de la escala
# categorica de arriba, en el mismo orden. Asi el mapa y la cinta no son dos
# lenguajes de color distintos: un condado naranja en el mapa esta,
# literalmente, en el peldano naranja de la cinta.
ESCALA_TORMENTA = [
    [0.00, "#F4F4F2"],
    [0.14, "#DCEEDC"],
    [0.34, "#FFE9A8"],
    [0.58, "#FFD2AE"],
    [0.80, "#F3B7B7"],
    [1.00, "#C77FCE"],
]


def color_escala_tormenta(t: float) -> tuple[int, int, int]:
    """Un color RGB (0-255) interpolado sobre ESCALA_TORMENTA para un t entre
    0 y 1. Sirve para capas que no hablan colorscales de Plotly (pydeck, por
    ejemplo) pero deben verse igual que el resto."""
    t = min(1.0, max(0.0, t))
    paradas = ESCALA_TORMENTA
    for (t0, c0), (t1, c1) in zip(paradas, paradas[1:]):
        if t0 <= t <= t1:
            frac = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            r0, g0, b0 = int(c0[1:3], 16), int(c0[3:5], 16), int(c0[5:7], 16)
            r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
            return (round(r0 + (r1 - r0) * frac), round(g0 + (g1 - g0) * frac),
                    round(b0 + (b1 - b0) * frac))
    return (int(paradas[-1][1][1:3], 16), int(paradas[-1][1][3:5], 16),
            int(paradas[-1][1][5:7], 16))


PLOTLY_LAYOUT = dict(
    paper_bgcolor=PANEL,
    plot_bgcolor=PANEL,
    font=dict(family=FONT_BODY, color=INK, size=12.5),
    margin=dict(l=54, r=20, t=26, b=44),
    legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor=BORDER, borderwidth=1),
)
PLOTLY_AXIS = dict(
    gridcolor=GRID, zerolinecolor=BORDER, showline=True, linecolor=BORDER,
    tickfont=dict(color=MUTED, size=11),
)


def modo_oscuro() -> bool:
    return bool(st.session_state.get("modo_oscuro", False))


def paleta() -> dict:
    """Los colores activos segun el modo actual. Usalo en vez de las
    constantes sueltas cuando una figura o un bloque de CSS si necesita
    responder al modo oscuro."""
    if modo_oscuro():
        return dict(ink=DARK_INK, ink_deep=DARK_INK_DEEP, ink_mid=DARK_INK_MID,
                    ink_soft=DARK_INK_SOFT, paper=DARK_PAPER, panel=DARK_PANEL,
                    border=DARK_BORDER, border_soft=DARK_BORDER_SOFT, muted=DARK_MUTED,
                    accent=DARK_ACCENT, accent_soft=DARK_ACCENT_SOFT, ok=DARK_OK,
                    ok_soft=DARK_OK_SOFT, orange=DARK_ORANGE, orange_soft=DARK_ORANGE_SOFT,
                    warn=DARK_WARN, warn_soft=DARK_WARN_SOFT, grid=DARK_GRID)
    return dict(ink=INK, ink_deep=INK_DEEP, ink_mid=INK_MID, ink_soft=INK_SOFT,
                paper=PAPER, panel=PANEL, border=BORDER, border_soft=BORDER_SOFT,
                muted=MUTED, accent=ACCENT, accent_soft=ACCENT_SOFT, ok=OK,
                ok_soft=OK_SOFT, orange=ORANGE, orange_soft=ORANGE_SOFT,
                warn=WARN, warn_soft=WARN_SOFT, grid=GRID)


def aplicar_tema(fig, titulo: str | None = None, altura: int = 380):
    """Aplica el tema de Plotly, consciente del modo oscuro.

    El titulo va pequeno y en mayusculas a proposito: cuando la figura vive
    dentro de `components.figura()`, el titulo real es el de la ficha
    ("FIGURE 3 - ..."), y un titular grande dentro del lienzo compite con
    el. Las figuras que todavia se dibujan sueltas siguen funcionando igual
    que antes."""
    p = paleta()
    fig.update_layout(
        paper_bgcolor=p["panel"], plot_bgcolor=p["panel"], height=altura,
        font=dict(family=FONT_BODY, color=p["ink"], size=12.5),
        margin=dict(l=54, r=20, t=44 if titulo else 24, b=44),
        legend=dict(bgcolor=p["panel"], bordercolor=p["border"], borderwidth=1,
                    font=dict(size=11)),
    )
    if titulo:
        fig.update_layout(title=dict(
            text=str(titulo).upper(),
            font=dict(family=FONT_BODY, size=11.5, color=p["muted"]),
            x=0, xanchor="left",
        ))
    eje = dict(gridcolor=p["grid"], zerolinecolor=p["border"], showline=True,
               linecolor=p["border"], tickfont=dict(color=p["muted"], size=11))
    fig.update_xaxes(**eje)
    fig.update_yaxes(**eje)
    return fig


def _css_niveles() -> str:
    """Una regla por peldano de la escala. Se genera desde NIVELES para que
    anadir o mover un nivel no obligue a tocar el CSS a mano."""
    reglas = []
    for clave, _n, _a, _nom, relleno, texto, borde, _d, _h in NIVELES:
        reglas.append(
            f".lvl-{clave} {{ background:{relleno}; color:{texto} !important; "
            f"border-color:{borde}; }}\n"
            f".bar-{clave} {{ background:{borde}; }}\n"
            f".rule-{clave} {{ border-left-color:{borde} !important; }}"
        )
    return "\n".join(reglas)


def _bloque_css(p: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ------------------------------------------------------------------
   RITMO. Todo el espaciado vertical del sitio sale de estos valores.
   Antes cada bloque traia su propio margen inventado (26px aqui, 22px
   alla, 42px mas abajo) y por eso el conjunto "casi" se alineaba sin
   llegar a hacerlo nunca. Ahora hay una reticula.
   ------------------------------------------------------------------ */
:root {{
    --bloque: 24px;    /* separacion entre piezas de un mismo apartado */
    --apartado: 44px;  /* separacion entre apartados */
    --hair: 1px solid {p['border']};
}}

html, body, [class*="css"] {{ font-family: {FONT_BODY}; }}
.stApp {{ background: {p['paper']}; }}

/* Columna de lectura acotada y algo mas estrecha que antes: 1120px con
   texto a 15px da una medida de linea de ~85 caracteres, que es donde
   dejan de leerse comodamente los parrafos largos. */
[data-testid="stMain"] .block-container, .main .block-container {{
    max-width: 1120px; margin-left: auto; margin-right: auto;
    padding-top: 0 !important;
}}

/* La barra lateral repite el indice de secciones completo, como el rail
   izquierdo de una oficina de weather.gov. Va colapsada por defecto: es
   redundancia deliberada, no la navegacion principal. */
[data-testid="stSidebar"] {{ background: {p['ink_deep']}; }}
[data-testid="stSidebar"] * {{ color: #DCE4F2 !important; }}
[data-testid="stSidebar"] a {{ color: #DCE4F2 !important; }}
.idx-grupo {{
    font-family: {FONT_BODY}; font-size: 10px; font-weight: 800; letter-spacing: 1.6px;
    text-transform: uppercase; color: #E8C77A !important;
    padding: 14px 0 4px; border-bottom: 1px solid rgba(255,255,255,0.14); margin-bottom: 2px;
}}
.idx-nota {{
    font-family: {FONT_MONO}; font-size: 10px; line-height: 1.7;
    color: #7E90AF !important; padding-top: 18px;
}}

h1, h2, h3, h4 {{ font-family: {FONT_DISPLAY}; color: {p['ink']}; }}
p, li, span, label, div {{ color: {p['ink_soft']}; }}
[data-testid="stMarkdownContainer"] p {{ color: {p['ink_soft']}; font-size: 15px; line-height: 1.7; }}
[data-testid="stMetricValue"] {{ font-family: {FONT_DISPLAY}; color: {p['ink']}; }}

/* Cifras siempre tabulares. Una columna de numeros que baila de ancho es
   la senal mas rapida de que nadie reviso la maqueta. */
[data-testid="stMetricValue"], .mcard .val, .stat-lead .val, .dc-row .v,
.vitals .v, .figframe .fnum {{ font-variant-numeric: tabular-nums; }}

/* ==================================================================
   1. CABECERA EN TRES BANDAS
   Franja de utilidad (casi negra) / cabecera institucional (azul) /
   indice de secciones (azul medio). Esa progresion de tres tonos es lo
   que distingue la cabecera de un sitio de la toolbar de una app.
   ================================================================== */
.site-strip {{
    margin: -1rem -1rem 0; padding: 5px 1.4rem;
    background: {p['ink_deep']}; display: flex; justify-content: space-between;
    align-items: center; gap: 16px; flex-wrap: wrap;
}}
.site-strip span {{
    font-family: {FONT_BODY}; font-size: 10px; letter-spacing: 1.3px;
    text-transform: uppercase; font-weight: 600; color: #93A6C6 !important;
}}
.site-strip .aviso {{ color: #E8C77A !important; }}

.masthead {{
    margin: 0 -1rem; padding: 16px 1.4rem 15px; background: {p['ink']};
    display: flex; justify-content: space-between; align-items: flex-end;
    gap: 24px; flex-wrap: wrap; border-bottom: 3px solid {p['warn']};
}}
.masthead .unidad {{ display: flex; flex-direction: column; gap: 3px; }}
.masthead .unidad .l1 {{
    font-family: {FONT_DISPLAY}; font-weight: 900; font-size: 20px; letter-spacing: .4px;
    color: #FFFFFF !important; line-height: 1.05;
}}
.masthead .unidad .l2 {{
    font-family: {FONT_BODY}; font-weight: 600; font-size: 11px; letter-spacing: 1.7px;
    text-transform: uppercase; color: #A9BEDD !important;
}}
/* El sello de emision. Monoespaciada, alineada a la derecha, con el
   identificador de producto arriba: la firma de un producto operativo. */
.masthead .sello {{ text-align: right; font-family: {FONT_MONO}; line-height: 1.55; }}
.masthead .sello .id {{
    font-size: 12px; font-weight: 600; color: #FFFFFF !important; letter-spacing: .6px;
}}
.masthead .sello .meta {{ font-size: 10.5px; color: #93A6C6 !important; letter-spacing: .3px; }}

/* Indice de secciones: enlaces agrupados bajo un rotulo de seccion, no
   once pestanas planas en fila. El rotulo dorado separa los grupos. */
.st-key-navbar_links {{
    background: {p['ink_mid']}; margin: 0 -1rem var(--apartado); padding: 2px 1rem 3px;
    border-bottom: 1px solid rgba(255,255,255,0.10);
}}
.st-key-navbar_links div[data-testid="stHorizontalBlock"] {{
    flex-wrap: wrap; gap: 0; row-gap: 0; align-items: center;
}}
.st-key-navbar_links div[data-testid="stColumn"] {{
    width: fit-content !important; flex: 0 0 auto !important; min-width: 0 !important;
}}
.st-key-navbar_links a, .st-key-navbar_links p {{
    color: #C7D5EC !important; text-decoration: none; font-size: 11.5px;
    padding: 9px 9px !important; font-family: {FONT_BODY}; white-space: nowrap;
    letter-spacing: .2px; font-weight: 600; border-bottom: 2px solid transparent;
    display: inline-block; margin: 0 !important;
}}
.st-key-navbar_links a:hover {{ color: #FFFFFF !important; border-bottom-color: #E8C77A; }}
.st-key-navbar_links a[aria-current] {{
    color: #FFFFFF !important; border-bottom-color: #FFFFFF;
}}
.navgroup {{
    display: inline-block; font-family: {FONT_BODY}; font-size: 9.5px; font-weight: 800;
    letter-spacing: 1.5px; text-transform: uppercase; color: #E8C77A !important;
    padding: 9px 10px 9px 16px; border-left: 1px solid rgba(255,255,255,0.16);
    white-space: nowrap;
}}
.navgroup.primero {{ border-left: none; padding-left: 0; }}

/* ==================================================================
   2. CABECERA DE PAGINA
   Migas > rotulo de seccion > H1 > entradilla > franja de metadatos.
   La franja de metadatos en monoespaciada bajo el titulo es lo que hace
   que una pagina parezca fechada y versionada en vez de decorativa.
   ================================================================== */
.breadcrumb {{
    font-family: {FONT_BODY}; font-size: 11.5px; color: {p['muted']} !important;
    margin-bottom: 18px; letter-spacing: .1px;
}}
.breadcrumb .sep {{ color: {p['border']} !important; padding: 0 6px; }}
.breadcrumb .actual {{ color: {p['ink']} !important; font-weight: 600; }}

.page-head {{ margin-bottom: var(--bloque); }}
.page-head .kicker {{
    font-family: {FONT_BODY}; font-weight: 800; font-size: 10.5px; letter-spacing: 2.2px;
    text-transform: uppercase; color: {p['accent']} !important; margin-bottom: 7px;
}}
.page-head h1 {{
    margin: 0 0 12px; font-size: 30px; line-height: 1.18; color: {p['ink']};
    font-weight: 800; letter-spacing: -.3px; max-width: 24ch;
}}
.page-head .lede {{
    color: {p['ink_soft']} !important; font-size: 16px; max-width: 66ch;
    margin: 0; line-height: 1.68;
}}
/* Metadatos de la pagina: que archivo, cuantas filas, cuando se calculo.
   Reglas arriba y abajo, monoespaciada, minuscula. */
.metaline {{
    display: flex; flex-wrap: wrap; gap: 0 26px; margin: 20px 0 var(--apartado);
    padding: 8px 0; border-top: 2px solid {p['ink']}; border-bottom: var(--hair);
    font-family: {FONT_MONO}; font-size: 11px; color: {p['muted']} !important;
    letter-spacing: .2px;
}}
.metaline b {{ color: {p['ink']} !important; font-weight: 600; }}

/* ==================================================================
   3. LENGUAJE DE PRODUCTO (SPC / NHC)
   ================================================================== */
{_css_niveles()}

/* Cinta categorica: los cinco peldanos siempre visibles, numerados, con
   el umbral debajo y el vigente marcado con una barra superior gruesa.
   Relleno pastel y texto oscuro, como el mapa del SPC. */
.riskband {{ margin: 0 0 var(--bloque); }}
.riskband .cabecera {{
    display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
    flex-wrap: wrap; margin-bottom: 6px;
}}
.riskband .cabecera .t {{
    font-family: {FONT_BODY}; font-size: 10.5px; font-weight: 800; letter-spacing: 1.6px;
    text-transform: uppercase; color: {p['ink']} !important;
}}
.riskband .cabecera .s {{
    font-family: {FONT_MONO}; font-size: 10.5px; color: {p['muted']} !important;
}}
.riskband .escala {{ display: flex; gap: 2px; }}
.riskband .peldano {{
    flex: 1; text-align: center; padding: 7px 4px 6px; border: 1px solid;
    opacity: .5; position: relative;
}}
.riskband .peldano .cat {{
    font-family: {FONT_BODY}; font-weight: 800; font-size: 11.5px; letter-spacing: .9px;
    display: block; line-height: 1.25;
}}
.riskband .peldano .um {{
    font-family: {FONT_MONO}; font-size: 9.5px; opacity: .78; display: block;
    letter-spacing: -.2px;
}}
.riskband .peldano.activo {{ opacity: 1; box-shadow: inset 0 4px 0 0 currentColor; }}
.riskband .nota {{
    font-family: {FONT_MONO}; font-size: 10.5px; color: {p['muted']} !important;
    margin-top: 5px; letter-spacing: .1px;
}}

/* Titular en mayusculas envuelto en puntos suspensivos. Es la firma
   tipografica de los productos de texto de la NWS y, junto con las
   migas, lo que mas aleja esto de "otra app con tarjetas". */
.headline-caps {{
    font-family: {FONT_MONO}; font-weight: 600; font-size: 15px; letter-spacing: .4px;
    color: {p['ink']} !important; margin: 0 0 var(--bloque); padding: 12px 0;
    border-top: 2px solid {p['ink']}; border-bottom: 2px solid {p['ink']};
    text-transform: uppercase; line-height: 1.5;
}}

/* Advisory: cabecera solida con nombre y numero de producto, vitales en
   monoespaciada con linea de puntos, y pie de vigencia. */
.advisory {{ border: var(--hair); background: {p['panel']}; margin: 0 0 var(--bloque); }}
.advisory .dc-head {{
    background: {p['ink']}; color: #FFFFFF !important; display: flex;
    justify-content: space-between; align-items: baseline; gap: 12px;
    font-family: {FONT_BODY}; font-weight: 800; font-size: 11.5px; letter-spacing: 1.3px;
    text-transform: uppercase; padding: 9px 15px;
}}
.advisory .dc-head .num {{
    font-family: {FONT_MONO}; font-weight: 500; font-size: 11px; letter-spacing: .4px;
    color: #A9BEDD !important; text-transform: none;
}}
.advisory .dc-row {{
    display: flex; align-items: baseline; gap: 10px; padding: 7px 15px;
    border-top: 1px solid {p['border_soft']}; font-family: {FONT_MONO}; font-size: 12.5px;
}}
.advisory .dc-row .k {{
    color: {p['muted']} !important; letter-spacing: .2px; white-space: nowrap;
    text-transform: uppercase; font-size: 11px;
}}
/* Linea de puntos entre etiqueta y valor: la convencion de una tabla de
   vitales impresa, y de paso resuelve la alineacion sin una tabla. */
.advisory .dc-row .fill {{
    flex: 1; border-bottom: 1px dotted {p['border']}; transform: translateY(-3px);
}}
.advisory .dc-row .v {{ color: {p['ink']} !important; font-weight: 600; white-space: nowrap; }}
.advisory .dc-foot {{
    border-top: var(--hair); padding: 7px 15px; background: {p['paper']};
    font-family: {FONT_MONO}; font-size: 10.5px; color: {p['muted']} !important;
    display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
}}

/* Lista de estado en vinetas, al modo de "Top News of the Day" de la NHC:
   que esta vigente ahora mismo, una linea por cosa, sin parrafo. */
.statuslist {{ margin: 0 0 var(--bloque); padding: 0; list-style: none; }}
.statuslist li {{
    padding: 7px 0 7px 20px; border-bottom: 1px solid {p['border_soft']};
    font-size: 14.5px; color: {p['ink_soft']} !important; line-height: 1.55;
    position: relative;
}}
.statuslist li::before {{
    content: ""; position: absolute; left: 2px; top: 15px;
    width: 7px; height: 7px; background: {p['accent']};
}}
.statuslist li b {{ color: {p['ink']} !important; }}
.statuslist li .cuando {{
    font-family: {FONT_MONO}; font-size: 11px; color: {p['muted']} !important; margin-left: 6px;
}}

.status-badge {{
    display: inline-block; font-family: {FONT_MONO}; font-size: 10.5px; font-weight: 600;
    letter-spacing: .5px; padding: 2px 7px; border: 1px solid; vertical-align: middle;
    white-space: nowrap;
}}

/* ==================================================================
   4. JERARQUIA DE CIFRAS
   Tres niveles explicitos y distintos: titular (una por pagina, enorme),
   fila de vitales (secundaria, monoespaciada, en caja), nota al pie
   (terciaria, 11px). Antes todo era la misma tarjeta de 40px y por eso
   no habia jerarquia que leer.
   ================================================================== */
.stat-lead {{
    display: flex; align-items: flex-start; gap: 22px; margin: 0 0 var(--bloque);
    padding: 0 0 18px; border-bottom: 2px solid {p['ink']};
}}
.stat-lead .val {{
    font-family: {FONT_DISPLAY}; font-size: 62px; font-weight: 800; line-height: .92;
    color: {p['ink']} !important; letter-spacing: -2px; flex-shrink: 0;
}}
.stat-lead .lado {{ padding-top: 4px; }}
.stat-lead .lbl {{
    font-family: {FONT_BODY}; font-weight: 800; font-size: 10.5px; letter-spacing: 1.8px;
    text-transform: uppercase; color: {p['accent']} !important; margin-bottom: 6px;
}}
.stat-lead .sub {{
    font-size: 14px; color: {p['ink_soft']} !important; line-height: 1.6;
    max-width: 58ch; margin: 0;
}}

/* Fila de vitales: una caja con separadores verticales, no cuatro
   tarjetas flotando. Un bloque, no cuatro objetos. */
.vitals {{
    border: var(--hair); border-top: 3px solid {p['ink']}; background: {p['panel']};
    padding: 14px 0; margin: 0 0 var(--bloque);
}}
.vitals .celda {{ padding: 0 18px; border-left: var(--hair); }}
.vitals .celda.primera {{ border-left: none; }}
.vitals .k {{
    font-family: {FONT_BODY}; font-weight: 700; font-size: 10px; letter-spacing: 1.4px;
    text-transform: uppercase; color: {p['muted']} !important; margin-bottom: 5px;
}}
.vitals .v {{
    font-family: {FONT_MONO}; font-size: 23px; font-weight: 600;
    color: {p['ink']} !important; line-height: 1.1;
}}
.vitals .s {{ font-size: 11.5px; color: {p['muted']} !important; margin-top: 4px; line-height: 1.4; }}

/* La tarjeta antigua se conserva para las hojas que aun la usan, pero
   alineada al ritmo nuevo y bastante mas contenida que antes. */
.mcard {{ border-top: 3px solid {p['accent']}; padding: 14px 16px 4px 0; height: 100%; }}
.mcard.tone-ok {{ border-top-color: {p['ok']}; }}
.mcard.tone-warn {{ border-top-color: {p['warn']}; }}
.mcard.tone-ink {{ border-top-color: {p['ink']}; }}
.mcard .lbl {{
    font-family: {FONT_BODY}; font-weight: 700; font-size: 10px; letter-spacing: 1.4px;
    text-transform: uppercase; color: {p['muted']} !important; margin-bottom: 6px;
}}
.mcard .val {{
    font-family: {FONT_MONO}; font-size: 23px; font-weight: 600;
    color: {p['ink']} !important; line-height: 1.1;
}}
.mcard .sub {{ font-size: 11.5px; color: {p['muted']} !important; margin-top: 4px; line-height: 1.4; }}

/* ==================================================================
   5. FIGURAS
   Una figura es una pieza citable: numero, titulo, grafico, y una linea
   de fuente debajo. Numerar las figuras es la diferencia entre un
   informe y una pantalla con graficas sueltas.
   ================================================================== */
.figframe {{ margin: 0 0 4px; }}
.figframe .cab {{
    display: flex; align-items: baseline; gap: 10px; padding-bottom: 7px;
    border-bottom: 2px solid {p['ink']}; margin-bottom: 2px; flex-wrap: wrap;
}}
.figframe .fnum {{
    font-family: {FONT_MONO}; font-size: 10.5px; font-weight: 600; letter-spacing: .8px;
    text-transform: uppercase; color: {p['accent']} !important; white-space: nowrap;
}}
.figframe .ftit {{
    font-family: {FONT_BODY}; font-size: 14px; font-weight: 700; color: {p['ink']} !important;
    line-height: 1.35;
}}
.figsource {{
    font-family: {FONT_MONO}; font-size: 10.5px; color: {p['muted']} !important;
    border-top: var(--hair); padding-top: 6px; margin: 0 0 var(--apartado);
    line-height: 1.6; letter-spacing: .1px;
}}
.figsource b {{ color: {p['ink_soft']} !important; font-weight: 600; }}

/* ==================================================================
   6. TEXTO Y APARTADOS
   ================================================================== */
.section-head {{
    display: flex; align-items: baseline; gap: 12px; margin: var(--apartado) 0 14px;
    padding-bottom: 8px; border-bottom: 2px solid {p['ink']};
}}
.section-head .snum {{
    font-family: {FONT_MONO}; font-weight: 600; font-size: 12px; color: {p['accent']} !important;
    letter-spacing: .5px; flex-shrink: 0;
}}
.section-head h3 {{
    font-family: {FONT_DISPLAY}; font-weight: 800; font-size: 18px; color: {p['ink']};
    margin: 0; letter-spacing: -.1px;
}}

/* Entradilla de apartado, al modo de iii.org: el parrafo que explica que
   muestra el grafico y de donde sale el numero va ANTES del grafico, no
   como pie de foto despues. */
.standfirst {{
    font-size: 15px; line-height: 1.72; color: {p['ink_soft']} !important;
    max-width: 74ch; margin: 0 0 var(--bloque);
}}
.standfirst b {{ color: {p['ink']} !important; }}

.finding {{
    border-left: 3px solid {p['accent']}; padding: 4px 0 4px 18px; margin: 0 0 var(--bloque);
}}
.finding.tone-accent {{ border-left-color: {p['accent']}; }}
.finding.tone-ok {{ border-left-color: {p['ok']}; }}
.finding.tone-warn {{ border-left-color: {p['warn']}; }}
.finding.tone-ink {{ border-left-color: {p['ink']}; }}
.finding .flabel {{
    font-family: {FONT_BODY}; font-weight: 800; font-size: 10.5px; letter-spacing: 1.6px;
    text-transform: uppercase; margin-bottom: 7px;
}}
.finding.tone-accent .flabel {{ color: {p['accent']} !important; }}
.finding.tone-ok .flabel {{ color: {p['ok']} !important; }}
.finding.tone-warn .flabel {{ color: {p['warn']} !important; }}
.finding.tone-ink .flabel {{ color: {p['ink']} !important; }}
.finding p {{ margin: 0; color: {p['ink_soft']} !important; font-size: 14.5px; line-height: 1.7; }}
.finding p b {{ color: {p['ink']} !important; }}

/* Nota de procedencia de los datos. Sin fondo de color y sin icono: una
   regla lateral y letra pequena, como una nota al pie metodologica. */
.banner-sim {{
    border-left: 3px solid {p['accent']}; padding: 6px 0 6px 18px; margin: 0 0 var(--apartado);
    font-family: {FONT_MONO}; font-size: 11.5px; line-height: 1.65;
    color: {p['muted']} !important; max-width: 82ch;
}}
.banner-sim, .banner-sim * {{ color: {p['muted']} !important; }}
.banner-sim b, .banner-sim b * {{ color: {p['ink']} !important; font-weight: 600; }}

.pull-quote {{
    border-left: 4px solid {p['accent']}; padding: 2px 0 2px 20px; margin: 0 0 var(--bloque);
    font-family: {FONT_DISPLAY}; font-size: 19px; font-weight: 600; color: {p['ink']};
    line-height: 1.5; max-width: 56ch;
}}

.card {{ background: {p['panel']}; border: var(--hair); padding: 16px 18px; height: 100%; }}
.card h4 {{ font-family: {FONT_DISPLAY}; margin: 0 0 7px; color: {p['ink']}; font-size: 15px; }}
.card p {{ color: {p['muted']} !important; font-size: 13px; line-height: 1.65; margin: 0; }}

.chip {{
    display: inline-flex; align-items: center; gap: 6px; font-family: {FONT_MONO};
    font-size: 10.5px; padding: 3px 8px; background: {p['paper']};
    color: {p['muted']} !important; border: var(--hair);
}}

/* Aviso de momento concreto dentro de una animacion. Ahora hereda el
   color del peldano de la escala en vez de tener su propio dorado. */
.event-banner {{
    padding: 9px 15px; margin: 0 0 10px; font-family: {FONT_MONO}; font-size: 12px;
    border: 1px solid {p['border']}; border-left: 4px solid {p['ink']};
    background: {p['panel']}; color: {p['ink']} !important; letter-spacing: .1px;
}}

/* Indice de contenidos en forma de tabla de productos, no de tarjetas.
   Una fila por pagina: numero, nombre, descripcion, seccion. */
.toc {{ border-top: 2px solid {p['ink']}; margin: 0 0 var(--apartado); }}
.toc-row {{
    display: flex; align-items: baseline; gap: 16px; padding: 11px 0;
    border-bottom: 1px solid {p['border_soft']};
}}
.toc-row .num {{
    font-family: {FONT_MONO}; font-size: 11px; color: {p['accent']} !important;
    min-width: 26px; flex-shrink: 0;
}}
.toc-row h4 {{
    font-family: {FONT_BODY}; margin: 0; color: {p['ink']}; font-size: 14px; font-weight: 700;
    min-width: 168px; flex-shrink: 0;
}}
.toc-row p {{
    color: {p['muted']} !important; font-size: 13px; line-height: 1.55; margin: 0; flex: 1;
}}
.toc-row .sec {{
    font-family: {FONT_MONO}; font-size: 9.5px; letter-spacing: .6px; text-transform: uppercase;
    color: {p['muted']} !important; white-space: nowrap; flex-shrink: 0;
}}

/* "Ver tambien": los sitios reales enlazan hacia dentro al final de cada
   pagina; las apps te dejan en un callejon. */
.seealso {{ border-top: 2px solid {p['ink']}; margin: var(--apartado) 0 0; padding-top: 10px; }}
.seealso .t {{
    font-family: {FONT_BODY}; font-size: 10.5px; font-weight: 800; letter-spacing: 1.6px;
    text-transform: uppercase; color: {p['muted']} !important; margin-bottom: 4px;
}}

/* Pie de sitio: bloque institucional, aviso y sello de emision. */
.sitefoot {{
    margin: var(--apartado) -1rem 0; padding: 22px 1.4rem 26px;
    background: {p['ink_deep']}; border-top: 3px solid {p['warn']};
}}
.sitefoot .fila {{ display: flex; gap: 40px; flex-wrap: wrap; justify-content: space-between; }}
.sitefoot .org {{
    font-family: {FONT_BODY}; font-size: 12.5px; line-height: 1.75; color: #A9BEDD !important;
}}
.sitefoot .org b {{ color: #FFFFFF !important; font-weight: 700; }}
.sitefoot .legal {{
    font-family: {FONT_MONO}; font-size: 10.5px; line-height: 1.75; color: #7E90AF !important;
    max-width: 54ch; text-align: right;
}}
.sitefoot a {{ color: #C7D5EC !important; }}

hr.thin {{ border: none; border-top: var(--hair); margin: var(--bloque) 0; }}

/* Tablas: rejilla de datos, no tarjetas redondeadas. */
[data-testid="stDataFrame"] {{ border: var(--hair); }}

/* Reveal se conserva para no romper llamadas existentes, pero mucho mas
   corto: una animacion de 0.7s en cada bloque es un tic de plantilla. */
@keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
.reveal {{ animation: fadeInUp .25s ease both; }}

/* Compatibilidad: nombres de clase de la version anterior, redirigidos a
   las piezas nuevas para que ninguna hoja quede sin estilo. */
.data-card {{ border: var(--hair); background: {p['panel']}; margin: 0 0 var(--bloque); }}
.data-card .dc-head {{
    background: {p['ink']}; color: #FFFFFF !important; font-family: {FONT_BODY};
    font-weight: 800; font-size: 11.5px; letter-spacing: 1.3px; text-transform: uppercase;
    padding: 9px 15px;
}}
.data-card .dc-row {{
    display: flex; justify-content: space-between; gap: 10px; padding: 7px 15px;
    border-top: 1px solid {p['border_soft']}; font-family: {FONT_MONO}; font-size: 12.5px;
}}
.data-card .dc-row .k {{
    color: {p['muted']} !important; font-size: 11px; text-transform: uppercase;
}}
.data-card .dc-row .v {{ color: {p['ink']} !important; font-weight: 600; }}
.eyebrow {{
    font-family: {FONT_BODY}; font-weight: 800; font-size: 10.5px; letter-spacing: 2.2px;
    text-transform: uppercase; color: {p['accent']} !important; margin-bottom: 7px;
}}
.dateline {{
    font-family: {FONT_MONO}; font-size: 11px; letter-spacing: .2px;
    color: {p['muted']} !important; margin-bottom: 10px; display: flex;
    align-items: center; gap: 8px;
}}
.dateline .dot {{ width: 7px; height: 7px; display: inline-block; flex-shrink: 0; }}
.alert-band {{
    display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
    margin: 0 0 var(--bloque); padding: 10px 15px; border: 1px solid;
}}
.alert-band .kicker {{
    font-family: {FONT_MONO}; font-size: 11px; font-weight: 600; letter-spacing: .8px;
    white-space: nowrap;
}}
.alert-band .msg {{ font-family: {FONT_BODY}; font-size: 14px; line-height: 1.6; flex: 1; }}
.risk-ribbon {{ display: flex; gap: 2px; margin: 0 0 var(--bloque); }}
.risk-ribbon .tier {{
    flex: 1; text-align: center; padding: 7px 5px; font-family: {FONT_BODY};
    font-weight: 800; font-size: 11px; letter-spacing: .8px; text-transform: uppercase;
    border: 1px solid; opacity: .5;
}}
.risk-ribbon .tier.activo {{ opacity: 1; box-shadow: inset 0 4px 0 0 currentColor; }}
.hero-narrativa {{ border-bottom: 3px solid {p['ink']}; padding: 0 0 24px; margin-bottom: 24px; }}
.hero-narrativa h1 {{
    color: {p['ink']} !important; font-family: {FONT_DISPLAY}; font-weight: 800;
    font-size: 34px; line-height: 1.15; max-width: 24ch; margin: 10px 0 14px;
}}
.hero-narrativa p.sub {{
    color: {p['ink_soft']} !important; font-size: 16px; line-height: 1.68;
    max-width: 66ch; margin: 0;
}}
</style>
"""


def inyectar_estilos() -> None:
    if "modo_oscuro" not in st.session_state:
        st.session_state.modo_oscuro = False
    st.markdown(_bloque_css(paleta()), unsafe_allow_html=True)

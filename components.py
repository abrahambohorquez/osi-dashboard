"""
Las piezas de interfaz que se repiten en todas las hojas.

Estan aqui, y no sueltas en cada pagina, para que el ritmo vertical y la
jerarquia tipografica sean automaticos: si todas las hojas piden un titular
de apartado a la misma funcion, todos los apartados respiran igual.

Vocabulario de la maqueta
-------------------------
El sitio distingue tres pesos de informacion y hay una funcion para cada uno.
Confundirlos es lo que hace que un tablero parezca generado: cuando todo se
presenta como una tarjeta de metrica, no queda nada que jerarquizar.

  1. Titular      -> `cifra_titular()`. Una por pagina, como mucho. La cifra
                     que justifica que la pagina exista.
  2. Vitales      -> `fila_metricas()`. Una caja con separadores, en
                     monoespaciada, tamano medio. Contexto, no titular.
  3. Nota al pie  -> `nota_fuente()`, `pie_de_hoja()`. 10.5px, monoespaciada.
                     Procedencia, salvedades y metodo.

Y tres piezas de "producto", que son las que dan el tono de agencia:

  * `titular()`      ...TEXTO EN MAYUSCULAS ENTRE PUNTOS SUSPENSIVOS...
  * `cinta_riesgo()` la escala categorica completa, con el nivel vigente
                     marcado, al modo del outlook del SPC.
  * `tarjeta_datos()` el advisory con numero de producto y vitales.

Todo el texto que ve el usuario esta en ingles porque es una competencia en
ingles; los comentarios y los nombres de funcion estan en espanol porque el
equipo trabaja en espanol.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
from streamlit.components.v1 import html as components_html

import schema
import theme

# ---------------------------------------------------------------------
# Identidad. No hay ningun sello, escudo ni marca ".gov": solo un nombre de
# unidad inventado por el equipo. La franja de utilidad de arriba lo deja
# dicho de forma explicita, que es tambien lo que hace honesto el pastiche.
# ---------------------------------------------------------------------
UNIDAD = "OSI Analysis Desk"
UNIDAD_LINEA2 = "Storm-Driven Outage Severity &middot; IN &middot; OH &middot; PA &middot; WV"
EQUIPO = "The Overfitters"
PROGRAMA = "INFORMS 2026 Data Mining Society Data Challenge"
AVISO_CORTO = "Student project &middot; not an operational forecast"

# ---------------------------------------------------------------------
# El indice de secciones.
#
# Este es el cambio estructural que mas aleja el sitio de "una app con
# pestanas": las once hojas ya no son once botones planos en fila, sino
# cuatro secciones con nombre, igual que un sitio de agencia agrupa sus
# productos (Analysis & Forecasts / Data & Tools / Archives / About). El
# rotulo de la seccion aparece a la izquierda de su grupo de enlaces, tanto
# en la barra superior como en el rail lateral, y tambien en las migas de
# pan de cada pagina.
# ---------------------------------------------------------------------
SECCIONES = [
    ("summary", "Summary"),
    ("analysis", "Analysis"),
    ("diagnostics", "Diagnostics"),
    ("impacts", "Impacts &amp; models"),
    ("data", "Data &amp; docs"),
]

NOMBRE_SECCION = {c: n.replace("&amp;", "&") for c, n in SECCIONES}

# clave, ruta, etiqueta corta (barra), titulo largo, seccion, resumen (indice)
PAGINAS = [
    ("home", "Inicio.py", "Home", "Current products",
     "summary",
     "Status of the loaded file: severity category in effect, headline figures and the product index."),
    ("map", "pages/2_Storm_map.py", "Storm field", "Storm field analysis",
     "analysis",
     "County-level severity through the event window, on real county boundaries and as a 3D relief, plus a single-hour explorer."),
    ("patterns", "pages/3_Patterns.py", "Patterns", "Multivariate patterns",
     "analysis",
     "Parallel coordinates, clustered heatmap with dendrogram, escalation Sankey and an animated county cloud."),
    ("series", "pages/4_Time_series.py", "Time series", "Time series",
     "analysis",
     "Wind, gust, pressure, snow and humidity hour by hour, aggregated or county by county."),
    ("hyst", "pages/8_Hysteresis_and_memory.py", "Hysteresis", "Hysteresis and memory",
     "analysis",
     "First-wave peak against second-wave peak, and how long severity stays autocorrelated."),
    ("dist", "pages/5_Distributions.py", "Distributions", "Distributions and zero-inflation",
     "diagnostics",
     "Zero share, skewness and kurtosis: the numerical case for a Tweedie loss over plain squared error."),
    ("corr", "pages/6_Correlations.py", "Correlations", "Correlations and multicollinearity",
     "diagnostics",
     "Correlation matrix and variance inflation factors across the weather predictors."),
    ("fwl", "pages/7_FWL.py", "FWL", "Frisch-Waugh-Lovell",
     "diagnostics",
     "A predictor's effect on severity before and after partialling out the rest. Signs can flip here."),
    ("costs", "pages/9_Costs.py", "Cost estimate", "Estimated cost by customer segment",
     "impacts",
     "Severity converted to dollars using published interruption-cost rates, split by customer class."),
    ("models", "pages/10_Models.py", "Model results", "Model results",
     "impacts",
     "Placeholder for horizon-by-horizon error once the submitted model is settled."),
    ("load", "pages/1_Load_data.py", "Load data", "Load data",
     "data",
     "Upload a file with the expected columns, or return to the simulated sample."),
    ("refs", "pages/11_References.py", "References", "References and credits",
     "data",
     "Team, companion paper, and the source behind every method computed on these pages."),
]

PAGINA_POR_CLAVE = {p[0]: p for p in PAGINAS}

# Compatibilidad: la lista plana que usaba la version anterior del navbar.
PAGINAS_NAV = [(p[1], p[2]) for p in PAGINAS]


def _pagina_actual() -> tuple | None:
    clave = st.session_state.get("_pagina_actual")
    return PAGINA_POR_CLAVE.get(clave)


def _sello() -> tuple[str, str]:
    """El identificador y la hora de emision del "producto".

    Formato calcado de un producto operativo: identificador corto, numero de
    ciclo y sello doble (hora local y UTC). El numero de ciclo es el dia del
    ano modulo 100, asi que cambia de un dia a otro como cambiaria de verdad.
    No hay ningun prefijo de oficina real (nada de MIA/KWNS): el prefijo es
    OVF, por el nombre del equipo.
    """
    ahora = datetime.now(timezone.utc)
    ciclo = ahora.timetuple().tm_yday % 100
    ident = f"OVF-OSI EDA {ciclo:02d}"
    sello = ahora.strftime("%H%M UTC %a %d %b %Y").upper()
    return ident, sello


def _fuente_activa() -> tuple[str, str]:
    """('simulados'|'propio', etiqueta legible)."""
    fuente = st.session_state.get("fuente", "simulados")
    return fuente, ("SIMULATED SAMPLE" if fuente == "simulados" else "USER-SUPPLIED FILE")


# =====================================================================
# 1. ESTRUCTURA DEL SITIO
# =====================================================================

def cabecera_sitio() -> None:
    """Las tres bandas superiores: franja de utilidad, cabecera de unidad
    con sello de emision, y (en `indice_secciones`) la barra de secciones.

    Tres tonos de azul distintos y decrecientes en peso, que es lo que hace
    que se lea como la cabecera de un sitio y no como la toolbar de una app.
    """
    ident, sello = _sello()
    _, etiqueta_fuente = _fuente_activa()
    st.markdown(f"""
<div class="site-strip">
  <span>{EQUIPO} &middot; {PROGRAMA}</span>
  <span class="aviso">{AVISO_CORTO}</span>
</div>
<div class="masthead">
  <div class="unidad">
    <div class="l1">{UNIDAD}</div>
    <div class="l2">{UNIDAD_LINEA2}</div>
  </div>
  <div class="sello">
    <div class="id">{ident}</div>
    <div class="meta">ISSUED {sello}</div>
    <div class="meta">INPUT: {etiqueta_fuente}</div>
  </div>
</div>
""", unsafe_allow_html=True)


def indice_secciones() -> None:
    """La barra de navegacion, agrupada por seccion.

    Cada grupo se abre con su rotulo en dorado y a continuacion vienen sus
    enlaces. Los enlaces siguen siendo `st.page_link`, asi que Streamlit
    marca solo cual es la pagina activa; si el contexto multipagina no esta
    disponible (algunos entornos de prueba), cae a texto plano sin tumbar la
    hoja.
    """
    # Una columna por rotulo de grupo y una por enlace; el CSS las deja a
    # ancho de contenido y las envuelve en varias lineas si hace falta.
    piezas: list[tuple[str, object]] = []
    for i, (clave_sec, nombre_sec) in enumerate(SECCIONES):
        paginas = [p for p in PAGINAS if p[4] == clave_sec]
        if not paginas:
            continue
        piezas.append(("grupo", (nombre_sec, i == 0)))
        for p in paginas:
            piezas.append(("enlace", p))

    with st.container(key="navbar_links"):
        cols = st.columns(len(piezas))
        for col, (tipo, dato) in zip(cols, piezas):
            with col:
                if tipo == "grupo":
                    nombre, primero = dato
                    st.markdown(
                        f'<span class="navgroup{" primero" if primero else ""}">{nombre}</span>',
                        unsafe_allow_html=True)
                else:
                    _, ruta, etiqueta = dato[0], dato[1], dato[2]
                    try:
                        st.page_link(ruta, label=etiqueta)
                    except Exception:
                        st.caption(etiqueta)


def rail_lateral() -> None:
    """El indice completo repetido en la barra lateral, al modo del rail
    izquierdo de una oficina de weather.gov. Va colapsada por defecto: es
    redundancia deliberada para quien la abra, no la navegacion principal."""
    ident, sello = _sello()
    with st.sidebar:
        st.markdown(f'<div class="idx-grupo">Site index</div>', unsafe_allow_html=True)
        for clave_sec, nombre_sec in SECCIONES:
            paginas = [p for p in PAGINAS if p[4] == clave_sec]
            if not paginas:
                continue
            st.markdown(f'<div class="idx-grupo">{nombre_sec}</div>', unsafe_allow_html=True)
            for p in paginas:
                try:
                    st.page_link(p[1], label=p[2])
                except Exception:
                    st.caption(p[2])
        st.markdown(
            f'<div class="idx-nota">{ident}<br>ISSUED {sello}<br><br>'
            f'{EQUIPO}<br>Universidad de los Andes</div>',
            unsafe_allow_html=True)


def navbar(pagina_actual: str | None = None) -> None:
    """Compatibilidad hacia atras: la cabecera completa de una sola llamada.
    Las hojas antiguas llamaban `comp.navbar()` y siguen funcionando."""
    if pagina_actual:
        st.session_state["_pagina_actual"] = pagina_actual
    cabecera_sitio()
    indice_secciones()
    rail_lateral()


def migas(seccion: str | None, titulo: str) -> str:
    """Las migas de pan. Un sitio real te dice siempre donde estas dentro de
    su arbol; una app te deja adivinarlo por la pestana resaltada. Es un
    detalle barato y es de los que mas cambian la lectura."""
    nombre_sec = NOMBRE_SECCION.get(seccion or "", "")
    partes = [f'<a href="#" style="color:inherit;text-decoration:none;">{UNIDAD}</a>']
    if nombre_sec:
        partes.append(nombre_sec)
    partes.append(f'<span class="actual">{titulo}</span>')
    sep = '<span class="sep">&rsaquo;</span>'
    return f'<div class="breadcrumb">{sep.join(partes)}</div>'


def _metadatos_archivo() -> str:
    """La franja de metadatos que va bajo el titulo de cada pagina: de que
    archivo salen los numeros, cuantas filas tiene y cuando se calculo. Es la
    linea que hace que la pagina parezca fechada y versionada."""
    fuente, etiqueta = _fuente_activa()
    ident, sello = _sello()
    campos = [f"<b>INPUT</b> {etiqueta}"]
    try:
        df = st.session_state.get("df")
        if df is not None and len(df):
            r = schema.resumen_condados(df)
            campos.append(f"<b>COUNTIES</b> {r['n_condados']}")
            campos.append(f"<b>ROWS</b> {r['n_filas']:,}")
            if r["n_horas"]:
                campos.append(f"<b>HOURS</b> {r['n_horas']}")
            if r["estados"]:
                campos.append("<b>AREA</b> " + " ".join(r["estados"]))
    except Exception:
        pass
    campos.append(f"<b>COMPUTED</b> {sello}")
    return '<div class="metaline">' + "".join(f"<span>{c}</span>" for c in campos) + "</div>"


def encabezado_pagina(titulo: str, descripcion: str, seccion: str | None = None,
                      kicker: str | None = None) -> None:
    """La cabecera de una pagina: migas, rotulo de seccion, titulo,
    entradilla y franja de metadatos.

    `seccion` y `kicker` son opcionales; si no vienen, se deducen de la
    pagina activa que registro `preparar_hoja`, de modo que las llamadas
    antiguas de dos argumentos siguen siendo validas.
    """
    actual = _pagina_actual()
    if seccion is None and actual:
        seccion = actual[4]
    if kicker is None:
        kicker = NOMBRE_SECCION.get(seccion or "", "Product")
    st.markdown(migas(seccion, titulo), unsafe_allow_html=True)
    st.markdown(f"""
<div class="page-head">
  <div class="kicker">{kicker}</div>
  <h1>{titulo}</h1>
  <p class="lede">{descripcion}</p>
</div>
{_metadatos_archivo()}
""", unsafe_allow_html=True)


def pie_sitio() -> None:
    """El pie institucional. Los sitios de verdad cierran con un bloque de
    quien publica, con que salvedades y cuando se emitio; las apps cierran
    con el ultimo grafico y ya."""
    ident, sello = _sello()
    st.markdown(f"""
<div class="sitefoot">
  <div class="fila">
    <div class="org">
      <b>{UNIDAD}</b><br>
      {EQUIPO} &middot; Department of Industrial Engineering<br>
      Universidad de los Andes &middot; Bogota, Colombia<br>
      Prepared for the {PROGRAMA}.
    </div>
    <div class="legal">
      {ident} &middot; ISSUED {sello}<br><br>
      This is a student project. It is not affiliated with, endorsed by, or a
      product of NOAA, the National Weather Service or any government agency,
      and nothing published here is an operational forecast.<br><br>
      Challenge data are covered by a non-disclosure agreement and are never
      stored in this repository. Figures shown by default are computed from a
      synthetic sample.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


def preparar_hoja(config_pagina: dict, mostrar_navbar: bool = True,
                  clave: str | None = None) -> "object":
    """La llamada estandar al principio de cada hoja: configura la pagina,
    inyecta el CSS del modo activo, dibuja la cabecera y garantiza que haya
    datos cargados. Devuelve el DataFrame activo.

    `clave` identifica la pagina dentro de `PAGINAS` y es lo que permite que
    las migas y el rotulo de seccion sean correctos. Si no se pasa, se
    intenta deducir del `page_title`, de modo que una hoja que todavia no lo
    pase sigue funcionando (solo pierde las migas)."""
    config_pagina.setdefault("initial_sidebar_state", "collapsed")
    st.set_page_config(**config_pagina)
    if clave is None:
        clave = _inferir_clave(config_pagina.get("page_title", ""))
    if clave:
        st.session_state["_pagina_actual"] = clave
    theme.inyectar_estilos()
    if mostrar_navbar:
        cabecera_sitio()
        indice_secciones()
        rail_lateral()
    return schema.obtener_datos_activos()


def _inferir_clave(page_title: str) -> str | None:
    """Deduce la pagina a partir del titulo del navegador. Solo es una red de
    seguridad para hojas que no pasen `clave` explicitamente."""
    if not page_title:
        return None
    base = page_title.split("|")[0].split("\u00b7")[0].split(" - ")[0].strip().lower()
    for p in PAGINAS:
        if base and (base == p[3].lower() or base == p[2].lower()):
            return p[0]
    return None


# =====================================================================
# 2. LENGUAJE DE PRODUCTO
# =====================================================================

def titular(texto: str) -> None:
    """El titular en mayusculas envuelto en puntos suspensivos.

        ...OSI PEAKS AT 0.41 DURING THE SECOND WAVE...

    Es la firma tipografica de los productos de texto de la NWS (los
    advisories de la NHC abren exactamente asi) y, junto con las migas, es lo
    que mas rapido cambia la lectura de "app" a "producto publicado"."""
    limpio = str(texto).strip().strip(".").upper()
    st.markdown(f'<div class="headline-caps">...{limpio}...</div>', unsafe_allow_html=True)


def cinta_riesgo(nivel_actual: str, titulo: str = "Outage severity category",
                 subtitulo: str | None = None, nota: str | None = None) -> None:
    """La escala categorica completa, con el peldano vigente marcado.

    Gramatica tomada del outlook convectivo del SPC: cinco categorias
    numeradas, abreviatura de cuatro letras, relleno pastel y texto oscuro, y
    el umbral impreso debajo de cada peldano. Que se vea la escala entera y
    no solo la categoria vigente es justamente lo que la convierte en un
    producto legible: dice donde estas y cuanto falta para el siguiente."""
    clave = theme.normalizar_nivel(nivel_actual)
    d = theme.datos_nivel(clave)
    if subtitulo is None:
        subtitulo = f"CATEGORY {d['numero']} OF 5 IN EFFECT"
    peldanos = []
    for c, num, abrev, _nom, _f, _t, _b, _de, _h in theme.NIVELES:
        activo = " activo" if c == clave else ""
        peldanos.append(
            f'<div class="peldano lvl-{c}{activo}">'
            f'<span class="cat">{num} {abrev}</span>'
            f'<span class="um">{theme.rango_nivel(c)}</span></div>'
        )
    pie = f'<div class="nota">{nota}</div>' if nota else ""
    st.markdown(f"""
<div class="riskband">
  <div class="cabecera"><span class="t">{titulo}</span><span class="s">{subtitulo}</span></div>
  <div class="escala">{"".join(peldanos)}</div>
  {pie}
</div>
""", unsafe_allow_html=True)


def insignia_severidad(nivel: str) -> str:
    """Una insignia en linea con la categoria: '3 ELEV'. Devuelve HTML para
    incrustar dentro de otro texto, no lo pinta por su cuenta."""
    d = theme.datos_nivel(nivel)
    return (f'<span class="status-badge lvl-{d["clave"]}">'
            f'{d["numero"]} {d["abrev"]}</span>')


def banda_alerta(nivel: str, etiqueta: str, mensaje: str) -> None:
    """La banda de aviso a todo el ancho.

    Ya no es una barra saturada con texto blanco: usa el relleno pastel y el
    texto oscuro del peldano correspondiente, que es como colorea sus areas
    de riesgo el SPC. Un bloque de color plano y agresivo se lee como una
    notificacion de app; este se lee como un area sombreada de un mapa."""
    d = theme.datos_nivel(nivel)
    st.markdown(f"""
<div class="alert-band lvl-{d['clave']}" style="border-color:{d['borde']};">
  <span class="kicker">{etiqueta}</span>
  <span class="msg">{mensaje}</span>
</div>
""", unsafe_allow_html=True)


def tarjeta_datos(titulo: str, filas: list[tuple[str, str]], numero: str | None = None,
                  pie_izq: str | None = None, pie_der: str | None = None) -> None:
    """El advisory: cabecera solida con el nombre y el numero del producto,
    filas de etiqueta/valor unidas por una linea de puntos, y pie de
    vigencia. Es la forma de la tabla de vitales de un ciclon (posicion,
    presion, viento maximo) de la NHC."""
    ident, sello = _sello()
    if numero is None:
        numero = ident
    filas_html = "".join(
        f'<div class="dc-row"><span class="k">{k}</span>'
        f'<span class="fill"></span><span class="v">{v}</span></div>'
        for k, v in filas
    )
    if pie_izq is None:
        pie_izq = f"ISSUED {sello}"
    if pie_der is None:
        pie_der = "RECOMPUTED ON EVERY PAGE LOAD"
    st.markdown(f"""
<div class="advisory">
  <div class="dc-head"><span>{titulo}</span><span class="num">{numero}</span></div>
  {filas_html}
  <div class="dc-foot"><span>{pie_izq}</span><span>{pie_der}</span></div>
</div>
""", unsafe_allow_html=True)


def lista_estado(items: list[str]) -> None:
    """La lista de estado en vinetas, al modo de "Top News of the Day" de la
    NHC: una linea por cosa vigente, sin parrafo de enlace. Cada item puede
    traer HTML (<b>, <span class="cuando">...</span>)."""
    lis = "".join(f"<li>{t}</li>" for t in items)
    st.markdown(f'<ul class="statuslist">{lis}</ul>', unsafe_allow_html=True)


# =====================================================================
# 3. JERARQUIA DE CIFRAS
# =====================================================================

def cifra_titular(valor: str, etiqueta: str, sub: str = "") -> None:
    """La cifra titular de una pagina: enorme, a la izquierda, con la
    explicacion al lado y una regla gruesa debajo. Como mucho una por pagina;
    si hay dos, ninguna es el titular."""
    st.markdown(f"""
<div class="stat-lead">
  <div class="val">{valor}</div>
  <div class="lado">
    <div class="lbl">{etiqueta}</div>
    <p class="sub">{sub}</p>
  </div>
</div>
""", unsafe_allow_html=True)


def fila_metricas(metricas: list[tuple[str, str, str, str]]) -> None:
    """La fila de vitales.

    `metricas` es una lista de (etiqueta, valor, subtexto, tono); el tono se
    acepta por compatibilidad con las llamadas existentes pero ya no pinta
    cuatro bordes de colores distintos: la fila entera es una sola caja con
    separadores verticales, que es como se lee un bloque de vitales y no
    cuatro tarjetas sueltas flotando.

    Se dibuja como un unico bloque de HTML (y no con `st.columns`) justamente
    para poder encerrarlas en una sola caja."""
    celdas = []
    for i, m in enumerate(metricas):
        lbl, val, sub = m[0], m[1], (m[2] if len(m) > 2 else "")
        primera = " primera" if i == 0 else ""
        celdas.append(
            f'<div class="celda{primera}" style="flex:1;min-width:0;">'
            f'<div class="k">{lbl}</div><div class="v">{val}</div>'
            + (f'<div class="s">{sub}</div>' if sub else "")
            + "</div>"
        )
    st.markdown(
        '<div class="vitals" style="display:flex;">' + "".join(celdas) + "</div>",
        unsafe_allow_html=True)


# =====================================================================
# 4. FIGURAS Y TEXTO
# =====================================================================

def entradilla(texto_html: str) -> None:
    """El parrafo que precede a un grafico y explica que muestra y de donde
    sale. Va ANTES de la figura, no como pie: es la convencion de una
    publicacion de datos (iii.org lo hace en cada apartado) y es lo que
    diferencia un grafico presentado de un grafico soltado."""
    st.markdown(f'<p class="standfirst">{texto_html}</p>', unsafe_allow_html=True)


def marco_figura(numero: str, titulo: str) -> None:
    """La cabecera numerada de una figura: 'FIGURE 4 | Titulo'."""
    st.markdown(f"""
<div class="figframe">
  <div class="cab"><span class="fnum">Figure {numero}</span><span class="ftit">{titulo}</span></div>
</div>
""", unsafe_allow_html=True)


def nota_fuente(texto_html: str) -> None:
    """La linea de procedencia bajo una figura o una tabla. Monoespaciada,
    10.5px, separada por una regla fina: peso de nota al pie, no de texto."""
    st.markdown(f'<div class="figsource">{texto_html}</div>', unsafe_allow_html=True)


def figura(fig, numero: str, titulo: str, fuente: str | None = None, **kwargs) -> None:
    """Dibuja una figura de Plotly enmarcada: numero y titulo arriba,
    grafico, linea de fuente abajo.

    Numerar las figuras es la diferencia entre un informe (donde el texto
    puede decir "vease la figura 3") y una pantalla con graficas sueltas. Si
    no se pasa `fuente`, se escribe la procedencia por defecto del archivo
    activo, que siempre es cierta y siempre es util."""
    marco_figura(numero, titulo)
    st.plotly_chart(fig, width="stretch", **kwargs)
    if fuente is None:
        _, etiqueta = _fuente_activa()
        fuente = (f"<b>Source:</b> computed from the {etiqueta.lower()} currently loaded. "
                  "Weather fields follow the challenge's URMA/ERA5 variable set.")
    nota_fuente(fuente)


def titulo_seccion(numero: str, titulo: str) -> None:
    """Un titular de apartado numerado. La numeracion no es decorativa: hace
    que el apartado sea citable desde el texto y desde el informe."""
    st.markdown(f"""
<div class="section-head">
  <span class="snum">{numero}</span>
  <h3>{titulo}</h3>
</div>
""", unsafe_allow_html=True)


def hallazgo(titulo: str, texto_html: str, tono: str = "accent") -> None:
    """Caja destacada con algo que el sitio encontro por su cuenta en el
    archivo activo. `texto_html` admite <b> para resaltar cifras."""
    st.markdown(f"""
<div class="finding tone-{tono}">
  <div class="flabel">{titulo}</div>
  <p>{texto_html}</p>
</div>
""", unsafe_allow_html=True)


def cita(texto_html: str) -> None:
    """Una frase destacada, para fijar una conclusion antes del detalle."""
    st.markdown(f'<div class="pull-quote">{texto_html}</div>', unsafe_allow_html=True)


def chip(texto: str) -> str:
    return f'<span class="chip">{texto}</span>'


def banner_evento(texto_html: str) -> None:
    """Aviso de un momento concreto dentro de la animacion (el pico de una
    ola, el valle entre las dos)."""
    st.markdown(f'<div class="event-banner">{texto_html}</div>', unsafe_allow_html=True)


def tarjeta(titulo: str, texto: str) -> str:
    return f"""<div class="card"><h4>{titulo}</h4><p>{texto}</p></div>"""


def banner_datos_simulados() -> None:
    """La nota de procedencia de los datos.

    Deliberadamente escrita como una salvedad metodologica y no como una
    alerta: sin fondo de color, sin icono, en monoespaciada pequena. Un
    recuadro amarillo con emoji en cada pagina es el tic mas reconocible de
    un tablero generado; una nota al margen es lo que pondria una
    publicacion."""
    fuente, _ = _fuente_activa()
    if fuente == "simulados":
        st.markdown("""
<div class="banner-sim">
<b>Input: synthetic sample.</b> Figures on this page are computed from a
generated storm, not from the challenge dataset, which is covered by a
non-disclosure agreement and is never stored in this repository. The sample
shares the challenge's public structure (216 hourly steps per county, the
published OSI formula) and nothing else. Load your own file under Data &amp;
docs to recompute every page against real observations.
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="banner-sim">
<b>Input: user-supplied file.</b> Every figure and statistic on this page was
computed from the file loaded in this browser session. Nothing is written to
disk; refreshing returns the site to the synthetic sample.
</div>
""", unsafe_allow_html=True)


def ver_tambien(claves: list[str], titulo: str = "Related products") -> None:
    """El bloque de enlaces internos al final de una pagina. Un sitio real
    siempre te ofrece a donde ir despues; una app te deja en un callejon."""
    paginas = [PAGINA_POR_CLAVE[c] for c in claves if c in PAGINA_POR_CLAVE]
    if not paginas:
        return
    st.markdown(f'<div class="seealso"><div class="t">{titulo}</div></div>',
                unsafe_allow_html=True)
    cols = st.columns(len(paginas))
    for col, p in zip(cols, paginas):
        with col:
            try:
                st.page_link(p[1], label=p[3])
            except Exception:
                st.caption(p[3])


def pie_de_hoja(nota: str) -> None:
    """Nota metodologica al cierre de una pagina, antes del pie del sitio."""
    nota_fuente(f"<b>Notes:</b> {nota}")


# =====================================================================
# 5. FIGURA ANIMADA (sin cambios de comportamiento)
# =====================================================================

def figura_autoreproducida(fig, altura: int = 740, duracion_ms: int = 140,
                           en_bucle: bool = True, lluvia: bool = False) -> None:
    """Muestra una figura animada de Plotly que ARRANCA SOLA y se repite.

    `st.plotly_chart` dibuja los frames pero nunca los lanza: Plotly solo
    anima cuando alguien pulsa play, y no existe ninguna propiedad de la
    figura que diga "empieza sola". La unica forma de conseguirlo sin volver
    a animar desde el servidor (que es justo lo que hacia titilar la pagina:
    cada `st.rerun` reenviaba la figura entera) es exportar la figura a HTML
    y adjuntarle un script que llame a `Plotly.animate` en cuanto termina de
    dibujarse.

    El boton de pausa integrado se sigue respetando: escuchamos que boton
    pulso la persona y, si fue pausa, el bucle no la vuelve a arrancar.

    `lluvia=True` agrega, sobre el mismo div del grafico, un canvas con gotas
    cayendo (opacidad baja a proposito: la primera version de este efecto
    tapaba el mapa entero, esta va calibrada para que se note sin estorbar).
    """
    import json

    nombres = [f.name for f in (fig.frames or []) if f.name]
    if not nombres:
        st.plotly_chart(fig, width="stretch")
        return

    js = """
    var gd = document.getElementById('{plot_id}');
    var nombres = __NOMBRES__;
    var pausado = false;

    function reproducir() {
        if (pausado) { return; }
        Plotly.animate(gd, null, {
            frame: {duration: __DURACION__, redraw: true},
            transition: {duration: 0},
            mode: 'immediate',
            fromcurrent: true
        });
    }

    // Respeta el boton integrado: si pulsan pausa, el bucle no la reanuda.
    gd.on('plotly_buttonclicked', function (ev) {
        var etiqueta = ev && ev.button && ev.button.label;
        if (etiqueta === 'pause') { pausado = true; }
        if (etiqueta === 'play') { pausado = false; }
    });

    if (__BUCLE__) {
        gd.on('plotly_animated', function () {
            if (pausado) { return; }
            Plotly.animate(gd, [nombres[0]], {
                frame: {duration: 0, redraw: true},
                transition: {duration: 0},
                mode: 'immediate'
            });
            setTimeout(reproducir, 200);
        });
    }

    setTimeout(reproducir, 350);

    if (__LLUVIA__) {
        (function () {
            if (gd.querySelector('.lluvia-canvas')) { return; }
            var canvas = document.createElement('canvas');
            canvas.className = 'lluvia-canvas';
            canvas.style.position = 'absolute';
            canvas.style.top = '0'; canvas.style.left = '0';
            canvas.style.width = '100%'; canvas.style.height = '100%';
            canvas.style.pointerEvents = 'none';
            canvas.style.zIndex = 20;
            gd.style.position = 'relative';
            gd.appendChild(canvas);
            var ctx = canvas.getContext('2d');
            function ajustar() {
                canvas.width = gd.clientWidth;
                canvas.height = gd.clientHeight;
            }
            ajustar();
            window.addEventListener('resize', ajustar);
            var gotas = [];
            var n = 140;
            for (var i = 0; i < n; i++) {
                gotas.push({
                    x: Math.random() * canvas.width, y: Math.random() * canvas.height,
                    len: 7 + Math.random() * 12, vel: 6 + Math.random() * 7, drift: 1.2,
                });
            }
            function paso() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.strokeStyle = 'rgba(180,205,240,0.30)';
                ctx.lineWidth = 1;
                for (var k = 0; k < gotas.length; k++) {
                    var g = gotas[k];
                    ctx.beginPath();
                    ctx.moveTo(g.x, g.y);
                    ctx.lineTo(g.x - g.drift * 2, g.y + g.len);
                    ctx.stroke();
                    g.x -= g.drift; g.y += g.vel;
                    if (g.y > canvas.height) { g.y = -g.len; g.x = Math.random() * canvas.width; }
                    if (g.x < 0) { g.x = canvas.width; }
                }
                requestAnimationFrame(paso);
            }
            requestAnimationFrame(paso);
        })();
    }
    """
    js = js.replace("__NOMBRES__", json.dumps(nombres))
    js = js.replace("__DURACION__", str(int(duracion_ms)))
    js = js.replace("__BUCLE__", "true" if en_bucle else "false")
    js = js.replace("__LLUVIA__", "true" if lluvia else "false")

    html = fig.to_html(full_html=False, include_plotlyjs="cdn",
                       config={"displaylogo": False}, post_script=js)
    components_html(html, height=altura, scrolling=False)

"""
Portada del sitio.

No es una landing de producto con un titular gigante: es una pagina de
"productos vigentes", que es lo que publica de portada una agencia real. El
orden lo dice todo:

    1. Lista de estado en vinetas: que hay ahora mismo en el archivo activo.
    2. Escala categorica con el nivel vigente marcado.
    3. Advisory con los vitales del archivo.
    4. La cifra titular de la portada y por que importa.
    5. El indice de productos, en forma de tabla.

Todos los numeros se calculan en vivo sobre el archivo cargado. Ninguno esta
escrito a mano, ni copiado del informe: si alguien sube otro archivo, la
portada cambia entera, incluida la categoria vigente y el titular.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import components as comp
import schema
import theme

st.set_page_config(page_title="Current products | OSI Analysis Desk", layout="wide",
                   initial_sidebar_state="collapsed")
st.session_state["_pagina_actual"] = "home"
theme.inyectar_estilos()
comp.cabecera_sitio()
comp.indice_secciones()
comp.rail_lateral()

df = schema.obtener_datos_activos()
resumen = schema.resumen_condados(df)

# ---------------------------------------------------------------------
# Todo lo que sigue sale del archivo activo. Se calcula una sola vez aqui y
# se reutiliza en la lista de estado, la cinta, el advisory y el titular,
# para que las cuatro piezas no puedan contradecirse entre si.
# ---------------------------------------------------------------------
tiene_osi = "osi" in df.columns and len(df) > 0

if tiene_osi:
    pico_global = float(df["osi"].max())
    hora_pico = int(df.loc[df["osi"].idxmax(), "hour_idx"]) if "hour_idx" in df.columns else 0
    pct_cero = float((df["osi"] == 0).mean() * 100)
    nivel_pico = theme.nivel_para_osi(pico_global)
    d_nivel = theme.datos_nivel(nivel_pico)

    # El condado y el estado del peor momento del archivo.
    fila_pico = df.loc[df["osi"].idxmax()]
    condado_pico = str(fila_pico.get("countyName", "n/a"))
    estado_pico = str(fila_pico.get("stateAbbr", ""))

    # Pico por condado y reparto por categoria: cuantos condados llegaron a
    # cada peldano de la escala en algun momento de la ventana.
    picos_condado = df.groupby("fipsCode")["osi"].max()
    reparto = {}
    for c, _n, _a, _nom, _f, _t, _b, _de, _h in theme.NIVELES:
        reparto[c] = int(sum(1 for v in picos_condado if theme.nivel_para_osi(v) == c))
    n_sobre_umbral = int((picos_condado >= 0.08).sum())

    # Las dos olas: se parte la ventana por la mitad y se toma el maximo
    # regional de cada mitad. Es una particion tosca a proposito, porque la
    # portada solo necesita saber si la segunda ola pego menos que la
    # primera; la pagina de histeresis lo hace bien.
    serie = df.groupby("hour_idx")["osi"].mean() if "hour_idx" in df.columns else None
    if serie is not None and len(serie) > 8:
        mitad = len(serie) // 2
        pico_ola1 = float(serie.iloc[:mitad].max())
        pico_ola2 = float(serie.iloc[mitad:].max())
        hora_ola1 = int(serie.iloc[:mitad].idxmax())
        hora_ola2 = int(serie.iloc[mitad:].idxmax())
        atenuacion = (1 - pico_ola2 / pico_ola1) * 100 if pico_ola1 > 0 else 0.0
    else:
        pico_ola1 = pico_ola2 = hora_ola1 = hora_ola2 = atenuacion = None
else:
    pico_global = hora_pico = pct_cero = None
    nivel_pico = "mnml"
    d_nivel = theme.datos_nivel(nivel_pico)
    condado_pico = estado_pico = ""
    reparto = {}
    n_sobre_umbral = 0
    pico_ola1 = pico_ola2 = hora_ola1 = hora_ola2 = atenuacion = None

comp.encabezado_pagina(
    "Current products",
    "This page summarises the outage record currently loaded into the site and indexes every "
    "analysis product built on top of it. Category, headline figures and wave structure below "
    "are recomputed from the active file each time the page is served.",
    seccion="summary",
)

# ---------------------------------------------------------------------
# 1. Titular y estado, al modo de la portada de la NHC: primero el titular
#    del producto en mayusculas, luego que hay vigente, en vinetas.
# ---------------------------------------------------------------------
if tiene_osi:
    comp.titular(
        f"peak outage severity {pico_global:.3f} at hour {hora_pico} "
        f"in {condado_pico} {estado_pico} &middot; category {d_nivel['numero']} {d_nivel['abrev']}"
    )

    items = [
        f"<b>Category {d_nivel['numero']} ({d_nivel['nombre']})</b> in effect for the loaded "
        f"window, set by the file's maximum county-hour severity of {pico_global:.3f}."
        f"<span class='cuando'>hour {hora_pico}</span>",
        f"<b>{n_sobre_umbral} of {resumen['n_condados']} counties</b> reached category 3 "
        f"(ELEV, OSI 0.08) or above at some point in the window.",
        f"<b>{pct_cero:.0f}% of county-hours</b> record no outage at all. The series is "
        "zero-inflated, which is the single most consequential fact for model choice.",
    ]
    if atenuacion is not None:
        items.append(
            f"<b>Two waves detected.</b> Regional mean severity peaked at {pico_ola1:.3f} "
            f"(hour {hora_ola1}) and again at {pico_ola2:.3f} (hour {hora_ola2}), "
            f"{abs(atenuacion):.0f}% "
            f"{'below' if atenuacion > 0 else 'above'} the first."
            f"<span class='cuando'>see Hysteresis</span>"
        )
    items.append(
        "<b>Input is the synthetic sample.</b> Challenge observations are under NDA and are "
        "never committed to this repository."
        if st.session_state.get("fuente", "simulados") == "simulados" else
        "<b>Input is a user-supplied file</b>, held in this browser session only."
    )
    comp.lista_estado(items)

    comp.cinta_riesgo(
        nivel_pico,
        titulo="Outage severity category in effect",
        subtitulo=f"CATEGORY {d_nivel['numero']} OF 5 &middot; PEAK OSI {pico_global:.3f}",
        nota=("Thresholds are fixed on the OSI scale and identical on every page. "
              "Category is set by the maximum county-hour value in the loaded window, "
              "not by an average."),
    )
else:
    comp.titular("loaded file contains no osi column &middot; severity products unavailable")
    st.warning(
        "The active file has no `osi` column, so no severity category can be assigned. "
        "Load a file with the expected columns under Data & docs."
    )

comp.banner_datos_simulados()

# ---------------------------------------------------------------------
# 2. Vitales del archivo, en formato advisory.
# ---------------------------------------------------------------------
comp.titulo_seccion("01", "Record vitals")

filas = [
    ("Counties", str(resumen["n_condados"])),
    ("County-hour rows", f"{resumen['n_filas']:,}"),
    ("Hours per county", str(resumen["n_horas"])),
    ("States covered", ", ".join(resumen["estados"]) if resumen["estados"] else "n/a"),
    ("County geometry", "resolved" if resumen["tiene_coordenadas"] else "derived from FIPS"),
]
if tiene_osi:
    filas.insert(0, ("Peak OSI", f"{pico_global:.4f}"))
    filas.insert(1, ("Peak location", f"{condado_pico}, {estado_pico}".strip(", ")))
    filas.insert(2, ("Peak hour index", str(hora_pico)))

comp.tarjeta_datos("Record vitals", filas)

if tiene_osi and reparto:
    comp.entradilla(
        "Counties are assigned to the highest category they reach at any hour of the window, "
        "which is why the counts below sum to the full county set rather than describing a "
        "single instant."
    )
    comp.fila_metricas([
        (f"{theme.datos_nivel(c)['numero']} {theme.datos_nivel(c)['abrev']}",
         str(reparto[c]),
         f"OSI {theme.rango_nivel(c)}",
         "ink")
        for c in reparto
    ])
    comp.nota_fuente(
        "<b>Source:</b> county-level maxima over the loaded window. "
        "<b>Category thresholds:</b> fixed on the OSI scale, documented in "
        "<code>theme.NIVELES</code> and applied identically across the site."
    )

# ---------------------------------------------------------------------
# 3. La cifra titular de la portada. Una sola, y es la que decide el modelo.
# ---------------------------------------------------------------------
if tiene_osi:
    comp.titulo_seccion("02", "Why this record is not an ordinary regression problem")
    comp.cifra_titular(
        f"{pct_cero:.0f}%",
        "of county-hours at exactly zero",
        f"Against a peak of {pico_global:.3f} in the same file. A squared-error loss weights a "
        "correctly predicted calm hour exactly as heavily as a correctly predicted emergency, so "
        "a model trained on it will spend most of its capacity on the majority class and "
        "underpredict the tail. The Distributions page quantifies the skew and kurtosis behind "
        "this figure; the submitted model uses a Tweedie objective in response."
    )
    comp.cita(
        "The forecasting question is not whether outages occur. It is when the series stops "
        "being zero, and how far it travels once it does."
    )

# ---------------------------------------------------------------------
# 4. Indice de productos. Tabla, no tarjetas: una fila por pagina, con su
#    seccion a la derecha, como el indice de una oficina.
# ---------------------------------------------------------------------
comp.titulo_seccion("03", "Product index")
comp.entradilla(
    "Every page listed below recomputes from the active file. None of them contains a figure "
    "transcribed from the companion paper."
)

filas_toc = []
for i, (clave, ruta, etiqueta, titulo_largo, seccion, resumen_txt) in enumerate(comp.PAGINAS, 1):
    if clave == "home":
        continue
    filas_toc.append(f"""
    <div class="toc-row">
      <div class="num">{i - 1:02d}</div>
      <h4>{titulo_largo}</h4>
      <p>{resumen_txt}</p>
      <div class="sec">{comp.NOMBRE_SECCION.get(seccion, "")}</div>
    </div>""")
st.markdown('<div class="toc">' + "".join(filas_toc) + "</div>", unsafe_allow_html=True)

comp.titulo_seccion("04", "Loading your own record")
comp.entradilla(
    "The site validates an uploaded CSV against the column set the challenge publishes and "
    "refuses anything incomplete rather than filling gaps silently. Uploads live in the browser "
    "session only: nothing is written to disk and nothing is committed to the repository."
)
comp.ver_tambien(["load", "map", "dist", "hyst"], titulo="Start here")

comp.pie_sitio()

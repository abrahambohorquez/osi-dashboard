"""
Comprobaciones con `streamlit.testing.v1.AppTest`.

Ejecutar desde la raiz del proyecto:

    pip install -r requirements.txt pytest
    pytest tests/ -v

Que se comprueba
----------------
1. Que cada hoja se ejecuta entera sin excepcion (`assert not at.exception`),
   con los datos simulados por defecto y tambien con un archivo cargado en
   sesion, que es el otro camino real del sitio.
2. Que las invariantes de la maqueta se cumplen en todas las hojas: migas de
   pan, cabecera de tres bandas, franja de metadatos, indice de secciones
   agrupado y pie institucional. Son justo las piezas que distinguen esto de
   un tablero generico, asi que si alguien las quita sin querer, el test lo
   dice.
3. Que ninguna hoja publica un sello, un logotipo o una marca ".gov": es una
   restriccion del proyecto, no una preferencia, y conviene tenerla vigilada
   por una prueba y no por la memoria de nadie.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import schema  # noqa: E402

HOJAS = [RAIZ / "Inicio.py"] + sorted((RAIZ / "pages").glob("*.py"))
IDS = [h.name for h in HOJAS]

TIEMPO_LIMITE = 120  # el mapa animado y el clustering tardan


def _correr(hoja: Path, estado: dict | None = None) -> AppTest:
    at = AppTest.from_file(str(hoja), default_timeout=TIEMPO_LIMITE)
    # Patterns arranca su propio bucle de reproduccion (st.rerun() en cada
    # tick): sin esto, AppTest nunca ve un run terminado y se queda
    # esperando hasta el timeout en vez de pasar en segundos.
    at.session_state["pt_reproduciendo"] = False
    if estado:
        for clave, valor in estado.items():
            at.session_state[clave] = valor
    return at.run()


def _texto(at: AppTest) -> str:
    """Todo el markdown que la hoja emitio, concatenado."""
    return "\n".join(str(m.value) for m in at.markdown)


# ---------------------------------------------------------------------
# 1. Todas las hojas corren
# ---------------------------------------------------------------------

@pytest.mark.parametrize("hoja", HOJAS, ids=IDS)
def test_hoja_corre_con_datos_simulados(hoja):
    at = _correr(hoja)
    assert not at.exception, f"{hoja.name} lanzo: {at.exception}"


@pytest.mark.parametrize("hoja", HOJAS, ids=IDS)
def test_hoja_corre_con_archivo_del_usuario(hoja):
    """El otro camino real: alguien subio su propio archivo. Se reutiliza el
    simulado como si lo hubiera subido, que es exactamente lo que hace la
    hoja de carga, y se comprueba que ninguna pagina asume la ruta del
    archivo de muestra."""
    df = schema.cargar_datos_simulados()
    at = _correr(hoja, {"df": df, "fuente": "propio"})
    assert not at.exception, f"{hoja.name} lanzo con archivo propio: {at.exception}"
    assert "user-supplied" in _texto(at).lower()


def test_hoja_aguanta_un_archivo_sin_osi():
    """Un archivo valido en columnas pero sin severidad calculada no debe
    tumbar la portada: debe degradar a un aviso."""
    df = schema.cargar_datos_simulados().drop(columns=["osi"])
    at = _correr(RAIZ / "Inicio.py", {"df": df, "fuente": "propio"})
    assert not at.exception
    assert at.warning, "la portada deberia avisar de que falta la columna osi"


# ---------------------------------------------------------------------
# 2. Invariantes de la maqueta
# ---------------------------------------------------------------------

@pytest.mark.parametrize("hoja", HOJAS, ids=IDS)
def test_cabecera_de_tres_bandas(hoja):
    """Franja de utilidad + cabecera de unidad + indice de secciones en dos
    niveles. El marcador `st-key-navsec_` es la regla CSS que cada render
    emite para resaltar su seccion activa: si desaparece, la fila superior
    perdio el estado activo o la navegacion entera."""
    texto = _texto(_correr(hoja))
    assert 'class="site-strip"' in texto
    assert 'class="masthead"' in texto
    assert ".st-key-navsec_" in texto, "falta la marca de seccion activa del indice"


@pytest.mark.parametrize("hoja", HOJAS, ids=IDS)
def test_hallazgos_no_son_todos_cajas(hoja):
    """La variante con caja de los hallazgos queda reservada: nunca mas de
    una por pagina. Si esto falla, alguien volvio a encajonar la prosa."""
    texto = _texto(_correr(hoja))
    assert texto.count('class="finding destacado"') <= 1


@pytest.mark.parametrize("hoja", HOJAS, ids=IDS)
def test_sello_de_emision(hoja):
    """Toda pagina lleva identificador de producto y hora de emision."""
    texto = _texto(_correr(hoja))
    assert "OVF-OSI EDA" in texto
    assert "ISSUED" in texto


@pytest.mark.parametrize("hoja", HOJAS, ids=IDS)
def test_pie_institucional_y_aviso(hoja):
    """El pie tiene que estar y tiene que decir explicitamente que esto no es
    un producto oficial. La renuncia es la que hace honesto el pastiche."""
    texto = _texto(_correr(hoja))
    assert 'class="sitefoot"' in texto, f"{hoja.name} no cierra con el pie del sitio"
    assert "not an operational forecast" in texto


@pytest.mark.parametrize("hoja", [h for h in HOJAS if h.name != "Inicio.py"], ids=IDS[1:])
def test_migas_y_metadatos(hoja):
    """Cada pagina interior dice donde esta en el arbol del sitio y de que
    archivo salen sus numeros."""
    texto = _texto(_correr(hoja))
    assert 'class="breadcrumb"' in texto, f"{hoja.name} no lleva migas de pan"
    assert 'class="metaline"' in texto, f"{hoja.name} no lleva franja de metadatos"


def test_portada_publica_la_escala_completa():
    """La cinta categorica muestra los cinco peldanos, no solo el vigente:
    eso es lo que la convierte en una escala legible."""
    texto = _texto(_correr(RAIZ / "Inicio.py"))
    for abrev in ("MNML", "LMTD", "ELEV", "MAJR", "EXTR"):
        assert abrev in texto, f"falta el peldano {abrev} en la cinta"
    assert texto.count('class="peldano') >= 5
    assert "activo" in texto, "ningun peldano marcado como vigente"


def test_portada_lleva_titular_de_producto():
    """El titular en mayusculas entre puntos suspensivos."""
    texto = _texto(_correr(RAIZ / "Inicio.py"))
    assert 'class="headline-caps"' in texto
    assert "..." in texto


# ---------------------------------------------------------------------
# 3. Restricciones del proyecto
# ---------------------------------------------------------------------

PROHIBIDO = ["noaa.gov", "weather.gov/logo", ".gov/images", "usa_gov",
             "NWS_logo", "NOAA_noText_logo", "DOC_logo"]


@pytest.mark.parametrize("hoja", HOJAS, ids=IDS)
def test_sin_marcas_de_agencia(hoja):
    """Ni sellos, ni logotipos, ni dominios oficiales incrustados."""
    texto = _texto(_correr(hoja))
    for marca in PROHIBIDO:
        assert marca not in texto, f"{hoja.name} incrusta una marca oficial: {marca}"


@pytest.mark.parametrize("hoja", HOJAS, ids=IDS)
def test_sin_servicios_con_credenciales(hoja):
    """El sitio tiene que arrancar sin ninguna cuenta ni token. Mapbox es el
    que se cuela con mas facilidad porque Plotly lo ofrece por defecto."""
    texto = _texto(_correr(hoja)).lower()
    assert "mapbox_style" not in texto
    assert "access_token" not in texto


def test_codigo_no_pide_token_de_mapa():
    """La comprobacion equivalente sobre el codigo fuente, que cubre lo que
    no llega a emitirse como markdown."""
    sospechosos = []
    for py in list(RAIZ.glob("*.py")) + list((RAIZ / "pages").glob("*.py")):
        fuente = py.read_text(encoding="utf-8").lower()
        if "mapbox_accesstoken" in fuente or "set_mapbox_access_token" in fuente:
            sospechosos.append(py.name)
    assert not sospechosos, f"estas hojas necesitarian una cuenta: {sospechosos}"


def test_no_hay_datos_del_reto_en_el_repositorio():
    """Restriccion de NDA: el unico csv versionado es el simulado."""
    csvs = {p.name for p in RAIZ.rglob("*.csv")}
    assert csvs <= {"datos_simulados.csv"}, f"csv inesperado en el repositorio: {csvs}"


# ---------------------------------------------------------------------
# 4. Coherencia de la escala de severidad
# ---------------------------------------------------------------------

def test_la_escala_no_deja_huecos_ni_solapes():
    """Los cinco umbrales tienen que cubrir la recta sin hueco ni solape, o
    habria valores de OSI sin categoria."""
    import theme
    for (a, b) in zip(theme.NIVELES, theme.NIVELES[1:]):
        assert a[8] == b[7], f"hueco o solape entre {a[2]} y {b[2]}"
    assert theme.NIVELES[0][7] == 0.0


@pytest.mark.parametrize("valor,esperado", [
    (0.0, "mnml"), (0.019, "mnml"), (0.02, "lmtd"), (0.079, "lmtd"),
    (0.08, "elev"), (0.199, "elev"), (0.20, "majr"), (0.349, "majr"),
    (0.35, "extr"), (0.90, "extr"),
])
def test_asignacion_de_categoria(valor, esperado):
    import theme
    assert theme.nivel_para_osi(valor) == esperado


def test_vocabulario_antiguo_sigue_resolviendo():
    """Las hojas que aun hablan de calm/watch/warning/severe no deben
    romperse ni caer en una categoria arbitraria."""
    import theme
    assert theme.normalizar_nivel("calm") == "mnml"
    assert theme.normalizar_nivel("severe") == "majr"
    assert theme.normalizar_nivel("no existe") == "mnml"

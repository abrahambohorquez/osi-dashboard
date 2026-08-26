"""Límites reales de condados de EEUU (Census TIGER/Line), para dibujar la
tormenta sobre un mapa geográfico de verdad en vez de coordenadas
inventadas. Solo tiene sentido con datos reales: el fipsCode real (18009,
39001, etc) es el mismo GEOID que usa el Census, así que el cruce es
directo y sin ambigüedad. Los datos simulados usan fipsCode inventado
(100001+, seis dígitos) que nunca calza con un condado real, así que esta
pieza nunca debería activarse con el archivo de ejemplo.

El archivo nacional del Census pesa bastante y tarda un rato en bajar, así
que la primera vez que se use se recorta a los cuatro estados del reto
(IN, OH, PA, WV) y se guarda en cache local; las siguientes veces se lee
esa copia chica, sin internet."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

URL_TIGER = "https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip"
FIPS_ESTADOS_RETO = {"18": "IN", "39": "OH", "42": "PA", "54": "WV"}
RUTA_CACHE = Path(__file__).resolve().parent / "data" / "condados_reales_reto.geojson"


def hay_cache() -> bool:
    return RUTA_CACHE.exists()


def descargar_y_cachear() -> "object":
    """Baja el shapefile nacional del Census, lo recorta a los cuatro
    estados del reto, lo simplifica un poco (es para visualización, no
    para análisis geoespacial de precisión) y lo guarda en cache local.
    Tarda un minuto largo y necesita internet; se llama una sola vez."""
    import geopandas as gpd

    condados = gpd.read_file(URL_TIGER)
    condados = condados[condados["STATEFP"].isin(FIPS_ESTADOS_RETO)].copy()
    condados["stateAbbr"] = condados["STATEFP"].map(FIPS_ESTADOS_RETO)
    condados["fipsCode"] = condados["GEOID"].astype(int)
    condados["geometry"] = condados["geometry"].simplify(0.003)
    condados = condados[["fipsCode", "stateAbbr", "NAME", "NAMELSAD", "geometry"]]
    RUTA_CACHE.parent.mkdir(exist_ok=True)
    condados.to_file(RUTA_CACHE, driver="GeoJSON")
    return condados


def obtener_geometrias() -> "object | None":
    """Devuelve el GeoDataFrame de los 239 condados del reto si ya hay
    cache local; None si no hay cache y no se ha pedido descargar todavía
    (la descarga es una acción explícita del usuario, no automática, por
    el tiempo que toma y porque necesita internet)."""
    import geopandas as gpd

    if not hay_cache():
        return None
    return gpd.read_file(RUTA_CACHE)


def emparejar(df: pd.DataFrame, geo) -> "object":
    """Cruza el dataframe activo (debe traer fipsCode) con las geometrías
    reales, por fipsCode == GEOID. Ninguna fila de un condado inventado
    va a calzar, así que el resultado queda vacío para datos simulados."""
    return geo.merge(df, on="fipsCode", how="inner")


def cobertura(df: pd.DataFrame, geo) -> tuple[int, int]:
    """(condados del archivo activo que sí tienen geometría real, total
    de condados distintos en el archivo activo). Sirve para decidir si
    tiene sentido ofrecer el mapa geográfico o no."""
    if "fipsCode" not in df.columns:
        return 0, 0
    propios = set(df["fipsCode"].unique())
    return len(propios & set(geo["fipsCode"].unique())), len(propios)


def asignar_condados_reales(fips_propios: list, geo) -> dict:
    """Para datos sin fipsCode real (los simulados): asigna cada condado
    inventado a un condado real distinto de la región del reto, de forma
    determinista (mismo archivo, misma asignación siempre), solo para
    poder dibujar la severidad sobre una forma de condado real. Es un
    préstamo de geometría, no una afirmación de que ese condado real tuvo
    esa severidad: la hoja que use esto debe dejarlo dicho."""
    reales = sorted(geo["fipsCode"].unique().tolist())
    asignacion = {}
    for i, f in enumerate(sorted(set(fips_propios))):
        asignacion[f] = reales[i % len(reales)]
    return asignacion

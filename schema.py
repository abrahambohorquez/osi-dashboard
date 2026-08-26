"""Esquema de columnas esperado, y las funciones para cargar o validar
un archivo. Ninguna hoja debería leer un CSV directamente sin pasar por
acá, para que el validador sea siempre el mismo."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HORAS_TOTALES = 216
ANCLA_H = 71

COLUMNAS_REQUERIDAS = [
    "timestamp_et", "fipsCode", "countyName", "stateAbbr", "hour_idx",
    "customersTracked", "outageCount", "P_t", "N_t", "D_t", "R_t", "osi",
    "gust", "wind_speed_10m", "mslma", "tp", "rain", "csnow", "soil_moist", "r2",
]

# opcionales: si vienen, algunas hojas hacen más (el mapa animado necesita
# posicion_x/posicion_y, por ejemplo) pero nada se rompe si faltan
COLUMNAS_OPCIONALES = ["posicion_x", "posicion_y", "severity_tier", "osi_lag24h", "blh"]

RUTA_DATOS_SIMULADOS = Path(__file__).resolve().parent / "data" / "datos_simulados.csv"


def cargar_datos_simulados() -> pd.DataFrame:
    df = pd.read_csv(RUTA_DATOS_SIMULADOS)
    df["timestamp_et"] = pd.to_datetime(df["timestamp_et"])
    return df


def derivar_hour_idx(df: pd.DataFrame) -> pd.DataFrame:
    """El archivo real del reto no trae hour_idx, solo timestamp_et: cada
    condado arranca en la misma hora de inicio del evento, así que
    hour_idx se puede derivar como horas transcurridas desde el mínimo
    timestamp de todo el archivo. Si ya viene hour_idx, no toca nada."""
    if "hour_idx" in df.columns or "timestamp_et" not in df.columns:
        return df
    ts = pd.to_datetime(df["timestamp_et"], errors="coerce")
    if ts.isna().all():
        return df
    df = df.copy()
    df["hour_idx"] = ((ts - ts.min()).dt.total_seconds() / 3600).round().astype("Int64")
    return df


def validar_columnas(df: pd.DataFrame) -> list[str]:
    """Columnas requeridas que faltan en df. Vacía si el archivo trae
    todo lo que las demás hojas necesitan para funcionar."""
    return [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]


def resumen_condados(df: pd.DataFrame) -> dict:
    return {
        "n_condados": df["fipsCode"].nunique(),
        "n_filas": len(df),
        "n_horas": df["hour_idx"].nunique() if "hour_idx" in df.columns else None,
        "estados": sorted(df["stateAbbr"].unique().tolist()) if "stateAbbr" in df.columns else [],
        "tiene_coordenadas": {"posicion_x", "posicion_y"}.issubset(df.columns),
    }


def obtener_datos_activos() -> pd.DataFrame:
    """Punto único de entrada para cualquier hoja: si todavía no hay
    nada en la sesión, carga los datos simulados; si ya hay algo (propio
    o simulado), lo devuelve tal cual."""
    import streamlit as st

    if "df" not in st.session_state:
        st.session_state.df = cargar_datos_simulados()
        st.session_state.fuente = "simulados"
    return st.session_state.df

"""
Genera un conjunto de datos simulado para el dashboard, con las mismas
columnas que el equipo usa para el reto real, pero condados, tormentas y
valores completamente inventados. No viene de DM_Train.csv en ningún
paso, y no tiene ninguna relación con los datos oficiales del reto ni con
los condados reales de Indiana, Ohio, Pennsylvania o West Virginia.

Por qué existe: las reglas del reto no permiten mostrar ni distribuir los
datos oficiales fuera del equipo registrado. Para poder enseñar cómo se
ve el problema (dos oleadas de tormenta, histéresis, cero-inflación,
clustering espacial) sin tocar esa restricción, este script arma una
tormenta de juguete con la misma forma general, usando solo funciones
matemáticas simples: nada aprendido de los datos reales, nada que se le
parezca fila por fila.

La física que reproduce, a propósito, para que el dashboard cuente la
misma historia que el EDA real:
  - dos rachas de viento, la segunda con histéresis (mismo viento,
    menos daño nuevo, porque ya golpeó antes)
  - la tormenta barre el mapa de oeste a este, así que condados cercanos
    se golpean en momentos parecidos (autocorrelación espacial real,
    no simulada a mano)
  - P_t/N_t/D_t/R_t se contabilizan con la fórmula oficial del OSI
  - tp = rain + csnow (misma identidad exacta que existe en los datos
    reales, para poder enseñar el problema de multicolinealidad)

Uso:
    python simular_datos.py
Escribe data/datos_simulados.csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HORAS_TOTALES = 216
ANCLA_H = 71
SEED = 42

# condados de juguete, agrupados en 4 "estados" simulados, nombrados
# así a propósito para que nadie los confunda con los 239/63 condados
# reales del reto. Se acomodan de oeste a este en ese mismo orden, para
# que la tormenta (que también viaja de oeste a este) los golpee en
# secuencia, como una tormenta real cruzando una región.
ESTADOS_SIMULADOS = ["SIM-A", "SIM-B", "SIM-C", "SIM-D"]
CONDADOS_POR_ESTADO = 10
ANCHO_MAPA = 12.0   # posicion_x va de 0 (oeste) a ANCHO_MAPA (este)
ALTO_MAPA = 7.0     # posicion_y va de 0 (sur) a ALTO_MAPA (norte)


def _ola(hora: np.ndarray, centro: float, ancho: float, alto: float) -> np.ndarray:
    return alto * np.exp(-0.5 * ((hora - centro) / ancho) ** 2)


def generar_datos_simulados(n_condados_por_estado: int = CONDADOS_POR_ESTADO, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    hora = np.arange(HORAS_TOTALES)
    filas = []

    n_estados = len(ESTADOS_SIMULADOS)
    fips = 100000
    for idx_estado, estado in enumerate(ESTADOS_SIMULADOS):
        # cada estado ocupa una franja de oeste a este
        x_min = idx_estado * (ANCHO_MAPA / n_estados)
        x_max = (idx_estado + 1) * (ANCHO_MAPA / n_estados)

        for i in range(n_condados_por_estado):
            fips += 1
            nombre = f"Simulated County {fips - 100000:03d} ({estado})"

            posicion_x = float(rng.uniform(x_min, x_max))
            posicion_y = float(rng.uniform(0.4, ALTO_MAPA - 0.4))

            # la tormenta viaja de oeste a este: entre más al este esté
            # el condado, más tarde le llega el centro de cada ola. Esto
            # es lo que hace que el mapa animado se vea como una tormenta
            # real barriendo la región, y lo que le da contenido genuino
            # al indice de Moran (condados vecinos se parecen entre si).
            # cruzar todo el mapa toma 18-20 horas, igual de rapido que
            # un sistema de viento real a escala regional
            fraccion_x = posicion_x / ANCHO_MAPA
            corrimiento1 = fraccion_x * 18.0 + rng.normal(0, 2.0)
            corrimiento2 = fraccion_x * 20.0 + rng.normal(0, 2.5)

            # la intensidad tambien tiene un componente espacial suave
            # (una franja norte-sur mas golpeada que el resto) mas ruido
            # propio de cada condado, moderado a proposito para que la
            # franja siga siendo la que manda y el mapa/Moran's I tengan
            # una señal real que encontrar, no solo ruido condado a condado
            franja_dura = np.exp(-0.5 * ((posicion_y - 3.4) / 1.3) ** 2)
            intensidad_base = 0.28 + 1.9 * franja_dura
            intensidad = float(np.clip(intensidad_base * rng.lognormal(0, 0.22), 0.08, 3.0))

            customers = int(rng.uniform(5_000, 250_000))

            gust_base = 8 + 3 * np.sin(2 * np.pi * hora / 24.0) + rng.normal(0, 1.2, HORAS_TOTALES)
            gust = (
                gust_base
                + _ola(hora, 55 + corrimiento1, 9, 32 * intensidad)
                + _ola(hora, 140 + corrimiento2, 10, 26 * intensidad)
            )
            gust = np.clip(gust, 3, None)
            wind_speed_10m = gust * rng.uniform(0.55, 0.7)

            t2m_k = 278 + 4 * np.sin(2 * np.pi * (hora - 6) / 24.0) + rng.normal(0, 0.6, HORAS_TOTALES)
            d2m_k = t2m_k - rng.uniform(2, 6, HORAS_TOTALES)
            r2 = np.clip(60 + 15 * np.sin(2 * np.pi * hora / 24.0 + 1) + rng.normal(0, 5, HORAS_TOTALES), 20, 100)

            mslma = 1015 - _ola(hora, 55 + corrimiento1, 14, 18 * intensidad) - _ola(hora, 140 + corrimiento2, 16, 14 * intensidad)
            mslma += rng.normal(0, 0.8, HORAS_TOTALES)
            sp = mslma - rng.uniform(5, 15)

            rain = np.clip(_ola(hora, 55 + corrimiento1, 6, 4 * intensidad) + _ola(hora, 140 + corrimiento2, 7, 3 * intensidad)
                           + rng.normal(0, 0.3, HORAS_TOTALES), 0, None)
            csnow = np.where(t2m_k < 274, np.clip(rain * rng.uniform(0.3, 0.8), 0, None), 0.0)
            tp = rain + csnow  # identidad exacta, igual que en los datos reales, a propósito

            sdwe = np.clip(np.cumsum(csnow) * 0.01, 0, None)
            blh = np.clip(400 + _ola(hora, 55 + corrimiento1, 10, 700) + rng.normal(0, 60, HORAS_TOTALES), 50, None)
            tcc = np.clip(30 + _ola(hora, 55, 12, 55) + rng.normal(0, 8, HORAS_TOTALES), 0, 100)
            soil_moist = np.clip(0.18 + _ola(hora, 58, 14, 0.12) + rng.normal(0, 0.01, HORAS_TOTALES), 0.05, 0.5)

            umbral_gust = 22.0
            exc = np.clip(gust - umbral_gust, 0, None)

            # --- balance de apagones, hora a hora, con histéresis --------
            # dosis_previa acumula SIN decaer (lo ya roto no se repara
            # solo), es la fragilidad estructural que deja la primera ola:
            # postes y árboles débiles que ya cayeron, y que por lo tanto
            # no le restan daño nuevo a la segunda ola
            P = np.zeros(HORAS_TOTALES)
            N = np.zeros(HORAS_TOTALES)
            R = np.zeros(HORAS_TOTALES)
            dosis_previa = 0.0
            for h in range(1, HORAS_TOTALES):
                atenuacion = max(0.0, 1 - 0.75 * min(dosis_previa / 160.0, 1.0))
                if exc[h] > 0:
                    nuevo_dano = max(0.0, 0.0045 * exc[h] * atenuacion + rng.normal(0, 0.0006))
                else:
                    nuevo_dano = 0.0
                restauracion = 0.16 * P[h - 1]
                p_nuevo = P[h - 1] + nuevo_dano - restauracion
                if p_nuevo < 0.0015:
                    p_nuevo = 0.0
                P[h] = np.clip(p_nuevo, 0, 1)
                N[h] = nuevo_dano
                R[h] = restauracion
                dosis_previa += exc[h]

            D = pd.Series(P).rolling(6, min_periods=1).mean().to_numpy()
            osi = np.clip(0.40 * P + 0.35 * N + 0.25 * D - 0.10 * R, 0, None)
            osi = np.clip(osi, 0, 0.65)

            outage_count = np.round(P * customers).astype(int)

            marco = pd.DataFrame({
                "hour_idx": hora,
                "fipsCode": fips,
                "countyName": nombre,
                "stateAbbr": estado,
                "posicion_x": posicion_x,
                "posicion_y": posicion_y,
                "customersTracked": customers,
                "outageCount": outage_count,
                "P_t": P, "N_t": N, "D_t": D, "R_t": R, "osi": osi,
                "gust": gust, "wind_speed_10m": wind_speed_10m,
                "t2m": t2m_k, "d2m": d2m_k, "r2": r2,
                "mslma": mslma, "sp": sp,
                "tp": tp, "rain": rain, "csnow": csnow, "sdwe": sdwe,
                "blh": blh, "tcc": tcc, "soil_moist": soil_moist,
                "exc": exc,
            })
            filas.append(marco)

    df = pd.concat(filas, ignore_index=True)
    df["timestamp_et"] = pd.Timestamp("2031-01-01") + pd.to_timedelta(df["hour_idx"], unit="h")
    df["in_event_window"] = df["hour_idx"] >= 24

    df = df.sort_values(["fipsCode", "hour_idx"]).reset_index(drop=True)
    g = df.groupby("fipsCode")["osi"]
    for k in (1, 6, 24, 48):
        df[f"osi_lag{k}h"] = g.shift(k)

    for k, h in [("t01h", 1), ("t06h", 6), ("t24h", 24), ("t48h", 48)]:
        df[f"osi_target_{k}"] = g.shift(-h)

    # tiers por cuantil del pico de OSI de cada condado (0=mas tranquilo,
    # 4=mas severo), igual de espiritu que el severity_tier real, que
    # tambien es un ranking dentro del propio conjunto de condados
    pico = df.groupby("fipsCode")["osi"].transform("max")
    df["severity_tier"] = pd.qcut(pico.rank(method="first"), 5, labels=[0, 1, 2, 3, 4]).astype(int)

    orden_cols = [
        "timestamp_et", "fipsCode", "countyName", "stateAbbr", "hour_idx", "in_event_window",
        "posicion_x", "posicion_y",
        "severity_tier", "customersTracked", "outageCount",
        "P_t", "N_t", "D_t", "R_t", "osi",
        "osi_lag1h", "osi_lag6h", "osi_lag24h", "osi_lag48h",
        "osi_target_t01h", "osi_target_t06h", "osi_target_t24h", "osi_target_t48h",
        "gust", "wind_speed_10m", "t2m", "d2m", "r2",
        "mslma", "sp", "tp", "rain", "csnow", "sdwe", "blh", "tcc", "soil_moist", "exc",
    ]
    return df[orden_cols]


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "data" / "datos_simulados.csv"
    out.parent.mkdir(exist_ok=True)
    df = generar_datos_simulados()
    df.to_csv(out, index=False)
    print(f"listo: {len(df)} filas, {df['fipsCode'].nunique()} condados simulados -> {out}")

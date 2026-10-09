"""Agregaciones: horas -> días -> ventanas semanales, y emparejamiento de estaciones."""
import numpy as np
import pandas as pd

PROMEDIO_CIUDAD = "PROMEDIO_CIUDAD"


def horario_a_diario(largo):
    """De horas a días por estación.

    Para cada parámetro calcula el promedio y el máximo del día. Para la dirección
    del viento (WDR) calcula en su lugar la fracción de horas con viento del norte
    (entre 315° y 45°), porque promediar ángulos no tiene sentido.
    """
    df = largo.copy()
    # El SIMAT reporta la hora en que termina la medición (01:00 = de 00:00 a 01:00),
    # así que la hora 24:00 (00:00 del día siguiente) pertenece al día anterior.
    df["dia"] = (df["fecha"] - pd.Timedelta(hours=1)).dt.normalize()

    viento = df[df["parametro"] == "WDR"]
    resto = df[df["parametro"] != "WDR"]

    diario = resto.groupby(["estacion", "dia", "parametro"])["valor"].agg(["mean", "max"]).unstack("parametro")
    diario.columns = [f"{p.lower()}_{'prom' if a == 'mean' else 'max'}" for a, p in diario.columns]

    if not viento.empty:
        norte = ((viento["valor"] >= 315) | (viento["valor"] <= 45)).groupby(
            [viento["estacion"], viento["dia"]]).mean().rename("viento_norte_frac")
        diario = diario.join(norte, how="outer")

    return diario.reset_index().rename(columns={"dia": "fecha"})


def distancia_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def emparejar_estaciones(estaciones_redda, estaciones_destino, catalogo, max_km):
    """Asigna a cada estación REDDA una estación RAMA/REDMET.

    1. Misma clave, si la estación también mide contaminantes o meteorología.
    2. Si no, la más cercana dentro de max_km según el catálogo de coordenadas.
    3. Si no hay ninguna cerca (o no hay catálogo), el promedio de toda la ciudad.
    """
    destino = set(estaciones_destino)
    coords = {}
    if catalogo is not None and {"lat", "lon"} <= set(catalogo.columns):
        coords = catalogo.dropna(subset=["lat", "lon"]).set_index("estacion")[["lat", "lon"]].to_dict("index")

    filas = []
    for est in sorted(set(estaciones_redda)):
        if est in destino:
            filas.append((est, est, 0.0, "misma clave"))
            continue
        mejor, dist = None, None
        if est in coords:
            for cand in destino:
                if cand in coords:
                    d = distancia_km(coords[est]["lat"], coords[est]["lon"], coords[cand]["lat"], coords[cand]["lon"])
                    if dist is None or d < dist:
                        mejor, dist = cand, d
        if mejor is not None and dist <= max_km:
            filas.append((est, mejor, round(float(dist), 2), "más cercana"))
        else:
            filas.append((est, PROMEDIO_CIUDAD, np.nan, "promedio de la ciudad"))
    return pd.DataFrame(filas, columns=["estacion", "estacion_aire", "distancia_km", "metodo"])


def agregar_promedio_ciudad(diario):
    """Agrega una pseudo-estación con el promedio diario de todas las estaciones."""
    ciudad = diario.drop(columns="estacion").groupby("fecha").mean(numeric_only=True).reset_index()
    ciudad.insert(0, "estacion", PROMEDIO_CIUDAD)
    return pd.concat([diario, ciudad], ignore_index=True)


def ventanas(diario, ventana_dias, min_dias=None):
    """Promedios móviles de ventana_dias días que terminan en cada fecha.

    Regresa, por estación y fecha, el promedio de los ventana_dias días hasta esa
    fecha (columna *_sem) y el de la ventana anterior (columna *_sem_ant).
    Se exige al menos min_dias con dato en la ventana; si no, queda vacío.
    """
    min_dias = min_dias or max(1, ventana_dias // 2 + 1)
    valores = [c for c in diario.columns if c not in ("estacion", "fecha")]
    partes = []
    for est, g in diario.groupby("estacion"):
        g = g.set_index("fecha").sort_index()[valores].asfreq("D")
        sem = g.rolling(ventana_dias, min_periods=min_dias).mean()
        ant = sem.shift(ventana_dias)
        out = sem.add_suffix("_sem").join(ant.add_suffix("_sem_ant"))
        out.insert(0, "estacion_aire", est)
        partes.append(out.reset_index())
    return pd.concat(partes, ignore_index=True)

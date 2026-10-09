"""Limpieza de los archivos crudos del SIMAT (capa raw -> interim)."""
import pandas as pd

from src.utils.lectura import leer_csv_simat, normalizar_columnas, parsear_fecha

COLUMNAS_LARGO = ["fecha", "estacion", "parametro", "valor"]


def limpiar_largo(df, parametros=None, faltantes=(-99,)):
    """Limpia una tabla en formato largo (una fila por estación, fecha y parámetro).

    - normaliza nombres de columna y textos (mayúsculas, sin espacios);
    - convierte la fecha a datetime y el valor a número;
    - marca como faltantes los códigos de "sin dato" del SIMAT;
    - filtra los parámetros pedidos y elimina filas sin fecha, estación o valor;
    - elimina duplicados exactos de (fecha, estación, parámetro) quedándose con el primero.
    Regresa (df_limpio, resumen) donde resumen cuenta lo que se quitó en cada paso.
    """
    df = normalizar_columnas(df)
    faltan = set(COLUMNAS_LARGO) - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en el archivo crudo: {sorted(faltan)}")

    resumen = {"filas_crudas": len(df)}
    df = df[COLUMNAS_LARGO].copy()
    df["estacion"] = df["estacion"].astype(str).str.strip().str.upper()
    df["parametro"] = df["parametro"].astype(str).str.strip().str.upper()
    df["fecha"] = parsear_fecha(df["fecha"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df.loc[df["valor"].isin(list(faltantes)), "valor"] = pd.NA

    if parametros:
        antes = len(df)
        df = df[df["parametro"].isin([p.upper() for p in parametros])]
        resumen["filas_otros_parametros"] = antes - len(df)

    antes = len(df)
    df = df.dropna(subset=["fecha", "valor"])
    resumen["filas_sin_fecha_o_valor"] = antes - len(df)

    antes = len(df)
    df = df.drop_duplicates(subset=["fecha", "estacion", "parametro"], keep="first")
    resumen["filas_duplicadas"] = antes - len(df)

    df["valor"] = df["valor"].astype("float64")
    resumen["filas_limpias"] = len(df)
    return df.reset_index(drop=True), resumen


def limpiar_horario(path, parametros, faltantes):
    """Lee y limpia un archivo anual horario de RAMA o REDMET."""
    return limpiar_largo(leer_csv_simat(path), parametros, faltantes)


def limpiar_redda(path, faltantes):
    """Lee REDDA y la pasa a formato ancho: una fila por estación y muestra semanal.

    Las columnas de parámetros quedan en minúsculas (ph, so4, no3, nh4, pp, ...).
    """
    largo, resumen = limpiar_largo(leer_csv_simat(path), None, faltantes)
    largo["fecha"] = largo["fecha"].dt.normalize()
    ancho = largo.pivot_table(index=["estacion", "fecha"], columns="parametro",
                              values="valor", aggfunc="mean").reset_index()
    ancho.columns.name = None
    ancho = ancho.rename(columns={c: c.lower() for c in ancho.columns if c not in ("estacion", "fecha")})
    resumen["muestras"] = len(ancho)
    return ancho, resumen


def limpiar_catalogo(path):
    """Catálogo de estaciones con clave, nombre y coordenadas."""
    df = normalizar_columnas(leer_csv_simat(path))
    columnas = [c for c in ["estacion", "nombre", "lat", "lon"] if c in df.columns]
    df = df[columnas].copy()
    df["estacion"] = df["estacion"].astype(str).str.strip().str.upper()
    for c in ("lat", "lon"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.drop_duplicates("estacion").reset_index(drop=True)

"""Lectura de los CSV publicados por el SIMAT (aire.cdmx.gob.mx).

Los archivos traen unas líneas de notas antes del encabezado real, así que
se busca la primera línea que parezca encabezado antes de pasarle el texto a pandas.
Los nombres de columna se normalizan para que el resto del pipeline no dependa
de si el archivo dice "date" o "fecha", "id_station" o "cve_estac", etc.
"""
import gzip
import io
import pathlib

import pandas as pd

INICIOS_ENCABEZADO = ("date", "fecha", "cve_", "id_station")

# nombre en el archivo -> nombre en el pipeline
ALIAS_COLUMNAS = {
    "date": "fecha", "fecha": "fecha",
    "id_station": "estacion", "cve_estac": "estacion", "estacion": "estacion",
    "id_parameter": "parametro", "cve_param": "parametro", "parametro": "parametro",
    "value": "valor", "valor": "valor",
    "unit": "unidad", "unidad": "unidad", "id_unit": "unidad",
    "nom_estac": "nombre", "longitud": "lon", "lon": "lon", "latitud": "lat", "lat": "lat",
}


def leer_texto(path):
    path = pathlib.Path(path)
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return data.decode("latin-1")


def separar_notas(texto):
    """Regresa (notas, csv) donde notas son las líneas previas al encabezado."""
    lineas = texto.splitlines()
    inicio = next(
        (i for i, l in enumerate(lineas) if l.strip().lower().startswith(INICIOS_ENCABEZADO)),
        0,
    )
    return lineas[:inicio], "\n".join(lineas[inicio:])


def leer_csv_simat(path):
    """Lee un CSV del SIMAT (plano o .gz) como DataFrame, sin modificar valores."""
    _, csv = separar_notas(leer_texto(path))
    return pd.read_csv(io.StringIO(csv))


def normalizar_columnas(df):
    df = df.rename(columns=lambda c: str(c).strip().lower())
    return df.rename(columns={c: ALIAS_COLUMNAS[c] for c in df.columns if c in ALIAS_COLUMNAS})


FORMATOS_FECHA = ["%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]


def parsear_fecha(serie):
    """Convierte fechas del SIMAT a datetime.

    Acepta "dd/mm/aaaa hh:mm", "aaaa-mm-dd hh:mm" o solo la fecha. El SIMAT numera
    las horas de 1 a 24, así que "24:00" se convierte en las 00:00 del día siguiente.
    Primero prueba formatos fijos (mucho más rápido con millones de filas) y solo
    si ninguno funciona deja que pandas adivine.
    """
    s = serie.astype(str).str.strip()
    es_24 = s.str.contains(" 24:00", regex=False)
    s = s.str.replace(" 24:00", " 00:00", regex=False)
    muestra = s.head(1000)
    fechas = None
    for fmt in FORMATOS_FECHA:
        if pd.to_datetime(muestra, format=fmt, errors="coerce").notna().mean() > 0.99:
            fechas = pd.to_datetime(s, format=fmt, errors="coerce")
            break
    if fechas is None:
        fechas = pd.to_datetime(s, dayfirst=s.str.contains("/", regex=False).any(), format="mixed", errors="coerce")
    return fechas + pd.to_timedelta(es_24.astype(int), unit="D")


def es_texto(serie):
    return pd.api.types.is_object_dtype(serie) or pd.api.types.is_string_dtype(serie)

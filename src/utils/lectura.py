"""Lectura de los CSV publicados por el SIMAT (aire.cdmx.gob.mx).

Los archivos traen unas líneas de notas antes del encabezado real, así que
se busca la primera línea que parezca encabezado antes de pasarle el texto a pandas.
"""
import gzip
import io
import pathlib

import pandas as pd

INICIOS_ENCABEZADO = ("date", "fecha", "cve_", "id_station")


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

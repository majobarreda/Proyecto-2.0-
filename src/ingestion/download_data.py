"""Descarga los datos públicos del SIMAT (CDMX) y guarda una copia cruda.

Uso (desde la raíz del repositorio):
    python -m src.ingestion.download_data                  # años definidos en config
    python -m src.ingestion.download_data --anios 2015-2024

Qué descarga:
    - REDDA, depósito húmedo: química de la lluvia por estación (pH, iones, lluvia en mm).
    - RAMA: contaminantes horarios por estación, un archivo por año.
    - REDMET: meteorología horaria por estación, un archivo por año.

Todo queda sin modificar en data/raw/simat/. Si un archivo ya existe no se vuelve
a descargar. Los errores se registran en data/raw/simat/descargas.log.
No requiere credenciales.
"""
import argparse
import logging
import pathlib
import urllib.request

from src.utils.lectura import es_texto, leer_csv_simat, leer_texto, separar_notas

# El sitio publica los mismos archivos en dos hosts; se intenta el primero y luego el segundo.
HOSTS = [
    "http://www.aire.cdmx.gob.mx/opendata/",
    "http://datosabiertos.aire.cdmx.gob.mx:8080/opendata/",
]

REDDA = [
    "redda/concentracion.csv",  # concentración de iones en la lluvia (incluye pH y PP en mm)
    "redda/deposito.csv",       # cantidad de cada ion depositada
]

# Catálogo de estaciones (coordenadas). Es opcional: sin él se empareja por clave.
CATALOGO = "catalogos/cat_estacion.csv"

HORARIOS = [
    "anuales_horarios_gz/contaminantes_{anio}.csv.gz",
    "anuales_horarios_gz/meteorologia_{anio}.csv.gz",
]

RAW = pathlib.Path("data/raw/simat")
log = logging.getLogger("download_data")


def descargar(ruta):
    destino = RAW / ruta
    if destino.exists() and destino.stat().st_size > 0:
        log.info("Ya existe, se omite: %s", destino)
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    for host in HOSTS:
        url = host + ruta
        try:
            log.info("Descargando %s", url)
            with urllib.request.urlopen(url, timeout=300) as r:
                contenido = r.read()
            if contenido.lstrip()[:1] == b"<":
                raise ValueError("el servidor regresó una página HTML, no un CSV")
            destino.write_bytes(contenido)
            return destino
        except Exception as e:  # se registra y se intenta el siguiente host
            log.warning("Falló %s: %s", url, e)
    log.error("No se pudo descargar %s", ruta)
    return None


def resumir(path, n=5):
    """Imprime las notas del archivo, las primeras filas y los valores de columnas de texto."""
    notas, _ = separar_notas(leer_texto(path))
    df = leer_csv_simat(path)
    print(f"\n===== {path} =====")
    if notas:
        print("Notas del archivo:\n  " + "\n  ".join(notas))
    print(f"Filas: {len(df):,}  Columnas: {list(df.columns)}")
    print(df.head(n).to_string(index=False))
    for col in df.columns:
        if es_texto(df[col]) and df[col].nunique() <= 60:
            print(f"Valores de {col}: {sorted(df[col].dropna().astype(str).unique())}")


def leer_anios_config():
    try:
        import yaml
        cfg = yaml.safe_load(pathlib.Path("config/config.yaml").read_text())
        return cfg["anios"]["inicio"], cfg["anios"]["fin"]
    except Exception:
        return 2023, 2024


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anios", help="rango de años de los archivos horarios, p. ej. 2015-2024")
    p.add_argument("--sin-resumen", action="store_true", help="no imprimir la muestra de cada archivo")
    args = p.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(RAW / "descargas.log", encoding="utf-8")],
    )

    a, b = (int(x) for x in args.anios.split("-")) if args.anios else leer_anios_config()
    rutas = REDDA + [h.format(anio=y) for y in range(a, b + 1) for h in HORARIOS]
    fallidos = []
    if descargar(CATALOGO) is None:
        log.warning("Sin catálogo de estaciones; las estaciones se emparejarán solo por clave")
    for ruta in rutas:
        path = descargar(ruta)
        if path is None:
            fallidos.append(ruta)
        elif not args.sin_resumen:
            resumir(path)

    if fallidos:
        log.error("Archivos que no se pudieron descargar: %s", fallidos)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

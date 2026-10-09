"""Comparación de desempeño de operaciones del pipeline.

Uso (después de build_dataset):
    python -m src.processing.comparar_desempeno
    python -m src.processing.comparar_desempeno --repeticiones 3

Pruebas:
    1. Leer los contaminantes horarios en CSV comprimido (formato de descarga).
    2. Leer exactamente los mismos datos crudos guardados en Parquet.
    3. Leer los datos ya limpios de la capa interim (Parquet, solo parámetros útiles).
    4. Leer de Parquet solo SO2 y solo 3 columnas (lectura por columnas y filtro).
    5. Convertir fechas dejando que pandas adivine el formato.
    6. Convertir fechas con el formato fijo del SIMAT.

Cada prueba corre en un proceso aparte para medir su memoria sin que se mezcle
con las demás. Se guarda en reports/tables/desempeno.csv.
"""
import argparse
import multiprocessing as mp
import pathlib
import threading
import time

import pandas as pd

from src.utils.config import cargar_config


def _tamano_mb(rutas):
    return sum(p.stat().st_size for p in rutas) / 1e6


def _leer_csv(rutas):
    from src.utils.lectura import leer_csv_simat
    return sum(len(leer_csv_simat(p)) for p in rutas)


def _leer_parquet(rutas):
    return sum(len(pd.read_parquet(p)) for p in rutas)


def _leer_parquet_columnas(rutas):
    return sum(len(pd.read_parquet(p, columns=["fecha", "estacion", "valor"], filters=[("parametro", "==", "SO2")]))
               for p in rutas)


def _fechas_texto(rutas):
    from src.utils.lectura import leer_csv_simat
    return leer_csv_simat(rutas[0]).iloc[:, 0].astype(str).str.replace(" 24:00", " 00:00", regex=False)


def _fechas_inferidas(rutas):
    s = _fechas_texto(rutas)
    return int(pd.to_datetime(s, dayfirst=True, format="mixed", errors="coerce").notna().sum())


def _fechas_formato_fijo(rutas):
    s = _fechas_texto(rutas)
    return int(pd.to_datetime(s, format="%d/%m/%Y %H:%M", errors="coerce").notna().sum())


def _hijo(funcion, rutas, cola):
    import psutil
    proc = psutil.Process()
    base = proc.memory_info().rss
    pico = [base]
    activo = [True]

    def vigilar():
        while activo[0]:
            pico[0] = max(pico[0], proc.memory_info().rss)
            time.sleep(0.01)

    hilo = threading.Thread(target=vigilar, daemon=True)
    hilo.start()
    t0 = time.perf_counter()
    filas = funcion(rutas)
    segundos = time.perf_counter() - t0
    activo[0] = False
    hilo.join()
    cola.put((segundos, (pico[0] - base) / 1e6, filas))


def medir(funcion, rutas):
    ctx = mp.get_context("spawn")
    cola = ctx.Queue()
    p = ctx.Process(target=_hijo, args=(funcion, rutas, cola))
    p.start()
    resultado = cola.get()
    p.join()
    return resultado


def comparar(cfg, repeticiones=1):
    raw = pathlib.Path(cfg["rutas"]["raw"]) / "anuales_horarios_gz"
    interim = pathlib.Path(cfg["rutas"]["interim"]) / "horarios" / "red=contaminantes"
    csvs = sorted(raw.glob("contaminantes_*.csv*"))
    parquets = sorted(interim.glob("anio=*/datos.parquet"))
    if not csvs or not parquets:
        raise FileNotFoundError("Faltan archivos. Corre primero la descarga y build_dataset.")

    # Copia de los CSV crudos en Parquet, sin limpiar, para comparar formato contra formato
    from src.utils.lectura import leer_csv_simat
    crudos_pq = []
    for c in csvs:
        destino = pathlib.Path(cfg["rutas"]["interim"]) / "desempeno" / (c.name.split(".")[0] + ".parquet")
        if not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            leer_csv_simat(c).to_parquet(destino, index=False)
        crudos_pq.append(destino)

    pruebas = [
        ("Leer contaminantes en CSV.gz", _leer_csv, csvs),
        ("Leer los mismos datos crudos en Parquet", _leer_parquet, crudos_pq),
        ("Leer datos limpios de interim (Parquet)", _leer_parquet, parquets),
        ("Leer de Parquet solo SO2 y 3 columnas", _leer_parquet_columnas, parquets),
        ("Convertir fechas: pandas adivina el formato", _fechas_inferidas, csvs[:1]),
        ("Convertir fechas: formato fijo del SIMAT", _fechas_formato_fijo, csvs[:1]),
    ]
    filas = []
    for nombre, funcion, rutas in pruebas:
        tiempos, memorias = [], []
        for _ in range(repeticiones):
            seg, mem, n = medir(funcion, rutas)
            tiempos.append(seg)
            memorias.append(mem)
        filas.append({
            "prueba": nombre,
            "archivos": len(rutas),
            "tamano_mb": round(_tamano_mb(rutas), 1),
            "filas": n,
            "tiempo_s": round(min(tiempos), 2),
            "memoria_mb": round(max(memorias), 0),
            "resultado": "Correcto" if n > 0 else "Sin filas",
        })
        print(f"{nombre}: {min(tiempos):.2f} s, {max(memorias):.0f} MB")
    tabla = pd.DataFrame(filas)
    destino = pathlib.Path(cfg["rutas"].get("tablas", "reports/tables")) / "desempeno.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(destino, index=False)
    print("\n" + tabla.to_string(index=False))
    return tabla


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="ruta a un archivo de configuración")
    p.add_argument("--repeticiones", type=int, default=1)
    args = p.parse_args()
    comparar(cargar_config(args.config), args.repeticiones)


if __name__ == "__main__":
    main()

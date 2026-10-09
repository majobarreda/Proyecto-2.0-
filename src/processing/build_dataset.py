"""Construye el dataset analítico (capas raw -> interim -> processed).

Uso (desde la raíz del repositorio, después de descargar los datos):
    python -m src.processing.build_dataset
    python -m src.processing.build_dataset --forzar     # rehace todo aunque ya exista

Pasos:
    1. Cada archivo horario anual (RAMA, REDMET) se limpia por separado y se guarda
       en Parquet particionado por red y año, junto con su agregado diario.
       Procesar año por año evita cargar todos los millones de filas a la vez.
    2. REDDA se limpia y pasa a formato ancho (una fila por estación y muestra).
    3. Se calculan ventanas semanales de contaminación y clima por estación.
    4. Cada estación REDDA se empareja con la estación RAMA y REDMET más adecuada,
       y se pegan las ventanas a cada muestra de lluvia.
    5. Se agregan variables derivadas y se exporta data/processed/dataset_semanal.parquet.
"""
import argparse
import json
import logging
import pathlib
import re

import numpy as np
import pandas as pd

from src.processing.agregacion import (
    agregar_promedio_ciudad, emparejar_estaciones, horario_a_diario, ventanas,
)
from src.processing.limpieza import limpiar_catalogo, limpiar_horario, limpiar_redda
from src.utils.config import cargar_config

log = logging.getLogger("build_dataset")
PATRON_HORARIO = re.compile(r"(contaminantes|meteorologia)_(\d{4})\.csv(\.gz)?$")


def esta_al_dia(destino, origen):
    return destino.exists() and destino.stat().st_mtime >= origen.stat().st_mtime


def procesar_horarios(cfg, raw, interim, forzar):
    """Paso 1: raw horario -> interim (largo y diario), un archivo a la vez."""
    resumenes = []
    for f in sorted((raw / "anuales_horarios_gz").glob("*.csv*")):
        m = PATRON_HORARIO.search(f.name)
        if not m:
            continue
        red, anio = m.group(1), int(m.group(2))
        params = cfg["contaminantes"] if red == "contaminantes" else cfg["meteorologia"]
        destino = interim / "horarios" / f"red={red}" / f"anio={anio}" / "datos.parquet"
        destino_diario = interim / "diarios" / f"red={red}" / f"anio={anio}.parquet"
        destino_resumen = destino.with_name("resumen.json")
        if forzar or not (esta_al_dia(destino, f) and destino_diario.exists() and destino_resumen.exists()):
            log.info("Limpiando %s", f.name)
            largo, resumen = limpiar_horario(f, params, cfg["valores_faltantes"])
            destino.parent.mkdir(parents=True, exist_ok=True)
            largo.to_parquet(destino, index=False)
            destino_diario.parent.mkdir(parents=True, exist_ok=True)
            horario_a_diario(largo).to_parquet(destino_diario, index=False)
            resumen = {"archivo": f.name, "red": red, "anio": anio, "estaciones": int(largo["estacion"].nunique()), **resumen}
            destino_resumen.write_text(json.dumps(resumen))
        else:
            log.info("Al día, se omite: %s", f.name)
        resumenes.append(json.loads(destino_resumen.read_text()))
    return resumenes


def cargar_diarios(interim):
    """Une los agregados diarios de contaminantes y meteorología por estación y fecha."""
    tablas = {}
    for red in ("contaminantes", "meteorologia"):
        archivos = sorted((interim / "diarios" / f"red={red}").glob("*.parquet"))
        if archivos:
            t = pd.concat([pd.read_parquet(a) for a in archivos], ignore_index=True)
            # un mismo día puede aparecer en dos archivos anuales en la frontera de año
            tablas[red] = t.groupby(["estacion", "fecha"], as_index=False).mean(numeric_only=True)
    if not tablas:
        raise FileNotFoundError("No hay datos horarios procesados. Corre primero la descarga.")
    diario = None
    for t in tablas.values():
        diario = t if diario is None else diario.merge(t, on=["estacion", "fecha"], how="outer")
    return diario


def estaciones_con(diario, columna):
    if columna not in diario.columns:
        return []
    return diario.loc[diario[columna].notna(), "estacion"].unique().tolist()


def construir(cfg, forzar=False):
    raw = pathlib.Path(cfg["rutas"]["raw"])
    interim = pathlib.Path(cfg["rutas"]["interim"])
    processed = pathlib.Path(cfg["rutas"]["processed"])
    tablas = pathlib.Path(cfg["rutas"].get("tablas", "reports/tables"))
    sample = pathlib.Path(cfg["rutas"].get("sample", "data/sample"))
    for d in (interim, processed, tablas, sample):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Horarios
    resumenes = procesar_horarios(cfg, raw, interim, forzar)

    # 2. REDDA
    redda_path = raw / "redda" / "concentracion.csv"
    if not redda_path.exists():
        raise FileNotFoundError(f"No existe {redda_path}. Corre: python -m src.ingestion.download_data")
    redda, resumen_redda = limpiar_redda(redda_path, cfg["valores_faltantes"])
    redda.to_parquet(interim / "redda.parquet", index=False)
    resumenes.append({"archivo": redda_path.name, "red": "redda", **resumen_redda})
    pd.DataFrame(resumenes).to_csv(tablas / "limpieza_resumen.csv", index=False)

    catalogo = None
    cat_path = raw / "catalogos" / "cat_estacion.csv"
    if cat_path.exists():
        catalogo = limpiar_catalogo(cat_path)
        catalogo.to_parquet(interim / "estaciones.parquet", index=False)

    # 3. Ventanas semanales
    diario = agregar_promedio_ciudad(cargar_diarios(interim))
    sem = ventanas(diario, cfg["ventana_dias"])
    aire_prefijos = tuple(p.lower() + "_" for p in cfg["contaminantes"])
    cols_aire = [c for c in sem.columns if c.startswith(aire_prefijos)]
    cols_clima = [c for c in sem.columns if c not in cols_aire and c not in ("estacion_aire", "fecha")]

    # 4. Emparejar y unir
    so2_col = cfg["contaminantes"][0].lower() + "_prom"
    tmp_col = "tmp_prom"
    emp_aire = emparejar_estaciones(redda["estacion"], estaciones_con(diario, so2_col), catalogo, cfg["distancia_max_km"])
    emp_clima = emparejar_estaciones(redda["estacion"], estaciones_con(diario, tmp_col), catalogo, cfg["distancia_max_km"])
    emp = emp_aire.merge(emp_clima, on="estacion", suffixes=("_rama", "_redmet")).rename(
        columns={"estacion_aire_rama": "estacion_rama", "estacion_aire_redmet": "estacion_redmet"})
    emp.to_csv(tablas / "emparejamiento_estaciones.csv", index=False)

    ds = redda.merge(emp[["estacion", "estacion_rama", "estacion_redmet"]], on="estacion", how="left")
    ds = ds.merge(sem[["estacion_aire", "fecha"] + cols_aire].rename(columns={"estacion_aire": "estacion_rama"}),
                  on=["estacion_rama", "fecha"], how="left")
    ds = ds.merge(sem[["estacion_aire", "fecha"] + cols_clima].rename(columns={"estacion_aire": "estacion_redmet"}),
                  on=["estacion_redmet", "fecha"], how="left")

    # 5. Variables derivadas
    ds["anio"] = ds["fecha"].dt.year
    ds["mes"] = ds["fecha"].dt.month
    if "ph" in ds.columns:
        ds["lluvia_acida"] = ds["ph"] < 5.6
        ds["h_ueq_l"] = np.power(10.0, 6 - ds["ph"])  # iones hidrógeno en µeq/L
    ds = ds.sort_values(["estacion", "fecha"]).reset_index(drop=True)

    salida = processed / "dataset_semanal.parquet"
    ds.to_parquet(salida, index=False)
    muestra = sample / "dataset_semanal_muestra.csv"
    ds.sample(min(200, len(ds)), random_state=0).sort_values(["estacion", "fecha"]).to_csv(muestra, index=False)
    log.info("Dataset final: %s filas x %s columnas -> %s", len(ds), ds.shape[1], salida)
    return ds


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--forzar", action="store_true", help="rehacer aunque los archivos intermedios estén al día")
    p.add_argument("--config", help="ruta a un archivo de configuración")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    construir(cargar_config(args.config), args.forzar)


if __name__ == "__main__":
    main()

"""Corre todo el pipeline en orden.

    python main.py                     # descarga, procesa y valida los datos reales
    python main.py --sin-descarga      # usa lo que ya está en data/raw/
    python main.py --desempeno         # además mide CSV vs Parquet
    python main.py --sintetico         # prueba todo con datos sintéticos (sin internet)
"""
import argparse
import logging
import pathlib
import sys

from src.processing.build_dataset import construir
from src.processing.comparar_desempeno import comparar
from src.utils.config import cargar_config
from src.validation.validate_dataset import validar


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sin-descarga", action="store_true")
    p.add_argument("--desempeno", action="store_true")
    p.add_argument("--sintetico", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.sintetico:
        from src.utils.datos_sinteticos import generar
        cfg = cargar_config("config/config.sintetico.yaml")
        if not pathlib.Path(cfg["rutas"]["raw"]).exists():
            generar(cfg["rutas"]["raw"], cfg["anios"]["inicio"], cfg["anios"]["fin"])
    else:
        cfg = cargar_config()
        if not args.sin_descarga:
            from src.ingestion import download_data
            sys.argv = ["download_data", "--sin-resumen", "--anios", f"{cfg['anios']['inicio']}-{cfg['anios']['fin']}"]
            download_data.main()

    construir(cfg)
    tabla = validar(cfg)
    if args.desempeno:
        comparar(cfg)

    errores = tabla[(tabla["resultado"] == "FALLA") & (tabla["nivel"] == "error")]
    if not errores.empty:
        raise SystemExit(f"Validación con {len(errores)} errores. Revisa el reporte de validación.")
    logging.info("Listo. Dataset en %s/dataset_semanal.parquet", cfg["rutas"]["processed"])


if __name__ == "__main__":
    main()

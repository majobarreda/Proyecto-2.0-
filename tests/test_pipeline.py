"""Prueba de punta a punta con datos sintéticos pequeños (no usa internet)."""
import copy

import pandas as pd

from src.processing.build_dataset import construir
from src.utils.config import cargar_config
from src.utils.datos_sinteticos import generar
from src.validation.validate_dataset import validar


def test_pipeline_completo(tmp_path):
    raw = tmp_path / "raw"
    generar(raw, 2024, 2024, n_estaciones=5)
    cfg = copy.deepcopy(cargar_config("config/config.example.yaml"))
    cfg["anios"] = {"inicio": 2024, "fin": 2024}
    cfg["rutas"] = {"raw": str(raw), "interim": str(tmp_path / "interim"), "processed": str(tmp_path / "processed"),
                    "sample": str(tmp_path / "sample"), "tablas": str(tmp_path / "tablas"),
                    "reporte_validacion": str(tmp_path / "validation.md")}

    ds = construir(cfg)
    assert len(ds) > 0
    assert {"ph", "so2_prom_sem", "tmp_prom_sem", "lluvia_acida"} <= set(ds.columns)
    assert ds.duplicated(["estacion", "fecha"]).sum() == 0

    tabla = validar(cfg)
    errores = tabla[(tabla["resultado"] == "FALLA") & (tabla["nivel"] == "error")]
    assert errores.empty, errores.to_string()
    assert (tmp_path / "validation.md").exists()
    assert pd.read_parquet(tmp_path / "processed" / "dataset_semanal.parquet").shape == ds.shape

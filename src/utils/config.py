"""Carga de la configuración del proyecto.

Se lee config/config.yaml y, si no existe, config/config.example.yaml,
para que el pipeline funcione aunque nadie haya copiado el archivo todavía.
"""
import pathlib

import yaml


def cargar_config(ruta=None):
    candidatos = [ruta] if ruta else ["config/config.yaml", "config/config.example.yaml"]
    for c in candidatos:
        p = pathlib.Path(c)
        if p.exists():
            return yaml.safe_load(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("No se encontró config/config.yaml ni config/config.example.yaml")

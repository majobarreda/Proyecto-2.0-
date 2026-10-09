import pandas as pd
import pytest

from src.validation.validate_dataset import columnas_fuera_de_rango, validate_required_columns


def test_columnas_requeridas():
    df = pd.DataFrame({"ph": [5.0]})
    validate_required_columns(df, ["ph"])
    with pytest.raises(ValueError, match="Faltan columnas"):
        validate_required_columns(df, ["ph", "fecha"])


def test_rangos_usan_el_parametro_de_la_columna():
    df = pd.DataFrame({"ph": [5.0, 12.0], "so2_prom_sem": [3.0, -1.0], "estacion": ["A", "B"]})
    fuera = columnas_fuera_de_rango(df, {"PH": [3, 9], "SO2": [0, 500]})
    assert fuera == {"ph": 1, "so2_prom_sem": 1}

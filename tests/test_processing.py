import pandas as pd

from src.processing.agregacion import PROMEDIO_CIUDAD, emparejar_estaciones, horario_a_diario, ventanas
from src.processing.limpieza import limpiar_largo
from src.utils.lectura import parsear_fecha


def crudo(filas):
    return pd.DataFrame(filas, columns=["date", "id_station", "id_parameter", "value", "unit"])


def test_hora_24_es_medianoche_del_dia_siguiente():
    f = parsear_fecha(pd.Series(["31/12/2024 24:00", "01/01/2024 01:00"]))
    assert f[0] == pd.Timestamp("2025-01-01 00:00")
    assert f[1] == pd.Timestamp("2024-01-01 01:00")


def test_limpieza_quita_faltantes_duplicados_y_otros_parametros():
    df = crudo([
        ["01/06/2024 01:00", "mer ", "so2", 3, 1],
        ["01/06/2024 01:00", "MER", "SO2", 3, 1],      # duplicado
        ["01/06/2024 02:00", "MER", "SO2", -99, 1],    # sin dato
        ["01/06/2024 01:00", "MER", "O3", 40, 1],      # parámetro que no se usa
    ])
    limpio, resumen = limpiar_largo(df, ["SO2"], [-99])
    assert len(limpio) == 1
    assert limpio.loc[0, "estacion"] == "MER"
    assert resumen["filas_duplicadas"] == 1
    assert resumen["filas_sin_fecha_o_valor"] == 1
    assert resumen["filas_otros_parametros"] == 1


def test_diario_asigna_hora_24_al_mismo_dia_y_calcula_viento_norte():
    largo = pd.DataFrame({
        "fecha": pd.to_datetime(["2024-06-01 01:00", "2024-06-02 00:00", "2024-06-01 01:00", "2024-06-02 00:00"]),
        "estacion": "MER",
        "parametro": ["SO2", "SO2", "WDR", "WDR"],
        "valor": [2.0, 4.0, 350.0, 180.0],
    })
    d = horario_a_diario(largo)
    assert len(d) == 1
    assert d.loc[0, "fecha"] == pd.Timestamp("2024-06-01")
    assert d.loc[0, "so2_prom"] == 3.0
    assert d.loc[0, "so2_max"] == 4.0
    assert d.loc[0, "viento_norte_frac"] == 0.5


def test_ventanas_semana_y_semana_anterior():
    dias = pd.date_range("2024-06-01", periods=14, freq="D")
    diario = pd.DataFrame({"estacion": "MER", "fecha": dias, "so2_prom": [1.0] * 7 + [3.0] * 7})
    v = ventanas(diario, 7).set_index("fecha")
    assert v.loc["2024-06-14", "so2_prom_sem"] == 3.0
    assert v.loc["2024-06-14", "so2_prom_sem_ant"] == 1.0


def test_emparejar_por_clave_cercania_y_promedio():
    catalogo = pd.DataFrame({"estacion": ["A", "B", "R1", "R2"],
                             "lat": [19.40, 19.30, 19.401, 25.0], "lon": [-99.10, -99.20, -99.101, -100.0]})
    emp = emparejar_estaciones(["A", "R1", "R2"], ["A", "B"], catalogo, max_km=10).set_index("estacion")
    assert emp.loc["A", "metodo"] == "misma clave"
    assert emp.loc["R1", "estacion_aire"] == "A"
    assert emp.loc["R2", "estacion_aire"] == PROMEDIO_CIUDAD

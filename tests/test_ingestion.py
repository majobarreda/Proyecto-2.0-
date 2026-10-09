import gzip

from src.utils.lectura import leer_csv_simat, separar_notas

MUESTRA = "Nota 1 del SIMAT\nNota 2\ndate,id_station,id_parameter,value,unit\n01/01/2024 01:00,MER,SO2,2,1\n"


def test_separa_notas_del_encabezado():
    notas, csv = separar_notas(MUESTRA)
    assert notas == ["Nota 1 del SIMAT", "Nota 2"]
    assert csv.startswith("date,")


def test_lee_csv_comprimido(tmp_path):
    archivo = tmp_path / "contaminantes_2024.csv.gz"
    archivo.write_bytes(gzip.compress(MUESTRA.encode("latin-1")))
    df = leer_csv_simat(archivo)
    assert list(df.columns) == ["date", "id_station", "id_parameter", "value", "unit"]
    assert len(df) == 1

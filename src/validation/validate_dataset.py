"""Valida las capas interim y processed y documenta el resultado.

Uso (después de build_dataset):
    python -m src.validation.validate_dataset

Revisa: existencia de columnas, tipos, faltantes, duplicados, rangos válidos,
consistencia temporal, consistencia entre tablas y volumen esperado.
Escribe la tabla en reports/tables/validacion.csv y el reporte en docs/validation.md.
Termina con código de error si falla alguna revisión de nivel "error".
"""
import argparse
import datetime as dt
import logging
import pathlib

import pandas as pd

from src.utils.config import cargar_config

log = logging.getLogger("validate_dataset")

COLUMNAS_REQUERIDAS = ["estacion", "fecha", "ph", "estacion_rama", "estacion_redmet", "anio", "mes", "lluvia_acida"]
UMBRAL_FALTANTES = 0.30  # más de 30% vacío en una columna se reporta como aviso


class Validador:
    def __init__(self):
        self.filas = []

    def registrar(self, categoria, revision, ok, detalle, nivel="error"):
        self.filas.append({"categoria": categoria, "revision": revision, "nivel": nivel,
                           "resultado": "OK" if ok else "FALLA", "detalle": detalle})
        (log.info if ok else log.warning)("%s | %s | %s", "OK" if ok else "FALLA", revision, detalle)

    def tabla(self):
        return pd.DataFrame(self.filas)


# --- revisiones individuales (también se usan en tests/) ----------------------

def validate_required_columns(df, required_columns):
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas: {sorted(missing)}")


def columnas_fuera_de_rango(df, rangos):
    """Regresa {columna: filas fuera de rango} para las columnas cuyo parámetro tiene rango.

    Una columna como so2_prom_sem se revisa con el rango de SO2.
    """
    fuera = {}
    for col in df.columns:
        param = col.split("_")[0].upper()
        if param in rangos and pd.api.types.is_numeric_dtype(df[col]):
            lo, hi = rangos[param]
            n = int(((df[col] < lo) | (df[col] > hi)).sum())
            if n:
                fuera[col] = n
    return fuera


# --- validación completa ------------------------------------------------------

def validar(cfg):
    v = Validador()
    interim = pathlib.Path(cfg["rutas"]["interim"])
    processed = pathlib.Path(cfg["rutas"]["processed"])
    tablas = pathlib.Path(cfg["rutas"].get("tablas", "reports/tables"))
    rangos = cfg["rangos"]

    ds_path = processed / "dataset_semanal.parquet"
    if not ds_path.exists():
        raise FileNotFoundError(f"No existe {ds_path}. Corre: python -m src.processing.build_dataset")
    ds = pd.read_parquet(ds_path)
    redda = pd.read_parquet(interim / "redda.parquet")

    # Existencia de columnas
    faltan = set(COLUMNAS_REQUERIDAS) - set(ds.columns)
    v.registrar("columnas", "Columnas requeridas en el dataset final", not faltan,
                "todas presentes" if not faltan else f"faltan {sorted(faltan)}")
    aire = [c for c in ds.columns if c.startswith(tuple(p.lower() + "_" for p in cfg["contaminantes"]))]
    v.registrar("columnas", "Columnas de contaminantes", bool(aire), f"{len(aire)} columnas")

    # Tipos de datos
    v.registrar("tipos", "fecha es datetime", pd.api.types.is_datetime64_any_dtype(ds["fecha"]), str(ds["fecha"].dtype))
    numericas_mal = [c for c in ["ph"] + aire if c in ds.columns and not pd.api.types.is_numeric_dtype(ds[c])]
    v.registrar("tipos", "Mediciones numéricas", not numericas_mal,
                "todas numéricas" if not numericas_mal else f"no numéricas: {numericas_mal}")

    # Valores faltantes
    pct = ds.isna().mean()
    v.registrar("faltantes", "pH sin faltantes", pct.get("ph", 1) == 0, f"{pct.get('ph', 1):.1%} vacío")
    altas = pct[pct > UMBRAL_FALTANTES]
    v.registrar("faltantes", f"Columnas con más de {UMBRAL_FALTANTES:.0%} vacío", altas.empty,
                "ninguna" if altas.empty else ", ".join(f"{c} {p:.0%}" for c, p in altas.items()), nivel="aviso")

    # Duplicados
    dup = int(ds.duplicated(subset=["estacion", "fecha"]).sum())
    v.registrar("duplicados", "Una fila por estación y semana", dup == 0, f"{dup} duplicados")

    # Rangos válidos
    fuera = columnas_fuera_de_rango(ds, rangos)
    v.registrar("rangos", "Valores dentro de rangos físicos (config.rangos)", not fuera,
                "todo en rango" if not fuera else ", ".join(f"{c}: {n}" for c, n in fuera.items()), nivel="aviso")

    # Consistencia temporal
    a, b = cfg["anios"]["inicio"], cfg["anios"]["fin"]
    fuera_periodo = int((~ds["anio"].between(a, b)).sum())
    v.registrar("temporal", f"Muestras dentro de {a}-{b}", fuera_periodo == 0,
                f"{fuera_periodo} fuera del periodo", nivel="aviso")
    futuras = int((ds["fecha"] > pd.Timestamp.today()).sum())
    v.registrar("temporal", "Sin fechas futuras", futuras == 0, f"{futuras} fechas futuras")
    fuera_lluvias = (~ds["mes"].between(5, 11)).mean()
    v.registrar("temporal", "Muestras en temporada de lluvias (mayo-noviembre)", fuera_lluvias < 0.10,
                f"{fuera_lluvias:.1%} fuera de temporada", nivel="aviso")

    # Consistencia entre tablas
    v.registrar("entre tablas", "Mismas muestras en interim/redda y processed", len(ds) == len(redda),
                f"redda {len(redda)} vs final {len(ds)}")
    sin_par = int(ds["estacion_rama"].isna().sum() + ds["estacion_redmet"].isna().sum())
    v.registrar("entre tablas", "Toda estación REDDA tiene estación de aire y clima", sin_par == 0,
                f"{sin_par} filas sin pareja")
    if aire:
        sin_aire = ds[aire].isna().all(axis=1).mean()
        v.registrar("entre tablas", "Muestras con datos de contaminación en su semana", sin_aire < 0.20,
                    f"{sin_aire:.1%} sin ningún dato de contaminantes", nivel="aviso")

    # Volumen esperado
    resumen_path = tablas / "limpieza_resumen.csv"
    if resumen_path.exists():
        res = pd.read_csv(resumen_path)
        hor = res[res["red"].isin(["contaminantes", "meteorologia"])]
        for _, r in hor.iterrows():
            params = len(cfg["contaminantes"] if r["red"] == "contaminantes" else cfg["meteorologia"])
            esperado = r["estaciones"] * params * 8760
            ratio = r["filas_limpias"] / esperado if esperado else 0
            v.registrar("volumen", f"Filas horarias {r['red']} {int(r['anio'])}", ratio >= 0.5,
                        f"{int(r['filas_limpias']):,} filas ({ratio:.0%} de {int(esperado):,} posibles)", nivel="aviso")
    v.registrar("volumen", "Dataset final no vacío", len(ds) > 0, f"{len(ds):,} filas")

    tabla = v.tabla()
    tablas.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(tablas / "validacion.csv", index=False)
    escribir_reporte(tabla, ds, pathlib.Path(cfg["rutas"].get("reporte_validacion", "docs/validation.md")), cfg)
    return tabla


def escribir_reporte(tabla, ds, destino, cfg):
    fallas = tabla[(tabla["resultado"] == "FALLA") & (tabla["nivel"] == "error")]
    avisos = tabla[(tabla["resultado"] == "FALLA") & (tabla["nivel"] == "aviso")]
    lineas = [
        "# Validación",
        "",
        "Este archivo lo genera `python -m src.validation.validate_dataset`. No editar a mano.",
        "",
        f"- Fecha de ejecución: {dt.datetime.now():%Y-%m-%d %H:%M}",
        f"- Datos de entrada: `{cfg['rutas']['raw']}`",
        f"- Dataset validado: {len(ds):,} filas × {ds.shape[1]} columnas, {ds['estacion'].nunique()} estaciones REDDA",
        f"- Resultado: **{len(fallas)} errores, {len(avisos)} avisos**",
        "",
        "| Categoría | Revisión | Nivel | Resultado | Detalle |",
        "|---|---|---|---|---|",
    ]
    for _, r in tabla.iterrows():
        lineas.append(f"| {r['categoria']} | {r['revision']} | {r['nivel']} | {r['resultado']} | {r['detalle']} |")
    lineas += ["", "Nivel *error* detiene el pipeline; nivel *aviso* se documenta y se revisa en el análisis.", ""]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="ruta a un archivo de configuración")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    tabla = validar(cargar_config(args.config))
    errores = tabla[(tabla["resultado"] == "FALLA") & (tabla["nivel"] == "error")]
    if not errores.empty:
        raise SystemExit(f"Validación con {len(errores)} errores. Ver docs/validation.md")


if __name__ == "__main__":
    main()

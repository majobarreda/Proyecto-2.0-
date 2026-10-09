"""Genera datos SINTÉTICOS con el mismo formato que los archivos del SIMAT.

Sirven para probar el pipeline y medir desempeño sin internet. NO son datos reales
y nunca deben usarse para el análisis.

Uso:
    python -m src.utils.datos_sinteticos --destino data/synthetic/raw/simat --anios 2023-2024
"""
import argparse
import gzip
import pathlib

import numpy as np
import pandas as pd

NOTAS = "Datos SINTETICOS para pruebas, no son mediciones reales\nFormato imitando al SIMAT\n"


def _estaciones(n, rng):
    lat = rng.uniform(19.20, 19.60, n)
    lon = rng.uniform(-99.30, -98.95, n)
    return pd.DataFrame({"estacion": [f"SA{i:02d}" for i in range(1, n + 1)], "lat": lat, "lon": lon})


def _escribir(df, path, comprimir):
    path.parent.mkdir(parents=True, exist_ok=True)
    texto = NOTAS + df.to_csv(index=False)
    path.write_bytes(gzip.compress(texto.encode("latin-1")) if comprimir else texto.encode("latin-1"))


def _fecha_simat(horas):
    """Fechas con horas numeradas de 1 a 24, como el SIMAT."""
    texto = horas.strftime("%d/%m/%Y %H:%M")
    es_medianoche = horas.hour == 0
    previo = (horas - pd.Timedelta(days=1)).strftime("%d/%m/%Y 24:00")
    return np.where(es_medianoche, previo, texto)


def generar(destino, anio_ini, anio_fin, n_estaciones=20, semilla=0):
    rng = np.random.default_rng(semilla)
    destino = pathlib.Path(destino)
    est = _estaciones(n_estaciones, rng)
    sur = (19.60 - est["lat"].to_numpy()) / 0.40  # 0 en el norte, 1 en el sur

    # REDDA: algunas estaciones comparten clave con RAMA, otras solo están en el catálogo
    redda = pd.DataFrame({
        "estacion": list(est["estacion"].iloc[:4]) + [f"SR{i:02d}" for i in range(1, 5)],
        "lat": list(est["lat"].iloc[:4]) + list(rng.uniform(19.20, 19.60, 4)),
        "lon": list(est["lon"].iloc[:4]) + list(rng.uniform(-99.30, -98.95, 4)),
    })
    catalogo = pd.concat([est, redda[~redda["estacion"].isin(est["estacion"])]], ignore_index=True)
    catalogo = catalogo.rename(columns={"estacion": "cve_estac", "lat": "latitud", "lon": "longitud"})
    catalogo.insert(1, "nom_estac", "Estación sintética " + catalogo["cve_estac"])
    _escribir(catalogo, destino / "catalogos" / "cat_estacion.csv", False)

    so2_diario_por_est = {}
    for anio in range(anio_ini, anio_fin + 1):
        horas = pd.date_range(f"{anio}-01-01 01:00", f"{anio + 1}-01-01 00:00", freq="h")
        n = len(horas)
        hora = horas.hour.to_numpy()
        doy = horas.dayofyear.to_numpy()
        fechas = _fecha_simat(horas)

        filas_c, filas_m = [], []
        for i, e in enumerate(est["estacion"]):
            base_so2 = 2 + 4 * (1 - sur[i]) + 1.5 * np.sin(2 * np.pi * doy / 365)
            so2 = np.clip(base_so2 + rng.gamma(1.5, 1.2, n), 0, None)
            no2 = np.clip(20 + 10 * np.sin(2 * np.pi * (hora - 8) / 24) + rng.normal(0, 6, n), 0, None)
            nox = no2 * rng.uniform(1.3, 1.8, n)
            tmp = 16 + 6 * np.sin(2 * np.pi * (hora - 9) / 24) + 3 * np.sin(2 * np.pi * (doy - 80) / 365) + rng.normal(0, 1.5, n)
            rh = np.clip(55 - 1.5 * (tmp - 16) + rng.normal(0, 8, n), 5, 100)
            wdr = rng.choice([0, 20, 45, 90, 180, 200, 270, 330, 350], n).astype(float)
            wsp = np.clip(rng.gamma(2, 1.2, n), 0, None)
            so2_diario_por_est.setdefault(e, []).append(pd.Series(so2, index=horas).resample("D").mean())

            for nombre, vals, filas in (("SO2", so2, filas_c), ("NO2", no2, filas_c), ("NOX", nox, filas_c), ("CO", no2 / 30, filas_c),
                                        ("TMP", tmp, filas_m), ("RH", rh, filas_m), ("WDR", wdr, filas_m), ("WSP", wsp, filas_m)):
                v = np.round(vals, 1)
                v[rng.random(n) < 0.02] = -99  # código de "sin dato"
                filas.append(pd.DataFrame({"date": fechas, "id_station": e, "id_parameter": nombre, "value": v, "unit": 1}))

        cont = pd.concat(filas_c, ignore_index=True)
        cont = pd.concat([cont, cont.sample(50, random_state=anio)], ignore_index=True)  # duplicados a propósito
        _escribir(cont, destino / "anuales_horarios_gz" / f"contaminantes_{anio}.csv.gz", True)
        _escribir(pd.concat(filas_m, ignore_index=True), destino / "anuales_horarios_gz" / f"meteorologia_{anio}.csv.gz", True)

    # REDDA: muestras semanales de mayo a noviembre; el pH baja con más SO2 y hacia el sur
    so2_ciudad = pd.concat({k: pd.concat(v) for k, v in so2_diario_por_est.items()}, axis=1).mean(axis=1)
    filas = []
    for _, r in redda.iterrows():
        cerca = r["estacion"] if r["estacion"] in so2_diario_por_est else None
        so2_d = pd.concat(so2_diario_por_est[cerca]) if cerca else so2_ciudad
        so2_sem = so2_d.rolling(7, min_periods=4).mean()
        lat_sur = (19.60 - r["lat"]) / 0.40
        for anio in range(anio_ini, anio_fin + 1):
            for fecha in pd.date_range(f"{anio}-05-06", f"{anio}-11-25", freq="7D"):
                if rng.random() < 0.15:
                    continue  # semana sin muestra
                s = so2_sem.get(fecha, np.nan)
                ph = 6.6 - 0.12 * (s if s == s else 5) - 0.6 * lat_sur + rng.normal(0, 0.25)
                so4 = max(0.5, 15 + 3 * (s if s == s else 5) + rng.normal(0, 4))
                vals = {"PH": round(ph, 2), "SO4": round(so4, 2), "NO3": round(max(0.5, 12 + rng.normal(0, 4)), 2),
                        "NH4": round(max(0.5, 18 + rng.normal(0, 5)), 2), "PP": round(max(0.2, rng.gamma(2, 12)), 1)}
                for k, v in vals.items():
                    filas.append({"date": fecha.strftime("%d/%m/%Y"), "id_station": r["estacion"], "id_parameter": k, "value": v, "unit": 1})
    _escribir(pd.DataFrame(filas), destino / "redda" / "concentracion.csv", False)
    return destino


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--destino", default="data/synthetic/raw/simat")
    p.add_argument("--anios", default="2023-2024")
    p.add_argument("--estaciones", type=int, default=20)
    args = p.parse_args()
    a, b = (int(x) for x in args.anios.split("-"))
    print("Generados en", generar(args.destino, a, b, args.estaciones))


if __name__ == "__main__":
    main()

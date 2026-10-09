# Diccionario de datos

> **Borrador.** Las columnas de abajo vienen de la documentación del SIMAT y de estudios publicados. Hay que confirmarlas al correr `python -m src.ingestion.download_data` y llenar las columnas de valores faltantes y observaciones con lo que muestre `notebooks/01_exploration.ipynb`.

## Fuente 1: REDDA, depósito húmedo (`data/raw/simat/redda/concentracion.csv`)

| Campo | Detalle |
|---|---|
| Origen | SIMAT, Red de Depósito Atmosférico |
| Propietario | Secretaría del Medio Ambiente de la CDMX (SEDEMA) |
| Método de acceso | Descarga pública por HTTP, automatizada en `src/ingestion/download_data.py` |
| Formato | CSV con líneas de notas antes del encabezado |
| Frecuencia | Muestras semanales en temporada de lluvias (mayo a noviembre), desde 1997 |
| Volumen aproximado | Por confirmar |
| Restricciones de uso | Datos públicos del Gobierno de la CDMX |
| Problemas conocidos | Semanas sin muestra; formato largo (una fila por parámetro) |

| Variable | Tipo | Descripción | Unidad | Faltantes | Observaciones |
|---|---|---|---|---|---|
| `date` | datetime | Fecha de la muestra semanal | — | ? | Por confirmar formato |
| `id_station` | string | Clave de la estación REDDA | — | ? | |
| `id_parameter` | string | Parámetro medido (pH, conductividad, SO4, NO3, NH4, Ca, Mg, Na, K, Cl, PP) | — | ? | PP = lluvia en mm |
| `value` | float | Valor medido | Depende del parámetro | ? | |
| `unit` | string/int | Unidad o clave de unidad | — | ? | |

## Fuente 2: RAMA, contaminantes horarios (`data/raw/simat/anuales_horarios_gz/contaminantes_AAAA.csv.gz`)

| Campo | Detalle |
|---|---|
| Origen | SIMAT, Red Automática de Monitoreo Atmosférico |
| Propietario | SEDEMA |
| Método de acceso | Descarga pública por HTTP, un archivo comprimido por año |
| Formato | CSV comprimido (gz) con notas antes del encabezado |
| Frecuencia | Horaria, desde 1986 |
| Volumen aproximado | Millones de filas por año (por confirmar) |
| Problemas conocidos | Horas sin dato; horario estándar del centro (UTC-6) sin horario de verano |

| Variable | Tipo | Descripción | Unidad | Faltantes | Observaciones |
|---|---|---|---|---|---|
| `date` | datetime | Fecha y hora de la medición | Hora local UTC-6 | ? | |
| `id_station` | string | Clave de la estación | — | ? | |
| `id_parameter` | string | SO2, NO2, NOX, NO, CO, O3, PM10, PM25 | — | ? | |
| `value` | float | Concentración | ppb, ppm o µg/m³ según parámetro | ? | |
| `unit` | int | Clave de unidad | — | ? | |

## Fuente 3: REDMET, meteorología horaria (`data/raw/simat/anuales_horarios_gz/meteorologia_AAAA.csv.gz`)

Mismo formato que RAMA. Parámetros: `TMP` (temperatura, °C), `RH` (humedad relativa, %), `WDR` (dirección del viento, grados), `WSP` (velocidad del viento, m/s).

## Dataset final: `data/processed/dataset_semanal.parquet`

Una fila = una muestra semanal de lluvia en una estación REDDA. Lo genera `python -m src.processing.build_dataset`. Muestra en `data/sample/dataset_semanal_muestra.csv`.

| Variable | Tipo | Descripción | Unidad | Origen |
|---|---|---|---|---|
| `estacion` | string | Clave de la estación REDDA | — | REDDA |
| `fecha` | datetime | Fecha de la muestra semanal | — | REDDA |
| `ph`, `so4`, `no3`, `nh4`, `pp`, ... | float | Un parámetro de REDDA por columna, en minúsculas | Según REDDA (pp en mm) | REDDA |
| `estacion_rama` | string | Estación de contaminantes emparejada (`PROMEDIO_CIUDAD` si no hay cercana) | — | Emparejamiento |
| `estacion_redmet` | string | Estación de meteorología emparejada | — | Emparejamiento |
| `so2_prom_sem`, `no2_prom_sem`, `nox_prom_sem` | float | Promedio de los 7 días hasta la muestra | ppb | RAMA |
| `so2_max_sem`, ... | float | Promedio de los máximos diarios en esos 7 días | ppb | RAMA |
| `*_sem_ant` | float | Lo mismo para los 7 días anteriores (rezago) | ppb / °C / % | RAMA / REDMET |
| `tmp_prom_sem`, `rh_prom_sem`, `wsp_prom_sem` | float | Temperatura, humedad y viento promedio de la semana | °C, %, m/s | REDMET |
| `viento_norte_frac_sem` | float | Fracción de horas con viento del norte (315° a 45°) | 0 a 1 | REDMET |
| `anio`, `mes` | int | Año y mes de la muestra | — | Derivada |
| `lluvia_acida` | bool | pH menor a 5.6 | — | Derivada |
| `h_ueq_l` | float | Concentración de iones hidrógeno, 10^(6 − pH) | µeq/L | Derivada |

Los nombres exactos de las columnas de REDDA dependen de las claves de parámetro del archivo real.

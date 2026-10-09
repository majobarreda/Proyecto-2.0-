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

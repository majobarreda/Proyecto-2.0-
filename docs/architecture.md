# Arquitectura

## Arquitectura real (segundo parcial)

```
SIMAT (aire.cdmx.gob.mx/opendata)
  redda/concentracion.csv           anuales_horarios_gz/contaminantes_AAAA.csv.gz
  catalogos/cat_estacion.csv        anuales_horarios_gz/meteorologia_AAAA.csv.gz
        │
        ↓  python -m src.ingestion.download_data
data/raw/simat/                     copia exacta de la descarga, sin modificar
        │
        ↓  python -m src.processing.build_dataset   (un archivo anual a la vez)
data/interim/
  horarios/red=contaminantes/anio=2024/datos.parquet   horas limpias, formato largo
  horarios/red=meteorologia/anio=2024/datos.parquet
  diarios/red=.../anio=2024.parquet                    promedio y máximo por día y estación
  redda.parquet                                        una fila por estación y muestra semanal
  estaciones.parquet                                   catálogo con coordenadas
        │
        ↓  ventanas de 7 días + emparejamiento de estaciones
data/processed/dataset_semanal.parquet                 estación REDDA × semana
        │
        ↓  python -m src.validation.validate_dataset
docs/validation.md  +  reports/tables/validacion.csv
        │
        ↓  python -m src.analysis.* (examen final)
reports/
```

Todo se puede correr con un solo comando: `python main.py`.

## Qué hace cada paso

| Paso | Módulo | Entrada | Salida | Transformaciones |
|---|---|---|---|---|
| Adquisición | `src/ingestion/download_data.py` | Sitio del SIMAT | `data/raw/simat/` | Descarga, no repite archivos existentes, rechaza respuestas HTML, registra errores en `descargas.log` |
| Limpieza horaria | `src/processing/limpieza.py` | CSV.gz por año | `interim/horarios/` | Quita notas del encabezado, normaliza columnas, convierte fechas (hora 24 → 00:00 del día siguiente), marca -99 como faltante, filtra parámetros, elimina duplicados |
| Agregación diaria | `src/processing/agregacion.py` | Horas limpias | `interim/diarios/` | Promedio y máximo por día; para el viento, fracción de horas con viento del norte |
| REDDA | `src/processing/limpieza.py` | `concentracion.csv` | `interim/redda.parquet` | Formato largo → ancho (ph, so4, no3, nh4, pp...) |
| Ventanas | `src/processing/agregacion.py` | Diarios | en memoria | Promedio de los 7 días hasta la muestra y de los 7 días anteriores |
| Emparejamiento | `src/processing/agregacion.py` | REDDA + catálogo | `reports/tables/emparejamiento_estaciones.csv` | Misma clave → estación más cercana ≤ 10 km → promedio de la ciudad |
| Dataset final | `src/processing/build_dataset.py` | Todo lo anterior | `processed/dataset_semanal.parquet` | Unión, variables derivadas (`lluvia_acida`, `h_ueq_l`, `anio`, `mes`) |
| Validación | `src/validation/validate_dataset.py` | interim + processed | `docs/validation.md` | 8 tipos de revisión, ver ese archivo |

## Dónde se almacenan los datos

En la computadora de cada integrante, dentro de `data/`. GitHub solo guarda el código y `data/sample/`. Cualquiera reconstruye los datos con `python main.py`.

## Herramientas

Python, pandas, pyarrow (Parquet), PyYAML (configuración), psutil (medir memoria), pytest.

## Comparación de desempeño

Se corre con `python -m src.processing.comparar_desempeno`. Cada prueba corre en un proceso aparte para medir su memoria.

Resultados con **datos sintéticos** (mismo formato que el SIMAT, 20 estaciones, 2 años; generados con `python -m src.utils.datos_sinteticos`). Hay que volver a correrlo con los datos reales y reemplazar esta tabla con `reports/tables/desempeno.csv`.

| Prueba | Volumen | Filas | Tiempo | Memoria | Resultado |
|---|---|---|---|---|---|
| Leer contaminantes en CSV.gz | 5.6 MB | 1,403,620 | 2.58 s | 240 MB | Correcto |
| Leer los mismos datos crudos en Parquet | 4.1 MB | 1,403,620 | 0.12 s | 178 MB | Correcto |
| Leer datos limpios de interim (Parquet) | 3.2 MB | 1,031,403 | 0.10 s | 87 MB | Correcto |
| Leer de Parquet solo SO₂ y 3 columnas | 3.2 MB | 343,733 | 0.17 s | 113 MB | Correcto |
| Convertir fechas: pandas adivina el formato | 2.8 MB | 700,850 | 38.67 s | 228 MB | Correcto |
| Convertir fechas: formato fijo del SIMAT | 2.8 MB | 700,850 | 2.60 s | 228 MB | Correcto |

**¿Qué operación se midió?** La lectura de los contaminantes horarios y la conversión de su columna de fechas, que son los pasos más pesados del pipeline.

**¿Qué cambió?** El formato del archivo (CSV comprimido contra Parquet), la cantidad de columnas y filas leídas (lectura por columnas con filtro) y la forma de convertir fechas (inferencia contra formato fijo).

**¿Por qué mejoró?** Parquet guarda los datos ya tipados y por columnas, así que no hay que descomprimir texto ni convertir cada valor: leer los mismos datos fue unas 20 veces más rápido y usó menos memoria. En las fechas, cuando pandas adivina el formato revisa cada valor por separado; con el formato fijo usa un camino vectorizado, unas 15 veces más rápido. Este segundo hallazgo hizo que la primera versión del pipeline tardara 2.5 minutos y la versión final 15 segundos con los mismos datos.

**¿Qué pasaría con un volumen mayor?** Los datos reales tienen más estaciones y 10 años o más. El tiempo de lectura de CSV crece en proporción, y leer todos los años juntos en pandas podría agotar la memoria de una laptop. Por eso el pipeline procesa un archivo anual a la vez y guarda Parquet particionado por red y año: cada año se puede leer (o volver a procesar) por separado. Si aun así no alcanzara, el siguiente paso sería consultar los Parquet con DuckDB o Polars sin cargarlos completos.

## Qué podría dejar de funcionar al crecer el volumen

- `cargar_diarios` junta los diarios de todos los años en memoria. Son pocos datos (estaciones × días), así que aguanta décadas.
- `ventanas` recorre estación por estación; con cientos de estaciones convendría vectorizarlo con `groupby().rolling()`.
- La descarga es secuencial; con muchos años se podría paralelizar.

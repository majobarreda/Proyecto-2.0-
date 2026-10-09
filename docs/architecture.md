# Arquitectura (primera propuesta)

```
SIMAT (aire.cdmx.gob.mx)
  REDDA (lluvia)   RAMA (contaminantes)   REDMET (meteorología)
        │                 │                       │
        └─────────────────┼───────────────────────┘
                          ↓
          src/ingestion/download_data.py
                          ↓
        data/raw/simat/   (CSV y CSV.gz sin modificar)
                          ↓
          src/processing/  (limpieza, formato ancho, horas → semanas)
                          ↓
        data/interim/     (Parquet particionado por año)
                          ↓
          src/processing/  (unión REDDA + estación RAMA/REDMET más cercana)
                          ↓
        data/processed/   (estación × semana, listo para análisis)
                          ↓
          src/validation/ → docs/validation.md
                          ↓
          src/analysis/ y notebooks/ → reports/
```

## Dónde se almacenan los datos

En la computadora de cada integrante, dentro de `data/`. Solo `data/sample/` se sube a GitHub.

## Cómo se obtienen

Descarga HTTP directa desde el sitio del SIMAT con `python -m src.ingestion.download_data`. No requiere credenciales. El script no repite descargas y registra errores en `data/raw/simat/descargas.log`.

## Transformaciones necesarias

- Quitar las líneas de notas al inicio de cada CSV.
- Convertir fechas a datetime (hora local UTC-6).
- Pasar de formato largo (una fila por parámetro) a ancho (una columna por parámetro).
- Agregar las horas de RAMA y REDMET a la semana de cada muestra REDDA.
- Emparejar cada estación REDDA con la estación RAMA/REDMET más cercana.
- Calcular variables derivadas: depósito ácido, rezagos de 1 a 7 días, viento del norte.

## Herramientas

Python, pandas, pyarrow (Parquet), matplotlib, pytest. Si el volumen crece, evaluar DuckDB o Polars.

## Qué podría dejar de funcionar al crecer el volumen

Cada año horario de RAMA son millones de filas. Leer 10 o más años en CSV con pandas de una sola vez puede agotar la memoria. Por eso se plantea convertir a Parquet particionado por año y procesar año por año.

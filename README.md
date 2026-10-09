# Lluvia ácida en la Ciudad de México: contaminación, temperatura y exposición de techos

Proyecto semestral del curso de Datos Masivos. Usa las mediciones públicas del Sistema de Monitoreo Atmosférico de la Ciudad de México (SIMAT) para relacionar la contaminación del aire y la temperatura con la acidez de la lluvia en cada zona de la ciudad, y estimar qué zonas exponen más sus techos e infraestructura a lluvia ácida.

> Este repositorio sustituye a [Proyecto-datos-masivos](https://github.com/majobarreda/Proyecto-datos-masivos). El historial de cómo llegamos a esta pregunta está en `docs/decisions.md`.

---

## Integrantes

| Nombre | Usuario de GitHub |
|---|---|
| María José Barreda | @majobarreda |
| Sofia Villegas | @sofia-villegas |
| Emiliano Martinez | <!-- COMPLETAR --> |

---

## Problema

La lluvia ácida (pH menor a 5.6) se forma cuando el dióxido de azufre (SO₂) y los óxidos de nitrógeno (NOx) del aire se convierten en ácido sulfúrico y nítrico dentro de las gotas. En el Valle de México se han medido lluvias con pH de hasta 4.16, y la acidez aumenta de norte a sur porque el viento arrastra las emisiones del corredor industrial de Tula. La lluvia ácida acelera el desgaste de impermeabilizantes, concreto, metales y selladores, justo cuando las lluvias en la ciudad son cada vez más intensas.

Los estudios publicados llegan hasta 2014 y no traducen la acidez en exposición de techos por zona. Este proyecto extiende el análisis con datos recientes y horarios.

## Pregunta principal

**¿Cómo se relacionan las concentraciones de SO₂ y NO₂ y la temperatura con la acidez de la lluvia en las distintas zonas de la Ciudad de México, y qué zonas tienen mayor exposición de techos e infraestructura a lluvia ácida?**

Preguntas secundarias en `docs/project_scope.md`.

## Objetivo

Construir un pipeline reproducible que descargue, limpie y una las tres redes del SIMAT (lluvia, contaminantes y meteorología) en un dataset semanal por estación, y usarlo para medir la relación entre contaminación, temperatura y acidez de la lluvia.

## Fuentes de datos

Todas son del SIMAT (SEDEMA, Gobierno de la CDMX), públicas, gratuitas y sin registro. Página de descarga: [aire.cdmx.gob.mx → Datos](http://www.aire.cdmx.gob.mx/default.php?opc='aKBh').

| Red | Qué mide | Frecuencia | Desde | Archivo |
|---|---|---|---|---|
| REDDA, depósito húmedo | Química de la lluvia: pH, conductividad, iones (sulfato, nitrato, amonio, etc.) y lluvia (mm) | Semanal, temporada de lluvias | 1997 | `redda/concentracion.csv`, `redda/deposito.csv` |
| RAMA | Contaminantes: SO₂, NO₂, NOx, CO, O₃, PM10, PM2.5 | Horaria | 1986 | `anuales_horarios_gz/contaminantes_AAAA.csv.gz` |
| REDMET | Temperatura, humedad, dirección y velocidad del viento | Horaria | 1986 | `anuales_horarios_gz/meteorologia_AAAA.csv.gz` |

Detalle de cada fuente en `docs/data_dictionary.md`.

## Estructura del repositorio

```
├── config/            # config.example.yaml (copiar a config.yaml)
├── data/
│   ├── raw/           # descargas sin modificar (no se suben)
│   ├── interim/       # datos parcialmente limpios (no se suben)
│   ├── processed/     # dataset analítico (no se sube)
│   └── sample/        # muestra pequeña para revisar y probar (sí se sube)
├── docs/              # alcance, diccionario, arquitectura, decisiones, validación, reporte
├── notebooks/         # 01_exploration.ipynb, ...
├── reports/           # figuras y tablas de resultados
├── src/
│   ├── ingestion/     # download_data.py
│   ├── processing/
│   ├── validation/
│   ├── analysis/
│   └── utils/         # lectura de CSV del SIMAT
└── tests/
```

## Instrucciones de ejecución

Desde la terminal de VS Code, en la carpeta del repositorio:

```bash
# 1. Crear y activar el entorno (una sola vez)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac / Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar la configuración (opcional: si no existe se usa config.example.yaml)
copy config\config.example.yaml config\config.yaml     # Windows
# cp config/config.example.yaml config/config.yaml     # Mac / Linux

# 4. Correr todo: descarga, procesamiento y validación
python main.py
```

O paso por paso:

```bash
python -m src.ingestion.download_data          # descarga a data/raw/simat/
python -m src.processing.build_dataset         # raw -> interim -> processed
python -m src.validation.validate_dataset      # escribe docs/validation.md
python -m src.processing.comparar_desempeno    # CSV vs Parquet, en reports/tables/desempeno.csv
pytest                                         # pruebas automáticas
```

Para probar sin internet: `python main.py --sintetico` genera datos **sintéticos** con el mismo formato en `data/synthetic/` y corre todo con ellos. Nunca se usan para el análisis.

### Dónde quedan los resultados

| Qué | Dónde |
|---|---|
| Descargas sin modificar | `data/raw/simat/` |
| Datos limpios en Parquet, por red y año | `data/interim/` |
| Dataset final (estación × semana) | `data/processed/dataset_semanal.parquet` |
| Muestra pequeña para revisar | `data/sample/dataset_semanal_muestra.csv` |
| Resumen de limpieza, emparejamiento, validación y desempeño | `reports/tables/` |
| Reporte de validación | `docs/validation.md` |

## Estado actual

- **Primer parcial:** estructura, pregunta, alcance, fuentes, script de descarga y notebook de exploración.
- **Segundo parcial:** pipeline completo de procesamiento (capas raw, interim y processed), validaciones, comparación de desempeño, pruebas automáticas y `main.py`. Probado de punta a punta con datos sintéticos; falta correrlo con los datos reales del SIMAT y actualizar `docs/validation.md` y la tabla de desempeño.
- **Examen final:** análisis de la pregunta en `src/analysis/` y `notebooks/03_analysis.ipynb`.

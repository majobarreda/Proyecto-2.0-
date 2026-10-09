# Decisiones técnicas

## Decisión: cambiar la pregunta a lluvia ácida y empezar un repositorio nuevo

**Razón:** el proyecto pasó por dos preguntas antes de esta (ver repositorio anterior [Proyecto-datos-masivos](https://github.com/majobarreda/Proyecto-datos-masivos)):

1. *Comparación de clima y calidad del aire en 20 ciudades de Latinoamérica* (Kaggle + Open-Meteo). El profesor la consideró demasiado obvia.
2. *Rezago entre clima, contaminación y mortalidad respiratoria/cardiovascular en la CDMX* (INEGI). Resultó inviable: los efectos en salud tardan años, se confunden con muchos otros factores y la mortalidad diaria por causa es una serie corta.

La lluvia ácida conserva el tema (contaminación y temperatura), su efecto se mide en la misma temporada y no en años, y no es una relación obvia.

**Alternativas consideradas:** demanda y escasez de impermeabilizantes contra lluvias (no hay datos públicos de ventas por ciudad); reportes de inundaciones del 911 contra lluvia (se aleja del tema de contaminación).

**Consecuencias:** los datos y el código de mortalidad no se traen a este repositorio. Se conservan del anterior: la estructura de carpetas, la lección de unir con llave compuesta (fecha + ubicación) y el cuidado con zonas horarias.

---

## Decisión: usar mediciones de estación del SIMAT en lugar de Open-Meteo

**Razón:** el repositorio anterior usaba Open-Meteo, que entrega valores modelados por coordenada. El SIMAT mide directamente en estaciones de la ciudad, y es la única fuente que tiene la química de la lluvia (REDDA). Así las tres redes vienen del mismo sistema y son comparables.

**Alternativas consideradas:** seguir con Open-Meteo para contaminantes y SIMAT solo para lluvia (mezcla datos modelados con medidos).

**Consecuencias:** los archivos horarios son mucho más grandes (millones de filas por año), lo que justifica Parquet y procesamiento por partes en el segundo parcial.

---

## Decisión: unidad de análisis estación × semana

**Razón:** REDDA toma una muestra semanal por estación; es la resolución más fina de la variable de respuesta (acidez).

**Alternativas consideradas:** mes × alcaldía (pierde detalle y reduce filas).

**Consecuencias:** los datos horarios de RAMA y REDMET se agregan a la semana de cada muestra.

---

## Decisión: usar Parquet particionado por red y año en la capa interim

**Razón:** con los datos de prueba, leer los mismos datos en Parquet fue unas 20 veces más rápido que en CSV.gz y usó menos memoria (ver `docs/architecture.md`). Parquet permite además leer solo algunas columnas y filtrar parámetros.

**Alternativas consideradas:** CSV (lento y sin tipos), un solo Parquet con todos los años (obliga a reescribir todo cuando cambia un año).

**Consecuencias:** se requiere `pyarrow`. Los datos crudos se conservan como CSV en `data/raw/` para trazabilidad.

---

## Decisión: procesar un archivo anual a la vez

**Razón:** cada año horario son millones de filas. Limpiar y agregar año por año mantiene la memoria acotada y permite no repetir años que no cambiaron (el pipeline revisa la fecha de modificación).

**Alternativas consideradas:** cargar todos los años juntos (más simple, pero no escala a 10 o más años).

**Consecuencias:** el agregado diario se guarda por año y luego se une. Un mismo día puede aparecer en dos archivos (la hora 24:00 del 31 de diciembre); se resuelve promediando por estación y fecha.

---

## Decisión: convertir fechas con formato fijo antes de dejar que pandas adivine

**Razón:** con 700 mil fechas, adivinar el formato tardó unos 39 s y el formato fijo `%d/%m/%Y %H:%M` unos 2.6 s.

**Alternativas consideradas:** `format="mixed"` siempre (robusto pero lento).

**Consecuencias:** `parsear_fecha` prueba una lista de formatos conocidos en una muestra y solo usa la inferencia si ninguno funciona.

---

## Decisión: asignar cada hora al día en que termina la medición

**Razón:** el SIMAT reporta horas de 1 a 24; la hora "24:00" es el promedio de 23:00 a 24:00 de ese mismo día. Se convierte a 00:00 del día siguiente para tener un datetime válido, y al agregar por día se resta una hora para que quede en el día correcto.

**Consecuencias:** cada día tiene sus 24 horas completas.

---

## Decisión: emparejar estaciones por clave, luego por cercanía, luego promedio de la ciudad

**Razón:** las estaciones REDDA no siempre miden contaminantes o meteorología. Usar la estación RAMA/REDMET más cercana (hasta 10 km, configurable) es la aproximación más directa a lo que respiró la nube que llovió ahí.

**Alternativas consideradas:** promedio de toda la ciudad para todas (pierde la diferencia norte-sur, que es parte de la pregunta); interpolación espacial (más compleja, se puede evaluar en el examen final).

**Consecuencias:** el método usado para cada estación queda en `reports/tables/emparejamiento_estaciones.csv`.

---

## Decisión: datos sintéticos para pruebas y desempeño

**Razón:** las pruebas automáticas no deben depender de internet ni del sitio del SIMAT. `src/utils/datos_sinteticos.py` genera archivos con el mismo formato (notas iniciales, horas 1-24, códigos -99, duplicados).

**Consecuencias:** los datos sintéticos viven en `data/synthetic/` (no se suben a GitHub) y usan su propia configuración, `config/config.sintetico.yaml`, para no mezclarse nunca con los reales. No se usan en el análisis.

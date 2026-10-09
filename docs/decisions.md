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

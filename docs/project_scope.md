# Alcance del proyecto

## Contexto del problema

La Ciudad de México tiene episodios de mala calidad del aire y lluvias cada vez más intensas. Cuando llueve, los contaminantes del aire no desaparecen: el SO₂ y los NOx se disuelven en las gotas como ácido sulfúrico y nítrico, y caen sobre techos, fachadas y calles. A esto se le llama lluvia ácida (pH menor a 5.6).

Un estudio con datos del SIMAT y la UNAM (16 estaciones, 2003-2014, 3,867 muestras semanales) encontró:

- pH anual mínimo de 4.16 (estación LOM, 2006);
- en la estación MON el pH bajó de 7.48 (2003) a 5.03 (2014);
- la acidez aumenta de norte a sur, porque los vientos dominantes arrastran las emisiones del corredor industrial Tula-Vito-Apasco;
- la relación sulfato/nitrato fue cercana a 1.5: el SO₂ es el principal acidificante.

Fuente: [García et al., revista Atmósfera](https://www.redalyc.org/journal/565/56559474007/movil).

Ese estudio termina en 2014 y no habla del efecto sobre materiales. La lluvia ácida acelera el desgaste de impermeabilizantes, concreto, metales y selladores, así que saber dónde cae más ácido es útil para vecinos, alcaldías y quienes fabrican o aplican impermeabilizantes.

## Pregunta principal

¿Cómo se relacionan las concentraciones de SO₂ y NO₂ y la temperatura con la acidez de la lluvia en las distintas zonas de la Ciudad de México, y qué zonas tienen mayor exposición de techos e infraestructura a lluvia ácida?

## Preguntas secundarias

1. ¿Qué estaciones tienen la lluvia con pH más bajo y cómo ha cambiado por año?
2. ¿Las semanas con más SO₂ y NO₂ tienen lluvia más ácida? ¿Con cuántos días de rezago?
3. ¿La temperatura y la dirección del viento (por ejemplo, viento del norte) cambian la acidez?
4. ¿Cuánto ácido (sulfato + nitrato) se deposita por zona y temporada? Este es el indicador de exposición de techos.
5. (Opcional) ¿Coincide el pico de interés en "impermeabilizante" (Google Trends, CDMX) con la temporada de lluvia más ácida?

## Unidad de análisis

Estación de depósito húmedo (REDDA) × semana de lluvias.

## ¿Qué representa una fila?

En el dataset analítico final, **una fila es una muestra semanal de lluvia en una estación REDDA**, con:

- de REDDA: pH, conductividad, sulfato, nitrato, amonio, lluvia (mm) y depósito ácido;
- de RAMA (estación más cercana): promedio y máximo de SO₂ y NO₂ en esa semana y la anterior;
- de REDMET: temperatura media, humedad y porcentaje de horas con viento del norte;
- del catálogo de estaciones: alcaldía y coordenadas.

En los datos crudos horarios (RAMA y REDMET), una fila es **un parámetro medido en una estación en una hora**.

## Alcance

- Territorio: estaciones del SIMAT en la Ciudad de México y su zona metropolitana.
- Periodo: 2015 a 2024 para el análisis principal (empezamos con 2023-2024 para probar el pipeline).
- Variables: química de la lluvia, SO₂, NO₂, NOx, temperatura, humedad y viento.

## Limitaciones

- REDDA solo muestrea en temporada de lluvias y tiene semanas sin muestra.
- Las estaciones REDDA y RAMA no están en el mismo punto; se emparejan por cercanía.
- Se mide **exposición** a lluvia ácida, no el daño de un techo concreto. Los resultados son asociaciones, no causalidad.
- Parte de los contaminantes viene de fuera de la ciudad (Tula, Popocatépetl), lo que las estaciones urbanas no capturan del todo.

## Posibles usuarios del resultado

| Usuario | Para qué le sirve |
|---|---|
| Vecinos y administradores de edificios | Saber si su zona necesita impermeabilizantes más resistentes o mantenimiento más frecuente |
| Alcaldías y Gobierno de la CDMX | Priorizar mantenimiento de edificios públicos e infraestructura |
| SEDEMA | Ver qué contaminantes vigilar para reducir la lluvia ácida |
| Fabricantes y aplicadores de impermeabilizantes | Planear producto y temporada por zona |

## Valor esperado

Un mapa y una serie actualizada de la acidez de la lluvia por zona, ligada a la contaminación y la temperatura, construida con un pipeline reproducible que cualquiera puede volver a ejecutar cuando el SIMAT publique datos nuevos.

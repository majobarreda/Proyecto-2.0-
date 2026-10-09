# Validación

Este archivo lo genera automáticamente `python -m src.validation.validate_dataset` (o `python main.py`) cada vez que se corre con los datos reales. Hasta que se corra, aquí no hay resultados.

Revisiones incluidas:

| Categoría | Qué revisa | Nivel |
|---|---|---|
| Columnas | Que existan estación, fecha, pH, estaciones emparejadas y columnas de contaminantes | error |
| Tipos | Fecha como datetime y mediciones numéricas | error |
| Faltantes | pH sin vacíos; columnas con más de 30% vacío | error / aviso |
| Duplicados | Una sola fila por estación y semana | error |
| Rangos | pH entre 3 y 9, SO₂ entre 0 y 500 ppb, temperatura entre -10 y 40 °C, etc. (`config.rangos`) | aviso |
| Consistencia temporal | Muestras dentro del periodo, sin fechas futuras, en temporada de lluvias | error / aviso |
| Consistencia entre tablas | Mismas muestras en interim y processed; toda estación REDDA con pareja; muestras con datos de contaminación | error / aviso |
| Volumen esperado | Filas horarias limpias ≥ 50% de estaciones × parámetros × 8,760 horas | aviso |

Con datos sintéticos (`python main.py --sintetico`) todas las revisiones pasan; ese reporte se escribe en `data/synthetic/validation.md` para no mezclarlo con este.

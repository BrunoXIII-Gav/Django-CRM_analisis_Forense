# Informe forense [ID del caso]

## Identificación y autorización

Solicitante, autorización, alcance, activos ficticios, intervalo UTC, operador, custodio, analista y revisor. Declarar funciones compartidas. Registrar decisiones de contención y su impacto sobre las fuentes.

## Fuentes y adquisición

Inventario por ID: descripción, procedencia, ruta, formato, tamaño, SHA-256, adquirente, fecha UTC, método y herramientas/versiones. Incluir inicio, fin, errores, códigos de retorno, condiciones del dump y offset medido o desconocido. Justificar faltantes y binlog condicional.

## Examen de copias

Verificaciones antes de examinar; archivos de trabajo utilizados; restauración aislada; algoritmo de normalización; tiempos originales y offsets; duplicados, faltantes y errores. Identificar y calcular hashes de los derivados.

## Cronología y hallazgos

| UTC | Cuenta | Canal | Acción y registro | Before/after | Evidencia, archivo y ubicación | Respaldo |
| --- | --- | --- | --- | --- | --- | --- |

Distinguir hechos, inferencias y preguntas abiertas. Usar: confirmado con contraste, sustentado en una fuente, indeterminado o contradicho. Describir qué atributo confirma cada fuente. Una coincidencia temporal no demuestra causalidad.

## Hipótesis y limitaciones

Contrastar cambio legítimo, error operativo, sesión compartida, automatización API y desfase horario. La calificación de indebida requiere las reglas del escenario. Cuenta e IP no identifican por sí solas a una persona; hash no demuestra veracidad previa. Declarar SQL directo y demás exclusiones.

## Evaluación A/B

Documentar equivalencia inicial, guion independiente, reglas de no-op e intentos rechazados, desviaciones y matriz por operación. Para cada métrica: numerador, denominador, porcentaje o no aplicable. Registrar tiempo de adquisición y tiempo de análisis medidos, sin extrapolar ahorros.

## Custodia, revisión y cierre

Adjuntar manifiestos, transferencias, constancias de entrega y recepción, bitácoras, scripts y hashes. Registrar observaciones del segundo integrante, resolución de pendientes, última verificación, ubicación de originales, custodio y decisión de retención. Mantener G5 pendiente hasta la revisión independiente.

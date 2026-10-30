# Registro de implementación y validación

Fecha: 30 de octubre de 2026 (America/Lima). Rama de desarrollo: `creacion_auditoria`; rama de entrega: `implementacion_forense`. HEAD de partida: `151329f5708bc3c9c26405fc04c6cc1e6b2b7884`. La ejecución documentada se realizó antes del commit de entrega. El SHA de partida no representa por sí solo el árbol modificado: cada adquisición registra los hashes del árbol local y de las fuentes Python de la aplicación en ejecución.

## Entorno comprobado

Python 3.12.10 en Windows y Python 3.12 en Linux/Docker; Django 5.2.18; DRF 3.18.3; mysqlclient 2.3.0. Docker cliente/servidor 29.7.2; Compose 5.5.1. Las versiones transitivas se fijaron en `requirements.lock`. El perfil del laboratorio utiliza MySQL/InnoDB, UTC, `DEBUG=False` y redes/volúmenes separados.

La aplicación original extraída para A coincide byte a byte con `website/` y `dcrm/` del commit `5f80cd103e32825f4504fa5e96103d56cfbd968e`. Los overlays de construcción y el perfil MySQL se declaran en la guía; no se añadió AuditEvent a A.

Imágenes utilizadas en la ejecución comparativa:

| Imagen | ID local |
| --- | --- |
| A, `tasi-forensic-baseline:local` | `sha256:61ef70031541e5b535f0d7198520612e45aa824dd2c58ec873370ac046e81a48` |
| B, `tasi-forensic-lab:local` | `sha256:6388d5e8d7b99d49cf1677ba74dbb19a3ac5b27e8fdf4d74cd02ebdeced87f09` |
| MySQL 8.0 | `sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b` |

## Pruebas y no conformidades resueltas

La línea base de Windows ejecutó 42 pruebas Django: 41 pasaron y una falló por timestamps de creación iguales. Se añadió desempate por clave primaria al orden de Record. La línea base Linux ejecutó 51 pruebas: las 42 de Django pasaron y cinco de adquisición fallaron por finales CRLF en Bash. Los entrypoints actuales y `.gitattributes` usan LF.

La suite final ejecutó **71 pruebas en Linux/MySQL, todas satisfactorias**, incluyendo bloqueo concurrente con dos conexiones, rollback del servicio, fallos en cada canal, borrado administrativo masivo real y atómico, contexto HTTP, exportación, migración de dos eventos históricos con UUID únicos, adquisición parcial/truncada, detección de un byte alterado, transferencias y métricas. En Windows/SQLite se ejecutaron 71 pruebas con dos exclusiones justificadas: bloqueo no soportado por SQLite y entrypoint Bash. Los logs de ejecución están en `.lab/mysql-tests-final.log` y `.lab/sqlite-tests-final.log`.

`manage.py check`, `makemigrations --check --dry-run`, compilación Python, `git diff --check` y validación Compose terminaron correctamente. CI ahora incluye pushes a `creacion_auditoria`, fija explícitamente el backend SQLite/MySQL y ejecuta las pruebas; no se afirma una ejecución remota de GitHub Actions.

Con la cuenta real `crm_runtime`, SELECT de auditoría fue permitido y UPDATE/DELETE con condición que no afecta filas devolvieron el error MySQL 1142. El servicio escribió correctamente con esa misma cuenta durante el escenario. Se preservó `0003_auditevent.py` y se comprobó la migración de eventos preexistentes.

La primera adquisición A (`CASE-A-001`) no publicó manifiesto: MySQL rechazó el archivo de credenciales montado desde Windows por permisos demasiado amplios. El caso parcial permanece conservado. La herramienta ahora crea un archivo temporal Linux con modo 0600 y elimina sólo ese temporal al terminar; `CASE-A-002` completó la adquisición con la cuenta lectora. La disponibilidad inicial de MySQL se corrigió para comprobar TCP y evitar aceptar el servidor temporal de inicialización.

## Ejecución comparativa observada

Se verificaron tres clientes iniciales idénticos (IDs, datos y fechas fijas) y dos cuentas funcionalmente equivalentes. A no contiene AuditEvent; B sí. La tabla de verdad independiente se guarda en `.lab/truth-A.json` y `.lab/truth-B.json`, separada de las evidencias.

| Entorno | Intervalo real UTC del guion | Caso completo |
| --- | --- | --- |
| A | 2026-10-30 19:31:53.282113 a 19:31:53.832592 | `../forensic_cases/CASE-A-002` |
| B | 2026-10-30 19:31:54.885556 a 19:31:55.544142 | `../forensic_cases/CASE-B-001` |

Cada ejecución realizó diez cambios confirmados, un no-op y un intento anónimo rechazado. B conservó diez eventos de éxito y un no-op; el intento rechazado no generó modificación. Las siete observaciones nativas por entorno son parciales y no se cuentan como operaciones adicionales.

| Métrica | A | B |
| --- | --- | --- |
| Operaciones con cuenta, tiempo, canal, ID y snapshots aplicables completos | 0/10 (0 %) | 10/10 (100 %) |
| Cobertura de auditoría completa respecto de los cambios esperados | 0/10 (0 %) | 10/10 (100 %) |
| Integridad de originales y copias examinados | 12/12 (100 %) | 12/12 (100 %) |
| Transferencias físicas realizadas | Ninguna; métrica no aplicable | Ninguna; métrica no aplicable |
| Adquisición de fuentes, antes de copias/manifiesto | 4,500456 s | 4,523424 s |

Estos valores corresponden a una ejecución por entorno; no representan una mejora generalizada ni una comparación de rendimiento. A conserva observaciones de actividad, aunque no resuelve la reconstrucción completa exigida. Los tiempos de ejecución de las herramientas se registran en los expedientes; no se midió el tiempo humano de investigación.

Cada caso completo contiene seis fuentes originales y sus seis copias, inventario, manifiesto, custodia, normalización, cambios por registro, línea de tiempo y reporte. Ambos dumps se restauraron en contenedores temporales MySQL sin red: un cliente final en A/B y once eventos en B. Los resultados constan en `analisis/restore_validation.json`; los contenedores de restauración se eliminaron, sin tocar los volúmenes A/B.

Informes actuales: `reporte/report-v3.md`, con `metrics-v3.json`, hashes y procedencia. Las revisiones previas permanecen conservadas. El binlog no estuvo disponible en estas adquisiciones y no sustenta resultados. El offset respecto de una referencia externa de reloj no fue medido y permanece declarado como desconocido. Las correlaciones dentro del laboratorio no certifican precisión temporal externa.

Hashes SHA-256 de los manifiestos completos, como referencia adicional (requieren respaldo separado):

- A: `52e72ed2d6ba69b7c085bdebf04b23eed582f308715558f2d46d6bb28db44a3b`.
- B: `bd80647c12ff96b40e268c8b539af4da300c51279f8bb7edb241759a2252955e`.

## Estado de las puertas de control

| Puerta | Estado y alcance comprobado |
| --- | --- |
| G1 | Configuraciones aisladas, fuente original, dependencias y equivalencia inicial verificadas. Queda pendiente medir desfase frente a una referencia temporal externa antes de una nueva evaluación formal. |
| G2 | Cobertura web/API/admin y borrado masivo verificados por pruebas y escenario. |
| G3 | Snapshots, no-op, concurrencia real y rollback verificados en MySQL; historial anterior preservado. |
| G4 | Adquisición, custodia generada, integridad y restauración verificadas; sin transferencias físicas. Respaldo externo y constancias personales pertenecen al custodio. |
| G5 | Derivados, línea de tiempo y reportes trazables generados; **pendiente revisión independiente por otro integrante y cierre formal**. |

El operador automatizado asumió preparación, adquisición y análisis; esta coincidencia se declara, sin simular una segunda persona ni constancias firmadas. La calificación de indebida depende de las reglas del guion. La cuenta no identifica a una persona y SHA-256 no demuestra veracidad previa. Los resultados para el capítulo V quedan disponibles en los expedientes; no se modificó el documento académico.

SHA-256 del Markdown académico al inicio y al cierre: `60250ce4a98d5511be1d8c5cade19d72aa0694b3edd01e7bd63482c2208aa10d`. En la carpeta consultada sólo se encontró esa versión Markdown; no se encontró un `.docx` independiente.

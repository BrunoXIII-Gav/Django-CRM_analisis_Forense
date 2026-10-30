# Plan de implementación forense para Django-CRM

**Proyecto:** Análisis forense digital para la reconstrucción de incidentes simulados en Django-CRM mediante preparación y preservación de evidencias.  
**Fecha de elaboración:** 30 de octubre de 2026.  
**Estado:** Fork y rama verificados; adaptación de la implementación existente pendiente de ejecución y validación.  
**Documento base:** `Capitulo_4_Forense_Django_CRM.docx.md`.  
**Insumo complementario:** Plan proporcionado en `Texto pegado.txt`.

Este plan organiza la implementación propuesta para el fork de Django-CRM y la relaciona con los objetivos, el alcance y los criterios de aceptación del documento base. Describe el trabajo por realizar; las actividades redactadas en pasado en el capítulo IV no se consideran, por ese solo hecho, implementaciones o pruebas verificadas. Los resultados experimentales deberán documentarse en el capítulo V.

## 1. Objetivo y alcance

Implementar una capa de auditoría común a la interfaz web, la API y el panel administrativo de Django-CRM. Después de ejecutar incidentes simulados, adquirir y preservar las evidencias, examinar copias verificadas, reconstruir las operaciones y generar un informe forense trazable.

El desarrollo conservará la arquitectura original del CRM y se dividirá en dos componentes:

1. **Preparación forense del CRM:** módulo `website/forensics/`, responsable de registrar las operaciones y su contexto, conservando inicialmente `AuditEvent` en la aplicación `website` existente.
2. **Laboratorio de investigación forense:** directorio `forensic_lab/`, responsable de los entornos comparativos, las simulaciones y el procesamiento de evidencias.

Las plantillas de inventario, cadena de custodia e informe se mantendrán en `forensic_docs/`. Los archivos de evidencia de cada caso se almacenarán fuera del repositorio.

### 1.1 Correspondencia con el documento base

| Objetivo | Trabajo previsto | Referencia del documento base |
| --- | --- | --- |
| OE1. Configurar el entorno y el escenario | Preparar dos despliegues aislados, datos ficticios equivalentes y un guion de operaciones. | 1.3.2; 4.1.1–4.1.2 |
| OE2. Implementar preparación forense | Ampliar `AuditEvent` y reorganizar el contexto y los snapshots existentes; incorporar el servicio transaccional común a web, API y admin. | 4.1.3–4.1.4 |
| OE3. Adquirir y preservar evidencias | Implementar adquisición, SHA-256, inventario, custodia y copias de trabajo. | 4.1.5–4.1.7 |
| OE4. Reconstruir los hechos | Examinar fuentes, correlacionar eventos y elaborar la línea de tiempo y el informe. | 4.1.6 |
| OE5. Comparar la reconstrucción | Aplicar el mismo guion a los entornos A y B y calcular las métricas definidas. | 4.1.8; 4.4 |

### 1.2 Límites de la implementación

La cobertura comprenderá CREATE, UPDATE y DELETE de `Record` desde los flujos instrumentados de web, API y administración, incluido el borrado administrativo masivo. La simulación utilizará cuentas y clientes ficticios en un laboratorio local.

Se conservarán las exclusiones del documento base: SQL directo y actualizaciones ajenas al servicio auditado, adquisición de RAM, LiME, imágenes bit a bit, análisis de redo logs, almacenamiento WORM y registros criptográficamente resistentes a la manipulación. El binlog de MySQL será una fuente secundaria condicional, disponible únicamente si se habilitó y conservó antes del incidente.

## 2. Condiciones previas y decisiones de partida

Se verificó el fork [BrunoXIII-Gav/Django-CRM_analisis_Forense](https://github.com/BrunoXIII-Gav/Django-CRM_analisis_Forense). La copia local se encuentra en `C:/Users/Kato/Documents/Cursos/TASI/Proyecto/Django-CRM_analisis_Forense`.

| Referencia | Resultado de la revisión inicial |
| --- | --- |
| Rama de trabajo indicada por el usuario | `creacion_auditoria` |
| Commit de la rama revisada | `151329f5708bc3c9c26405fc04c6cc1e6b2b7884` |
| Rama original | `main` |
| Commit original y ancestro común | `5f80cd103e32825f4504fa5e96103d56cfbd968e` |
| Diferencia respecto de `main` | Un commit adicional; 13 archivos afectados. |
| Estado local tras la revisión del código | Sin modificaciones al código. |

La rama ya contiene `AuditEvent` en `website/models.py`, su migración `0003_auditevent.py`, middleware y señales en `website/forensic.py`, consulta administrativa y scripts de adquisición y verificación. La referencia `5f80cd1` del documento base coincide con el commit completo de `main`.

El desarrollo continuará en `creacion_auditoria`, según la indicación del usuario, conservando `main` como referencia original. Antes de las simulaciones se deberá:

- Preparar el entorno de dependencias y ejecutar las pruebas funcionales existentes. En la revisión inicial solo se comprobaron las sintaxis Python y Bash.
- Configurar explícitamente los settings del laboratorio: `dcrm.settings` carga `dev.py`, que fuerza SQLite y `DEBUG=True`; las variables `DB_*` por sí solas no activan MySQL.
- Definir los proyectos, redes, puertos y volúmenes independientes de los entornos A y B.
- Preparar secretos ficticios propios del laboratorio, excluirlos de Git y separar las cuentas MySQL de migración y ejecución.
- Establecer UTC como referencia temporal y registrar versiones de herramientas, imágenes, anfitrión y posibles desfases horarios.

La auditoría actual utiliza señales, no el servicio común propuesto. Su reorganización deberá retirar o redirigir la escritura por señales al activar el servicio para evitar eventos duplicados. El diagnóstico y las brechas se detallan en `Revision_Inicial_Fork_Django_CRM.md`.

Los scripts `.sh` del plan se ejecutarán en un entorno Linux compatible, por ejemplo WSL en un anfitrión Windows. Ese entorno deberá quedar documentado para reproducir el procedimiento.

## 3. Arquitectura propuesta

Los tres canales invocarán el mismo servicio de auditoría. El servicio conservará el cambio de negocio y su evento dentro de una única transacción MySQL/InnoDB.

```text
Interfaz web ─┐
API ─────────┼──> forensics/services.py ──> Record + AuditEvent
Admin ───────┘          │                  misma transacción
                        │
                        └── Contexto HTTP + snapshots before/after

AuditEvent + logs + exportación MySQL + metadatos
                        │
                        v
Adquisición y preservación -> Copias verificadas -> Examen
                        -> Línea de tiempo -> Informe y comparación A/B
```

### 3.1 Estructura de archivos

El árbol siguiente muestra la estructura objetivo ajustada al fork. `website/forensic.py`, `website/models.py`, la migración `0003_auditevent.py` y las pruebas actuales ya existen. Los directorios `website/forensics/`, `forensic_lab/` y `forensic_docs/` están pendientes de creación.

```text
Django-CRM_analisis_Forense/
├── dcrm/
│   └── settings/
│       └── base.py                       # Modificar configuración
├── website/
│   ├── models.py                         # Existentes: Record y AuditEvent
│   ├── apps.py                           # Actualmente conecta las señales
│   ├── forensic.py                       # Contexto y señales actuales; transición
│   ├── views.py                          # Integrar CRUD web
│   ├── api_views.py                      # Integrar CRUD API
│   ├── admin.py                          # Integrar CRUD y borrado masivo
│   ├── migrations/
│   │   ├── 0003_auditevent.py             # Existente; conservar historial
│   │   └── ...                           # Nuevas migraciones si cambia el modelo
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── export_audit.py            # Comando de la aplicación website
│   ├── tests.py                          # Pruebas actuales del CRM
│   ├── tests_forensic.py                  # Pruebas forenses existentes
│   ├── tests_evidence_scripts.py          # Pruebas de scripts con Docker simulado
│   └── forensics/                        # Nuevo paquete dentro de website
│       ├── __init__.py
│       ├── middleware.py                 # Contexto de solicitud
│       ├── context.py                    # Cuenta, IP, sesión y canal
│       ├── snapshots.py                  # Estados permitidos before/after
│       ├── services.py                   # Operaciones transaccionales
│       ├── export.py                     # Exportación controlada
│       └── tests/
│           ├── __init__.py
│           ├── test_web.py
│           ├── test_api.py
│           ├── test_admin.py
│           ├── test_transactions.py
│           └── test_middleware.py
├── forensic_lab/
│   ├── environments/
│   │   ├── compose.baseline.yml
│   │   └── compose.instrumented.yml
│   ├── fixtures/
│   │   └── seed_demo.py
│   ├── scenarios/
│   │   └── scenario_01.py
│   └── tools/
│       ├── acquire_case.sh
│       ├── verify_evidence.sh
│       ├── examine_evidence.py
│       ├── build_timeline.py
│       └── generate_report.py
├── forensic_docs/
│   ├── chain_of_custody_template.csv
│   ├── evidence_inventory_template.csv
│   └── forensic_report_template.md
├── docs/
│   └── forense.md                        # Documentación existente a actualizar
├── adquirir_evidencias.sh                # Existente; adaptar o delegar
├── verificar_integridad.sh               # Existente; adaptar o delegar
├── docker-compose.yml                    # Ajustar despliegue
├── .gitignore                            # Excluir secretos y evidencias
├── requirements.txt                      # Ajustar solo si es necesario
└── manage.py
```

### 3.2 Integración con la aplicación existente

Para la primera implementación se conservarán `website.AuditEvent`, la tabla `website_auditevent` y su historial de migraciones. `website/forensics/` será un paquete Python de la aplicación `website`, que ya está instalada. No se registrará una segunda aplicación ni se creará otro modelo `AuditEvent`.

Este ajuste respecto de la propuesta inicial permite separar contexto, snapshots, servicio y exportación sin trasladar de aplicación un modelo ya migrado. Las ampliaciones del evento se harán mediante nuevas migraciones de `website`, conservando los datos existentes. El comando `export_audit` se ubicará en `website/management/commands/` para que Django lo descubra como parte de esa aplicación.

La conexión de señales en `website/apps.py` y el middleware configurado en `base.py` se actualizarán durante la transición. Las pruebas deberán demostrar que cada operación genera un único evento y que se mantiene el rollback. Una separación futura en otra aplicación exigiría un plan explícito para preservar tabla, migraciones y permisos.

## 4. Diseño del módulo forense

### 4.1 Modelo `AuditEvent`

| Campo o grupo | Regla prevista |
| --- | --- |
| `event_id`, `case_tag` | UUID único del evento y etiqueta de ejecución. La etiqueta no sustituye el ID de evidencia. |
| `occurred_at_utc` | Fecha y hora generadas por el servidor, con zona horaria y referencia UTC. |
| `actor_id`, `actor_username` | Cuenta autenticada que ejecutó la operación. |
| `session_correlation_id` | UUID controlado por el servidor para agrupar actividad; sin almacenar la cookie o el token de autenticación. |
| `request_id`, `channel` | UUID por solicitud y canal `web`, `api` o `admin`. |
| `src_ip`, `user_agent` | IP obtenida de `REMOTE_ADDR` y agente de usuario acotado. Los encabezados reenviados solo se admitirán bajo un proxy expresamente confiable. |
| `action`, `record_id`, `outcome` | Operación, identificador del cliente y resultado, diferenciando cambios confirmados de intentos fallidos. |
| `before_json`, `after_json` | Valores permitidos del registro antes y después de la operación. |
| `changed_fields`, `committed` | Campos efectivamente cambiados y estado de confirmación, sin eventos de éxito para transacciones revertidas. |

La lista de campos de los snapshots se contrastará con `Record`. Según el documento base, comprenderá nombre, apellido, correo, teléfono, dirección, ciudad, estado, código postal y marcas de creación y actualización disponibles. Se excluirán contraseñas, cookies, tokens, encabezados `Authorization`, secretos y cargas ajenas al caso.

Para CREATE, `before_json` será nulo; para DELETE, `after_json` será nulo. En UPDATE se conservarán ambos estados. Antes de la evaluación se definirá cómo clasificar las solicitudes sin cambios efectivos (`no-op`) y su tratamiento en las métricas.

### 4.2 Contexto y servicio transaccional

`middleware.py` y `context.py` prepararán el contexto por solicitud después de que estén disponibles la sesión y la autenticación. Se comprobará que el contexto no se mezcle entre solicitudes y se documentará la correlación utilizada por la API según su mecanismo de autenticación.

`services.py` centralizará las operaciones con datos previamente validados. En una actualización o eliminación deberá obtener el registro con bloqueo cuando corresponda, capturar el estado anterior, realizar la escritura y crear el evento dentro de `transaction.atomic()`.

La secuencia conceptual para UPDATE será:

```text
Abrir transacción
  Obtener y bloquear Record
  Capturar before
  Aplicar datos validados y guardar Record
  Capturar after y campos modificados
  Crear AuditEvent con el contexto de la solicitud
Confirmar ambas escrituras
```

Si falla la escritura de auditoría, se revertirá el cambio del cliente. Los intentos rechazados se tratarán por separado y nunca como modificaciones confirmadas. En DELETE se conservarán el ID y el snapshot antes de retirar el registro.

### 4.3 Integración con los canales originales

| Canal | Punto de integración | Cambio previsto |
| --- | --- | --- |
| Web | `add_record`, `update_record`, `delete_record` en `views.py` | Sustituir escrituras directas por llamadas al servicio después de validar formularios y permisos. |
| API | `perform_create`, `perform_update`, `perform_destroy` en `RecordViewSet` | Usar el servicio común y conservar la validación del serializador. |
| Admin | `save_model`, `delete_model`, `delete_queryset` en `RecordAdmin` | Cubrir altas, modificaciones, bajas y eliminación masiva con el mismo servicio. |

La integración deberá evitar escrituras duplicadas entre los métodos originales y el servicio. El borrado masivo se implementará por una vía auditada; si no puede garantizarse su cobertura, se deshabilitará hasta resolverla. Las señales de Django podrán ser complementarias, pero no sustituirán la instrumentación de los flujos definidos.

### 4.4 Protección y conservación preventiva

- Usar una cuenta MySQL de ejecución sin permisos UPDATE ni DELETE sobre `AuditEvent`, separada de la cuenta de migración.
- Mantener el registro operativo de Django y Docker como fuente complementaria, con timestamps y correlación de solicitudes cuando estén disponibles.
- Documentar rotación y retención antes de la simulación y adquirir los logs antes de que se pierdan.
- Restringir la exposición de MySQL a la red necesaria para el laboratorio y emplear `DEBUG=False` durante la evaluación.
- Mantener originales, dumps y credenciales fuera de Git, con acceso restringido y respaldo de manifiestos y custodia.

Estos controles no implican inmutabilidad frente a un administrador de MySQL o del anfitrión. SHA-256 permitirá verificar cambios respecto del archivo adquirido, sin demostrar la veracidad previa de su contenido.

## 5. Etapas de implementación

### Etapa 1. Línea base y módulo forense

1. Partir del commit verificado de `creacion_auditoria` y conservar el commit de `main` como referencia de A.
2. Preparar el despliegue original A, registrar su configuración y generar la carga ficticia inicial.
3. Definir el guion y las reglas que distinguen operaciones legítimas de indebidas.
4. Crear el paquete `website/forensics/` y reorganizar la lógica existente, conservando `website.AuditEvent` y evitando duplicar capturas durante la transición.
5. Ampliar el modelo existente mediante nuevas migraciones, sin reescribir `0003_auditevent.py` ni crear una segunda tabla de auditoría.
6. Preparar las cuentas MySQL y comprobar los permisos diferenciados.

**Entregables:** versión de partida documentada, línea base reproducible, modelo de evento ampliado y migraciones. A utilizará el commit de `main`; B partirá de `creacion_auditoria`. Se documentará que las diferencias de esquema corresponden a la instrumentación y se comprobará la equivalencia de los clientes y las cuentas iniciales.

### Etapa 2. Instrumentación CRUD

1. Implementar contexto HTTP, snapshots y servicio transaccional.
2. Integrar web, API y administración, incluido el borrado masivo.
3. Incorporar la exportación controlada de auditoría.
4. Ejecutar pruebas de cobertura, permisos, rollback, concurrencia, IP, correlación y cambios sin diferencias.
5. Corregir las rutas que permitan cambios confirmados sin evento o generen eventos duplicados.

**Entregables:** módulo integrado, eventos completos y resultados de las pruebas de los tres canales.

### Etapa 3. Laboratorios A/B y adquisición

1. Completar `compose.baseline.yml` y `compose.instrumented.yml` con redes, proyectos y volúmenes independientes.
2. Restaurar estados iniciales equivalentes mediante `seed_demo.py` y los snapshots definidos.
3. Ejecutar `scenario_01.py` con operaciones normales, cambios indebidos, modificaciones sucesivas y eliminación de otro registro.
4. Mantener una tabla de verdad del guion separada de las evidencias y utilizarla para la evaluación posterior al examen.
5. Detener nuevas operaciones del guion al abrir el caso y adquirir las fuentes antes de eliminar o reiniciar servicios.
6. Calcular hashes, registrar custodia y generar copias verificadas.

**Entregables:** ejecuciones identificadas por entorno y repetición, actas de adquisición y paquetes de evidencia con manifiestos. No se ejecutará `docker compose down -v` ni se eliminarán volúmenes con evidencia pendiente de adquisición.

### Etapa 4. Examen, reconstrucción e informe

1. Verificar las copias y restaurar el dump en una base temporal aislada cuando sea necesario.
2. Extraer y normalizar los eventos, conservando el vínculo con su fuente.
3. Construir la línea de tiempo y contrastar hallazgos con fuentes secundarias disponibles.
4. Aplicar las mismas preguntas forenses a los entornos A y B.
5. Comparar la reconstrucción con el guion independiente y calcular las métricas.
6. Generar el informe, someterlo a revisión por otro integrante y cerrar el expediente con una verificación final.

**Entregables:** datos normalizados, línea de tiempo, matriz comparativa e informe con evidencias, inferencias y limitaciones. Los resultados observados se incorporarán al capítulo V.

## 6. Procedimiento forense y herramientas

La preparación del caso y la cadena de custodia acompañarán las cuatro fases de NIST SP 800-86 descritas en el documento base.

| Fase | Herramienta prevista | Actividades y salida |
| --- | --- | --- |
| Recolección | `acquire_case.sh` y `export_audit.py` | Adquirir logs, auditoría, dump MySQL y metadatos; registrar método, tiempos, errores, códigos de retorno y SHA-256. |
| Examen | `verify_evidence.sh` y `examine_evidence.py` | Verificar copias, extraer campos y generar eventos normalizados, cambios por registro e inconsistencias. |
| Análisis | `build_timeline.py` | Correlacionar cuenta, sesión, solicitud, registro y tiempo; contrastar hipótesis y construir la cronología con referencias a evidencias. |
| Reporte | `generate_report.py` | Elaborar el informe con metodología, hallazgos, respaldo, hipótesis alternativas, limitaciones y anexos. |

Antes de adquirir se abrirá el caso con identificador, autorización académica, alcance, responsables, intervalo temporal y preguntas de investigación. Toda intervención sobre el laboratorio quedará registrada con su justificación y efecto sobre las fuentes.

### 6.1 Fuentes de evidencia

| ID | Fuente | Tratamiento previsto |
| --- | --- | --- |
| F1 | `AuditEvent` | Fuente principal del entorno B; exportación controlada y conservación en el dump. Su ausencia en A forma parte de la comparación. |
| F2 | Logs Django/Docker | Adquisición temprana con timestamps antes de rotación, parada o eliminación. |
| F3 | Exportación MySQL | Dump lógico coherente para InnoDB, con inicio, fin, condiciones de consistencia y verificación de errores. |
| F4 | `LogEntry` del administrador | Extracción desde la copia adquirida para contrastar operaciones del panel. |
| F5 | Metadatos técnicos | SHA de Git, versiones, imágenes, contenedores, referencia UTC y configuración sanitizada. |
| F6 | Binlog MySQL | Contraste opcional si estaba habilitado y cubre el periodo investigado. |

`acquire_case.sh` deberá comprobar espacio disponible, errores, códigos de retorno y archivos vacíos inesperados. El hash se calculará al cerrar cada archivo. Un dump incompleto no se declarará una adquisición satisfactoria. Los secretos utilizados para acceder a MySQL deberán quedar fuera de comandos registrados, trazas e informes compartidos.

### 6.2 Organización del expediente y custodia

Cada expediente se almacenará fuera de Git y de los volúmenes operativos de Docker:

```text
forensic_cases/
└── CASE-001/
    ├── original/     # Archivos adquiridos, conservados sin transformación
    ├── trabajo/      # Copias verificadas para examen
    ├── custodia/     # Inventario, actas y manifiestos SHA-256
    ├── analisis/     # Derivados, inconsistencias y línea de tiempo
    └── reporte/      # Informe y anexos
```

El inventario y la cadena de custodia incluirán ID del caso y de la evidencia, descripción, procedencia, ruta, formato, tamaño, SHA-256, fecha y hora UTC, adquirente, custodio, emisor, receptor, motivo de transferencia, ubicación y constancias de entrega y recepción.

Se verificará SHA-256 antes de cada examen y después de cada transferencia. Cada derivado tendrá identificación y hash propios. Ante una discrepancia se apartará la copia afectada, se registrará la incidencia y se recuperará una copia válida o se declarará la limitación, sin reemplazar silenciosamente los originales.

### 6.3 Reglas del examen y del informe

El examen trabajará sobre copias y conservará los tiempos originales y sus offsets junto con la normalización a UTC. Se documentarán faltantes, duplicados, errores de lectura y discrepancias. La línea de tiempo utilizará los identificadores disponibles; la coincidencia temporal por sí sola no se tratará como prueba concluyente de causalidad.

Cada hallazgo deberá referenciar su evidencia y distinguir hechos observados de inferencias. El informe aplicará la escala prevista en el documento base: confirmado con contraste, sustentado en una sola fuente, indeterminado o contradicho. También considerará explicaciones alternativas, como cambio legítimo, error operativo, sesión compartida, automatización por API o desfase horario.

La identificación de una cuenta no atribuye por sí sola una acción a una persona. La calificación de una operación como indebida dependerá de las reglas del escenario, y no únicamente de que exista un UPDATE o DELETE.

## 7. Validación y criterios de aceptación

### 7.1 Pruebas previstas

| Archivo o ámbito | Verificación |
| --- | --- |
| `test_web.py` | CREATE, UPDATE y DELETE; formularios inválidos y permisos; evento y snapshots correspondientes. |
| `test_api.py` | Operaciones equivalentes por API, autenticación, validación y asociación del evento a la solicitud. |
| `test_admin.py` | Alta, modificación, eliminación individual y borrado masivo, sin eventos duplicados ni registros omitidos. |
| `test_transactions.py` | Reversión si falla la auditoría, ausencia de éxito tras rollback, concurrencia y política de no-op. |
| `test_middleware.py` | IP con y sin proxy confiable, UUID de sesión y solicitud, separación de contexto y exclusión de secretos. |
| Base de datos | Restricción efectiva de UPDATE y DELETE sobre `AuditEvent` para la cuenta de ejecución. |
| Adquisición e integridad | Rechazo de exportaciones incompletas y detección de una copia alterada en un byte. |
| Reconstrucción | Repetición por otro analista utilizando las copias, las herramientas documentadas y las referencias de evidencia. |

### 7.2 Puertas de control

| Puerta | Condición de aceptación | Evidencia requerida |
| --- | --- | --- |
| G1 | Laboratorio reproducible y estados iniciales equivalentes. | SHA completo, versiones, configuraciones, carga ficticia y comprobación inicial A/B. |
| G2 | Cobertura de CREATE/UPDATE/DELETE en web, API y admin, incluido borrado masivo. | Resultados de pruebas por canal y correspondencia entre operaciones y eventos. |
| G3 | Snapshots correctos y consistencia transaccional. | Pruebas before/after, concurrencia y rollback sin falsos eventos de éxito. |
| G4 | Adquisición y copias con integridad y custodia verificables. | Inventario, manifiestos, verificaciones y registro de transferencias. |
| G5 | Línea de tiempo e informe trazables hasta los originales. | Referencias por hallazgo, procedimiento reproducible y revisión independiente. |

Si una puerta falla, se registrará la no conformidad, se corregirá la causa y se repetirá la comprobación. La existencia de una tabla de auditoría o un manifiesto de hashes no bastará para declarar validado el procedimiento completo.

## 8. Métricas de la comparación

Las métricas se calcularán después de las pruebas, por entorno y ejecución cuando corresponda. Las metas son criterios técnicos del documento base y no resultados ya obtenidos.

| Métrica | Cálculo | Meta o uso |
| --- | --- | --- |
| Cobertura de auditoría | Operaciones CRUD confirmadas con evento completo / operaciones CRUD confirmadas esperadas × 100. | Meta del 100 % para las operaciones del guion en B. |
| Reconstrucción completa | Operaciones con cuenta, tiempo, canal, ID y before/after aplicables / operaciones del guion × 100. | Comparar A y B con los mismos criterios. |
| Integridad de copias | Archivos con SHA-256 coincidente / archivos examinados × 100. | Meta del 100 %. |
| Trazabilidad de custodia | Transferencias documentadas / transferencias realizadas × 100. | Meta del 100 %. |
| Tiempo por caso | Duración de adquisición y duración de análisis a partir de marcas registradas. | Reportar y comparar, sin anticipar ahorros. |

Los intentos fallidos y los no-op seguirán la clasificación definida antes de ejecutar el guion. Las operaciones esperadas y confirmadas se identificarán explícitamente para no ocultar omisiones. Cuando un denominador sea cero, se registrará la métrica como no aplicable. No se inventarán porcentajes de mejora, costos o retorno económico.

## 9. Cronograma de cuatro semanas

| Periodo | Trabajo principal | Hito |
| --- | --- | --- |
| Semana 1 | Verificar el fork, fijar versión, desplegar la línea base, preparar datos y guion e iniciar la aplicación forense. | Entorno reproducible y matriz de operaciones esperadas. |
| Semana 2 | Completar `AuditEvent`, contexto, snapshots, servicio e integración de los tres canales; ejecutar pruebas. | Instrumentación y verificaciones G2–G3. |
| Semana 3 | Completar la equivalencia A/B, ejecutar escenarios y adquirir evidencias con hashes y custodia. | Paquetes de evidencia y verificación G4. |
| Semana 4 | Examinar, correlacionar, calcular métricas y elaborar y revisar el informe. | Matriz comparativa, informe y verificación G5. |

La línea base deberá prepararse desde la primera semana. La tercera etapa completará el laboratorio comparativo y ejecutará los escenarios sobre la versión instrumentada ya comprobada.

## 10. Responsabilidades y seguimiento de riesgos

Los integrantes asignarán responsables de backend, infraestructura, QA, adquisición/custodia y análisis/revisión. Si una persona asume varias funciones, se dejará constancia en el acta del caso. La revisión del informe deberá realizarla otro integrante.

| Riesgo del documento base | Acción prevista | Responsable funcional |
| --- | --- | --- |
| R1. Ruta CRUD sin auditoría | Servicio común, pruebas de los tres canales y borrado masivo. | Backend y QA |
| R2. Eventos inconsistentes o perdidos | Transacción conjunta y pruebas de rollback, concurrencia y duplicados. | Backend y QA |
| R3. Pérdida por rotación de logs | Retención previa y adquisición antes de reinicios o eliminación. | Infraestructura y custodio |
| R4. Manipulación de evidencias | Original restringido, SHA-256, manifiesto y custodia. | Custodio |
| R5. Identificación errónea de cuenta o IP | Proxy confiable, correlación y límites explícitos de atribución. | Backend y analista |
| R6. Desfase horario | UTC, comprobación de relojes y conservación de offsets. | Infraestructura y analista |
| R7. Secretos o datos sensibles en el expediente | Datos ficticios, acceso restringido y exclusión de evidencias de Git. | Backend y custodio |
| R8. Comparación A/B no equivalente | Semilla, estado inicial, guion y registro de desviaciones comunes. | QA y analista |
| R9. Conclusiones sin respaldo suficiente | Evidencias por hallazgo, hipótesis alternativas y revisión independiente. | Analista y revisor |

Se revisarán los riesgos antes de la simulación, al completar la instrumentación, después de la adquisición y antes de emitir el informe. Ante cambios confirmados sin auditoría, hashes discrepantes o pérdida de originales se detendrá la evaluación del caso, se preservará lo disponible y se documentará la incidencia y su efecto.

## 11. Entregables para el cierre

- [x] Fork localizado, rama `creacion_auditoria` identificada y commits original e instrumentado registrados.
- [ ] Configuraciones A/B aisladas, datos ficticios y guion reproducible.
- [ ] Módulo `website/forensics/` con servicio común y exportación, y nuevas migraciones de `website` para ampliar el modelo existente.
- [ ] Integración y pruebas de web, API y administración, incluido borrado masivo.
- [ ] Herramientas de adquisición, verificación, examen, línea de tiempo y reporte.
- [ ] Plantillas de inventario, custodia e informe en `forensic_docs/`.
- [ ] Expedientes fuera de Git con originales, copias, manifiestos y registros de manejo.
- [ ] Matriz de resultados A/B, métricas, desviaciones y no conformidades.
- [ ] Informe revisado con hallazgos trazables, limitaciones y pendientes de cada caso.
- [ ] Registro de cumplimiento de G1–G5 y resultados experimentales para el capítulo V.

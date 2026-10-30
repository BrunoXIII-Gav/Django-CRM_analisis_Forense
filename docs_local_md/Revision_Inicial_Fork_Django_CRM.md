# Revisión inicial del fork de Django-CRM

**Fecha:** 30 de octubre de 2026.  
**Alcance:** Verificar la versión, estructura y puntos de integración del fork con el plan de implementación.  
**Resultado:** Revisión inicial completada. El código ya contiene una primera implementación forense; corresponde ampliarla y reorganizarla. Su funcionamiento experimental todavía no se ha validado en esta revisión.

## 1. Repositorio y rama de trabajo

| Elemento | Valor verificado |
| --- | --- |
| Repositorio | [BrunoXIII-Gav/Django-CRM_analisis_Forense](https://github.com/BrunoXIII-Gav/Django-CRM_analisis_Forense) |
| Copia local | `C:/Users/Kato/Documents/Cursos/TASI/Proyecto/Django-CRM_analisis_Forense` |
| Ramas remotas | `main` y `creacion_auditoria` |
| Rama seleccionada | `creacion_auditoria`, interpretada como la segunda rama indicada por el usuario. |
| HEAD revisado | `151329f5708bc3c9c26405fc04c6cc1e6b2b7884` |
| HEAD de `main` | `5f80cd103e32825f4504fa5e96103d56cfbd968e` |
| Ancestro común | Coincide con el HEAD de `main`. |
| Diferencia | Un commit adicional en `creacion_auditoria`; 13 archivos afectados, 825 líneas añadidas y 3 eliminadas. |
| Estado de la copia local | Sin cambios al código tras la revisión. |

La referencia `5f80cd1` del documento académico coincide con la versión original de `main`. Se descargó el fork y se seleccionó `creacion_auditoria`. No se crearon ramas adicionales ni se publicaron cambios en GitHub.

## 2. Estructura y componentes encontrados

| Componente | Situación observada |
| --- | --- |
| `website/models.py` | Contiene `Record`, `AuditEvent` y restricciones de modificación del historial por las operaciones ORM habituales. `Record.save()` abre una transacción. |
| `website/migrations/0003_auditevent.py` | Crea el modelo existente de auditoría dentro de la aplicación `website`. |
| `website/forensic.py` | Concentra middleware, contexto con `ContextVar`, snapshots y señales de guardado y eliminación. |
| `website/apps.py` | Conecta las señales desde `WebsiteConfig.ready()`. |
| `dcrm/settings/base.py` | Habilita el middleware después de autenticación, utiliza UTC y define autenticación de API por sesión. |
| `website/views.py` | Las vistas web siguen escribiendo mediante formularios y eliminación del objeto. Las señales capturan esas operaciones. |
| `website/api_views.py` | Mantiene `RecordViewSet` sin métodos `perform_*` propios; la captura actual depende de las señales. |
| `website/admin.py` | Permite gestionar clientes y consultar auditoría sin altas, cambios ni bajas de eventos desde el panel. |
| `adquirir_evidencias.sh` | Adquiere logs, configuración Compose, dump MySQL y binlog condicional; crea manifiesto, copias y custodia. |
| `verificar_integridad.sh` | Comprueba originales y copias contra el manifiesto y registra los resultados en custodia. |
| `website/tests_forensic.py` | Contiene pruebas de cobertura, snapshots, rollback, permisos, contexto y borrado de varios objetos. |
| `website/tests_evidence_scripts.py` | Contiene pruebas de adquisición y verificación con Docker simulado. |
| `docs/forense.md` | Describe activación, alcance, consulta del historial y uso de los scripts actuales. |
| `website/forensics/`, `forensic_lab/`, `forensic_docs/` | No existen en la versión revisada. Son parte del trabajo pendiente. |

## 3. Ajustes necesarios respecto del plan

### 3.1 Conservar y ampliar la auditoría existente

No se debe volver a crear `AuditEvent` como si el fork partiera del CRM original. El modelo actual guarda cuenta, hora, IP, correlación, solicitud, canal, acción, ID del cliente y estados before/after.

Los nombres difieren del diseño propuesto: `timestamp`, `username`, `user_id`, `ip_address`, `correlation_id`, `source`, `object_id`, `before` y `after` ya cubren parte de los atributos. El evento tiene una clave primaria numérica; faltan el UUID de evento, la etiqueta de ejecución y los campos explícitos de diferencias y resultado previstos en el plan. Antes de añadir o renombrar campos se deberá definir su correspondencia y conservar los eventos existentes.

La correlación actual utiliza los primeros 16 caracteres del SHA-256 de la clave de sesión. El plan propone un UUID generado y controlado por el servidor. El snapshot actual obtiene los campos mediante `model_to_dict()` y añade las fechas; falta una lista positiva explícita de campos.

### 3.2 Organizar el servicio y evitar duplicados

La captura actual se realiza mediante señales. El servicio común previsto en el plan aún no existe. La transición deberá preservar los snapshots persistidos, la transacción y las pruebas que ya aporta el fork.

La recomendación incorporada al plan es conservar inicialmente el modelo en `website/models.py` y organizar la lógica en el paquete `website/forensics/`. Sus migraciones seguirán perteneciendo a `website`; el comando de exportación irá en `website/management/commands/`.

Al integrar el servicio con vistas, API y admin se retirará o redirigirá la escritura de auditoría por señales. Mantener simultáneamente ambos mecanismos sin coordinación podría generar eventos duplicados. El borrado masivo administrativo deberá verificarse mediante una solicitud real al panel, además de las pruebas existentes sobre querysets.

### 3.3 Configurar explícitamente MySQL para el laboratorio

`manage.py`, WSGI y ASGI utilizan por defecto `dcrm.settings`. Ese módulo importa `dev.py`, que fuerza SQLite y `DEBUG=True`, aunque existan variables `DB_*` para MySQL.

`docker-compose.yml` configura `DB_HOST=db`, pero no establece un módulo de settings de laboratorio. `.env.example` tampoco fija `DJANGO_SETTINGS_MODULE`. Por tanto, utilizar el ejemplo sin ajustes dejaría el CRM en SQLite y separaría sus datos del MySQL adquirido por los scripts.

Se deberá incorporar una configuración explícita para el laboratorio con MySQL/InnoDB y `DEBUG=False`, utilizada tanto por migraciones como por la aplicación. Los dos entornos necesitarán sus propios proyectos, volúmenes y condiciones de acceso. El perfil de producción incluye redirección obligatoria a HTTPS, por lo que no debe adoptarse sin revisar cómo se accederá al laboratorio local.

### 3.4 Separar permisos y completar el laboratorio

El Compose publica `3306:3306` y configura MySQL con la cuenta root. No se encontraron scripts de creación de un rol de migraciones y otro de ejecución con permisos diferenciados sobre la auditoría. La protección ORM existente no equivale a una restricción de permisos en MySQL.

Tampoco existen aún las configuraciones A/B, la semilla reproducible, el guion automatizado, la exportación específica de auditoría ni las herramientas de examen, línea de tiempo e informe del plan.

### 3.5 Adaptar la adquisición y la custodia

Los scripts existentes ofrecen un punto de partida: evitan sobrescribir casos, conservan capturas parciales si falla una adquisición obligatoria y comprueban originales y copias con SHA-256.

Persisten diferencias con el procedimiento previsto:

- El destino está fijado en `evidencias/<CASO>` dentro del repositorio, aunque está excluido de Git. El plan requiere un destino externo configurable.
- Se guarda la salida completa de `docker compose config`, que puede contener secretos interpolados. Hace falta definir qué configuración sanitizada se preservará como metadato.
- El acceso a MySQL usa root y pasa su contraseña como argumento de las herramientas. Deberá adaptarse al mecanismo de credenciales y permisos del laboratorio.
- La custodia CSV registra fecha, acción, responsable, archivo y hash; faltan los identificadores, procedencia, tamaño y datos de transferencia previstos en el plan.
- Falta registrar sistemáticamente versiones, commit, intervalo cubierto, inicio y fin de adquisición, errores y condiciones de consistencia.
- Los scripts no comprueban espacio disponible ni validan semánticamente que el dump sea completo antes de publicar el manifiesto.

No se ejecutaron estos scripts contra contenedores ni se adquirió evidencia real durante esta revisión.

### 3.6 Ajustar la validación automatizada

El flujo `.github/workflows/ci.yml` se activa por pushes a `main` y solicitudes de integración dirigidas a `main`. Un push aislado a `creacion_auditoria` no activa ese flujo.

Aunque el flujo configura un servicio MySQL y variables de conexión, no fija `DJANGO_SETTINGS_MODULE`. La configuración predeterminada carga SQLite, de modo que ese flujo no acredita por sí solo la validación de la aplicación sobre MySQL. Se deberá fijar el perfil del laboratorio o de pruebas y comprobar el motor efectivo antes de declarar cobertura de transacciones o concurrencia en MySQL.

## 4. Comprobaciones realizadas y límites

| Comprobación | Resultado |
| --- | --- |
| Consulta de ramas y commits remotos | Completada. |
| Descarga y selección de `creacion_auditoria` | Completadas. |
| Relación entre la rama de trabajo y `main` | Verificada: un commit adicional sobre la referencia del documento. |
| Lectura de configuración, auditoría, migración, canales, scripts y pruebas | Completada. |
| Sintaxis de los 28 archivos Python | Correcta mediante análisis estático; no ejecuta Django. |
| Sintaxis de los dos scripts Bash | Correcta mediante `bash -n`; no ejecuta la adquisición. |
| Docker y Compose disponibles | Sí; se consultó el motor Docker sin iniciar contenedores. |
| Dependencias Django del Python local | Django, DRF y otras dependencias requeridas no están instaladas. |
| `manage.py check`, consistencia de migraciones y suite Django | Pendientes; no se instalaron dependencias durante esta revisión. |
| Suite de scripts con Docker simulado | Pendiente de un entorno compatible; no equivale a adquisición real. |
| Simulación y verificación con MySQL real | Pendientes. |

No se modificó el código del fork, no se crearon datos de aplicación y no se ejecutaron migraciones. Se actualizaron los documentos de planificación fuera del repositorio clonado.

## 5. Punto de inicio para la implementación

El primer paso de identificación y revisión del fork queda completado. El siguiente bloque de trabajo será preparar un entorno reproducible de desarrollo y pruebas, fijar explícitamente la configuración MySQL del laboratorio y ejecutar las comprobaciones existentes para establecer la línea base funcional de `creacion_auditoria`.

Después se podrá reorganizar la auditoría y completar las herramientas del plan, conservando el historial de migraciones y las pruebas actuales. Las puertas G1–G5 permanecen pendientes de validación experimental.

# Preparación e investigación forense de Django-CRM

La implementación se desarrolló sobre `creacion_auditoria` y se entrega en `implementacion_forense`. `website.AuditEvent` y la migración `0003_auditevent` conservan su identidad. El documento académico es material de consulta y no se modifica.

## Entorno y comprobaciones

Usar Python 3.12 y Docker Desktop con contenedores Linux. Los entrypoints `.sh` requieren Bash, Python 3 y Docker Compose con soporte para `include`, `extends` y `!override` (versión validada en `validacion_forense.md`). En Windows, los comandos Python y Compose pueden ejecutarse desde PowerShell; los `.sh` pueden ejecutarse desde WSL con integración de Docker Desktop. `.gitattributes` mantiene LF en los scripts.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test website --settings=dcrm.settings.test_sqlite
```

El perfil `test_sqlite` usa un hasher rápido exclusivamente para pruebas. En SQLite se excluye la prueba de bloqueo concurrente; en Windows se excluye la comprobación Bash. Las pruebas de adquisición con Docker simulado son distintas de la adquisición real.

## Laboratorios A y B

A usa el commit `5f80cd103e32825f4504fa5e96103d56cfbd968e` de la versión original. B usa la rama local instrumentada. `prepare_lab.py` extrae A con `git archive` en `.lab/baseline` sin cambiar de rama. Sólo añade ajustes de compilación y monta el perfil MySQL compartido; no incorpora la auditoría en A. Ambos usan las mismas dependencias de `requirements.lock`.

```powershell
.\.venv\Scripts\python.exe forensic_lab/tools/prepare_lab.py
docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.baseline.yml build
docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.instrumented.yml build
```

Para cada archivo Compose, ejecutar secuencialmente: `up -d db`, `run --rm migrate`, `exec -T db bash /lab/provision_mysql.sh`, cargar la semilla mediante el servicio `migrate` y finalmente `up -d web`. No preparar el mismo proyecto desde dos procesos simultáneos. Ejemplo B:

```powershell
docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.instrumented.yml up -d db
docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.instrumented.yml run --rm migrate
docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.instrumented.yml exec -T db bash /lab/provision_mysql.sh
Get-Content -Raw forensic_lab/fixtures/seed_demo.py | docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.instrumented.yml run --rm -T migrate python manage.py shell
docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.instrumented.yml up -d web
```

Repetir para A sustituyendo `instrumented` por `baseline`. Los proyectos predeterminados son `crm-forensic-a` y `crm-forensic-b`: redes y volúmenes independientes, MySQL sin puerto publicado, web en [A](http://127.0.0.1:8001) y [B](http://127.0.0.1:8002). Para nuevas repeticiones, usar `-p crm-forensic-a-r02` / `-p crm-forensic-b-r02` en **todos** los comandos; detener los servicios web de la ejecución anterior sólo después de adquirir sus evidencias para liberar los puertos. No borrar volúmenes ni reutilizar bases ya pobladas. La semilla rechaza una base con datos.

Los secretos ficticios se generan en `.lab/lab.env`, excluido de Git y de las imágenes. `lab_admin` y `lab_operator` comparten la contraseña de laboratorio generada en `LAB_DEMO_PASSWORD`; su valor no se imprime. En una revisión manual de ambos sitios usar perfiles de navegador independientes, porque las cookies no se aíslan por puerto.

El perfil `dcrm.settings.lab` fija MySQL/InnoDB, UTC y `DEBUG=False`. La cuenta `crm_migrate` modifica el esquema; `crm_runtime` escribe clientes y sólo SELECT/INSERT de auditoría; `crm_reader` adquiere el dump sin contraseña en argumentos. Las credenciales montadas desde Windows se copian temporalmente a un archivo privado Linux durante el dump y se retiran al terminar. `provision_mysql.sh` concede al migrador permisos sobre `test_crm_lab` exclusivamente para la suite. Las restricciones se comprueban con SQL que no afecta filas:

```powershell
Get-Content -Raw forensic_lab/tools/check_db_permissions.py | docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.instrumented.yml exec -T web python -
docker compose --env-file .lab/lab.env -f forensic_lab/environments/compose.instrumented.yml run --rm -e DJANGO_SETTINGS_MODULE=dcrm.settings.test_mysql migrate python manage.py test website --noinput
```

## Auditoría común

Web, API y admin llaman a `website/forensics/services.py`. UPDATE y DELETE bloquean la fila en la misma base que registra el evento. La escritura del cliente y su evento comparten `transaction.atomic()`: un fallo de auditoría revierte ambos. El borrado masivo administrativo es una sola transacción y registra un evento por cliente. Las señales de `website/forensic.py` quedan como compatibilidad para llamadas ORM antiguas y omiten las operaciones del servicio, evitando duplicados. Sus límites siguen siendo explícitos: SQL directo, `QuerySet.update()`, operaciones bulk y fixtures no representan cobertura del servicio.

Los snapshots usan una lista positiva de campos de `Record`: ID, nombre, apellido, correo, teléfono, dirección, ciudad, estado, código postal y fechas. CREATE tiene `before=null`; DELETE tiene `after=null`. No se capturan cookies, contraseñas, tokens, Authorization ni cuerpos HTTP. Un UPDATE sin cambios de negocio conserva los timestamps y registra `outcome=noop`, con diferencias vacías; se excluye de las métricas de modificaciones. Las solicitudes rechazadas sólo dejan el resultado HTTP en logs, sin evento de modificación confirmada.

La migración `0004` añade UUID único, etiqueta de ejecución, agente de usuario acotado, campos cambiados, resultado y confirmación sin renombrar campos históricos. Asigna UUID distinto a cada evento anterior y lo marca `legacy_unknown` / `committed=null`; no inventa contexto de sesiones anterior ni reescribe snapshots. Los nombres existentes corresponden a: `timestamp` → hora UTC; `username/user_id` → cuenta; `correlation_id` → correlación; `source` → canal; `object_id` → cliente; `before/after` → snapshots.

El middleware genera UUID de solicitud y un UUID aleatorio guardado en la sesión del servidor, compartido por web/admin/API con autenticación de sesión. No deriva correlación de la cookie. Usa `REMOTE_ADDR`; sólo interpreta X-Forwarded-For si la IP inmediata pertenece a `FORENSIC_TRUSTED_PROXIES`, recorriendo los saltos desde la derecha hasta el primer salto no confiable. El encabezado `X-Request-ID` de respuesta permite contrastar el evento con el log HTTP. El contexto se limpia incluso ante excepciones. El canal y la ruta se toman de rutas controladas, sin query strings ni cargas.

El admin permite consulta con `website.view_auditevent` e impide altas, cambios y bajas. La protección ORM y los permisos de ejecución no garantizan inmutabilidad frente al administrador de MySQL o del anfitrión.

```bash
python manage.py export_audit --case-tag scenario-01 --since 2026-10-30T00:00:00Z --until 2026-10-31T00:00:00Z > audit.json
```

El comando es de consola, no un endpoint público. Exporta JSON de auditoría filtrada, clientes y LogEntry relevante. El exportador genérico del laboratorio también identifica las cuentas por ID/nombre, sin hashes de contraseña ni cookies. El dump SQL completo sí contiene material de autenticación ficticio y requiere acceso restringido.

## Guion y equivalencia

Antes del guion, exportar A/B con `export_sources.py` y comparar `records` y `accounts`; `database_vendor` debe ser `mysql`, con `audit_available=false` en A y `true` en B. La semilla fija IDs y fechas iniciales; los hashes de contraseña y fechas de creación de cuenta no forman parte de la equivalencia funcional.

```powershell
.\.venv\Scripts\python.exe forensic_lab/scenarios/scenario_01.py --base-url http://127.0.0.1:8001 --environment A --env-file .lab/lab.env --output .lab/truth-A.json
.\.venv\Scripts\python.exe forensic_lab/scenarios/scenario_01.py --base-url http://127.0.0.1:8002 --environment B --env-file .lab/lab.env --output .lab/truth-B.json
```

El cliente HTTP usa CSRF y sesiones reales. Ejecuta diez cambios confirmados por lecturas posteriores, un no-op y un intento anónimo rechazado. Incluye cambios sucesivos y borrado administrativo masivo. La tabla de verdad guarda reglas previas y valores esperados fuera de los expedientes; sólo se incorpora tras el examen para evaluar resultados. El escenario acepta exclusivamente HTTP en loopback. No repetirlo sobre una base ya usada.

## Adquisición y preservación

Detener nuevas operaciones del guion. Declarar autorización, alcance, intervalo, operadores, custodio y posibles desfases. El directorio de casos debe estar **fuera del repositorio**. Ejemplo desde Bash; en PowerShell usar la ruta a `.venv/Scripts/python.exe` y ajustar las continuaciones:

```bash
python forensic_lab/tools/acquire_case.py \
  --root ../forensic_cases --case CASE-B-001 --operator 'Analista del laboratorio' \
  --compose forensic_lab/environments/compose.instrumented.yml --env-file .lab/lab.env \
  --environment B --scope 'Clientes ficticios; escenario 01' \
  --authorization 'Referencia a la autorización académica local' \
  --interval-start 2026-10-30T00:00:00Z --interval-end 2026-10-31T00:00:00Z \
  --writes-stopped
python forensic_lab/tools/verify_evidence.py --root ../forensic_cases --case CASE-B-001 --operator 'Analista del laboratorio'
```

Usar el intervalo real guardado en `truth-B.json`. Añadir `--project` si se cambió el proyecto Compose. `--clock-offset-seconds` permite declarar una medición; dejarlo ausente registra desconocido, no cero. Los entrypoints `adquirir_evidencias.sh` y `verificar_integridad.sh` delegan a estas herramientas con los mismos argumentos; sus antiguas posiciones caso/responsable se sustituyen por opciones explícitas. Consultar `--help`.

Cada caso contiene `original/`, `trabajo/`, `custodia/`, `analisis/` y `reporte/`. La adquisición comprueba espacio, conserva logs antes de reinicios, exporta datos y dump, valida marcadores de esquema/finalización y captura versiones, código en ejecución, comandos, tiempos y retornos. La configuración preservada usa una lista positiva que excluye secretos. El binlog es condicional; si falla se declara indisponible y no sustenta conclusiones. Las fuentes se adquieren secuencialmente; no forman una instantánea atómica conjunta.

Inventario y custodia incluyen IDs, origen, formato, tamaño, SHA-256, fecha UTC, adquirente/custodio y ubicación. El manifiesto sólo se publica después de completar fuentes obligatorias, copias y verificaciones. Si algo falla, conservar el caso parcial y abrir otro ID para el reintento. No sobrescribir. Los originales y copias iniciales quedan sin escritura; los permisos Windows deben complementarse con las ACL de la carpeta del custodio. Mantener respaldo separado del manifiesto y custodia. SHA-256 acredita conservación desde la adquisición, no veracidad previa.

Docker retiene cinco archivos de 20 MB por servicio. Esa rotación es preventiva y finita: adquirir antes de que rote. No ejecutar `docker compose down -v`, truncar logs, eliminar contenedores o volúmenes con evidencia pendiente.

## Examen, restauración y reporte

```bash
python forensic_lab/tools/validate_restore.py --root ../forensic_cases --case CASE-B-001 --operator Analista
python forensic_lab/tools/examine_evidence.py --root ../forensic_cases --case CASE-B-001 --operator Analista
python forensic_lab/tools/build_timeline.py --root ../forensic_cases --case CASE-B-001 --operator Analista
python forensic_lab/tools/generate_report.py --root ../forensic_cases --case CASE-B-001 --operator Analista --truth .lab/truth-B.json
```

`validate_restore.py` restaura únicamente una copia verificada en un MySQL temporal sin red ni puertos; comprueba tablas/recuentos y elimina sólo ese contenedor desechable. No elimina volúmenes del caso. Una restauración posterior al primer informe se incorpora con `generate_report.py --revision 2`, conservando los derivados anteriores. El resultado queda en `restore_validation.json`, no se modifica el metadato original adquirido.

El examen conserva tiempos originales y offsets, normaliza UTC, identifica duplicados y errores, y produce JSON/CSV, cambios por registro e inconsistencias. La línea de tiempo referencia evidencia/archivo/ubicación. El contraste por request UUID confirma solicitud y resultado HTTP; los valores before/after siguen sustentados en la auditoría. LogEntry e INFO nativos conservan observaciones parciales sin inventar estados previos. Los derivados tienen ID, hash y procedencia, que se verifican antes del siguiente paso. Una discrepancia bloquea el examen; apartar la copia afectada y documentar la recuperación, sin reemplazar silenciosamente el original.

Para transferir una copia, `transfer_evidence.py` requiere origen del caso, destino externo nuevo, emisor, receptor, motivo y referencia de constancia (`--receipt`), y verifica hashes antes y después. La herramienta registra la declaración; no firma por las personas. Las métricas de transferencias son no aplicables si no hubo transferencias.

Las métricas se calculan por operación contra el guion independiente, con correspondencia única: cuenta, tiempo, canal, ID y estados aplicables completos. No-op e intentos rechazados se excluyen; denominador cero produce `null`. Conservar aparte la tabla de verdad para permitir la evaluación posterior al examen. El informe mantiene pendientes la revisión por otro integrante y el cierre de G5. Consultar las plantillas de `forensic_docs/` y el registro de validación en `docs/validacion_forense.md`.

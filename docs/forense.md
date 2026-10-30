# Extensión forense del CRM

Integración del material local `codigo_capitulo4`, preparado para el commit
`5f80cd1` del proyecto original (también base de este fork). Se incorporaron el
parche Django, la migración `0003_auditevent`, las pruebas y los dos scripts de
evidencias; se adaptaron para consultar eventos en el administrador, proteger las
escrituras y evitar sobrescribir casos. Los archivos de Descargas no se modifican.
No se requiere aplicar otra vez el parche original.

## Activación local

Desde la raíz del repositorio, con las dependencias de `requirements.txt`
instaladas en el entorno virtual:

```bash
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=dcrm.settings.dev
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`dcrm.settings.dev` utiliza SQLite. Si instalas `mysqlclient` en Linux, necesitarás
también las bibliotecas de desarrollo de MySQL y `pkg-config`, como en el CI.
Para desarrollo exclusivo con SQLite no se necesita ese controlador.

El middleware queda habilitado en la configuración base, inmediatamente después
de `AuthenticationMiddleware`. Las señales se conectan desde `WebsiteConfig`.
La migración crea una tabla nueva y no genera historia de los clientes existentes.

## Qué registra

Cada creación, modificación o eliminación de `Record` mediante `save()` o
`delete()` genera un `AuditEvent`. Esto cubre los formularios web, la API actual y
el administrador, incluido su borrado masivo. El evento conserva:

- Fecha y hora UTC, acción, modelo e identificador del registro.
- Usuario e identificador de cuenta, conservados aunque la cuenta se elimine.
- IP de `REMOTE_ADDR`, origen (`web`, `api`, `admin`) e identificador de solicitud.
- Correlación de sesión: los primeros 16 caracteres del SHA-256 de la clave de
  sesión; no se guarda la clave de sesión original.
- Estados anterior y posterior en JSON, con las fechas del registro. En creación
  no hay estado anterior; en eliminación no hay estado posterior.

El guardado del cliente y el evento comparten transacción y base de datos: un
fallo al escribir la auditoría revierte el guardado. El borrado utiliza la
transacción del colector de Django. Las capturas posteriores se leen de la base
para reflejar `update_fields` y expresiones de base de datos. En motores que lo
soportan se bloquea la fila al obtener el estado anterior de una actualización.

Los cambios desde shell o tareas sin una solicitud también se registran, pero sin
usuario, IP, origen ni identificadores de sesión/solicitud. No se interpreta
`X-Forwarded-For`: detrás de un proxy, `REMOTE_ADDR` puede ser la IP del proxy.

## Consulta y simulación

1. Inicia sesión en el CRM y crea un cliente con datos ficticios.
2. Modifica un campo, por ejemplo la ciudad, y después elimina ese cliente.
3. Entra con un superusuario a `/admin/website/auditevent/`.
4. Comprueba los eventos `CREATE`, `UPDATE` y `DELETE` y sus estados JSON.

El listado permite filtrar por acción, origen y fecha, y buscar por usuario,
registro, correlación o solicitud. El administrador no permite crear, editar ni
eliminar eventos. Para delegar la consulta a una cuenta de personal (`is_staff`),
asígnale el permiso `website.view_auditevent`.

## Adquisición de evidencias con Docker y MySQL

Estos scripts se ejecutan desde la raíz del repositorio y requieren los servicios
`web` y `db` de `docker-compose.yml` en ejecución. La adquisición usa las variables
`MYSQL_ROOT_PASSWORD` y `MYSQL_DATABASE` del contenedor `db`. No funciona contra
SQLite ni contra el despliegue PostgreSQL de Railway.

```bash
./adquirir_evidencias.sh CASO-001 "Bruno Gav"
./verificar_integridad.sh CASO-001 "Bruno Gav"
# También se puede indicar otro archivo Compose:
./adquirir_evidencias.sh CASO-002 "Bruno Gav" docker-compose.yml
```

Cada caso tiene esta estructura, excluida de Git:

```text
evidencias/CASO-001/
├── originales/              # Logs, configuración Compose, dump MySQL y estado del binlog
├── trabajo/                 # Copias iniciales de los originales
├── manifiesto_sha256.txt    # Hashes de los originales, usado para verificar ambos directorios
└── cadena_custodia.csv      # Responsable, fecha UTC, adquisición y verificaciones
```

Los archivos originales y las copias se dejan sin permisos de escritura. Se
rechaza un caso que ya existe; usa otro identificador para una nueva captura.
Los directorios nuevos son privados y la configuración Compose y el dump pueden
contener contraseñas y datos personales: conserva la carpeta en un lugar con
acceso restringido.

El manifiesto definitivo solo se publica si los pasos obligatorios terminaron.
Si fallan, se conservan los archivos parciales y se informa de una adquisición
incompleta. La verificación devuelve `0` si ambos directorios coinciden con el
manifiesto y un código distinto de cero si faltan archivos, falta el manifiesto
o hay diferencias. Cada verificación completa añade su resultado a la custodia.

El binlog es opcional. `estado_binlog.txt` indica si estaba deshabilitado, se
capturó o falló su adquisición. La ruta asumida es
`/var/lib/mysql/binlog.[0-9]*` y requiere `mysqlbinlog` dentro del contenedor.
Los logs, el dump y los binlogs se obtienen en momentos distintos; no forman una
instantánea atómica conjunta. El dump usa `--single-transaction` para tablas
transaccionales; evita cambios de esquema durante la captura.

## Alcance de esta versión

- Se auditan cambios de `Record`; no se registran lecturas, inicios de sesión ni
  modificaciones de otros modelos.
- `QuerySet.update()`, `bulk_create()`, `bulk_update()`, SQL directo y la carga de
  fixtures (`raw=True`) no generan eventos. Usa los flujos cubiertos para la
  simulación; el binlog puede aportar evidencia adicional si está disponible.
- El modelo y su queryset impiden las modificaciones y eliminaciones habituales
  de eventos por ORM. Un administrador de la base de datos, SQL directo o vías
  internas de Django pueden eludir esa protección.
- Los hashes detectan diferencias respecto del manifiesto conservado; no prueban
  autenticidad si alguien puede reemplazar tanto los archivos como el manifiesto.
  La custodia CSV y los permisos de solo lectura tampoco son almacenamiento
  inmutable ni una firma digital.
- Es una base de laboratorio para preparación forense. No incluye un almacén de
  evidencias externo, sellado de tiempo ni garantías de cumplimiento normativo.

## Verificación técnica

```bash
DJANGO_SETTINGS_MODULE=dcrm.settings.dev python manage.py check
DJANGO_SETTINGS_MODULE=dcrm.settings.dev python manage.py makemigrations --check --dry-run
DJANGO_SETTINGS_MODULE=dcrm.settings.dev python manage.py test website
bash -n adquirir_evidencias.sh verificar_integridad.sh
```

La suite cubre el CRM original, captura web/API/admin, estados persistidos,
reversiones, permisos de consulta, protección de eventos, contexto de solicitud y
adquisición/verificación de archivos con Docker simulado. Las pruebas de scripts
no ejecutan contenedores ni adquieren una base real.

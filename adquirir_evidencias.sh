#!/usr/bin/env bash
# Adquisición de laboratorio - Django-CRM en Docker + MySQL
# Uso: ./adquirir_evidencias.sh <CASO> <RESPONSABLE> [compose_file]
set -euo pipefail

umask 077
CASO="${1:?caso}"
RESP="${2:?responsable}"
COMPOSE="${3:-docker-compose.yml}"
[[ "$CASO" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || {
  echo "Caso inválido: usa letras, números, guiones o guiones bajos." >&2
  exit 1
}
[[ "$RESP" != *$'\n'* && "$RESP" != *$'\r'* ]] || {
  echo "El responsable debe ocupar una sola línea." >&2
  exit 1
}
[[ -f "$COMPOSE" ]] || { echo "No existe el archivo Compose: $COMPOSE" >&2; exit 1; }
command -v docker >/dev/null
docker compose version >/dev/null
BASE="evidencias/${CASO}"
ORIG="${BASE}/originales"
TRAB="${BASE}/trabajo"
mkdir -p evidencias
mkdir "$BASE" || { echo "El caso ya existe o no se puede crear; no se sobrescribirá." >&2; exit 1; }
trap 'echo "Adquisición incompleta. Archivos parciales conservados en: $BASE" >&2' ERR
mkdir "$ORIG" "$TRAB"
ahora() { date -u +%Y-%m-%dT%H:%M:%SZ; }
RESP_CSV="${RESP//\"/\"\"}"
custodia() { printf '%s,%s,"%s",%s,%s\n' "$(ahora)" "$1" "$RESP_CSV" "$2" "$3" >> "${BASE}/cadena_custodia.csv"; }
echo "fecha_utc,accion,responsable,archivo,sha256" > "${BASE}/cadena_custodia.csv"

# 1) Registros de Docker (antes de detener/eliminar contenedores)
docker compose -f "$COMPOSE" logs --no-color --timestamps web > "${ORIG}/docker_web.log"
docker compose -f "$COMPOSE" logs --no-color --timestamps db  > "${ORIG}/docker_db.log"
docker compose -f "$COMPOSE" config > "${ORIG}/compose_config.yml"

# 2) Exportación lógica coherente de MySQL (incluye website_auditevent y django_admin_log)
docker compose -f "$COMPOSE" exec -T db sh -c \
  'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines \
   --no-tablespaces "$MYSQL_DATABASE"' > "${ORIG}/mysql_dump.sql"

# 3) Registro binario de MySQL: solo si está habilitado
if docker compose -f "$COMPOSE" exec -T db sh -c \
   'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e "SELECT @@log_bin"' > "${BASE}/log_bin.tmp"; then
  if [[ "$(cat "${BASE}/log_bin.tmp")" == "1" ]]; then
    if docker compose -f "$COMPOSE" exec -T db sh -c \
       'mysqlbinlog /var/lib/mysql/binlog.[0-9]*' > "${BASE}/mysql_binlog.tmp"; then
      mv "${BASE}/mysql_binlog.tmp" "${ORIG}/mysql_binlog.txt"
      echo "Binlog adquirido; no es una instantánea atómica del dump." > "${ORIG}/estado_binlog.txt"
    else
      rm -f "${BASE}/mysql_binlog.tmp"
      echo "No se pudo adquirir el binlog; revisar ruta, permisos y herramienta mysqlbinlog." > "${ORIG}/estado_binlog.txt"
    fi
  else
    echo "Binlog deshabilitado en MySQL." > "${ORIG}/estado_binlog.txt"
  fi
else
  echo "No se pudo consultar si MySQL tiene binlog habilitado." > "${ORIG}/estado_binlog.txt"
fi
rm -f "${BASE}/log_bin.tmp"
cat "${ORIG}/estado_binlog.txt" >&2

# 4) Hash de cada original, custodia y copia de trabajo de solo lectura
( cd "$ORIG" && sha256sum -- * ) > "${BASE}/manifiesto_sha256.tmp"
for f in "$ORIG"/*; do
  h=$(sha256sum "$f" | cut -d' ' -f1)
  custodia ADQUISICION "$(basename "$f")" "$h"
  cp -p "$f" "$TRAB/"
done
chmod a-w "$ORIG"/* "$TRAB"/*
# Publicar el manifiesto solo cuando la adquisición y las copias terminaron.
mv "${BASE}/manifiesto_sha256.tmp" "${BASE}/manifiesto_sha256.txt"
chmod a-w "${BASE}/manifiesto_sha256.txt"
trap - ERR
echo "Adquisición completa: $(ls "$ORIG" | wc -l) archivos en ${ORIG}"

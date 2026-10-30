#!/usr/bin/env bash
# Verifica que originales y copias de trabajo coincidan con el manifiesto SHA-256
# Uso: ./verificar_integridad.sh <CASO> <RESPONSABLE>
set -euo pipefail
umask 077
CASO="${1:?caso}"
RESP="${2:?responsable}"
[[ "$CASO" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || {
  echo "Caso inválido: usa letras, números, guiones o guiones bajos." >&2
  exit 1
}
[[ "$RESP" != *$'\n'* && "$RESP" != *$'\r'* ]] || {
  echo "El responsable debe ocupar una sola línea." >&2
  exit 1
}
BASE="evidencias/${CASO}"
[[ -s "${BASE}/manifiesto_sha256.txt" ]] || {
  echo "Falta un manifiesto completo para el caso: $CASO" >&2
  exit 1
}
RESP_CSV="${RESP//\"/\"\"}"
estado=0
for dir in originales trabajo; do
  if ( cd "${BASE}/${dir}" && sha256sum --quiet -c "../manifiesto_sha256.txt" ); then
    r=OK
  else
    r=FALLO; estado=1
  fi
  printf '%s,VERIFICACION_%s,"%s",manifiesto,%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$dir" "$RESP_CSV" "$r" >> "${BASE}/cadena_custodia.csv"
  echo "${dir}: ${r}"
done
exit $estado

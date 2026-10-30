#!/usr/bin/env bash
set -euo pipefail
exec bash "$(dirname "$0")/forensic_lab/tools/acquire_case.sh" "$@"

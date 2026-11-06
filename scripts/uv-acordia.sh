#!/usr/bin/env bash
# Corre un comando con las credenciales del índice `acordia` (librería de render, R1) en el entorno.
# Uso:  scripts/uv-acordia.sh uv --no-config sync     (o lock, run, etc.)
# El token sale de las credenciales de gcloud (~/.config/gcloud-saul); no se guarda en ningún archivo.
set -euo pipefail
export CLOUDSDK_CONFIG="${CLOUDSDK_CONFIG:-$HOME/.config/gcloud-saul}"
export UV_INDEX_ACORDIA_USERNAME=oauth2accesstoken
UV_INDEX_ACORDIA_PASSWORD="$(gcloud auth print-access-token)"
export UV_INDEX_ACORDIA_PASSWORD
exec "$@"

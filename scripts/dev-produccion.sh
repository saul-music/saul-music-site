#!/usr/bin/env bash
# Sitio local con los temas que están publicados en producción.
#
# Baja la publicación vigente del bucket editorial (solo lectura) a ../../acordes-produccion, FUERA de
# este repo (público: los temas no se versionan, M9) y arranca el sitio apuntando a esa copia.
#
# Uso:  scripts/dev-produccion.sh [--solo-bajar]      Variables: PORT (8767), DEST
set -euo pipefail

BUCKET="gs://saulapp-music-editorial"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${DEST:-$ROOT/../acordes-produccion}"
PORT="${PORT:-8767}"

# Credenciales de este proyecto (CLAUDE.md del control): nunca las de otra cuenta de la máquina.
export CLOUDSDK_CONFIG="${CLOUDSDK_CONFIG:-$HOME/.config/gcloud-saul}"
export PYENV_VERSION="${PYENV_VERSION:-3.14.3}" UV_PYTHON_PREFERENCE=only-managed

if [[ "$(mkdir -p "$DEST" && cd "$DEST" && pwd)" == "$ROOT"* ]]; then
  echo "DEST no puede estar dentro del repo del sitio (es público): $DEST" >&2
  exit 1
fi

release="$(gcloud storage cat "$BUCKET/current.txt" | tr -d '\n')"
if [[ ! "$release" =~ ^releases/[A-Za-z0-9-]+$ ]]; then
  echo "current.txt no apunta a una publicación válida: «$release»" >&2
  exit 1
fi

echo "Bajando $release …"
rm -rf "$DEST/releases"            # solo se guarda la publicación vigente
mkdir -p "$DEST/$release"
gcloud storage cp -q "$BUCKET/$release/*" "$DEST/$release/"
printf '%s' "$release" > "$DEST/current.txt"
echo "Listo: $(ls "$DEST/$release"/*.toml | wc -l | tr -d ' ') temas en $DEST/$release"

[[ "${1:-}" == "--solo-bajar" ]] && exit 0

echo "Sitio en http://127.0.0.1:$PORT (Ctrl+C para salir)"
cd "$ROOT"
PORT="$PORT" EDITORIAL_DIR="$DEST" exec uv --no-config run python -m musicsite.app

#!/usr/bin/env bash
# Sirve el laboratorio de guitarra (S37) en la red local, solo la carpeta lab/midi/.
# Uso: lab/midi/servir.sh [puerto]   (por defecto 8090)
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8090}"
# Lee las formas de guitarra del sitio tal como están, por un enlace (ignorado por git), sin copiarlas.
ln -sf ../../src/musicsite/data/chords-guitar.json datos-chords-guitar.json
IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
echo "Laboratorio en http://localhost:${PORT}/"
[ -n "${IP}" ] && echo "Desde el celular (misma red wifi): http://${IP}:${PORT}/"
exec python3 -m http.server "${PORT}" --bind 0.0.0.0

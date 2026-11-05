#!/usr/bin/env bash
# Baja las muestras FluidR3_GM de guitarra acústica (acero y nailon) a lab/midi/muestras/, ignorada por git.
# Fuente: https://github.com/gleitz/midi-js-soundfonts (CC BY 3.0 según ese repo; licencia del .sf2 original por
# verificar, L1). Solo para el laboratorio local: no se publican ni se suben al repo (público).
set -euo pipefail
cd "$(dirname "$0")"
BASE="https://gleitz.github.io/midi-js-soundfonts/FluidR3_GM"
FLAT=(C Db D Eb E F Gb G Ab A Bb B)
for inst in acoustic_guitar_steel acoustic_guitar_nylon; do
  dest="muestras/FluidR3_GM/${inst}"
  mkdir -p "${dest}"
  for m in $(seq 40 88); do   # E2 a E6
    name="${FLAT[$((m % 12))]}$((m / 12 - 1))"
    [ -s "${dest}/${name}.mp3" ] && continue
    curl -fsS --retry 2 -o "${dest}/${name}.mp3" "${BASE}/${inst}-mp3/${name}.mp3"
  done
  echo "${inst}: $(ls "${dest}" | wc -l | tr -d ' ') notas, $(du -sh "${dest}" | cut -f1)"
done

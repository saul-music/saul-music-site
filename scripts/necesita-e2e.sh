#!/usr/bin/env bash
# ¿Este cambio necesita las pruebas de navegador del sitio? (S48)
# Uso: scripts/necesita-e2e.sh <rango de git>   (p. ej. origin/main...HEAD); imprime «true» o «false».
#
# El render (página de canción, metrónomo, guitarra) vive en la librería saul-music-render y se prueba
# allá. Un cambio que solo sube su versión (pyproject.toml y uv.lock) o solo toca documentación no
# vuelve a correr la matriz de navegadores aquí; después del despliegue se corre
# scripts/e2e-produccion.sh en local. Cualquier otro archivo, u otra dependencia, sí la corre.
set -euo pipefail
range="${1:?falta el rango de git}"
files="$(git diff --name-only "$range")"
if [ -z "$files" ]; then echo true; exit 0; fi  # sin diferencia conocida: mejor probar
while IFS= read -r file; do
  case "$file" in
    pyproject.toml | uv.lock | *.md) ;;
    *) echo true; exit 0 ;;
  esac
done <<< "$files"
# En pyproject.toml solo puede cambiar la línea de la librería de render.
if git diff "$range" -- pyproject.toml | grep -E '^[-+][^-+]' | grep -qv 'saul-music-render=='; then
  echo true; exit 0
fi
echo false

#!/usr/bin/env bash
# Pruebas de navegador del sitio contra producción, en esta máquina (S48). Se corre después de desplegar un
# cambio que no pasó por el e2e del CI (p. ej. una subida de la librería de render, scripts/necesita-e2e.sh).
# Las pruebas que arman temas propios se saltan: solo valen en local (uv run pytest -m e2e).
#
# Uso:  scripts/e2e-produccion.sh                 Chromium, Firefox, WebKit, Pixel 7 e iPhone 14
#       scripts/e2e-produccion.sh chromium        un navegador
#       E2E_BASE_URL=https://otro.sitio scripts/e2e-produccion.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PYENV_VERSION="${PYENV_VERSION:-3.14.3}" UV_PYTHON_PREFERENCE="${UV_PYTHON_PREFERENCE:-only-managed}"
export E2E_BASE_URL="${E2E_BASE_URL:-https://musicsite-ufi63f4rva-tl.a.run.app}"
echo "Contra: $E2E_BASE_URL"
run() {
  echo "== $*"
  # --no-sync: usa el entorno ya instalado (scripts/uv-acordia.sh uv --no-config sync), sin pedir el índice.
  uv --no-config run --no-sync pytest -q -m e2e -rs "$@" -p no:cacheprovider tests/e2e/test_site.py
}
fail=0
if [ $# -gt 0 ]; then
  run --browser "$1" || fail=1
else
  run --browser chromium || fail=1
  run --browser firefox || fail=1
  run --browser webkit || fail=1
  run --browser chromium --device "Pixel 7" || fail=1
  run --browser webkit --device "iPhone 14" || fail=1
fi
exit $fail

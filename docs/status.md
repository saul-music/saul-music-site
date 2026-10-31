# Estado del sitio

> Registro vivo. Última actualización: 2026-10-30.

## Paso actual

**Etapa A cerrada (2026-10-30).** El sitio se sirve desde Cloud Run, `musicsite`, en
`https://musicsite-ufi63f4rva-tl.a.run.app` (URL de `run.app`, sin dominio propio). GitHub Pages
está desactivado. Siguiente: S2 (derechos de la canción de ejemplo) antes de anunciar, y decidir la
etapa B. No se adelanta.

## Plan de la etapa A (ejecutado; PR #2)

| Archivo | Contenido |
|---|---|
| `pyproject.toml`, `uv.lock` | fastapi, uvicorn; dev: pytest, ruff, httpx2. `uv --no-config`; `grep -c artifactory uv.lock` = 0 |
| `src/musicsite/app.py` | Sirve los archivos con GET y HEAD; sin `/docs`, `/redoc`, `/openapi.json`; 404 sin cuerpo; cabeceras `nosniff`, `Referrer-Policy`, `frame-ancestors` |
| `src/musicsite/web/` | `index.html`, `cancion.html`, `guias.html`, `style.css`, `acordia.js` (`git mv`) |
| `Dockerfile` | uv fijado, solo PyPI, usuario no root; copia solo `src/` |
| `tests/test_app.py` | 200 en las 3 páginas y tipos correctos; HEAD; 404 en `/docs`, `/openapi.json`, rutas inexistentes y path traversal; cabeceras |
| `tests/test_public_content.py` | Los archivos servidos no contienen referencias a servicios internos ni a investigación; todo enlace interno resuelve |
| `bootstrap/gcp.sh`, `bootstrap/README.md` | Cuentas de servicio propias, repositorio de imágenes, WIF restringido a este repo y a `main` |
| `.github/workflows/pipeline.yml` | lint ∥ test → image → publish → deploy; acciones fijadas por SHA; prueba de humo final |
| `README.md`, `PROMPTS.md` | Rutas nuevas; se elimina `bootstrap/github-pages.sh` al final |

Orden: mergear mockups → PR de la etapa A (verde hasta `image`) → ejecutar `bootstrap/gcp.sh`
(con confirmación) → merge y despliegue → verificar URL → bajar Pages (con OK) → actualizar este
archivo y `decisions.md`.

## Criterios de aceptación

| Criterio | Estado |
|---|---|
| Pruebas y `ruff` pasan | Cumplido: 39 pruebas, ruff y format en verde en el CI (PR #2 y `main`) |
| `/`, `/cancion.html`, `/guias.html` responden 200 en la URL pública | Cumplido (comprobado con `curl` tras el despliegue) |
| `/docs` y `/dashboard/latest` responden 404 | Cumplido (`curl`) |
| `min-instances=0` y región `southamerica-west1` | Cumplido (`gcloud run services describe`: sin `minScale`, región correcta) |
| La imagen construye, sirve y arranca en Cloud Run con Python 3.14 | Cumplido: smoke del CI y del despliegue |
| Runtime sin roles, imagen con tag de git sha | Cumplido (`describe` del servicio) |
| `bootstrap/gcp.sh` recrea el entorno desde cero | **Pendiente**: se ejecutó sobre un proyecto con el pool `github` ya creado y se reintentó una vez por cuota de lecturas; no se probó en un proyecto vacío |
| Contraste, aspecto y celular | **Pendiente** (a ojo, por el usuario) |
| GitHub Pages desactivado | Cumplido (la API de Pages responde 404) |

## Puntos abiertos

1. **S2:** canción ajena en `cancion.html` se mantiene; derechos de autor pendientes antes de anunciar. La verificación global V2 (derechos de autor) se lleva en el repo de control.
2. El deployer tiene `run.admin` a nivel de proyecto (necesario para fijar la política pública), así que también podría administrar otros servicios del mismo proyecto. Riesgo aceptado como en el otro nicho.
3. Dominio propio: hoy sería una URL `*.run.app`; un dominio es una decisión aparte.
4. No anunciar el sitio antes de resolver S2 y de proteger cualquier servicio interno vinculado.
5. Etapa B (primera interacción, "pide una canción"): requiere decidir datos, almacenamiento en
   `southamerica-west1`, consentimiento, aviso de privacidad y límite de envíos. No se adelanta.

## Bitácora

```text
AAAA-MM-DD · paso · qué se hizo · qué quedó pendiente · decisiones nuevas
2026-10-30 · mockups · Acordia (index, cancion, guias) sobre Bootstrap, PR pendiente · S2 abierta
2026-10-30 · mockups mergeados · PR #1 a main; GitHub Pages desactivado por el usuario (sin URL pública hasta Cloud Run) · pendiente: despliegue · S1
2026-10-30 · código etapa A · app FastAPI, 39 tests, Dockerfile, pipeline ci→image→publish→deploy, bootstrap/gcp.sh (dry-run) en feat/cloud-run · pendiente: ejecutar bootstrap, CI, despliegue real, Python 3.14 en Cloud Run
2026-10-30 · despliegue · bootstrap/gcp.sh ejecutado en saulapp-music (un reintento por cuota de lecturas), variable GCP_WIF_PROVIDER, PR #2 mergeado, pipeline ci→image→publish→deploy verde en main, servicio musicsite en Cloud Run verificado con curl · pendiente: S2, revisión visual, bootstrap desde cero · S1
2026-10-30 · plan etapa A · decisión de desplegar en Cloud Run desde este repo y plan documentado; sin código · pendiente: aprobación del plan · S1, S2
2026-10-30 · panel de guías · rama feat/panel-profes: profes.toml (reglas por artista, tema o todo), musicsite.profes, panel en las 16 páginas de tema y guias.html generado con filtro ?tema= (216 tests, ruff limpio) · pendiente: revisión visual por el usuario, merge · S3
2026-10-30 · migración a la organización saul-music · remotos movidos; condición del proveedor WIF y binding de la cuenta del deployer cambiados a saul-music/<repo> en GCP (los dos), y GITHUB_REPO del bootstrap actualizado · pendiente: comprobar el pipeline en el repo nuevo
2026-10-30 · Cámara lenta Intermedio · notación de varios acordes por compás (F#-F#7, F#-%-F#7-B7; PR #16, 224 tests) y página regenerada con el modo Intermedio; el panel de guías (PR #14) quedó revisado y mergeado · pendiente: Avanzado de Cámara lenta, V2 (asesoría legal)
2026-10-31 · templates y metrónomo · rama feat/metronomo-templates: Jinja2 (S4), base.html y cancion.html reemplazan 16 HTML generados; songs/ con los 16 TOML publicables, comando publish; metrónomo (Web Audio, 30–240 bpm, +/-, deslizante, restablecer, pulso visual) en cada tema con bpm; 231 tests, ruff limpio · pendiente: oír el clic y revisar el pulso y el celular (usuario), PR siguiente con Playwright en matriz de navegadores · S4
```

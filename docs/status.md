# Estado del sitio

> Registro vivo. Última actualización: 2026-10-30.

## Paso actual

Mockups de Acordia listos en la rama `feat/acordia-mockups` (PR sin mergear). **Etapa A y plan aprobados
por el usuario (S1); canción de ejemplo se mantiene (S2). Aún no hay código.**

## Plan de la etapa A (rama `feat/cloud-run`, desde `main` tras mergear los mockups)

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
| Pruebas y `ruff` pasan | Pendiente |
| `/`, `/cancion.html`, `/guias.html` responden 200 en la URL pública | Pendiente |
| `/docs` y rutas ajenas responden 404 | Pendiente |
| `min-instances=0` y región `southamerica-west1` | Pendiente |
| `bootstrap/gcp.sh` recrea el entorno desde cero | Pendiente (solo dry-run al principio) |
| La imagen con Python 3.14 y FastAPI arranca en Cloud Run | Pendiente de verificación |
| Contraste, aspecto y celular | Pendiente (a ojo, por el usuario) |

## Puntos abiertos

1. **S2:** canción ajena en `cancion.html` se mantiene; derechos de autor pendientes antes de anunciar.
2. Dominio propio: hoy sería una URL `*.run.app`; un dominio es una decisión aparte.
3. No anunciar el sitio antes de resolver S2 y de proteger cualquier servicio interno vinculado.
4. Etapa B (primera interacción, "pide una canción"): requiere decidir datos, almacenamiento en
   `southamerica-west1`, consentimiento, aviso de privacidad y límite de envíos. No se adelanta.

## Bitácora

```text
AAAA-MM-DD · paso · qué se hizo · qué quedó pendiente · decisiones nuevas
2026-10-30 · mockups · Acordia (index, cancion, guias) sobre Bootstrap, PR pendiente · S2 abierta
2026-10-30 · plan etapa A · decisión de desplegar en Cloud Run desde este repo y plan documentado; sin código · pendiente: aprobación del plan · S1, S2
```

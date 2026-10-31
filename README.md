# saul-music-site

Sitio público de SAÚL música (Acordia). Servicio FastAPI en Cloud Run (`southamerica-west1`,
`min-instances=0`), desplegado desde este repo (decisión S1 en `docs/decisions.md`).

- Este repo es público: nada de datos de usuarios ni de investigación entra aquí.
- Estrategia, decisiones y verificaciones comunes de SAÚL música viven en un repo de control privado.
- Los cambios van por rama y PR hacia `main`. El pipeline es uno solo y secuencial:
  `ci` (lint y tests) → `image` → `publish` → `deploy`. Los PR terminan en `image`.
- Infraestructura manual en GCP: `bootstrap/gcp.sh` (ver `bootstrap/README.md`).
- Estado, plan y puntos abiertos: `docs/status.md`.

## Desarrollo

```bash
export PYENV_VERSION=3.14.3 UV_PYTHON_PREFERENCE=only-managed
uv --no-config sync
uv --no-config run pytest
uv --no-config run ruff check && uv --no-config run ruff format --check
PORT=8080 uv --no-config run python -m musicsite.app    # http://localhost:8080
```

## Páginas (`src/musicsite/web/`)

| Archivo | Qué es |
|---|---|
| `index.html` | Inicio de Acordia |
| `cancion.html` | Mockup de una canción de ejemplo (sin enlaces, con noindex) |
| `guias.html` | Directorio de guías (mockup) |
| `artistas.html` | Artistas del repertorio inicial, con enlace a su perfil en MusicaPopular.cl (solo enlaces, sin copiar sus textos) |
| `style.css` | Tema de marca sobre Bootstrap 5.3.3 |
| `acordia.js` | Tema, diagramas de acorde, práctica, filtro y modal |

## Páginas de canción (`templates/` y `songs/`)

Ya no hay un HTML por tema. `templates/cancion.html` (sobre `templates/base.html`, con Jinja2) se
renderiza al arrancar el servicio para cada `songs/<tema>.toml`, y se sirve en
`/cancion-<tema>.html`. Un tema que no es `publicable` rompe el arranque. Cada página con `bpm`
trae un metrónomo (Web Audio) que parte en ese tempo. Flujo del equipo editorial: validar en
`acordes-local/` y copiar los publicables con
`python -m musicsite.acordes publish --dir ../acordes-local --out src/musicsite/songs`; las
tarjetas de la Biblioteca siguen con `python -m musicsite.acordes library`.

**Todo archivo en `src/musicsite/web/` se publica.** El servidor entrega solo los archivos de esa
carpeta, por nombre exacto; un archivo nuevo ahí debe ser contenido del sitio (un test lo exige).
`PROMPTS.md` explica el sistema de diseño y trae la plantilla para páginas nuevas; no se publica.

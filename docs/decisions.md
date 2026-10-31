# Decisiones del sitio

Las decisiones no se borran: se reemplazan con una nueva que referencia la anterior.
Este repo es público: aquí no van datos de usuarios ni de investigación.

> Las decisiones **globales** de SAÚL música (M1, M2, M6, M7 y M9) viven en el repo de control
> privado, no aquí. Las del sitio (S1 y S2) se quedan completas en este archivo.

## S1 · El sitio se despliega en Cloud Run desde este repo (2026-10-30)

El sitio sigue en su propio repo (`saul-music/saul-music-site`) y deja GitHub Pages por un
servicio FastAPI en Cloud Run, público, `min-instances=0`, región `southamerica-west1`, en el mismo
patrón de CI/CD del otro nicho de SAÚL música. Decisión del usuario. **Por qué:** la interacción
futura (formularios) necesita un servidor, y así el sitio y su backend viven juntos. **Consecuencias:**
- Servicio, cuentas y recursos propios del sitio (prefijo `musicsite`), separados de cualquier
  servicio interno. El sitio no enlaza ni comparte imagen con ellos.
- Tecnología nueva en este repo: `fastapi` y `uvicorn` (ejecución); `pytest`, `ruff` y `httpx2`
  (desarrollo). Solo PyPI público.
- Pipeline único y secuencial: `lint` y `test` en paralelo; luego `image`, `publish` y `deploy`,
  cada uno con `needs` del anterior. Los PR terminan en `image`.
- Todo lo manual en GCP va a `bootstrap/gcp.sh` (idempotente, `DRY_RUN=1`).
- GitHub Pages se baja solo después de verificar la URL de Cloud Run, con aprobación explícita.
- El repo sigue público: el contenido servido no incluye datos de investigación.

## S2 · Se mantiene la canción de ejemplo, V2 sigue abierta (2026-10-30)

`cancion.html` muestra acordes y estructura de una canción ajena, marcada "Ejemplo". Publicar
acordes o letras de terceros puede requerir licencias (SCD, editores). **Decisión del usuario:** se
deja la canción actual. **Riesgo aceptado:** el contenido ya es público; no se publican letras.
**Pendiente:** resolver los derechos (reemplazar por dominio público o pieza original, o licenciar)
antes de anunciar o promocionar el sitio.

## S3 · Cada profe declara qué enseña; cada tema muestra quién puede (2026-10-30)

El modelo de oferta es `src/musicsite/profes.toml`: cada profe lista reglas explícitas de
`ensena`: un artista (todos sus temas, también los futuros), un tema puntual de ese artista, o `*`
(todo el repertorio). `musicsite.profes` las valida contra el repertorio y resuelve quién puede
enseñar cada tema. Cada página de tema lleva un panel fijo, sobre las pestañas, con cuántos guías
pueden enseñarlo y un enlace a `guias.html?tema=<slug>`. Las tarjetas de `guias.html` se generan
del mismo archivo.

**Los perfiles son mockups.** Gonzalo Pincheira y Alejandro Bustos (lo saben y lo aceptaron)
enseñan todo el repertorio, sin precio ni datos inventados; el resto lleva `mock = true` y se rotula
"Ejemplo". Nada de esto es una oferta real de clases hasta que exista el marketplace (M2, M6).

## S4 · Páginas de canción con Jinja2 y datos en git (2026-10-31)

Se agrega `jinja2` (solo PyPI). Un solo template (`templates/cancion.html` sobre `base.html`)
reemplaza los 16 `cancion-*.html` generados. Los TOML `publicable` viven en `src/musicsite/songs/`
(en git; esos acordes ya eran públicos como HTML) y el servicio los renderiza al arrancar a un
diccionario de rutas exactas, sin ruta dinámica ni recorrido de directorios. Un tema no publicable
rompe el arranque, así que el error aparece en el pipeline y no en una visita. Los borradores se
quedan en `acordes-local/` (fuera de git); se publican con `musicsite.acordes publish`.
`index.html`, `guias.html` y `artistas.html` siguen estáticos: pasar a `base.html` queda para
cuando se toquen.


## S5 · Pruebas de navegador con Playwright en matriz (2026-10-31)

Se agrega `pytest-playwright` al grupo `dev` (solo PyPI; sin Node). Los tests están en
`tests/e2e/`, marcados `e2e`: el `pytest` normal los excluye y corren con `-m e2e` contra el sitio
real levantado en un puerto libre. El pipeline suma el job `e2e` entre `ci` e `image` (D45): una
matriz con `fail-fast: false` de chromium, firefox, webkit, Pixel 7 (chromium) e iPhone 14
(webkit); la imagen solo se construye si todas pasan. Un navegador headless no oye el clic: el
sonido y la precisión del pulso se revisan a mano. Sin caché de navegadores por ahora (una acción
más que fijar); cada entrada instala solo el suyo.

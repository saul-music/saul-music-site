# Decisiones del sitio

Las decisiones no se borran: se reemplazan con una nueva que referencia la anterior.
Este repo es público: aquí no van datos de usuarios ni de investigación.

> Las decisiones **globales** de SAÚL música (M1, M2, M6, M7 y M9) viven en el repo de control
> privado, no aquí. Las del sitio (S1 y S2) se quedan completas en este archivo.

## S1 · El sitio se despliega en Cloud Run desde este repo (2026-10-30)

El sitio sigue en su propio repo (`saulapp-legal/saul-music-site`) y deja GitHub Pages por un
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

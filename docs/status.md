# Estado del sitio

> Registro vivo. Última actualización: 2026-11-05 (S36: acordes con paréntesis).

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
2026-10-31 · Playwright · rama feat/e2e-playwright: 9 pruebas de navegador (metrónomo, pestañas, tema, 404, sin desborde) en 5 configuraciones locales verdes (chromium, firefox, webkit, Pixel 7, iPhone 14); job e2e en matriz antes de la imagen · la suite halló un desborde horizontal de 15 px en celular por el panel de guías (PR #14), corregido · pendiente: ver el job e2e en verde en el CI, oír el clic · S5
2026-11-01 · metrónomo en Safari · rama fix/metronomo-safari: el audio solo sonaba en Chrome porque el primer clic se agendaba antes de que resume() terminara (reloj detenido en Safari) y iOS silenciaba Web Audio con el interruptor de silencio; ahora se espera a `running`, se reanuda si se suspende y se fija audioSession=playback; prueba e2e con contexto suspendido (falla sin el arreglo) · el usuario confirmó el sonido en Safari de Mac y en iPhone · pendiente: nada de este tema
2026-11-01 · audio real en CI · test_audio_real.py mide señal en la salida de un AudioContext real con un AnalyserNode; el pipeline arranca un sink nulo de PulseAudio (+7 s por job); 5 de 5 corridas verdes en las 5 configuraciones y, sin PulseAudio, Firefox falla con el contexto suspended (control); el pulso de test_site.py usa un contexto simulado para no depender del runner (PR #20, experimento PR #21) · pendiente: lo audible sigue siendo de oído
2026-11-01 · cursor de compases, metrónomo fijo y tipografía · rama feat/cursor-compases: los compases de la pestaña visible parpadean al pulso con flecha ▼ y contador «n / N» de repeticiones; el metrónomo queda fijo junto a los compases y las guías van arriba; acordes en Petaluma Script (SIL OFL 1.1, alojada en el sitio, CSP font-src 'self') con ♯/♭ solo al mostrar; el deslizante del metrónomo recupera una pista visible; 233 tests y 13 e2e en las 5 configuraciones · revisión visual hecha por el usuario · pendiente: S6 (SEO y medición antes de anunciar)
2026-11-02 · sin sonido, guías y %  · rama feat/sin-sonido-y-guias: «Sin sonido» sigue el tempo con reloj propio y sin tocar audioSession (recuerda la elección); franja de guías arriba que, al salir de pantalla, pasa a un botón corto en la barra fija; ambos abren un desplegable con las 5 guías mejor puntuadas (nota, cobertura del tema y precio por clase) y cada una enlaza a su tarjeta en guias.html (#guia-id, resaltada); puntuación solo en perfiles de ejemplo, las personas reales figuran como «Nuevo»; el % repite el acorde anterior atenuado; barra más compacta (sin puntos de pulso ni íconos de más) · 243 tests y 20 e2e en las 5 configuraciones · pendiente: oír el modo sin sonido en Safari/iPhone y revisar a ojo el desplegable en celular; página de perfil propia por guía (no existe), S6
2026-11-02 · diagramas de acorde · rama feat/diagramas-acordes (sin PR): cada acorde abre un panel con guitarra + tab y teclado (escritorio: cursor, foco o clic; celular: panel inferior), con «Otra forma»; formas estándar de chords-db (MIT, 893 formas vendorizadas, aviso en THIRD_PARTY_NOTICES.md) y formas propias opcionales en [intermedio.formas]/[avanzado.formas] con validación; teclado calculado con teoría propia (notas por grado); título y artista quedan fijos al bajar · 283 tests y 23 e2e en las 5 configuraciones · pendiente: revisión a ojo de los 23 acordes y del panel en Safari/iPhone (usuario), replicar la regla en el validador y el editor de research (M16), S8
2026-11-02 · lo publicado llega al sitio (rama feat/editorial-bucket, sin PR) · S9: catalog.py lee la publicación vigente del bucket editorial (puntero, relectura cada 60 s, una publicación inválida nunca reemplaza a la buena, respaldo en songs/); la Biblioteca del inicio también sale de lo publicado, con «Próximamente» solo con título y artista; bootstrap: musicsite-runtime con objectViewer en el bucket (aplicado) y volumen de solo lectura en el despliegue; 295 tests, y probado con la publicación real del bucket (16 temas, edición de dejate-caer visible) · pendiente: merge y despliegue, comprobar en producción, retirar songs/ cuando sea estable, artistas.html/guias.html siguen estáticos · S9
2026-11-02 · cuenta inicial del metrónomo (rama feat/cuenta-inicial, sin PR) · S10: 4 clics antes del compás 1, activada por defecto, botón «Cuenta inicial» para desactivarla y preferencia en localStorage; suena si hay sonido, visual en «Sin sonido»; tests de unidad y e2e · pendiente: revisión a ojo y de oído por el usuario, PR y merge, oírla en Safari/iPhone · S10
2026-11-02 · arreglo de la barra del metrónomo en escritorio (rama fix/barra-metronomo-escritorio) · el PR #26 (cuenta inicial) se mergeó con e2e firefox en rojo: en el CI de Linux la barra fija pasaba a dos filas y tapaba las pestañas (test_difficulty_tabs_switch); el despliegue no corrió; se achica el mínimo del deslizador (8 a 5 rem) y la barra vuelve a una fila · pendiente: merge y verificar el despliegue de S10
2026-11-02 · parpadeo por subdivisión (rama feat/parpadeo-subdivisiones, sin PR) · S11: en un compás con varios acordes parpadea solo la parte que suena (data-weight en .ac-part, beatTarget en acordia.js); tests de unidad y e2e en los 5 navegadores · pendiente: revisión a ojo del usuario, PR y merge · S11
2026-11-02 · partir desde un compás y compás centrado (misma rama feat/parpadeo-subdivisiones, sin PR) · S12: bandera «Partir desde aquí» en cada compás (una marca por página) y centrado del compás actual con pausa de 4 s si la persona hace scroll; tests e2e en los 5 navegadores; un test existente con igualdad exacta de flotantes se pasó a tolerancia (firefox) · pendiente: revisión a ojo y de oído del usuario, PR y merge (incluye S11) · S12
2026-11-02 · indicador de la cuenta inicial (misma rama, sin PR) · el botón principal muestra 1 2 3 4 durante la cuenta; la barra no crece · en el camino un `git checkout` del CSS borró estilos sin commit (bandera y parpadeo); se rehicieron y los tests los cubren · pendiente: revisión a ojo del usuario, PR y merge (S10, S11, S12)
2026-11-02 · tips entre secciones (rama feat/tips, sin PR) · S13: línea `> Título | Texto` en la partitura, tarjeta con ícono que brilla y se despliega, validación y límites, cursor del metrónomo las ignora; tests de unidad y e2e; guía de edición con la sección «Tips» · pendiente: revisión a ojo del usuario, PR y merge, sincronizar el validador de research para publicarlos desde el admin · S13
2026-11-02 · contrato del validador (rama feat/contrato-validador) · tests/fixtures/acordes/contract.json copiado de research (con 9 casos de tips) y tests/test_contract.py lo prueba contra musicsite.acordes: 24 casos en verde, 328 tests de unidad; si las copias divergen, falla · pendiente: PR · research M28
2026-11-02 · biblioteca por artista y buscador (rama feat/biblioteca-por-artista) · S14: orden y grupos por artista con cabecera, buscador de la portada que filtra y buscador fijo en la galería con «Limpiar búsqueda»; acordes-local sincronizado con los borradores del admin y bloque estático regenerado; 330 tests y e2e en 5 navegadores · pendiente: revisión a ojo en celular real · S14
2026-11-02 · desarrollo con lo publicado (rama feat/dev-produccion) · scripts/dev-produccion.sh: baja la publicación vigente del bucket editorial a ../acordes-produccion (fuera del repo, ignorada en el control) y arranca el sitio con EDITORIAL_DIR; probado: 17 temas, Moizefala 200, rechaza un DEST dentro del repo · pendiente: PR
2026-11-02 · acordes menores y sus4add9 (rama feat/acordes-menores) · S16: se suman m11, m69, mmaj7, mmaj7b5, mmaj9, mmaj11 y sus2sus4 (= sus4add9) a la teoría y a los diagramas; 1228 formas de chords-db (antes 893; 27 descartadas por notas ajenas), 12 tonalidades en cada menor nuevo y 11 en sus2sus4 (sin Ab); 357 tests · pendiente: PR y merge, sincronizar el validador de research (PR aparte), madd11 y m13 quedan fuera (forma propia por tema) · S16
2026-11-03 · validador de acordes menores (rama fix/validador-acordes-menores) · S16: la regex del validador rechazaba mmaj7, mmaj9, mmaj11, mmaj7b5 y mM7 en las partituras (el PR #36 solo los había sumado al dibujo); ahora se aceptan, se quitan los alias con paréntesis (m(maj7), sus4(add9)) y el contrato suma un caso · pendiente: PR gemelo en research con el mismo contrato · S16
2026-11-02 · acordes en los tips (rama feat/tips-acordes-inline) · S15: lo que va entre backticks en el título o el texto de un tip usa la fuente de acordes, escapado y sin HTML; tests nuevos · pendiente: revisar a ojo en celular · S15
2026-11-02 · niveles (rama feat/niveles-bajo-intermedio) · S17: bajos en Intermedio; `[avanzado.tabs]`, `[avanzado.arreglos]` y tips de 80/600 en Avanzado; 370 tests, contrato ampliado · pendiente: revisar en celular real, publicar un tema con estos campos desde el admin
2026-11-03 · casillas anchas (rama fix/compas-ancho-con-bajos) · S18: compases con 3+ acordes o nombres largos ocupan dos columnas (la fila en celular); arregla el desborde de «Moizefala» en Intermedio; 380 tests · pendiente: revisar a ojo en celular real
2026-11-03 · guitarra con bajo (rama feat/guitarra-slash-chords) · S19: forma de chords-db con bajo (G/B), o el acorde base sin el bajo con aviso en el panel; 388 tests; comprobado en navegador con Moizefala · pendiente: visto bueno a ojo, aclarar el origen de chords-guitar.json (no coincide con 0.5.1 de jsDelivr)
2026-11-03 · Biblioteca por versiones (rama feat/biblioteca-por-versiones) · S20: dentro de cada artista, primero el tema con más versiones (Básico, Intermedio, Avanzado con compases), luego por título; «Próximamente» al final; 390 tests · pendiente: visto bueno a ojo, PR
2026-11-03 · acordes add#11 y madd#11 (rama feat/acorde-add-sostenido-11) · S21: el sitio sabe sus notas y dibuja el teclado (Dmadd#11 = D F A G#); sin guitarra estándar (forma propia); validadores sin cambios · pendiente: visto bueno, PR
```
2026-11-03 · silencios en producción · site: el punto `.` es un silencio (S22 del site, M36 de research; PR #43 y #42), probado en navegador y desplegado por pipeline · pendiente: probar con login real escribir un silencio, publicar y verlo en el sitio · S22, M36
2026-11-03 · catálogo sin Los Jaivas, Congreso ni Subhira (rama fix/quitar-jaivas-congreso-subhira, PR #45) · se quitan 5 temas (2 publicados: Corre que te pillo y Takirari del Puerto), sus fichas en artistas.html, la Biblioteca y la regla de guía; REPERTOIRE pasa a 15 temas y los publicados a 14 · pendiente: publicar un release nuevo desde el admin y borrar sus borradores en GCP
2026-11-03 · acorde mMaj7 (rama fix/acorde-mmaj-y-combos-anchos) · el validador y el teclado aceptan «DmMaj7» como alias de mmaj7 (antes solo mmaj7 y mM7); el contrato se copió de research

## 2026-11-04 · Sección Artistas (S24)

- `artists.json` del release (fallback a los datos estáticos), enlaces externos en pestaña nueva, conteo de temas publicados y
  «Ver sus temas en la Biblioteca» (`?q=`). Pruebas: `tests/test_artists.py` y 4 de navegador. Detalle en `decisions.md` (S24).
- **Pendiente:** revisar a ojo en celular real; probar con un `artists.json` real cuando el admin lo publique.

## 2026-11-04 · Mockups de pedidos y opinión (S25)

- `pedidos.html`/`pedidos.js`: demo sin envío con pedidos ficticios que cambian de estado; adaptador `createSource()` listo para una fuente real.
  Pruebas: `tests/test_pedidos_demo.py` y 4 de navegador (reloj simulado, reduced-motion, sin envío, sin desborde). Revisado a 360 px en captura.
- **Pendiente:** revisar a ojo en celular real y en claro/oscuro; elegir backend (etapa B) antes de conectar nada.

## 2026-11-04 · Orden de formas de guitarra: cejilla y forma por defecto del tema (S27)

- Regla de cejilla (formas estándar desde el traste 3 se ordenan por traste base) y tabla `[formas]` por tema, que vale para los tres
  niveles; precedencia: forma del nivel (S8) > `[formas]` > cejilla > chords-db. Validador, plantilla simple, contrato compartido
  (11 casos) y guía de edición actualizados. **Research debe copiar `tests/fixtures/acordes/contract.json` y soportar `[formas]`.**
- Pruebas: puras (regla, validador, payload) y de navegador (default primero, propia del nivel gana, navegación).
- **Pendiente:** verificar en producción tras el deploy; ningún tema publicado usa `[formas]` todavía.


## 2026-11-04 · Selector de nivel y barra plegable en celular (S26)

- Selector de nivel con borde visible y activa destacada (claro/oscuro, foco accesible); en <= 575 px los controles secundarios
  de la barra van bajo «Opciones» (plegable, `aria-expanded`); escritorio igual. Detalle en `decisions.md` (S26).
- Pruebas: 6 de navegador nuevas (borde, contraste en ambos temas, plegado, Escape con el metrónomo andando, sin desborde, capturas
  con `AC_SHOTS=<carpeta>`); las existentes abren el grupo con `set_options()`. Capturas revisadas en Pixel 7 y iPhone 14.
- **Pendiente:** revisar a ojo en celular real; el botón «Opciones» no indica si «Sin sonido» está activo mientras está plegado.

## 2026-11-04 · Resumen plegado de posiciones (S28)

- `<details>` cerrado al inicio de cada pestaña con guitarra y piano de sus acordes, con la forma que verá el usuario al tocarlos.
  Pruebas de navegador: cerrado por defecto, un diagrama por acorde, forma por defecto del tema, sin desborde.
- **Pendiente:** revisar a ojo en celular real y en claro/oscuro.


## 2026-11-04 · Barra en dos filas, sin aviso de guías (S30, reemplaza a S29)

- El usuario rechazó el aviso: se quita por completo (HTML, CSS, JS, pruebas). Niveles arriba y controles abajo; queda una prueba de
  orden de filas. Se conservan el borde del selector (S26), «Opciones» en celular y «Habla con una guía».
- **Pendiente:** revisar a ojo en celular real.


## 2026-11-04 · Avanzado hereda Intermedio (S31, reemplaza parte de S17)

- Avanzado ya no tiene partitura: muestra la de Intermedio y suma extras por sección en `[avanzado.secciones."Nombre"]` (`tab`, `arreglo`, `tips`).
  `[avanzado.tabs]`, `[avanzado.arreglos]` y `[avanzado] partitura` dan un error de migración. `[avanzado.formas]` y `tab` general se conservan.
- Validador, render (`songpages.py`), plantillas, guía de edición (control) y contrato compartido actualizados (24 casos nuevos). Formato exacto y
  mensajes de error: `docs/decisions.md` S31. Pruebas: pytest, ruff y e2e con un tema sintético con Avanzado.
- **Para research:** copiar `contract.json`, adaptar validador y editor, y correr `scripts/sync_site_render.py` para la copia del render.
- Ningún tema publicado usa Avanzado: sin migración.



## 2026-11-04 · Aviso de «Sin sonido» y timeouts (S32)

- «Opciones» (celular) muestra un ícono de silencio y `aria-label`/`title` «sin sonido activado» mientras el modo está activo; prueba e2e en Pixel 7 e iPhone 14 con captura revisada.
- `timeout-minutes` en todos los jobs (e2e 20, resto 10) medido con los últimos 12 runs; pipeline sigue secuencial. Detalle: `docs/decisions.md` S32.

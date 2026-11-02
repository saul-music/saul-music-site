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

## S6 · No se sale al mercado sin SEO ni medición listos (2026-11-01)

**Decisión del usuario:** el sitio todavía no sale al mercado y **no puede anunciarse ni promocionarse**
mientras no estén hechos el trabajo de SEO y la medición de accesos. Se hará más adelante; esta
decisión fija que es requisito de salida, junto a V2/S2 y M13.

**Hoy (diagnóstico del 2026-11-01):** el HTML de cada tema sale completo desde el servidor (Jinja2), así
que el renderizado no perjudica. Falta lo que lo rodea: sin `robots.txt` ni `sitemap.xml`; la
descripción es la misma frase en todos los temas; sin `canonical`, Open Graph ni datos
estructurados; contenido delgado (casi solo la grilla de acordes, sin letras por D-C15); URL
`run.app` sin dominio propio; aviso «Prototipo» en todas las páginas.

**Requisitos de SEO antes de salir:**
1. Dominio propio decidido primero (sitemap y canonical llevan URLs absolutas; cambiarlo después
   exige redirecciones).
2. `sitemap.xml` generado desde `songs/` solo con los temas publicados, y `robots.txt` que lo apunte:
   un tema nuevo entra solo.
3. Título y descripción únicos por tema, más `canonical`, Open Graph y JSON-LD (`MusicComposition`).
4. Contenido propio por tema (sin letras ni acordes copiados), temas relacionados y enlace desde la
   ficha del artista.
5. Prueba automática: cada tema publicado está en el sitemap y tiene título y descripción únicos.
6. Retirar o reformular el aviso «Prototipo» al salir.

**Requisitos de medición (listos antes del anuncio, para tener línea base):**
- **Google Search Console:** dominio verificado y sitemap enviado.
- **Analítica de accesos** activa. **Herramienta sin decidir** (Google Analytics u otra): al elegirla
  se registra como decisión nueva. Condiciones: aviso de privacidad y consentimiento (Ley 21.719), CSP
  del sitio ajustada (hoy solo permite jsDelivr y Google Fonts), ningún dato personal en el repo
  público (M9) y revisar la regla de datos solo en `southamerica-west1` si la herramienta los envía
  fuera de Santiago.

**Estado:** no iniciado. Plan y aprobación explícita antes de cualquier código.

## S8 · Diagramas de acorde: forma estándar de chords-db y formas propias opcionales (2026-11-02)

Cada acorde de la página de canción abre un panel (al pasar el cursor, al enfocar o al tocar; panel
inferior en celular) con la forma de guitarra y su tab de texto, y el teclado. **Escribir un tema no
pide formas:** cada acorde usa la forma estándar. Las formas vienen de *chords-db* (MIT), recortadas a
`data/chords-guitar.json` (893 formas; se descartaron 21 que sonaban notas ajenas) con el aviso en
`THIRD_PARTY_NOTICES.md`; no hay dependencia en tiempo de ejecución ni red (política L1, control).

**Formas propias, opcionales y solo en Intermedio y Avanzado:** `[avanzado.formas]` o
`[intermedio.formas]`, p. ej. `"Cmaj7" = "x 3 2 0 0 0"` (trastes de la 6ª a la 1ª cuerda; `x` = no
suena). El validador exige 6 valores (0 a 24), un acorde que aparezca en esa versión y que solo suenen
notas del acorde (con bajo `G/B`, la nota más grave debe ser el bajo). El Básico no admite formas. La
forma propia se muestra primero en su versión, con la etiqueta «Forma de esta versión»; las estándar
siguen con «Otra forma».

**El teclado se calcula** con teoría propia (`chordtheory.py`, notas escritas por grado: Cm = C Eb G),
sin datos de terceros. Un acorde sin forma disponible (`G/B`, extensiones raras) muestra el teclado y
«Sin diagrama de guitarra»; no se inventan formas. No incluye ukelele ni dedos propios.

**Pendiente en research (M16):** replicar la regla en la copia del validador (test de contrato) y
sumar al admin una sección opcional «Formas específicas» en Avanzado. Lo revisa un guitarrista: las
formas estándar de los 23 acordes del repertorio, y una propia de ejemplo.

## S9 · El sitio muestra lo publicado desde el admin, con `songs/` como respaldo (2026-11-02)

Aplica la decisión M17 del control. Con `EDITORIAL_DIR` (el bucket `saulapp-music-editorial` montado de
**solo lectura** en Cloud Run), las páginas de canción **y la Biblioteca del inicio** salen de la
publicación vigente que dejó el admin (`current.txt` → `releases/<versión>/`), no de `songs/` en git.
Reemplaza en parte S4 (datos en git).

- **Mismo servicio, sin tecnología nueva:** `musicsite.catalog.Catalog` lee archivos del volumen
  montado; no hay librería de Google Cloud ni credenciales en el código.
- **Relectura cada 60 s** (`EDITORIAL_REFRESH_SECONDS`): publicar aparece en el sitio en ese plazo más
  los 5 minutos de caché del navegador (`max-age=300`). No hace falta desplegar ni reiniciar.
- **Una publicación que no sirve nunca reemplaza a la buena:** un tema no publicable, un nombre de
  archivo fuera de `[a-z0-9-]`, una publicación vacía o un error de lectura se descartan y se sigue
  mostrando lo anterior (la descartada por datos no se reintenta hasta que cambie el puntero). El
  puntero nunca sale de `releases/`.
- **Respaldo:** al arrancar sin publicación válida (bucket vacío, puntero roto, montaje caído) se usa
  `songs/` de git, y la Biblioteca estática de `index.html`. Un dato malo en `songs/` sigue rompiendo
  el arranque (S4). **`songs/` se retira de git cuando esta vía lleve un tiempo estable.**
- **Lo publicado reemplaza, no se mezcla:** un tema que está en git pero no en la publicación
  vigente no se muestra.
- **Biblioteca:** el repertorio inicial va primero en su orden; los publicados con su tarjeta completa;
  los del repertorio aún no publicados como «Próximamente» **solo con título y artista** (antes
  mostraban los acordes de sus borradores); los temas nuevos fuera del repertorio, al final por
  título. `acordes library` sigue sirviendo para regenerar el HTML estático de respaldo.
- **Permisos (D56):** `musicsite-runtime` recibe solo `roles/storage.objectViewer` en el bucket editorial
  (`bootstrap/gcp.sh`). No ve los borradores ni los datos de research.
- **Frontera M9:** nada del bucket entra a git. El bucket lleva solo temas ya publicables.
- **No cubre:** las fichas de `artistas.html` y los perfiles de `guias.html` siguen estáticos (un
  artista nuevo no aparece solo); el `sitemap.xml` por tema es parte de S6.


## S10 · Cuenta inicial del metrónomo, activada por defecto (2026-11-02)

Al reproducir un tema suenan **4 clics de cuenta** (el primero acentuado) antes del compás 1. Durante la
cuenta los puntos de pulso parpadean y el cursor de compases no avanza. Suena si el sonido está activado;
en «Sin sonido» es solo visual.

- **Activada por defecto**; el botón «Cuenta inicial» la desactiva. La elección se guarda en
  `localStorage` (`acordia-cuenta-inicial`), como «Sin sonido»; si falla, la página sigue funcionando.
- Siempre son 4 clics, sea cual sea el compás. Solo se hace al iniciar: cambiar el bpm o el sonido
  mientras suena no la repite.
- Sin tecnología nueva ni cambios de servidor: solo `acordia.js`, la plantilla y el CSS.

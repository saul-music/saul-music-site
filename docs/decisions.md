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

## S11 · El parpadeo del pulso sigue el acorde dentro de un compás partido (2026-11-02)

En una casilla con varios acordes (`F#-F#7`, `F#-%-F#7-B7`), cada pulso ilumina solo la parte (`.ac-part`)
cuyo acorde está sonando, no la casilla entera. Una casilla con un solo acorde no cambia.

- Cada parte lleva `data-weight` con su duración; el pulso `p` del compás cae en la parte que contiene
  la posición `floor(p × total / pulsos)`. En 4/4, `F#-%-F#7-B7` ilumina F# dos pulsos, F#7 uno y B7 uno.
- Si los trozos no dividen exacto los pulsos (3 trozos en 4/4), la primera parte recibe más pulsos.
- El acento del primer pulso cae sobre la parte que lo contiene. Marco, flecha, contador y cuenta
  inicial (S10) no cambian. Sin tecnología nueva.

## S12 · Partir desde cualquier compás y compás actual centrado (2026-11-02)

- **Bandera de inicio:** cada compás tiene un botón «Partir desde aquí» (esquina superior izquierda; visible
  al pasar el cursor o con foco, y siempre atenuado en pantallas táctiles). Hay una sola marca por página;
  tocar la misma bandera la quita. «Reproducir» (con su cuenta inicial) parte de ese compás, en la primera
  pasada de su sección; «Detener» no borra la marca. Si la marca no está en la pestaña visible, se parte del
  primer compás. No se guarda en `localStorage`. Las banderas las agrega `acordia.js`; el HTML generado no cambia.
- **Centrado:** mientras suena, el compás actual se mantiene centrado entre la barra fija y el borde de la
  ventana (antes solo se movía la página si el compás salía de pantalla). Scroll suave, o instantáneo con
  movimiento reducido. Un scroll manual (rueda, dedo o teclado) pausa el seguimiento 4 segundos.
- Sin tecnología nueva.
- **Indicador de la cuenta inicial (S10):** mientras cuenta, el botón principal muestra «1 2 3 4» con el
  número actual resaltado, en vez de «Reproducir/Detener». Va dentro del botón para que la barra fija no
  crezca (un elemento aparte la pasaba a dos filas). También en «Sin sonido». Los números solo existen en el
  DOM durante la cuenta.

## S13 · Tips o consejos entre secciones de la partitura (2026-11-02)

Una línea `> Título | Texto` dentro de la `partitura` (de cualquier versión) es un tip que se muestra donde se
escribe: al inicio o entre secciones. Cerrado muestra el ícono de destello que brilla, la etiqueta «Tip» y el
título gancho; al tocarlo (o con Enter/Espacio) se despliega el texto.

- **Límites:** título hasta 60 caracteres, texto hasta 280, ambos obligatorios; el texto siempre se escapa.
- **No son compases:** el cursor del metrónomo, el conteo de compases y los acordes usados los ignoran.
- **Brillo:** se apaga con `prefers-reduced-motion` y, una vez abierto, el tip deja de brillar (se recuerda
  en `localStorage` por contenido; si falla, simplemente vuelve a brillar).
- **Sin tecnología nueva** ni formato nuevo: reutiliza la `partitura`. Los temas sin tips no cambian.
- **Pendiente (research):** el validador del admin es una copia y rechazaría estas líneas; hay que
  sincronizarlo (con el contrato) antes de publicar tips desde el admin. Fuera de alcance de este paso.


## S14 · Biblioteca ordenada y agrupada por artista, con buscador propio (2026-11-02)

- **Orden:** por artista sin tildes ni mayúsculas e ignorando el artículo inicial (Los/Las/La/El: «Los Bunkers»
  va en la B), y dentro del artista por título. Los «Próximamente» y los temas nuevos se mezclan por su
  artista; ya no van al final. Lo hace `songpages.render_library`, igual para el bloque estático y el
  publicado.
- **Grupos:** cada artista abre con una cabecera de ancho completo (nombre, «N temas» y una línea). El artista
  pasa a `h3` y el título de cada tarjeta a `h4`.
- **Buscador:** el de la portada dejó de ser un prototipo. Filtra las tarjetas por título o artista (sin
  tildes ni mayúsculas, todas las palabras) en el navegador, sin servidor. La galería tiene su propio campo,
  fijo bajo la barra, con contador y «Limpiar búsqueda»; el de la portada pasa su texto a ese campo y se
  vacía al buscar, para que el texto viva en un solo lugar.
- **Sin tecnología nueva.** `artistas.html` queda fuera de alcance.
- **Se comprueba:** pruebas de unidad del orden y de las cabeceras, y dos e2e del buscador (5 navegadores).
- **Secciones importantes con más presencia, sobrio (mismo PR):** la Biblioteca del home es una banda con
  tinte dorado leve y bordes de 2 px arriba y abajo; en cada tema, cada sección de compases (Intro, Estrofa…)
  es un panel con borde, fondo propio y barra dorada a la izquierda (`.ac-score`). Solo CSS y una clase;
  funciona en oscuro y claro. Regla: lo que más importa se destaca así, sin colores nuevos.

## S15 · Nivel en la barra de reproducción, en la URL, y final de la pasada (2026-11-02)

- **Selector de nivel en la barra.** Básico, Intermedio y Avanzado pasan a la tarjeta del metrónomo (fija al
  bajar) y se quitan las píldoras de debajo: un solo control, sin duplicados. En un tema sin bpm no hay
  barra y las píldoras siguen en su lugar. Se puede cambiar de nivel en cualquier momento, también sonando:
  el pulso no se corta, el cursor sigue en el mismo número de compás del panel nuevo y la bandera de
  partida pasa con él. Si un nivel tiene menos compases que otro, el cursor da la vuelta; si está en
  «Próximamente», no hay cursor.
- **Nivel en la URL.** `#basico`, `#intermedio` y `#avanzado` (en español, sin tildes). Cambiar de nivel
  actualiza el hash con `history.replaceState` (sin llenar el historial ni mover el scroll); abrir un enlace
  con hash abre ese nivel, uno desconocido cae en Básico y `hashchange` se escucha.
- **Final de la pasada.** Al sonar el último pulso del último compás (última repetición; desde la bandera, si
  hay una) se detiene todo, no queda ningún compás marcado (ni cursor ni bandera de partida) y
  «Reproducir» es reemplazado por «Volver al inicio». Ese botón solo lleva el scroll, directo, al primer
  compás del nivel visible: no reproduce. Se oculta al cambiar de nivel o mover la bandera.
- **Sin tecnología nueva.** Bootstrap Tab y JS propio; sin dependencias.
- **Se comprueba:** 4 pruebas e2e nuevas (selector único y hash, hash al cargar, final y reinicio sin sonido,
  cambio de nivel sonando) en chromium y iPhone 14. Pendiente: oírlo y verlo en Safari/iPhone real.


## S15 · Acordes entre backticks dentro de un tip (2026-11-02)

En el título y el texto de un tip, lo que va entre `` ` `` (por ejemplo `` `C#m7b5` ``) se dibuja con la fuente de
acordes (Petaluma Script) y sin los backticks. Igual en la vista previa del admin (research M33).

- **Seguro:** el texto se escapa primero y solo después se envuelve en `<span class="ac-inline-chord">`; no se acepta HTML.
- **Sin pareja:** un backtick suelto queda como texto. Los límites de 60 y 280 caracteres cuentan lo escrito, con backticks.
- **Sin formato nuevo:** es solo presentación; el validador no cambia y los tips existentes se ven igual.

## S16 · Todos los acordes menores de chords-db y sus4add9 (2026-11-02)

El sitio reconocía seis menores (`m`, `m6`, `m7`, `m7b5`, `m9`, `madd9`). Se suman los que chords-db 0.5.1
trae y faltaban: `m11`, `m69`, `mmaj7` (alias `mM7`, `m(maj7)`), `mmaj7b5`, `mmaj9` y `mmaj11`, más
`sus2sus4` (alias `sus4add9`, `sus4(add9)`). Cada uno tiene formas en las 12 tonalidades, salvo `sus2sus4`,
que no trae `Ab`. Se volvió a vendorizar con el mismo origen y la misma regla (`position_ok`): 1228 formas, 27
descartadas por sonar notas ajenas. **Fuera, a propósito:** `madd11` y `m13` (chords-db no los trae y se usan
poco): se escriben con la forma propia por tema (S8). Los slash chords menores no se importan: el bajo ya lo
resuelve `Chord.bass`. **Pendiente:** replicar los sufijos en el validador de research (M16).

## S17 · Bajos en Intermedio; tabs, arreglos y tips largos por sección en Avanzado (2026-11-02)

- **Intermedio** acepta bajos e inversiones (`G/B`, `Am7/G`), además de las extensiones. Básico no cambia.
  El Avanzado sigue aceptando todo lo del Intermedio.
- **Avanzado** se distingue por contenido, no por acordes: `[avanzado.tabs]` y `[avanzado.arreglos]`
  (clave = nombre de una sección de su partitura; tab hasta 2000 caracteres, arreglo hasta 600; se muestran
  dentro de la sección, la primera vez que aparece), y tips de hasta 80/600 caracteres (Básico e Intermedio:
  60/280). El `tab` general se conserva.
- El validador comprueba que el nombre exista, que sea texto no vacío y los límites; todo se escapa (el arreglo
  admite acordes entre acentos graves, como los tips, S15).
- Sin sintaxis ni tecnología nuevas. **Descartado:** tips de varias líneas (la partitura es una línea por
  elemento); se amplió el límite en su lugar. Contrato actualizado (`contract.json`); research debe copiarlo (M34).


## S18 · Casillas anchas para compases con muchos acordes o bajos (2026-11-03)

En «Moizefala» (Intermedio), un compás como `Dmaj7-Em7/B-F#m7/A-D6/F#` desbordaba su casilla (un cuarto de la fila).
- **Regla** (`songpages.is_wide`): una casilla con **3 o más acordes distintos**, o con **10 o más letras** de acordes
  sumadas, ocupa **dos columnas** (`is-wide`; en celular, la fila completa). Un solo acorde largo (`Gmaj7/A`) no cambia.
- **Ancho de cada acorde:** en las casillas anchas parte de su propio ancho y el sobrante se reparte por duración
  (`%` sigue alargando). En celular la letra baja a `min(1.2rem, 4.4vw)` solo ahí.
- Comprobado en navegador con el tema publicado a 1100, 390 y 360 px: ninguna casilla desbordada. Sin formato nuevo;
  el cursor del metrónomo y el conteo de compases no cambian.

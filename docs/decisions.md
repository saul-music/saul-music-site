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
trae y faltaban: `m11`, `m69`, `mmaj7` (alias `mM7`), `mmaj7b5`, `mmaj9` y `mmaj11`, más
`sus2sus4` (alias `sus4add9`). Cada uno tiene formas en las 12 tonalidades, salvo `sus2sus4`,
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

## S19 · Guitarra para acordes con bajo: forma con bajo, o el acorde base sin el bajo (2026-11-03)

Hasta S18, cualquier acorde con bajo (`G/B`, `Em7/B`) abría el panel solo con teclado. Ahora la guitarra se
resuelve en este orden (`chordtheory.guitar_positions`):
1. **Forma propia** del tema (`[intermedio.formas]`, S8): sigue mandando sobre todo.
2. **Forma de chords-db con ese bajo** (`G/B`, `D/F#`, `C/E`…): 48 entradas nuevas en `chords-guitar.json`, claves
   `«major/11»` (sufijo y clase del bajo). Solo entran las que `check_shape` acepta (sin notas ajenas y con el bajo
   como nota más grave); 2 se descartaron.
3. **Acorde base** (`Gmaj7/B` → `Gmaj7`): primero las formas cuya nota más grave ya es el bajo (esas sí lo
   dibujan); si ninguna lo es, todas, **sin el bajo**.
4. Sin acorde base con diagrama: «Sin diagrama de guitarra», como antes.
- **Aviso:** cuando el bajo no está dibujado, el panel dice «Diagrama de Gmaj7. El bajo (B) no está dibujado:
  míralo en el teclado.» (`guitar_note` en el payload). El teclado no cambia: ya marca el bajo.
- **Datos:** `python -m musicsite.chordsdb vendor guitar.json --only-slash` agrega las formas con bajo sin tocar lo
  ya vendorizado.
- **Hallazgo de procedencia (pendiente):** el `chords-guitar.json` publicado **no coincide** con el `guitar.json` de
  `@tombatossals/chords-db@0.5.1` en jsDelivr: ahí no existe `sus2sus4` y algunas formas difieren (p. ej. una
  de `C`). Los datos de S16 vienen de otra fuente o versión que `fuente` nombra como 0.5.1. No cambia nada hoy (por eso
  `--only-slash` no regenera), pero hay que aclarar el origen y corregir `THIRD_PARTY_NOTICES.md` si corresponde (L1).
- **Fuera de alcance:** `G7b9` (sin bajo, no está en chords-db): forma propia por tema.

## S20 · En la Biblioteca, dentro de cada artista, primero el tema con más versiones (2026-11-03)

Los artistas siguen en orden alfabético (sin artículo ni tildes, S14). Dentro de cada artista el orden pasa a ser
**más versiones primero**, y a igualdad de versiones, por título.
- **Versiones** (`songpages.version_count`): cuántos de Básico, Intermedio y Avanzado tienen al menos un compás
  (0 a 3). Un nivel que solo trae tips no cuenta. Un tema «Próximamente» vale 0 y queda al final de su artista.
- **Empates:** alfabéticos; Avanzado no pesa más que Intermedio.
- Un tema publicado sin base armónica (p. ej. un tema sin compases) también vale 0: sale tras los que tienen
  acordes y antes de los «Próximamente» solo por orden alfabético entre ceros.
- No cambia el buscador, los contadores por artista ni el HTML de las tarjetas; no hay indicador visual de versiones.
## S21 · Acordes `add#11` y `madd#11` (2026-11-03)

Se escriben **sin paréntesis**: `Dmadd#11` (D F A G♯) y `Dadd#11` (D F♯ A G♯). El validador del site y el del admin de
research ya los aceptaban (`add` + `#11`); lo que faltaba era que el sitio supiera sus notas.
- **Teoría** (`chordtheory`): sufijos `add#11` (0, 4, 7, 18) y `madd#11` (0, 3, 7, 18), con la #11 escrita como cuarta
  aumentada (G♯ en Re). Dan el nombre de las notas y las teclas del piano.
- **Guitarra:** chords-db no trae ningún sufijo `#11`, así que no hay forma estándar («Sin diagrama de guitarra»); se
  escribe una forma propia por tema (`[intermedio.formas]`), que ya valida que solo suenen notas del acorde.
- **Con paréntesis** (`Dm(add#11)`) sigue sin aceptarse: cambiaría el patrón de acordes en los dos repos y el contrato
  por un solo acorde. **Descartado por ahora:** `add11` natural (`Dmadd11`) y `m7#11`.

## S22 · Silencios en la partitura: el punto `.` (2026-11-03)

Un silencio se escribe `.`, solo o dentro de un compás partido. Se eligió el punto por ser un carácter, fácil de teclear
(también en celular) y imposible de confundir con un acorde; `~` y `sil` se descartaron.
- **Compás entero:** `Estrofa: G % . Em`. **Dentro de un compás:** `G-.`, `.-G`, `G-%-.` (G tres partes, silencio una);
  `%` después de un silencio lo alarga (`.-%-G`).
- **`%` solo no repite un silencio** (error claro): no hay acorde que repetir. Una sección entera de silencios es válida.
- Funciona igual en Básico, Intermedio y Avanzado. No es un acorde: no exige estar en la lista de acordes ni lleva diagrama.
- **En el sitio:** símbolo de silencio de negra (SVG, no depende de la tipografía) tenue y sin botón, con
  `aria-label="silencio"`. En Cámara lenta y el metrónomo dura lo que dura su parte y el pulso lo ilumina como a un acorde.
- **Contrato compartido** (`tests/fixtures/acordes/contract.json`): 8 casos nuevos, idénticos en research (M36).

## S23 · Contador de temas publicados en la portada (2026-11-04)

La portada dice «N canciones disponibles con acordes, gratis» bajo el subtítulo del hero.
- **Qué cuenta:** solo los temas publicados (tarjetas con enlace de la Biblioteca); los «Próximamente» no. 1 va en singular.
- **Cómo:** marcas `<!-- temas:inicio -->`/`<!-- temas:fin -->` en `index.html`; `apply_library` actualiza el número a la vez
  que la Biblioteca, así que sigue a lo publicado en el bucket (también al despublicar). Sin marcas, no cambia nada.
- El `index.html` estático lleva el número de sus propias tarjetas (respaldo de git).

## S24 · Sección Artistas: `artists.json` del release, enlaces externos y conteo de temas (2026-11-04)

- **Datos:** `artistas.html` lleva solo las marcas `<!-- artistas:inicio/fin -->`; `musicsite.artists` arma el bloque. Los artistas
  salen de `artists.json` en el release vigente del bucket editorial, junto a `index.json`:
  `{"format":1,"artists":[{"slug","name","description","links":[{"label","url"}]}]}`. Se lee con la misma mecánica que S9
  (con la publicación, relectura cada 60 s, una publicación nunca rompe la anterior). **Respaldo:** `FALLBACK` en `artists.py`
  (los 4 artistas de siempre) si el archivo no existe o no sirve; también en el modo `songs/` de git.
- **Validación:** `format` = 1; 1 a 200 artistas; `slug` en minúsculas con guiones y sin repetir; nombre 1 a 80; descripción
  ≤ 1500; hasta 10 enlaces por artista, con `label` de 1 a 100 y URL http/https absoluta (≤ 500, sin espacios). Un artista
  mal formado o un archivo roto invalida todo el archivo (se usa el respaldo); **un enlace inválido solo se descarta**. Todo se escapa
  (sin HTML en descripciones).
- **Enlaces externos:** `target="_blank" rel="noopener noreferrer"` más texto oculto «(se abre en otra pestaña)».
- **Conteo:** cuenta los temas publicados del release (igual que S23); un tema «Artista (versión)» cuenta para «Artista». Sin
  temas: «Próximamente». Con temas: lista de títulos con enlace y botón «Ver sus temas en la Biblioteca».
- **`?q=`:** `index.html?q=Nombre#biblioteca` llena el buscador de la galería (S14) y deja la Biblioteca a la vista; el valor se asigna
  como texto, nunca como HTML, y se recorta a 100 caracteres.
- **Sin cambio de contrato:** el sitio ignora campos desconocidos de `artists.json`; no lee `index.json` para esto.

## S25 · Mockups de «Pide una canción» y opinión, solo front (2026-11-04)

- `pedidos.html` + `pedidos.js` (en la nav y el pie de todas las páginas): formulario de pedido (canción, nivel, correo opcional),
  lista de pedidos públicos ficticios con estados Recibida → En revisión → En preparación → Publicada, y formulario de opinión.
  **Ningún formulario envía ni lee nada** (sin `action`, `preventDefault`, aviso visible); sin red, sin almacenamiento y sin dependencias.
- **Rotulado:** insignia «Demo / datos de ejemplo» en el encabezado, en cada sección y en cada pedido; `noindex`. Datos sintéticos:
  títulos del repertorio público o genéricos «(ejemplo)», sin nombres, correos (solo el placeholder `tucorreo@ejemplo.com`), letras ni acordes.
- **Tiempo real simulado:** cada 5 s avanza un pedido (los publicados salen y entra uno nuevo como Recibida), con barra y destello suaves;
  `prefers-reduced-motion` quita transiciones y destello; un `aria-live` discreto anuncia el cambio.
- **Adaptador:** la lista solo conoce `createSource()` -> `subscribe(onChange) -> unsubscribe`, con la lista completa en cada cambio.
  Hoy `DemoSource`; **ahí se conecta Firebase Realtime Database en la etapa B** (decisión aparte, no se agrega ahora). Lo real
  deberá, además, cambiar la CSP (`connect-src`, `form-action`) y el aviso de privacidad; nada de eso se adelanta.
- No es la etapa B ni se anuncia el sitio (S6 sigue pendiente).

## S27 · Orden de las formas de guitarra: regla de cejilla y forma por defecto del tema (2026-11-04)

Orden en que el panel de acorde ofrece las formas de guitarra (la primera es la que se ve al tocar el acorde; «Otra
forma» recorre el resto):
1. **Forma propia del nivel** (`[intermedio.formas]` o `[avanzado.formas]`, S8), etiqueta «Forma de esta versión».
2. **Forma por defecto del tema** (`[formas]`, abajo), etiqueta «Forma de este tema».
3. **Regla de cejilla:** formas estándar de chords-db reordenadas.
4. El resto de chords-db en su orden. Una forma repetida (mismos trastes) se muestra una sola vez.

**Regla de cejilla** (`chordtheory.nearest_barre_first`, constante `BARRE_FROM_FRET = 3`): *traste base* = traste más bajo
que se pisa (los aires y las cuerdas mudas no cuentan; 0 si no se pisa ninguno). Si la **primera** forma de chords-db tiene
traste base >= 3, todas se ordenan por traste base ascendente; **empate: se conserva el orden de chords-db**. Si la primera
empieza antes del traste 3 (abierta o cejilla baja) no se toca nada. Se aplica también a las formas con bajo y a las del
acorde base (S19). Afecta a 44 acordes de chords-db (p. ej. Cm7: la cejilla del traste 1 sale antes que la del 8).

**Contrato del campo por defecto** (compartido con research, `tests/fixtures/acordes/contract.json`, 11 casos nuevos):
- **Tabla TOML de primer nivel `[formas]`**, hermana de `[intermedio]`/`[avanzado]` (antes el validador rechazaba una
  clave `formas` suelta; ahora es esta tabla). Una sola lista para los tres niveles.
- **Formato:** `"<acorde>" = "<6 valores>"`, igual que S8: trastes de la 6ª a la 1ª cuerda, `x` = no suena, `0` = al aire,
  enteros 0 a 24. Ejemplo: `[formas]` / `"F#" = "2 4 4 3 2 2"`.
- **Validaciones** (mismos mensajes que S8, con el prefijo `formas «ACORDE»:`): debe ser una tabla («formas debe ser una
  tabla»); el acorde se puede dibujar («no sé dibujar este acorde»); **aparece en algún nivel del tema** (lista `acordes`,
  Básico, Intermedio o Avanzado; «el acorde no aparece en ningún nivel del tema»); 6 valores; cada valor es `x` o un
  número; traste dentro de 0 a 24; al menos 3 cuerdas suenan; solo suenan notas del acorde («suena X, que no es del acorde
  …»); con bajo (`G/B`) la nota más grave es el bajo.
- El prefijo de los errores de nivel sigue siendo `intermedio.formas «…»` / `avanzado.formas «…»` (sin cambios).
- Payload de la página (`#acordes-data`): nueva clave `default` (`{acorde: {frets, tab}}`) junto a `chords` y `own`.


## S26 · Selector de nivel con borde y barra de reproducción plegable en celular (2026-11-04)

**Parte 1, selector de nivel.** Usuarios no notaban que Básico/Intermedio/Avanzado es un selector. Ahora es un control
segmentado: borde de 2 px en el color de acento (≥ 3:1 contra el fondo en Noche y Marfil), opciones inactivas con el color
de texto pleno (≥ 4,5:1), la activa rellena y en negrita con doble anillo, y foco por teclado de 3 px.

**Parte 2, «Opciones» en celular (≤ 575 px).** La barra fija ocupaba demasiado. Quedan visibles Reproducir/pausar,
«Opciones» y los niveles (dos filas); metrónomo, BPM, deslizante, «Sin sonido», «Cuenta inicial» y «Restablecer» van en un
grupo `#met-extra` que se despliega y se repliega cuando se quiera (botón con `aria-expanded` y `aria-controls`; Escape
lo cierra).
- **Escritorio no cambia:** el grupo usa `display: contents` y el botón no se muestra; el orden visual se conserva con `order`.
- **No toca el estado:** los controles siguen en el DOM (solo `display: none`), así que metrónomo, cursor y centrado (S10 a S12)
  no cambian. El botón «Habla con una guía» queda fuera del grupo.
- **Estado inicial plegado, sin recordarlo:** cada visita parte compacta. Descartado: recordarlo en `localStorage`.
- Las pruebas de navegador abren el grupo en celular con `set_options()`; hay pruebas propias del plegado, del contraste y del desborde.

## S28 · Resumen plegado de posiciones al inicio de cada pestaña (2026-11-04)

Cada pestaña de reproducción (Básico, Intermedio, Avanzado) trae, justo bajo su descripción, un `<details class="ac-summary">`
**cerrado por defecto** («Posiciones de los acordes (N)») con guitarra y piano de todos los acordes que usa ESA pestaña
(los de sus botones `.ac-chord-btn`, sin repetir, en orden de aparición).
- **Misma forma que el panel:** la guitarra dibuja `formsFor(acorde, nivel)[0]` (S27: propia del nivel > `[formas]` del tema >
  regla de cejilla > chords-db); el piano usa las teclas del acorde. Reutiliza `guitarSVG` y `pianoSVG` del panel.
- **Carga:** nada se dibuja hasta la primera vez que se abre (evento `toggle`); la carga de la página no cambia.
- **Celular:** rejilla `auto-fill minmax(7.5rem, 1fr)` (2 columnas a 360 px), sin desborde horizontal; comprobado en la matriz.
- Un acorde sin guitarra estándar ni forma propia dice «Sin diagrama de guitarra» y conserva el piano. No hay ukelele ni dedos propios.


## S29 · Barra de reproducción en filas: niveles, controles y aviso de guías (2026-11-04)

Orden de arriba abajo, en escritorio y celular: **(1)** selector de nivel (con el borde de S26), **(2)** controles de
reproducción (en celular, Reproducir + «Opciones» plegable de S26), **(3)** aviso de guías.
- **Aviso (mockup):** «Editores-profes · clases por solicitud (ejemplo del prototipo)», enlace a `guias.html?tema=<slug>`.
  No envía datos ni afirma precios ni disponibilidad. Se puede ocultar con «×» (se recuerda en la pestaña con
  `sessionStorage`, con respaldo si no está disponible); en celular el texto se acorta a una línea.
- No toca el metrónomo, el cursor ni el centrado (S10 a S12): es solo un enlace. Convive con la franja de guías de arriba y
  con el botón corto «Habla con una guía» de la barra, que no cambian.
- Los niveles pasan a una fila propia (`.ac-met-levels-row`, `order: -2`); el resto del orden visual se logra con `order` sin mover el DOM
  de los controles.

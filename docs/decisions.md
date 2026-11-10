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
- **Con paréntesis** (`Dm(add#11)`) sigue sin aceptarse *(reemplazado por S36: ya se acepta)*: cambiaría el patrón de acordes en los dos repos y el contrato
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


## S29 · Barra de reproducción en filas: niveles, controles y aviso de guías (2026-11-04) — reemplazada por S30 (se quita el aviso; quedan los niveles arriba)

Orden de arriba abajo, en escritorio y celular: **(1)** selector de nivel (con el borde de S26), **(2)** controles de
reproducción (en celular, Reproducir + «Opciones» plegable de S26), **(3)** aviso de guías.
- **Aviso (mockup):** «Editores-profes · clases por solicitud (ejemplo del prototipo)», enlace a `guias.html?tema=<slug>`.
  No envía datos ni afirma precios ni disponibilidad. Se puede ocultar con «×» (se recuerda en la pestaña con
  `sessionStorage`, con respaldo si no está disponible); en celular el texto se acorta a una línea.
- No toca el metrónomo, el cursor ni el centrado (S10 a S12): es solo un enlace. Convive con la franja de guías de arriba y
  con el botón corto «Habla con una guía» de la barra, que no cambian.
- **Sin duplicar:** cuando la franja de guías sale de pantalla y aparece el botón corto «Habla con una guía», el aviso se
  oculta (CSS, `.ac-met-help:not([hidden]) ~ .ac-met-banner`). La barra fija compacta el espacio entre filas para no pasar
  del 35 % de la pantalla en escritorio.
- Los niveles pasan a una fila propia (`.ac-met-levels-row`, `order: -2`); el resto del orden visual se logra con `order` sin mover el DOM
  de los controles.


## S30 · La barra de reproducción queda en dos filas, sin aviso de guías (2026-11-04)

Reemplaza a S29. El usuario rechazó el concepto de aviso (banner) en la barra. Se quita por completo: HTML, CSS, JS (el «×», su
memoria en `sessionStorage` y la regla que lo ocultaba junto a «Habla con una guía») y sus pruebas.
- **Barra:** **(1)** selector de nivel (borde de S26), **(2)** controles de reproducción (en celular, Reproducir + «Opciones»
  plegable). Se conserva el botón corto «Habla con una guía» y la franja de guías de arriba.
- Se conserva de S29 la fila propia de los niveles (`.ac-met-levels-row`) y la barra compacta.


## S31 · Avanzado hereda la partitura de Intermedio y declara solo extras por sección (2026-11-04)

Reemplaza la parte de S17 que daba a Avanzado su propia partitura, `[avanzado.tabs]` y `[avanzado.arreglos]`. Se conservan de S17 los
límites (tab 2000, arreglo 600, tips 80/600), el escape y que cada extra se muestra la primera vez que aparece su sección.
Los bajos siguen siendo de Intermedio. Ningún tema (publicado, `songs/` ni `acordes-local/`) usaba Avanzado: no hay datos que migrar.

**Contrato del formato** (compartido con research, `tests/fixtures/acordes/contract.json`; 24 casos nuevos, los de `avanzado.partitura`,
`tabs` y `arreglos` se reemplazaron):
```toml
[intermedio]
partitura = '''
Intro: Em G/B
Estrofa x2: C D
'''

[avanzado]                        # sin partitura
tab = '''...'''                    # opcional: tab general, al final de la pestaña (se conserva)

[avanzado.secciones."Intro"]      # clave = nombre de una sección de la partitura de INTERMEDIO
tab = '''e|--0--|'''              # opcional, hasta 2000 caracteres
arreglo = "Rasgueo suave con `Em`" # opcional, hasta 600 (acordes entre acentos graves, S15)
tips = ["Título | Texto"]         # opcional, lista de «Título | Texto»: título ≤ 80, texto ≤ 600
                                  # (Intermedio y Básico siguen en 60/280 con `> Título | Texto` en la partitura)

[avanzado.formas]                 # S8, se conserva: acordes que aparecen en Intermedio
"G/B" = "x 2 0 0 3 3"
```
- Cada sección entrada debe tener al menos una de `tab`, `arreglo`, `tips`. Una sección de Intermedio sin entrada se muestra igual, sin extras.
- **Render:** la pestaña Avanzado es la partitura de Intermedio (compases y tips de Intermedio incluidos) más, en cada sección la primera
  vez que aparece: `arreglo`, `tab` bajo los compases y los `tips` de Avanzado como tarjetas tras la sección. Hay Avanzado (`avanzado_secciones`
  = secciones de Intermedio) solo si hay entradas en `secciones` o `tab`; si no, «Próximamente» y no cuenta en `version_count` (S20). Los acordes
  del panel y del resumen plegado (S28) son los de Intermedio; Avanzado no admite acordes propios.
- **Mensajes de error** (en español, con `avanzado` como prefijo; `N` desde 1):
  `avanzado debe ser una tabla` · `avanzado: ya no lleva partitura propia; muestra la de Intermedio. Pon lo propio en [avanzado.secciones."Nombre"] (tab, arreglo, tips)` ·
  `avanzado.tabs ya no existe: usa [avanzado.secciones."Nombre"] con tab = ...` · `avanzado.arreglos ya no existe: ... con arreglo = ...` ·
  `avanzado: tab debe ser texto` · `avanzado.secciones debe ser una tabla ([avanzado.secciones."Nombre"])` ·
  `avanzado: necesita la partitura de Intermedio (Avanzado la hereda)` (hay extras o `tab` y Intermedio no tiene compases; es el único error) ·
  por sección, prefijo `avanzado.secciones «Nombre»:` → `no hay una sección con ese nombre en la partitura de Intermedio` ·
  `debe ser una tabla (tab, arreglo, tips)` · `clave desconocida «k» (usa tab, arreglo o tips)` · `no tiene extras; escribe tab, arreglo o tips (o quita la sección)` ·
  `tab debe ser texto, no vacío` / `arreglo debe ser texto, no vacío` · `tab pasa de 2000 caracteres` / `arreglo pasa de 600 caracteres` ·
  `tips debe ser una lista de textos «Título | Texto»` · `tips[N] debe ser texto «Título | Texto»` ·
  `tips[N]: un tip se escribe «> Título | Texto» (con título y texto)` / `tips[N]: el título del tip pasa de 80 caracteres` / `tips[N]: el texto del tip pasa de 600 caracteres`.
  Las formas de Avanzado siguen: `avanzado.formas «Dm7»: el acorde no aparece en la versión avanzado` (se compara con los acordes de Intermedio).
- **Plantillas:** la técnica y la simple dejan de traer `[avanzado] partitura`; traen `[avanzado.secciones."Nombre"]` comentado.
- **Cómo sincroniza research:** copiar `tests/fixtures/acordes/contract.json` y adaptar su validador (`parse_score` ya no recibe `advanced`; la
  validación de Avanzado es `check_advanced` + `advanced_extras` de `musicsite/acordes.py`), el editor y la copia vendorizada del render
  (`scripts/sync_site_render.py` de research, que toma `songpages.py` y `acordia.js`; `load_song` compone Avanzado y `structure(sections, extras)`
  renderiza los extras). `acordia.js` no cambió.
- **Descartado:** compatibilidad con la partitura propia de Avanzado (nada la usa; un archivo viejo da el error de migración de arriba).


## S32 · «Opciones» avisa «Sin sonido» y el pipeline tiene límites de tiempo (2026-11-04)

**Parte 1.** En celular, con el panel de S26 plegado, el modo «Sin sonido» (que se recuerda entre visitas) no se notaba. El botón «Opciones»
muestra ahora un ícono de altavoz tachado y su nombre accesible pasa a «Opciones (sin sonido activado)» (`aria-label` y `title`); todo se
quita al desactivar el modo. Solo celular (el botón no existe en escritorio). Probado en Pixel 7 e iPhone 14, con captura revisada.

**Parte 2.** Los jobs e2e se colgaron de 12 a 30 min en `playwright install` (incidentes de GitHub Actions). Duraciones típicas de los últimos
12 runs: lint y tests 12-26 s, e2e 150-270 s (atascos de 450-1120 s), imagen 11-24 s, publicar 35-46 s, desplegar 27-35 s. `timeout-minutes`:
**e2e 20, lint y tests 10, imagen 10, publicar 10, desplegar 10**. Un atasco falla en vez de colgar; se reintenta el run. El pipeline sigue
secuencial (D45): no cambian los `needs`.

## S33 · Foto del artista en su tarjeta (2026-11-04)

`artists.json` puede traer `photo` (`fotos/<slug>-<12 hex>.jpg`, de research M49). La tarjeta del artista la muestra, redonda de 72 px (estilo en línea: `style.css` está copiado en research y tocarlo obliga a sincronizar), con `alt="Foto de <nombre>"`, carga diferida y el nombre al lado.
- **Servida desde la publicación:** `/fotos/<archivo>.jpg` sale del release vigente (el catálogo guarda los JPEG al cargar, hasta 200 de 300 KB como máximo) con `Cache-Control: public, max-age=31536000, immutable`: el nombre
  lleva el hash, así que una foto nueva es otra URL. Solo se sirve lo que cita el `artists.json` vigente; cualquier otra ruta de `/fotos/` da 404.
- **Nunca bloquea una publicación:** una ruta fuera del contrato (con `..`, otra extensión, otro slug), un archivo que falta, que no empieza como JPEG o pesa más de 300 KB se descarta y el artista sale sin foto.
- Sin foto, la tarjeta es igual que antes. El respaldo de git no trae fotos. CSP sin cambios (`img-src 'self'`).

## S34 · Descripción del artista en párrafos legibles (2026-11-04)

La descripción de un artista (texto plano de research M49/M41) se dibuja como párrafos: una **línea en blanco separa párrafos** y un salto simple dentro de uno es un `<br>`. Antes todo salía como un solo
bloque porque HTML colapsa los saltos. Cada párrafo va escapado, con interlineado de 1,65 y separación entre párrafos (estilo en línea, por lo mismo que S33: `style.css` está copiado en research). Una descripción vacía
o solo de espacios no dibuja nada. Sin cambios en el contrato de `artists.json`.

## S35 · Crédito de la foto del artista (2026-11-04)

`artists.json` puede traer `photo_credit` (texto, ≤ 200) y `photo_credit_url` (http/https). La tarjeta los muestra bajo la foto (`<p class="ac-photo-credit">`), con el texto escapado y el enlace externo con `rel="noopener noreferrer"`. Las licencias CC BY y CC BY-SA exigen atribución. Solo se muestra si hay foto; una URL inválida se descarta y queda el texto. Contrato con research M51.

## S36 · Acordes con paréntesis, separadores y 6/9 (2026-11-05)

Pedido del equipo editorial: poder escribir las extensiones entre paréntesis (`Dm(add#11)`). Reemplaza la nota de S21 («con paréntesis sigue sin aceptarse») y retoma los alias con paréntesis que S16 había quitado, esta vez con una gramática general. Se investigó cómo se escriben en la práctica (Dobrian, Open Music Theory, Maricopa, MuseScore, Oolimo, ChordPro): **no hay un estándar**; el paréntesis es de estilo, sirve para ver que la alteración es de la extensión y no de la raíz, y las alteraciones se escriben pegadas, con coma, con barra o con espacio según el autor.
- **Gramática (solo Intermedio):** un único grupo entre paréntesis, justo antes del bajo, con las extensiones de siempre (`7`, `9`, `13`, `b9`, `#11`, `add9`, `sus4`…) separadas por **coma, barra o pegadas**: `Dm(add#11)`, `G7(b9)`, `Am7(b5)`, `C(add9)/E`, `G7(b9,#11,13)`, `G7(b9/#11/13)`, `G7(b9#11)`. La barra dentro del paréntesis no se confunde con el bajo, que va después del cierre. **Rechazados:** paréntesis anidados, vacíos o sin cerrar, dos grupos (`G7(b9)(b13)`), espacios dentro (separan acordes), comas sobrantes, paréntesis en la raíz o la calidad (`(Dm)`, `D(m)`).
- **Dentro del paréntesis cada extensión lleva su número** (salvo `sus`): `b`, `#` o `add` sueltos no significan nada. Así se atrapa el error típico `Dm(add11#)` (lo correcto es `Dm(add#11)`), que la gramática heredada habría aceptado como `add11` más un `#` suelto. Fuera del paréntesis la gramática no cambia (sin romper lo existente).
- **6/9:** `D6/9`, `D(6/9)`, `D69` y `D6add9` son el mismo acorde, y `Dm6/9` el menor. Un bajo es siempre una letra de nota, así que una barra seguida de un número no es un bajo (`D6/A` sigue siendo un 6 con bajo en La y `D6/9/A` un 6/9 con bajo). Solo se acepta `6/9` (no cualquier `/número`). El 6/9 mayor se suma a la teoría: D F♯ A B E, con teclado (la guitarra no tiene forma estándar en chords-db).
- **Identidad y presentación:** `chordtheory.canonical` quita paréntesis y separadores y pasa `6/9` a `69` (`Dm(add#11)` = `Dmadd#11`, `G7(b9/#11/13)` = `G7b9#1113`). Con esa forma se buscan las notas y se comparan la lista de acordes y las **formas propias**: una forma escrita `Dmadd#11` vale para `Dm(add#11)` en la partitura, y el JavaScript la recibe bajo el nombre de la partitura. **Se muestra como se escribió**; los `b` y `#` dentro del paréntesis también salen como ♭ y ♯ (`G7(♭9/♯11)`).
- **Límite asumido:** una combinación válida cuyas notas no conocemos (`G7(b9/#11/13)`) pasa el validador pero sale como texto, sin botón ni teclado, igual que cualquier acorde que no sabemos dibujar. Calcular las notas de cualquier combinación sumando extensiones queda como decisión aparte.
- **Contrato compartido:** casos nuevos (válidos y rechazados). Research recibe el cambio con `scripts/sync_site_render.py`. El validador del Básico no cambia (sigue sin extensiones).
- **Pruebas:** gramática (16 válidos, 17 rechazados), `canonical`, teoría (6/9, equivalencia), página (botón, notas, formas, acentos) y una prueba de navegador del panel con `D6/9` y `Dm(add#11)`.


## S38 · Novenas alteradas (7b9, 7#9) y forma propia obligatoria cuando no hay estándar (2026-11-05)

**Integrada a main (2026-11-05).** Hasta hoy `G7b9` (que usa «Déjate caer») se aceptaba como texto en la partitura, pero
`chordtheory.parse` no lo conocía: sin notas, sin teclado, sin guitarra y sin forma propia posible («no sé dibujar este acorde»).

- **Teoría:** `7b9`, `7#9` y `7b9#9` entran a `INTERVALS` y `ALIASES` (b9 = 13, #9 = 15 semitonos; grado 2). Con la forma
  normalizada de S35, `G7(b9)`, `G7b9`, `E7(b9,#9)` y `E7(#9/b9)` son el mismo acorde de cada tipo. Otras alteraciones (#11, b13, b5)
  siguen como texto, igual que antes (el cálculo de combinaciones sigue como decisión aparte).
- **Regla del validador:** si un acorde se sabe nombrar pero chords-db no trae forma (`guitar_positions` es None: 7b9, 7#9, add#11,
  madd#11, 6/9 mayor…), el tema debe traer una forma propia en `[formas]` o en la tabla de un nivel; si no, error con el
  nombre del acorde. Las formas se siguen comprobando con `check_shape`.
- **El admin exige, el sitio tolera:** `validate_file(path, strict_shapes=True)` (por defecto: admin, CLI y contrato) devuelve la falta de forma como **error**; el sitio
  (`songpages`) la valida con `strict_shapes=False` y la deja como **aviso** (`Report.warnings`): un tema publicado sin esa forma se muestra igual (ese acorde sin diagrama ni sonido)
  en vez de descartar la publicación entera. Así ningún despliegue puede tumbar lo publicado (hoy «Déjate caer» usa G7b9 sin forma propia en producción).
- **Research:** su copia del validador replica la regla (M45 la comprueba).
- `songs/dejate-caer.toml` (respaldo) suma `[formas] "G7b9" = "3 2 3 1 x x"`. Los casos del contrato que usan estos acordes traen `[formas]`.

## S37 · Guitarra con sonido MIDI en el reproductor: resultado de la investigación (2026-11-05)

Se investigó en la rama `feat/investigacion-midi` (preservada con la etiqueta `investigacion-midi-lab`; el laboratorio vive ahora en el repo de control, `labs/midi/`, decisión C1) si el
reproductor podía tocar las formas de guitarra. **Resultado:** sí, con una suma por cuerda (afinación + traste = nota MIDI), una **muestra mp3 por nota** y el reloj de Web Audio del metrónomo.
Quedó integrado en el reproductor (S38 a S42): botón «Guitarra» (apagado al abrir cada página), rasgueo redonda/blancas/negras, **guitarra de nailon** y **contrabajo** cuando el acorde lleva bajo.
No hay sonido sintetizado (se descartaron Karplus-Strong y el acero).
- **Muestras:** FluidR3_GM por midi-js-soundfonts, 49 de nailon (E2 a E6) y 12 de contrabajo (E1 a Eb2), ~1 MB, en `src/musicsite/web/` (se cargan solo al activar «Guitarra»; caché de un día). Licencia y atribución en
  `THIRD_PARTY_NOTICES.md`.
- **Licencia (L1):** el distribuidor las publica bajo **CC BY 3.0** (el repo, bajo MIT). L1 solo lista MIT, BSD, ISC y Apache-2.0: la inclusión es una **excepción decidida por el usuario el 2026-11-05**, con atribución. El repo del site es
  **público**, así que las muestras quedan expuestas con su aviso. Si alguna vez hay un reclamo o se quiere cerrar la excepción, basta quitar las muestras y el botón (el resto del reproductor no depende de ellas).
- **Pendiente:** consulta legal D-C25 (sonido de acordes de temas de terceros); probar en Safari/iPhone reales; R1 sigue por migrar (research mantiene su copia del render, M45).

## S39 · Guitarra de nailon y volúmenes separados al integrar (2026-11-05)

Tras oír el laboratorio y el reproductor local, el usuario elige la **guitarra de nailon** (muestras FluidR3_GM,
una por semitono, E2 a E6, unos 850 KB) frente a la cuerda sintetizada (Karplus-Strong) y a la de acero. «Más acorde a lo que necesito.» El reproductor las toma de `web/guitarra-nylon-*.mp3` (licencia y atribución: S37).

**Requisito de la integración:** el reproductor debe tener una **sección de volúmenes con un control
para el metrónomo y otro para la guitarra**, independientes. Falta decidir cuando se integre: dónde va (dentro de «Opciones», S26), si se
recuerda por dispositivo (`localStorage`, con respaldo si falla) y si «Sin sonido» (S32) sigue siendo un interruptor que silencia ambos.
**Hecho:** dos deslizadores en «Opciones» (`data-ac-vol-met`, 100 % por defecto, y `data-ac-vol-guitar`, 70 %), que se
recuerdan por dispositivo en `localStorage` (con try/catch). Al activar «Guitarra» se crea el audio y se bajan las muestras, y mientras una nota
no ha cargado no suena. **Actualización:** se elimina del reproductor todo el sonido sintetizado (Karplus-Strong) y el de acero: solo queda
el nailon, sin respaldo (si faltan las muestras, no suena). El laboratorio (`labs/midi/` del control) conserva sus dos motores solo para comparar.

## S40 · Rediseño de la barra de reproducción: Tempo y Sonido en grupos (2026-11-05)

**Rama `feat/investigacion-midi`, sin PR.** Con la guitarra y sus volúmenes (S37, S39), la barra mezclaba botones de encendido y deslizadores en una fila, y los
volúmenes se veían como un punto sin riel. Se reorganiza en grupos con título; no cambian los `data-*`, los ids ni los comportamientos de S10, S12, S26, S30 y S32.

- **Tempo:** Reproducir, − bpm +, deslizante y Restablecer. **Sonido:** tarjeta *Metrónomo* (volumen con riel y valor en %, más «Cuenta inicial»),
  tarjeta *Guitarra* (interruptor y volumen, atenuado y deshabilitado mientras está apagada) y «Sin sonido» como interruptor general, con texto.
- **El metrónomo no tiene interruptor propio:** su volumen en 0 % lo apaga (decisión del usuario). «Sin sonido» sigue silenciando todo.
- **Escritorio:** tres filas (nivel; Tempo; Sonido). «Habla con una guía» pasa a la derecha de la fila del selector de nivel para que la barra fija siga
  bajo el 35 % de la pantalla (guarda e2e existente). **Celular (≤ 575 px):** igual que S26: Reproducir + «Opciones»; dentro, las secciones «Tempo» y
  «Sonido» con título (los textos de «Cuenta inicial» y «Sin sonido» ya no se ocultan: hay lugar).
- Los deslizadores de volumen usan el mismo estilo de riel y control que el de tempo, con foco visible por teclado, en Noche y Marfil.
- **Ajuste de prueba por S38:** el fixture e2e `parens_url` suma `[formas]` para `D6/9` y `Dm(add#11)`, que ahora exigen forma propia.
- Comprobado: ruff, 608 tests y e2e de chromium (57 pasan, 2 se saltan) y las pruebas de la barra en Pixel 7. **No probado:** Safari/iPhone real y Firefox.

## S41 · Sonido de bajo cuando el acorde lleva bajo (2026-11-05)

Con la guitarra activa, un acorde con bajo (`F#m7/A`, `Dm/F`, `C#m7b5/F#`…) suena además con una nota de **contrabajo**
(`acoustic_bass` de FluidR3_GM, elegido por el usuario) en la octava más grave de E1 a Eb2 (12 muestras, ~190 KB, `web/bajo-<nota>.mp3`; licencia: S37, igual que las de nailon). Arranca con el primer golpe del acorde y se corta con el siguiente acorde o silencio. Con la guitarra apagada no suena. Sigue el
volumen de la guitarra al inicio (S42 le dio uno propio); suena aunque el diagrama ya dibuje el bajo. Las muestras se cargan al activar «Guitarra», junto con las de nailon.

**Panel del acorde:** si el diagrama es del acorde base, «… El bajo (X) no está dibujado, pero si activas la guitarra suena como bajo.»; si el bajo sí está dibujado,
«El bajo (X) suena aparte, como bajo, si activas la guitarra.»

**Pendiente:** el contrabajo suena más jazzero que el eléctrico (`electric_bass_finger`), por si se cambia de opinión.

## S42 · Volumen propio del bajo y sección Sonido en una fila (2026-11-05)

La tarjeta «Guitarra» suma un deslizador **«Bajo»** (70 % por defecto, se recuerda por dispositivo en `localStorage` con try/catch) con su propio nodo de ganancia, independiente del de la guitarra.
Se desactiva junto con la guitarra cuando está apagada. Los tres deslizadores del grupo Sonido miden 3 rem para que Metrónomo, Guitarra, Bajo y «Sin sonido» quepan en una fila en escritorio (la barra fija sigue bajo el 35 % de la pantalla, guarda e2e).

## S43 · Forma propia de un acorde con bajo, con o sin el bajo (2026-11-05)

`[formas]` acepta para `Dmaj7/E` tanto la forma con el bajo como nota más grave (`0 5 7 6 7 5`) como la del acorde base sin él (`x 5 7 6 7 5`), siempre sin notas ajenas. Antes la segunda se rechazaba («la nota más grave debe ser E»). Una sola forma por acorde. En la segunda, el panel dice «Esta forma no incluye el bajo (E): otro instrumento puede tocarlo, y si activas la guitarra suena como bajo.» (`no_bass` en el JSON de la página; `chordtheory.shape_lacks_bass`). Contrato compartido con 2 casos nuevos.

## S44 · El site usa la librería `acordia_render` y borra su copia del render (2026-11-06)

Último paso de R1 en el site. El render, el validador, el contrato, los datos de chords-db, las plantillas, `acordia.js`, `guitarra.js`, `style.css`, la tipografía y las 61 muestras viven en `saul-music-render` (`acordia-render==0.1.0`, Artifact Registry); aquí se borran `chordtheory`, `acordes`, `songpages`, `chordsdb`, `data/`, `templates/` y esos archivos de `web/`, junto con sus tests y el contrato (ahora fuente única en la librería, que además lo prueba contra el validador). El site conserva `app.py`, `catalog.py`, `artists.py`, `profes.py` (las guías de ejemplo), `songs/` (respaldo) y las páginas estáticas, más los e2e.

- **Servidor:** `create_app` sirve `{**archivos de la librería, **web/}` (los del site tienen prioridad); el resto es 404 como antes. Las muestras siguen con un día de caché.
- **Guías:** son del site; `create_app` hace `guides.use(profes)` y los tests lo hacen con un `conftest.py`.
- **Dependencia y token:** un único índice propio, `explicit`, solo para la librería (excepción registrada en R1). Sin token en el repo: en local `scripts/uv-acordia.sh uv --no-config sync`; en el CI, `lint y tests`, los 5 `e2e`, `imagen` y `publicar imagen` piden el token a `render-reader` por WIF (`vars.GCP_WIF_RENDER_READER`); en el `Dockerfile` entra como secreto de build, sin quedar en ninguna capa. El repo del site es público: quien lo clone puede leer el código, pero no instalar la librería sin acceso a GCP.
- **Avisos de terceros** (chords-db, Petaluma, FluidR3_GM con su excepción a L1): se mudaron a `THIRD_PARTY_NOTICES.md` de la librería; el site publica los mismos archivos, así que aquí queda un puntero.
- **Para cambiar el render:** se cambia en la librería, se sube `version` y se publica; después el site y research suben su versión fijada. Ya no se toca nada de eso aquí.

## S45 · Acordes 13 y 7(13) y guitarra activa por defecto: el site sube a `acordia-render` 0.2.0 (2026-11-06)

Sin código de render aquí (vive en la librería, RD5): el site fija `saul-music-render==0.2.0` y cambia sus pruebas de navegador. **La guitarra parte activa** (y se recuerda por dispositivo si se apaga); las muestras bajan en el primer gesto, no al abrir. Antes los e2e asumían la guitarra apagada y `test_guitar_loads_its_samples_and_unlocks_the_volumes` se reemplazó por tres: parte activa y no descarga nada hasta el primer gesto, apagarla se recuerda al recargar y no baja más, y volver a activarla baja las 61. En celular, abrir «Opciones» ya es un gesto, así que esas pruebas leen el estado sin tocar la página antes de medir. Los acordes `13` y `7(13)` (= `7add13`, `713`) ya se validan y se dibujan con las formas de chords-db; ver RD5 en la librería para su definición y fuentes. Matriz e2e de 5 navegadores en local (60 a 61 tests cada una) antes de publicar la librería.

**Ajuste de las pruebas tras el primer CI de S45:** con la guitarra activa, en el emulador de celular del CI las 61 muestras tardaron decenas de segundos y competían con pruebas ajenas al sonido (el cambio de tema falló). La fixture `song` ahora deja la guitarra apagada (`ac-guitar = off` por script de inicio) para todo lo que no es sonido; `song_sound` y las pruebas de sonido la ven como una persona, con esperas de hasta 40 s. Sin cambios en la librería ni en el comportamiento.

## S46 · El primer acorde ya no sale mudo: el site sube a `acordia-render` 0.2.1 (2026-11-06)

Sin código de render aquí (vive en la librería, RD6). **El problema:** al dar Reproducir como primer gesto, las muestras de la guitarra tenían solo la cuenta inicial (≈ 2 s) para llegar; con red lenta o caché fría el compás 1 sonaba mudo, sin aviso. Medido en producción con Playwright: red rápida suena; con 1,5 Mbps los dos primeros compases quedaban mudos y con 0,4 Mbps ninguno. **Ahora** Reproducir dice «Cargando sonido N%» y la cuenta espera a que estén las notas del tema (menos de la mitad del banco); con un tope de 10 s arranca igual y muestra 8 s «Sin guitarra: el sonido no terminó de cargar». El site fija `saul-music-render==0.2.1`.

**Pruebas (e2e, `HeldSamples` retiene las descargas):** la cuenta no empieza mientras carga y sí al llegar; detener durante la carga cancela esa partida; con el tope el aviso se ve y el metrónomo sigue. Sin la espera, las dos primeras fallan (comprobado). `song_audio`, que prueba el pulso, deja la guitarra apagada como `song`. **Sin comprobar:** si el primer acorde también falla con red rápida y muestras en caché, sería el arranque de la salida de audio del dispositivo (Bluetooth, macOS), que un navegador sin pantalla no oye.


## S47 · Ligado `_` en la partitura: el site sube a `acordia-render` 0.3.0 (2026-11-06)

Sin código de render aquí (vive en la librería, RD7). `_` es un ligado: el acorde que sonaba sigue sonando sin golpe nuevo, como compás entero (`E _`) o como parte de un compás partido (`B-F# _-F#`). Se ve atenuado y con un arco, abre el diagrama de ese acorde, y la guitarra y el bajo no golpean en esa parte. La nota bajo la partitura explica el arco solo si el tema usa ligados. No abre una sección ni liga un silencio. El site sube **antes** que research: debe entender `_` antes de que el admin deje publicarlo. Fija `saul-music-render==0.3.0`.

**Pruebas (e2e, fixture `ties_url` con «Cámara lenta» ligada):** dos ligados dibujados con su acorde y su arco, el diagrama se abre, la nota se ve, el cursor pasa por ellos y no hay errores ni desborde; en Chromium, Firefox y WebKit (iPhone 14). Que la guitarra no golpee lo prueba la librería (`tests/js/ligado_guitarra.js`). **Sin comprobar:** oírlo en un dispositivo real (el usuario lo revisó a ojo y oído en una vista previa local).

## S48 · El e2e del CI corre solo con código propio del sitio; contra producción, en local (2026-11-06)

**Decisión del usuario.** Desde R1 el render (página de canción, metrónomo, guitarra) vive en `saul-music-render`, pero el e2e del sitio lo seguía probando con la matriz de 5 navegadores en cada PR y otra vez en `main`, aunque el cambio fuera solo subir la versión de la librería. Además `playwright install` de WebKit se cuelga a menudo en el runner (el PR #70 necesitó tres intentos de iPhone 14).

1. **`scripts/necesita-e2e.sh <rango>`** decide: si el cambio solo toca `pyproject.toml` (y ahí solo la línea `saul-music-render==`), `uv.lock` o archivos `.md`, imprime `false`; cualquier otro archivo u otra dependencia, `true`. Sin diferencia conocida, `true`. Probado con repos temporales (`tests/test_necesita_e2e.py`).
2. **Pipeline.** El job de lint y tests lo calcula (PR: contra la base; push: contra `before`; a mano: siempre `true`) y el e2e corre solo con `true`. `imagen`, `publicar imagen` y `desplegar` siguen con el e2e en verde **o saltado**, nunca fallido o cancelado (`!cancelled()` y el resultado del paso anterior). El orden de D45 no cambia; `main` no tiene checks obligatorios, así que un e2e saltado no bloquea un PR.
3. **`scripts/e2e-produccion.sh [navegador]`** corre en local las pruebas de navegador del sitio contra producción (`E2E_BASE_URL`; por defecto la URL de `musicsite`), en Chromium, Firefox, WebKit, Pixel 7 e iPhone 14. Se usa después de desplegar un cambio que saltó el e2e. Las pruebas que arman temas propios (fixtures `*_url` salvo `base_url`) y las que dependen del catálogo de `songs/` se saltan con «solo en local». Primera corrida contra producción en Chromium: 53 pasan, 12 saltadas.

**Pendiente (paso 3 del plan, sin empezar):** mover las pruebas de navegador del render a la librería, solo locales; aquí quedarían las propias del sitio.

## S49 · e2e más liviano en el CI: solo en PR, dos navegadores y sin cuelgues de 20 minutos (2026-11-06)

**Decisión del usuario**, tras analizar las 175 corridas del pipeline (31 de octubre al 6 de noviembre): 744 jobs de e2e, unas 41 horas de runner en 7 días, 38 % en repetir el e2e al mezclar a `main` y 19 % en jobs que no terminaron bien. De 70 jobs no exitosos, 31 fueron pruebas que fallaron (casi todas bugs reales de ramas nuevas: el e2e sí atrapa errores; solo 2 pasaron con un reintento sin cambios) y unos 29 cuelgues del runner en `apt` (instalar el navegador con `--with-deps` o PulseAudio), en aumento (0 el 3 de noviembre, 11 el 6). Un job sano dura ~3 min (1,9 de pruebas).

1. **El e2e no se repite al mezclar a `main`** (`push` → `e2e=false`): el PR ya lo corrió sobre ese código. Tras desplegar, `scripts/e2e-produccion.sh` en local. A mano (`workflow_dispatch`) sigue corriendo.
2. **Dos navegadores en el CI:** Chromium e iPhone 14 (WebKit). Firefox, WebKit de escritorio y Pixel 7 quedan para `e2e-produccion.sh`, que corre los cinco.
3. **Sin «audio virtual (experimento)» en el CI:** `test_audio_real.py` se salta con `CI=true` y corre en local.
4. **Instalar el navegador con hasta 3 intentos de 4 minutos** (`timeout -k 10 240`, luego se matan los `apt`/`dpkg` colgados y se repara `dpkg`), con tope de 13 minutos para el paso. Caché de los navegadores: no, por ahora (sería una acción de terceros más).
5. **`test_beat_flash_follows_the_chord_inside_a_split_bar`** parte con la bandera desde el primer compás partido en vez de esperar ~30 compases: de 36 s a 1,3 s (era el 27 % del tiempo de pruebas). La del tope de 10 s del sonido (13 s) no se acorta aquí: el tope vive en la librería y esa prueba se mudará a ella (paso 3 de S48).

Efecto esperado: un PR que toca el sitio pasa de ~15 min de runner (5 × 3, más la repetición en `main`) a ~6 (2 × 3), una sola vez.

## S50 · Las pruebas de navegador de la página de canción se mudan a la librería (2026-11-06)

Paso 3 del plan (C2 en el control; RD8 en `saul-music-render`). 46 pruebas de la página de canción y `test_audio_real.py` pasan a la librería, donde corren solo en local. Aquí quedan **18**, las propias del sitio: cabeceras de seguridad de la página de canción, guías (4), portada y Biblioteca con su buscador, artistas (4), pedidos (4) y el 404 de un tema sin publicar. Las fixtures que armaban variantes de «Cámara lenta» (tips, formas, paréntesis, Avanzado, silencios, ligados) se fueron con sus pruebas; queda `one_song_url`. En Chromium local el e2e del sitio pasa de 66 pruebas en 136 s a 18 en 15 s. `scripts/e2e-produccion.sh` corre ahora solo estas; el render contra producción se prueba con `E2E_BASE_URL=… scripts/e2e.sh` en la librería.

## S51 · Acordes extendidos, tanda 1: el site sube a `acordia-render` 0.4.0 (2026-11-06)

Sin código de render aquí (vive en la librería, RD10). Los acordes que antes salían como texto ahora tienen notas,
teclado, guitarra y sonido: `5` (también en dos cuerdas), `add11`, `madd11`, `m7add11`, `7sus2`, `9sus4`, `11`, `7#5`
(`7+`), `7b5`, `maj7#11`, `maj13`, `m13`, `13sus4` (`Bsus413`, `Bsus4(9,13)`) y `7b9#11` (`7(b9,#11)`). `7b9`, `7#9` y
`69` ganan formas estándar de chords-db; la forma propia de un acorde vale para todas sus escrituras.

**Pruebas:** las de la librería (567 y su contrato). Aquí, los 239 tests del sitio en verde; el CI salta el e2e porque
solo sube la librería (S48). Se publica antes que research.


## S52 · Landing: «Donde se respiran acordes» y el problema de encontrar un acorde (2026-11-06)

El lema pasa de «Donde se respira música» a **«Donde se respiran acordes»** (título, hero, descripción y pie de `index.html`, `artistas.html`, `guias.html`, `pedidos.html` y `cancion.html`), con la línea «Encontrar el acorde no debería ser la parte difícil». La portada gana: (1) una animación de chips «¿Am? ¿F? ¿C? ¿G?» que se ordenan en «Am F C G», solo CSS y sin movimiento con `prefers-reduced-motion`; (2) la sección **«Ya lo viviste»** con tres tarjetas del dolor (tono arriba, no coincidía con el disco, para quien ya sabe tocar); (3) **«El mismo tema, a tu medida»** con Básico, Intermedio y Avanzado, con progresiones genéricas (ningún acorde de un tema ajeno).

Los estilos nuevos van en un `<style>` de `index.html` (la CSP ya permite estilos en línea) para no tocar `style.css`, que vive en la librería. **Queda fuera:** el pie de las páginas de cada canción, que sale de la plantilla de la librería y sigue con el lema anterior hasta su próxima versión (RD). **Pruebas:** `test_landing_leads_with_chords`; 240 tests en verde y revisión en Chromium (escritorio, 390 px y tema claro); Safari, iPhone y Firefox sin ejecutar.

## S53 · La pantalla queda encendida mientras suena: el site sube a `acordia-render` 0.4.1 (2026-11-07)

**Decisión del usuario**, por un error en iPhone: con el bloqueo automático, la pantalla se apagaba a mitad del tema y
el tema dejaba de sonar, mala experiencia para quien toca con el teléfono en un atril. La librería (RD11) pide mantener la
pantalla encendida al apretar Reproducir (Screen Wake Lock: Safari 16.4+, Chrome en Android) y la libera al detener o al
terminar la pasada; sin la función queda como antes. El site solo sube la dependencia; las pruebas de navegador de esto
viven en la librería (RD8). **Pendiente:** comprobar en un iPhone real con bloqueo automático de 30 s que un tema de más
de 1 minuto suena entero.

## S54 · Landing: la Biblioteca va primero y las ventajas debajo (2026-11-09)

**Decisión del usuario.** La portada pasa a: hero compacto → **Biblioteca** → «¿Por qué Acordia?» (problema, niveles, cómo funciona,
barrios) → guías → planes. Reemplaza en parte a S52: sale la animación del caos de acordes y los chips de barrios del hero, y la
ilustración queda solo en escritorio. La Biblioteca gana contador (solo temas con enlace, igual al del hero), filtros rápidos por
barrio y nivel (script propio de la portada, clase `ac-fuera`, sin chocar con el filtro de texto de la librería), insignia de nivel
de color y «Ver acordes →». Todo es HTML, CSS y JS de `index.html`; la librería no se toca. Se mantiene el buscador del hero.
**Queda fuera:** foto del artista en la cabecera del grupo (el HTML lo genera la librería). **Pendiente:** revisar a ojo en Safari/iPhone
y celular reales.

## S55 · Página «Ser guía» y postulación por correo (2026-11-09)

**Decisión del usuario.** El texto de la portada sobre la IA que arma la guía de práctica ya no aplica. «Quiero ser guía» lleva a
`ser-guia.html`: qué es un guía, compromisos (**al menos 4 contactos al mes** con respuesta en 24 h, M18; **una transcripción pública**
al entrar y luego una por trimestre; acordes de oído con declaración de procedencia y cesión por escrito, D-C15; revisión editorial,
D-C21), incentivos sin pago fijo (firma, perfil público, prioridad en las solicitudes de los temas editados, créditos y niveles, D-C25),
pasos y preguntas frecuentes. **Postular es enviar un correo** a contacto@saulapp.com (`mailto` prellenado); no hay formulario ni base
de datos. Sin montos ni porcentajes (P-15). **Pendiente:** V3 (relación con los guías, cesión y cobro) antes de operar el programa;
revisar el texto de las preguntas frecuentes; revisar a ojo en celular real.

## S56 · El site sube a `acordia-render` 0.4.2: acorde `7(b13)` (2026-11-09)

La librería (RD13) reconoce `A7(b13)` / `A7b13` como acorde propio (A C# E G F, con la quinta justa), con notas, teclado y
sonido; sin forma estándar, así que el tema lleva una forma propia. El site sube la dependencia para que un tema publicado
con ese acorde no salga como texto. Sin otros cambios.

## S57 · El site sube a `acordia-render` 0.4.3: cejilla en las formas propias (2026-11-10)

La librería (RD14) deduce la cejilla de las formas propias, que no traían el dato: solo en el traste más bajo, si 2 o más
cuerdas lo pisan y ninguna cuerda intermedia está al aire, apagada o más baja. Las formas de chords-db no cambian.
El site sube la dependencia; sin otros cambios. Limitación: formas propias como D (`x x 0 2 3 2`) o A (`x 0 2 2 2 0`)
también muestran cejilla.

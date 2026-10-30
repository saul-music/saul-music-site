# Acordia · Prompts para integrar y seguir construyendo

Paquete de mockups para `saul-music-site`: tres páginas en HTML sobre **Bootstrap 5.3.3** con un tema de marca hecho solo con variables CSS (`--ac-*` → `--bs-*`). No hay build: se copian a la raíz y se publican con el pipeline actual.

## 1. Qué trae y dónde va

```
saul-music-site/
├── index.html        # REEMPLAZA · Inicio: hero, cómo funciona, barrios, biblioteca, guías, planes
├── style.css         # REEMPLAZA · tema de marca sobre Bootstrap
├── cancion.html      # NUEVO · página de canción: acordes, estructura, rasgueo, práctica
├── guias.html        # NUEVO · directorio de guías con filtros y modal de conexión
├── acordia.js        # NUEVO · tema claro/oscuro, diagramas de acorde, práctica, filtro, modal
├── PROMPTS.md        # NUEVO · este archivo (queda en el repo, NO se publica)
├── README.md         # se actualiza (sección "Páginas")
├── .gitignore        # sin cambios
├── bootstrap/github-pages.sh   # sin cambios
└── .github/workflows/pipeline.yml  # cambian 2 pasos: "revisar" y "preparar solo los archivos públicos"
```

- Bootstrap y las fuentes (Marcellus, Work Sans) se cargan por CDN con `integrity`: no se publica ningún archivo de Bootstrap.
- Ningún formulario envía datos. El buscador navega a `cancion.html`; el de "ser guía" está desactivado. Cumple la regla de repo público.
- Lo único que guarda el navegador (localStorage) es el tema elegido y los pasos de práctica marcados, solo en ese navegador.

---

## 2. Prompt · Integrar el paquete en el repo

Copia los 6 archivos del paquete a la raíz del repo y pega esto en Claude Code:

```text
Trabaja en el repo saul-music-site. Reglas del repo:
- Es público: no agregues datos de usuarios ni de investigación, solo contenido del sitio.
- Todo cambio va por rama y PR hacia main. Usa la rama feat/acordia-mockups.
- El deploy solo publica lo listado en el paso "preparar solo los archivos públicos"
  de .github/workflows/pipeline.yml. Lo que no esté ahí no se publica.
- Las acciones del pipeline están fijadas por SHA: no las cambies ni las actualices.

Tarea:
1. Crea la rama feat/acordia-mockups desde main.
2. Los archivos index.html, style.css, cancion.html, guias.html, acordia.js y PROMPTS.md
   ya están en la raíz. index.html y style.css reemplazan a los anteriores.
   No los reformatees ni cambies su contenido.
3. En pipeline.yml, job "deploy", paso "preparar solo los archivos públicos":
   copia a _site/ index.html, style.css, cancion.html, guias.html y acordia.js.
   PROMPTS.md y README.md NO se copian. No toques nada más del job.
4. En el job "check" ("revisar"):
   a) comprueba que los cinco archivos públicos existan y no estén vacíos;
   b) comprueba que cada href="X.html" de los .html apunte a un archivo que exista;
   c) comprueba que cada .html cargue style.css y acordia.js.
5. README.md: agrega una sección "Páginas" (ver bloque README de PROMPTS.md).
6. Verifica en local con `python3 -m http.server 8000`:
   - las tres páginas cargan sin errores en consola;
   - el botón de tema cambia entre Noche y Marfil y se recuerda al recargar;
   - el menú móvil abre a 375 px y no hay scroll horizontal;
   - en cancion.html las pestañas cambian y se dibujan 4 diagramas de acorde;
   - en guias.html el filtro cambia el conteo y el modal muestra nombre y precio del guía.
7. Commit: "feat: mockups de Acordia con tema Bootstrap de marca".
   Abre el PR hacia main con la lista de archivos nuevos y el cambio al pipeline.
```

### Cambio esperado en `pipeline.yml`

Ajusta los nombres a como estén escritos tus pasos; las acciones fijadas por SHA no se tocan.

```yaml
  check:
    # ...
    steps:
      # ... checkout fijado por SHA, sin cambios
      - name: revisar
        run: |
          set -eu
          PUBLICOS="index.html style.css cancion.html guias.html acordia.js"
          for f in $PUBLICOS; do
            test -s "$f" || { echo "Falta o está vacío: $f"; exit 1; }
          done
          for ref in $(grep -oh 'href="[a-z0-9-]*\.html' *.html | sed 's/href="//' | sort -u); do
            test -f "$ref" || { echo "Enlace roto: $ref"; exit 1; }
          done
          for p in *.html; do
            grep -q 'href="style.css"' "$p" || { echo "$p no carga style.css"; exit 1; }
            grep -q 'src="acordia.js"' "$p"  || { echo "$p no carga acordia.js"; exit 1; }
          done

  deploy:
    # ... needs: [check], entorno github-pages, permisos sin cambios
    steps:
      # ...
      - name: preparar solo los archivos públicos
        run: |
          mkdir -p _site
          cp index.html style.css cancion.html guias.html acordia.js _site/
      # configure-pages, upload-pages-artifact, deploy-pages: sin cambios
```

### Bloque para `README.md`

```markdown
## Páginas

| Archivo | Qué es |
|---|---|
| `index.html` | Inicio de Acordia |
| `cancion.html` | Página de una canción (mockup) |
| `guias.html` | Directorio de guías (mockup) |
| `style.css` | Tema de marca sobre Bootstrap 5.3.3 |
| `acordia.js` | Tema, diagramas de acorde, práctica, filtro y modal |

Para publicar una página o asset nuevo, agrégalo al paso "preparar solo los archivos
públicos" del deploy **y** a la variable `PUBLICOS` del paso "revisar". Si no, no se publica.
`PROMPTS.md` explica el sistema y trae la plantilla para páginas nuevas.
```

---

## 3. Prompt · Crear una página nueva (plantilla HTML incluida)

Sirve para cualquier página futura: `barrio-cueca.html`, `plus.html`, `sobre.html`, `ser-guia.html`. Cambia lo que está entre corchetes.

````text
Crea [nombre].html en la raíz de saul-music-site usando el sistema de Acordia.
Parte EXACTAMENTE de esta plantilla. No cambies el <head>, la navbar, el aviso ni el footer,
salvo el <title>, la description y la clase "active" del enlace que corresponda.

```html
<!doctype html>
<html lang="es-CL" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>[Título de la página] · Acordia</title>
  <meta name="description" content="[Una frase clara sobre la página]">
  <meta name="theme-color" content="#191430">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 56'%3E%3Crect width='48' height='56' fill='%23191430'/%3E%3Cpath d='M6 54V24a18 18 0 0 1 36 0v30' fill='none' stroke='%23D4A64A' stroke-width='5'/%3E%3Ccircle cx='24' cy='16' r='4' fill='%235FB39B'/%3E%3C/svg%3E">
  <script>(function(){var t="dark";try{t=localStorage.getItem("acordia-tema")||"dark"}catch(e){}document.documentElement.setAttribute("data-bs-theme",t)})();</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Marcellus&family=Work+Sans:wght@400;500;600&display=swap">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
  <link rel="stylesheet" href="style.css">
</head>
<body>

  <div class="ac-proto">Prototipo en investigación · los temas y guías que ves son de ejemplo</div>

  <nav class="navbar navbar-expand-md sticky-top" aria-label="Principal">
    <div class="container">
      <a class="ac-brand navbar-brand" href="index.html" aria-label="Acordia, inicio">
        <svg viewBox="0 0 48 56" aria-hidden="true">
          <path class="ac-logo-arch" d="M6 54V24a18 18 0 0 1 36 0v30" fill="none" stroke-width="4"/>
          <g class="ac-logo-string" stroke-width="1.6">
            <line x1="14" y1="26" x2="14" y2="54"/><line x1="19" y1="26" x2="19" y2="54"/>
            <line x1="24" y1="26" x2="24" y2="54"/><line x1="29" y1="26" x2="29" y2="54"/>
            <line x1="34" y1="26" x2="34" y2="54"/>
          </g>
          <circle class="ac-logo-dot" cx="24" cy="16" r="3"/>
        </svg>
        <span class="ac-brand-name">ACORDIA</span>
      </a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav" aria-controls="nav" aria-expanded="false" aria-label="Abrir menú">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="nav">
        <ul class="navbar-nav ms-md-4 me-auto gap-md-2">
          <li class="nav-item"><a class="nav-link" href="cancion.html">Biblioteca</a></li>
          <li class="nav-item"><a class="nav-link" href="guias.html">Guías</a></li>
          <li class="nav-item"><a class="nav-link" href="index.html#planes">Planes</a></li>
        </ul>
        <div class="d-flex align-items-center gap-2 pb-3 pb-md-0">
          <button class="btn btn-ghost ac-theme-toggle" type="button" data-ac-theme-toggle aria-label="Cambiar tema">
            <svg class="ac-icon-sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5" fill="currentColor"/><g stroke="currentColor" stroke-width="2"><path d="M12 1v3M12 20v3M1 12h3M20 12h3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/></g></svg>
            <svg class="ac-icon-moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11z" fill="currentColor"/></svg>
          </button>
          <a class="btn btn-outline-primary" href="index.html#planes">Entrar a Acordia</a>
        </div>
      </div>
    </div>
  </nav>

  <main>
    <section class="ac-section">
      <div class="container">
        <div class="ac-section-head">
          <span class="ac-eyebrow">[Antetítulo]</span>
          <h1 class="display-5 m-0">[Título]</h1>
          <p>[Bajada clara: qué encuentra la persona aquí]</p>
        </div>
        <!-- [contenido] -->
      </div>
    </section>
  </main>

  <footer class="ac-footer">
    <div class="container d-grid gap-3">
      <div class="d-flex flex-wrap justify-content-between gap-3 align-items-center">
        <span class="ac-footer-brand">Acordia. Donde se respira música.</span>
        <nav class="d-flex flex-wrap gap-3" aria-label="Pie de página">
          <a href="cancion.html">Biblioteca</a><a href="guias.html">Guías</a><a href="index.html#planes">Planes</a>
        </nav>
      </div>
      <p class="m-0">Acordia publica acordes, estructura y rasgueo. No publica letras de terceros. Un proyecto de SAÚL.</p>
    </div>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
  <script src="acordia.js"></script>
</body>
</html>
```

Reglas técnicas:
- Todo color sale de las variables de style.css: --ac-bg, --ac-surface, --ac-line, --ac-fg,
  --ac-fg-muted, --ac-accent, --ac-second, --ac-fill, --ac-on-fill, --ac-fill-2, --ac-on-fill-2.
  Nunca escribas un hex en el HTML, salvo dentro de ilustraciones SVG de color fijo.
- Sin estilos en línea. Si falta algo, agrega una clase .ac-* en el bloque 7 de style.css.
- JS: nada de <script> en línea más allá del de tema del <head>. Si hace falta comportamiento,
  agrégalo a acordia.js activado por un atributo data-ac-*.
- Usa componentes de Bootstrap (grid, card, nav-pills, form-control, list-group, modal) y los
  bloques de la sección 4 de PROMPTS.md.

Estilo de marca (obligatorio):
- Plano y artístico, como serigrafía o grabado en linóleo: colores sólidos, formas geométricas,
  mucho espacio vacío. Sin fotos, degradados, sombras, brillos ni 3D. Nada "realista de IA".
- El arco (portal) es la forma firma: úsalo como marco (.ac-arch), avatar (.ac-avatar) o divisor (.ac-frieze).
- Marcellus solo en títulos; Work Sans en texto y botones.
- Oro para la acción principal (.btn-primary), jade para lo positivo y lo secundario (.btn-jade, .ac-chip-ok).

Contenido:
- Página: [qué es y para quién].
- Secciones: [lista].
- La poesía va en la marca, la claridad en los botones: cada botón dice exactamente qué hace.
- Nada de letras de canciones de terceros. Temas y artistas como "[Tema de ejemplo]" /
  "[Artista de ejemplo]", marcados con <span class="ac-chip ac-chip-example">Ejemplo</span>.
- Ningún formulario envía datos: usa data-ac-demo="destino.html" o déjalo desactivado.

Al terminar:
- Agrega [nombre].html al paso "preparar solo los archivos públicos" y a PUBLICOS en "revisar".
- Agrega la fila a la tabla "Páginas" del README.
- Enlázala desde la navbar o el footer de todas las páginas si corresponde.
- Revisa a 375 px y 1280 px, en Noche y en Marfil, sin scroll horizontal.
````

---

## 4. Bloques HTML listos para copiar

Todos usan solo clases de Bootstrap + `.ac-*`. Funcionan en Noche y Marfil sin cambios.

### Cabecera de sección
```html
<section class="ac-section" id="[id]">
  <div class="container">
    <div class="ac-section-head">
      <span class="ac-eyebrow">[Antetítulo]</span>
      <h2>[Título de sección]</h2>
      <p>[Bajada]</p>
    </div>
    <!-- contenido -->
  </div>
</section>
```

### Botones
```html
<a class="btn btn-primary" href="#">[Acción principal]</a>        <!-- oro relleno -->
<a class="btn btn-outline-primary" href="#">[Acción secundaria]</a> <!-- oro contorno -->
<a class="btn btn-jade" href="#">[Acción positiva]</a>            <!-- jade relleno -->
<a class="btn btn-ghost" href="#">[Acción neutra]</a>             <!-- solo línea -->
```

### Fichas
```html
<span class="ac-chip">Cueca</span>
<span class="ac-chip ac-chip-chord">Am</span>
<span class="ac-chip ac-chip-ok">Disponible hoy</span>
<span class="ac-chip ac-chip-example">Ejemplo</span>
```

### Tarjeta de canción (Biblioteca)
```html
<div class="col">
  <a class="card h-100" href="cancion.html">
    <div class="card-body d-grid gap-3">
      <div class="d-flex justify-content-between align-items-start gap-2">
        <span class="ac-chip ac-chip-example">Ejemplo</span>
        <span class="small text-body-secondary">[Barrio]</span>
      </div>
      <div><h3 class="h4 mb-1">[Tema de ejemplo]</h3><p class="m-0 text-body-secondary">[Artista de ejemplo]</p></div>
      <div class="d-flex flex-wrap gap-2">
        <span class="ac-chip ac-chip-chord">G</span><span class="ac-chip ac-chip-chord">D</span>
      </div>
      <div class="d-flex flex-wrap gap-3 small text-body-secondary ac-mono"><span>Nivel inicial</span><span>4/4 · 92 bpm</span></div>
    </div>
  </a>
</div>
```
Va dentro de `<div class="row row-cols-1 row-cols-md-3 g-3">`.

### Diagrama de acorde (lo dibuja acordia.js)
```html
<div class="ac-chord" data-name="Am" data-frets="x 0 2 2 1 0"></div>
```
Trastes de 6ª (grave) a 1ª (aguda): número = traste, `0` = al aire, `x` = no suena. Si el traste más alto pasa de 4, se dibuja desde el traste más bajo con su número al lado.

### Estructura por compases
```html
<h2 class="h5 m-0">Estrofa <span class="text-body-secondary fw-normal ac-mono">× 2</span></h2>
<div class="ac-bars">
  <div class="ac-bar">G</div><div class="ac-bar">C</div><div class="ac-bar">D</div><div class="ac-bar is-repeat">%</div>
</div>
```

### Rasgueo (8 corcheas)
```html
<div class="ac-strum" role="img" aria-label="Patrón: abajo, nada, abajo, arriba, nada, arriba, abajo, arriba">
  <div class="ac-strum-cell is-down">↓</div><div class="ac-strum-cell"></div>
  <div class="ac-strum-cell is-down">↓</div><div class="ac-strum-cell is-up">↑</div>
  <div class="ac-strum-cell"></div><div class="ac-strum-cell is-up">↑</div>
  <div class="ac-strum-cell is-down">↓</div><div class="ac-strum-cell is-up">↑</div>
</div>
```

### Ruta de práctica con progreso (se guarda en el navegador)
```html
<span class="small text-body-secondary ac-mono" id="practica-label">0 de 2 pasos</span>
<div class="progress mb-4" role="progressbar" aria-label="Avance de práctica" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
  <div class="progress-bar" id="practica-bar" style="width:0%"></div>
</div>
<div class="list-group" data-ac-practice="[id-del-tema]" data-ac-progress="#practica-bar" data-ac-progress-label="#practica-label">
  <label class="list-group-item d-flex gap-3 py-3"><input class="form-check-input flex-shrink-0" type="checkbox"><span><strong>[Paso]</strong><br><span class="small text-body-secondary">[Detalle]</span></span></label>
  <label class="list-group-item d-flex gap-3 py-3"><input class="form-check-input flex-shrink-0" type="checkbox"><span><strong>[Paso]</strong><br><span class="small text-body-secondary">[Detalle]</span></span></label>
</div>
```
(El `style="width:0%"` de la barra es la única excepción a "sin estilos en línea": lo actualiza acordia.js.)

### Tarjeta de guía (filtrable)
```html
<div class="col" data-barrio="Cueca,Nueva Canción" data-inst="Guitarra" data-modo="linea,presencial" data-hoy="1">
  <div class="card h-100"><div class="card-body d-grid gap-3 align-content-start">
    <div class="d-flex gap-3 align-items-center">
      <span class="ac-avatar" aria-hidden="true">[XY]</span>  <!-- .ac-avatar.is-oro para alternar -->
      <div class="d-grid"><h2 class="h5 m-0">[Nombre I.]</h2><span class="small text-body-secondary">[Comuna] · en línea</span></div>
    </div>
    <div class="d-flex flex-wrap gap-2"><span class="ac-chip">Cueca</span><span class="ac-chip">Guitarra</span></div>
    <p class="m-0 small text-body-secondary">[Una línea sobre qué enseña]</p>
    <div class="d-flex justify-content-between align-items-center gap-2">
      <span class="ac-chip ac-chip-ok">Disponible hoy</span>
      <span class="ac-mono fw-semibold">$12.000 <span class="small fw-normal text-body-secondary">/ clase</span></span>
    </div>
    <button class="btn btn-primary" type="button" data-bs-toggle="modal" data-bs-target="#conectar" data-guia="[Nombre I.]" data-precio="$12.000">Conectar</button>
  </div></div>
</div>
```

### Filtro (acordia.js lo conecta solo)
```html
<form class="card mb-4" aria-label="Filtrar guías" data-ac-filter="#resultados" data-ac-count="#conteo" data-ac-empty="#sin-resultados">
  <div class="card-body"><div class="row g-3 align-items-end">
    <div class="col-sm-6 col-lg-3">
      <label class="form-label" for="f-barrio">Barrio</label>
      <select class="form-select" id="f-barrio" data-ac-key="barrio"><option value="">Todos</option><option>Cueca</option></select>
    </div>
    <div class="col-sm-6 col-lg-3">
      <div class="form-check form-switch mb-2">
        <input class="form-check-input" type="checkbox" role="switch" id="f-hoy" value="1" data-ac-key="hoy">
        <label class="form-check-label" for="f-hoy">Disponible hoy</label>
      </div>
    </div>
  </div></div>
</form>
<p class="m-0 text-body-secondary ac-mono" id="conteo" aria-live="polite"></p>
<div class="row row-cols-1 row-cols-md-2 row-cols-xl-3 g-3" id="resultados"><!-- tarjetas --></div>
<div class="card mt-3 d-none" id="sin-resultados"><div class="card-body">No hay resultados con esos filtros.</div></div>
```
`data-ac-key="barrio"` filtra contra `data-barrio` de cada tarjeta (lista separada por comas).

### Modal de conexión
```html
<div class="modal fade" id="conectar" data-ac-connect tabindex="-1" aria-labelledby="conectar-titulo" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered"><div class="modal-content">
    <div class="modal-header">
      <h2 class="modal-title h4" id="conectar-titulo">Conectar con <span data-guia-nombre>tu guía</span></h2>
      <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
    </div>
    <div class="modal-body">
      <table class="table m-0 ac-mono"><tbody>
        <tr><td>Conexión Acordia (primera vez)</td><td class="text-end">$3.990</td></tr>
        <tr><td>Clase, se paga al guía</td><td class="text-end" data-guia-precio>—</td></tr>
      </tbody></table>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn btn-ghost" data-bs-dismiss="modal">Volver</button>
      <button type="button" class="btn btn-primary" disabled>Reservar (prototipo)</button>
    </div>
  </div></div>
</div>
```

### Tarjeta de plan
```html
<div class="col">
  <div class="card h-100 ac-plan-featured"> <!-- quita ac-plan-featured si no es el destacado -->
    <div class="card-body d-grid gap-3 align-content-start">
      <h3 class="h4 m-0">[Plan]</h3>
      <p class="ac-price ac-mono m-0">$2.990 <small>al mes</small></p>
      <ul class="ac-list"><li>[Beneficio]</li><li>[Beneficio]</li></ul>
      <a class="btn btn-jade mt-2" href="#">[Acción]</a>
    </div>
  </div>
</div>
```

### Ventana en arco y friso
```html
<div class="ac-arch p-4 pt-5 text-center">[contenido enmarcado por el portal]</div>
<div class="ac-frieze" aria-hidden="true"></div>
```

---

## 5. Prompts para iterar cada mockup

### Inicio (`index.html`)
```text
En index.html de Acordia, [cambio]. Mantén: el hero con la ilustración del portal,
el titular "Donde se respira música." y la bajada "Aprende canciones chilenas.
Acordes gratis y profes disponibles cuando te trabas." Mantén los precios:
Biblioteca $0; conexión $3.990 la primera vez con cada guía; Acordia Plus $2.990
al mes o $24.990 al año, con 1 conexión al mes y garantía de reemplazo.
Usa solo los bloques de la sección 4 de PROMPTS.md y las variables --ac-* de style.css.
Sin estilos ni scripts en línea.
```

### Canción (`cancion.html`)
```text
En cancion.html de Acordia, [cambio]. La página muestra acordes, estructura por compases,
rasgueo y una ruta de práctica; nunca la letra. Los acordes se declaran con
<div class="ac-chord" data-name="Am" data-frets="x 0 2 2 1 0"></div> y los dibuja acordia.js.
La ruta de práctica es una .list-group con data-ac-practice="id-del-tema".
Mantén el lateral "¿Te trabaste?" con guías de ejemplo y el botón "Encontrar a tu guía".
```

### Guías (`guias.html`)
```text
En guias.html de Acordia, [cambio]. Cada guía es una .col con data-barrio, data-inst,
data-modo y data-hoy, que filtra el formulario data-ac-filter (lógica en acordia.js).
Los avatares son arcos con iniciales (.ac-avatar), sin fotos. Todos los perfiles son de
ejemplo y siguen marcados así. El modal data-ac-connect muestra $3.990 de conexión y el
precio de clase del guía; "Reservar" queda desactivado mientras sea prototipo.
```

---

## 6. Prompt · Cambiar la marca sin tocar el HTML

```text
En style.css de Acordia cambia solo el bloque 1 (tokens de marca) y, si hace falta,
los bloques 2 y 3 (roles en modo Noche y Marfil). No cambies los bloques 4 en adelante:
ahí Bootstrap lee los tokens. Si cambias un color con versión -rgb, actualiza también
esa versión. Comprueba contraste AA de --ac-fg sobre --ac-bg y de --ac-on-fill sobre
--ac-fill en ambos modos.
```

## 7. Referencia del tema

| Token | Noche (por defecto) | Marfil |
|---|---|---|
| `--ac-bg` | #191430 | #F1ECE2 |
| `--ac-surface` | #221C40 | #E7E0D1 |
| `--ac-line` | #342C5C | #D3C9B4 |
| `--ac-fg` | #F1ECE2 | #191430 |
| `--ac-fg-muted` | #BCB5CC | #57506D |
| `--ac-accent` (texto y enlaces) | #D4A64A | #7A5712 |
| `--ac-second` (jade texto) | #5FB39B | #2E6F5E |
| `--ac-fill` / `--ac-on-fill` (botón principal) | #D4A64A / #191430 | #D4A64A / #191430 |
| `--ac-fill-2` / `--ac-on-fill-2` (botón jade) | #5FB39B / #191430 | #2E6F5E / #F1ECE2 |

El modo se cambia con `data-bs-theme="dark"` o `"light"` en `<html>`; el botón de la navbar lo alterna y lo recuerda en el navegador.

### Bloques de `style.css`
1. Tokens de marca · 2. Roles Noche · 3. Roles Marfil · 4. Bootstrap ← tokens · 5. Botones · 6. Componentes Bootstrap · 7. Piezas propias de Acordia (`.ac-*`)

### Atributos que activa `acordia.js`
| Atributo | Qué hace |
|---|---|
| `data-ac-theme-toggle` | Alterna Noche/Marfil y lo recuerda |
| `.ac-chord[data-frets]` | Dibuja el diagrama del acorde |
| `data-ac-practice` | Guarda los pasos marcados y mueve la barra de progreso |
| `form[data-ac-filter]` | Filtra tarjetas por `data-*` y actualiza el conteo |
| `.modal[data-ac-connect]` | Copia `data-guia` y `data-precio` del botón al modal |
| `form[data-ac-demo]` | Evita el envío; navega al destino si lo hay |

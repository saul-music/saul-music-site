"""Genera las páginas de canción y las tarjetas de la Biblioteca desde las transcripciones propias.

Cada página tiene solo la sección Estructura, con tres pestañas: Básico (acordes mayores y menores),
Intermedio (con extensiones) y Avanzado (extensiones, bajos e inversiones, y arreglos con tab). Una
versión sin contenido muestra «Próximamente».

Por defecto solo incluye los temas publicables: revisados y con los derechos resueltos (V2).
Con preview = True incluye también los borradores, marcados como tales y con noindex, para
revisarlos en local; esa salida no debe copiarse al sitio.

Uso:
    python -m musicsite.acordes pages --dir ../acordes-local --out ../vista-previa --preview
    python -m musicsite.acordes library --dir ../acordes-local --index src/musicsite/web/index.html
"""

import html
import shutil
import tomllib
from pathlib import Path

from musicsite.acordes import REPEAT, REPERTOIRE, parse_score, validate_file
from musicsite.app import WEB_DIR
from musicsite.profes import avatar, teachers_for

LIBRARY_START = "<!-- biblioteca:inicio -->"
LIBRARY_END = "<!-- biblioteca:fin -->"
SHOWN_CHORDS = 4

MODES = [
    ("basico", "Básico", "Acordes mayores y menores, sin extensiones."),
    ("intermedio", "Intermedio", "Con extensiones: séptimas, sus, add y similares."),
    ("avanzado", "Avanzado", "Extensiones, bajos e inversiones, y arreglos con tab."),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def structure(sections: list[dict]) -> str:
    blocks = []
    for section in sections:
        times = section.get("repeticiones", 1)
        label = (
            f' <span class="text-body-secondary fw-normal ac-mono">× {times}</span>'
            if times > 1
            else ""
        )
        bars = "".join(f'<div class="ac-bar">{esc(t)}</div>' for t in section.get("compases", []))
        blocks.append(
            '          <div class="d-grid gap-2">\n'
            f'            <h2 class="h5 m-0">{esc(section.get("nombre", ""))}{label}</h2>\n'
            f'            <div class="ac-bars">{bars}</div>\n'
            "          </div>"
        )
    return "\n".join(blocks)


def load_song(path: Path) -> dict:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    compact, _ = parse_score(data.get("partitura", ""))
    data["secciones"] = list(data.get("secciones", [])) + compact
    for mode in ("intermedio", "avanzado"):
        data[mode + "_secciones"], _ = parse_score(data.get(mode, {}).get("partitura", ""))
    data["tab"] = data.get("avanzado", {}).get("tab", "").strip("\n")
    return data


def shell() -> tuple[str, str]:
    """Cabecera (hasta <main>) y pie de las páginas del sitio, tomados de artistas.html."""
    page = (WEB_DIR / "artistas.html").read_text(encoding="utf-8")
    head = page[: page.index("<main")]
    foot = page[page.index("  <footer") :]
    head = head.replace(
        'class="nav-link active" aria-current="page" href="artistas.html"',
        'class="nav-link" href="artistas.html"',
    )
    return head, foot


def mode_pane(key: str, song: dict, no_harmony: bool) -> str:
    """Contenido de una pestaña: solo la estructura de ese modo, o «Próximamente»."""
    if key == "basico":
        sections = song.get("secciones", [])
        body = structure(sections) if sections else ""
        if no_harmony and not sections:
            body = (
                '<p class="text-body-secondary m-0">Este tema no tiene una base armónica estable '
                "que podamos mostrar.</p>"
            )
    else:
        sections = song.get(key + "_secciones", [])
        tab = song.get("tab", "") if key == "avanzado" else ""
        body = structure(sections) if sections else ""
        if tab:
            body += f'\n          <pre class="ac-mono small m-0">{esc(tab)}</pre>'
        if not body:
            body = (
                '<p class="text-body-secondary m-0"><span class="ac-chip">Próximamente</span></p>'
            )
    return body


def teacher_panel(slug: str, title: str) -> str:
    """Panel fijo bajo la cabecera: quién puede enseñar este tema, según lo que cada profe declaró."""
    teachers = teachers_for(slug)
    if not teachers:
        return (
            '    <aside class="card mb-4" aria-label="Guías de este tema"><div class="card-body">'
            '<p class="m-0 text-body-secondary">Aún no hay guías que enseñen este tema.</p>'
            "</div></aside>\n"
        )
    count = len(teachers)
    names = ", ".join(esc(t["nombre"]) for t in teachers[:2])
    more = f" y {count - 2} más" if count > 2 else ""
    example = (
        ' · <span class="ac-chip ac-chip-example">Perfiles de ejemplo</span>'
        if any(t.get("mock") for t in teachers)
        else ""
    )
    avatars = "".join(avatar(t, i) for i, t in enumerate(teachers[:3]))
    noun = "guía puede" if count == 1 else "guías pueden"
    return f"""    <aside class="card mb-4 ac-plan-featured" aria-label="Guías de este tema">
      <div class="card-body d-flex flex-wrap gap-3 align-items-center justify-content-between">
        <div class="d-flex gap-3 align-items-center">
          <div class="d-flex gap-2">{avatars}</div>
          <div class="d-grid">
            <strong>{count} {noun} enseñarte «{esc(title)}»</strong>
            <span class="small text-body-secondary">{names}{more}{example}</span>
          </div>
        </div>
        <a class="btn btn-primary" href="guias.html?tema={esc(slug)}">Ver guías</a>
      </div>
    </aside>

"""


def render(song: dict, status: str, preview: bool) -> str:
    head, foot = shell()
    title = esc(song["titulo"])
    head = head.replace("<title>Artistas · Acordia</title>", f"<title>{title} · Acordia</title>")
    head = head.replace(
        "Los artistas del repertorio inicial de la Biblioteca de Acordia, con enlace a su perfil en MusicaPopular.cl.",
        f"{title}: estructura por compases, con versiones básica, intermedia y avanzada.",
    )
    if preview:
        head = head.replace("</head>", '  <meta name="robots" content="noindex">\n</head>')

    badge = ""
    if preview:
        badge = f'<span class="ac-chip ac-chip-example">Borrador sin revisar ({esc(status)})</span>'
    facts = [
        ("Tono", song.get("tono")),
        ("Cejilla", song.get("cejilla")),
        ("Compás", song.get("compas")),
        ("Tempo", f"{song['bpm']} bpm" if song.get("bpm") else ""),
        ("Nivel", str(song.get("nivel", "")).capitalize()),
    ]
    facts_html = "\n".join(
        f'        <div><dt class="small text-body-secondary fw-normal">{label}</dt>'
        f'<dd class="m-0 fw-semibold">{esc(value)}</dd></div>'
        for label, value in facts
        if value
    )
    no_harmony = bool(song.get("sin_base_armonica")) and not song.get("acordes")
    form = song.get("forma", "")
    form_html = f'<p class="text-body-secondary m-0">{esc(form)}</p>' if form else ""
    note = (
        f'<p class="small text-body-secondary m-0">Cada casilla es un compás. {REPEAT} repite el '
        "compás anterior. Escucha la grabación original para seguir la letra.</p>"
    )
    tabs, panes = [], []
    for index, (key, label, description) in enumerate(MODES):
        active = index == 0
        tabs.append(
            f'      <li class="nav-item" role="presentation"><button class="nav-link{" active" if active else ""}" '
            f'id="t-{key}" data-bs-toggle="pill" data-bs-target="#p-{key}" type="button" role="tab" '
            f'aria-controls="p-{key}" aria-selected="{"true" if active else "false"}">{label}</button></li>'
        )
        panes.append(
            f'      <section class="tab-pane fade{" show active" if active else ""}" id="p-{key}" '
            f'role="tabpanel" aria-labelledby="t-{key}" tabindex="0">\n'
            '        <div class="d-grid gap-4">\n'
            f'          <p class="text-body-secondary m-0">{description}</p>\n'
            f"          {form_html if active else ''}\n"
            f"{mode_pane(key, song, no_harmony)}\n"
            f"          {note if active else ''}\n"
            "        </div>\n"
            "      </section>"
        )
    main = f"""<main class="container py-4 py-lg-5">
    <header class="d-grid gap-3 pb-4 mb-4 border-bottom">
      <div class="d-flex flex-wrap gap-2 align-items-center">
        {badge}
        <a class="ac-eyebrow" href="index.html#biblioteca">La Biblioteca</a>
      </div>
      <h1 class="display-5 m-0">{title}</h1>
      <p class="m-0 fs-5 text-body-secondary">{esc(song["artista"])}</p>
      <dl class="d-flex flex-wrap gap-4 m-0 ac-mono">
{facts_html}
      </dl>
    </header>

{teacher_panel(song["slug"], song["titulo"])}    <ul class="nav nav-pills mb-4 flex-wrap" id="tabs" role="tablist">
{chr(10).join(tabs)}
    </ul>

    <div class="tab-content">
{chr(10).join(panes)}
    </div>
  </main>

"""
    return head + main + foot


def card(song: dict, slug: str, status: str) -> str:
    """Tarjeta de la Biblioteca: acordes básicos resumidos, nivel y tempo."""
    published = status == "publicable"
    chords = song.get("acordes", [])
    chips = "".join(
        f'<span class="ac-chip ac-chip-chord">{esc(c)}</span>' for c in chords[:SHOWN_CHORDS]
    )
    if len(chords) > SHOWN_CHORDS:
        chips += f'<span class="ac-chip">+{len(chords) - SHOWN_CHORDS}</span>'
    if song.get("tipo") == "instrumental" and not chords:
        chips = '<span class="ac-chip">Instrumental</span>'
    left = "" if published else '<span class="ac-chip">Próximamente</span>'
    right = (
        f'<span class="small text-body-secondary">{esc(song["barrio"])}</span>'
        if song.get("barrio")
        else ""
    )
    facts = []
    if song.get("nivel"):
        facts.append(f"Nivel {esc(song['nivel'])}")
    meter = esc(song.get("compas", ""))
    if meter and song.get("bpm"):
        facts.append(f"{meter} · {song['bpm']} bpm")
    elif meter:
        facts.append(meter)
    facts_html = "".join(f"<span>{fact}</span>" for fact in facts)
    tag, attrs = ("a", f' href="cancion-{slug}.html"') if published else ("div", "")
    return f"""          <div class="col">
            <{tag} class="card h-100"{attrs}>
              <div class="card-body d-grid gap-3">
                <div class="d-flex justify-content-between align-items-start gap-2">{left}{right}</div>
                <div><h3 class="h4 mb-1">{esc(song["titulo"])}</h3><p class="m-0 text-body-secondary">{esc(song["artista"])}</p></div>
                <div class="d-flex flex-wrap gap-2">{chips}</div>
                <div class="d-flex flex-wrap gap-3 small text-body-secondary ac-mono">{facts_html}</div>
              </div>
            </{tag}>
          </div>"""


def library_html(directory: Path) -> str:
    cards = []
    for slug, *_ in REPERTOIRE:
        path = directory / f"{slug}.toml"
        if not path.exists():
            continue
        report = validate_file(path)
        status = (
            "publicable" if not report.errors and report.status == "publicable" else report.status
        )
        cards.append(card(load_song(path), slug, status))
    return (
        '        <div class="row row-cols-1 row-cols-md-3 g-3">\n'
        + "\n".join(cards)
        + "\n        </div>"
    )


def update_library(directory: Path, index: Path) -> int:
    """Reemplaza las tarjetas de index.html entre las marcas de la Biblioteca."""
    page = index.read_text(encoding="utf-8")
    start = page.index(LIBRARY_START) + len(LIBRARY_START)
    end = page.index(LIBRARY_END)
    block = library_html(directory)
    index.write_text(page[:start] + "\n" + block + "\n        " + page[end:], encoding="utf-8")
    return block.count('<div class="col">')


def build(directory: Path, out: Path, preview: bool = False) -> list[Path]:
    """Escribe una página por tema que corresponda y devuelve las rutas creadas."""
    allowed = {"publicable"} | ({"borrador", "revisado"} if preview else set())
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for path in sorted(directory.glob("*.toml")):
        report = validate_file(path)
        if report.errors or report.status not in allowed:
            continue
        song = load_song(path)
        target = out / f"cancion-{path.stem}.html"
        target.write_text(render(song, report.status, preview), encoding="utf-8")
        written.append(target)
    if preview and written:
        # La vista previa se abre desde el disco: necesita el tema y el script junto a las páginas.
        for asset in ("style.css", "acordia.js"):
            shutil.copy(WEB_DIR / asset, out / asset)
    return written

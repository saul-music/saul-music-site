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

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from musicsite.acordes import REPEAT, REPERTOIRE, parse_score, validate_file
from musicsite.profes import avatar, teachers_for

TEMPLATES_DIR = Path(__file__).parent / "templates"
ENV = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    keep_trailing_newline=True,
)
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


def bar_html(token: str) -> str:
    """Una casilla por compás; con guiones, cada acorde ocupa el ancho de las partes que dura."""
    parts = token.split("-") if token != REPEAT else [token]
    if len(parts) == 1:
        return f'<div class="ac-bar">{esc(token)}</div>'
    chords: list[list] = []
    for part in parts:
        if part == REPEAT and chords:
            chords[-1][1] += 1
        else:
            chords.append([part, 1])
    spans = "".join(
        f'<span class="ac-part" style="flex: {weight}">{esc(chord)}</span>'
        for chord, weight in chords
    )
    return f'<div class="ac-bar is-split">{spans}</div>'


def structure(sections: list[dict]) -> str:
    blocks = []
    for section in sections:
        times = section.get("repeticiones", 1)
        label = (
            f' <span class="text-body-secondary fw-normal ac-mono">× {times}</span>'
            if times > 1
            else ""
        )
        bars = "".join(bar_html(t) for t in section.get("compases", []))
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
        <div class="d-flex flex-wrap gap-3 align-items-center">
          <div class="d-flex gap-2 flex-shrink-0">{avatars}</div>
          <div class="d-grid" style="min-width: 0; grid-template-columns: minmax(0, 1fr)">
            <strong>{count} {noun} enseñarte «{esc(title)}»</strong>
            <span class="small text-body-secondary">{names}{more}{example}</span>
          </div>
        </div>
        <a class="btn btn-primary" href="guias.html?tema={esc(slug)}">Ver guías</a>
      </div>
    </aside>

"""


def beats_per_bar(meter: str) -> int:
    """Clics por compás: el numerador (en 6/8 y 12/8 el bpm marca la corchea)."""
    try:
        return max(1, min(16, int(str(meter).split("/")[0])))
    except ValueError:
        return 4


def render(song: dict, status: str, preview: bool) -> str:
    facts = [
        ("Tono", song.get("tono")),
        ("Cejilla", song.get("cejilla")),
        ("Compás", song.get("compas")),
        ("Tempo", f"{song['bpm']} bpm" if song.get("bpm") else ""),
        ("Nivel", str(song.get("nivel", "")).capitalize()),
    ]
    no_harmony = bool(song.get("sin_base_armonica")) and not song.get("acordes")
    note = (
        f'<p class="small text-body-secondary m-0">Cada casilla es un compás. {REPEAT} repite el '
        "compás anterior. Escucha la grabación original para seguir la letra.</p>"
    )
    return ENV.get_template("cancion.html").render(
        song=song,
        status=status,
        preview=preview,
        facts=[(label, value) for label, value in facts if value],
        bpm=song.get("bpm") or 0,
        beats=beats_per_bar(song.get("compas", "4/4")),
        form=song.get("forma", ""),
        modes=MODES,
        panes={key: Markup(mode_pane(key, song, no_harmony)) for key, *_ in MODES},
        teacher_panel=Markup(teacher_panel(song["slug"], song["titulo"])),
        note=Markup(note),
    )


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
        from musicsite.app import WEB_DIR

        for asset in ("style.css", "acordia.js"):
            shutil.copy(WEB_DIR / asset, out / asset)
    return written


def render_published(directory: Path) -> dict[str, str]:
    """slug -> HTML de cada tema de `directory`. Falla si alguno no es publicable.

    Es lo que el servicio ejecuta al arrancar: un error de datos rompe el arranque (y el pipeline),
    no una visita.
    """
    pages = {}
    for path in sorted(directory.glob("*.toml")):
        report = validate_file(path)
        if report.errors or report.status != "publicable":
            raise ValueError(f"{path.name} no es publicable: {report.status} {report.errors}")
        pages[path.stem] = render(load_song(path), report.status, preview=False)
    return pages

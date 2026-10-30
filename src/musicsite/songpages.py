"""Genera las páginas de canción a partir de las transcripciones propias (carpeta local).

Por defecto solo incluye los temas publicables: revisados y con los derechos resueltos (V2).
Con preview = True incluye también los borradores, marcados como tales y con noindex, para
revisarlos en local; esa salida no debe copiarse al sitio.

Uso:
    python -m musicsite.acordes pages --dir ../acordes-local --out ../vista-previa --preview
"""

import html
import tomllib
from pathlib import Path

from musicsite.acordes import REPEAT, parse_score, validate_file
from musicsite.app import WEB_DIR

ENHARMONIC = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
# Posiciones abiertas; el resto se arma con cejilla (forma de Mi o de La).
OPEN = {
    "C": "x 3 2 0 1 0",
    "D": "x x 0 2 3 2",
    "E": "0 2 2 1 0 0",
    "G": "3 2 0 0 0 3",
    "A": "x 0 2 2 2 0",
    "Am": "x 0 2 2 1 0",
    "Dm": "x x 0 2 3 1",
    "Em": "0 2 2 0 0 0",
}
E_SHAPE = {"F": 1, "F#": 2, "G": 3, "G#": 4}  # raíz en la 6ª cuerda
A_SHAPE = {"A#": 1, "B": 2, "C": 3, "C#": 4, "D": 5, "D#": 6}  # raíz en la 5ª cuerda


def fingering(chord: str) -> str:
    """Trastes de la 6ª a la 1ª cuerda para un acorde básico (mayor o menor)."""
    minor = chord.endswith("m")
    root = chord[:-1] if minor else chord
    root = ENHARMONIC.get(root, root)
    name = root + ("m" if minor else "")
    if name in OPEN:
        return OPEN[name]
    if root in E_SHAPE:
        n = E_SHAPE[root]
        frets = [n, n + 2, n + 2, n if minor else n + 1, n, n]
    else:
        n = A_SHAPE[root]
        frets = ["x", n, n + 2, n + 2, n + 1 if minor else n + 2, n]
    return " ".join(str(fret) for fret in frets)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def chord_grid(chords: list[str]) -> str:
    cells = "\n".join(
        f'              <div class="col"><div class="ac-chord" data-name="{esc(c)}" '
        f'data-frets="{fingering(c)}"></div></div>'
        for c in chords
    )
    return f'<div class="row row-cols-2 row-cols-sm-4 g-4 py-3">\n{cells}\n            </div>'


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
            '              <div class="d-grid gap-2">\n'
            f'                <h2 class="h5 m-0">{esc(section.get("nombre", ""))}{label}</h2>\n'
            f'                <div class="ac-bars">{bars}</div>\n'
            "              </div>"
        )
    return "\n".join(blocks)


def load_song(path: Path) -> dict:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    compact, _ = parse_score(data.get("partitura", ""))
    data["secciones"] = list(data.get("secciones", [])) + compact
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


def render(song: dict, status: str, preview: bool) -> str:
    head, foot = shell()
    title = esc(song["titulo"])
    head = head.replace("<title>Artistas · Acordia</title>", f"<title>{title} · Acordia</title>")
    head = head.replace(
        "Los artistas del repertorio inicial de la Biblioteca de Acordia, con enlace a su perfil en MusicaPopular.cl.",
        f"{title}: acordes básicos y estructura.",
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
    chords = song.get("acordes", [])
    sections = song.get("secciones", [])
    no_harmony = bool(song.get("sin_base_armonica")) and not chords
    if no_harmony:
        chords_html = (
            '<p class="text-body-secondary">Este tema no tiene una base armónica estable que '
            "podamos mostrar. Mira su forma en la pestaña Estructura.</p>"
        )
    else:
        chords_html = chord_grid(chords) + (
            '\n            <p class="small text-body-secondary m-0">Cuerdas de 6ª (grave) a 1ª (aguda). '
            "Círculo vacío: al aire. Cruz: no suena.</p>"
        )
    form = song.get("forma", "")
    form_html = f'<p class="text-body-secondary m-0">{esc(form)}</p>' if form else ""
    structure_html = structure(sections) if sections else ""
    note = (
        f'<p class="small text-body-secondary m-0">Cada casilla es un compás. {REPEAT} repite el '
        "compás anterior. Escucha la grabación original para seguir la letra.</p>"
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

    <ul class="nav nav-pills mb-4 flex-wrap" id="tabs" role="tablist">
      <li class="nav-item" role="presentation"><button class="nav-link active" id="t-acordes" data-bs-toggle="pill" data-bs-target="#p-acordes" type="button" role="tab" aria-controls="p-acordes" aria-selected="true">Acordes</button></li>
      <li class="nav-item" role="presentation"><button class="nav-link" id="t-estructura" data-bs-toggle="pill" data-bs-target="#p-estructura" type="button" role="tab" aria-controls="p-estructura" aria-selected="false">Estructura</button></li>
    </ul>

    <div class="tab-content">
      <section class="tab-pane fade show active" id="p-acordes" role="tabpanel" aria-labelledby="t-acordes" tabindex="0">
            {chords_html}
      </section>
      <section class="tab-pane fade" id="p-estructura" role="tabpanel" aria-labelledby="t-estructura" tabindex="0">
        <div class="d-grid gap-4">
          {form_html}
{structure_html}
          {note}
        </div>
      </section>
    </div>
  </main>

"""
    return head + main + foot


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
    return written

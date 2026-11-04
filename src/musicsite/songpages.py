"""Genera las páginas de canción y las tarjetas de la Biblioteca desde las transcripciones propias.

Cada página tiene solo la sección Estructura, con tres pestañas: Básico (acordes mayores y menores),
Intermedio (extensiones y bajos) y Avanzado (además tabs, arreglos y tips por sección). Una
versión sin contenido muestra «Próximamente».

Por defecto solo incluye los temas publicables: revisados y con los derechos resueltos (V2).
Con preview = True incluye también los borradores, marcados como tales y con noindex, para
revisarlos en local; esa salida no debe copiarse al sitio.

Uso:
    python -m musicsite.acordes pages --dir ../acordes-local --out ../vista-previa --preview
    python -m musicsite.acordes library --dir ../acordes-local --index src/musicsite/web/index.html
"""

import hashlib
import html
import json
import re
import shutil
import tomllib
import unicodedata
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from musicsite import chordtheory as theory
from musicsite.acordes import REPEAT, REPERTOIRE, REST, parse_score, validate_file
from musicsite.profes import avatar, coverage, price, teachers_for, top_teachers

TEMPLATES_DIR = Path(__file__).parent / "templates"
ENV = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    keep_trailing_newline=True,
)
LIBRARY_START = "<!-- biblioteca:inicio -->"
LIBRARY_END = "<!-- biblioteca:fin -->"
COUNT_START = "<!-- temas:inicio -->"
COUNT_END = "<!-- temas:fin -->"
SHOWN_CHORDS = 4
WIDE_CHARS = 10  # letras de acordes en una casilla a partir de las cuales ocupa dos columnas

MODES = [
    ("basico", "Básico", "Acordes mayores y menores, sin extensiones."),
    ("intermedio", "Intermedio", "Con extensiones y bajos: séptimas, sus, add, G/B."),
    ("avanzado", "Avanzado", "Extensiones, bajos, tabs y arreglos por sección."),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


ACCIDENTALS = ((re.compile(r"(?<=[A-G0-9])#"), "\u266f"), (re.compile(r"(?<=[A-G0-9])b"), "\u266d"))


def accidentals(chord: str) -> str:
    """Solo para mostrar: F# -> F♯, Bb -> B♭, 7b9 -> 7♭9. El dato en el TOML no cambia."""
    for pattern, symbol in ACCIDENTALS:
        chord = pattern.sub(symbol, chord)
    return chord


REST_ICON = (
    '<svg viewBox="0 0 24 28" width="14" height="22" fill="none" stroke="currentColor" '
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M9 2l7 7-6 6 6 6c-4-1-6 1-5 5"/></svg>'
)


def chord_html(chord: str) -> str:
    """El acorde como botón que abre su diagrama; texto plano si no sabemos dibujarlo.
    El silencio (S22) es un símbolo sin botón ni diagrama."""
    if chord == REST:
        return f'<span class="ac-rest" role="img" aria-label="silencio">{REST_ICON}</span>'
    shown = esc(accidentals(chord))
    if theory.parse(chord) is None:
        return shown
    return (
        f'<button type="button" class="ac-chord-btn" data-chord="{esc(chord)}" '
        f'aria-haspopup="dialog">{shown}</button>'
    )


def is_wide(parts: list[str]) -> bool:
    """Una casilla con 3 o más acordes, o con nombres largos (bajos, extensiones), no cabe en un
    cuarto de la fila: ocupa el doble de ancho (S18)."""
    chords = [part for part in dict.fromkeys(parts) if part not in (REPEAT, REST)]
    return len(chords) >= 3 or sum(len(chord) for chord in chords) >= WIDE_CHARS


def bar_html(token: str, repeat: bool = False) -> str:
    """Una casilla por compás; con guiones, cada acorde ocupa el ancho de las partes que dura.

    `repeat` marca la casilla que repite el compás anterior: muestra sus acordes en gris atenuado.
    """
    parts = token.split("-") if token != REPEAT else [token]
    mark = ' is-repeat" title="Repite el compás anterior' if repeat else ""
    if is_wide(parts):
        mark = " is-wide" + mark
    if len(parts) == 1:
        return f'<div class="ac-bar{mark}">{chord_html(token)}</div>'
    chords: list[list] = []
    for part in parts:
        if part == REPEAT and chords:
            chords[-1][1] += 1
        else:
            chords.append([part, 1])
    spans = "".join(
        f'<span class="ac-part" style="flex: {weight}" data-weight="{weight}">{chord_html(chord)}</span>'
        for chord, weight in chords
    )
    return f'<div class="ac-bar is-split{mark}">{spans}</div>'


TIP_ICON = (
    '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">'
    '<path d="M12 2l2.1 6.1L20 10l-5.9 1.9L12 18l-2.1-6.1L4 10l5.9-1.9z"/>'
    '<path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z"/></svg>'
)


_INLINE_CHORD = re.compile(r"`([^`\n]+)`")


def tip_inline(text: str) -> str:
    """Escapa el texto de un tip y pone en la fuente de acordes lo que va entre `backticks` (S15).

    Se escapa primero y solo después se envuelve: nunca entra HTML del autor. Un backtick sin pareja queda tal cual."""
    return _INLINE_CHORD.sub(
        lambda m: f'<span class="ac-inline-chord">{m.group(1)}</span>', esc(text)
    )


def tip_html(tip: dict) -> str:
    """Un tip entre secciones: tarjeta con ícono que brilla; cerrada muestra solo el título gancho."""
    title, text = tip["titulo"], tip["texto"]
    key = hashlib.sha1(f"{title}|{text}".encode()).hexdigest()[:10]  # noqa: S324
    return (
        f'          <div class="ac-tip" data-ac-tip="{key}">\n'
        '            <button type="button" class="ac-tip-btn" aria-expanded="false">'
        f'<span class="ac-tip-icon">{TIP_ICON}</span>'
        f'<span class="ac-tip-label"><span class="ac-tip-kicker">Tip</span>'
        f'<span class="ac-tip-title">{tip_inline(title)}</span></span>'
        '<span class="ac-tip-chev" aria-hidden="true">\u25be</span></button>\n'
        f'            <p class="ac-tip-body" hidden>{tip_inline(text)}</p>\n'
        "          </div>"
    )


def section_extras(song: dict, name: str) -> str:
    """Arreglo y tab propios de una sección del Avanzado (S17), siempre escapados."""
    html = ""
    note = song.get("arreglos", {}).get(name)
    if note:
        html += f'\n            <p class="ac-arrangement small m-0">{tip_inline(note)}</p>'
    tab = song.get("tabs", {}).get(name)
    if tab:
        html += (
            f'\n            <pre class="ac-mono ac-tab small m-0">{esc(tab.strip(chr(10)))}</pre>'
        )
    return html


def structure(sections: list[dict], song: dict | None = None) -> str:
    blocks = []
    pending = set((song or {}).get("tabs", {})) | set((song or {}).get("arreglos", {}))
    for section in sections:
        if "consejo" in section:
            blocks.append(tip_html(section["consejo"]))
            continue
        times = section.get("repeticiones", 1)
        label = (
            f' <span class="text-body-secondary fw-normal ac-mono">× {times}</span>'
            if times > 1
            else ""
        )
        bars, previous = [], None
        for token in section.get("compases", []):
            # «%» repite el compás anterior: la casilla muestra ese mismo acorde, atenuado.
            repeated = token == REPEAT and previous is not None
            shown = previous if repeated else token
            bars.append(bar_html(shown, repeat=repeated))
            previous = shown
        bars = "".join(bars)
        name = section.get("nombre", "")
        extras = ""
        if song and name in pending:  # solo en la primera vez que aparece la sección
            extras = section_extras(song, name)
            pending.discard(name)
        blocks.append(
            '          <div class="d-grid gap-2 ac-score">\n'
            f'            <h2 class="h5 m-0">{esc(section.get("nombre", ""))}{label}</h2>\n'
            f'            <div class="ac-bars" data-reps="{times}">{bars}</div>{extras}\n'
            "          </div>"
        )
    return "\n".join(blocks)


def own_shapes(data: dict) -> dict[str, dict[str, list[int]]]:
    """Formas propias de guitarra por versión ({modo: {acorde: trastes}}). Opcionales: la
    validación está en acordes.py; aquí se ignora lo que no se pueda leer."""
    shapes: dict[str, dict[str, list[int]]] = {}
    for mode in ("intermedio", "avanzado"):
        table = data.get(mode, {}).get("formas", {})
        for name, text in table.items() if isinstance(table, dict) else []:
            try:
                shapes.setdefault(mode, {})[name] = theory.parse_shape(text)
            except ValueError:
                continue
    return shapes


def theme_shapes(data: dict) -> dict[str, list[int]]:
    """Formas por defecto del tema (`[formas]`, S27): valen para los tres niveles."""
    table = data.get("formas", {})
    shapes: dict[str, list[int]] = {}
    for name, text in table.items() if isinstance(table, dict) else []:
        try:
            shapes[name] = theory.parse_shape(text)
        except ValueError:
            continue
    return shapes


def load_song(path: Path) -> dict:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    compact, _ = parse_score(data.get("partitura", ""))
    data["secciones"] = list(data.get("secciones", [])) + compact
    for mode in ("intermedio", "avanzado"):
        data[mode + "_secciones"], _ = parse_score(
            data.get(mode, {}).get("partitura", ""), advanced=mode == "avanzado"
        )
    advanced = data.get("avanzado", {})
    data["tab"] = advanced.get("tab", "").strip("\n")
    for key in ("tabs", "arreglos"):
        table = advanced.get(key, {})
        data[key] = table if isinstance(table, dict) else {}
    data["formas_tema"] = theme_shapes(data)  # antes de que `formas` pase a ser {modo: ...}
    data["formas"] = own_shapes(data)
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
        body = structure(sections, song if key == "avanzado" else None) if sections else ""
        if tab:
            body += f'\n          <pre class="ac-mono small m-0">{esc(tab)}</pre>'
        if not body:
            body = (
                '<p class="text-body-secondary m-0"><span class="ac-chip">Próximamente</span></p>'
            )
    return body


def chords_payload(song: dict) -> dict:
    """Datos de los diagramas que usa este tema: acordes, teclas y formas de guitarra."""
    used: set[str] = set()
    for key in ("secciones", "intermedio_secciones", "avanzado_secciones"):
        for section in song.get(key, []):
            for token in section.get("compases", []):
                used.update(
                    part for part in token.split("-") if part and part not in (REPEAT, REST)
                )
    chords = {}
    for name in sorted(used):
        chord = theory.parse(name)
        if chord is None:
            continue
        keys, bass = theory.piano_keys(chord)
        standard, bass_drawn = theory.guitar_positions(chord)
        chords[name] = {
            "label": accidentals(name),
            "notes": [accidentals(n) for n in theory.note_names(chord)],
            "keys": keys,
            "bass": bass,
            "guitar": [{**p, "tab": list(theory.tab_lines(p["frets"]))} for p in standard]
            if standard
            else None,
        }
        if standard and not bass_drawn:  # el diagrama es el del acorde base (S19)
            base = name.split("/")[0]
            chords[name]["guitar_note"] = {
                "base": accidentals(base),
                "bass": accidentals(name.split("/")[1]),
            }
    own = {
        mode: {
            name: {"frets": frets, "tab": list(theory.tab_lines(frets))}
            for name, frets in table.items()
        }
        for mode, table in song.get("formas", {}).items()
    }
    default = {
        name: {"frets": frets, "tab": list(theory.tab_lines(frets))}
        for name, frets in song.get("formas_tema", {}).items()
    }
    return {"chords": chords, "own": own, "default": default}


def json_script(data: dict) -> str:
    """JSON seguro para incrustar en una etiqueta <script>."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def guide_row(profile: dict, index: int, slug: str) -> str:
    """Una guía en el desplegable: nota, cuánto cubre de este tema y su precio por clase."""
    score = profile.get("puntuacion")
    rating = (
        f'<span class="ac-rating">★ {score:.1f}</span> ({profile["resenas"]})'
        if score is not None
        else '<span class="ac-chip">Nuevo</span>'
    )
    example = ' <span class="ac-chip ac-chip-example">Ejemplo</span>' if profile.get("mock") else ""
    cost = (
        f'<span class="ac-mono fw-semibold">{esc(price(profile))}</span>'
        ' <span class="small text-body-secondary">/ clase</span>'
        if profile.get("precio")
        else '<span class="small text-body-secondary">Precio por definir</span>'
    )
    href = f"guias.html?tema={esc(slug)}#guia-{esc(profile['id'])}"
    return (
        '<li><a class="ac-guide-row" href="' + href + '" '
        f'aria-label="Ver el perfil de {esc(profile["nombre"])}">'
        f"{avatar(profile, index)}"
        f'<div class="ac-guide-info"><strong>{esc(profile["nombre"])}</strong>{example}'
        f'<span class="small text-body-secondary d-block">{rating} · {esc(coverage(profile, slug))}'
        "</span></div>"
        f'<div class="ac-guide-cost">{cost}</div></a></li>'
    )


def guides_panel(slug: str, title: str) -> str:
    """Desplegable con las 5 guías mejor puntuadas que pueden enseñar el tema y el enlace a todas."""
    total = len(teachers_for(slug))
    rows = "".join(guide_row(p, i, slug) for i, p in enumerate(top_teachers(slug)))
    noun = "la guía" if total == 1 else f"las {total} guías"
    return f"""<div class="collapse ac-guides-panel" id="guias-panel">
      <div class="card"><div class="card-body d-grid gap-3">
        <div class="d-flex justify-content-between align-items-center gap-3">
          <strong>Quienes pueden enseñarte «{esc(title)}»</strong>
          <button type="button" class="btn-close" data-bs-toggle="collapse" data-bs-target="#guias-panel" aria-label="Cerrar"></button>
        </div>
        <ul class="list-unstyled m-0 d-grid gap-2">{rows}</ul>
        <a class="btn btn-primary" href="guias.html?tema={esc(slug)}">Ver {noun}</a>
      </div></div>
    </div>"""


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
        '<p class="small text-body-secondary m-0">Cada casilla es un compás. Las casillas en gris '
        "repiten el compás anterior. Escucha la grabación original para seguir la letra.</p>"
    )
    teachers = teachers_for(song["slug"])
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
        chords_json=Markup(json_script(chords_payload(song))),
        guides_count=len(teachers),
        guides_panel=Markup(guides_panel(song["slug"], song["titulo"])) if teachers else "",
        guide_avatars=Markup("".join(avatar(t, i) for i, t in enumerate(teachers[:3]))),
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
                <div><h4 class="h4 mb-1">{esc(song["titulo"])}</h4><p class="m-0 text-body-secondary">{esc(song["artista"])}</p></div>
                <div class="d-flex flex-wrap gap-2">{chips}</div>
                <div class="d-flex flex-wrap gap-3 small text-body-secondary ac-mono">{facts_html}</div>
              </div>
            </{tag}>
          </div>"""


ARTICLES = ("los ", "las ", "la ", "el ")


def sort_key(text: str) -> str:
    """Clave de orden sin mayúsculas ni tildes: «Los Bunkers» y «Álvaro» se ordenan por B y A."""
    plain = unicodedata.normalize("NFD", text.casefold())
    return "".join(ch for ch in plain if unicodedata.category(ch) != "Mn")


def artist_key(artist: str) -> str:
    """Clave del artista; ignora el artículo inicial («Los Jaivas» va en la J)."""
    key = sort_key(artist).strip()
    for article in ARTICLES:
        if key.startswith(article):
            return key[len(article) :]
    return key


def version_count(song: dict, status: str = "publicable") -> int:
    """Cuántas versiones (Básico, Intermedio, Avanzado) tienen al menos un compás (S20).

    Un nivel que solo trae tips no cuenta, y un tema «Próximamente» no tiene ninguna."""
    if status != "publicable":
        return 0
    levels = ("secciones", "intermedio_secciones", "avanzado_secciones")
    return sum(any(sec.get("compases") for sec in song.get(key, [])) for key in levels)


def render_library(entries: list[tuple[dict, str, str]]) -> str:
    """Tarjetas (canción, slug, estado): por artista y, dentro de cada uno, primero el tema con más
    versiones y luego por título (S14, S20)."""
    ordered = sorted(
        entries,
        key=lambda e: (
            artist_key(e[0]["artista"]),
            -version_count(e[0], e[2]),
            sort_key(e[0]["titulo"]),
        ),
    )
    parts, current = [], None
    for song, slug, status in ordered:
        key = artist_key(song["artista"])
        if key != current:
            current = key
            total = sum(1 for other, _, _ in ordered if artist_key(other["artista"]) == key)
            parts.append(artist_head(song["artista"], total))
        parts.append(card(song, slug, status))
    return (
        '        <div class="row row-cols-1 row-cols-md-3 g-3">\n'
        + "\n".join(parts)
        + "\n        </div>"
    )


def artist_head(artist: str, total: int) -> str:
    """Cabecera de ancho completo que abre el grupo de temas de un artista."""
    count = f"{total} tema" if total == 1 else f"{total} temas"
    return (
        f'          <div class="col-12 ac-artist-head" data-ac-artist="{esc(sort_key(artist))}">'
        f'<h3 class="ac-artist"><span>{esc(artist)}</span><small>{count}</small></h3></div>'
    )


def library_html(directory: Path) -> str:
    entries = []
    for slug, *_ in REPERTOIRE:
        path = directory / f"{slug}.toml"
        if not path.exists():
            continue
        report = validate_file(path)
        status = (
            "publicable" if not report.errors and report.status == "publicable" else report.status
        )
        entries.append((load_song(path), slug, status))
    return render_library(entries)


def published_library_html(directory: Path) -> str:
    """Biblioteca de lo publicado (S9), ordenada por artista (S14): una tarjeta por tema de `directory`.

    Los del repertorio inicial que aún no están publicados salen como «Próximamente» solo con
    título y artista (sus datos son borrador y no se muestran); los temas nuevos se mezclan por
    su artista."""
    entries = []
    for slug, title, artist, kind in REPERTOIRE:
        path = directory / f"{slug}.toml"
        if path.exists():
            entries.append((load_song(path), slug, "publicable"))
        else:
            entries.append(({"titulo": title, "artista": artist, "tipo": kind}, slug, "borrador"))
    known = {slug for slug, *_ in REPERTOIRE}
    for path in sorted(directory.glob("*.toml")):
        if path.stem not in known:
            song = load_song(path)
            entries.append((song, song["slug"], "publicable"))
    return render_library(entries)


def count_published(block: str) -> int:
    """Temas con enlace (publicados) en el bloque de la Biblioteca; los «Próximamente» no cuentan."""
    return block.count('<a class="card h-100"')


def apply_count(page: str, total: int) -> str:
    """`page` con «N canciones» entre las marcas de la portada; sin marcas, igual."""
    if COUNT_START not in page:
        return page
    start = page.index(COUNT_START) + len(COUNT_START)
    label = "1 canción disponible" if total == 1 else f"{total} canciones disponibles"
    end = page.index(COUNT_END)
    return page[:start] + f"<strong>{label}</strong>" + page[end:]


def apply_library(page: str, block: str) -> str:
    """`page` (index.html) con `block` entre las marcas de la Biblioteca y el conteo de la portada."""
    start = page.index(LIBRARY_START) + len(LIBRARY_START)
    end = page.index(LIBRARY_END)
    page = page[:start] + "\n" + block + "\n        " + page[end:]
    return apply_count(page, count_published(block))


def update_library(directory: Path, index: Path) -> int:
    """Reemplaza las tarjetas de index.html entre las marcas de la Biblioteca."""
    block = library_html(directory)
    index.write_text(apply_library(index.read_text(encoding="utf-8"), block), encoding="utf-8")
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

        for asset in ("style.css", "acordia.js", "PetalumaScript.woff2"):
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

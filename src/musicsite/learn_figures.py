"""Figuras de «Aprender» (S65): tablas y diagramas de mástil calculados, nunca escritos a mano.

Todo sale de la afinación de la guitarra (`acordia_render.chordtheory.TUNING`) y de la teoría de
acordes de la librería, así que un error de teoría no se cuela en un diagrama: lo atrapan los
tests, que comparan contra valores conocidos y contra `note_names` de la librería.

Cuerdas numeradas como las nombra la gente: 6 = la más grave (Mi), 1 = la más aguda (mi). Un
traste es un semitono. Los SVG usan clases (`ac-fb-*`) que define el estilo de las páginas, para
que sigan el tema claro u oscuro; cada uno lleva `role="img"` y un título para lectores de pantalla.
"""

from html import escape

from acordia_render.chordtheory import (
    FLAT_NAMES,
    LETTERS,
    NATURAL,
    SHARP_NAMES,
    TUNING,
    note_names,
    parse,
)

STRINGS = (6, 5, 4, 3, 2, 1)
OPEN_NAMES = {6: "Mi", 5: "La", 4: "Re", 3: "Sol", 2: "Si", 1: "mi"}
MAJOR_STEPS = (0, 2, 4, 5, 7, 9, 11)  # semitonos de cada grado de la escala mayor desde la tónica

# Intervalos de 0 a 12 semitonos: (semitonos, nombre, grado en la notación de acordes, nota sobre Do).
INTERVALS = (
    (0, "Unísono", "1", "C"),
    (1, "Segunda menor", "b2 (b9)", "Db"),
    (2, "Segunda mayor", "2 (9)", "D"),
    (3, "Tercera menor", "b3", "Eb"),
    (4, "Tercera mayor", "3", "E"),
    (5, "Cuarta justa", "4 (11)", "F"),
    (6, "Cuarta aumentada o quinta disminuida", "#4 (#11) o b5", "F#"),
    (7, "Quinta justa", "5", "G"),
    (8, "Quinta aumentada o sexta menor", "#5 o b6 (b13)", "G#"),
    (9, "Sexta mayor", "6 (13)", "A"),
    (10, "Séptima menor", "b7", "Bb"),
    (11, "Séptima mayor", "7 (maj7)", "B"),
    (12, "Octava", "8", "C"),
)
SHORT = {
    0: "R",
    1: "2m",
    2: "2M",
    3: "3m",
    4: "3M",
    5: "4J",
    6: "b5",
    7: "5J",
    8: "#5",
    9: "6M",
    10: "7m",
    11: "7M",
    12: "8ª",
}


def midi_at(string: int, fret: int) -> int:
    """Altura (midi) de la nota de una cuerda en un traste."""
    return TUNING[6 - string] + fret


def note_at(string: int, fret: int, flats: bool = False) -> str:
    """Nombre de la nota (con sostenidos o bemoles) de una cuerda en un traste."""
    return (FLAT_NAMES if flats else SHARP_NAMES)[midi_at(string, fret) % 12]


def semitones_between(low: tuple[int, int], high: tuple[int, int]) -> int:
    """Semitonos entre dos posiciones (cuerda, traste); positivo si `high` es más aguda."""
    return midi_at(*high) - midi_at(*low)


def major_scale(root: str) -> list[str]:
    """Escala mayor con sus nombres por letra (G: G A B C D E F#), no por sostenidos al azar."""
    letter, accidental = root[0], root[1:]
    start = LETTERS.index(letter)
    root_pc = (NATURAL[letter] + {"": 0, "#": 1, "b": -1}[accidental]) % 12
    names = []
    for degree, step in enumerate(MAJOR_STEPS):
        letter_i = LETTERS[(start + degree) % 7]
        shift = (root_pc + step - NATURAL[letter_i] + 6) % 12 - 6
        names.append(letter_i + ("#" * shift if shift > 0 else "b" * -shift))
    return names


def triad(root: str, minor: bool = False) -> list[str]:
    """Tríada por grados de la escala mayor: 1-3-5, o 1-b3-5 si es menor (se baja la tercera)."""
    scale = major_scale(root)
    third = scale[2]
    if minor:
        third = third[:-1] if third.endswith("#") else third + "b"
    return [scale[0], third, scale[4]]


def library_triad(root: str, minor: bool = False) -> list[str]:
    """La misma tríada según la teoría de acordes de la librería (para contrastar en los tests)."""
    chord = parse(root + ("m" if minor else ""))
    assert chord is not None, root
    return note_names(chord)


# ---- Tablas ----


def chromatic_row() -> str:
    """Las 12 notas de una octava; los pares Mi–Fa y Si–Do, sin nada entre ellos, resaltados."""
    cells = []
    for pc in range(12):
        sharp, flat = SHARP_NAMES[pc], FLAT_NAMES[pc]
        label = f"{sharp}<small>/{flat}</small>" if sharp != flat else sharp
        natural = sharp == flat
        cls = "ac-note ac-note-nat" if natural else "ac-note"
        cells.append(f'<li class="{cls}">{label}</li>')
    return (
        '<figure class="ac-fig"><ol class="ac-chromatic" aria-label="Las doce notas de una octava">'
        + "".join(cells)
        + "</ol><figcaption>Cada paso es un semitono. Entre Mi y Fa, y entre Si y Do, no hay "
        "nota con # ni b: ya están a un semitono.</figcaption></figure>"
    )


def intervals_table() -> str:
    rows = "".join(
        f"<tr><td class='ac-mono'>{semis}</td><td>{escape(name)}</td>"
        f"<td class='ac-mono'>{escape(degree)}</td><td class='ac-mono'>{escape(example)}</td></tr>"
        for semis, name, degree, example in INTERVALS
    )
    return (
        '<figure class="ac-fig"><div class="table-responsive"><table class="table ac-table">'
        "<caption>Intervalos medidos desde Do (C). En la guitarra, un traste es un semitono.</caption>"
        "<thead><tr><th scope='col'>Semitonos</th><th scope='col'>Intervalo</th>"
        "<th scope='col'>En un acorde</th><th scope='col'>Sobre Do</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div></figure>"
    )


def triads_table(roots: tuple[str, ...] = ("C", "G", "D", "A", "E")) -> str:
    rows = []
    for root in roots:
        scale = major_scale(root)
        major, minor = triad(root), triad(root, minor=True)
        rows.append(
            f"<tr><th scope='row' class='ac-mono'>{root}</th>"
            f"<td class='ac-mono'>{' '.join(scale)}</td>"
            f"<td class='ac-mono'>{root} = {' '.join(major)}</td>"
            f"<td class='ac-mono'>{root}m = {' '.join(minor)}</td></tr>"
        )
    return (
        '<figure class="ac-fig"><div class="table-responsive"><table class="table ac-table">'
        "<caption>Cada acorde sale de su escala mayor: mayor = grados 1, 3 y 5; menor = 1, b3 y 5.</caption>"
        "<thead><tr><th scope='col'>Tónica</th><th scope='col'>Escala mayor</th>"
        "<th scope='col'>Acorde mayor</th><th scope='col'>Acorde menor</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></figure>"
    )


# ---- Mástil horizontal ----

CELL, LEFT, TOP, GAP = (
    44,
    46,
    26,
    28,
)  # ancho de un traste, margen izquierdo y superior, entre cuerdas
DOT_FRETS = (3, 5, 7, 9, 12)


def fretboard(
    marks: list[tuple[int, int, str, str]],
    *,
    first: int,
    last: int,
    title: str,
    caption: str,
) -> str:
    """Mástil visto de frente, con la cuerda 1 arriba. `marks`: (cuerda, traste, etiqueta, tipo)
    con tipo «root» (la nota de partida) o «note» (otra nota). Los trastes `first` a `last`."""
    count = last - first + 1
    width = LEFT + count * CELL + 12
    height = TOP + 5 * GAP + 36
    parts = [
        f'<svg class="ac-fb" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>"
    ]
    for i, string in enumerate(reversed(STRINGS)):  # 1 arriba, 6 abajo
        y = TOP + i * GAP
        parts.append(
            f'<line class="ac-fb-string" x1="{LEFT}" y1="{y}" x2="{width - 12}" y2="{y}"/>'
        )
        parts.append(
            f'<text class="ac-fb-label" x="12" y="{y + 4}" text-anchor="middle">{string}</text>'
        )
    for j in range(count + 1):
        x = LEFT + j * CELL
        heavy = " ac-fb-nut" if first == 0 and j == 0 else ""
        parts.append(
            f'<line class="ac-fb-fret{heavy}" x1="{x}" y1="{TOP}" x2="{x}" y2="{TOP + 5 * GAP}"/>'
        )
    for fret in range(first, last + 1):
        x = LEFT + (fret - first) * CELL + CELL / 2
        if fret in DOT_FRETS:
            parts.append(f'<circle class="ac-fb-inlay" cx="{x}" cy="{TOP + 5 * GAP + 16}" r="3"/>')
        if fret > 0:
            parts.append(
                f'<text class="ac-fb-num" x="{x}" y="{TOP + 5 * GAP + 30}" text-anchor="middle">{fret}</text>'
            )
    for string, fret, label, kind in marks:
        row = STRINGS[::-1].index(string)
        x = LEFT - 14 if fret == 0 else LEFT + (fret - first) * CELL + CELL / 2
        y = TOP + row * GAP
        parts.append(f'<circle class="ac-fb-dot ac-fb-{kind}" cx="{x}" cy="{y}" r="11"/>')
        parts.append(
            f'<text class="ac-fb-dot-text" x="{x}" y="{y + 4}" text-anchor="middle">{escape(label)}</text>'
        )
    parts.append("</svg>")
    return f'<figure class="ac-fig"><div class="ac-fb-wrap">{"".join(parts)}</div><figcaption>{caption}</figcaption></figure>'


def natural_notes_fretboard() -> str:
    """Las notas naturales (sin # ni b) de las cuerdas 6 y 5, hasta el traste 12."""
    marks = []
    for string in (6, 5):
        for fret in range(0, 13):
            name = note_at(string, fret)
            if len(name) == 1:
                marks.append((string, fret, name, "root" if fret == 0 else "note"))
    return fretboard(
        [m for m in marks],
        first=0,
        last=12,
        title="Notas naturales de las cuerdas 6 (Mi) y 5 (La) hasta el traste 12",
        caption=(
            "Las notas naturales de las dos cuerdas graves. Aprenderlas es el punto de partida: "
            "las demás son un traste a cada lado (# a la derecha, b a la izquierda)."
        ),
    )


def interval_shapes_fretboard(root_string: int, root_fret: int, wanted: tuple[int, ...]) -> str:
    """Desde una raíz, dónde queda cada intervalo en `wanted` (semitonos) mirando las cuerdas
    cercanas, dentro de la ventana de trastes visible."""
    first, last = max(0, root_fret - 1), root_fret + 9
    root = (root_string, root_fret)
    marks = [(root_string, root_fret, "R", "root")]
    for string in STRINGS:
        for fret in range(first, last + 1):
            if (string, fret) == root:
                continue
            semis = semitones_between(root, (string, fret))
            if semis in wanted and abs(string - root_string) <= 2:
                marks.append((string, fret, SHORT[semis], "note"))
    # una sola posición por intervalo y cuerda: la más cercana a la raíz
    seen: dict[tuple[int, int], tuple[int, int, str, str]] = {}
    for mark in marks[1:]:
        key = (mark[0], semitones_between(root, (mark[0], mark[1])))
        best = seen.get(key)
        if best is None or abs(mark[1] - root_fret) < abs(best[1] - root_fret):
            seen[key] = mark
    chosen = [marks[0], *seen.values()]
    root_name = note_at(root_string, root_fret)
    return fretboard(
        chosen,
        first=first,
        last=last,
        title=f"Intervalos desde {root_name} (cuerda {root_string}, traste {root_fret})",
        caption=f"R es la raíz ({root_name}, cuerda {root_string}, traste {root_fret}). Las letras marcan el intervalo.",
    )


# ---- Diagrama de acorde vertical ----

CHORD_COL, CHORD_ROW = 22, 26


def chord_diagram(
    frets: list[int],
    *,
    title: str,
    base_fret: int = 1,
    barre: tuple[int, int, int] | None = None,
    highlight: int | None = None,
    caption: str = "",
) -> str:
    """Diagrama de acorde: 6 cuerdas (de la 6 a la 1, izquierda a derecha) y 5 trastes visibles.
    `frets`: -1 no suena, 0 al aire, n traste absoluto. `barre`: (traste, cuerda desde, cuerda hasta)
    con cuerdas 6..1. `highlight`: índice 0-5 de la cuerda cuya nota explica el texto."""
    left, top = 26, 38
    width = left + 5 * CHORD_COL + 26
    height = top + 5 * CHORD_ROW + 24
    parts = [
        f'<svg class="ac-cd" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>"
    ]
    for i in range(6):
        x = left + i * CHORD_COL
        parts.append(
            f'<line class="ac-fb-string" x1="{x}" y1="{top}" x2="{x}" y2="{top + 5 * CHORD_ROW}"/>'
        )
    for j in range(6):
        y = top + j * CHORD_ROW
        heavy = " ac-fb-nut" if j == 0 and base_fret == 1 else ""
        parts.append(
            f'<line class="ac-fb-fret{heavy}" x1="{left}" y1="{y}" x2="{left + 5 * CHORD_COL}" y2="{y}"/>'
        )
    if base_fret > 1:
        parts.append(
            f'<text class="ac-fb-num" x="{left - 8}" y="{top + CHORD_ROW // 2 + 4}" text-anchor="end">{base_fret}</text>'
        )
    if barre:
        fret, from_string, to_string = barre
        row = fret - base_fret
        x1 = left + (6 - from_string) * CHORD_COL
        x2 = left + (6 - to_string) * CHORD_COL
        y = top + row * CHORD_ROW + CHORD_ROW / 2
        parts.append(f'<line class="ac-cd-barre" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/>')
    for i, fret in enumerate(frets):
        x = left + i * CHORD_COL
        if fret == -1:
            parts.append(
                f'<text class="ac-fb-num" x="{x}" y="{top - 10}" text-anchor="middle">×</text>'
            )
        elif fret == 0:
            marked = " ac-cd-hl" if i == highlight else ""
            parts.append(f'<circle class="ac-cd-open{marked}" cx="{x}" cy="{top - 14}" r="4.5"/>')
        else:
            y = top + (fret - base_fret) * CHORD_ROW + CHORD_ROW / 2
            kind = "root" if i == highlight else "note"
            parts.append(f'<circle class="ac-fb-dot ac-fb-{kind}" cx="{x}" cy="{y}" r="8"/>')
    parts.append("</svg>")
    figure = f'<div class="ac-cd-wrap">{"".join(parts)}</div>'
    return (
        f'<figure class="ac-fig ac-fig-chord">{figure}<figcaption>{caption}</figcaption></figure>'
        if caption
        else figure
    )


def chord_diagram_notes(frets: list[int]) -> list[str]:
    """Las notas que suena una forma (de la cuerda 6 a la 1), con sostenidos."""
    return [SHARP_NAMES[(TUNING[i] + f) % 12] for i, f in enumerate(frets) if f != -1]


def e_and_em() -> str:
    """E y Em lado a lado: solo cambia la tercera (G# en E, G en Em), un semitono."""
    major = chord_diagram(
        [0, 2, 2, 1, 0, 0],
        title="Acorde E mayor: 0 2 2 1 0 0",
        highlight=3,
        caption="<strong>E</strong>: Mi, Si, Mi, <em>Sol#</em>, Si, Mi",
    )
    minor = chord_diagram(
        [0, 2, 2, 0, 0, 0],
        title="Acorde E menor: 0 2 2 0 0 0",
        highlight=3,
        caption="<strong>Em</strong>: Mi, Si, Mi, <em>Sol</em>, Si, Mi",
    )
    return f'<div class="ac-fig-pair">{major}{minor}</div>'


def barre_shapes() -> str:
    """La forma de E corrida tres trastes con cejilla: G mayor y G menor."""
    major = chord_diagram(
        [3, 5, 5, 4, 3, 3],
        title="Acorde G mayor con cejilla en el traste 3: 3 5 5 4 3 3",
        base_fret=3,
        barre=(3, 6, 1),
        caption="<strong>G</strong> con la forma de E",
    )
    minor = chord_diagram(
        [3, 5, 5, 3, 3, 3],
        title="Acorde G menor con cejilla en el traste 3: 3 5 5 3 3 3",
        base_fret=3,
        barre=(3, 6, 1),
        caption="<strong>Gm</strong> con la forma de Em",
    )
    return f'<div class="ac-fig-pair">{major}{minor}</div>'


FIGURES = {
    "escala-cromatica": chromatic_row,
    "tabla-intervalos": intervals_table,
    "mastil-naturales": natural_notes_fretboard,
    "mastil-intervalos-cuerda6": lambda: interval_shapes_fretboard(6, 3, (3, 4, 5, 7, 12)),
    "mastil-intervalos-cuerda4": lambda: interval_shapes_fretboard(4, 3, (3, 4, 7, 12)),
    "tabla-triadas": triads_table,
    "e-em": e_and_em,
    "cejilla": barre_shapes,
}

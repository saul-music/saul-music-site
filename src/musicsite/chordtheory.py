"""Teoría mínima de acordes y formas de guitarra para los diagramas del sitio.

- Interpreta un acorde de nuestra notación («F#m», «Bbmaj7», «G/B») y calcula sus notas.
- Entrega la forma estándar de guitarra desde `data/chords-guitar.json`, un recorte de chords-db
  (MIT, ver THIRD_PARTY_NOTICES.md). No hay dependencia en tiempo de ejecución ni de red.
- Valida una forma propia (la de `[avanzado.formas]`): solo puede sonar notas del acorde.

Los trastes son absolutos: 0 = al aire, -1 = cuerda que no suena, de la 6ª a la 1ª cuerda.
"""

import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DATA_FILE = Path(__file__).with_name("data") / "chords-guitar.json"
TUNING = (40, 45, 50, 55, 59, 64)  # E2 A2 D3 G3 B3 E4: de la 6ª a la 1ª cuerda
STRING_NAMES = ("E", "A", "D", "G", "B", "e")
MAX_FRET = 24
MUTED = -1

NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLAT_NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
DB_KEYS = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")  # nombres de chords-db

# Sufijo de chords-db -> semitonos desde la raíz (el 9 va como 14: la novena, una octava arriba).
INTERVALS: dict[str, tuple[int, ...]] = {
    "major": (0, 4, 7),
    "minor": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "6": (0, 4, 7, 9),
    "m6": (0, 3, 7, 9),
    "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10),
    "m7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9),
    "7sus4": (0, 5, 7, 10),
    "add9": (0, 4, 7, 14),
    "madd9": (0, 3, 7, 14),
    "9": (0, 4, 7, 10, 14),
    "maj9": (0, 4, 7, 11, 14),
    "m9": (0, 3, 7, 10, 14),
    "m11": (0, 3, 7, 10, 14, 17),
    "m69": (0, 3, 7, 9, 14),
    "mmaj7": (0, 3, 7, 11),
    "mmaj7b5": (0, 3, 6, 11),
    "mmaj9": (0, 3, 7, 11, 14),
    "mmaj11": (0, 3, 7, 11, 14, 17),
    "sus2sus4": (0, 2, 5, 7),  # = sus4add9
    "add#11": (0, 4, 7, 18),  # sin guitarra estándar: chords-db no los trae (S21)
    "madd#11": (0, 3, 7, 18),
}
# Cómo se escribe en nuestras partituras -> sufijo de chords-db.
ALIASES = {
    "": "major",
    "m": "minor",
    "min": "minor",
    "dim": "dim",
    "aug": "aug",
    "+": "aug",
    "sus2": "sus2",
    "sus4": "sus4",
    "sus": "sus4",
    "6": "6",
    "m6": "m6",
    "7": "7",
    "maj7": "maj7",
    "m7": "m7",
    "min7": "m7",
    "m7b5": "m7b5",
    "dim7": "dim7",
    "7sus4": "7sus4",
    "add9": "add9",
    "madd9": "madd9",
    "9": "9",
    "maj9": "maj9",
    "m9": "m9",
    "m11": "m11",
    "m69": "m69",
    "mmaj7": "mmaj7",
    "mM7": "mmaj7",
    "mmaj7b5": "mmaj7b5",
    "mmaj9": "mmaj9",
    "mmaj11": "mmaj11",
    "sus2sus4": "sus2sus4",
    "sus4add9": "sus2sus4",
    "add#11": "add#11",
    "madd#11": "madd#11",
}
CHORD = re.compile(r"^([A-G])([#b]?)([^/]*)(?:/([A-G])([#b]?))?$")


LETTERS = "CDEFGAB"
# Grado de la escala al que corresponde cada intervalo (el 9 es la novena, grado 2).
DEGREE = {
    0: 1,
    1: 2,
    2: 2,
    3: 3,
    4: 3,
    5: 4,
    6: 5,
    7: 5,
    8: 5,
    9: 6,
    10: 7,
    11: 7,
    14: 2,
    17: 4,
    18: 4,
}


@dataclass(frozen=True)
class Chord:
    token: str
    root: int
    bass: int | None
    suffix: str  # sufijo de chords-db
    flats: bool  # para nombrar una nota suelta: con bemoles o con sostenidos
    letter: str = "C"  # letra de la raíz tal como se escribió
    accidental: str = ""
    bass_letter: str = ""
    bass_accidental: str = ""

    @property
    def intervals(self) -> tuple[int, ...]:
        return INTERVALS[self.suffix]

    @property
    def tones(self) -> frozenset[int]:
        return frozenset((self.root + i) % 12 for i in self.intervals)

    @property
    def allowed(self) -> frozenset[int]:
        """Notas que puede sonar una forma de este acorde: las suyas y el bajo."""
        return self.tones | ({self.bass} if self.bass is not None else frozenset())


def note_name(pc: int, flats: bool) -> str:
    return (FLAT_NAMES if flats else SHARP_NAMES)[pc % 12]


def _pitch_class(letter: str, accidental: str) -> int:
    return (NATURAL[letter] + {"#": 1, "b": -1, "": 0}[accidental]) % 12


def _prefers_flats(letter: str, accidental: str) -> bool:
    if accidental == "b":
        return True
    return accidental == "" and letter == "F"


def parse(token: str) -> Chord | None:
    """El acorde interpretado, o None si no está entre los que sabemos dibujar."""
    match = CHORD.match(token)
    if not match:
        return None
    letter, accidental, rest, bass_letter, bass_accidental = match.groups()
    suffix = ALIASES.get(re.sub(r"^m?Maj", lambda m: m.group().lower(), rest))  # «Maj» = «maj»
    if suffix is None:
        return None
    bass = _pitch_class(bass_letter, bass_accidental) if bass_letter else None
    return Chord(
        token=token,
        root=_pitch_class(letter, accidental),
        bass=bass,
        suffix=suffix,
        flats=_prefers_flats(letter, accidental),
        letter=letter,
        accidental=accidental,
        bass_letter=bass_letter or "",
        bass_accidental=bass_accidental or "",
    )


def _spell(pc: int, letter: str) -> str:
    """El nombre de la nota `pc` que usa la letra dada («Eb», no «D#», en Do menor)."""
    shift = (pc - NATURAL[letter] + 6) % 12 - 6  # -6..5 semitonos respecto de la natural
    if abs(shift) > 2:
        return note_name(pc, False)
    return letter + ("#" * shift if shift > 0 else "b" * -shift)


def note_names(chord: Chord) -> list[str]:
    """Notas del acorde, de la raíz hacia arriba, escritas por grado (Cm = C Eb G)."""
    start = LETTERS.index(chord.letter)
    names = []
    for interval in chord.intervals:
        degree = DEGREE[interval]
        if chord.suffix == "dim7" and interval == 9:
            degree = 7  # séptima disminuida: Cdim7 = C Eb Gb Bbb
        letter = LETTERS[(start + degree - 1) % 7]
        names.append(_spell(chord.root + interval, letter))
    if chord.bass is not None and chord.bass not in chord.tones:
        names.insert(0, chord.bass_letter + chord.bass_accidental)
    return names


def piano_keys(chord: Chord) -> tuple[list[int], int | None]:
    """Teclas por resaltar en dos octavas desde un do (0 a 23) y la del bajo, si lo hay."""
    keys = []
    for interval in chord.intervals:
        position = chord.root + interval
        while position > 23:
            position -= 12
        keys.append(position)
    bass = chord.bass % 12 if chord.bass is not None else None
    return sorted(set(keys)), bass


# --- Guitarra: forma estándar ---------------------------------------------------------------


def sounded(frets: list[int]) -> list[int]:
    """Alturas (midi) de las cuerdas que suenan."""
    return [TUNING[i] + f for i, f in enumerate(frets) if f != MUTED]


def check_shape(chord: Chord, frets: list[int]) -> list[str]:
    """Errores de una forma para este acorde (lista vacía si es válida)."""
    errors = []
    if len(frets) != 6:
        return [f"debe tener 6 valores, uno por cuerda (tiene {len(frets)})"]
    for f in frets:
        if f != MUTED and not 0 <= f <= MAX_FRET:
            errors.append(f"el traste {f} está fuera de 0 a {MAX_FRET}")
    if errors:
        return errors
    notes = sounded(frets)
    if len(notes) < 3:
        return ["debe sonar al menos en 3 cuerdas"]
    foreign = sorted({n % 12 for n in notes} - chord.allowed)
    if foreign:
        names = ", ".join(note_name(pc, chord.flats) for pc in foreign)
        return [f"suena {names}, que no es del acorde {chord.token}"]
    if chord.bass is not None and min(notes) % 12 != chord.bass:
        return [f"la nota más grave debe ser {note_name(chord.bass, chord.flats)} (el bajo)"]
    return []


def position_ok(chord: Chord, frets: list[int]) -> bool:
    """Forma estándar válida: sin notas ajenas y con la raíz y la nota que define el acorde."""
    if check_shape(chord, frets):
        return False
    pcs = {n % 12 for n in sounded(frets)}
    defining = (chord.root + chord.intervals[1]) % 12
    return chord.root in pcs and defining in pcs


@cache
def _database() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def _positions(root: int, key: str) -> list[dict] | None:
    positions = _database()["acordes"].get(DB_KEYS[root], {}).get(key)
    if not positions:
        return None
    return [{"frets": p["f"], "fingers": p["d"], "barres": p["b"]} for p in positions]


def standard_positions(chord: Chord) -> list[dict] | None:
    """Formas estándar de guitarra ({frets, fingers, barres}) de este acorde tal cual, con su
    bajo si lo tiene; None si chords-db no trae ninguna."""
    key = chord.suffix if chord.bass is None else f"{chord.suffix}/{chord.bass}"
    return _positions(chord.root, key)


def guitar_positions(chord: Chord) -> tuple[list[dict] | None, bool]:
    """Formas para mostrar y si dibujan el bajo: (formas, bajo_dibujado) (S19).

    Sin bajo, o con una forma de chords-db para ese bajo (G/B), el bajo está dibujado. Si no hay,
    se usa el acorde base (Gmaj7/B -> Gmaj7): primero las formas cuya nota más grave ya es el
    bajo (esas sí lo dibujan) y, si ninguna lo es, todas, sin el bajo. Sin acorde base: None."""
    exact = standard_positions(chord)
    if exact or chord.bass is None:
        return exact, True
    base = _positions(chord.root, chord.suffix)
    if not base:
        return None, False
    with_bass = [p for p in base if min(sounded(p["frets"])) % 12 == chord.bass]
    return (with_bass, True) if with_bass else (base, False)


def parse_shape(text: str) -> list[int]:
    """«x 3 2 0 1 0» -> [-1, 3, 2, 0, 1, 0]. Lanza ValueError con un mensaje en español."""
    values = []
    for part in str(text).split():
        if part.lower() == "x":
            values.append(MUTED)
        elif part.isdigit():
            values.append(int(part))
        else:
            raise ValueError(f"«{part}» no es un traste (usa números o x)")
    return values


def tab_lines(frets: list[int]) -> tuple[str, str]:
    """Dos líneas alineadas: nombres de las cuerdas y trastes («x» = no suena)."""
    cells = ["x" if f == MUTED else str(f) for f in frets]
    width = max(len(c) for c in cells)
    return (
        " ".join(n.ljust(width) for n in STRING_NAMES).rstrip(),
        " ".join(c.ljust(width) for c in cells).rstrip(),
    )

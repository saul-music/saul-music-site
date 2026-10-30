"""Plantillas y validador de la transcripción propia de acordes (versión básica).

Los archivos viven fuera de git (carpeta local) y los escribe una persona del equipo. Este módulo
solo crea las plantillas y comprueba que cada archivo cumpla las reglas: acordes mayores y menores
sin extensiones y procedencia declarada. No lee ningún sitio externo ni publica nada.

Uso:
    python -m musicsite.acordes init --dir ../acordes-local
    python -m musicsite.acordes validate --dir ../acordes-local
    python -m musicsite.acordes pages --dir ../acordes-local --out ../vista-previa --preview
    python -m musicsite.acordes library --dir ../acordes-local --index src/musicsite/web/index.html
    python -m musicsite.acordes simple --dir ../acordes-local --out ../para-enviar [--slug otra-era]
"""

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# (slug, título, artista, tipo): el repertorio inicial más los tres ejemplos del sitio.
REPERTOIRE = [
    ("esquemas-juveniles", "Esquemas juveniles", "Javiera Mena", "cancion"),
    ("yo-no-te-pido-la-luna", "Yo no te pido la luna", "Javiera Mena (versión)", "cancion"),
    ("otra-era", "Otra era", "Javiera Mena", "cancion"),
    ("camara-lenta", "Cámara lenta", "Javiera Mena", "cancion"),
    ("luz-de-piedra-de-luna", "Luz de Piedra de Luna", "Javiera Mena", "cancion"),
    ("un-amor-violento", "Un amor violento", "Los Tres", "cancion"),
    ("dejate-caer", "Déjate caer", "Los Tres", "cancion"),
    ("he-barrido-el-sol", "He barrido el sol", "Los Tres", "cancion"),
    ("cantar-y-amar", "Cantar y amar", "Los Tres", "cancion"),
    ("la-primera-vez", "La Primera Vez", "Los Tres", "cancion"),
    ("llueve-sobre-la-ciudad", "Llueve sobre la ciudad", "Los Bunkers", "cancion"),
    ("bailando-solo", "Bailando solo", "Los Bunkers", "cancion"),
    ("ven-aqui", "Ven aquí", "Los Bunkers", "cancion"),
    ("entre-mis-brazos", "Entre mis brazos", "Los Bunkers", "cancion"),
    ("corre-que-te-pillo", "Corre que te pillo", "Los Jaivas", "instrumental"),
    ("la-vida-magica-ay-si", "La vida mágica, ay sí", "Los Jaivas", "instrumental"),
    ("takirari-del-puerto", "Takirari del Puerto", "Los Jaivas", "instrumental"),
    ("el-errante", "El errante", "Congreso", "instrumental"),
    ("norte-y-cal", "Norte y cal", "Subhira", "instrumental"),
    ("hablar-de-ti", "Hablar de ti", "Gepe", "cancion"),
]

# Versión básica: nota, sostenido o bemol opcional y "m" para menor. Nada de 7, sus, add, 9, etc.
BASIC_CHORD = re.compile(r"^[A-G][#b]?m?$")
# Intermedio: con extensiones (7, maj7, sus4, add9, m7b5...). Avanzado: además bajos e inversiones.
EXTENDED_CHORD = re.compile(
    r"^[A-G][#b]?(?:maj|min|m|dim|aug|\+)?(?:\d{1,2}|(?:sus|add|b|#)\d{0,2})*$"
)
SLASH_CHORD = re.compile(
    r"^[A-G][#b]?(?:maj|min|m|dim|aug|\+)?(?:\d{1,2}|(?:sus|add|b|#)\d{0,2})*(?:/[A-G][#b]?)?$"
)
BARRIOS = {"", "Rock", "Pop", "Indie"}
MODES = {"intermedio": EXTENDED_CHORD, "avanzado": SLASH_CHORD}
TIME_SIGNATURE = re.compile(r"^\d{1,2}/\d{1,2}$")
LEVELS = {"", "inicial", "medio", "avanzado"}
KINDS = {"cancion", "instrumental"}
REPEAT = "%"

TEMPLATE = """\
# Transcripción propia de «{title}» ({artist}).
# Solo acordes básicos: mayores y menores, sin extensiones (G, Em, C#m; no G7, Dsus4, Am9).
# Se escribe de oído o con una fuente que se declare en [procedencia]. No se copia ningún texto
# de otro sitio. No se publica nada hasta marcar revisado y v2_resuelto.

slug = "{slug}"
titulo = "{title}"
artista = "{artist}"
tipo = "{kind}"
barrio = ""      # Rock, Pop o Indie (vacío si no aplica)

tono = ""        # por ejemplo "Sol mayor"
cejilla = ""     # por ejemplo "Sin cejilla" o "Cejilla 3"
compas = ""      # por ejemplo "4/4"
bpm = 0          # entre 40 y 240
nivel = ""       # inicial, medio o avanzado
acordes = []     # los acordes que usa el tema, por ejemplo ["G", "D", "Em", "C"]

forma = ""       # estructura general, por ejemplo "Intro - Estrofa - Coro - Estrofa - Coro - Final"
confianza = ""   # alta, media o baja
dudas = ""       # qué hay que verificar de oído
sin_base_armonica = false   # true en un instrumental sin progresión estable

# Secciones en notación compacta, una por línea: «Nombre xN: acordes». Un acorde por compás;
# «%» repite el compás anterior. Por ejemplo:
#   Intro x1: G D
#   Estrofa x2: G % D Em C
partitura = '''
'''

[procedencia]
metodo = ""      # por ejemplo "de oído, con la grabación original"
autor = ""       # quién transcribió
fecha = ""       # AAAA-MM-DD

[revision]
revisado = false      # true cuando la transcripción está terminada y revisada
v2_resuelto = false   # true solo cuando los derechos (V2) estén resueltos

# Versiones con más detalle (opcionales). Si no existen, la página muestra «Próximamente».
# [intermedio]     # con extensiones: G7, Dsus4, Am9
# partitura = '''
# '''
# [avanzado]       # con extensiones, bajos e inversiones (G/B) y arreglos con tab
# partitura = '''
# '''
# tab = '''
# '''
"""


SIMPLE_TEMPLATE = """\
# ==========================================================================
#  {title} · {artist}
#  Completa solo lo que está entre comillas o corchetes.
#  Las líneas que empiezan con # son notas: no las cambies ni las borres.
# ==========================================================================

# --- No cambies estas líneas ---
slug = "{slug}"
titulo = "{title}"
artista = "{artist}"
tipo = "{kind}"
barrio = "{barrio}"
{no_base}
# --- 1) Datos del tema ---
tono = ""        # Ejemplo: "Sol mayor"
compas = ""      # Ejemplo: "4/4"
bpm = 0          # Qué tan rápido va, un número. Ejemplo: 96
nivel = ""       # Escribe "inicial", "medio" o "avanzado"

# --- 2) Los acordes que usa el tema (todos, entre corchetes y comillas) ---
acordes = []     # Ejemplo: ["G", "Em", "C", "D"]

# --- 3) El orden de las partes ---
forma = ""       # Ejemplo: "Intro – Estrofa – Coro – Estrofa – Coro – Final"

# --- 4) Los acordes de cada parte: un acorde por compás, una línea por parte ---
#   "%" repite el acorde anterior. "x2" quiere decir que se toca dos veces.
#   Ejemplo:   Estrofa x2: G % Em C
#   Escribe tus líneas entre las dos líneas de comillas triples.
partitura = '''
'''

# --- 5) Lo que no sepas con certeza (nadie lo ve) ---
dudas = ""

# --- 6) Quién lo hizo y cómo ---
[procedencia]
metodo = ""      # Ejemplo: "De oído"
autor = ""       # Tu nombre
fecha = ""       # Ejemplo: "2026-10-30"

# --- No toques estas líneas: las completa quien te envió el archivo ---
[revision]
revisado = false
v2_resuelto = false
"""


def simple_template(song: dict) -> str:
    """Archivo limpio para quien no es informático: datos fijos puestos, sin acordes."""
    no_base = ""
    if song.get("tipo") == "instrumental":
        no_base = (
            "\n# Si el tema no tiene acordes fijos, cambia false por true y deja acordes vacío.\n"
            "sin_base_armonica = false\n"
        )
    return SIMPLE_TEMPLATE.format(
        slug=song["slug"],
        title=song["titulo"],
        artist=song["artista"],
        kind=song.get("tipo", "cancion"),
        barrio=song.get("barrio", ""),
        no_base=no_base,
    )


def export_simple(directory: Path, out: Path, slug: str | None = None) -> list[Path]:
    """Crea un .txt limpio por tema (o solo el indicado). Nunca sobrescribe y no copia acordes."""
    out.mkdir(parents=True, exist_ok=True)
    created = []
    for path in sorted(directory.glob("*.toml")):
        if slug and path.stem != slug:
            continue
        target = out / f"{path.stem}.txt"
        if target.exists():
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        target.write_text(simple_template(data), encoding="utf-8")
        created.append(target)
    return created


@dataclass
class Report:
    path: Path
    status: str = "vacío"
    errors: list[str] = field(default_factory=list)


def init(directory: Path) -> list[Path]:
    """Crea las plantillas que falten. Nunca sobrescribe un archivo existente."""
    directory.mkdir(parents=True, exist_ok=True)
    created = []
    for slug, title, artist, kind in REPERTOIRE:
        path = directory / f"{slug}.toml"
        if path.exists():
            continue
        path.write_text(
            TEMPLATE.format(slug=slug, title=title, artist=artist, kind=kind), encoding="utf-8"
        )
        created.append(path)
    return created


SECTION_LINE = re.compile(r"^(?P<name>.+?)(?:\s+x(?P<times>\d+))?\s*:\s*(?P<bars>.*)$")


def parse_score(text: str) -> tuple[list[dict], list[str]]:
    """Convierte la notación compacta («Estrofa x2: G % D») en secciones."""
    sections, errors = [], []
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = SECTION_LINE.match(line)
        if not match:
            errors.append(f"partitura, línea {number}: usa la forma «Nombre xN: acordes»")
            continue
        sections.append(
            {
                "nombre": match["name"].strip(),
                "repeticiones": int(match["times"] or 1),
                "compases": match["bars"].split(),
            }
        )
    return sections, errors


def check_chord(token: str, where: str, errors: list[str]) -> None:
    if BASIC_CHORD.match(token):
        return
    errors.append(
        f"{where}: «{token}» no es un acorde básico (usa mayores y menores, sin extensiones)"
    )


def validate_file(path: Path) -> Report:
    report = Report(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        report.status = "inválido"
        report.errors.append(f"TOML inválido: {error}")
        return report

    errors = report.errors
    if data.get("slug") != path.stem:
        errors.append(f"slug «{data.get('slug')}» no coincide con el nombre del archivo")
    if data.get("tipo") not in KINDS:
        errors.append("tipo debe ser «cancion» o «instrumental»")
    if data.get("nivel", "") not in LEVELS:
        errors.append("nivel debe ser inicial, medio o avanzado")
    bpm = data.get("bpm", 0)
    if bpm != 0 and not 40 <= bpm <= 240:
        errors.append("bpm debe estar entre 40 y 240")
    meter = data.get("compas", "")
    if meter and not TIME_SIGNATURE.match(meter):
        errors.append("compas debe tener la forma 4/4")

    chords = data.get("acordes", [])
    for chord in chords:
        check_chord(chord, "acordes", errors)
    sections = list(data.get("secciones", []))
    compact, score_errors = parse_score(data.get("partitura", ""))
    sections += compact
    errors.extend(score_errors)
    no_harmony = bool(data.get("sin_base_armonica", False))
    bars = 0
    for section in sections:
        name = section.get("nombre", "?")
        previous = None
        for token in section.get("compases", []):
            bars += 1
            if token == REPEAT:
                if previous is None:
                    errors.append(f"sección «{name}»: «%» no puede ser el primer compás")
                continue
            check_chord(token, f"sección «{name}»", errors)
            if BASIC_CHORD.match(token) and token not in chords:
                errors.append(f"sección «{name}»: «{token}» no está en la lista de acordes")
            previous = token

    if data.get("barrio", "") not in BARRIOS:
        errors.append("barrio debe ser Rock, Pop o Indie")
    for mode, pattern in MODES.items():
        score = data.get(mode, {}).get("partitura", "")
        mode_sections, mode_errors = parse_score(score)
        errors.extend(f"{mode}: {error}" for error in mode_errors)
        for section in mode_sections:
            for token in section["compases"]:
                if token != REPEAT and not pattern.match(token):
                    errors.append(f"{mode}: «{token}» no es un acorde válido para este modo")
    tab = data.get("avanzado", {}).get("tab", "")
    if not isinstance(tab, str):
        errors.append("avanzado: tab debe ser texto")

    origin = data.get("procedencia", {})
    review = data.get("revision", {})
    reviewed = bool(review.get("revisado", False))
    cleared = bool(review.get("v2_resuelto", False))
    if cleared and not reviewed:
        errors.append("v2_resuelto exige revisado = true")
    if reviewed:
        for key in ("tono", "compas", "nivel"):
            if not data.get(key):
                errors.append(f"revisado exige completar «{key}»")
        if not bpm:
            errors.append("revisado exige completar «bpm»")
        if not no_harmony and (not chords or not bars):
            errors.append("revisado exige acordes y compases")
        for key in ("metodo", "autor", "fecha"):
            if not origin.get(key):
                errors.append(f"revisado exige declarar la procedencia («{key}»)")

    if errors:
        report.status = "con errores"
    elif reviewed and cleared:
        report.status = "publicable"
    elif reviewed:
        report.status = "revisado"
    elif chords or bars:
        report.status = "borrador"
    return report


def validate(directory: Path) -> list[Report]:
    return [validate_file(path) for path in sorted(directory.glob("*.toml"))]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="musicsite.acordes", description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["init", "validate", "pages", "library", "simple"])
    parser.add_argument("--dir", required=True, type=Path, help="carpeta local (fuera de git)")
    parser.add_argument("--out", type=Path, help="carpeta de salida de las páginas (pages)")
    parser.add_argument(
        "--index", type=Path, help="index.html cuyas tarjetas se actualizan (library)"
    )
    parser.add_argument("--slug", help="un solo tema (simple)")
    parser.add_argument("--preview", action="store_true", help="incluye borradores, con noindex")
    args = parser.parse_args(argv)

    if args.command == "simple":
        if not args.out:
            parser.error("simple exige --out")
        created = export_simple(args.dir, args.out, args.slug)
        print(f"{len(created)} archivos limpios escritos en {args.out}")
        return 0

    if args.command == "library":
        if not args.index:
            parser.error("library exige --index")
        from musicsite.songpages import update_library

        print(f"{update_library(args.dir, args.index)} tarjetas escritas en {args.index}")
        return 0

    if args.command == "pages":
        if not args.out:
            parser.error("pages exige --out")
        from musicsite.songpages import build

        written = build(args.dir, args.out, preview=args.preview)
        print(f"{len(written)} páginas escritas en {args.out}")
        return 0

    if args.command == "init":
        created = init(args.dir)
        print(f"{len(created)} plantillas creadas en {args.dir}")
        return 0

    reports = validate(args.dir)
    for report in reports:
        print(f"{report.status:12} {report.path.name}")
        for error in report.errors:
            print(f"    - {error}")
    failed = sum(1 for report in reports if report.errors)
    print(f"{len(reports)} archivos, {failed} con errores")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

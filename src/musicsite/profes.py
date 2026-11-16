"""Quién enseña qué: perfiles de ejemplo con reglas explícitas por artista o por tema.

Cada profe declara en `profes.toml` lo que puede enseñar: todos los temas de un artista, un tema
puntual o todo el repertorio (artista = "*"). Los temas existentes son los **publicados**: el
catálogo (`musicsite.catalog`) registra aquí el título y el artista de cada uno al cargar una
publicación (`use_catalog`). Este módulo dice quién puede enseñar un tema y escribe las tarjetas de guias.html.

Uso (con una carpeta de temas: una publicación o una copia local de lo publicado):
    python -m musicsite.profes validate [--dir <carpeta>]
    python -m musicsite.profes guides --dir <carpeta> [--page src/musicsite/web/guias.html]
"""

import argparse
import re
import tomllib
from pathlib import Path

from musicsite.app import WEB_DIR

PROFES_FILE = Path(__file__).with_name("profes.toml")
GUIDES_START = "<!-- guias:inicio -->"
GUIDES_END = "<!-- guias:fin -->"
ALL = "*"
RULE_KEYS = {"artista", "tema"}
MODES = {"linea", "presencial"}
MODE_LABELS = {"linea": "en línea", "presencial": "presencial"}


def artist_base(name: str) -> str:
    """«Javiera Mena (versión)» se enseña como «Javiera Mena»."""
    return re.sub(r"\s*\(.*\)$", "", name)


# slug -> (título, artista) de los temas publicados; lo registra el catálogo (`use_catalog`).
_catalog: dict[str, tuple[str, str]] = {}


def use_catalog(songs: dict[str, tuple[str, str]]) -> None:
    """Fija los temas que existen (los publicados): de ahí salen títulos, artistas y quién enseña qué."""
    global _catalog
    _catalog = dict(songs)


def songs_in(directory: Path) -> dict[str, tuple[str, str]]:
    """slug -> (título, artista) de los `.toml` de una carpeta (una publicación o una copia de ella)."""
    songs = {}
    for path in sorted(directory.glob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        songs[path.stem] = (str(data.get("titulo", path.stem)), str(data.get("artista", "")))
    return songs


def song_artist(slug: str) -> str | None:
    entry = _catalog.get(slug)
    return artist_base(entry[1]) if entry else None


def song_title(slug: str) -> str:
    return _catalog[slug][0] if slug in _catalog else slug


def check_rule(rule: dict) -> list[str]:
    """Forma de una regla (lo que no depende de qué temas haya publicados)."""
    errors = []
    if unknown := set(rule) - RULE_KEYS:
        errors.append(f"claves desconocidas {sorted(unknown)}")
    artist = rule.get("artista")
    if not artist:
        return errors + ["la regla no declara artista"]
    if artist == ALL and rule.get("tema"):
        errors.append("artista = «*» no admite tema")
    return errors


def check_rule_in_catalog(rule: dict) -> list[str]:
    """Lo que la regla dice contra los temas publicados: el artista o el tema pueden no existir (aún)."""
    artist, slug = rule.get("artista"), rule.get("tema")
    if not artist or artist == ALL:
        return []
    artists = {song_artist(s) for s in _catalog}
    if artist not in artists:
        return [f"artista «{artist}» no tiene temas publicados"]
    if slug and slug not in _catalog:
        return [f"tema «{slug}» no está publicado"]
    if slug and song_artist(slug) != artist:
        return [f"tema «{slug}» no es de {artist}"]
    return []


def catalog_warnings(profiles: list[dict]) -> list[str]:
    """Reglas que hoy no alcanzan a ningún tema publicado: se avisan, pero no impiden mostrar nada."""
    return [
        f"{p.get('id', '?')}: regla {rule}: {e}"
        for p in profiles
        for rule in p.get("ensena", [])
        for e in check_rule_in_catalog(rule)
    ]


def check_profile(profile: dict) -> list[str]:
    errors = []
    for key in ("id", "nombre", "lugar", "modo", "ensena"):
        if not profile.get(key):
            errors.append(f"falta {key}")
    if set(profile.get("modo", [])) - MODES:
        errors.append("modo solo admite linea y presencial")
    for rule in profile.get("ensena", []):
        errors += [f"regla {rule}: {e}" for e in check_rule(rule)]
    score, reviews = profile.get("puntuacion"), profile.get("resenas")
    if (score is None) != (reviews is None):
        errors.append("puntuacion y resenas van juntas")
    elif score is not None:
        if not isinstance(score, int | float) or isinstance(score, bool) or not 1 <= score <= 5:
            errors.append("puntuacion debe estar entre 1 y 5")
        if not isinstance(reviews, int) or isinstance(reviews, bool) or reviews < 1:
            errors.append("resenas debe ser un entero desde 1")
        if not profile.get("mock"):
            errors.append("puntuacion solo en perfiles de ejemplo (mock = true)")
    return errors


def load_profiles(path: Path = PROFES_FILE) -> list[dict]:
    """Lee y valida los perfiles; lanza ValueError con todos los errores juntos."""
    profiles = tomllib.loads(path.read_text(encoding="utf-8")).get("profe", [])
    errors, seen = [], set()
    for profile in profiles:
        name = profile.get("id", "?")
        errors += [f"{name}: {e}" for e in check_profile(profile)]
        if name in seen:
            errors.append(f"{name}: id repetido")
        seen.add(name)
    if errors:
        raise ValueError("\n".join(errors))
    return profiles


def teaches(profile: dict, slug: str) -> bool:
    for rule in profile["ensena"]:
        if rule["artista"] == ALL:
            return True
        if rule["artista"] == song_artist(slug) and rule.get("tema", slug) == slug:
            return True
    return False


def songs_of(profile: dict) -> list[str]:
    return [slug for slug in _catalog if teaches(profile, slug)]


def teachers_for(slug: str, profiles: list[dict] | None = None) -> list[dict]:
    return [p for p in profiles or load_profiles() if teaches(p, slug)]


def top_teachers(slug: str, limit: int = 5, profiles: list[dict] | None = None) -> list[dict]:
    """Las guías que pueden enseñar el tema, mejor puntuadas primero.

    Con nota: por puntuación y luego por reseñas. Sin nota («Nuevo»): al final, primero las que
    están disponibles hoy.
    """

    def key(p: dict):
        rated = p.get("puntuacion") is not None
        return (
            not rated,
            -(p.get("puntuacion") or 0),
            -(p.get("resenas") or 0),
            not p.get("hoy", False),
            p["nombre"],
        )

    return sorted(teachers_for(slug, profiles), key=key)[:limit]


def coverage(profile: dict, slug: str) -> str:
    """Cuánto cubre la guía respecto de este tema: «Todo el repertorio», «Los Tres (todos)»…"""
    best = None
    for rule in profile["ensena"]:
        if rule["artista"] == ALL:
            best = best or "Todo el repertorio"
        elif rule["artista"] == song_artist(slug):
            if rule.get("tema") == slug:
                return "Este tema"
            if "tema" not in rule:
                best = f"{rule['artista']} (todos)"
    return best or ""


def describe(profile: dict) -> str:
    """Las reglas en palabras: «Todo el repertorio», «Los Tres (todos)», «Ven aquí»."""
    parts = []
    for rule in profile["ensena"]:
        if rule["artista"] == ALL:
            return "Todo el repertorio"
        slug = rule.get("tema")
        parts.append(song_title(slug) if slug else f"{rule['artista']} (todos)")
    return ", ".join(parts)


def initials(name: str) -> str:
    return "".join(word[0] for word in name.split()[:2]).upper()


def avatar(profile: dict, index: int) -> str:
    cls = "ac-avatar is-oro" if index % 2 else "ac-avatar"
    return f'<span class="{cls}" aria-hidden="true">{initials(profile["nombre"])}</span>'


def price(profile: dict) -> str:
    return f"${profile['precio']:,}".replace(",", ".") if profile.get("precio") else "Por definir"


def guide_card(profile: dict, index: int) -> str:
    from acordia_render.songpages import esc

    songs = songs_of(profile)
    modes = ",".join(profile["modo"])
    hoy = profile.get("hoy", False)
    cost = (
        f'<span class="ac-mono fw-semibold">{price(profile)} <span class="small fw-normal '
        'text-body-secondary">/ clase</span></span>'
        if profile.get("precio")
        else '<span class="small text-body-secondary">Precio por definir</span>'
    )
    when = (
        '<span class="ac-chip ac-chip-ok">Disponible hoy</span>'
        if hoy
        else f'<span class="small text-body-secondary">Próxima hora: {esc(profile.get("proxima", "por definir"))}</span>'
    )
    chips = "".join(
        f'<span class="ac-chip">{esc(x)}</span>'
        for x in profile["barrios"] + profile["instrumentos"]
    )
    mock = '<span class="ac-chip ac-chip-example">Ejemplo</span>' if profile.get("mock") else ""
    note = f" {esc(profile['nota'])}" if profile.get("nota") else ""
    name = esc(profile["nombre"])
    return f"""      <div class="col" id="guia-{profile["id"]}" data-barrio="{",".join(profile["barrios"])}" data-inst="{",".join(profile["instrumentos"])}" data-modo="{modes}" data-hoy="{int(hoy)}" data-temas="{",".join(songs)}">
        <div class="card h-100"><div class="card-body d-grid gap-3 align-content-start">
          <div class="d-flex gap-3 align-items-center">
            {avatar(profile, index)}
            <div class="d-grid"><h2 class="h5 m-0">{name}</h2><span class="small text-body-secondary">{esc(profile["lugar"])}</span></div>
          </div>
          <div class="d-flex flex-wrap gap-2">{chips}{mock}</div>
          <p class="m-0 small text-body-secondary"><strong>Enseña:</strong> {esc(describe(profile))} ({len(songs)} {"tema" if len(songs) == 1 else "temas"}).{note}</p>
          <div class="d-flex justify-content-between align-items-center gap-2">
            {when}{cost}
          </div>
          <button class="btn {"btn-primary" if hoy else "btn-outline-primary"}" type="button" data-bs-toggle="modal" data-bs-target="#conectar" data-guia="{name}" data-precio="{price(profile)}">Conectar</button>
        </div></div>
      </div>"""


def render_guides(text: str, profiles: list[dict] | None = None) -> str:
    """`text` (guias.html) con las tarjetas de los guías entre las marcas; usa los temas publicados."""
    profiles = profiles or load_profiles()
    start = text.index(GUIDES_START) + len(GUIDES_START)
    end = text.index(GUIDES_END)
    cards = "\n".join(guide_card(p, i) for i, p in enumerate(profiles))
    return text[:start] + "\n" + cards + "\n      " + text[end:]


def update_guides(page: Path, profiles: list[dict] | None = None) -> int:
    """Reemplaza las tarjetas de guias.html entre las marcas de los guías."""
    profiles = profiles or load_profiles()
    page.write_text(render_guides(page.read_text(encoding="utf-8"), profiles), encoding="utf-8")
    return len(profiles)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="musicsite.profes", description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["validate", "guides"])
    parser.add_argument("--page", type=Path, default=WEB_DIR / "guias.html")
    parser.add_argument(
        "--dir", type=Path, help="carpeta con los temas (publicación o copia local)"
    )
    args = parser.parse_args(argv)
    try:
        profiles = load_profiles()
    except ValueError as error:
        print(error)
        return 1
    if args.dir:
        use_catalog(songs_in(args.dir))
    if args.command == "guides":
        if not args.dir:
            parser.error("guides exige --dir (los temas que existen)")
        print(f"{update_guides(args.page, profiles)} tarjetas escritas en {args.page}")
    else:
        print(f"{len(profiles)} perfiles válidos")
        if args.dir:
            for warning in catalog_warnings(profiles):
                print(f"  aviso: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Quién enseña qué: perfiles de ejemplo con reglas explícitas por artista o por tema.

Cada profe declara en `profes.toml` lo que puede enseñar: todos los temas de un artista, un tema
puntual o todo el repertorio (artista = "*"). Este módulo valida esas reglas contra el repertorio,
dice quién puede enseñar un tema y escribe las tarjetas de guias.html.

Uso:
    python -m musicsite.profes validate
    python -m musicsite.profes guides [--page src/musicsite/web/guias.html]
"""

import argparse
import re
import tomllib
from pathlib import Path

from musicsite.acordes import REPERTOIRE
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


TITLES = {slug: title for slug, title, _, _ in REPERTOIRE}
SONG_ARTIST = {slug: artist_base(artist) for slug, _, artist, _ in REPERTOIRE}
ARTISTS = set(SONG_ARTIST.values())


def check_rule(rule: dict) -> list[str]:
    errors = []
    if unknown := set(rule) - RULE_KEYS:
        errors.append(f"claves desconocidas {sorted(unknown)}")
    artist, slug = rule.get("artista"), rule.get("tema")
    if not artist:
        return errors + ["la regla no declara artista"]
    if artist == ALL:
        if slug:
            errors.append("artista = «*» no admite tema")
    elif artist not in ARTISTS:
        errors.append(f"artista «{artist}» no está en el repertorio")
    elif slug and SONG_ARTIST.get(slug) != artist:
        errors.append(f"tema «{slug}» no es de {artist}")
    elif slug is not None and slug not in SONG_ARTIST:
        errors.append(f"tema «{slug}» no está en el repertorio")
    return errors


def check_profile(profile: dict) -> list[str]:
    errors = []
    for key in ("id", "nombre", "lugar", "modo", "ensena"):
        if not profile.get(key):
            errors.append(f"falta {key}")
    if set(profile.get("modo", [])) - MODES:
        errors.append("modo solo admite linea y presencial")
    for rule in profile.get("ensena", []):
        errors += [f"regla {rule}: {e}" for e in check_rule(rule)]
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
        if rule["artista"] == SONG_ARTIST.get(slug) and rule.get("tema", slug) == slug:
            return True
    return False


def songs_of(profile: dict) -> list[str]:
    return [slug for slug, *_ in REPERTOIRE if teaches(profile, slug)]


def teachers_for(slug: str, profiles: list[dict] | None = None) -> list[dict]:
    return [p for p in profiles or load_profiles() if teaches(p, slug)]


def describe(profile: dict) -> str:
    """Las reglas en palabras: «Todo el repertorio», «Los Tres (todos)», «Ven aquí»."""
    parts = []
    for rule in profile["ensena"]:
        if rule["artista"] == ALL:
            return "Todo el repertorio"
        slug = rule.get("tema")
        parts.append(TITLES[slug] if slug else f"{rule['artista']} (todos)")
    return ", ".join(parts)


def initials(name: str) -> str:
    return "".join(word[0] for word in name.split()[:2]).upper()


def avatar(profile: dict, index: int) -> str:
    cls = "ac-avatar is-oro" if index % 2 else "ac-avatar"
    return f'<span class="{cls}" aria-hidden="true">{initials(profile["nombre"])}</span>'


def price(profile: dict) -> str:
    return f"${profile['precio']:,}".replace(",", ".") if profile.get("precio") else "Por definir"


def guide_card(profile: dict, index: int) -> str:
    from musicsite.songpages import esc

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
    return f"""      <div class="col" data-barrio="{",".join(profile["barrios"])}" data-inst="{",".join(profile["instrumentos"])}" data-modo="{modes}" data-hoy="{int(hoy)}" data-temas="{",".join(songs)}">
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


def update_guides(page: Path, profiles: list[dict] | None = None) -> int:
    """Reemplaza las tarjetas de guias.html entre las marcas de los guías."""
    profiles = profiles or load_profiles()
    text = page.read_text(encoding="utf-8")
    start = text.index(GUIDES_START) + len(GUIDES_START)
    end = text.index(GUIDES_END)
    cards = "\n".join(guide_card(p, i) for i, p in enumerate(profiles))
    page.write_text(text[:start] + "\n" + cards + "\n      " + text[end:], encoding="utf-8")
    return len(profiles)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="musicsite.profes", description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["validate", "guides"])
    parser.add_argument("--page", type=Path, default=WEB_DIR / "guias.html")
    args = parser.parse_args(argv)
    try:
        profiles = load_profiles()
    except ValueError as error:
        print(error)
        return 1
    if args.command == "guides":
        print(f"{update_guides(args.page, profiles)} tarjetas escritas en {args.page}")
    else:
        print(f"{len(profiles)} perfiles válidos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

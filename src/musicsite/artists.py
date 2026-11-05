"""Sección Artistas (S24): datos, validación y HTML de `artistas.html`.

Los artistas salen de `artists.json` en la publicación vigente del bucket editorial (junto a
`index.json`), que escribe el admin:

    {"format": 1, "artists": [{"slug", "name", "description", "links": [{"label", "url"}]}]}

Si el archivo no existe o no sirve, se usan los datos de `FALLBACK` (los de siempre). Todo texto
se escapa y los enlaces externos son solo http/https. La cantidad de temas de cada artista sale
de los temas publicados, igual que el contador de la portada (S23).
"""

import json
import logging
import re
import tomllib
from pathlib import Path
from urllib.parse import quote, urlsplit

from musicsite.songpages import artist_key, esc, sort_key

ARTISTS_START = "<!-- artistas:inicio -->"
ARTISTS_END = "<!-- artistas:fin -->"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
MAX_ARTISTS = 200
MAX_LINKS = 10
PHOTO_MAX_BYTES = 300 * 1024
PHOTO = re.compile(r"fotos/[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{12}\.jpg")
log = logging.getLogger("musicsite.artists")

FALLBACK: list[dict] = [
    {
        "slug": "javiera-mena",
        "name": "Javiera Mena",
        "description": (
            "Cantautora y productora santiaguina, nacida en 1983, que se mueve entre el pop "
            "electrónico y el indie. Debutó con Esquemas juveniles (2006), y su canción «Otra era» "
            "(2014) fue nominada al Grammy Latino."
        ),
        "links": [
            {"label": "Wikipedia", "url": "https://es.wikipedia.org/wiki/Javiera_Mena"},
            {
                "label": "Más sobre Javiera Mena en MusicaPopular.cl",
                "url": "https://www.musicapopular.cl/artista/javiera-mena/",
            },
        ],
    },
    {
        "slug": "los-tres",
        "name": "Los Tres",
        "description": (
            "Banda de Concepción formada en 1987 y liderada por Álvaro Henríquez, que mezcla el "
            "rock con raíces del folclor chileno. Entre sus discos están La espada & la pared, de "
            "donde sale «Déjate caer», y su MTV Unplugged; en 2023 volvieron a reunirse con su "
            "formación original."
        ),
        "links": [
            {"label": "Wikipedia", "url": "https://es.wikipedia.org/wiki/Los_Tres"},
            {
                "label": "Más sobre Los Tres en MusicaPopular.cl",
                "url": "https://www.musicapopular.cl/grupo/los-tres-2023/",
            },
        ],
    },
    {
        "slug": "los-bunkers",
        "name": "Los Bunkers",
        "description": (
            "Banda de Concepción surgida a fines de los años noventa. «Llueve sobre la ciudad» y "
            "«Ven aquí» son de Vida de perros (2005) y «Bailando solo», de La velocidad de la luz "
            "(2013). Tras una pausa desde 2014, volvieron a los escenarios y dieron dos noches en "
            "el Estadio Nacional en 2024."
        ),
        "links": [
            {"label": "Wikipedia", "url": "https://es.wikipedia.org/wiki/Los_Bunkers"},
            {
                "label": "Más sobre Los Bunkers en MusicaPopular.cl",
                "url": "https://www.musicapopular.cl/grupo/los-bunkers/",
            },
        ],
    },
    {
        "slug": "gepe",
        "name": "Gepe",
        "description": (
            "Nombre artístico de Daniel Riveros, cantautor santiaguino nacido en 1981 que combina "
            "pop, electrónica y folclor. Debutó con Gepinto (2005) y en 2021 su canción «Confía», "
            "junto a Vicentico, fue nominada al Grammy Latino."
        ),
        "links": [
            {"label": "Wikipedia", "url": "https://es.wikipedia.org/wiki/Gepe"},
            {
                "label": "Más sobre Gepe en MusicaPopular.cl",
                "url": "https://www.musicapopular.cl/artista/gepe/",
            },
        ],
    },
]


def safe_url(value: object) -> str | None:
    """La URL si es http/https absoluta y sin espacios ni caracteres de control; si no, None."""
    if not isinstance(value, str) or not (1 <= len(value) <= 500):
        return None
    if any(ch.isspace() or ord(ch) < 32 for ch in value):
        return None
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    return value


def parse_artists(text: str) -> list[dict]:
    """Artistas válidos de `artists.json`. Falla (ValueError) si el archivo no sirve.

    Un enlace inválido se descarta (y se anota); un artista mal formado invalida el archivo."""
    data = json.loads(text)
    if not isinstance(data, dict) or data.get("format") != 1:
        raise ValueError("formato no soportado")
    raw = data.get("artists")
    if not isinstance(raw, list) or not (1 <= len(raw) <= MAX_ARTISTS):
        raise ValueError("lista de artistas ausente o fuera de rango")
    artists, seen = [], set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("artista mal formado")
        slug, name, description = item.get("slug"), item.get("name"), item.get("description", "")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or len(slug) > 80:
            raise ValueError(f"slug no válido: {slug!r}")
        if slug in seen:
            raise ValueError(f"slug repetido: {slug}")
        seen.add(slug)
        if not isinstance(name, str) or not (1 <= len(name.strip()) <= 80):
            raise ValueError(f"nombre no válido en {slug}")
        if not isinstance(description, str) or len(description) > 1500:
            raise ValueError(f"descripción no válida en {slug}")
        links = []
        raw_links = item.get("links", [])
        if not isinstance(raw_links, list):
            raise ValueError(f"enlaces no válidos en {slug}")
        for link in raw_links[:MAX_LINKS]:
            label = link.get("label") if isinstance(link, dict) else None
            url = safe_url(link.get("url")) if isinstance(link, dict) else None
            if url is None or not isinstance(label, str) or not (1 <= len(label.strip()) <= 100):
                log.warning("artistas: se descarta un enlace de %s", slug)
                continue
            links.append({"label": label.strip(), "url": url})
        artist = {
            "slug": slug,
            "name": name.strip(),
            "description": description.strip(),
            "links": links,
        }
        photo = item.get("photo")
        if photo is not None:
            if (
                isinstance(photo, str)
                and PHOTO.fullmatch(photo)
                and photo.startswith(f"fotos/{slug}-")
            ):
                artist["photo"] = photo
            else:
                log.warning("artistas: se descarta la foto de %s (ruta no válida)", slug)
        credit = item.get("photo_credit")
        if isinstance(credit, str) and 1 <= len(credit.strip()) <= 200:
            artist["photo_credit"] = credit.strip()
            credit_url = safe_url(item.get("photo_credit_url"))
            if credit_url:
                artist["photo_credit_url"] = credit_url
        artists.append(artist)
    return artists


def read_photo(directory: Path, path: str) -> bytes | None:
    """Los bytes de la foto si es un JPEG de tamaño razonable dentro de `directory`; si no, None."""
    if not PHOTO.fullmatch(path):
        return None
    try:
        data = (directory / path).read_bytes()
    except OSError:
        return None
    if len(data) > PHOTO_MAX_BYTES or not data.startswith(b"\xff\xd8\xff"):
        log.warning("artistas: se descarta la foto %s (no es un JPEG de hasta 300 KB)", path)
        return None
    return data


def load_artists_and_photos(directory: Path | None) -> tuple[list[dict], dict[str, bytes]]:
    """Artistas de la publicación y las fotos que sí sirven (ruta -> bytes).

    Un artista cuya foto falta o no sirve se muestra sin foto: nunca bloquea la publicación."""
    artists = load_artists(directory)
    photos: dict[str, bytes] = {}
    if directory is None:
        return artists, photos
    shown = []
    for artist in artists:
        path = artist.get("photo")
        data = read_photo(directory, path) if path else None
        if path and data is None:
            artist = {k: v for k, v in artist.items() if k != "photo"}
        elif path and data is not None:
            photos[path] = data
        shown.append(artist)
    return shown, photos


def load_artists(directory: Path | None) -> list[dict]:
    """Artistas de `directory/artists.json`, o `FALLBACK` si no existe o no sirve."""
    if directory is None:
        return FALLBACK
    try:
        return parse_artists((directory / "artists.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return FALLBACK
    except (OSError, ValueError, UnicodeDecodeError) as error:  # JSON roto incluido (ValueError)
        log.warning("artistas: artists.json no sirve (%s); se usan los datos de respaldo", error)
        return FALLBACK


def base_artist(name: str) -> str:
    """«Javiera Mena (versión)» -> «Javiera Mena»: una versión cuenta para su artista."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name)


def songs_by_artist(directory: Path) -> dict[str, list[tuple[str, str]]]:
    """artist_key -> [(título, slug)] de los temas de `directory` (todos publicados)."""
    result: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(directory.glob("*.toml")):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            title, artist = str(data["titulo"]), str(data["artista"])
        except OSError, ValueError, KeyError:
            continue
        result.setdefault(artist_key(base_artist(artist)), []).append((title, path.stem))
    for songs in result.values():
        songs.sort(key=lambda s: sort_key(s[0]))
    return result


def description_html(text: str) -> str:
    """La descripción como párrafos: una línea en blanco separa párrafos; un salto simple es `<br>`.

    Todo se escapa (texto plano). Sin texto, nada. El interlineado y la separación van en línea:
    `style.css` está copiado en research y tocarlo obliga a sincronizar."""
    paragraphs = [
        p.strip() for p in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()) if p.strip()
    ]
    if not paragraphs:
        return ""
    body = "".join(
        f'<p class="m-0">{"<br>".join(esc(line.strip()) for line in p.split(chr(10)))}</p>'
        for p in paragraphs
    )
    return f'<div class="ac-artist-desc d-grid gap-3" style="line-height:1.65">{body}</div>'


def photo_credit_html(artist: dict) -> str:
    """Atribución de la foto (CC BY/BY-SA la exigen): texto escapado y, si hay, enlace externo."""
    credit = artist.get("photo_credit")
    if not credit or not artist.get("photo"):
        return ""
    url = artist.get("photo_credit_url")
    if url:
        credit = (
            f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(credit)}'
            '<span class="visually-hidden"> (se abre en otra pestaña)</span></a>'
        )
    else:
        credit = esc(credit)
    return f'<p class="m-0 small text-body-secondary ac-photo-credit">{credit}</p>'


def artist_card(artist: dict, songs: list[tuple[str, str]]) -> str:
    name = artist["name"]
    desc = description_html(artist["description"])
    if songs:
        count = "1 tema disponible" if len(songs) == 1 else f"{len(songs)} temas disponibles"
        titles = "".join(
            f'<li><a href="cancion-{esc(slug)}.html">{esc(title)}</a></li>' for title, slug in songs
        )
        status = (
            f'<p class="m-0 ac-artist-count"><strong>{count}</strong></p>'
            f'<ul class="m-0 ps-3 text-body-secondary">{titles}</ul>'
            f'<a class="btn btn-outline-primary ac-artist-library" '
            f'href="index.html?q={quote(name)}#biblioteca">Ver sus temas en la Biblioteca</a>'
        )
    else:
        status = '<p class="m-0 ac-artist-count"><span class="ac-chip">Próximamente</span></p>'
    links = "".join(
        f'<li><a href="{esc(link["url"])}" target="_blank" rel="noopener noreferrer">'
        f'{esc(link["label"])}<span class="visually-hidden"> (se abre en otra pestaña)</span>'
        "</a></li>"
        for link in artist["links"]
    )
    links_html = (
        f'<ul class="m-0 ps-3 small ac-artist-links" aria-label="Enlaces externos de {esc(name)}">'
        f"{links}</ul>"
        if links
        else ""
    )
    photo = artist.get("photo")
    heading = f'<h2 class="h4 m-0">{esc(name)}</h2>'
    if photo:
        heading = (
            '<div class="d-flex align-items-center gap-3">'
            f'<img class="ac-artist-photo" src="{esc(photo)}" alt="Foto de {esc(name)}" '
            'width="72" height="72" loading="lazy" decoding="async" '
            'style="flex:none;border-radius:50%;object-fit:cover;border:2px solid var(--ac-oro)">'
            f"{heading}</div>{photo_credit_html(artist)}"
        )
    return f"""        <div class="col" id="{esc(artist["slug"])}" data-ac-artist-card>
          <div class="card h-100">
            <div class="card-body d-grid gap-3 align-content-start">
              {heading}
              {desc}
              {status}
              {links_html}
            </div>
          </div>
        </div>"""


def render_artists(artists: list[dict], published: dict[str, list[tuple[str, str]]]) -> str:
    ordered = sorted(artists, key=lambda a: artist_key(a["name"]))
    cards = "\n".join(artist_card(a, published.get(artist_key(a["name"]), [])) for a in ordered)
    return f'    <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3">\n{cards}\n    </div>'


def apply_artists(page: str, block: str) -> str:
    """`page` (artistas.html) con `block` entre las marcas de artistas; sin marcas, igual."""
    if ARTISTS_START not in page:
        return page
    start = page.index(ARTISTS_START) + len(ARTISTS_START)
    return page[:start] + "\n" + block + "\n    " + page[page.index(ARTISTS_END) :]


def build_page_and_photos(
    page: str, directory: Path | None, songs_dir: Path | None
) -> tuple[str, dict[str, bytes]]:
    """artistas.html listo y las fotos que cita (ruta -> bytes)."""
    published = songs_by_artist(songs_dir) if songs_dir is not None else {}
    artists, photos = load_artists_and_photos(directory)
    return apply_artists(page, render_artists(artists, published)), photos


def build_page(page: str, directory: Path | None, songs_dir: Path | None) -> str:
    """artistas.html listo: artistas de `directory` (o el respaldo) y temas de `songs_dir`."""
    return build_page_and_photos(page, directory, songs_dir)[0]

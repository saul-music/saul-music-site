"""SEO mínimo (S115): quién puede indexarse, `robots.txt`, `sitemap.xml` y los metadatos de un tema.

Hasta lanzar (S6), `INDEXING_ENABLED` está apagado y todo responde `noindex`. Lanzar es cambiar esa
constante por PR y quitar la cabecera de Firebase Hosting (`hosting.sh`, en `saul-music-infra`).
Incluso encendido, solo `acordia.io` se indexa: `*.web.app` y `*.run.app` siguen con `noindex`.
"""

import re
from xml.sax.saxutils import escape

from fastapi import Request

CANONICAL_HOST = "acordia.io"
INDEXING_ENABLED = False
BASE_URL = f"https://{CANONICAL_HOST}"

# Páginas públicas que van al mapa del sitio (las de cuenta, `pedidos` y demás nunca).
STATIC_PAGES = ("/", "/artistas.html", "/guias.html", "/privacidad.html")
INDEXABLE_PATHS = frozenset(STATIC_PAGES) | {"/index.html"}
SONG_PATH = re.compile(r"/cancion-[a-z0-9]+(?:-[a-z0-9]+)*\.html")

_TITLE = re.compile(r"<title>(.*?) · Acordia</title>", re.S)
_DESCRIPTION = re.compile(r'<meta name="description" content="[^"]*">')
_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
_ARTIST = re.compile(r'<p class="m-0 fs-5 text-body-secondary">(.*?)</p>', re.S)


def host_of(request: Request) -> str:
    """El host que escribió la persona: Hosting reenvía el original en `X-Forwarded-Host`."""
    raw = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    return raw.split(",")[0].strip().split(":")[0].lower()


def is_indexable(request: Request, *, enabled: bool = INDEXING_ENABLED) -> bool:
    """Solo el dominio propio, con el lanzamiento encendido, y solo páginas públicas."""
    if not enabled or host_of(request) != CANONICAL_HOST:
        return False
    if request.query_params.get("embed") == "1":
        return False  # el tema dentro del iframe del repertorio no se indexa
    return request.url.path in INDEXABLE_PATHS or bool(SONG_PATH.fullmatch(request.url.path))


def robots_txt(request: Request, *, enabled: bool = INDEXING_ENABLED) -> str:
    if not enabled or host_of(request) != CANONICAL_HOST:
        return "User-agent: *\nDisallow: /\n"
    return f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {BASE_URL}/sitemap.xml\n"


def sitemap_xml(song_paths: list[str], extra_pages: list[str]) -> str:
    """URLs absolutas con el dominio canónico: la página principal, las públicas y cada tema."""
    paths = [*extra_pages, *sorted(song_paths)]
    urls = "".join(f"<url><loc>{escape(BASE_URL + path)}</loc></url>" for path in paths)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'
    )


def enrich_song(text: str, path: str) -> str:
    """Título con el artista (único por tema), descripción propia y `canonical` absoluto."""
    heading, artist = _H1.search(text), _ARTIST.search(text)
    if heading is not None and artist is not None:
        name, by = heading.group(1).strip(), artist.group(1).strip()
        text = _TITLE.sub(lambda _: f"<title>{name} · {by} · Acordia</title>", text, count=1)
        description = (
            f'<meta name="description" content="Acordes de {name}, de {by}: '
            'estructura por compases, con la versión original y una simplificada.">'
        )
        text = _DESCRIPTION.sub(lambda _: description, text, count=1)
    canonical = f'<link rel="canonical" href="{BASE_URL}{path}">'
    return text.replace("</head>", canonical + "</head>", 1)

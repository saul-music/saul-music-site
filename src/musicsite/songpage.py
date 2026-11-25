"""Ajustes del sitio a las páginas de canción que arma la librería `acordia_render` (S104, S105).

La librería es compartida con el admin y no conoce las cuentas ni Aprende: el sitio le agrega,
al servir, lo suyo. Son reemplazos de texto sobre HTML propio y conocido; si la plantilla cambia
y un fragmento no está, no pasa nada.
"""

import html
import re

from musicsite import seo

PEDIDOS_NAV = (
    '<li class="nav-item"><a class="nav-link" href="pedidos.html">Pide una canción</a></li>'
)
ACCOUNT_NAV = (
    '\n          <li class="nav-item"><a class="nav-link" href="/aprende/">Aprende</a></li>'
    '\n          <li class="nav-item"><a class="nav-link" href="mi-acordia.html">Mi cuenta</a></li>'
)
PEDIDOS_FOOT = '<a href="pedidos.html">Pide una canción</a>'
ACCOUNT_FOOT = '<a href="/aprende/">Aprende</a><a href="mi-acordia.html">Mi cuenta</a>'
# Modo `?embed=1` (C31): el tema dentro de un iframe del repertorio, sin menú ni pie.
EMBED_STYLE = (
    "<style>.navbar,.ac-footer,.ac-frieze{display:none!important}"
    "body{padding-top:0!important}</style>"
)
SONG_PATH = re.compile(r"/cancion-([a-z0-9]+(?:-[a-z0-9]+)*)\.html")


def song_slug(path: str) -> str | None:
    found = SONG_PATH.fullmatch(path)
    return found.group(1) if found else None


def decorate(page: bytes, *, api_key: str = "", embed: bool = False, path: str = "") -> bytes:
    """Menú y pie con «Aprende» y «Mi cuenta»; «Aprende teoría» va a `/aprende/` (C28).

    Con `embed`, sin menú, pie ni script de cuenta (el reproductor va dentro de otra página).
    Sin `embed` y con `api_key`, suma el script de cuenta (favoritos, repertorios y preferencias);
    ese script no hace nada si la persona no tiene sesión.
    """
    text = page.decode("utf-8")
    text = text.replace('href="aprender.html"', 'href="/aprende/"')
    if embed:
        return text.replace("</head>", EMBED_STYLE + "</head>", 1).encode("utf-8")
    if song_slug(path):
        text = seo.enrich_song(text, path)  # título con artista y `canonical` (S115)
    text = text.replace(PEDIDOS_NAV, PEDIDOS_NAV + ACCOUNT_NAV, 1)
    text = text.replace(PEDIDOS_FOOT + "\n", PEDIDOS_FOOT + ACCOUNT_FOOT + "\n", 1)
    if api_key:
        meta = f'<meta name="firebase-api-key" content="{html.escape(api_key, quote=True)}">'
        text = text.replace("</head>", meta + "</head>", 1)
        text = text.replace(
            "</body>", '<script type="module" src="cuenta-tema.js"></script></body>', 1
        )
    return text.encode("utf-8")


def listing(pages: dict[str, bytes]) -> list[dict]:
    """Los temas publicados con título y artista, de sus páginas (datos que ya son públicos)."""
    out = []
    for path, body in pages.items():
        slug = song_slug(path)
        if slug is None:
            continue
        text = body.decode("utf-8")
        title = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
        artist = re.search(r'<p class="m-0 fs-5 text-body-secondary">(.*?)</p>', text, re.S)
        out.append(
            {
                "slug": slug,
                "title": html.unescape(title.group(1).strip()) if title else slug,
                "artist": html.unescape(artist.group(1).strip()) if artist else "",
            }
        )
    return sorted(out, key=lambda s: (s["artist"].casefold(), s["title"].casefold()))

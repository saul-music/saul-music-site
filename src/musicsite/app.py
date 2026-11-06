"""Servidor del sitio: FastAPI entrega los archivos de `web/` y las páginas de canción; lo demás
es 404 sin cuerpo.

Las páginas de canción las renderiza la librería `acordia_render` (R1: plantillas, validador,
estilos, scripts y muestras de la guitarra) desde los TOML publicados: los de la publicación
vigente del bucket editorial si `EDITORIAL_DIR` está (S9, ver `catalog.py`) o, si no, los de
`songs/` (el respaldo). Solo se sirve lo que existe en `web/`, en los archivos de la librería o en
el catálogo, buscado por nombre exacto en un diccionario: no hay sistema de archivos por ruta, así
que no hay recorrido de directorios.
Sin /docs, /redoc ni /openapi.json.
"""

import mimetypes
import os
from pathlib import Path

import uvicorn
from acordia_render import guides
from acordia_render.songpages import WEB_DIR as LIB_WEB_DIR
from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException

WEB_DIR = Path(__file__).parent / "web"
SONGS_DIR = Path(__file__).parent / "songs"
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}
CACHE_SAMPLES = "public, max-age=86400"  # 1 día; un banco nuevo debe llevar otro nombre de archivo
HEADERS = {
    "Cache-Control": "public, max-age=300",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Las páginas cargan Bootstrap (jsDelivr) y fuentes (Google Fonts) y traen un script y estilos
    # en línea; nada más. Los formularios no envían a ningún lado (todavía).
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
}


def load_files(root: Path) -> dict[str, tuple[bytes, str]]:
    """Ruta pública -> (contenido, tipo). Solo archivos directos de `root`, sin ocultos."""
    files: dict[str, tuple[bytes, str]] = {}
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        kind = TYPES.get(path.suffix) or mimetypes.guess_type(path.name)[0]
        if kind is None:
            continue  # tipo desconocido: no se sirve
        files["/" + path.name] = (path.read_bytes(), kind)
    if "/index.html" in files:
        files["/"] = files["/index.html"]
    return files


def create_app(
    root: Path = WEB_DIR,
    songs: Path | None = SONGS_DIR,
    editorial: Path | None = None,
    refresh_seconds: float = 60,
) -> FastAPI:
    from musicsite import profes
    from musicsite.catalog import Catalog  # aquí y no arriba: profes importa este módulo

    guides.use(profes)  # las guías de ejemplo son del sitio; la librería las pide a este módulo
    # Los archivos de la página de canción (style.css, acordia.js, guitarra.js, la tipografía y las
    # muestras) vienen de la librería; los del sitio (portada, guías, artistas…) tienen prioridad.
    files = {**load_files(LIB_WEB_DIR), **load_files(root)}
    index_html = files["/index.html"][0].decode() if "/index.html" in files else ""
    artists_html = files["/artistas.html"][0].decode() if "/artistas.html" in files else ""
    catalog = Catalog(index_html, songs, editorial, refresh_seconds, artists_html=artists_html)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)

    @app.middleware("http")
    async def secure_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        for name, value in HEADERS.items():
            if name == "Cache-Control" and name in response.headers:
                continue  # las fotos con hash en el nombre fijan su propia caché larga
            response.headers[name] = value
        return response

    @app.exception_handler(HTTPException)
    async def empty_error(_: Request, exc: HTTPException) -> Response:
        return Response(status_code=exc.status_code)  # sin cuerpo: no revela nada

    @app.api_route("/{name:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def page(name: str) -> Response:
        path = "/" + name
        state = catalog.current()
        if path in ("/", "/index.html") and state.index is not None:
            return Response(state.index, media_type=TYPES[".html"])
        if path == "/artistas.html" and state.artists is not None:
            return Response(state.artists, media_type=TYPES[".html"])
        photo = state.photos.get(path[1:]) if path.startswith("/fotos/") else None
        if photo is not None:  # el nombre lleva el hash: una foto nueva es otro archivo
            return Response(
                photo,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=31536000, immutable"},
            )
        song = state.pages.get(path)
        if song is not None:
            return Response(song, media_type=TYPES[".html"])
        entry = files.get(path)
        if entry is None:
            return Response(status_code=404)
        body, kind = entry
        if path.endswith(".mp3"):  # muestras de la guitarra (S37): no cambian; un día de caché
            return Response(body, media_type=kind, headers={"Cache-Control": CACHE_SAMPLES})
        return Response(body, media_type=kind)

    return app


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    editorial = os.environ.get("EDITORIAL_DIR", "")
    refresh = float(os.environ.get("EDITORIAL_REFRESH_SECONDS", "60"))
    app = create_app(editorial=Path(editorial) if editorial else None, refresh_seconds=refresh)
    # Sin registro de accesos: el sitio no guarda rastro de quién lo visita.
    uvicorn.run(app, host="0.0.0.0", port=port, access_log=False, log_level="warning")  # noqa: S104
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

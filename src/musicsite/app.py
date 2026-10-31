"""Servidor del sitio: FastAPI entrega los archivos de `web/` y las páginas de canción; lo demás
es 404 sin cuerpo.

Las páginas de canción se renderizan con Jinja2 (`templates/`) desde los TOML de `songs/` al
arrancar. Solo se sirve lo que existe en `web/` o en `songs/` en ese momento, buscado por nombre
exacto en un diccionario: no hay sistema de archivos por ruta, así que no hay recorrido de
directorios.
Sin /docs, /redoc ni /openapi.json.
"""

import mimetypes
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException

WEB_DIR = Path(__file__).parent / "web"
SONGS_DIR = Path(__file__).parent / "songs"
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}
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
        "font-src https://fonts.gstatic.com; img-src 'self' data:; "
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


def create_app(root: Path = WEB_DIR, songs: Path | None = SONGS_DIR) -> FastAPI:
    files = load_files(root)
    if songs is not None:
        from musicsite.songpages import render_published

        for slug, page in render_published(songs).items():
            files[f"/cancion-{slug}.html"] = (page.encode(), TYPES[".html"])
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)

    @app.middleware("http")
    async def secure_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.update(HEADERS)
        return response

    @app.exception_handler(HTTPException)
    async def empty_error(_: Request, exc: HTTPException) -> Response:
        return Response(status_code=exc.status_code)  # sin cuerpo: no revela nada

    @app.api_route("/{name:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def page(name: str) -> Response:
        entry = files.get("/" + name)
        if entry is None:
            return Response(status_code=404)
        body, kind = entry
        return Response(body, media_type=kind)

    return app


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    # Sin registro de accesos: el sitio no guarda rastro de quién lo visita.
    uvicorn.run(create_app(), host="0.0.0.0", port=port, access_log=False, log_level="warning")  # noqa: S104
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

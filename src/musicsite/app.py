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

import html
import mimetypes
import os
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from acordia_render import guides
from acordia_render.songpages import WEB_DIR as LIB_WEB_DIR
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from musicsite import learn
from musicsite.accounts import (
    MAX_BODY_BYTES as MAX_BODY,
)
from musicsite.accounts import (
    NOTICE_VERSION,
    Accounts,
    InvalidPreferences,
    accounts_from_env,
    clean_consent,
    clean_preferences,
    clean_result,
    parse_body,
)

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


# La página de entrada (S101, C40) es la única que carga el SDK de Firebase desde el CDN de Google y
# habla con Identity Toolkit: la política se amplía solo para ella. El resto conserva la suya.
LOGIN_PAGE = "/entrar.html"
_SCRIPTS = "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
_LOGIN_SCRIPTS = _SCRIPTS + " https://www.gstatic.com https://apis.google.com"
_LOGIN_EXTRA = (
    "; connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com"
    "; frame-src 'self' https://apis.google.com"
)
LOGIN_CSP = HEADERS["Content-Security-Policy"].replace(_SCRIPTS, _LOGIN_SCRIPTS) + _LOGIN_EXTRA


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
    accounts: Accounts | None = None,
    firebase_api_key: str = "",
) -> FastAPI:
    from musicsite import profes
    from musicsite.catalog import Catalog  # aquí y no arriba: profes importa este módulo

    guides.use(profes)  # las guías de ejemplo son del sitio; la librería las pide a este módulo
    # Los archivos de la página de canción (style.css, acordia.js, guitarra.js, la tipografía y las
    # muestras) vienen de la librería; los del sitio (portada, guías, artistas…) tienen prioridad.
    # «Aprender» (S65): páginas y estilos armados una vez desde `aprender/`; los del sitio mandan.
    files = {**load_files(LIB_WEB_DIR), **learn.build_pages(), **load_files(root)}
    if (
        LOGIN_PAGE in files
    ):  # la llave del navegador es pública, pero se inyecta para no fijarla en el repo (D56)
        body, kind = files[LOGIN_PAGE]
        files[LOGIN_PAGE] = (
            body.decode()
            .replace("__API_KEY__", html.escape(firebase_api_key, quote=True))
            .encode(),
            kind,
        )
    index_html = files["/index.html"][0].decode() if "/index.html" in files else ""
    artists_html = files["/artistas.html"][0].decode() if "/artistas.html" in files else ""
    guides_html = files["/guias.html"][0].decode() if "/guias.html" in files else ""
    catalog = Catalog(
        index_html,
        songs,
        editorial,
        refresh_seconds,
        artists_html=artists_html,
        guides_html=guides_html,
    )
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)

    @app.middleware("http")
    async def secure_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        for name, value in HEADERS.items():
            if name == "Cache-Control" and name in response.headers:
                continue  # las fotos con hash en el nombre fijan su propia caché larga
            if name == "Content-Security-Policy" and request.url.path == LOGIN_PAGE:
                value = LOGIN_CSP
            response.headers[name] = value
        return response

    @app.exception_handler(HTTPException)
    async def empty_error(_: Request, exc: HTTPException) -> Response:
        return Response(status_code=exc.status_code)  # sin cuerpo: no revela nada

    if accounts is not None:
        _register_me(app, accounts)

    @app.api_route("/{name:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def page(name: str) -> Response:
        path = "/" + name
        state = catalog.current()
        if path in ("/", "/index.html") and state.index is not None:
            return Response(state.index, media_type=TYPES[".html"])
        if path == "/artistas.html" and state.artists is not None:
            return Response(state.artists, media_type=TYPES[".html"])
        if path == "/guias.html" and state.guides is not None:
            return Response(state.guides, media_type=TYPES[".html"])
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


# Lo de una persona nunca va al caché compartido de Hosting (C20): `private, no-store` y `Vary`.
PRIVATE = {"Cache-Control": "private, no-store", "Vary": "Authorization"}


def _register_me(app: FastAPI, accounts: Accounts) -> None:
    """`/api/me/preferences` (S99). Sin sesión del grupo público, 404 sin cuerpo como el resto."""

    def caller(request: Request) -> str:
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        uid = accounts.verifier.verify(token) if scheme.lower() == "bearer" and token else None
        if uid is None:
            raise HTTPException(404)
        if not accounts.limiter.allow(uid):
            raise HTTPException(429)
        return uid

    def consenting(request: Request) -> str:
        """Nada de una persona se lee ni se guarda sin aceptar el aviso vigente (C39)."""
        uid = caller(request)
        if accounts.store.get_consent(uid) != NOTICE_VERSION:
            raise HTTPException(403)
        return uid

    def consent_state(uid: str) -> JSONResponse:
        accepted = accounts.store.get_consent(uid)
        return JSONResponse(
            {
                "current": NOTICE_VERSION,
                "accepted": accepted if accepted == NOTICE_VERSION else None,
            },
            headers=PRIVATE,
        )

    @app.get("/api/me/consent", include_in_schema=False)
    def read_consent(request: Request) -> Response:
        return consent_state(caller(request))

    @app.put("/api/me/consent", include_in_schema=False)
    async def write_consent(request: Request) -> Response:
        uid = caller(request)
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_BODY:
            raise HTTPException(413)
        try:
            version = clean_consent(parse_body(await request.body()))
        except InvalidPreferences as error:
            raise HTTPException(422) from error
        accounts.store.put_consent(uid, version)
        return consent_state(uid)

    @app.get("/api/me/progress", include_in_schema=False)
    def read_progress(request: Request) -> Response:
        uid = consenting(request)
        return JSONResponse({"progress": accounts.store.get_progress(uid)}, headers=PRIVATE)

    @app.put("/api/me/progress", include_in_schema=False)
    async def write_progress(request: Request) -> Response:
        """El resultado de una lección de Aprende (S103): se guarda el mejor de cada una."""
        uid = consenting(request)
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_BODY:
            raise HTTPException(413)
        try:
            path, lesson, points, stars = clean_result(parse_body(await request.body()))
        except InvalidPreferences as error:
            raise HTTPException(422) from error
        best = accounts.store.put_result(uid, path, lesson, points, stars)
        if best is None:
            raise HTTPException(422)
        return JSONResponse({"path": path, "lesson": lesson, **best}, headers=PRIVATE)

    @app.get("/api/me/export", include_in_schema=False)
    def export_data(request: Request) -> Response:
        """Derecho de acceso y portabilidad (S102): todo lo que hay de la persona, para descargar.

        Sin exigir consentimiento: quien nunca aceptó también puede ver (y llevarse) lo que haya.
        """
        uid = caller(request)
        _, _, token = request.headers.get("authorization", "").partition(" ")
        stored = accounts.store.export(uid)
        body = {
            "generatedAt": datetime.now(UTC).isoformat(timespec="seconds"),
            "stored": stored,
            "firebaseAuthentication": accounts.verifier.identity(token) or {},
            "note": (
                "stored es lo que Acordia guarda en su base de datos. "
                "firebaseAuthentication son los datos de tu cuenta de Google o Facebook "
                "que guarda Firebase Authentication; Acordia no los copia."
            ),
        }
        return JSONResponse(
            body,
            headers={
                **PRIVATE,
                "Content-Disposition": 'attachment; filename="acordia-mis-datos.json"',
            },
        )

    @app.delete("/api/me", include_in_schema=False)
    def delete_data(request: Request) -> Response:
        """Derecho de supresión (S102): borra el documento de la persona. Sin exigir consentimiento.

        La cuenta de Firebase Authentication la elimina el navegador después (sin permisos nuevos);
        si no llega a hacerlo, queda sin consentimiento y la limpia `auth-cleanup-unconsented.sh`.
        """
        accounts.store.delete(caller(request))
        return Response(status_code=204, headers=PRIVATE)

    @app.get("/api/me/preferences", include_in_schema=False)
    def read_preferences(request: Request) -> Response:
        uid = consenting(request)
        return JSONResponse({"preferences": accounts.store.get(uid)}, headers=PRIVATE)

    @app.put("/api/me/preferences", include_in_schema=False)
    async def write_preferences(request: Request) -> Response:
        uid = consenting(request)
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_BODY:
            raise HTTPException(413)
        try:
            body = parse_body(await request.body())
            payload = body.get("preferences") if isinstance(body, dict) else None
            preferences = clean_preferences(payload)
        except InvalidPreferences as error:
            raise HTTPException(422) from error
        accounts.store.put(uid, preferences)
        return JSONResponse({"preferences": preferences}, headers=PRIVATE)


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    editorial = os.environ.get("EDITORIAL_DIR", "")
    refresh = float(os.environ.get("EDITORIAL_REFRESH_SECONDS", "60"))
    app = create_app(
        editorial=Path(editorial) if editorial else None,
        refresh_seconds=refresh,
        accounts=accounts_from_env(dict(os.environ)),
        firebase_api_key=os.environ.get("FIREBASE_API_KEY", ""),
    )
    # Sin registro de accesos: el sitio no guarda rastro de quién lo visita.
    uvicorn.run(app, host="0.0.0.0", port=port, access_log=False, log_level="warning")  # noqa: S104
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Catálogo de temas publicados: de dónde salen las páginas de canción y la Biblioteca (S9).

Con `EDITORIAL_DIR` (el bucket editorial montado de solo lectura), el sitio muestra la publicación
vigente que dejó el admin:

    current.txt                      apunta a `releases/<versión>`
    releases/<versión>/<tema>.toml   los temas de esa publicación (inmutable)
    releases/<versión>/artists.json  los artistas de la sección Artistas (S24; opcional)

Reglas:
- Al arrancar se usa la publicación vigente; si no hay o no sirve, `songs/` de git (el respaldo).
- Cada `refresh_seconds` se vuelve a leer `current.txt`; si apunta a otra publicación, se carga
  entera y se cambia de una vez. Una publicación que no sirve (un tema no publicable, un nombre
  raro, un error de lectura) **nunca reemplaza** a la que ya se estaba mostrando.
- El que refresca es un solo hilo; los demás siguen sirviendo lo actual, sin esperar.
- Una publicación reemplaza a `songs/`, no se mezclan: lo publicado es la fuente de verdad.
"""

import logging
import re
import threading
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from acordia_render.dificultad import classify_song
from acordia_render.songpages import apply_library, published_library_html, render_published

from musicsite.artists import build_page_and_photos

RELEASE = re.compile(r"releases/[0-9]{8}-[0-9]{6}-[0-9a-f]{4}")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
log = logging.getLogger("musicsite.catalog")


def level_drift(directory: Path) -> list[str]:
    """Temas de una publicación cuyo `nivel` escrito no es el que da la regla (C56, RD54).

    El nivel sale de la versión Original y lo escribe el admin al publicar; si alguien lo edita a
    mano o la regla cambia sin republicar, difiere. Solo se avisa (la publicación igual sirve)."""
    drifted = []
    for path in sorted(directory.glob("*.toml")):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except OSError, tomllib.TOMLDecodeError:
            continue  # la lectura o el formato malo los trata `_load`
        if data.get("nivel", "") != classify_song(data).nivel:
            drifted.append(path.stem)
    return drifted


@dataclass(frozen=True)
class State:
    source: str  # "editorial" o "git"
    release: str  # `releases/<versión>`; vacío si viene de git
    pages: dict[str, bytes]  # "/cancion-<tema>.html" -> HTML
    index: bytes | None  # index.html con la Biblioteca de lo publicado; None = el de web/
    artists: bytes | None = (
        None  # artistas.html con artists.json (o el respaldo) y los conteos (S24)
    )
    photos: dict[str, bytes] = field(default_factory=dict)  # "fotos/<archivo>.jpg" -> JPEG (S33)
    guides: bytes | None = None  # guias.html con las tarjetas de los guías según lo publicado (S76)


class Catalog:
    def __init__(
        self,
        index_html: str,
        git_songs: Path | None,
        editorial: Path | None = None,
        refresh_seconds: float = 60,
        clock: Callable[[], float] | None = None,
        artists_html: str = "",
        guides_html: str = "",
    ) -> None:
        from musicsite import profes  # aquí y no arriba: profes importa `musicsite.app`

        self._index_html = index_html
        self._artists_html = artists_html
        self._guides_html = guides_html
        self._songs: dict[str, tuple[str, str]] = {}  # los temas publicados que conocen las guías
        self._editorial = editorial
        self._ttl = refresh_seconds
        self._clock = clock or (lambda: time.monotonic())  # noqa: PLW0108 - se resuelve al llamar
        self._lock = threading.Lock()
        self._rejected = ""  # publicación descartada por datos; no se reintenta hasta que cambie
        pages = {}
        if git_songs is not None:  # un dato malo en git rompe el arranque, como siempre
            self._songs = profes.songs_in(git_songs)
            profes.use_catalog(
                self._songs
            )  # antes de armar las páginas: ellas piden quién enseña cada tema
            pages = {
                f"/cancion-{s}.html": h.encode() for s, h in render_published(git_songs).items()
            }
        artists, photos = self._artists_page(None, git_songs)
        self._state = State("git", "", pages, None, artists, photos, self._guides_page())
        self._next_check = self._clock() + self._ttl
        if editorial is not None:
            self._try_load(self._pointer())

    def current(self) -> State:
        if self._editorial is not None and self._clock() >= self._next_check:
            self._refresh()
        return self._state

    # --- internos ---
    def _pointer(self) -> str | None:
        assert self._editorial is not None
        try:
            release = (self._editorial / "current.txt").read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return release if RELEASE.fullmatch(release) else None  # nunca sale de `releases/`

    def _refresh(self) -> None:
        if not self._lock.acquire(blocking=False):
            return  # otro hilo ya está refrescando: se sigue con lo actual
        try:
            self._next_check = self._clock() + self._ttl
            self._try_load(self._pointer())
        finally:
            self._lock.release()

    def _try_load(self, release: str | None) -> None:
        if release is None or release == self._state.release or release == self._rejected:
            return
        try:
            self._state = self._load(release)
            self._rejected = ""
            log.warning("catálogo: %s (%d temas)", release, len(self._state.pages))
        except OSError as error:  # lectura que falló: se reintenta en el próximo ciclo
            log.warning("catálogo: no se pudo leer %s: %s", release, error)
        except Exception as error:  # noqa: BLE001 - datos que no sirven: se descarta esa publicación
            self._rejected = release
            log.warning("catálogo: se descarta %s: %s", release, error)

    def _load(self, release: str) -> State:
        assert self._editorial is not None
        directory = self._editorial / release
        names = [p.stem for p in directory.glob("*.toml")]
        if not names:
            raise ValueError("la publicación no tiene temas")
        bad = [n for n in names if not SLUG.fullmatch(n)]
        if bad:
            raise ValueError(f"nombres de tema no válidos: {bad}")
        from musicsite import profes

        songs = profes.songs_in(directory)
        profes.use_catalog(songs)  # antes de armar las páginas: ellas piden quién enseña cada tema
        try:
            pages = {
                f"/cancion-{s}.html": h.encode() for s, h in render_published(directory).items()
            }
            index = apply_library(self._index_html, published_library_html(directory)).encode()
            artists, photos = self._artists_page(directory, directory)
            guides = self._guides_page()
        except BaseException:
            profes.use_catalog(
                self._songs
            )  # una publicación descartada no cambia lo que se muestra
            raise
        self._songs = songs
        if drift := level_drift(directory):  # solo los nombres de los temas, nada del contenido
            log.warning("catálogo: nivel publicado distinto del calculado en %s", ", ".join(drift))
        return State("editorial", release, pages, index, artists, photos, guides)

    def _guides_page(self) -> bytes | None:
        """guias.html con las tarjetas de los guías para los temas publicados (S76).

        Nunca impide cargar una publicación: si algo falla, esa página sigue siendo la de web/."""
        if not self._guides_html:
            return None
        from musicsite import profes

        try:
            profiles = profes.load_profiles()
            for warning in profes.catalog_warnings(profiles):
                log.warning("catálogo: guías: %s", warning)
            return profes.render_guides(self._guides_html, profiles).encode()
        except Exception as error:  # noqa: BLE001
            log.warning("catálogo: no se pudo armar guias.html: %s", error)
            return None

    def _artists_page(
        self, directory: Path | None, songs: Path | None
    ) -> tuple[bytes | None, dict[str, bytes]]:
        """artistas.html con `artists.json` de `directory` (o el respaldo), los temas de `songs`
        y las fotos que cita (ruta -> JPEG).

        Nunca impide cargar una publicación: si algo falla, esa página sigue siendo la de web/."""
        if not self._artists_html:
            return None, {}
        try:
            html, photos = build_page_and_photos(self._artists_html, directory, songs)
            return html.encode(), photos
        except Exception as error:  # noqa: BLE001
            log.warning("catálogo: no se pudo armar artistas.html: %s", error)
            return None, {}

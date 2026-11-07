"""Pruebas de navegador: levantan el sitio real en un puerto libre y lo abren con Playwright.

Con `E2E_BASE_URL` (scripts/e2e-produccion.sh, S48) corren contra ese sitio en vez de uno local.
Las que arman temas de prueba propios (fixtures `*_url` salvo `base_url`) se saltan: solo valen en
local."""

import os
import socket
import threading
import time

import pytest
import uvicorn

from musicsite.app import SONGS_DIR, create_app


def pytest_collection_modifyitems(items):
    for item in items:
        if "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


def serve(app):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("el servidor no arrancó")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


REMOTE = os.environ.get("E2E_BASE_URL", "").rstrip("/")


def local_only() -> None:
    """Una fixture que arma su propio catálogo no puede ir contra un sitio desplegado."""
    if REMOTE:
        pytest.skip("solo en local: arma temas de prueba propios")


@pytest.fixture(scope="session")
def base_url() -> str:
    if REMOTE:
        yield REMOTE
        return
    yield from serve(create_app())


@pytest.fixture(scope="session")
def one_song_url(tmp_path_factory) -> str:
    """Sitio con un solo tema publicado: los demás artistas quedan en «Próximamente»."""
    local_only()
    folder = tmp_path_factory.mktemp("songs-one")
    (folder / "camara-lenta.toml").write_text(
        (SONGS_DIR / "camara-lenta.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    yield from serve(create_app(songs=folder))

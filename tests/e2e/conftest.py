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
def tips_url(tmp_path_factory) -> str:
    """Sitio con «Cámara lenta» más dos tips (al inicio y entre secciones): los temas reales no
    llevan tips todavía, así que se prueban sobre una copia en una carpeta temporal."""
    local_only()
    folder = tmp_path_factory.mktemp("songs-with-tips")
    text = (SONGS_DIR / "camara-lenta.toml").read_text(encoding="utf-8")
    text = text.replace(
        "Intro x2: E F# B F#\n",
        "> ¿Qué hace el bajo aquí? | La guitarra sostiene E y el bajo baja a B.\n"
        "Intro x2: E F# B F#\n",
        1,
    ).replace(
        "Coro x2: E F# B F#\n",
        "> Antes del coro | Respira y entra con fuerza.\nCoro x2: E F# B F#\n",
        1,
    )
    (folder / "camara-lenta.toml").write_text(text, encoding="utf-8")
    yield from serve(create_app(songs=folder))


@pytest.fixture(scope="session")
def shapes_url(tmp_path_factory) -> str:
    """«Cámara lenta» con una forma por defecto del tema (`[formas]`, S27) para E y una forma
    propia del Intermedio (S8) para Emaj7: la propia manda sobre la del tema."""
    local_only()
    folder = tmp_path_factory.mktemp("songs-with-shapes")
    text = (SONGS_DIR / "camara-lenta.toml").read_text(encoding="utf-8")
    text += '\n[formas]\n"E" = "x 7 9 9 9 7"\n\n[intermedio.formas]\n"Emaj7" = "x 7 9 8 9 7"\n'
    (folder / "camara-lenta.toml").write_text(text, encoding="utf-8")
    yield from serve(create_app(songs=folder))


@pytest.fixture(scope="session")
def parens_url(tmp_path_factory) -> str:
    """«Cámara lenta» con acordes escritos con paréntesis y el 6/9 con barra en Intermedio (S35)."""
    local_only()
    folder = tmp_path_factory.mktemp("songs-with-parens")
    head, tail = (SONGS_DIR / "camara-lenta.toml").read_text(encoding="utf-8").split("[intermedio]")
    tail = tail.replace(
        "Intro x2: E F# Bmaj7 F#\n",
        "Intro x2: E F# D6/9 Dm(add#11) G7(b9/#11/13)\n",
        1,
    )
    # S38: sin forma estándar en chords-db, el tema debe traer su forma propia por defecto.
    shapes = '\n[formas]\n"D6/9" = "x 5 2 2 0 2"\n"Dm(add#11)" = "x 5 3 2 3 4"\n\n'
    (folder / "camara-lenta.toml").write_text(
        head + shapes + "[intermedio]" + tail, encoding="utf-8"
    )
    yield from serve(create_app(songs=folder))


@pytest.fixture(scope="session")
def advanced_url(tmp_path_factory) -> str:
    """«Cámara lenta» con Avanzado sintético (S31): hereda Intermedio y suma extras por sección."""
    local_only()
    folder = tmp_path_factory.mktemp("songs-with-advanced")
    text = (SONGS_DIR / "camara-lenta.toml").read_text(encoding="utf-8")
    assert "\n[avanzado" not in text
    text += (
        "\n[avanzado.secciones.Intro]\ntab = '''\ne|--0--|\n'''\n"
        'arreglo = "Rasgueo suave con `Emaj7`"\n'
        'tips = ["Sonido | Deja sonar el acorde hasta el siguiente compás."]\n'
    )
    (folder / "camara-lenta.toml").write_text(text, encoding="utf-8")
    yield from serve(create_app(songs=folder))


@pytest.fixture(scope="session")
def rests_url(tmp_path_factory) -> str:
    """Sitio con «Cámara lenta» más silencios (compás entero y dentro de un compás partido, S22)."""
    local_only()
    folder = tmp_path_factory.mktemp("songs-with-rests")
    text = (SONGS_DIR / "camara-lenta.toml").read_text(encoding="utf-8")
    assert "Intro x2: E F# B F#\n" in text
    text = text.replace("Intro x2: E F# B F#\n", "Intro x2: . F# B-. .-%-F#\n", 1)
    (folder / "camara-lenta.toml").write_text(text, encoding="utf-8")
    yield from serve(create_app(songs=folder))


@pytest.fixture(scope="session")
def ties_url(tmp_path_factory) -> str:
    """Sitio con «Cámara lenta» más ligados (compás entero y parte de un compás partido, S47)."""
    local_only()
    folder = tmp_path_factory.mktemp("songs-with-ties")
    text = (SONGS_DIR / "camara-lenta.toml").read_text(encoding="utf-8")
    assert "Intro x2: E F# B F#\n" in text
    text = text.replace("Intro x2: E F# B F#\n", "Intro x2: E _ B-F# _-F#\n", 1)
    (folder / "camara-lenta.toml").write_text(text, encoding="utf-8")
    yield from serve(create_app(songs=folder))


@pytest.fixture(scope="session")
def one_song_url(tmp_path_factory) -> str:
    """Sitio con un solo tema publicado: los demás artistas quedan en «Próximamente»."""
    local_only()
    folder = tmp_path_factory.mktemp("songs-one")
    (folder / "camara-lenta.toml").write_text(
        (SONGS_DIR / "camara-lenta.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    yield from serve(create_app(songs=folder))

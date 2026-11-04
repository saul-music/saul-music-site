"""El sitio muestra la publicación vigente del bucket editorial y cae a `songs/` si no la hay (S9).

Los temas de prueba salen de `songs/` (ya públicos) o son sintéticos; nada del bucket real.
"""

import json
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from musicsite.acordes import REPERTOIRE
from musicsite.app import HEADERS, SONGS_DIR, WEB_DIR, create_app
from musicsite.songpages import apply_count, apply_library, published_library_html, update_library

FORBIDDEN = ["musicres", "run.app", "dashboard", "saulapp-music", "youtube", "bigquery", "secret"]
VERSION = iter(range(1, 10_000))


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def song_text(name: str, **changes) -> str:
    """TOML de un tema público de `songs/` con cambios; si no existe, parte de otra-era."""
    source = name if (SONGS_DIR / f"{name}.toml").exists() else "otra-era"
    text = (SONGS_DIR / f"{source}.toml").read_text(encoding="utf-8")
    data = tomllib.loads(text)
    data.update(changes)
    return render_toml(data)


def render_toml(data: dict) -> str:
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            continue
        lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"\n[{key}]")
            lines += [f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in value.items()]
    return "\n".join(lines) + "\n"


def make_release(root: Path, files: dict[str, str], point: bool = True) -> str:
    release = f"releases/20261102-{next(VERSION):06d}-abcd"
    folder = root / release
    folder.mkdir(parents=True)
    for slug, text in files.items():
        (folder / f"{slug}.toml").write_text(text, encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps({"release": release}), encoding="utf-8")
    if point:
        (root / "current.txt").write_text(release + "\n", encoding="utf-8")
    return release


@pytest.fixture
def editorial(tmp_path: Path) -> Path:
    return tmp_path / "editorial"


def test_publication_replaces_songs_in_git(editorial):
    editorial.mkdir()
    make_release(
        editorial, {"otra-era": song_text("otra-era"), "camara-lenta": song_text("camara-lenta")}
    )
    client = TestClient(create_app(editorial=editorial))
    assert client.get("/cancion-otra-era.html").status_code == 200
    assert client.get("/cancion-camara-lenta.html").status_code == 200
    assert client.get("/cancion-dejate-caer.html").status_code == 404  # está en git, no publicado


def test_library_lists_published_and_marks_the_rest_as_coming_soon(editorial):
    editorial.mkdir()
    make_release(editorial, {"otra-era": song_text("otra-era")})
    index = TestClient(create_app(editorial=editorial)).get("/").text
    assert 'href="cancion-otra-era.html"' in index
    assert 'href="cancion-dejate-caer.html"' not in index
    assert index.count("Próximamente") >= len(REPERTOIRE) - 1  # el resto del repertorio
    assert "Dos veces" not in index and "Esquemas juveniles" in index  # título y artista visibles
    # lo que está fuera de la Biblioteca no cambia
    assert (
        "<strong>1 canción disponible</strong>" in index
    )  # el conteo de la portada (los próximamente no cuentan)
    static = apply_count((WEB_DIR / "index.html").read_text(encoding="utf-8"), 1)
    assert (
        index.split("<!-- biblioteca:inicio -->")[0]
        == static.split("<!-- biblioteca:inicio -->")[0]
    )
    assert index.split("<!-- biblioteca:fin -->")[1] == static.split("<!-- biblioteca:fin -->")[1]


def test_coming_soon_cards_do_not_leak_draft_data(editorial):
    editorial.mkdir()
    make_release(editorial, {"otra-era": song_text("otra-era")})
    index = TestClient(create_app(editorial=editorial)).get("/").text
    at = index.index("Cantar y amar")
    start = index.rindex('<div class="col">', 0, at)
    end = index.find('<div class="col">', at)
    card = index[start : end if end != -1 else len(index)]
    assert "Próximamente" in card and "ac-chip-chord" not in card and "bpm" not in card


def test_changed_content_and_a_new_song_show_up(editorial):
    editorial.mkdir()
    new = song_text("tema-nuevo", slug="tema-nuevo", titulo="Tema nuevo", artista="Artista Nuevo")
    make_release(editorial, {"otra-era": song_text("otra-era", bpm=99), "tema-nuevo": new})
    client = TestClient(create_app(editorial=editorial))
    assert "99 bpm" in client.get("/cancion-otra-era.html").text
    assert client.get("/cancion-tema-nuevo.html").status_code == 200
    index = client.get("/").text
    assert 'href="cancion-tema-nuevo.html"' in index and "Artista Nuevo" in index
    # los nuevos se mezclan por artista (S14): «Artista Nuevo» va antes que «Los Bunkers»
    assert index.index("Artista Nuevo") < index.index("Los Bunkers")


def test_new_publication_is_picked_up_after_the_refresh_interval(editorial, monkeypatch):
    import musicsite.catalog as catalog

    clock = Clock()
    monkeypatch.setattr(catalog.time, "monotonic", clock)
    editorial.mkdir()
    make_release(editorial, {"otra-era": song_text("otra-era")})
    client = TestClient(create_app(editorial=editorial, refresh_seconds=60))
    assert client.get("/cancion-camara-lenta.html").status_code == 404
    make_release(
        editorial, {"otra-era": song_text("otra-era"), "camara-lenta": song_text("camara-lenta")}
    )
    clock.now = 30  # todavía no toca releer
    assert client.get("/cancion-camara-lenta.html").status_code == 404
    clock.now = 61
    assert client.get("/cancion-camara-lenta.html").status_code == 200


@pytest.mark.parametrize(
    "bad",
    [
        {"otra-era": 'slug = "otra-era"\n'},  # un tema no publicable
        {"Otra Era": "x = 1\n"},  # nombre de archivo no válido
        {},  # publicación sin temas
    ],
)
def test_a_bad_publication_never_replaces_the_good_one(editorial, monkeypatch, bad):
    import musicsite.catalog as catalog

    clock = Clock()
    monkeypatch.setattr(catalog.time, "monotonic", clock)
    editorial.mkdir()
    make_release(editorial, {"otra-era": song_text("otra-era", bpm=99)})
    client = TestClient(create_app(editorial=editorial, refresh_seconds=60))
    make_release(editorial, bad)
    clock.now = 61
    assert "99 bpm" in client.get("/cancion-otra-era.html").text  # sigue lo anterior
    clock.now = 200
    assert client.get("/cancion-otra-era.html").status_code == 200  # y sin reintentos que rompan


def test_without_a_valid_publication_it_falls_back_to_git(editorial):
    static = (WEB_DIR / "index.html").read_bytes()
    for prepare in ("vacío", "puntero roto", "puntero fuera de releases"):
        editorial.mkdir(exist_ok=True)
        if prepare == "puntero roto":
            (editorial / "current.txt").write_text("releases/20261102-000001-abcd\n")  # no existe
        if prepare == "puntero fuera de releases":
            (editorial / "current.txt").write_text("../../etc\n")
        client = TestClient(create_app(editorial=editorial))
        assert client.get("/cancion-dejate-caer.html").status_code == 200  # el respaldo
        assert client.get("/").content == static  # la Biblioteca de siempre


def test_without_editorial_nothing_changes():
    client = TestClient(create_app())
    assert client.get("/").content == (WEB_DIR / "index.html").read_bytes()
    assert client.get("/cancion-dejate-caer.html").status_code == 200


def test_published_pages_keep_the_public_rules(editorial):
    editorial.mkdir()
    make_release(editorial, {"otra-era": song_text("otra-era")})
    client = TestClient(create_app(editorial=editorial))
    for path in ("/", "/cancion-otra-era.html"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-security-policy"] == HEADERS["Content-Security-Policy"]
        for word in FORBIDDEN:
            assert word not in response.text.lower(), f"{path} menciona {word!r}"
    assert client.get("/manifest.json").status_code == 404  # los archivos del bucket no se sirven
    assert client.get("/current.txt").status_code == 404


def test_apply_library_matches_the_generator_the_cli_uses(tmp_path):
    index = tmp_path / "index.html"
    index.write_text((WEB_DIR / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    update_library(SONGS_DIR, index)
    expected = apply_library(
        (WEB_DIR / "index.html").read_text(encoding="utf-8"), published_library_html(SONGS_DIR)
    )
    assert index.read_text(encoding="utf-8") == expected

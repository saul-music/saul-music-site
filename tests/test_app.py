"""Tests de la app con el sitio real y con un directorio sintético."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from musicsite.acordes import validate_file
from musicsite.app import HEADERS, SONGS_DIR, WEB_DIR, create_app, load_files


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        ("/", "text/html"),
        ("/index.html", "text/html"),
        ("/cancion.html", "text/html"),
        ("/guias.html", "text/html"),
        ("/style.css", "text/css"),
        ("/acordia.js", "text/javascript"),
    ],
)
def test_site_files_are_served(client, path, kind):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(kind)
    assert response.content


def test_head_has_no_body(client):
    response = client.head("/")
    assert response.status_code == 200
    assert response.content == b""


@pytest.mark.parametrize(
    "path",
    ["/docs", "/redoc", "/openapi.json", "/nada.html", "/web/index.html", "/dashboard/latest"],
)
def test_other_routes_are_empty_404(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.content == b""


@pytest.mark.parametrize(
    "path",
    ["/../pyproject.toml", "/..%2fapp.py", "/%2e%2e/app.py", "/web/../app.py", "//etc/passwd"],
)
def test_path_traversal_is_404(client, path):
    assert client.get(path).status_code == 404


def test_post_is_rejected(client):
    assert client.post("/").status_code == 405


def test_security_headers_on_every_response(client):
    for path in ("/", "/nada"):
        response = client.get(path)
        for name, value in HEADERS.items():
            assert response.headers[name] == value


def test_load_files_skips_hidden_unknown_and_subdirectories(tmp_path: Path):
    (tmp_path / "index.html").write_bytes(b"<p>ok</p>")
    (tmp_path / ".secreto.html").write_bytes(b"x")
    (tmp_path / "datos.xyz123").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.html").write_bytes(b"x")
    assert set(load_files(tmp_path)) == {"/", "/index.html"}


def test_web_dir_has_only_fixed_site_files():
    # Lo que está en web/ se publica entero: un archivo nuevo ahí debe ser contenido del sitio.
    # Las páginas de canción ya no son archivos: salen del template y de songs/.
    flats = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

    def sample(prefix: str, midi: int) -> str:  # una muestra por semitono, nombre = nota + octava
        return f"{prefix}{flats[midi % 12]}{midi // 12 - 1}.mp3"

    fixed = {
        "index.html",
        "cancion.html",
        "guias.html",
        "artistas.html",
        "pedidos.html",
        "pedidos.js",
        "style.css",
        "acordia.js",
        "guitarra.js",
        "PetalumaScript.woff2",
        "PetalumaScript-OFL.txt",
    }
    # Muestras del botón Guitarra (S37): nailon E2 a E6 (40 a 88) y contrabajo E1 a Eb2 (28 a 39).
    fixed |= {sample("guitarra-nylon-", m) for m in range(40, 89)}
    fixed |= {sample("bajo-", m) for m in range(28, 40)}
    assert {p.name for p in WEB_DIR.iterdir()} == fixed


def test_song_pages_come_from_published_songs(client):
    slugs = {p.stem for p in SONGS_DIR.glob("*.toml")}
    assert len(slugs) == 15  # el respaldo es lo último publicado, no solo el repertorio inicial
    for slug in slugs:
        response = client.get(f"/cancion-{slug}.html")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "data-ac-metronome" in response.text


UNPUBLISHED = ["cantar-y-amar"]


@pytest.mark.parametrize("slug", UNPUBLISHED)
def test_unpublished_songs_are_404(client, slug):
    assert client.get(f"/cancion-{slug}.html").status_code == 404


def test_every_published_song_is_valid():
    for path in SONGS_DIR.glob("*.toml"):
        report = validate_file(path)
        assert not report.errors
        assert report.status == "publicable"


def test_unpublishable_song_stops_startup(tmp_path: Path):
    (tmp_path / "otra-era.toml").write_text('slug = "otra-era"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        create_app(songs=tmp_path)


def test_guitar_samples_get_a_longer_cache_than_pages(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "guitarra-nylon-G2.mp3").write_bytes(b"ID3")
    test_client = TestClient(create_app(root=tmp_path, songs=tmp_path))
    sample = test_client.get("/guitarra-nylon-G2.mp3")
    assert sample.headers["content-type"] == "audio/mpeg"
    assert sample.headers["cache-control"] == "public, max-age=86400"
    assert test_client.get("/index.html").headers["cache-control"] == HEADERS["Cache-Control"]

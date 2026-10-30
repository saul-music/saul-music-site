"""Tests de la app con el sitio real y con un directorio sintético."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from musicsite.app import HEADERS, WEB_DIR, create_app, load_files


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


def test_every_file_in_web_dir_is_public_content():
    # Lo que está en web/ se publica entero: un archivo nuevo ahí debe ser contenido del sitio.
    names = {p.name for p in WEB_DIR.iterdir()}
    assert names == {
        "index.html",
        "cancion.html",
        "guias.html",
        "artistas.html",
        "style.css",
        "acordia.js",
    }

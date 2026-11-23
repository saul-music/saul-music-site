"""Tests de la app con el sitio real y con un directorio sintético."""

from pathlib import Path

import pytest
from acordia_render.acordes import validate_file
from fastapi.testclient import TestClient

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
        ("/aprender.html", "text/html"),
        ("/aprender.css", "text/css"),
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
    # Las páginas de canción salen de la librería y de songs/; sus estilos, scripts, tipografía y
    # muestras también son de la librería (R1) y no se copian aquí.
    fixed = {
        "index.html",
        "cancion.html",
        "guias.html",
        "ser-guia.html",
        "artistas.html",
        "pedidos.html",
        "pedidos.js",
        "privacidad.html",
        "entrar.html",
        "entrar.js",
    }
    assert {p.name for p in WEB_DIR.iterdir()} == fixed


def test_the_library_files_are_served_by_the_site(client):
    """R1: estilos, scripts, tipografía y muestras vienen de la librería."""
    for name, kind in (
        ("style.css", "text/css"),
        ("acordia.js", "text/javascript"),
        ("guitarra.js", "text/javascript"),
        ("PetalumaScript.woff2", "font/woff2"),
        ("guitarra-nylon-E2.mp3", "audio/mpeg"),
        ("bajo-E1.mp3", "audio/mpeg"),
    ):
        response = client.get(f"/{name}")
        assert response.status_code == 200, name
        assert response.headers["content-type"].startswith(kind), name
    assert client.get("/guitarra-nylon-E2.mp3").headers["cache-control"] == "public, max-age=86400"
    assert client.get("/nope.mp3").status_code == 404


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


def test_landing_leads_with_chords(client):
    html = client.get("/").text
    assert "Donde se respiran acordes" in html
    assert "Donde se respira música" not in html
    assert 'id="problema"' in html  # sección «Ya lo viviste»
    assert 'id="niveles"' in html
    assert html.count('class="card h-100 ac-dolor-card"') == 3
    # La animación respeta a quien pide menos movimiento.
    assert "prefers-reduced-motion" in html


def test_home_shows_library_before_the_advantages(client):
    """La Biblioteca va primero, «Cómo funciona» justo debajo y las ventajas de Acordia después."""
    html = client.get("/").text
    pos = {i: html.index(f'id="{i}"') for i in ("biblioteca", "problema", "niveles", "como")}
    assert pos["biblioteca"] < pos["como"] < pos["problema"] < pos["niveles"]


def test_home_has_a_divider_between_how_it_works_and_why_acordia(client):
    html = client.get("/").text
    divider = html.index('class="ac-divider"')
    assert html.index('id="como"') < divider < html.index("¿Por qué Acordia?")


def test_home_explains_the_three_difficulty_levels_with_example_chords(client):
    html = client.get("/").text
    block = html[html.index('id="dificultad"') : html.index('id="barrios"')]
    for level in ("inicial", "medio", "avanzado"):
        assert f'data-n="{level}"' in block
    for chord in ("Am", "Am7", "C/E", "D9sus4", "A13", "E7b9", "G7#9"):
        assert f'ac-chip-chord">{chord}<' in block
    assert html.index('id="niveles"') < html.index('id="dificultad"') < html.index('id="barrios"')


def test_home_explains_how_it_works_in_five_steps(client):
    """«Cómo funciona»: cinco pasos y un cierre; el plan de estudios todavía es «Pronto»."""
    html = client.get("/").text
    sec = html[html.index('id="como"') : html.index('class="container ac-porque"')]
    assert sec.count('class="ac-como-step"') == 5
    for n in range(1, 6):
        assert f"Paso {n}" in sec
    assert 'href="guias.html"' in sec and 'href="aprender.html"' in sec
    assert "ac-como-soon" in sec and "Prototipo en investigación" not in html


def test_how_it_works_diagrams_are_real_six_string_shapes(client):
    """Los diagramas de la maqueta son guitarras de 6 cuerdas con la forma real de cada acorde."""
    import re

    html = client.get("/").text
    sec = html[html.index('id="como"') : html.index('class="container ac-porque"')]
    figs = re.findall(r'<svg class="ac-como-fret" data-chord="(\w+)".*?</svg>', sec, re.S)
    assert figs == ["Am", "F", "C", "G"]
    am = re.search(r'<svg class="ac-como-fret" data-chord="Am".*?</svg>', sec, re.S).group(0)
    assert am.count("<circle") == 3  # x02210: tres dedos (la cuerda al aire no lleva punto)
    assert am.count("M") >= 1 and re.search(r"V\d+", am)
    assert len(re.findall(r"M[\d.]+ 18V", am)) == 6  # seis cuerdas
    assert [m for m in re.findall(r'class="num"[^>]*>(\d)<', am)] == ["2", "3", "1"]
    assert len(re.findall(r'<svg class="ac-como-mini"', sec)) == 4


def test_library_never_shows_the_shape_variant_asterisk(client):
    """El `*` de las variantes de forma es de uso interno: ninguna tarjeta lo muestra (RD52)."""
    import re

    html = client.get("/").text
    assert not re.findall(r'ac-chip-chord">[^<]*\*', html)


def test_pages_have_no_plans_or_prices_from_acordia(client):
    """Sin suscripción ni planes (C11): ninguna página ofrece planes ni cobra una conexión."""
    for page in ("/", "/guias.html", "/ser-guia.html", "/artistas.html", "/pedidos.html"):
        html = client.get(page).text
        assert 'id="planes"' not in html and "#planes" not in html, page
        assert "Acordia Plus" not in html and "$3.990" not in html and "$2.990" not in html, page


def test_become_a_guide_page_asks_for_an_email_and_has_no_ai_pitch(client):
    page = client.get("/ser-guia.html")
    assert page.status_code == 200
    assert "mailto:contacto@saulapp.com" in page.text
    assert "Al menos 4 contactos al mes" in page.text
    home = client.get("/").text
    assert 'href="ser-guia.html"' in home
    assert "La IA convierte" not in home

"""Sección Artistas (S24): artists.json del release, respaldo, validación, escape y conteos.

Todo sintético: los artistas de prueba no existen y los temas son los ya públicos de `songs/`.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from musicsite.app import create_app
from musicsite.artists import FALLBACK, parse_artists, safe_url
from test_catalog import Clock, make_release, song_text


def doc(*artists: dict, **top) -> str:
    return json.dumps({"format": 1, "artists": list(artists)} | top)


def artist(**changes) -> dict:
    base = {
        "slug": "banda-demo",
        "name": "Banda Demo",
        "description": "Texto de prueba.",
        "links": [{"label": "Sitio", "url": "https://example.org/demo"}],
    }
    return base | changes


@pytest.fixture
def editorial(tmp_path: Path) -> Path:
    folder = tmp_path / "editorial"
    folder.mkdir()
    return folder


def with_json(editorial: Path, text: str | None, songs=("otra-era",)) -> TestClient:
    release = make_release(editorial, {s: song_text(s) for s in songs})
    if text is not None:
        (editorial / release / "artists.json").write_text(text, encoding="utf-8")
    return TestClient(create_app(editorial=editorial))


def test_without_artists_json_the_static_data_work_in_git_and_editorial_modes(editorial):
    git = TestClient(create_app()).get("/artistas.html").text
    published = with_json(editorial, None).get("/artistas.html").text
    for page in (git, published):
        for item in FALLBACK:
            assert item["name"] in page
    assert "Ver sus temas en la Biblioteca" in git
    assert "<!-- artistas:inicio -->" in git


def test_counts_only_published_songs_and_coming_soon_when_none(editorial):
    page = with_json(editorial, None, songs=("otra-era", "camara-lenta")).get("/artistas.html").text
    mena = page[page.index('id="javiera-mena"') : page.index('id="los-tres"')]
    assert "2 temas disponibles" in mena and "Próximamente" not in mena
    assert 'href="index.html?q=Javiera%20Mena#biblioteca"' in mena
    gepe = page[page.index('id="gepe"') : page.index('id="javiera-mena"')]
    assert "Próximamente" in gepe and "Ver sus temas" not in gepe
    one = with_json(editorial, None).get("/artistas.html").text
    assert "1 tema disponible" in one


def test_valid_artists_json_replaces_the_static_data(editorial):
    page = with_json(editorial, doc(artist())).get("/artistas.html").text
    assert "Banda Demo" in page and "Javiera Mena" not in page
    assert "Próximamente" in page  # ningún tema publicado de esta banda


def test_artists_json_matches_published_songs_by_artist_name(editorial):
    text = doc(artist(slug="mena", name="Javiera Mena"))
    page = with_json(editorial, text).get("/artistas.html").text
    assert "1 tema disponible" in page and 'href="cancion-otra-era.html"' in page


def test_external_links_open_in_a_new_tab_without_opener(editorial):
    page = with_json(editorial, doc(artist())).get("/artistas.html").text
    assert (
        '<a href="https://example.org/demo" target="_blank" rel="noopener noreferrer">Sitio' in page
    )


@pytest.mark.parametrize(
    "bad",
    [
        "no es json",
        "[]",
        json.dumps({"format": 2, "artists": [artist()]}),
        json.dumps({"format": 1, "artists": []}),
        json.dumps({"format": 1, "artists": [artist(slug="Mal Slug")]}),
        json.dumps({"format": 1, "artists": [artist(), artist()]}),
        json.dumps({"format": 1, "artists": [artist(name="")]}),
        json.dumps({"format": 1, "artists": ["texto"]}),
    ],
)
def test_invalid_artists_json_falls_back_to_the_static_data(editorial, bad):
    page = with_json(editorial, bad).get("/artistas.html").text
    assert "Javiera Mena" in page and "Banda Demo" not in page


def test_everything_is_escaped(editorial):
    evil = artist(
        name="<script>alert(1)</script>",
        description='<img src=x onerror="y">',
        links=[{"label": "<b>x</b>", "url": 'https://example.org/"><script>z</script>'}],
    )
    page = with_json(editorial, doc(evil)).get("/artistas.html").text
    assert "<script>alert" not in page and "<img src=x" not in page and "<b>x</b>" not in page
    assert "&lt;script&gt;alert(1)" in page


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,x",
        "//example.org",
        "ftp://example.org",
        "/x",
        "",
        "https://",
        "https://exa mple.org",
        None,
        5,
    ],
)
def test_only_http_and_https_links_are_kept(url):
    assert safe_url(url) is None
    parsed = parse_artists(doc(artist(links=[{"label": "x", "url": url}])))
    assert parsed[0]["links"] == []


def test_http_and_https_are_accepted():
    assert safe_url("http://example.org/a?b=1") and safe_url("https://example.org")


def test_new_artists_json_is_picked_up_with_the_next_release(editorial, monkeypatch):
    import musicsite.catalog as catalog

    clock = Clock()
    monkeypatch.setattr(catalog.time, "monotonic", clock)
    client = with_json(editorial, doc(artist()))
    assert "Banda Demo" in client.get("/artistas.html").text
    release = make_release(editorial, {"otra-era": song_text("otra-era")})
    (editorial / release / "artists.json").write_text(
        doc(artist(slug="otra", name="Otra Banda")), encoding="utf-8"
    )
    clock.now += 61
    assert "Otra Banda" in client.get("/artistas.html").text

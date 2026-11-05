"""Sección Artistas (S24): artists.json del release, respaldo, validación, escape y conteos.

Todo sintético: los artistas de prueba no existen y los temas son los ya públicos de `songs/`.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from musicsite.app import create_app
from musicsite.artists import FALLBACK, parse_artists, photo_credit_html, safe_url
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


# --- foto del artista (S33) ---------------------------------------------------------------------

PHOTO_PATH = "fotos/banda-demo-0123456789ab.jpg"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"\xff\xd9"  # solo importa que parezca un JPEG


def with_photo(editorial: Path, data: bytes | None = JPEG, path: str = PHOTO_PATH, **changes):
    client = with_json(editorial, doc(artist(photo=path, **changes)))
    release = (editorial / "current.txt").read_text().strip()
    if data is not None:
        target = editorial / release / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return client, release


def test_a_photo_is_shown_on_the_card_and_served_with_a_long_cache(editorial):
    client, release = with_photo(editorial)
    # la publicación se cargó antes de escribir la foto: se vuelve a cargar
    client = TestClient(create_app(editorial=editorial))
    page = client.get("/artistas.html").text
    assert f'src="{PHOTO_PATH}"' in page and 'alt="Foto de Banda Demo"' in page
    response = client.get(f"/{PHOTO_PATH}")
    assert response.status_code == 200 and response.content == JPEG
    assert response.headers["content-type"] == "image/jpeg"
    assert "immutable" in response.headers["cache-control"]
    assert client.head(f"/{PHOTO_PATH}").status_code == 200


@pytest.mark.parametrize(
    "data",
    [None, b"GIF89a" + b"\x00" * 30, JPEG + b"\x00" * (300 * 1024)],
    ids=["falta", "gif", "grande"],
)
def test_a_missing_or_bad_photo_means_no_photo_but_the_release_still_loads(editorial, data):
    with_photo(editorial, data)
    client = TestClient(create_app(editorial=editorial))
    page = client.get("/artistas.html").text
    assert "Banda Demo" in page and "<img" not in page.split("data-ac-artist-card")[1]
    assert client.get(f"/{PHOTO_PATH}").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "../secreto.jpg",
        "fotos/../../x.jpg",
        "fotos/banda-demo-0123456789ab.png",
        "fotos/otro-0123456789ab.jpg",  # no empieza con el slug del artista
        "http://example.org/x.jpg",
        "fotos/banda-demo-XYZ.jpg",
    ],
)
def test_photo_paths_outside_the_contract_are_dropped(path):
    (parsed,) = parse_artists(doc(artist(photo=path)))
    assert "photo" not in parsed


def test_a_valid_photo_path_is_kept_by_the_parser():
    (parsed,) = parse_artists(doc(artist(photo=PHOTO_PATH)))
    assert parsed["photo"] == PHOTO_PATH


def test_photos_are_not_served_from_outside_the_published_ones(editorial):
    client, _ = with_photo(editorial)
    client = TestClient(create_app(editorial=editorial))
    for path in ("/fotos/otra-0123456789ab.jpg", "/fotos/", "/fotos/../manifest.json", "/fotos"):
        assert client.get(path).status_code == 404


# --- descripción con párrafos (S34) -------------------------------------------------------------


def test_a_long_description_is_split_into_paragraphs_and_lines(editorial):
    text = "Primer párrafo.\r\n\r\nSegundo párrafo,\nen dos líneas.\n\n\n   \nTercero."
    page = with_json(editorial, doc(artist(description=text))).get("/artistas.html").text
    card = page.split("data-ac-artist-card")[1]
    assert card.count('<p class="m-0">') >= 3
    assert '<p class="m-0">Primer párrafo.</p>' in card
    assert '<p class="m-0">Segundo párrafo,<br>en dos líneas.</p>' in card
    assert '<p class="m-0">Tercero.</p>' in card and "line-height" in card


def test_description_paragraphs_are_still_escaped(editorial):
    text = "<script>alert(1)</script>\n\n<b>negrita</b> & más"
    page = with_json(editorial, doc(artist(description=text))).get("/artistas.html").text
    assert "<script>alert(1)" not in page and "&lt;script&gt;" in page
    assert "<b>negrita" not in page and "&lt;b&gt;negrita" in page and "&amp; más" in page


def test_an_empty_or_blank_description_draws_nothing(editorial):
    page = with_json(editorial, doc(artist(description="  \n\n "))).get("/artistas.html").text
    assert "ac-artist-desc" not in page.split("data-ac-artist-card")[1]


def test_photo_credit_is_shown_escaped_with_an_external_link(editorial):
    with_photo(
        editorial,
        photo_credit="Foto: <b>Ana</b>, CC BY 2.0",
        photo_credit_url="https://commons.wikimedia.org/wiki/File:X.jpg",
    )
    page = TestClient(create_app(editorial=editorial)).get("/artistas.html").text
    assert "Foto: &lt;b&gt;Ana&lt;/b&gt;, CC BY 2.0" in page and "<b>Ana</b>" not in page
    assert (
        'href="https://commons.wikimedia.org/wiki/File:X.jpg" target="_blank" '
        'rel="noopener noreferrer"' in page
    )


def test_photo_credit_without_url_is_plain_text_and_bad_url_is_dropped(editorial):
    with_photo(editorial, photo_credit="Foto: Ana", photo_credit_url="javascript:alert(1)")
    page = TestClient(create_app(editorial=editorial)).get("/artistas.html").text
    assert "ac-photo-credit" in page and "Foto: Ana" in page and "javascript:" not in page


def test_credit_without_photo_is_not_shown():
    assert photo_credit_html({"photo_credit": "Foto: Ana"}) == ""

"""SEO mínimo (S115): noindex por host, robots.txt, sitemap.xml y metadatos únicos por tema."""

import re

import pytest
from fastapi.testclient import TestClient

from musicsite import seo
from musicsite.app import create_app

CANONICAL = {"host": seo.CANONICAL_HOST}
TECHNICAL = [{"host": "musicsite-ufi63f4rva-tl.a.run.app"}, {"host": "saulapp-music.web.app"}]


@pytest.fixture(scope="module")
def off() -> TestClient:
    return TestClient(create_app())  # el valor por defecto: sin lanzar


@pytest.fixture(scope="module")
def on() -> TestClient:
    return TestClient(create_app(indexing=True))


def song_paths(client: TestClient) -> list[str]:
    sitemap = client.get("/sitemap.xml").text
    return [
        loc.removeprefix(seo.BASE_URL)
        for loc in re.findall(r"<loc>(.*?)</loc>", sitemap)
        if seo.SONG_PATH.fullmatch(loc.removeprefix(seo.BASE_URL))
    ]


def test_indexing_ships_off():
    assert seo.INDEXING_ENABLED is False


@pytest.mark.parametrize("headers", [CANONICAL, *TECHNICAL])
@pytest.mark.parametrize("path", ["/", "/artistas.html", "/robots.txt", "/sitemap.xml"])
def test_everything_is_noindex_before_launch(off, headers, path):
    assert off.get(path, headers=headers).headers["x-robots-tag"] == "noindex, nofollow"


def test_robots_blocks_everything_before_launch(off):
    body = off.get("/robots.txt", headers=CANONICAL).text
    assert body == "User-agent: *\nDisallow: /\n"


def test_canonical_host_is_indexable_after_launch(on):
    for path in ("/", "/artistas.html", "/guias.html", "/privacidad.html"):
        assert "x-robots-tag" not in on.get(path, headers=CANONICAL).headers, path


@pytest.mark.parametrize("headers", TECHNICAL)
def test_technical_hosts_stay_noindex_after_launch(on, headers):
    assert on.get("/", headers=headers).headers["x-robots-tag"] == "noindex, nofollow"
    assert on.get("/robots.txt", headers=headers).text == "User-agent: *\nDisallow: /\n"


def test_forwarded_host_wins_over_host(on):
    # Hosting entrega el dominio original en X-Forwarded-Host y el de Cloud Run en Host.
    headers = {"host": "musicsite-ufi63f4rva-tl.a.run.app", "x-forwarded-host": seo.CANONICAL_HOST}
    assert "x-robots-tag" not in on.get("/", headers=headers).headers
    headers = {"host": seo.CANONICAL_HOST, "x-forwarded-host": "saulapp-music.web.app"}
    assert on.get("/", headers=headers).headers["x-robots-tag"] == "noindex, nofollow"


@pytest.mark.parametrize(
    "path",
    [
        "/entrar.html",
        "/mi-acordia.html",
        "/repertorio.html",
        "/pedidos.html",
        "/ser-guia.html",
    ],
)
def test_account_and_demo_pages_never_indexable(on, path):
    assert on.get(path, headers=CANONICAL).headers["x-robots-tag"] == "noindex, nofollow"


def test_launch_robots_points_to_sitemap(on):
    body = on.get("/robots.txt", headers=CANONICAL).text
    assert "Allow: /" in body
    assert "Disallow: /api/" in body
    assert f"Sitemap: {seo.BASE_URL}/sitemap.xml" in body


def test_sitemap_lists_every_published_song_and_no_private_page(off):
    response = off.get("/sitemap.xml")
    assert response.headers["content-type"].startswith("application/xml")
    paths = song_paths(off)
    assert paths, "el sitio de prueba trae temas"
    page_paths = off.get("/songs.json").json()
    assert sorted(f"/cancion-{song['slug']}.html" for song in page_paths) == sorted(paths)
    assert f"{seo.BASE_URL}/</loc>" in response.text
    for private in ("entrar", "mi-acordia", "repertorio", "pedidos", "ser-guia", "/api/"):
        assert private not in response.text


def test_every_published_song_has_unique_title_description_and_canonical(off):
    titles, descriptions = set(), set()
    paths = song_paths(off)
    assert paths
    for path in paths:
        text = off.get(path).text
        title = re.search(r"<title>(.*?)</title>", text, re.S).group(1)
        description = re.search(r'<meta name="description" content="([^"]*)">', text).group(1)
        assert f'<link rel="canonical" href="{seo.BASE_URL}{path}">' in text
        assert title.count(" · ") == 2, title  # tema · artista · Acordia
        titles.add(title)
        descriptions.add(description)
    assert len(titles) == len(paths)
    assert len(descriptions) == len(paths)


def test_embedded_song_is_never_indexable(on):
    path = song_paths(on)[0]
    assert "x-robots-tag" not in on.get(path, headers=CANONICAL).headers
    response = on.get(path + "?embed=1", headers=CANONICAL)
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert "canonical" not in response.text


def test_enrich_song_without_artist_still_gets_canonical():
    page = "<html><head><title>X · Acordia</title></head><body></body></html>"
    out = seo.enrich_song(page, "/cancion-x.html")
    assert f'<link rel="canonical" href="{seo.BASE_URL}/cancion-x.html">' in out
    assert "<title>X · Acordia</title>" in out

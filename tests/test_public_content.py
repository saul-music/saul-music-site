"""El sitio es público: nada de investigación ni de servicios internos en lo que se sirve."""

import re

import pytest

from musicsite.app import HEADERS, SONGS_DIR, WEB_DIR
from musicsite.songpages import render_published

# Todo lo que se sirve: los archivos de web/ y las páginas de canción que salen del template.
FILES = {p.name: p.read_text(encoding="utf-8").lower() for p in WEB_DIR.iterdir()}
SONG_PAGES = {
    f"cancion-{slug}.html": page.lower() for slug, page in render_published(SONGS_DIR).items()
}
SERVED = set(FILES) | set(SONG_PAGES)
PAGES = {n: c for n, c in (FILES | SONG_PAGES).items() if n.endswith(".html")}
FORBIDDEN = ["musicres", "run.app", "dashboard", "saulapp-music", "youtube", "bigquery", "secret"]
HOST = re.compile(r"""(?:<link[^>]*\shref|\ssrc)=["'](https://[^/"']+)""")
LINK_HOST = re.compile(r"""<a[^>]*\shref=["'](https://[^/"']+)""")
ALLOWED_LINKS = {
    "https://www.musicapopular.cl",
    "https://es.wikipedia.org",
    "https://www.biobiochile.cl",
    "https://www.allmusic.com",
}


@pytest.mark.parametrize("name", sorted(FILES | SONG_PAGES))
def test_no_internal_or_research_references(name):
    content = (FILES | SONG_PAGES)[name]
    for word in FORBIDDEN:
        assert word not in content, f"{name} menciona {word!r}"


@pytest.mark.parametrize("name", sorted(PAGES))
def test_internal_links_resolve_to_served_files(name):
    for ref in re.findall(r'(?:href|src)="([a-z0-9-]+\.(?:html|css|js))', PAGES[name]):
        assert ref in SERVED, f"{name} enlaza {ref}, que no se sirve"


@pytest.mark.parametrize("name", sorted(PAGES))
def test_pages_load_theme_and_script(name):
    assert 'href="style.css"' in PAGES[name]
    assert 'src="acordia.js"' in PAGES[name]


@pytest.mark.parametrize("name", sorted(PAGES))
def test_external_hosts_are_allowed_by_csp(name):
    for host in set(HOST.findall(PAGES[name])):
        assert host in HEADERS["Content-Security-Policy"], f"{name} carga {host} sin permiso"


@pytest.mark.parametrize("name", sorted(PAGES))
def test_forms_do_not_submit_anywhere(name):
    for form in re.findall(r"<form[^>]*>", PAGES[name]):
        assert "action=" not in form, f"{name} tiene un formulario que envía datos"


@pytest.mark.parametrize("name", sorted(PAGES))
def test_outbound_links_only_to_allowed_hosts(name):
    # La CSP no limita enlaces: los permitidos se declaran aquí.
    assert set(LINK_HOST.findall(PAGES[name])) <= ALLOWED_LINKS

"""El sitio es público: nada de investigación ni de servicios internos en lo que se sirve."""

import re

import pytest

from musicsite.app import HEADERS, WEB_DIR

PAGES = sorted(WEB_DIR.glob("*.html"))
FORBIDDEN = ["musicres", "run.app", "dashboard", "saulapp-music", "youtube", "bigquery", "secret"]
HOST = re.compile(r"""(?:<link[^>]*\shref|\ssrc)=["'](https://[^/"']+)""")
LINK_HOST = re.compile(r"""<a[^>]*\shref=["'](https://[^/"']+)""")
ALLOWED_LINKS = {
    "https://www.musicapopular.cl",
    "https://es.wikipedia.org",
    "https://www.biobiochile.cl",
    "https://www.allmusic.com",
}


def text(path) -> str:
    return path.read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("path", sorted(WEB_DIR.iterdir()), ids=lambda p: p.name)
def test_no_internal_or_research_references(path):
    content = text(path)
    for word in FORBIDDEN:
        assert word not in content, f"{path.name} menciona {word!r}"


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_internal_links_resolve_to_served_files(path):
    served = {p.name for p in WEB_DIR.iterdir()}
    for ref in re.findall(r'(?:href|src)="([a-z0-9-]+\.(?:html|css|js))', text(path)):
        assert ref in served, f"{path.name} enlaza {ref}, que no se sirve"


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_pages_load_theme_and_script(path):
    content = text(path)
    assert 'href="style.css"' in content
    assert 'src="acordia.js"' in content


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_external_hosts_are_allowed_by_csp(path):
    for host in set(HOST.findall(text(path))):
        assert host in HEADERS["Content-Security-Policy"], f"{path.name} carga {host} sin permiso"


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_forms_do_not_submit_anywhere(path):
    for form in re.findall(r"<form[^>]*>", text(path)):
        assert "action=" not in form, f"{path.name} tiene un formulario que envía datos"


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_outbound_links_only_to_allowed_hosts(path):
    # La CSP no limita enlaces: los permitidos se declaran aquí.
    assert set(LINK_HOST.findall(text(path))) <= ALLOWED_LINKS

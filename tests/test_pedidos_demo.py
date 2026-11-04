"""«Pide una canción» es una demostración (S25): rotulada, sin envío y sin red."""

import re

from musicsite.app import WEB_DIR

PAGE = (WEB_DIR / "pedidos.html").read_text(encoding="utf-8")
SCRIPT = (WEB_DIR / "pedidos.js").read_text(encoding="utf-8")


def test_every_section_is_labelled_as_a_demo():
    assert PAGE.count("Demo / datos de ejemplo") >= 4  # cabecera y tres secciones
    assert PAGE.count("ac-demo-badge") >= 4
    assert "Demo / datos de ejemplo" in SCRIPT  # y cada petición ficticia la repite


def test_forms_have_no_destination():
    forms = re.findall(r"<form[^>]*>", PAGE)
    assert len(forms) == 2
    for form in forms:
        assert "action=" not in form and "method=" not in form


def test_script_does_not_use_the_network_or_storage():
    for word in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "sendBeacon",
        "localStorage",
        "sessionStorage",
        "indexedDB",
        "document.cookie",
        "import(",
    ):
        assert word not in SCRIPT, word


def test_demo_data_is_synthetic():
    assert "@" not in SCRIPT.replace("@media", "")
    assert not re.search(r"https?://", SCRIPT)
    # solo el placeholder del correo, con un dominio reservado para ejemplos
    assert re.findall(r"[\w.]+@[\w]+\.(?:com|cl)\b", PAGE) == ["tucorreo@ejemplo.com"]


def test_the_source_is_a_single_replaceable_adapter():
    assert "function createSource()" in SCRIPT and "subscribe" in SCRIPT


def test_page_is_not_indexed():
    assert '<meta name="robots" content="noindex">' in PAGE

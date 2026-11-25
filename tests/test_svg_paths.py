"""Los trazos SVG de las páginas estáticas son válidos: cada comando lleva sus números completos.

Un `d="M2018H100"` (faltaba el espacio de `M20 18H100`) hace que el navegador rechace el trazo y lo
reporte en la consola, sin que ninguna otra prueba lo note.
"""

import re

import pytest

from musicsite.app import WEB_DIR

ARGS = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "t": 2, "a": 7, "z": 0}
TOKEN = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|(-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)|[\s,]+")
PATHS = [
    (page.name, d)
    for page in sorted(WEB_DIR.glob("*.html"))
    for d in re.findall(r'<path d="([^"]*)"', page.read_text(encoding="utf-8"))
]


def problems(d: str) -> str | None:
    pos, command, count = 0, None, 0
    while pos < len(d):
        match = TOKEN.match(d, pos)
        if match is None:
            return f"carácter inesperado en {d[pos : pos + 8]!r}"
        pos = match.end()
        if match.group(1):
            if command and ARGS[command.lower()] and count % ARGS[command.lower()]:
                return f"{command} con {count} números"
            command, count = match.group(1), 0
            if command in "zZ":
                count = 0
        elif match.group(2):
            if command is None:
                return "números sin comando"
            count += 1
    if command and ARGS[command.lower()] and (count == 0 or count % ARGS[command.lower()]):
        return f"{command} con {count} números"
    return None


def test_pages_have_svg_paths_to_check():
    assert len(PATHS) > 50


@pytest.mark.parametrize(("page", "d"), sorted(set(PATHS)))
def test_svg_path_data_is_valid(page, d):
    assert problems(d) is None, f"{page}: {d[:60]}"

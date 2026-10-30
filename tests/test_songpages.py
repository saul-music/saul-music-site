"""Generador de páginas de canción: datos sintéticos, sin red."""

import re

import pytest

from musicsite import songpages
from musicsite.acordes import main
from musicsite.songpages import build, fingering, load_song, render

SAMPLE = """
slug = "tema"
titulo = "Tema"
artista = "Artista"
tipo = "cancion"
tono = "Sol mayor"
cejilla = "Sin cejilla"
compas = "4/4"
bpm = 92
nivel = "inicial"
acordes = ["G", "D", "Em", "C"]
forma = "Intro - Estrofa - Coro"
partitura = '''
Estrofa x2: G % D Em C
'''

[procedencia]
metodo = "de oído"
autor = "Persona del equipo"
fecha = "2026-10-30"

[revision]
revisado = true
v2_resuelto = false
"""

ROOTS = [
    "C",
    "C#",
    "Db",
    "D",
    "D#",
    "Eb",
    "E",
    "F",
    "F#",
    "Gb",
    "G",
    "G#",
    "Ab",
    "A",
    "A#",
    "Bb",
    "B",
]


def write(folder, name, body):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.toml"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def song(tmp_path):
    return load_song(write(tmp_path, "tema", SAMPLE))


def test_every_basic_chord_has_a_six_string_fingering():
    for root in ROOTS:
        for chord in (root, root + "m"):
            frets = fingering(chord).split()
            assert len(frets) == 6, chord
            assert all(f == "x" or f.isdigit() for f in frets), chord


@pytest.mark.parametrize(
    ("chord", "frets"),
    [("G", "3 2 0 0 0 3"), ("Em", "0 2 2 0 0 0"), ("F", "1 3 3 2 1 1"), ("Bm", "x 2 4 4 3 2")],
)
def test_known_shapes(chord, frets):
    assert fingering(chord) == frets


def test_enharmonic_chords_share_fingering():
    assert fingering("Bb") == fingering("A#")
    assert fingering("Dbm") == fingering("C#m")


def test_render_includes_chords_structure_and_no_badge_when_published(song):
    page = render(song, "publicable", preview=False)
    assert 'data-frets="3 2 0 0 0 3"' in page
    assert '<div class="ac-bar">Em</div>' in page
    assert "Borrador" not in page and "noindex" not in page


def test_render_marks_preview_as_draft_and_noindex(song):
    page = render(song, "borrador", preview=True)
    assert "Borrador sin revisar (borrador)" in page
    assert 'content="noindex"' in page


def test_render_escapes_text(song):
    song["titulo"] = "<script>x</script>"
    page = render(song, "publicable", preview=False)
    assert "<script>x</script>" not in page and "&lt;script&gt;" in page


def test_instrumental_without_harmony_says_so(song):
    song.update(sin_base_armonica=True, acordes=[], secciones=[])
    assert "no tiene una base armónica estable" in render(song, "borrador", True)


def test_build_publishes_only_publishable_unless_preview(tmp_path):
    folder = tmp_path / "src"
    write(folder, "tema", SAMPLE)  # revisado, con V2 sin resolver
    assert build(folder, tmp_path / "a") == []
    assert [p.name for p in build(folder, tmp_path / "b", preview=True)] == ["cancion-tema.html"]
    write(folder, "tema", SAMPLE.replace("v2_resuelto = false", "v2_resuelto = true"))
    assert [p.name for p in build(folder, tmp_path / "c")] == ["cancion-tema.html"]


def test_preview_copies_theme_and_script_next_to_the_pages(tmp_path):
    folder = tmp_path / "src"
    write(folder, "tema", SAMPLE)
    build(folder, tmp_path / "p", preview=True)
    assert (tmp_path / "p" / "style.css").exists() and (tmp_path / "p" / "acordia.js").exists()
    build(folder, tmp_path / "q")  # sin preview no copia nada
    assert not (tmp_path / "q" / "style.css").exists()


def test_build_skips_files_with_errors(tmp_path):
    folder = tmp_path / "src"
    write(folder, "tema", SAMPLE.replace('"G", "D"', '"G7", "D"'))
    assert build(folder, tmp_path / "out", preview=True) == []


def test_cli_pages_command(tmp_path, capsys):
    folder = tmp_path / "src"
    write(folder, "tema", SAMPLE)
    args = ["pages", "--dir", str(folder), "--out", str(tmp_path / "o"), "--preview"]
    assert main(args) == 0
    assert "1 páginas escritas" in capsys.readouterr().out


def test_generated_page_loads_only_site_assets(song):
    page = render(song, "publicable", preview=False)
    hosts = set(re.findall(r'(?:<link[^>]*\shref|\ssrc)="(https://[^/"]+)', page))
    assert hosts <= {
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
        "https://cdn.jsdelivr.net",
    }


def test_songpages_module_has_no_network_code():
    text = open(songpages.__file__, encoding="utf-8").read().lower()
    for word in ("http://", "urllib", "requests", "httpx", "socket"):
        assert word not in text

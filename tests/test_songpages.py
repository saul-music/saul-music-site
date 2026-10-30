"""Generador de páginas y tarjetas: datos sintéticos, sin red."""

import re

import pytest

from musicsite import songpages
from musicsite.acordes import main, validate_file
from musicsite.songpages import (
    LIBRARY_END,
    LIBRARY_START,
    build,
    card,
    load_song,
    render,
    update_library,
)

SAMPLE = """
slug = "otra-era"
titulo = "Otra era"
artista = "Artista"
tipo = "cancion"
barrio = "Indie"
tono = "Sol mayor"
cejilla = "Sin cejilla"
compas = "4/4"
bpm = 92
nivel = "inicial"
acordes = ["G", "D", "Em", "C", "Am", "Bm"]
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
v2_resuelto = true
"""


def write(folder, name, body):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.toml"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def song(tmp_path):
    return load_song(write(tmp_path, "otra-era", SAMPLE))


def with_modes(extra):
    return SAMPLE + extra


def test_page_has_only_the_structure_section_with_three_mode_tabs(song):
    page = render(song, "publicable", preview=False)
    for key in ("basico", "intermedio", "avanzado"):
        assert f'id="p-{key}"' in page
    assert "Básico" in page and "Intermedio" in page and "Avanzado" in page
    assert "data-frets" not in page and "Rasgueo" not in page and "Práctica" not in page
    assert '<div class="ac-bar">Em</div>' in page
    assert "Borrador" not in page and "noindex" not in page


def test_empty_modes_say_proximamente(song):
    page = render(song, "publicable", preview=False)
    assert page.count("Próximamente") == 2  # intermedio y avanzado


def test_modes_with_content_show_it(tmp_path):
    body = with_modes(
        "\n[intermedio]\npartitura = '''\nEstrofa x2: G7 % Dsus4 Em7\n'''\n"
        "\n[avanzado]\npartitura = '''\nEstrofa: G/B C\n'''\ntab = '''\ne|--0--|\n'''\n"
    )
    page = render(load_song(write(tmp_path, "otra-era", body)), "publicable", False)
    assert "Dsus4" in page and "G/B" in page and "<pre" in page and "e|--0--|" in page
    assert "Próximamente" not in page


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


def test_extended_chords_are_valid_only_in_their_modes(tmp_path):
    ok = with_modes(
        "\n[intermedio]\npartitura = '''\nA: G7 Cmaj7 Dsus4 Am9 F#m7b5 Cadd9\n'''\n"
        "\n[avanzado]\npartitura = '''\nA: G/B D/F# C\n'''\n"
    )
    assert validate_file(write(tmp_path, "otra-era", ok)).errors == []
    slash_in_middle = with_modes("\n[intermedio]\npartitura = '''\nA: G/B\n'''\n")
    errors = validate_file(write(tmp_path, "otra-era", slash_in_middle)).errors
    assert any("intermedio" in e and "G/B" in e for e in errors)
    junk = with_modes("\n[avanzado]\npartitura = '''\nA: Hx\n'''\n")
    assert validate_file(write(tmp_path, "otra-era", junk)).errors


def test_basic_section_still_rejects_extensions(tmp_path):
    bad = SAMPLE.replace('"G", "D", "Em", "C", "Am", "Bm"]', '"G7", "D", "Em", "C", "Am", "Bm"]')
    assert any("«G7»" in e for e in validate_file(write(tmp_path, "otra-era", bad)).errors)


def test_barrio_must_be_a_known_one(tmp_path):
    bad = SAMPLE.replace('barrio = "Indie"', 'barrio = "Jazz"')
    assert any("barrio" in e for e in validate_file(write(tmp_path, "otra-era", bad)).errors)


def test_card_summarizes_basic_chords_and_links_when_published(song):
    html = card(song, "otra-era", "publicable")
    assert 'href="cancion-otra-era.html"' in html
    assert html.count("ac-chip-chord") == 4 and "+2" in html
    assert "Indie" in html and "Nivel inicial" in html and "4/4 · 92 bpm" in html
    assert "Próximamente" not in html


def test_card_of_unpublished_song_is_not_a_link(song):
    html = card(song, "otra-era", "con errores")
    assert "<a " not in html and "Próximamente" in html


def test_card_for_instrumental_without_chords_shows_instrumental(song):
    song.update(tipo="instrumental", acordes=[], barrio="")
    html = card(song, "otra-era", "publicable")
    assert "Instrumental" in html and "ac-chip-chord" not in html


def test_update_library_replaces_only_the_marked_block(tmp_path):
    folder = tmp_path / "src"
    write(folder, "otra-era", SAMPLE)
    index = tmp_path / "index.html"
    index.write_text(f"antes\n{LIBRARY_START}\nviejo\n{LIBRARY_END}\ndespués\n", encoding="utf-8")
    assert update_library(folder, index) == 1
    text = index.read_text(encoding="utf-8")
    assert text.startswith("antes\n") and text.rstrip().endswith("después")
    assert "viejo" not in text and "Otra era" in text


def test_build_publishes_only_publishable_unless_preview(tmp_path):
    folder = tmp_path / "src"
    write(folder, "otra-era", SAMPLE.replace("v2_resuelto = true", "v2_resuelto = false"))
    assert build(folder, tmp_path / "a") == []
    assert [p.name for p in build(folder, tmp_path / "b", preview=True)] == [
        "cancion-otra-era.html"
    ]
    write(folder, "otra-era", SAMPLE)
    assert [p.name for p in build(folder, tmp_path / "c")] == ["cancion-otra-era.html"]


def test_preview_copies_theme_and_script_next_to_the_pages(tmp_path):
    folder = tmp_path / "src"
    write(folder, "otra-era", SAMPLE)
    build(folder, tmp_path / "p", preview=True)
    assert (tmp_path / "p" / "style.css").exists() and (tmp_path / "p" / "acordia.js").exists()
    build(folder, tmp_path / "q")
    assert not (tmp_path / "q" / "style.css").exists()


def test_build_skips_files_with_errors(tmp_path):
    folder = tmp_path / "src"
    write(folder, "otra-era", SAMPLE.replace('"G", "D"', '"G7", "D"'))
    assert build(folder, tmp_path / "out", preview=True) == []


def test_cli_pages_and_library_commands(tmp_path, capsys):
    folder = tmp_path / "src"
    write(folder, "otra-era", SAMPLE)
    assert main(["pages", "--dir", str(folder), "--out", str(tmp_path / "o")]) == 0
    assert "1 páginas escritas" in capsys.readouterr().out
    index = tmp_path / "index.html"
    index.write_text(f"{LIBRARY_START}\n{LIBRARY_END}\n", encoding="utf-8")
    assert main(["library", "--dir", str(folder), "--index", str(index)]) == 0
    assert "1 tarjetas escritas" in capsys.readouterr().out


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


def test_bar_with_several_chords_is_one_cell_with_proportional_parts():
    from musicsite.songpages import bar_html

    assert bar_html("F#-F#7") == (
        '<div class="ac-bar is-split"><span class="ac-part" style="flex: 1">F#</span>'
        '<span class="ac-part" style="flex: 1">F#7</span></div>'
    )
    held = bar_html("F#-%-F#7-B7")
    assert held.count("<span") == 3
    assert 'style="flex: 2">F#<' in held and 'style="flex: 1">B7<' in held


def test_whole_bar_repeat_is_still_a_plain_cell():
    from musicsite.songpages import bar_html

    assert bar_html("%") == '<div class="ac-bar">%</div>'

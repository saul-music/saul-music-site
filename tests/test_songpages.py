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
    chords_payload,
    json_script,
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


def btn(chord: str, shown: str | None = None) -> str:
    """El botón con que se muestra un acorde (abre su diagrama)."""
    return (
        f'<button type="button" class="ac-chord-btn" data-chord="{chord}" '
        f'aria-haspopup="dialog">{shown or chord}</button>'
    )


def text_of(html: str) -> str:
    return re.sub(r"<[^>]*>", "", html)


def test_page_has_only_the_structure_section_with_three_mode_tabs(song):
    page = render(song, "publicable", preview=False)
    for key in ("basico", "intermedio", "avanzado"):
        assert f'id="p-{key}"' in page
    assert "Básico" in page and "Intermedio" in page and "Avanzado" in page
    assert "data-frets" not in page and "Rasgueo" not in page and "Práctica" not in page
    assert f'<div class="ac-bar">{btn("Em")}</div>' in page
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
        '<div class="ac-bar is-split"><span class="ac-part" style="flex: 1" data-weight="1">'
        + btn("F#", "F\u266f")
        + '</span><span class="ac-part" style="flex: 1" data-weight="1">'
        + btn("F#7", "F\u266f7")
        + "</span></div>"
    )
    held = bar_html("F#-%-F#7-B7")
    assert held.count("<span") == 3
    assert 'style="flex: 2" data-weight="2">' + btn("F#", "F\u266f") in held
    assert 'style="flex: 1" data-weight="1">' + btn("B7") in held


def test_whole_bar_repeat_is_still_a_plain_cell():
    from musicsite.songpages import bar_html

    assert bar_html("%") == '<div class="ac-bar">%</div>'


def test_each_section_exposes_its_repetitions_for_the_playhead():
    from musicsite.songpages import structure

    html = structure(
        [
            {"nombre": "Estrofa", "repeticiones": 4, "compases": ["E", "F#"]},
            {"nombre": "Final", "compases": ["E"]},
        ]
    )
    assert 'class="ac-bars" data-reps="4"' in html
    assert 'class="ac-bars" data-reps="1"' in html


def test_accidentals_are_shown_as_music_symbols_without_touching_the_data():
    from musicsite.songpages import accidentals, bar_html

    assert accidentals("F#m") == "F\u266fm"
    assert accidentals("Bb") == "B\u266d"
    assert accidentals("C7b9") == "C7\u266d9"
    assert accidentals("Dsus4/F#") == "Dsus4/F\u266f"
    assert accidentals("Em") == "Em" and accidentals("Gdim") == "Gdim" and accidentals("%") == "%"
    assert bar_html("F#").count("F\u266f") == 1


def test_metronome_bar_has_mute_and_a_guides_entry_only_when_there_are_guides(song, monkeypatch):
    from musicsite import songpages

    page = render(song, "publicable", preview=False)
    assert "data-ac-met-mute" in page
    assert 'data-ac-met-countin aria-pressed="true"' in page
    assert "2 guías pueden enseñarte esta canción" in page or "data-ac-met-guides" in page
    monkeypatch.setattr(songpages, "teachers_for", lambda slug: [])
    empty = render(song, "publicable", preview=False)
    assert "data-ac-met-guides" not in empty and "data-ac-met-help" not in empty
    assert "guias-panel" not in empty


def test_percent_bar_shows_the_previous_chord_dimmed():
    from musicsite.songpages import structure

    html = structure([{"nombre": "Interludio", "compases": ["E", "%", "D#m", "%", "%"]}])
    bars = re.findall(r'<div class="ac-bar([^"]*)"[^>]*>(.*?)</div>', html)
    assert [text_of(chord) for _, chord in bars] == ["E", "E", "D\u266fm", "D\u266fm", "D\u266fm"]
    assert ["is-repeat" in cls for cls, _ in bars] == [False, True, False, True, True]
    assert "%" not in text_of(html)


def test_percent_bar_repeats_a_split_bar_too():
    from musicsite.songpages import structure

    html = structure([{"nombre": "Puente", "compases": ["F#-F#7", "%"]}])
    assert html.count("is-split") == 2 and html.count("is-repeat") == 1
    assert html.count("F\u266f7") == 2


def test_percent_inside_a_bar_still_holds_the_chord():
    from musicsite.songpages import bar_html

    held = bar_html("F#-%-F#7-B7")
    assert 'style="flex: 2" data-weight="2">' + btn("F#", "F\u266f") in held
    assert "is-repeat" not in held


def test_own_shape_goes_only_to_its_version_and_the_page_embeds_the_data(tmp_path):
    body = with_modes(
        "\n[avanzado]\npartitura = '''\nA: G Em\n'''\n[avanzado.formas]\n\"G\" = \"3 5 5 4 3 3\"\n"
    )
    loaded = load_song(write(tmp_path, "otra-era", body))
    assert loaded["formas"] == {"avanzado": {"G": [3, 5, 5, 4, 3, 3]}}
    payload = chords_payload(loaded)
    assert payload["own"]["avanzado"]["G"]["frets"] == [3, 5, 5, 4, 3, 3]
    assert "intermedio" not in payload["own"] and payload["chords"]["G"]["guitar"]
    page = render(loaded, "publicable", preview=False)
    assert 'id="acordes-data"' in page and "ac-chord-btn" in page
    assert "<" not in page.split('id="acordes-data">')[1].split("</script>")[0]


def test_chords_data_is_embedded_safely_and_only_for_chords_of_the_song(song):
    assert "<" not in json_script({"x": "</script><b>"})
    payload = chords_payload(song)
    assert set(payload["chords"]) == {"G", "D", "Em", "C"}  # los de sus compases
    assert payload["chords"]["G"]["label"] == "G" and payload["own"] == {}


def test_title_and_artist_strip_is_in_the_sticky_area_and_starts_hidden(song):
    page = render(song, "publicable", preview=False)
    assert "data-ac-sticky-title hidden><strong>" in page
    assert page.index("ac-sticky-tools") < page.index("data-ac-sticky-title")


# --- Tips entre secciones -------------------------------------------------------------------


TIPS_SAMPLE = SAMPLE.replace(
    "Estrofa x2: G % D Em C\n",
    "> ¿Qué hace el bajo? | La guitarra sostiene G y el bajo baja a D <b>suave</b>.\n"
    "Estrofa x2: G % D Em C\n"
    "> Cierra con calma | Deja sonar el último C.\n"
    "Coro: C Am\n",
)


def test_tips_keep_their_place_between_sections():
    from musicsite.acordes import parse_score

    sections, errors = parse_score("> A | uno\nEstrofa: G D\n> B | dos\nCoro: C Am\n")
    assert errors == []
    assert [("consejo" in s) for s in sections] == [True, False, True, False]
    assert sections[0]["consejo"] == {"titulo": "A", "texto": "uno"}


@pytest.mark.parametrize(
    "line",
    [
        "> Solo título",
        "> | sin título",
        "> Sin texto |",
        "> " + "x" * 61 + " | t",
        "> t | " + "x" * 281,
    ],
)
def test_bad_tips_are_rejected_with_a_clear_message(tmp_path, line):
    body = SAMPLE.replace("Estrofa x2:", f"{line}\nEstrofa x2:")
    errors = validate_file(write(tmp_path, "otra-era", body)).errors
    assert any("tip" in e for e in errors)


def test_tips_validate_in_every_mode_and_do_not_count_as_bars(tmp_path):
    body = TIPS_SAMPLE + (
        "\n[intermedio]\npartitura = '''\n> Tip IM | texto\nEstrofa: G7 Em7\n'''\n"
        "[avanzado]\npartitura = '''\nEstrofa: Gmaj7 D\n> Tip AV | texto\n'''\n"
    )
    assert validate_file(write(tmp_path, "otra-era", body)).errors == []


def test_tip_renders_escaped_in_position_and_the_playhead_ignores_it(tmp_path):
    page = render(load_song(write(tmp_path, "otra-era", TIPS_SAMPLE)), "publicable", preview=False)
    assert page.count('data-ac-tip="') == 2
    assert "&lt;b&gt;suave&lt;/b&gt;" in page and "<b>suave</b>" not in page
    first, estrofa, second, coro = (
        page.index('data-ac-tip="'),
        page.index('<h2 class="h5 m-0">Estrofa'),
        page.rindex('data-ac-tip="'),
        page.index('<h2 class="h5 m-0">Coro'),
    )
    assert first < estrofa < second < coro
    assert '<button type="button" class="ac-tip-btn" aria-expanded="false">' in page
    # Los tips no son compases: ni cuentan como `.ac-bars` ni se mezclan con ellos.
    assert page.count('class="ac-bars"') == 2


def test_a_song_without_tips_is_unchanged(song):
    assert "ac-tip" not in render(song, "publicable", preview=False).split("</style>")[-1]


def test_library_is_sorted_by_artist_ignoring_articles_and_accents():
    from musicsite.songpages import artist_key, render_library, sort_key

    assert artist_key("Los Bunkers") == "bunkers" and artist_key("La Ley") == "ley"
    assert artist_key("Álvaro Díaz") == "alvaro diaz" and sort_key("ÉPICA") == "epica"
    songs = [
        {"titulo": "Zeta", "artista": "Los Tres"},
        {"titulo": "Beta", "artista": "Álvaro"},
        {"titulo": "Ánimo", "artista": "Los Bunkers"},
        {"titulo": "Alfa", "artista": "los bunkers"},
    ]
    page = render_library([(song, "x", "borrador") for song in songs])
    # Álvaro, luego Bunkers (Alfa antes que Ánimo, sin tildes), luego Tres
    order = [
        page.index(f'<h4 class="h4 mb-1">{title}') for title in ("Beta", "Alfa", "Ánimo", "Zeta")
    ]
    assert order == sorted(order)


def test_library_opens_each_artist_group_with_a_header_and_count():
    from musicsite.songpages import render_library

    songs = [
        {"titulo": "Uno", "artista": "Los Tres"},
        {"titulo": "Dos", "artista": "los tres"},
        {"titulo": "Solo", "artista": "Gepe"},
    ]
    page = render_library([(song, "x", "borrador") for song in songs])
    assert page.count('class="col-12 ac-artist-head"') == 2
    assert "<small>1 tema</small>" in page and "<small>2 temas</small>" in page
    assert page.index("Gepe") < page.index("Dos") < page.index("Uno")


def test_tip_inline_puts_backticked_chords_in_the_chord_font_and_stays_escaped():
    from musicsite.songpages import tip_inline

    assert tip_inline("Prueba `C#m7b5` y `Gmaj7`") == (
        'Prueba <span class="ac-inline-chord">C#m7b5</span> y '
        '<span class="ac-inline-chord">Gmaj7</span>'
    )
    assert tip_inline("un ` suelto") == "un ` suelto"
    assert tip_inline("`<b>x</b>`") == '<span class="ac-inline-chord">&lt;b&gt;x&lt;/b&gt;</span>'
    assert "<b>" not in tip_inline("<b>hola</b> `G`")


def test_tip_title_and_text_both_use_the_chord_font():
    from musicsite.songpages import tip_html

    out = tip_html({"titulo": "¿Suena `Em`?", "texto": "Cambia a `C#m7b5`."})
    assert out.count('class="ac-inline-chord"') == 2 and "`" not in out

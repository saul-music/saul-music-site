"""Perfiles de enseñanza: reglas por artista o por tema, datos sintéticos."""

import pytest
from acordia_render.songpages import render

from musicsite.profes import (
    GUIDES_END,
    GUIDES_START,
    check_rule,
    describe,
    load_profiles,
    songs_of,
    teachers_for,
    teaches,
    top_teachers,
    update_guides,
)

BY_ARTIST = {"ensena": [{"artista": "Los Tres"}]}
BY_SONG = {"ensena": [{"artista": "Los Bunkers", "tema": "ven-aqui"}]}
EVERYTHING = {"ensena": [{"artista": "*"}]}


def test_artist_rule_covers_all_its_songs_only():
    assert teaches(BY_ARTIST, "dejate-caer")
    assert not teaches(BY_ARTIST, "ven-aqui")


def test_song_rule_covers_only_that_song():
    assert songs_of(BY_SONG) == ["ven-aqui"]


def test_wildcard_covers_everything_and_version_suffix_counts_as_the_artist():
    assert teaches(EVERYTHING, "yo-no-te-pido-la-luna")
    assert teaches({"ensena": [{"artista": "Javiera Mena"}]}, "yo-no-te-pido-la-luna")


@pytest.mark.parametrize(
    "rule",
    [
        {},
        {"artista": "Nadie"},
        {"artista": "Los Tres", "tema": "ven-aqui"},
        {"artista": "Los Tres", "tema": "no-existe"},
        {"artista": "*", "tema": "ven-aqui"},
        {"artista": "Los Tres", "extra": 1},
    ],
)
def test_invalid_rules_are_rejected(rule):
    assert check_rule(rule)


def test_real_file_is_valid_and_two_people_teach_everything():
    profiles = load_profiles()
    everything = [p["nombre"] for p in profiles if describe(p) == "Todo el repertorio"]
    assert everything == ["Gonzalo Pincheira", "Alejandro Bustos"]
    assert all(p.get("mock") for p in profiles if p["nombre"] not in everything)


def test_invalid_file_reports_all_errors(tmp_path):
    bad = tmp_path / "profes.toml"
    bad.write_text('[[profe]]\nid = "x"\nensena = [{ artista = "Nadie" }]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="falta nombre"):
        load_profiles(bad)


def test_every_repertoire_song_has_at_least_two_teachers():
    from acordia_render.acordes import REPERTOIRE

    assert all(len(teachers_for(slug)) >= 2 for slug, *_ in REPERTOIRE)


def test_guides_appear_once_as_a_strip_before_the_player():
    song = {
        "slug": "ven-aqui",
        "titulo": "Ven aquí",
        "artista": "Los Bunkers",
        "tipo": "cancion",
        "bpm": 90,
    }
    page = render(song, "publicable", preview=False)
    # Una entrada con dos formas (franja y botón corto, oculto) que abren el mismo desplegable.
    assert page.count('data-bs-target="#guias-panel"') == 3  # franja, botón corto y cerrar
    assert page.count('href="guias.html?tema=ven-aqui"') == 3  # franja y botón (respaldo) + panel
    assert "data-ac-met-help" in page and " hidden>¿Se complica" in page
    # una sola franja de guías (la de Utilidades, RD22, es otra aparte)
    assert page.count('aria-label="Guías de este tema"') == 1 and "Ver guías" not in page
    # La franja va primero: antes de la barra del metrónomo, las pestañas y los compases.
    assert (
        page.index("data-ac-met-guides") < page.index("data-ac-metronome") < page.index('id="tabs"')
    )


def test_update_guides_writes_one_card_per_profile(tmp_path):
    page = tmp_path / "guias.html"
    page.write_text(f"<div>{GUIDES_START}\n{GUIDES_END}</div>", encoding="utf-8")
    assert update_guides(page) == len(load_profiles())
    text = page.read_text(encoding="utf-8")
    assert text.count('data-temas="') == len(load_profiles())
    assert "Todo el repertorio" in text


def test_top_teachers_rank_by_score_and_leave_unrated_last():
    from musicsite.profes import top_teachers

    rated = [
        {"nombre": "A", "puntuacion": 4.5, "resenas": 10, "hoy": False},
        {"nombre": "B", "puntuacion": 4.9, "resenas": 3, "hoy": False},
        {"nombre": "C", "puntuacion": 4.9, "resenas": 30, "hoy": False},
        {"nombre": "N1", "hoy": False},
        {"nombre": "N2", "hoy": True},
    ]
    profiles = [{**p, "id": p["nombre"], "ensena": [{"artista": "*"}]} for p in rated]
    names = [p["nombre"] for p in top_teachers("ven-aqui", 5, profiles)]
    assert names == ["C", "B", "A", "N2", "N1"]
    assert len(top_teachers("ven-aqui", 2, profiles)) == 2


def test_real_people_are_never_given_a_score():
    for profile in load_profiles():
        if not profile.get("mock"):
            assert "puntuacion" not in profile and "resenas" not in profile


def test_score_needs_reviews_and_a_valid_range(tmp_path):
    base = '[[profe]]\nid = "x"\nnombre = "X"\nlugar = "Santiago"\nmodo = ["linea"]\nmock = true\n'
    rules = 'ensena = [{ artista = "*" }]\n'
    bad = tmp_path / "profes.toml"
    bad.write_text(base + "puntuacion = 6\nresenas = 2\n" + rules, encoding="utf-8")
    with pytest.raises(ValueError, match="entre 1 y 5"):
        load_profiles(bad)
    bad.write_text(base + "puntuacion = 4\n" + rules, encoding="utf-8")
    with pytest.raises(ValueError, match="van juntas"):
        load_profiles(bad)


def test_coverage_says_how_much_of_the_song_a_guide_teaches():
    from musicsite.profes import coverage

    everything = {"ensena": [{"artista": "*"}]}
    artist = {"ensena": [{"artista": "Los Bunkers"}]}
    one = {"ensena": [{"artista": "Los Bunkers", "tema": "ven-aqui"}]}
    assert coverage(everything, "ven-aqui") == "Todo el repertorio"
    assert coverage(artist, "ven-aqui") == "Los Bunkers (todos)"
    assert coverage(one, "ven-aqui") == "Este tema"


def test_guides_panel_lists_at_most_five_with_price_and_links_to_the_filtered_page():
    from acordia_render.songpages import guides_panel

    html = guides_panel("ven-aqui", "Ven aquí")
    assert html.count('class="ac-guide-row"') <= 5
    assert 'href="guias.html?tema=ven-aqui"' in html and "/ clase" in html
    assert "★" in html  # las de ejemplo traen nota


def test_each_guide_row_links_to_that_guides_card_on_the_guides_page():
    from acordia_render.songpages import guides_panel

    html = guides_panel("camara-lenta", "Cámara lenta")
    for profile in top_teachers("camara-lenta"):
        assert f'href="guias.html?tema=camara-lenta#guia-{profile["id"]}"' in html


def test_guides_page_has_an_anchor_for_every_profile():
    from musicsite.app import WEB_DIR

    page = (WEB_DIR / "guias.html").read_text(encoding="utf-8")
    for profile in load_profiles():
        assert f'id="guia-{profile["id"]}"' in page

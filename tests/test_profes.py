"""Perfiles de enseñanza: reglas por artista o por tema, datos sintéticos."""

import pytest

from musicsite.profes import (
    GUIDES_END,
    GUIDES_START,
    check_rule,
    describe,
    load_profiles,
    songs_of,
    teachers_for,
    teaches,
    update_guides,
)
from musicsite.songpages import render, teacher_panel

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
    from musicsite.acordes import REPERTOIRE

    assert all(len(teachers_for(slug)) >= 2 for slug, *_ in REPERTOIRE)


def test_panel_names_the_song_and_links_to_the_filtered_guides():
    html = teacher_panel("ven-aqui", "Ven aquí")
    assert "Ven aquí" in html and "guias.html?tema=ven-aqui" in html
    assert "Gonzalo Pincheira" in html and "Perfiles de ejemplo" in html


def test_panel_sits_above_the_tabs_in_every_mode():
    song = {"slug": "ven-aqui", "titulo": "Ven aquí", "artista": "Los Bunkers", "tipo": "cancion"}
    page = render(song, "publicable", preview=False)
    assert page.index("Guías de este tema") < page.index('id="tabs"')


def test_update_guides_writes_one_card_per_profile(tmp_path):
    page = tmp_path / "guias.html"
    page.write_text(f"<div>{GUIDES_START}\n{GUIDES_END}</div>", encoding="utf-8")
    assert update_guides(page) == len(load_profiles())
    text = page.read_text(encoding="utf-8")
    assert text.count('data-temas="') == len(load_profiles())
    assert "Todo el repertorio" in text

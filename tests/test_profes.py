"""Perfiles de enseñanza: reglas por artista o por tema, datos sintéticos."""

import pytest
from acordia_render.songpages import render

from musicsite import profes
from musicsite.profes import (
    GUIDES_END,
    GUIDES_START,
    catalog_warnings,
    check_rule,
    check_rule_in_catalog,
    describe,
    load_profiles,
    render_guides,
    songs_in,
    songs_of,
    teachers_for,
    teaches,
    top_teachers,
    update_guides,
)

# Temas publicados de estas pruebas. «moizefala» nunca estuvo en el repertorio inicial:
# las guías por artista también lo alcanzan.
CATALOG = {
    "dejate-caer": ("Déjate caer", "Los Tres"),
    "he-barrido-el-sol": ("He barrido el sol", "Los Tres"),
    "moizefala": ("Moizefala", "Los Tres"),
    "ven-aqui": ("Ven aquí", "Los Bunkers"),
    "llueve-sobre-la-ciudad": ("Llueve sobre la ciudad", "Los Bunkers"),
    "bailando-solo": ("Bailando solo", "Los Bunkers"),
    "camara-lenta": ("Cámara lenta", "Javiera Mena"),
    "esquemas-juveniles": ("Esquemas juveniles", "Javiera Mena"),
    "otra-era": ("Otra era", "Javiera Mena"),
    "yo-no-te-pido-la-luna": ("Yo no te pido la luna", "Javiera Mena (versión)"),
    "hablar-de-ti": ("Hablar de ti", "Gepe"),
}


@pytest.fixture(autouse=True)
def published_songs():
    profes.use_catalog(CATALOG)
    yield
    profes.use_catalog({})


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
    [{}, {"artista": "*", "tema": "ven-aqui"}, {"artista": "Los Tres", "extra": 1}],
)
def test_malformed_rules_are_rejected(rule):
    assert check_rule(rule)


@pytest.mark.parametrize(
    "rule",
    [
        {"artista": "Nadie"},
        {"artista": "Los Tres", "tema": "ven-aqui"},
        {"artista": "Los Tres", "tema": "no-existe"},
    ],
)
def test_rules_that_reach_nothing_published_are_reported(rule):
    assert not check_rule(rule)  # la forma está bien
    assert check_rule_in_catalog(rule)  # pero hoy no alcanza ningún tema publicado


def test_a_song_published_later_is_reached_by_the_artist_rule():
    """Antes las reglas por artista solo veían los 15 temas de una lista fija."""
    assert teaches(BY_ARTIST, "moizefala")
    assert "moizefala" in songs_of(BY_ARTIST)


def test_without_a_catalog_only_the_wildcard_teaches_and_nothing_breaks():
    profes.use_catalog({})
    assert not teaches(BY_ARTIST, "dejate-caer") and teaches(EVERYTHING, "dejate-caer")
    assert songs_of(BY_ARTIST) == [] and profes.song_title("x") == "x"


def test_songs_in_reads_title_and_artist_from_a_folder(tmp_path):
    (tmp_path / "otra-era.toml").write_text('titulo = "Otra era"\nartista = "Javiera Mena"\n')
    (tmp_path / "sin-datos.toml").write_text('slug = "sin-datos"\n')
    assert songs_in(tmp_path) == {
        "otra-era": ("Otra era", "Javiera Mena"),
        "sin-datos": ("sin-datos", ""),
    }


def test_the_real_profiles_do_not_point_at_missing_published_songs():
    assert catalog_warnings(load_profiles()) == []


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


def test_every_published_song_has_at_least_two_teachers():
    assert all(len(teachers_for(slug)) >= 2 for slug in CATALOG)


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
    # La franja va primero: antes de las pestañas de versión (sobre la barra, RD26), de la barra
    # del metrónomo y de los compases.
    assert (
        page.index("data-ac-met-guides") < page.index('id="tabs"') < page.index("data-ac-metronome")
    )


def test_update_guides_writes_one_card_per_profile(tmp_path):
    page = tmp_path / "guias.html"
    page.write_text(f"<div>{GUIDES_START}\n{GUIDES_END}</div>", encoding="utf-8")
    assert update_guides(page) == len(load_profiles())
    text = page.read_text(encoding="utf-8")
    assert text.count('data-temas="') == len(load_profiles())
    assert "Todo el repertorio" in text
    assert "moizefala" in text  # el filtro por tema conoce los temas publicados
    assert render_guides(f"{GUIDES_START}{GUIDES_END}").count("data-temas") == len(load_profiles())


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

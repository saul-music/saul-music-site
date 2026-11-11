"""«Aprender» (S65): el árbol de rutas, los artículos y la teoría que dibujan las figuras."""

import re

import pytest
from acordia_render.chordtheory import check_shape, parse
from fastapi.testclient import TestClient

from musicsite import learn
from musicsite import learn_figures as fig
from musicsite.app import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(scope="module")
def routes() -> list[learn.Route]:
    return learn.load()


# ---- Teoría de las figuras ----


def test_each_fret_is_a_semitone_and_the_strings_are_tuned_in_fourths():
    assert fig.note_at(6, 0) == "E" and fig.note_at(6, 5) == "A" and fig.note_at(6, 1) == "F"
    assert fig.note_at(5, 0) == "A" and fig.note_at(2, 0) == "B" and fig.note_at(1, 0) == "E"
    # la misma nota, 5 trastes antes en la cuerda de arriba… salvo Sol–Si (4)
    for low, high in ((6, 5), (5, 4), (4, 3)):
        assert fig.note_at(low, 5) == fig.note_at(high, 0)
    assert fig.note_at(3, 4) == fig.note_at(2, 0)


def test_flats_and_sharps_name_the_same_fret():
    assert fig.note_at(6, 2, flats=False) == "F#" and fig.note_at(6, 2, flats=True) == "Gb"


@pytest.mark.parametrize(
    ("root", "scale"),
    [
        ("C", "C D E F G A B"),
        ("G", "G A B C D E F#"),
        ("D", "D E F# G A B C#"),
        ("A", "A B C# D E F# G#"),
        ("E", "E F# G# A B C# D#"),
        ("F", "F G A Bb C D E"),
    ],
)
def test_major_scale_is_spelled_by_letter(root, scale):
    assert " ".join(fig.major_scale(root)) == scale


@pytest.mark.parametrize("root", ["C", "G", "D", "A", "E", "F", "Bb", "F#"])
@pytest.mark.parametrize("minor", [False, True])
def test_triads_match_the_library_theory(root, minor):
    assert fig.triad(root, minor=minor) == fig.library_triad(root, minor=minor)


def test_the_minor_triad_lowers_only_the_third_by_one_semitone():
    for root in "CGDAE":
        major, minor = fig.triad(root), fig.triad(root, minor=True)
        assert major[0] == minor[0] and major[2] == minor[2]
        assert major[1] != minor[1]


def test_interval_rules_on_the_fretboard():
    root = (6, 3)  # Sol
    assert fig.semitones_between(root, (6, 6)) == 3  # tercera menor: +3 en la misma cuerda
    assert fig.semitones_between(root, (6, 7)) == 4  # tercera mayor
    assert fig.semitones_between(root, (5, 5)) == 7  # quinta: una cuerda arriba, +2 trastes
    assert fig.semitones_between(root, (4, 5)) == 12  # octava: dos cuerdas arriba, +2 trastes
    # el salto Sol–Si es un traste menor: desde la cuerda 4 la octava está en la 2, +3 trastes
    assert fig.semitones_between((4, 3), (2, 6)) == 12
    assert fig.semitones_between((4, 3), (2, 5)) == 11


def test_the_interval_table_is_consistent():
    assert [row[0] for row in fig.INTERVALS] == list(range(13))
    for semis, _name, _degree, example in fig.INTERVALS:
        assert fig.SHARP_NAMES[semis % 12] == example or fig.FLAT_NAMES[semis % 12] == example, (
            semis
        )


def test_chord_shapes_in_the_articles_are_valid_chords():
    cases = {
        "E": [0, 2, 2, 1, 0, 0],
        "Em": [0, 2, 2, 0, 0, 0],
        "G": [3, 5, 5, 4, 3, 3],
        "Gm": [3, 5, 5, 3, 3, 3],
    }
    for name, frets in cases.items():
        chord = parse(name)
        assert chord is not None and check_shape(chord, frets) == [], name
    # E y Em solo se distinguen en la cuerda 3 (índice 3): Sol# contra Sol
    major, minor = (
        fig.chord_diagram_notes([0, 2, 2, 1, 0, 0]),
        fig.chord_diagram_notes([0, 2, 2, 0, 0, 0]),
    )
    assert [a for a, b in zip(major, minor, strict=True) if a != b] == ["G#"]


def test_the_e_shape_moved_up_makes_g_a_and_b():
    base = [0, 2, 2, 1, 0, 0]
    for shift, chord in ((3, "G"), (5, "A"), (7, "B")):
        moved = [f + shift for f in base]
        assert check_shape(parse(chord), moved) == [], chord


def test_every_figure_renders_accessibly_without_external_resources():
    for name, make in fig.FIGURES.items():
        html = make()
        assert html.strip(), name
        assert "http" not in html and "<script" not in html and "javascript:" not in html, name
        if "<svg" in html:
            assert 'role="img"' in html and "<title>" in html, name


# ---- Árbol, artículos y páginas ----


def test_the_routes_are_basicos_then_acordes_with_their_topics_in_order(routes):
    assert [r.id for r in routes] == ["basicos", "acordes"]
    assert [r.title for r in routes] == ["Básicos", "Acordes"]
    assert [a.slug for a in routes[0].articles] == ["clave-americana", "compas-y-pulso"]
    assert [a.slug for a in routes[1].articles] == ["intervalos", "mayores-y-menores"]


def test_every_figure_token_in_the_articles_exists_and_none_is_left_over(routes):
    for route in routes:
        for article in route.articles:
            tokens = learn.TOKEN.findall(article.body)
            assert tokens, article.slug
            assert set(tokens) <= set(fig.FIGURES), article.slug
            assert "[[fig:" not in learn.resolve_figures(article.body)


def test_an_unknown_figure_is_an_error_not_a_hole():
    with pytest.raises(KeyError):
        learn.resolve_figures("<p>[[fig:no-existe]]</p>")


def test_titles_and_descriptions_are_unique(routes):
    articles = [a for r in routes for a in r.articles]
    assert len({a.title for a in articles}) == len(articles)
    assert len({a.description for a in articles}) == len(articles)
    assert all(40 <= len(a.description) <= 200 for a in articles)


def test_every_article_file_is_in_the_tree_and_vice_versa(routes):
    on_disk = {(p.parent.name, p.stem) for p in learn.LEARN_DIR.glob("*/*.html")}
    in_tree = {(r.id, a.slug) for r in routes for a in r.articles}
    assert on_disk == in_tree


@pytest.mark.parametrize(
    "path",
    [
        "/aprender.html",
        "/aprender-acordes-intervalos.html",
        "/aprender-acordes-mayores-y-menores.html",
    ],
)
def test_the_pages_are_served_as_html_with_the_security_headers(client, path):
    response = client.get(path)
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/html")
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert client.head(path).content == b""


def test_unknown_learning_pages_are_404_with_no_body(client):
    for path in (
        "/aprender-acordes-nada.html",
        "/aprender-otra-ruta-intervalos.html",
        "/aprender/",
    ):
        response = client.get(path)
        assert response.status_code == 404 and response.content == b""


def test_the_hub_shows_both_routes_in_order_with_all_four_topics(client, routes):
    page = client.get("/aprender.html").text
    assert page.count("<details open>") == 2
    assert page.index("Básicos") < page.index("Acordes")
    for route in routes:
        for article in route.articles:
            assert f'href="{article.url}"' in page and article.title in page
    assert "Más rutas, pronto" in page and "<title>Aprender · Acordia</title>" in page


def test_an_article_has_breadcrumb_current_marker_and_prev_next(client, routes):
    first = routes[0].articles[0]  # el primero de todos
    page = client.get("/" + first.url).text
    assert 'aria-label="Migas de pan"' in page and "Tópico 1 de 2" in page
    assert page.count('aria-current="page"') == 2  # miga y árbol
    assert f'href="{routes[0].articles[1].url}" rel="next"' in page and 'rel="prev"' not in page
    last = client.get("/" + routes[1].articles[-1].url).text  # el último de todos
    assert f'href="{routes[1].articles[0].url}" rel="prev"' in last and 'rel="next"' not in last
    assert 'href="aprender.html">Volver al mapa' in last


def test_previous_and_next_follow_the_reading_order_across_routes(client, routes):
    end_of_basics, start_of_chords = routes[0].articles[-1], routes[1].articles[0]
    page = client.get("/" + end_of_basics.url).text
    assert f'href="{start_of_chords.url}" rel="next">{start_of_chords.title} (Acordes) →' in page
    page = client.get("/" + start_of_chords.url).text
    assert f'href="{end_of_basics.url}" rel="prev">← {end_of_basics.title} (Básicos)' in page


def test_internal_links_and_styles_of_the_learning_pages_resolve(client):
    pages = [
        client.get(p).text
        for p in (
            "/aprender.html",
            "/aprender-acordes-intervalos.html",
            "/aprender-acordes-mayores-y-menores.html",
        )
    ]
    for page in pages:
        for href in set(re.findall(r'(?:href|src)="([^"#:?]+\.(?:html|css|js))(?:#[^"]*)?"', page)):
            assert client.get("/" + href).status_code == 200, href


def test_the_learning_pages_load_nothing_new_from_outside(client):
    for path in ("/aprender.html", "/aprender-acordes-intervalos.html"):
        page = client.get(path).text
        hosts = set(re.findall(r'(?:href|src)="https?://([^/"]+)', page))
        assert hosts <= {"fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net"}, hosts
        assert "<style" not in page.split("<body>", 1)[0]  # estilos en archivo propio, no en línea


# ---- Básicos: clave americana, compás y pulso ----


def test_the_spanish_and_american_names_match_the_library_theory():
    from acordia_render.chordtheory import NATURAL

    assert list(fig.SPANISH) == ["C", "D", "E", "F", "G", "A", "B"]
    assert [fig.SPANISH[letter] for letter in fig.SPANISH] == [
        "Do",
        "Re",
        "Mi",
        "Fa",
        "Sol",
        "La",
        "Si",
    ]
    assert [NATURAL[letter] for letter in fig.SPANISH] == [0, 2, 4, 5, 7, 9, 11]  # una escala de Do


def test_every_written_chord_in_the_article_is_one_the_library_understands():
    for name, token in fig.CHORD_WRITING:
        chord = parse(token)
        assert chord is not None, token
        assert name.split()[0] in fig.SPANISH.values(), name  # empieza por el nombre en español
        assert fig.SPANISH[token[0]] == name.split()[0], (name, token)


def test_the_open_strings_in_letters_match_the_tuning():
    letters = [fig.note_at(string, 0) for string in fig.STRINGS]
    assert letters == ["E", "A", "D", "G", "B", "E"]  # la 1 se escribe «e» en el texto
    assert "<td class='ac-mono'>e</td>" in fig.open_strings_table()


def test_note_values_are_halves_and_the_bar_of_4_4_is_filled():
    assert [beats for _, _, beats in fig.NOTE_VALUES] == [4.0, 2.0, 1.0, 0.5, 0.25]
    for _, _, beats in fig.NOTE_VALUES:
        assert (4 / beats) * beats == 4  # n figuras iguales llenan el compás
    assert [fig.beats_text(b) for _, _, b in fig.NOTE_VALUES] == ["4", "2", "1", "1/2", "1/4"]


@pytest.mark.parametrize(("bpm", "seconds"), [(60, 1.0), (120, 0.5), (90, 2 / 3), (100, 0.6)])
def test_seconds_per_beat_is_sixty_over_bpm(bpm, seconds):
    assert fig.seconds_per_beat(bpm) == pytest.approx(seconds)


def test_the_meter_grids_have_the_right_number_of_beats_and_accents():
    html = fig.meter_grids()
    grids = {
        name: html.split(f"Pulsos del compás de {name}")[1].split("</ol>")[0]
        for name, _ in fig.METERS
    }
    assert grids["4/4"].count("ac-beat ") == 4 and grids["3/4"].count("ac-beat ") == 3
    assert grids["6/8"].count("ac-beat ") == 6
    for grid in grids.values():
        assert grid.count("ac-beat-strong") == 1  # un solo tiempo fuerte por compás
    assert grids["4/4"].count("ac-beat-mid") == 1 and grids["6/8"].count("ac-beat-mid") == 1
    assert grids["3/4"].count("ac-beat-mid") == 0


def test_the_intervals_article_points_to_clave_americana(routes):
    body = next(a for r in routes for a in r.articles if a.slug == "intervalos").body
    assert 'href="aprender-basicos-clave-americana.html"' in body

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


def test_the_first_route_is_acordes_with_the_two_first_topics_in_order(routes):
    assert [r.id for r in routes][0] == "acordes" and routes[0].title == "Acordes"
    assert [a.slug for a in routes[0].articles] == ["intervalos", "mayores-y-menores"]


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


def test_the_hub_shows_the_tree_with_acordes_open_and_both_topics(client, routes):
    page = client.get("/aprender.html").text
    assert "<details open>" in page and "Acordes" in page
    for article in routes[0].articles:
        assert f'href="{article.url}"' in page and article.title in page
    assert "Más rutas, pronto" in page and "<title>Aprender · Acordia</title>" in page


def test_an_article_has_breadcrumb_current_marker_and_prev_next(client, routes):
    first, second = routes[0].articles
    page = client.get("/" + first.url).text
    assert 'aria-label="Migas de pan"' in page and "Tópico 1 de 2" in page
    assert page.count('aria-current="page"') == 2  # miga y árbol
    assert f'href="{second.url}" rel="next"' in page and 'rel="prev"' not in page
    last = client.get("/" + second.url).text
    assert f'href="{first.url}" rel="prev"' in last and 'rel="next"' not in last
    assert 'href="aprender.html">Volver al mapa' in last
    assert f"<title>{first.title.replace('#', '#')} · Acordia</title>" in page


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

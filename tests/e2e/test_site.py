"""Las páginas propias del sitio en un navegador real: portada, Biblioteca y buscador, artistas,
pedidos, guías y las cabeceras de seguridad de la página de canción.

La página de canción en sí (metrónomo, guitarra, panel de acordes, niveles) es de la librería
saul-music-render y se prueba allá, en local (RD8). Aquí:

    uv run pytest -m e2e --browser chromium
    scripts/e2e-produccion.sh             (contra producción, cinco navegadores)
"""

import os
import re

import pytest
from playwright.sync_api import Page, expect

SONG = "/cancion-camara-lenta.html"  # 4/4 a 86 bpm


def set_options(page: Page, open_: bool = True) -> None:
    """En celular (<= 575 px) los controles secundarios están plegados bajo «Opciones» (S26): abre o
    cierra el grupo. En escritorio el botón no se ve y no hace nada."""
    button = page.locator("[data-ac-met-options]")
    if button.is_visible() and (button.get_attribute("aria-expanded") == "true") != open_:
        button.click()


GUITAR_OFF = 'try { localStorage.setItem("ac-guitar", "off"); } catch (e) {}'


@pytest.fixture
def song(page: Page, base_url: str) -> Page:
    """La canción con la guitarra apagada: desde S45 parte activa y, en el primer gesto, baja 61
    muestras; las pruebas que no son de sonido no deben competir con esa descarga (en el emulador
    de celular del CI tarda decenas de segundos)."""
    page.add_init_script(GUITAR_OFF)
    page.goto(base_url + SONG)
    set_options(page)
    return page


def test_song_page_has_no_console_errors_or_blocked_resources(page: Page, base_url: str):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.goto(base_url + SONG, wait_until="networkidle")
    # Sin red a las fuentes o a Bootstrap en CI no se puede exigir silencio total: solo errores
    # propios (script, CSP).
    own = [p for p in problems if "Content Security Policy" in p or "Uncaught" in p]
    assert own == []


def test_guides_entry_changes_shape_but_is_never_shown_twice(song: Page):
    strip = song.locator(".ac-met-strip [data-ac-met-guides]")
    set_options(song, False)
    help_button = song.locator(".ac-sticky-tools [data-ac-met-help]")
    # Arriba: solo la franja, antes de la barra fija; el botón corto está oculto.
    expect(strip).to_be_in_viewport()
    expect(help_button).to_be_hidden()
    assert song.evaluate(
        "document.querySelector('.ac-met-strip').compareDocumentPosition("
        "document.querySelector('.ac-sticky-tools')) & Node.DOCUMENT_POSITION_FOLLOWING"
    )
    # Al bajar: la franja sale de pantalla y aparece el botón corto, a la vista y en la barra fija.
    song.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    song.wait_for_timeout(300)
    expect(strip).not_to_be_in_viewport()
    expect(help_button).to_be_visible()
    expect(help_button).to_be_in_viewport()
    expect(help_button).to_have_attribute("href", re.compile(r"guias\.html\?tema=camara-lenta"))
    assert (
        song.locator(".ac-sticky-tools").bounding_box()["height"]
        < song.viewport_size["height"] * 0.35
    )
    # De vuelta arriba: la franja otra vez y el botón se oculta.
    song.evaluate("window.scrollTo(0, 0)")
    song.wait_for_timeout(300)
    expect(help_button).to_be_hidden()
    expect(strip).to_be_in_viewport()


def test_guides_collapse_lists_top_five_with_prices_and_links_to_the_guides_page(song: Page):
    panel = song.locator("#guias-panel")
    expect(panel).to_be_hidden()
    song.locator(".ac-met-strip [data-ac-met-guides]").click()
    expect(panel).to_have_class(re.compile(r"\bshow\b"))  # animación terminada
    rows = panel.locator(".ac-guide-row")
    assert 1 <= rows.count() <= 5
    expect(panel.get_by_text("/ clase").first).to_be_visible()
    expect(panel.get_by_text("Todo el repertorio").first).to_be_visible()
    link = panel.get_by_role("link", name=re.compile("^Ver las"))
    expect(link).to_have_attribute("href", re.compile(r"guias\.html\?tema=camara-lenta"))
    expect(panel).to_be_in_viewport()
    song.keyboard.press("Escape")
    expect(panel).to_be_hidden()


def test_guides_collapse_opens_from_the_scrolled_bar_without_moving_the_bars(song: Page):
    song.evaluate("window.scrollTo(0, 900)")
    help_button = song.locator("[data-ac-met-help]")
    expect(help_button).to_be_visible()
    first_bar = song.locator("#p-basico .ac-bar").first
    page_y = "el => el.getBoundingClientRect().top + window.scrollY"
    before = first_bar.evaluate(page_y)
    help_button.click()
    panel = song.locator("#guias-panel")
    expect(panel).to_have_class(re.compile(r"\bshow\b"))
    expect(panel).to_be_in_viewport()
    assert abs(first_bar.evaluate(page_y) - before) < 0.5  # flota: no empuja los compases
    song.locator("h1").click(force=True)  # tocar fuera lo cierra
    expect(panel).to_be_hidden()


def test_clicking_a_guide_goes_straight_to_their_card(song: Page):
    song.locator(".ac-met-strip [data-ac-met-guides]").click()
    panel = song.locator("#guias-panel")
    expect(panel).to_have_class(re.compile(r"\bshow\b"))
    row = panel.locator("a.ac-guide-row").first
    guide_id = row.get_attribute("href").split("#guia-")[1]
    row.click()
    expect(song).to_have_url(re.compile(rf"guias\.html\?tema=camara-lenta#guia-{guide_id}$"))
    card = song.locator(f"#guia-{guide_id}")
    expect(card).to_be_visible()
    expect(card).to_be_in_viewport()
    expect(card).to_have_class(re.compile("is-target"))


def test_unpublished_song_is_404(page: Page, base_url: str):
    # Depende del catálogo local (songs/): en producción ese tema puede estar publicado (S48).
    if os.environ.get("E2E_BASE_URL"):
        pytest.skip("solo en local: depende de qué temas trae songs/")
    # Petición directa: Firefox trata un 404 sin cuerpo como error de red al navegar.
    response = page.request.get(base_url + "/cancion-cantar-y-amar.html")
    assert response.status == 404


def test_library_card_opens_song(page: Page, base_url: str):
    page.goto(base_url + "/")
    page.locator('a[href="cancion-camara-lenta.html"]').first.click()
    expect(page).to_have_url(re.compile(r"/cancion-camara-lenta\.html$"))
    expect(page.locator("h1")).to_have_text("Cámara lenta")


def test_landing_search_filters_the_library_and_goes_to_the_artist(page: Page, base_url: str):
    page.goto(f"{base_url}/index.html")
    cards = page.locator("#biblioteca .row > .col:not(.ac-artist-head)")
    heads = page.locator("#biblioteca .ac-artist-head:visible")
    total = cards.count()
    page.fill("#buscar", "los tres")
    expect(heads).to_have_count(1)
    expect(heads).to_contain_text("Los Tres")
    assert 0 < page.locator("#biblioteca .row > .col:not(.ac-artist-head):visible").count() < total
    assert all(
        "Los Tres" in t
        for t in page.locator(
            "#biblioteca .row > .col:not(.ac-artist-head):visible p"
        ).all_inner_texts()
    )
    page.keyboard.press("Enter")  # envía el formulario: baja a la Biblioteca
    expect(heads).to_be_in_viewport()
    page.fill("#buscar", "DEJATE")  # sin tildes ni mayúsculas, por título
    expect(page.locator("#biblioteca .row > .col:not(.ac-artist-head):visible")).to_have_count(1)
    page.fill("#buscar", "zzzz")
    expect(page.locator("#sin-resultados")).to_be_visible()
    page.fill("#buscar", "")
    expect(cards).to_have_count(total)
    expect(page.locator("#sin-resultados")).to_be_hidden()


def test_library_search_is_shared_with_the_landing_and_stays_in_reach(page: Page, base_url: str):
    page.goto(f"{base_url}/index.html")
    cards = page.locator("#biblioteca .row > .col:not(.ac-artist-head):visible")
    total = cards.count()
    page.fill("#buscar", "bunkers")  # mientras se escribe arriba, la galería ya lo muestra
    expect(page.locator("#buscar-biblioteca")).to_have_value("bunkers")
    expect(page.locator("#lib-count")).to_have_text(re.compile(r"^\d+ de \d+ temas$"))
    page.keyboard.press("Enter")  # al buscar, arriba se vacía y la galería conserva el texto
    expect(page.locator("#buscar")).to_have_value("")
    expect(page.locator("#buscar-biblioteca")).to_have_value("bunkers")
    page.locator("#biblioteca .ac-artist-head:visible").scroll_into_view_if_needed()
    page.evaluate("window.scrollBy(0, 300)")
    expect(page.locator(".ac-lib-search")).to_be_in_viewport()  # sigue a mano al bajar
    page.fill("#buscar-biblioteca", "tres")  # y se puede cambiar sin volver al inicio
    expect(page.locator("#buscar")).to_have_value("")
    page.click("#lib-clear")
    expect(cards).to_have_count(total)
    expect(page.locator("#buscar")).to_have_value("")
    expect(page.locator("#lib-clear")).to_be_hidden()


def test_home_count_matches_the_linked_cards_of_the_library(page: Page, base_url: str):
    page.goto(f"{base_url}/")
    shown = page.locator(".ac-count strong").inner_text()
    linked = page.locator("#biblioteca a.card").count()
    assert shown == f"{linked} canciones disponibles"


def test_artists_page_links_open_outside_and_the_library_link_filters_by_artist(
    page: Page, base_url: str
):
    page.goto(f"{base_url}/artistas.html")
    external = page.locator("[data-ac-artist-card] ul a[target=_blank]")
    assert external.count() > 0
    for rel in external.evaluate_all("els => els.map(e => e.rel)"):
        assert "noopener" in rel and "noreferrer" in rel
    expect(page.locator("#los-bunkers .ac-artist-count")).to_contain_text("temas disponibles")
    page.locator("#los-bunkers .ac-artist-library").click()
    expect(page).to_have_url(re.compile(r"/index\.html\?q=Los%20Bunkers#biblioteca"))
    expect(page.locator("#buscar-biblioteca")).to_have_value("Los Bunkers")
    heads = page.locator("#biblioteca .ac-artist-head:visible")
    expect(heads).to_have_count(1)
    expect(heads).to_contain_text("Los Bunkers")
    expect(heads).to_be_in_viewport()


def test_artist_without_published_songs_says_coming_soon(page: Page, one_song_url: str):
    page.goto(f"{one_song_url}/artistas.html")
    expect(page.locator("#los-bunkers .ac-artist-count")).to_contain_text("Próximamente")
    expect(page.locator("#los-bunkers .ac-artist-library")).to_have_count(0)
    expect(page.locator("#javiera-mena .ac-artist-count")).to_contain_text("1 tema disponible")


def test_library_query_parameter_is_text_only(page: Page, base_url: str):
    page.goto(f"{base_url}/index.html?q=%3Cimg%20src%3Dx%20onerror%3Dwindow.__x%3D1%3E#biblioteca")
    expect(page.locator("#sin-resultados")).to_be_visible()
    assert page.evaluate("window.__x") is None


def test_artists_page_has_no_horizontal_scroll(page: Page, base_url: str):
    page.goto(f"{base_url}/artistas.html")
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0


def test_requests_demo_is_labelled_and_states_change_over_time(page: Page, base_url: str):
    page.clock.install()
    page.goto(f"{base_url}/pedidos.html")
    items = page.locator("[data-ac-requests] > li")
    expect(items).to_have_count(4)
    expect(page.locator("[data-ac-requests] .ac-demo-badge")).to_have_count(4)
    before = page.locator("[data-ac-requests] .ac-req-state").all_inner_texts()
    assert set(before) == {"Recibida", "En revisión", "En preparación", "Publicada"}
    page.clock.run_for(5100)
    after = page.locator("[data-ac-requests] .ac-req-state").all_inner_texts()
    assert after != before
    expect(page.locator("[data-ac-req-announce]")).to_contain_text("Pedido de ejemplo")
    for _ in range(12):  # tarde o temprano un pedido publicado sale y entra uno nuevo
        if "Nuevo pedido" in page.locator("[data-ac-req-announce]").inner_text():
            break
        page.clock.run_for(5000)
    expect(page.locator("[data-ac-req-announce]")).to_contain_text("Nuevo pedido de ejemplo")
    expect(items).to_have_count(4)


def test_requests_demo_respects_reduced_motion(page: Page, base_url: str):
    page.emulate_media(reduced_motion="reduce")
    page.clock.install()
    page.goto(f"{base_url}/pedidos.html")
    page.clock.run_for(5100)
    expect(page.locator(".ac-req-flash")).to_have_count(0)
    page.emulate_media(reduced_motion="no-preference")
    page.clock.run_for(5000)
    expect(page.locator(".ac-req-flash")).to_have_count(1)


def test_mock_forms_send_nothing_and_say_so(page: Page, base_url: str):
    sent = []
    page.on("request", lambda r: sent.append(r) if r.method != "GET" else None)
    page.goto(f"{base_url}/pedidos.html")
    forms = page.locator("form[data-ac-mock-form]")
    expect(forms).to_have_count(2)
    for i in range(2):
        form = forms.nth(i)
        form.locator("input[type=text], textarea").first.fill("texto de prueba")
        form.locator("button[type=submit]").click()
        expect(form.locator("[data-ac-mock-note]")).to_contain_text("no se envió ni se guardó nada")
    assert sent == []
    expect(page).to_have_url(re.compile(r"/pedidos\.html$"))


def test_requests_page_is_in_the_nav_and_fits_the_screen(page: Page, base_url: str):
    page.goto(f"{base_url}/index.html")
    assert page.locator("a[href='pedidos.html']").count() >= 1
    page.goto(f"{base_url}/pedidos.html")
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0

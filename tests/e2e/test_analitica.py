"""Analítica con consentimiento previo (S116, C51), en un navegador real.

Google se reemplaza por un doble: no sale nada a Internet. Se comprueba el orden: sin decisión
no hay ninguna petición a Google, aceptar la carga, y rechazar o retirar el permiso la detiene y
borra las cookies. Solo en local.

    uv run pytest tests/e2e/test_analitica.py --browser chromium
"""

import pytest
from playwright.sync_api import Page, expect

from musicsite.app import create_app

GOOGLE = "googletagmanager.com"


@pytest.fixture
def url(serve_local):
    return serve_local(create_app(analytics_hosts=("127.0.0.1",)))


def watch(page: Page, base: str) -> list[str]:
    """Anota cada petición a Google y la responde con un doble; el resto de Internet se corta."""
    calls: list[str] = []

    def route(r):
        if GOOGLE in r.request.url:
            calls.append(r.request.url)
            return r.fulfill(body="window.__gtagLoaded = true;", content_type="text/javascript")
        return r.abort()

    page.route(lambda u: not u.startswith(base), route)
    return calls


def gtag_loaded(page: Page) -> None:
    """Espera al doble de gtag.js (`wait_for_function` evalúa texto y la CSP lo prohíbe)."""
    for _ in range(60):
        if page.evaluate("window.__gtagLoaded === true"):
            return
        page.wait_for_timeout(50)
    raise AssertionError("gtag.js no se cargó")


def test_without_a_decision_nothing_is_loaded_from_google(page: Page, url: str):
    calls = watch(page, url)
    page.goto(url + "/")
    expect(page.get_by_role("dialog", name="Cookies")).to_be_visible()
    page.wait_for_timeout(500)
    assert calls == []
    assert page.evaluate("typeof window.dataLayer") == "undefined"


def test_accepting_loads_analytics_and_is_remembered(page: Page, url: str):
    calls = watch(page, url)
    page.goto(url + "/")
    page.get_by_role("button", name="Aceptar").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    gtag_loaded(page)
    assert len(calls) == 1 and "id=G-" in calls[0]
    page.reload()
    expect(page.get_by_role("dialog")).to_have_count(0)  # no vuelve a preguntar
    gtag_loaded(page)
    assert len(calls) == 2


def test_rejecting_never_loads_google_even_after_a_reload(page: Page, url: str):
    calls = watch(page, url)
    page.goto(url + "/")
    page.get_by_role("button", name="Rechazar").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    page.reload()
    expect(page.get_by_role("dialog")).to_have_count(0)
    page.wait_for_timeout(500)
    assert calls == []


def test_withdrawing_the_permission_clears_the_cookies(page: Page, url: str):
    watch(page, url)
    page.goto(url + "/")
    page.get_by_role("button", name="Aceptar").click()
    gtag_loaded(page)
    page.evaluate(
        "document.cookie = '_ga=GA1.1.1; path=/'; document.cookie = '_ga_ABC=GS1; path=/'"
    )
    page.get_by_role("link", name="Preferencias de cookies").click()
    page.get_by_role("button", name="Rechazar").click()
    assert "_ga" not in page.evaluate("document.cookie")
    assert (
        page.evaluate(
            "window['ga-disable-' + document.querySelector('script[data-id]').dataset.id]"
        )
        is True
    )
    page.reload()
    expect(page.get_by_role("dialog")).to_have_count(0)


def test_a_song_page_asks_too_and_the_footer_link_reopens_the_banner(page: Page, url: str):
    calls = watch(page, url)
    slug = page.request.get(url + "/songs.json").json()[0]["slug"]
    page.goto(f"{url}/cancion-{slug}.html")
    expect(page.get_by_role("dialog", name="Cookies")).to_be_visible()
    assert calls == []
    page.get_by_role("button", name="Rechazar").click()
    page.get_by_role("link", name="Preferencias de cookies").click()
    expect(page.get_by_role("dialog", name="Cookies")).to_be_visible()


@pytest.mark.parametrize("path", ["/mi-acordia.html", "/entrar.html", "/pedidos.html"])
def test_account_pages_are_never_measured(page: Page, url: str, path: str):
    calls = watch(page, url)
    page.goto(url + path)
    page.wait_for_timeout(300)
    expect(page.get_by_role("dialog", name="Cookies")).to_have_count(0)
    assert calls == []


def test_embedded_song_never_asks(page: Page, url: str):
    calls = watch(page, url)
    slug = page.request.get(url + "/songs.json").json()[0]["slug"]
    page.goto(f"{url}/cancion-{slug}.html?embed=1")
    page.wait_for_timeout(300)
    expect(page.get_by_role("dialog", name="Cookies")).to_have_count(0)
    assert calls == []


# Eventos de uso (S124): la librería avisa `acordia:uso` (RD56) y analitica.js lo envía
# solo con permiso.


def uso(page: Page, action: str, **detail) -> None:
    page.evaluate(
        "d => document.dispatchEvent(new CustomEvent('acordia:uso', { detail: d }))",
        {"action": action, **detail},
    )


def leave(page: Page) -> None:
    """Salir de la página envía la búsqueda pendiente sin esperar."""
    page.evaluate("window.dispatchEvent(new Event('pagehide'))")


def events(page: Page) -> list:
    return page.evaluate(
        "(window.dataLayer || []).filter(a => a[0] === 'event').map(a => [a[1], a[2] || null])"
    )


def accept(page: Page, url: str) -> list[str]:
    calls = watch(page, url)
    page.goto(url + "/")
    page.get_by_role("button", name="Aceptar").click()
    gtag_loaded(page)
    return calls


def test_usage_events_wait_for_consent(page: Page, url: str):
    calls = watch(page, url)
    page.goto(url + "/")
    uso(page, "play")
    assert page.evaluate("typeof window.dataLayer") == "undefined"
    page.get_by_role("button", name="Rechazar").click()
    uso(page, "play")
    uso(page, "search", term="camara", shown=1)
    leave(page)
    assert page.evaluate("typeof window.dataLayer") == "undefined"
    assert calls == []


def test_after_accepting_play_and_complete_are_sent(page: Page, url: str):
    accept(page, url)
    uso(page, "play")
    uso(page, "complete")
    uso(page, "otra-cosa")
    assert events(page) == [["song_play", None], ["song_complete", None]]


def test_a_search_is_sent_once_typing_stops_and_normalized(page: Page, url: str):
    accept(page, url)
    for term in ("Cá", "Cáma", "  Cámara   LENTA "):
        uso(page, "search", term=term, shown=1)
    assert events(page) == []  # todavía escribe
    page.wait_for_timeout(1800)
    assert events(page) == [["search", {"search_term": "camara lenta"}]]
    uso(page, "search", term="cámara lenta", shown=1)
    page.wait_for_timeout(1800)
    assert len(events(page)) == 1  # el mismo término no se repite en la visita


def test_short_or_personal_terms_are_never_sent_and_long_ones_are_cut(page: Page, url: str):
    accept(page, url)
    for term in ("a", "ana@correo.cl", "+56 9 1234 5678"):
        uso(page, "search", term=term, shown=0)
        leave(page)
    assert events(page) == []
    uso(page, "search", term="x" * 60, shown=0)
    leave(page)
    assert events(page) == [["search", {"search_term": "x" * 40}]]


def test_withdrawing_the_permission_stops_the_usage_events(page: Page, url: str):
    accept(page, url)
    uso(page, "play")
    page.get_by_role("link", name="Preferencias de cookies").click()
    page.get_by_role("button", name="Rechazar").click()
    uso(page, "play")
    assert events(page) == [["song_play", None]]


def test_a_team_browser_is_never_measured_until_unmarked(page: Page, url: str):
    calls = watch(page, url)
    page.goto(url + "/?interno=1")
    page.wait_for_timeout(300)
    expect(page.get_by_role("dialog", name="Cookies")).to_have_count(0)
    expect(page.get_by_role("link", name="Preferencias de cookies")).to_have_count(0)
    page.goto(url + "/guias.html")  # la marca queda en el navegador
    page.wait_for_timeout(300)
    expect(page.get_by_role("dialog", name="Cookies")).to_have_count(0)
    uso(page, "play")
    assert page.evaluate("typeof window.dataLayer") == "undefined"
    assert calls == []
    page.goto(url + "/?interno=0")
    expect(page.get_by_role("dialog", name="Cookies")).to_be_visible()


def test_marking_a_browser_that_had_accepted_stops_loading_google(page: Page, url: str):
    calls = accept(page, url)
    assert len(calls) == 1
    page.goto(url + "/?interno=1")
    page.wait_for_timeout(300)
    expect(page.get_by_role("dialog")).to_have_count(0)
    assert len(calls) == 1
    assert page.evaluate("typeof window.dataLayer") == "undefined"

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

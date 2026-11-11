"""«Aprender» (S65) en un navegador real: árbol de rutas, artículos y lectura en celular."""

import re

import pytest
from playwright.sync_api import Page, expect

HUB = "/aprender.html"
FIRST = "/aprender-acordes-intervalos.html"
SECOND = "/aprender-acordes-mayores-y-menores.html"
CLAVE = "/aprender-basicos-clave-americana.html"
COMPAS = "/aprender-basicos-compas-y-pulso.html"


def test_the_hub_shows_basicos_then_acordes_open_with_their_four_topics(page: Page, base_url: str):
    page.goto(base_url + HUB)
    expect(page.get_by_role("heading", level=1)).to_have_text("Rutas de aprendizaje")
    tree = page.locator(".ac-tree")
    expect(tree.locator("details")).to_have_count(2)
    expect(tree.locator("details").first).to_have_attribute("open", "")
    expect(tree.locator("summary").first).to_contain_text("Básicos")
    expect(tree.locator("summary").nth(1)).to_contain_text("Acordes")
    expect(tree.locator("a.ac-tree-link")).to_have_count(4)
    expect(tree.get_by_text("Más rutas, pronto")).to_be_visible()


def test_navigating_the_route_with_the_tree_and_prev_next(page: Page, base_url: str):
    page.goto(base_url + HUB)
    page.locator("a.ac-tree-link", has_text="Intervalos con # y b").click()
    expect(page).to_have_url(re.compile(re.escape(FIRST) + "$"))
    expect(page.get_by_role("heading", level=1)).to_contain_text("Intervalos con # y b")
    expect(page.locator(".ac-article svg").first).to_be_visible()
    expect(page.locator('.ac-tree [aria-current="page"]')).to_contain_text("Intervalos")
    page.locator('a[rel="next"]').click()
    expect(page).to_have_url(re.compile(re.escape(SECOND) + "$"))
    expect(page.locator('.ac-tree [aria-current="page"]')).to_contain_text(
        "acordes mayores y menores"
    )
    page.locator('a[rel="prev"]').click()
    expect(page).to_have_url(re.compile(re.escape(FIRST) + "$"))


@pytest.mark.parametrize("path", [HUB, CLAVE, COMPAS, FIRST, SECOND])
@pytest.mark.parametrize("width", [360, 1100])
def test_pages_never_scroll_sideways(page: Page, base_url: str, path: str, width: int):
    page.set_viewport_size({"width": width, "height": 800})
    page.goto(base_url + path)
    assert page.evaluate("document.documentElement.scrollWidth") <= width


@pytest.mark.parametrize("path", [HUB, CLAVE, COMPAS, FIRST, SECOND])
def test_pages_have_no_own_console_errors_or_blocked_resources(page: Page, base_url: str, path):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.goto(base_url + path, wait_until="networkidle")
    assert [p for p in problems if "Content Security Policy" in p or "Uncaught" in p] == []


def test_the_articles_read_without_javascript(browser, base_url: str):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(base_url + SECOND)
    expect(page.get_by_role("heading", level=1)).to_contain_text("acordes mayores y menores")
    expect(page.locator(".ac-article svg").first).to_be_visible()
    # en un artículo solo la ruta actual está abierta: su enlace actual se ve sin JavaScript
    expect(page.locator('.ac-tree [aria-current="page"]')).to_be_visible()
    context.close()


def test_a_figure_is_readable_in_the_light_theme_too(page: Page, base_url: str):
    page.add_init_script('try { localStorage.setItem("acordia-tema", "light"); } catch (e) {}')
    page.goto(base_url + SECOND)
    expect(page.locator("html")).to_have_attribute("data-bs-theme", "light")
    expect(page.locator(".ac-article .ac-cd").first).to_be_visible()


def test_the_song_page_learn_button_opens_the_hub_in_another_tab(page: Page, base_url: str):
    page.add_init_script('try { localStorage.setItem("ac-guitar", "off"); } catch (e) {}')
    page.goto(base_url + "/cancion-camara-lenta.html")
    link = page.locator("[data-ac-util-learn]")
    expect(link).to_be_visible()
    with page.context.expect_page() as opened:
        link.click()
    tab = opened.value
    tab.wait_for_load_state()
    assert tab.url.endswith(HUB)
    expect(tab.get_by_role("heading", level=1)).to_have_text("Rutas de aprendizaje")
    assert page.url.endswith("/cancion-camara-lenta.html")  # la canción sigue abierta


def test_reading_order_continues_from_basicos_into_acordes(page: Page, base_url: str):
    page.goto(base_url + CLAVE)
    page.locator('a[rel="next"]').click()
    expect(page).to_have_url(re.compile(re.escape(COMPAS) + "$"))
    expect(page.locator(".ac-beats").first).to_be_visible()  # las cuadrículas de pulsos
    page.locator('a[rel="next"]').click()
    expect(page).to_have_url(re.compile(re.escape(FIRST) + "$"))
    page.locator('a[rel="prev"]').click()
    expect(page).to_have_url(re.compile(re.escape(COMPAS) + "$"))

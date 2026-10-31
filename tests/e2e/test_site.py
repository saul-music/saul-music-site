"""El sitio en un navegador real. Se ejecuta por navegador y dispositivo (ver el pipeline):

    uv run pytest -m e2e --browser chromium
    uv run pytest -m e2e --browser webkit --device "iPhone 14"

El sonido no se puede comprobar aquí: solo que el reloj de audio arranca y el pulso se mueve.
"""

import re

import pytest
from playwright.sync_api import Page, expect

SONG = "/cancion-camara-lenta.html"  # 4/4 a 86 bpm
SONG_BPM = 86


@pytest.fixture
def song(page: Page, base_url: str) -> Page:
    page.goto(base_url + SONG)
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


def test_metronome_starts_at_song_tempo(song: Page):
    expect(song.locator("[data-ac-met-bpm]")).to_have_value(str(SONG_BPM))
    expect(song.locator("[data-ac-met-range]")).to_have_value(str(SONG_BPM))
    expect(song.locator("[data-ac-met-dots] span")).to_have_count(4)
    expect(song.locator("[data-ac-met-toggle]")).to_have_attribute("aria-pressed", "false")


def test_metronome_controls_stay_in_sync_and_clamp(song: Page):
    bpm = song.locator("[data-ac-met-bpm]")
    rng = song.locator("[data-ac-met-range]")
    song.locator('[data-ac-met-step="1"]').click()
    expect(bpm).to_have_value(str(SONG_BPM + 1))
    expect(rng).to_have_value(str(SONG_BPM + 1))
    song.locator('[data-ac-met-step="-1"]').click(click_count=3)
    expect(bpm).to_have_value(str(SONG_BPM - 2))
    bpm.fill("999")
    bpm.blur()
    expect(bpm).to_have_value("240")
    expect(rng).to_have_value("240")
    bpm.fill("5")
    bpm.blur()
    expect(bpm).to_have_value("30")
    song.locator("[data-ac-met-reset]").click()
    expect(bpm).to_have_value(str(SONG_BPM))


def test_metronome_plays_pulses_and_stops(song: Page):
    toggle = song.locator("[data-ac-met-toggle]")
    toggle.click()
    expect(toggle).to_have_attribute("aria-pressed", "true")
    expect(toggle).to_have_text("Detener")
    # Con el metrónomo sonando, cambiar el bpm no lo corta.
    song.locator('[data-ac-met-step="1"]').click()
    expect(toggle).to_have_attribute("aria-pressed", "true")
    expect(song.locator(".ac-met-dot.is-on")).to_have_count(1, timeout=5000)
    toggle.click()
    expect(toggle).to_have_attribute("aria-pressed", "false")
    expect(toggle).to_have_text("Reproducir")
    expect(song.locator(".ac-met-dot.is-on")).to_have_count(0)


def test_difficulty_tabs_switch(song: Page):
    expect(song.locator("#p-basico")).to_be_visible()
    song.locator("#t-intermedio").click()
    expect(song.locator("#p-intermedio")).to_be_visible()
    expect(song.locator("#p-basico")).to_be_hidden()


def test_theme_toggle_changes_theme(song: Page):
    html = song.locator("html")
    before = html.get_attribute("data-bs-theme")
    toggle = song.locator("[data-ac-theme-toggle]:visible").first
    if not toggle.is_visible():
        song.locator(".navbar-toggler").click()
    toggle.click()
    expect(html).not_to_have_attribute("data-bs-theme", before)


def test_no_horizontal_scroll(song: Page):
    overflow = song.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0


def test_unpublished_song_is_404(page: Page, base_url: str):
    # Petición directa: Firefox trata un 404 sin cuerpo como error de red al navegar.
    response = page.request.get(base_url + "/cancion-el-errante.html")
    assert response.status == 404


def test_library_card_opens_song(page: Page, base_url: str):
    page.goto(base_url + "/")
    page.locator('a[href="cancion-camara-lenta.html"]').first.click()
    expect(page).to_have_url(re.compile(r"/cancion-camara-lenta\.html$"))
    expect(page.locator("h1")).to_have_text("Cámara lenta")

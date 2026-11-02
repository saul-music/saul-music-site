"""El sitio en un navegador real. Se ejecuta por navegador y dispositivo (ver el pipeline):

    uv run pytest -m e2e --browser chromium
    uv run pytest -m e2e --browser webkit --device "iPhone 14"

Los altavoces no se pueden oír aquí: la lógica va contra un AudioContext simulado y
test_audio_real.py comprueba, con un sink nulo de PulseAudio en el CI, que el contexto real corre
y emite señal. Que suene en Safari/iPhone (interruptor de silencio) se comprueba de oído.
"""

import re

import pytest
from playwright.sync_api import Page, expect

SONG = "/cancion-camara-lenta.html"  # 4/4 a 86 bpm
SONG_BPM = 86


SAFARI_AUDIO_STUB = """
(() => {
  // Imita a Safari: el contexto nace suspendido, el reloj no corre y resume() tarda.
  window.__clicks = 0; window.__early = 0;
  class Ctx {
    constructor() { this.state = "suspended"; this._t = 0; this.destination = {}; }
    get currentTime() { return this._t; }
    resume() {
      return new Promise((ok) => setTimeout(() => {
        this.state = "running";
        this._t0 = performance.now();
        this._tick = setInterval(() => { this._t = (performance.now() - this._t0) / 1000; }, 5);
        ok();
      }, 300));
    }
    createGain() {
      const p = { setValueAtTime() {}, exponentialRampToValueAtTime() {} };
      return { gain: p, connect() {} };
    }
    createOscillator() {
      const c = this;
      return { frequency: {}, connect() {}, stop() {},
        start() { window.__clicks++; if (c.state !== "running") window.__early++; } };
    }
  }
  window.AudioContext = Ctx;
})();
"""


@pytest.fixture
def song_audio(page: Page, base_url: str) -> Page:
    """Canción con un AudioContext simulado: el pulso no depende de que el runner tenga audio."""
    page.add_init_script(SAFARI_AUDIO_STUB)
    page.goto(base_url + SONG)
    return page


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


def test_metronome_plays_pulses_and_stops(song_audio: Page):
    song = song_audio
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


def test_playhead_walks_the_bars_and_counts_repetitions(song_audio: Page):
    song = song_audio
    song.locator("[data-ac-met-range]").fill("240")  # ~0,25 s por pulso
    song.locator("[data-ac-met-toggle]").click()
    current = song.locator("#p-basico .ac-bar.is-current")
    expect(current).to_have_count(1, timeout=5000)
    first = current.evaluate("el => Array.from(el.closest('.ac-bars').children).indexOf(el)")
    assert first == 0
    # La sección Intro es × 2: aparece "1 / 2" y luego "2 / 2".
    counter = song.locator("#p-basico .ac-rep-count").first
    expect(counter).to_have_text("1 / 2", timeout=5000)
    expect(counter).to_have_text("2 / 2", timeout=8000)
    # Pasa a la sección siguiente: el cursor sigue siendo único y el contador de Intro desaparece.
    expect(song.locator("#p-basico .ac-bar.is-current")).to_have_count(1)
    expect(song.locator("#p-basico .ac-rep-count").first).not_to_have_text("2 / 2", timeout=8000)
    song.locator("[data-ac-met-toggle]").click()
    expect(song.locator(".ac-bar.is-current")).to_have_count(0)
    expect(song.locator(".ac-rep-count")).to_have_count(0)


def test_metronome_stays_visible_next_to_the_bars_and_guides_stay_on_top(song: Page):
    tools = song.locator(".ac-sticky-tools")
    guides = song.get_by_role("link", name="Ver guías")
    # Las guías van arriba, antes del metrónomo y de los compases.
    assert song.evaluate(
        "document.querySelector('aside[aria-label]').compareDocumentPosition("
        "document.querySelector('.ac-sticky-tools')) & Node.DOCUMENT_POSITION_FOLLOWING"
    )
    song.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    song.wait_for_timeout(200)
    box = tools.bounding_box()
    viewport_h = song.viewport_size["height"]
    assert box is not None and 0 <= box["y"] < viewport_h / 2
    assert box["height"] < viewport_h * 0.3
    expect(song.locator("[data-ac-met-toggle]")).to_be_in_viewport()
    expect(guides).not_to_be_in_viewport()  # las guías no son fijas


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


def test_metronome_waits_for_running_context_like_safari(page: Page, base_url: str):
    page.add_init_script(SAFARI_AUDIO_STUB)
    page.goto(base_url + SONG)
    page.locator("[data-ac-met-toggle]").click()
    page.wait_for_timeout(150)
    # Mientras el contexto sigue suspendido no se agenda ningún clic.
    assert page.evaluate("window.__clicks") == 0
    for _ in range(50):
        if page.evaluate("window.__clicks") >= 2:
            break
        page.wait_for_timeout(100)
    assert page.evaluate("window.__clicks") >= 2
    assert page.evaluate("window.__early") == 0

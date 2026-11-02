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
    expect(toggle).to_contain_text("Detener")
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


def test_metronome_stays_visible_next_to_the_bars(song: Page):
    tools = song.locator(".ac-sticky-tools")
    song.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    song.wait_for_timeout(200)
    box = tools.bounding_box()
    viewport_h = song.viewport_size["height"]
    assert box is not None and 0 <= box["y"] < viewport_h / 2
    assert box["height"] < viewport_h * 0.3
    expect(song.locator("[data-ac-met-toggle]")).to_be_in_viewport()


def test_guides_entry_changes_shape_but_is_never_shown_twice(song: Page):
    strip = song.locator(".ac-met-strip [data-ac-met-guides]")
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
        < song.viewport_size["height"] * 0.3
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


def test_title_and_artist_stay_visible_while_scrolling(song: Page):
    strip = song.locator("[data-ac-sticky-title]")
    expect(strip).to_be_hidden()  # arriba ya se ve el encabezado
    song.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    expect(strip).to_be_visible()
    expect(strip).to_contain_text("Cámara lenta")
    expect(strip).to_contain_text("Javiera Mena")
    expect(strip).to_be_in_viewport()
    song.evaluate("window.scrollTo(0, 0)")
    expect(strip).to_be_hidden()


def test_chord_opens_guitar_diagram_with_tab_then_keyboard_and_closes(song: Page):
    chord = song.locator("#p-basico .ac-chord-btn").first
    panel = song.locator(".ac-chord-panel")
    expect(panel).to_have_count(0)
    chord.click()
    expect(panel).to_be_visible()
    expect(panel.locator("svg[aria-label^='Acorde']")).to_be_visible()
    expect(panel.locator(".ac-cp-tab")).to_contain_text("E A D G B e")
    next_form = panel.locator(".ac-cp-next")
    expect(next_form).to_have_text(re.compile(r"^Otra forma \(1.\d+\)$"))
    first = panel.locator(".ac-cp-tab").inner_text()
    next_form.click()
    assert panel.locator(".ac-cp-tab").inner_text() != first
    panel.get_by_role("button", name="Teclado").click()
    expect(panel.locator("svg[aria-label^='Teclas']")).to_be_visible()
    expect(panel.locator("svg .key.on")).not_to_have_count(0)
    assert song.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
    box = panel.bounding_box()
    assert 0 <= box["x"] and box["x"] + box["width"] <= song.viewport_size["width"] + 1
    song.keyboard.press("Escape")
    expect(panel).to_be_hidden()
    chord.click()  # recuerda el instrumento elegido
    expect(panel.locator("svg[aria-label^='Teclas']")).to_be_visible()


def test_tapping_outside_closes_the_chord_panel(song: Page):
    song.locator("#p-basico .ac-chord-btn").nth(1).click()
    panel = song.locator(".ac-chord-panel")
    expect(panel).to_be_visible()
    song.locator("h1").click(force=True)
    expect(panel).to_be_hidden()


def _clicks(page: Page) -> int:
    return page.evaluate("window.__clicks")


def test_mute_keeps_the_tempo_and_the_cursor_without_any_sound(song_audio: Page):
    song = song_audio
    song.locator("[data-ac-met-range]").fill("240")
    mute = song.locator("[data-ac-met-mute]")
    mute.click()
    expect(mute).to_have_attribute("aria-pressed", "true")
    song.locator("[data-ac-met-toggle]").click()
    expect(song.locator("#p-basico .ac-bar.is-current")).to_have_count(1, timeout=5000)
    expect(song.locator("#p-basico .ac-rep-count").first).to_have_text("2 / 2", timeout=8000)
    assert _clicks(song) == 0


def test_toggling_sound_while_playing_does_not_stop_it(song_audio: Page):
    song = song_audio
    song.locator("[data-ac-met-range]").fill("240")
    toggle = song.locator("[data-ac-met-toggle]")
    toggle.click()
    for _ in range(40):
        if _clicks(song) >= 2:
            break
        song.wait_for_timeout(100)
    assert _clicks(song) >= 2
    mute = song.locator("[data-ac-met-mute]")
    mute.click()  # a silencio en marcha
    song.wait_for_timeout(300)
    frozen = _clicks(song)
    song.wait_for_timeout(700)
    assert _clicks(song) == frozen
    expect(toggle).to_have_attribute("aria-pressed", "true")
    expect(song.locator("#p-basico .ac-bar.is-current")).to_have_count(1)
    mute.click()  # de vuelta con sonido
    for _ in range(40):
        if _clicks(song) > frozen:
            break
        song.wait_for_timeout(100)
    assert _clicks(song) > frozen


def test_mute_choice_is_remembered(song_audio: Page, base_url: str):
    song_audio.locator("[data-ac-met-mute]").click()
    song_audio.goto(base_url + SONG)
    expect(song_audio.locator("[data-ac-met-mute]")).to_have_attribute("aria-pressed", "true")


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


def test_count_in_precedes_the_playhead_and_can_be_turned_off(song_audio: Page):
    song = song_audio
    song.locator("[data-ac-met-range]").fill("240")  # 0,25 s por pulso: la cuenta dura ~1 s
    count_btn = song.locator("[data-ac-met-countin]")
    expect(count_btn).to_have_attribute("aria-pressed", "true")
    song.locator("[data-ac-met-toggle]").click()
    expect(song.locator(".ac-met-dot.is-on")).to_have_count(1, timeout=2000)
    assert song.locator(".ac-bar.is-current").count() == 0  # aún cuenta, el cursor no empieza
    expect(song.locator(".ac-bar.is-current")).to_have_count(1, timeout=5000)
    assert song.evaluate("window.__clicks") >= 5  # 4 de cuenta + al menos el primer pulso
    song.locator("[data-ac-met-toggle]").click()
    # Desactivada: el cursor aparece sin esperar la cuenta, y la elección sobrevive a recargar.
    count_btn.click()
    expect(count_btn).to_have_attribute("aria-pressed", "false")
    song.reload()
    expect(song.locator("[data-ac-met-countin]")).to_have_attribute("aria-pressed", "false")
    song.locator("[data-ac-met-range]").fill("240")
    song.locator("[data-ac-met-toggle]").click()
    expect(song.locator(".ac-bar.is-current")).to_have_count(1, timeout=700)


def test_beat_flash_follows_the_chord_inside_a_split_bar(song_audio: Page):
    song = song_audio
    song.locator("#t-intermedio").click()
    pane = song.locator("#p-intermedio")
    expect(pane).to_be_visible()
    # Compases que preceden al primero partido, con las repeticiones de cada sección.
    before = pane.evaluate(
        """el => { let n = 0; for (const g of el.querySelectorAll('.ac-bars')) {
          const reps = +g.dataset.reps || 1, bars = [...g.querySelectorAll('.ac-bar')];
          const i = bars.findIndex(b => b.classList.contains('is-split'));
          if (i >= 0) return n + i; n += reps * bars.length; } return -1; }"""
    )
    assert before >= 0
    song.locator("[data-ac-met-countin]").click()  # sin cuenta: el compás 1 empieza ya
    song.locator("[data-ac-met-range]").fill("240")  # 0,25 s por pulso, 1 s por compás
    song.evaluate(
        """() => { window.__flash = [];
          new MutationObserver(ms => ms.forEach(m => {
            const t = m.target;
            if (t.classList.contains('ac-part') && t.classList.contains('is-beat')
                && !(m.oldValue || '').includes('is-beat')) {
              const parts = [...t.parentElement.querySelectorAll('.ac-part')];
              const g = t.closest('.ac-bars');
              window.__flash.push({ bar: [...g.children].indexOf(t.parentElement)
                + ':' + g.previousElementSibling?.textContent,
                part: parts.indexOf(t), of: parts.length });
            } }))
          .observe(document.querySelector('#p-intermedio'),
            { subtree: true, attributes: true, attributeFilter: ['class'],
              attributeOldValue: true }); }"""
    )
    song.locator("[data-ac-met-toggle]").click()
    song.wait_for_function("() => window.__flash.length >= 4", timeout=(before + 4) * 1000 + 8000)
    song.locator("[data-ac-met-toggle]").click()
    flash = song.evaluate("window.__flash")
    # Primer compás partido (4/4): cada pulso ilumina una parte y las partes se recorren en orden,
    # sin volver atrás ni saltarse ninguna dentro del compás.
    first = flash[:4]
    assert len({f["bar"] for f in first}) == 1
    order = [f["part"] for f in first]
    assert order == sorted(order) and order[0] == 0 and order[-1] == first[0]["of"] - 1
    # Al detener no queda nada iluminado.
    expect(song.locator(".ac-part.is-beat, .ac-bar.is-beat")).to_have_count(0, timeout=2000)


def test_playback_starts_from_the_flagged_bar_and_keeps_it_centered(song_audio: Page):
    song = song_audio
    song.locator("[data-ac-met-countin]").click()  # sin cuenta: el cursor arranca ya
    song.locator("[data-ac-met-range]").fill("240")
    bars = song.locator("#p-basico .ac-bar")
    n = bars.count()
    target = bars.nth(n // 2)
    flag = target.locator(".ac-start-flag")
    target.scroll_into_view_if_needed()
    flag.click()
    expect(flag).to_have_attribute("aria-pressed", "true")
    expect(target).to_have_class(re.compile(r"\bis-start\b"))
    # Una sola marca por página: marcar otro compás mueve la bandera.
    other = bars.nth(0).locator(".ac-start-flag")
    other.click()
    expect(flag).to_have_attribute("aria-pressed", "false")
    other.click()  # tocar la misma bandera la quita
    expect(other).to_have_attribute("aria-pressed", "false")
    target.scroll_into_view_if_needed()
    flag.click()
    song.evaluate("window.scrollTo(0, 0)")
    song.locator("[data-ac-met-toggle]").click()
    # El primer compás en sonar es el marcado (no el primero de la canción).
    expect(target).to_have_class(re.compile(r"\bis-current\b"), timeout=3000)
    assert "is-current" not in (bars.nth(0).get_attribute("class") or "")

    def off_center() -> float:
        return song.evaluate(
            """() => {
              const tools = document.querySelector('.ac-sticky-tools');
              const bottom = tools.getBoundingClientRect().bottom;
              const t = bottom + 12;
              const cur = document.querySelector('#p-basico .ac-bar.is-current');
              const r = cur.getBoundingClientRect();
              return Math.abs((r.top + r.height / 2) - (t + (innerHeight - t) / 2));
            }"""
        )

    for _ in range(40):  # el scroll suave tarda un poco en llegar
        if off_center() < 40:
            break
        song.wait_for_timeout(100)
    assert off_center() < 40
    song.locator("[data-ac-met-toggle]").click()
    # Tras detener, la marca sigue: reproducir otra vez parte del mismo compás.
    expect(target).to_have_class(re.compile(r"\bis-start\b"))


def test_count_in_shows_numbers_while_it_counts(song_audio: Page):
    song = song_audio
    song.locator("[data-ac-met-range]").fill("120")  # 0,5 s por pulso: la cuenta dura ~2 s
    toggle = song.locator("[data-ac-met-toggle]")
    count = song.locator("[data-ac-met-count]")
    tools = song.locator(".ac-sticky-tools")
    expect(count.locator("span")).to_have_count(0)
    expect(toggle).to_have_text("Reproducir")
    rest = tools.bounding_box()["height"]
    toggle.click()
    expect(count.locator("span.is-on")).to_have_count(1, timeout=3000)
    seen = set()
    for _ in range(30):
        on = count.locator("span.is-on")
        if on.count():
            seen.add(on.first.inner_text())
        song.wait_for_timeout(50)
    assert {"1", "2", "3", "4"} <= seen
    assert tools.bounding_box()["height"] <= rest + 1  # la barra no crece
    expect(count.locator("span")).to_have_count(0, timeout=3000)  # empieza el compás 1
    expect(song.locator(".ac-bar.is-current")).to_have_count(1, timeout=3000)
    toggle.click()
    song.locator("[data-ac-met-countin]").click()  # sin cuenta, no aparece
    toggle.click()
    song.wait_for_timeout(300)
    expect(count.locator("span")).to_have_count(0)

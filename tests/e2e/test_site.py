"""El sitio en un navegador real. Se ejecuta por navegador y dispositivo (ver el pipeline):

    uv run pytest -m e2e --browser chromium
    uv run pytest -m e2e --browser webkit --device "iPhone 14"

Los altavoces no se pueden oír aquí: la lógica va contra un AudioContext simulado y
test_audio_real.py comprueba, con un sink nulo de PulseAudio en el CI, que el contexto real corre
y emite señal. Que suene en Safari/iPhone (interruptor de silencio) se comprueba de oído.
"""

import os
import re
from pathlib import Path

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


# Además del contexto simulado, decodificar «funciona»: así la guitarra puede declararse lista.
DECODE_STUB = """
(() => {
  window.AudioContext.prototype.decodeAudioData = () => Promise.resolve({ duration: 1 });
})();
"""


def set_options(page: Page, open_: bool = True) -> None:
    """En celular (<= 575 px) los controles secundarios están plegados bajo «Opciones» (S26): abre o
    cierra el grupo. En escritorio el botón no se ve y no hace nada."""
    button = page.locator("[data-ac-met-options]")
    if button.is_visible() and (button.get_attribute("aria-expanded") == "true") != open_:
        button.click()


@pytest.fixture
def song_audio(page: Page, base_url: str) -> Page:
    """Canción con un AudioContext simulado: el pulso no depende de que el runner tenga audio.
    La guitarra va apagada: estas pruebas son del pulso, no de la carga de muestras."""
    page.add_init_script(SAFARI_AUDIO_STUB)
    page.add_init_script(GUITAR_OFF)
    page.goto(base_url + SONG)
    set_options(page)
    return page


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


@pytest.fixture
def song_sound(page: Page, base_url: str) -> Page:
    """La canción tal como la ve una persona: con la guitarra activa por defecto."""
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
    set_options(song, False)  # la altura máxima se mide con las opciones plegadas
    tools = song.locator(".ac-sticky-tools")
    song.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    song.wait_for_timeout(200)
    box = tools.bounding_box()
    viewport_h = song.viewport_size["height"]
    assert box is not None and 0 <= box["y"] < viewport_h / 2
    assert box["height"] < viewport_h * 0.35  # incluye la fila del selector de nivel (S15)
    expect(song.locator("[data-ac-met-toggle]")).to_be_in_viewport()


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


def test_theme_default_shape_first_and_own_version_shape_beats_it(page: Page, shapes_url: str):
    page.goto(shapes_url + SONG)
    panel = page.locator(".ac-chord-panel")
    page.locator("#p-basico .ac-chord-btn[data-chord='E']").first.click()
    expect(panel.locator(".ac-cp-tab")).to_contain_text("x 7 9 9 9 7")
    expect(panel.locator(".ac-chip-ok")).to_have_text("Forma de este tema")
    panel.locator(".ac-cp-next").click()  # se puede navegar por las demás
    expect(panel.locator(".ac-cp-tab")).not_to_contain_text("x 7 9 9 9 7")
    expect(panel.locator(".ac-chip-ok")).to_be_hidden()
    page.keyboard.press("Escape")
    page.get_by_role("tab", name=re.compile("Intermedio")).click()
    page.locator("#p-intermedio .ac-chord-btn[data-chord='E']").first.click()
    expect(panel.locator(".ac-cp-tab")).to_contain_text("x 7 9 9 9 7")  # el tema vale en todo nivel
    page.keyboard.press("Escape")
    page.locator("#p-intermedio .ac-chord-btn[data-chord='Emaj7']").first.click()
    expect(panel.locator(".ac-cp-tab")).to_contain_text("x 7 9 8 9 7")
    expect(panel.locator(".ac-chip-ok")).to_have_text("Forma de esta versión")


def test_summary_is_folded_and_draws_every_chord_of_its_tab(page: Page, shapes_url: str):
    page.goto(shapes_url + SONG)
    for mode in ("basico", "intermedio"):
        if mode == "intermedio":
            page.get_by_role("tab", name=re.compile("Intermedio")).click()
        pane = page.locator(f"#p-{mode}")
        details = pane.locator("details.ac-summary")
        expect(details).to_have_count(1)
        assert details.evaluate("d => !d.open")
        expect(details.locator(".ac-sum-item")).to_have_count(0)  # no se dibuja hasta abrirlo
        names = pane.evaluate(
            "p => [...new Set([...p.querySelectorAll('.ac-chord-btn')].map(b => b.dataset.chord))]"
        )
        # Con teclado (Enter sobre el resumen): accesible y sin depender de qué barra fija lo tape
        details.locator("summary").focus()
        page.keyboard.press("Enter")
        items = details.locator(".ac-sum-item")
        expect(items).to_have_count(len(names))
        expect(details.locator("svg[aria-label^='Teclas']")).to_have_count(len(names))
        expect(details.locator(".ac-sum-guitar svg")).to_have_count(len(names))
        # E: forma por defecto del tema (traste 7), no la estándar (sin número)
        e_item = items.filter(has=page.locator(".ac-sum-name", has_text=re.compile(r"^E$")))
        expect(e_item.locator("svg text")).to_have_text("7")
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        )
        box = details.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= page.viewport_size["width"] + 1


def test_advanced_shows_intermedio_bars_plus_section_extras(page: Page, advanced_url: str):
    page.goto(advanced_url + SONG)
    page.get_by_role("tab", name=re.compile("Avanzado")).click()
    pane = page.locator("#p-avanzado")
    expect(pane).to_be_visible()
    inter = page.locator("#p-intermedio")
    assert pane.locator(".ac-bar").count() == inter.locator(".ac-bar").count() > 0
    expect(pane.locator(".ac-tab")).to_contain_text("e|--0--|")
    expect(pane.locator(".ac-arrangement")).to_contain_text("Rasgueo suave")
    expect(pane.locator(".ac-tip-title", has_text="Sonido")).to_have_count(1)
    expect(inter.locator(".ac-tab")).to_have_count(0)
    expect(pane.locator("details.ac-summary")).to_have_count(1)
    pane.locator("details.ac-summary summary").focus()
    page.keyboard.press("Enter")
    expect(pane.locator(".ac-sum-item").first).to_be_visible()
    pane.locator(".ac-chord-btn[data-chord='Emaj7']").first.click()
    expect(page.locator(".ac-chord-panel")).to_be_visible()
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def test_barre_rule_shows_the_nearest_position_first(page: Page, base_url: str):
    """Regla de cejilla (S27): en el panel, la primera forma de un acorde que empieza desde el
    traste 3 es la de traste base más bajo (los datos de la página ya vienen ordenados)."""
    page.goto(base_url + SONG)
    bad = page.evaluate(
        """() => {
          const data = JSON.parse(document.getElementById('acordes-data').textContent);
          const base = f => Math.min(...f.frets.filter(x => x > 0), 99);
          return Object.entries(data.chords).filter(([, c]) => c.guitar).filter(([, c]) => {
            const b = c.guitar.map(g => base(g));
            return b[0] >= 3 && b[0] !== Math.min(...b);
          }).map(([n]) => n);
        }"""
    )
    assert bad == []


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
    set_options(song_audio)
    expect(song_audio.locator("[data-ac-met-mute]")).to_have_attribute("aria-pressed", "true")


def test_difficulty_tabs_switch(song: Page):
    expect(song.locator("#p-basico")).to_be_visible()
    song.locator("#t-intermedio").click()
    expect(song.locator("#p-intermedio")).to_be_visible()
    expect(song.locator("#p-basico")).to_be_hidden()


def test_level_selector_lives_only_in_the_playback_bar_and_sets_the_hash(song: Page):
    assert song.locator("#tabs").count() == 1  # sin pestañas duplicadas
    expect(song.locator("[data-ac-metronome] #tabs")).to_have_count(1)
    song.locator("[data-ac-metronome] #t-avanzado").click()
    expect(song.locator("#p-avanzado")).to_be_visible()
    assert song.evaluate("location.hash") == "#avanzado"
    song.evaluate("location.hash = '#basico'")
    expect(song.locator("#p-basico")).to_be_visible()


def test_hash_opens_that_level_and_unknown_hash_falls_back_to_basic(page: Page, base_url: str):
    page.goto(base_url + SONG + "#intermedio")
    expect(page.locator("#p-intermedio")).to_be_visible()
    expect(page.locator("#t-intermedio")).to_have_class(re.compile(r"\bactive\b"))
    page.goto("about:blank")  # carga nueva: cambiar solo el hash no recarga la página
    page.goto(base_url + SONG + "#no-existe")
    expect(page.locator("#p-basico")).to_be_visible()


def test_pass_stops_at_the_last_bar_and_offers_to_go_back(song_audio: Page):
    song = song_audio
    song.locator("[data-ac-met-countin]").click()  # sin cuenta
    song.locator("[data-ac-met-range]").fill("240")
    bars = song.locator("#p-basico .ac-bar")
    last = bars.nth(bars.count() - 1)
    last.scroll_into_view_if_needed()
    last.locator(".ac-start-flag").click()  # parte en el último compás: la pasada es corta
    toggle = song.locator("[data-ac-met-toggle]")
    restart = song.locator("[data-ac-met-restart]")
    toggle.click()
    expect(restart).to_be_visible(timeout=20000)
    expect(toggle).to_be_hidden()
    expect(toggle).to_have_attribute("aria-pressed", "false")
    expect(song.locator("#p-basico .ac-bar.is-current")).to_have_count(0)
    expect(song.locator(".ac-bar.is-start")).to_have_count(0)  # tampoco queda la bandera
    clicks = song.evaluate("window.__clicks")
    song.wait_for_timeout(800)
    assert song.evaluate("window.__clicks") == clicks  # nada sigue sonando
    song.evaluate(
        "window.scrollTo(0, 0)"
    )  # arriba: volver tiene que bajar hasta el compás de partida
    restart.click()
    song.wait_for_timeout(300)
    assert song.evaluate("scrollY") > 0  # el scroll va al primer compás, no al de la bandera
    first = bars.first.bounding_box()
    tools = song.locator(".ac-sticky-tools").bounding_box()
    assert first["y"] >= tools["y"] + tools["height"]  # el primer compás queda a la vista
    expect(restart).to_be_hidden()
    expect(toggle).to_be_visible()
    expect(toggle).to_have_attribute("aria-pressed", "false")  # solo vuelve: no reproduce
    song.wait_for_timeout(500)
    assert song.evaluate("window.__clicks") == clicks


def test_level_can_change_while_playing_without_stopping(song_audio: Page):
    song = song_audio
    song.locator("[data-ac-met-countin]").click()
    song.locator("[data-ac-met-range]").fill("240")
    toggle = song.locator("[data-ac-met-toggle]")
    toggle.click()
    expect(song.locator("#p-basico .ac-bar.is-current")).to_have_count(1, timeout=3000)
    song.locator("[data-ac-metronome] #t-intermedio").click()
    expect(toggle).to_have_attribute("aria-pressed", "true")
    expect(song.locator("#p-intermedio")).to_be_visible()
    if song.locator("#p-intermedio .ac-bar").count():
        expect(song.locator("#p-intermedio .ac-bar.is-current")).to_have_count(1, timeout=3000)
    toggle.click()


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
    set_options(song)
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
    expect(count.locator("span")).to_have_count(0)
    expect(toggle).to_have_text("Reproducir")
    toggle.click()
    expect(count.locator("span.is-on")).to_have_count(1, timeout=3000)
    seen, sizes = set(), []
    for _ in range(30):
        # En una sola llamada: el número resaltado y el tamaño del botón en ese instante.
        state = song.evaluate(
            """() => { const on = document.querySelector('[data-ac-met-count] span.is-on');
              const r = document.querySelector('[data-ac-met-toggle]').getBoundingClientRect();
              return on ? { n: on.textContent, w: r.width, h: r.height } : null; }"""
        )
        if state:
            seen.add(state["n"])
            sizes.append((state["w"], state["h"]))
        song.wait_for_timeout(50)
    assert {"1", "2", "3", "4"} <= seen
    expect(count.locator("span")).to_have_count(0, timeout=3000)  # empieza el compás 1
    # El botón no cambia de tamaño al pasar de la cuenta a «Detener» (la barra fija no crece).
    after = toggle.bounding_box()
    assert all(abs(w - after["width"]) < 1 and abs(h - after["height"]) < 1 for w, h in sizes)
    expect(song.locator(".ac-bar.is-current")).to_have_count(1, timeout=3000)
    toggle.click()
    song.locator("[data-ac-met-countin]").click()  # sin cuenta, no aparece
    toggle.click()
    song.wait_for_timeout(300)
    expect(count.locator("span")).to_have_count(0)


def test_tips_open_by_keyboard_stay_in_place_and_stop_glowing_once_seen(page: Page, tips_url: str):
    page.goto(tips_url + SONG)
    tips = page.locator("#p-basico .ac-tip")
    expect(tips).to_have_count(2)
    # Un tip al inicio (antes de la primera sección) y otro entre secciones.
    order = page.evaluate(
        """() => [...document.querySelectorAll('#p-basico .ac-tip, #p-basico h2')]
          .map(e => e.classList.contains('ac-tip') ? 'tip' : e.textContent.trim().split(' ')[0])"""
    )
    assert order[:2] == ["tip", "Intro"] and order.index("tip", 1) < order.index("Coro")
    first = tips.first
    button = first.locator(".ac-tip-btn")
    body = first.locator(".ac-tip-body")
    expect(button).to_have_attribute("aria-expanded", "false")
    expect(body).to_be_hidden()
    expect(first).not_to_have_class(re.compile(r"\bis-seen\b"))
    button.focus()
    page.keyboard.press("Enter")
    expect(button).to_have_attribute("aria-expanded", "true")
    expect(body).to_be_visible()
    expect(body).to_contain_text("el bajo baja a B")
    expect(first).to_have_class(re.compile(r"\bis-seen\b"))
    page.keyboard.press("Space")
    expect(body).to_be_hidden()
    # Lo ya visto se recuerda al recargar; el otro sigue brillando.
    page.reload()
    expect(page.locator("#p-basico .ac-tip").first).to_have_class(re.compile(r"\bis-seen\b"))
    expect(page.locator("#p-basico .ac-tip").nth(1)).not_to_have_class(re.compile(r"\bis-seen\b"))


def test_tips_do_not_disturb_the_playhead(page: Page, tips_url: str):
    page.add_init_script(SAFARI_AUDIO_STUB)
    page.goto(tips_url + SONG)
    set_options(page)
    page.locator("[data-ac-met-countin]").click()
    page.locator("[data-ac-met-range]").fill("240")
    page.locator("[data-ac-met-toggle]").click()
    expect(page.locator("#p-basico .ac-bar.is-current")).to_have_count(1, timeout=5000)
    first = page.locator("#p-basico .ac-bar.is-current").evaluate(
        "el => Array.from(el.closest('.ac-bars').children).indexOf(el)"
    )
    assert first == 0
    page.locator("[data-ac-met-toggle]").click()


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


def test_rests_are_drawn_without_chord_button_and_the_playhead_crosses_them(
    page: Page, rests_url: str
):
    page.add_init_script(SAFARI_AUDIO_STUB)
    page.goto(rests_url + SONG)
    set_options(page)
    pane = page.locator("#p-basico")
    rests = pane.locator(".ac-rest")
    expect(rests).to_have_count(3)
    expect(rests.first).to_have_attribute("aria-label", "silencio")
    expect(rests.first).to_be_visible()
    # Un silencio no abre diagrama: no es un botón.
    assert pane.locator("button .ac-rest").count() == 0
    rests.first.click()
    expect(page.locator(".ac-chord-panel")).to_have_count(0)
    # Un compás partido con silencio tiene sus dos partes (silencio 1 + 2 de G ... ver la fixture).
    split = pane.locator(".ac-bar.is-split").first
    expect(split.locator(".ac-part")).to_have_count(2)
    # El cursor pasa por el compás en silencio (es el primero) y avanza.
    page.locator("[data-ac-met-countin]").click()
    page.locator("[data-ac-met-range]").fill("240")
    page.locator("[data-ac-met-toggle]").click()
    first = pane.locator(".ac-bar.is-current")
    expect(first).to_have_count(1, timeout=5000)
    assert first.locator(".ac-rest").count() == 1
    page.wait_for_function(
        "() => !document.querySelector('#p-basico .ac-bar.is-current .ac-rest')", timeout=8000
    )
    page.locator("[data-ac-met-toggle]").click()
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0


def test_ties_show_the_held_chord_dimmed_open_its_diagram_and_the_playhead_crosses_them(
    page: Page, ties_url: str
):
    problems = []
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.add_init_script(SAFARI_AUDIO_STUB)
    page.add_init_script(GUITAR_OFF)
    page.goto(ties_url + SONG)
    set_options(page)
    pane = page.locator("#p-basico")
    ties = pane.locator("[data-tie='1']")
    expect(ties).to_have_count(2)
    # Compás entero: E sigue sonando, atenuado y con su arco.
    whole = pane.locator(".ac-bar.is-tie").first
    expect(whole.locator(".ac-tie-arc")).to_have_count(1)
    expect(whole.locator(".ac-chord-btn")).to_have_attribute("data-chord", "E")
    # Parte de un compás: F# ligado sobre la barra, luego F#.
    part = pane.locator(".ac-part.is-tie").first
    expect(part.locator(".ac-chord-btn")).to_have_attribute("data-chord", "F#")
    expect(page.locator("text=El arco indica un ligado").first).to_be_visible()
    # El acorde ligado abre su diagrama como cualquier otro.
    whole.locator(".ac-chord-btn").click()
    expect(page.locator(".ac-chord-panel")).to_be_visible()
    page.keyboard.press("Escape")
    # El cursor pasa por los ligados.
    page.locator("[data-ac-met-countin]").click()
    page.locator("[data-ac-met-range]").fill("240")
    page.locator("[data-ac-met-toggle]").click()
    page.wait_for_function(
        "() => document.querySelector('#p-basico .ac-bar.is-current.is-tie')", timeout=8000
    )
    page.locator("[data-ac-met-toggle]").click()
    assert problems == []
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0


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


def test_level_selector_has_a_visible_border_and_a_distinct_active_option(song: Page):
    bar = song.locator(".ac-levels-bar")
    assert bar.evaluate("el => parseFloat(getComputedStyle(el).borderTopWidth)") >= 2
    assert bar.evaluate("el => getComputedStyle(el).borderTopStyle") == "solid"
    active = song.locator(".ac-levels-bar .nav-link.active")
    other = song.locator(".ac-levels-bar .nav-link:not(.active)").first
    fill = "el => getComputedStyle(el).backgroundColor"
    assert active.evaluate(fill) != other.evaluate(fill)
    other.focus()
    song.keyboard.press("Tab")  # el foco por teclado se ve (anillo de 3 px)
    song.locator(".ac-levels-bar .nav-link").nth(1).focus()
    assert song.evaluate("parseFloat(getComputedStyle(document.activeElement).outlineWidth)") >= 2


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_level_selector_contrast_in_both_themes(page: Page, base_url: str, scheme: str):
    page.emulate_media(color_scheme=scheme)
    page.goto(base_url + SONG)
    page.evaluate(f"document.documentElement.setAttribute('data-bs-theme', '{scheme}')")
    page.wait_for_timeout(500)  # las transiciones de color terminan
    ratio = page.evaluate(
        """() => {
          const lum = (c) => { const v = c.match(/[\\d.]+/g).slice(0, 3).map(Number).map((x) => {
            x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
          const bg = lum(getComputedStyle(document.body).backgroundColor);
          const q = (s) => getComputedStyle(document.querySelector(s));
          const bar = lum(q('.ac-levels-bar').borderTopColor);
          const txt = lum(q('.ac-levels-bar .nav-link:not(.active)').color);
          const cr = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
          return { border: cr(bar, bg), text: cr(txt, bg) };
        }"""
    )
    assert ratio["border"] >= 3  # WCAG 1.4.11: componentes de interfaz
    assert ratio["text"] >= 4.5


def _is_mobile(page: Page) -> bool:
    return page.viewport_size["width"] <= 575


def test_options_group_is_collapsed_on_mobile_and_toggles_any_time(page: Page, base_url: str):
    page.goto(base_url + SONG)
    button = page.locator("[data-ac-met-options]")
    extra = page.locator("[data-ac-met-extra]")
    if not _is_mobile(page):
        expect(button).to_be_hidden()  # escritorio: nada cambia, todo suelto en la barra
        for sel in ("mute", "countin", "bpm", "range", "reset"):
            expect(page.locator(f"[data-ac-met-{sel}]")).to_be_visible()
        return
    expect(button).to_be_visible()
    expect(button).to_have_attribute("aria-expanded", "false")
    expect(button).to_have_attribute("aria-controls", "met-extra")
    expect(extra).to_be_hidden()
    for sel in ("toggle", "options"):
        expect(page.locator(f"[data-ac-met-{sel}]")).to_be_visible()
    expect(page.locator(".ac-levels-bar")).to_be_visible()
    closed_h = page.locator(".ac-sticky-tools").bounding_box()["height"]
    assert closed_h < page.viewport_size["height"] * 0.3
    button.click()
    expect(button).to_have_attribute("aria-expanded", "true")
    for sel in ("mute", "countin", "bpm", "range", "reset"):
        expect(page.locator(f"[data-ac-met-{sel}]")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    button.click()
    expect(extra).to_be_hidden()
    expect(button).to_have_attribute("aria-expanded", "false")


def test_options_can_be_closed_with_escape_and_keep_working_while_playing(
    song_audio: Page,
):
    song = song_audio  # la fixture las deja abiertas en celular
    button = song.locator("[data-ac-met-options]")
    song.locator("[data-ac-met-countin]").click()
    song.locator("[data-ac-met-range]").fill("240")
    song.locator("[data-ac-met-toggle]").click()
    expect(song.locator("#p-basico .ac-bar.is-current")).to_have_count(1, timeout=5000)
    if _is_mobile(song):
        song.locator("[data-ac-met-mute]").focus()
        song.keyboard.press("Escape")
        expect(button).to_have_attribute("aria-expanded", "false")
        expect(song.locator("[data-ac-met-extra]")).to_be_hidden()
        expect(song.locator("[data-ac-met-toggle]")).to_have_attribute("aria-pressed", "true")
        expect(song.locator("#p-basico .ac-bar.is-current")).to_have_count(1)
    song.locator("[data-ac-met-toggle]").click()
    expect(song.locator(".ac-bar.is-current")).to_have_count(0)


def test_playbar_has_no_horizontal_overflow_open_or_closed(page: Page, base_url: str):
    page.goto(base_url + SONG)
    for open_ in (False, True):
        set_options(page, open_)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        right = page.evaluate(
            "Math.max(...[...document.querySelectorAll('.ac-sticky-tools .btn, .ac-levels-bar')]"
            ".filter(e => e.offsetParent).map(e => e.getBoundingClientRect().right))"
        )
        assert right <= page.viewport_size["width"] + 0.5


def test_playbar_screenshots_for_review(page: Page, base_url: str, tmp_path_factory):
    out = Path(os.environ.get("AC_SHOTS", "")) if os.environ.get("AC_SHOTS") else None
    if out is None:
        pytest.skip("solo para revisar a ojo: AC_SHOTS=<carpeta>")
    out.mkdir(parents=True, exist_ok=True)
    name = f"{page.context.browser.browser_type.name}-{page.viewport_size['width']}"
    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme)
        page.goto(base_url + SONG)
        page.evaluate(f"document.documentElement.setAttribute('data-bs-theme', '{scheme}')")
        for open_ in (False, True):
            set_options(page, open_)
            state = "abierto" if open_ else "cerrado"
            page.wait_for_timeout(500)
            page.screenshot(path=str(out / f"{name}-{scheme}-{state}.png"))


def test_playbar_rows_levels_then_controls(page: Page, base_url: str):
    page.goto(base_url + SONG)
    levels = page.locator(".ac-met-levels-row").bounding_box()
    toggle = page.locator("[data-ac-met-toggle]").bounding_box()
    assert levels["y"] + levels["height"] <= toggle["y"] + 1  # niveles arriba de la reproducción
    assert page.locator(".ac-sticky-tools a[href*='guias.html']:visible").count() <= 1
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_options_button_flags_mute_while_the_panel_is_folded(song_audio: Page, tmp_path_factory):
    """S32: en celular «Opciones» avisa «Sin sonido» con ícono y nombre accesible."""
    page = song_audio
    if not _is_mobile(page):
        pytest.skip("«Opciones» solo existe en celular")
    button = page.locator("[data-ac-met-options]")
    flag = page.locator("[data-ac-met-options-mute]")
    set_options(page, False)
    expect(flag).to_be_hidden()
    expect(button).not_to_have_attribute("aria-label", re.compile("sin sonido"))
    set_options(page, True)
    page.locator("[data-ac-met-mute]").click()
    set_options(page, False)
    expect(page.locator("[data-ac-met-extra]")).to_be_hidden()
    expect(flag).to_be_visible()
    expect(button).to_have_attribute("aria-label", "Opciones (sin sonido activado)")
    expect(button).to_have_attribute("title", "Sin sonido activado")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    out = tmp_path_factory.mktemp("s32")
    page.locator(".ac-sticky-tools").screenshot(path=str(out / "opciones-sin-sonido.png"))
    print("CAPTURA", out / "opciones-sin-sonido.png")
    set_options(page, True)
    page.locator("[data-ac-met-mute]").click()
    set_options(page, False)
    expect(flag).to_be_hidden()
    expect(button).to_have_attribute("aria-label", "Opciones")


def test_parenthesized_chords_open_their_panel_and_the_unknown_one_is_plain_text(
    page: Page, parens_url: str
):
    page.goto(parens_url + SONG)
    page.get_by_role("tab", name=re.compile("Intermedio")).click()
    pane = page.locator("#p-intermedio")
    panel = page.locator(".ac-chord-panel")
    for written, label in (("D6/9", "D6/9"), ("Dm(add#11)", "Dm(add#11)")):
        button = pane.locator(f".ac-chord-btn[data-chord='{written}']").first
        expect(button).to_have_text(label)  # se ve como se escribió
        button.click()
        expect(panel).to_be_visible()
        panel.get_by_role("button", name="Teclado").click()  # sin guitarra estándar: el teclado
        expect(panel.locator("svg[aria-label^='Teclas']")).to_be_visible()
        page.keyboard.press("Escape")
    # válido pero sin notas conocidas: texto plano, sin botón, con los símbolos ♭ y ♯
    expect(pane.locator(".ac-chord-btn[data-chord='G7(b9/#11/13)']")).to_have_count(0)
    expect(pane.get_by_text("G7(♭9/♯11/13)").first).to_be_visible()


def watch_samples(page: Page) -> list[int]:
    samples: list[int] = []
    page.on(
        "response",
        lambda r: ("guitarra-nylon-" in r.url or "/bajo-" in r.url) and samples.append(r.status),
    )
    return samples


def wait_for_samples(page: Page, samples: list[int], count: int = 61) -> None:
    for _ in range(160):  # hasta 40 s: el emulador de celular del CI es lento
        if len(samples) >= count:
            break
        page.wait_for_timeout(250)


def test_guitar_starts_active_and_loads_its_samples_on_the_first_gesture(page: Page, base_url: str):
    """S45: la guitarra parte activa y con los volúmenes habilitados, pero no descarga nada al
    abrir: las 61 muestras bajan en el primer gesto (toque, clic o tecla) de la persona."""
    song = page  # sin la fixture `song`: en celular su set_options ya sería un gesto
    samples = watch_samples(song)
    song.goto(base_url + SONG)
    expect(song.locator("[data-ac-met-guitar]")).to_have_attribute("aria-pressed", "true")
    expect(song.locator("[data-ac-vol-guitar]")).to_be_enabled()
    expect(song.locator("[data-ac-vol-bass]")).to_be_enabled()
    song.wait_for_timeout(500)
    assert samples == []  # quien solo lee no gasta datos
    song.locator("h1").click()  # el primer gesto
    wait_for_samples(song, samples)
    assert sorted(set(samples)) == [200] and len(samples) == 61


def test_guitar_can_be_turned_off_and_the_choice_is_remembered(song_sound: Page):
    """S45: apagarla atenúa los volúmenes, se recuerda al recargar y no baja más."""
    song = song_sound
    samples = watch_samples(song)
    set_options(song)  # en celular es un gesto: puede bajar las muestras antes de apagarla
    song.locator("[data-ac-met-guitar]").click()
    expect(song.locator("[data-ac-met-guitar]")).to_have_attribute("aria-pressed", "false")
    expect(song.locator("[data-ac-vol-guitar]")).to_be_disabled()
    expect(song.locator("[data-ac-vol-bass]")).to_be_disabled()
    song.wait_for_timeout(1500)
    loaded = len(samples)
    song.reload()
    expect(song.locator("[data-ac-met-guitar]")).to_have_attribute("aria-pressed", "false")
    expect(song.locator("[data-ac-vol-guitar]")).to_be_disabled()
    set_options(song)
    song.locator("h1").click()
    song.wait_for_timeout(1500)
    assert len(samples) == loaded  # apagada: ni siquiera con gestos se descarga más


def test_turning_the_guitar_back_on_loads_its_samples(page: Page, base_url: str):
    """S37 y S45: apagada y activada otra vez, la guitarra queda con sus 61 muestras (en celular
    abrir «Opciones» ya las pidió: se cuentan todas, por eso se observa desde antes de abrir)."""
    song = page
    samples = watch_samples(song)
    song.goto(base_url + SONG)
    set_options(song)
    song.locator("[data-ac-met-guitar]").click()  # apagada
    song.locator("[data-ac-met-guitar]").click()  # activa otra vez
    expect(song.locator("[data-ac-vol-guitar]")).to_be_enabled()
    wait_for_samples(song, samples)
    assert sorted(set(samples)) == [200] and len(samples) == 61


# --- RD6: la cuenta espera a que la guitarra tenga sus muestras ---------------------------


class HeldSamples:
    """Retiene las descargas de muestras (red lenta); `release()` las deja pasar todas."""

    def __init__(self, page: Page):
        self.holding = True
        self.routes: list = []
        page.route("**/*.mp3", self._handle)

    def _handle(self, route) -> None:
        self.routes.append(route) if self.holding else route.continue_()

    def release(self) -> None:
        self.holding = False
        for route in self.routes:
            route.continue_()
        self.routes.clear()


@pytest.fixture
def slow_song(page: Page, base_url: str):
    page.add_init_script(SAFARI_AUDIO_STUB)
    page.add_init_script(DECODE_STUB)
    held = HeldSamples(page)
    page.goto(base_url + SONG)
    set_options(page)
    yield page, held
    held.release()


def test_play_waits_for_the_guitar_samples_before_the_count_in(slow_song):
    """RD6: con la guitarra activa y las muestras sin llegar, Reproducir dice «Cargando sonido» y la
    cuenta no empieza; al llegar, empieza y el primer acorde ya tiene sus notas."""
    song, held = slow_song
    toggle = song.locator("[data-ac-met-toggle]")
    toggle.click()
    expect(toggle).to_have_attribute("aria-busy", "true")
    expect(song.locator("[data-ac-met-label]")).to_contain_text("Cargando sonido")
    song.wait_for_timeout(1500)  # más que un pulso: sin la espera ya habría clics
    assert song.evaluate("window.__clicks") == 0
    assert song.locator(".ac-bar.is-current").count() == 0
    held.release()
    expect(toggle).not_to_have_attribute("aria-busy", "true", timeout=8000)
    expect(song.locator(".ac-bar.is-current")).to_have_count(1, timeout=8000)
    assert song.evaluate("window.__clicks") >= 5  # 4 de cuenta + el primer pulso


def test_stopping_while_the_sound_loads_cancels_the_start(slow_song):
    song, held = slow_song
    toggle = song.locator("[data-ac-met-toggle]")
    toggle.click()
    expect(toggle).to_have_attribute("aria-busy", "true")
    toggle.click()  # Detener
    expect(song.locator("[data-ac-met-label]")).to_have_text("Reproducir")
    expect(toggle).not_to_have_attribute("aria-busy", "true")
    held.release()
    song.wait_for_timeout(1500)
    assert song.evaluate("window.__clicks") == 0  # no arrancó la partida cancelada


def test_play_starts_anyway_with_a_visible_notice_when_the_sound_never_arrives(slow_song):
    """RD6: tope de 10 s. Si la red no alcanza, la cuenta empieza y el aviso se ve."""
    song, held = slow_song
    song.locator("[data-ac-met-toggle]").click()
    status = song.locator("[data-ac-met-status]")
    expect(status).to_have_text("Sin guitarra: el sonido no terminó de cargar", timeout=15000)
    expect(status).to_be_visible()
    expect(song.locator(".ac-bar.is-current")).to_have_count(1, timeout=8000)  # el metrónomo siguió
    assert song.evaluate("window.__clicks") >= 5

"""Experimento: el metrónomo contra un AudioContext REAL, sin simular.

Mide la señal que llega al destino con un AnalyserNode. Necesita una salida de audio: en CI un
sink nulo de PulseAudio (ver el pipeline). Si no funciona de forma estable, se descarta.
"""

import pytest
from playwright.sync_api import Page, expect

SONG = "/cancion-camara-lenta.html"

PROBE = """
(() => {
  const Orig = window.AudioContext || window.webkitAudioContext;
  window.__peak = 0;
  window.__state = "none";
  window.AudioContext = class extends Orig {
    constructor(...a) {
      super(...a);
      window.__ctx = this;
      const an = this.createAnalyser();
      an.fftSize = 2048;
      const buf = new Float32Array(an.fftSize);
      setInterval(() => {
        window.__state = this.state;
        an.getFloatTimeDomainData(buf);
        for (const v of buf) window.__peak = Math.max(window.__peak, Math.abs(v));
      }, 10);
      const connect = AudioNode.prototype.connect;
      const dest = this.destination;
      this.__tap = (node) => connect.call(node, an);
      this.__dest = dest;
    }
  };
  const connect = AudioNode.prototype.connect;
  AudioNode.prototype.connect = function (target, ...rest) {
    const r = connect.call(this, target, ...rest);
    if (window.__ctx && target === window.__ctx.__dest) window.__ctx.__tap(this);
    return r;
  };
})();
"""


@pytest.fixture
def song_real(page: Page, base_url: str) -> Page:
    page.add_init_script(PROBE)
    page.goto(base_url + SONG)
    return page


def test_real_audiocontext_runs_and_emits_signal(song_real: Page):
    song_real.locator("[data-ac-met-toggle]").click()
    expect(song_real.locator("[data-ac-met-toggle]")).to_have_attribute("aria-pressed", "true")
    for _ in range(40):
        if song_real.evaluate("window.__peak") > 0.05:
            break
        song_real.wait_for_timeout(100)
    state = song_real.evaluate("window.__state")
    peak = song_real.evaluate("window.__peak")
    assert state == "running", f"AudioContext en estado {state!r}"
    assert peak > 0.05, f"sin señal en la salida (pico {peak})"

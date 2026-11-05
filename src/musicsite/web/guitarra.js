/* Guitarra del reproductor (laboratorio S37, rama feat/investigacion-midi; no va a producción).
   Toca la primera forma del panel de cada acorde con guitarra de nailon (muestras FluidR3_GM).
   Rasgueo ultra simple, siempre hacia abajo:
   - compás de un acorde: un golpe en el tiempo 1 (redonda);
   - dos acordes de medio compás cada uno: un golpe al empezar cada uno (blancas);
   - cualquier otro reparto: un golpe por tiempo con el acorde que suena (negras).
   El silencio apaga las cuerdas. Empieza apagada en cada página. */
(function () {
  "use strict";
  var TUNING = [40, 45, 50, 55, 59, 64]; // E2 A2 D3 G3 B3 E4, igual que chords-guitar.json
  var SPREAD = 0.014;
  var enabled = false, data = null, out = null, outCtx = null;
  var voices = [null, null, null, null, null, null];
  /* Guitarra de nailon (FluidR3_GM, una muestra por semitono, E2 a E6): archivos planos
     guitarra-nylon-<nota>.mp3 junto a este script (ignorados por git, licencia por verificar).
     Si faltan o aún no cargan, esa nota no suena (no hay sonido sintetizado de respaldo). */
  var FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
  var samples = null, samplesCtx = null;
  var volume = 0.7; // 0 a 1 (S39); se recuerda por dispositivo

  function sampleName(m) { return "guitarra-nylon-" + FLAT[m % 12] + (Math.floor(m / 12) - 1) + ".mp3"; }

  function loadSamples(ctx) {
    if (samplesCtx === ctx) return;
    samplesCtx = ctx; samples = {};
    for (var m = 40; m <= 88; m++) (function (note) {
      fetch(sampleName(note)).then(function (r) { return r.ok ? r.arrayBuffer() : null; })
        .then(function (data) { return data && ctx.decodeAudioData(data); })
        .then(function (buf) { if (buf && samplesCtx === ctx) samples[note] = buf; })
        .catch(function () { /* sin esta muestra: esa nota no suena */ });
    })(m);
  }

  function payload() {
    if (data) return data;
    var el = document.getElementById("acordes-data");
    try { data = el ? JSON.parse(el.textContent) : null; } catch (e) { data = null; }
    return data || { chords: {}, own: {}, default: {} };
  }

  /* La primera forma del panel (S27): propia del nivel, luego la del tema, luego chords-db ordenada. */
  function firstForm(name, mode) {
    var d = payload();
    var own = (d.own[mode] || {})[name];
    if (own) return own.frets;
    var def = (d.default || {})[name];
    if (def) return def.frets;
    var std = (d.chords[name] || {}).guitar;
    return std && std.length ? std[0].frets : null;
  }

  function bus(ctx) {
    if (out && outCtx === ctx) return out;
    outCtx = ctx;
    var low = ctx.createBiquadFilter(); low.type = "peaking"; low.frequency.value = 105; low.Q.value = 1.2; low.gain.value = 4;
    var mid = ctx.createBiquadFilter(); mid.type = "peaking"; mid.frequency.value = 240; mid.Q.value = 1.6; mid.gain.value = 2;
    var air = ctx.createBiquadFilter(); air.type = "lowpass"; air.frequency.value = 6500;
    out = ctx.createGain(); out.gain.value = volume;
    out.connect(low); low.connect(mid); mid.connect(air); air.connect(ctx.destination);
    return out;
  }

  function stopString(s, when) {
    var v = voices[s];
    if (!v) return;
    v.gain.gain.cancelScheduledValues(when);
    v.gain.gain.setTargetAtTime(0, when, 0.015);
    try { v.src.stop(when + 0.2); } catch (e) { /* ya detenida */ }
    voices[s] = null;
  }

  function muteAll(when) { for (var s = 0; s < 6; s++) stopString(s, when); }

  function strum(ctx, frets, when) {
    var dest = bus(ctx), k = 0;
    loadSamples(ctx);
    for (var s = 0; s < 6; s++) {
      if (frets[s] < 0) { stopString(s, when); continue; }
      var at = when + k * SPREAD;
      k++;
      stopString(s, at); // una cuerda suena una nota a la vez
      /* Solo suena nailon: mientras una nota no ha cargado (o si faltan las muestras), no suena. */
      var buffer = samples && samples[TUNING[s] + frets[s]];
      if (!buffer) continue;
      var src = ctx.createBufferSource(), gain = ctx.createGain();
      src.buffer = buffer;
      gain.gain.value = 1;
      src.connect(gain); gain.connect(dest);
      src.start(at);
      voices[s] = { src: src, gain: gain };
    }
  }

  /* Partes del compás tal como las dibuja el sitio: [{peso, acorde | null}] (null = silencio o
     un acorde que no sabemos tocar). */
  function partsOf(bar) {
    var spans = bar.querySelectorAll(".ac-part");
    var list = spans.length ? Array.prototype.slice.call(spans) : [bar];
    return list.map(function (el) {
      var btn = el.querySelector(".ac-chord-btn");
      return { weight: +el.getAttribute("data-weight") || 1, chord: btn ? btn.getAttribute("data-chord") : null };
    });
  }

  /* En qué tiempos del compás hay golpe. */
  function hits(parts, beats) {
    var total = 0, at = [], i;
    parts.forEach(function (p) { total += p.weight; });
    if (parts.length === 1) return [0];
    var half = parts.length === 2 && parts[0].weight === parts[1].weight && beats % 2 === 0;
    if (half) return [0, beats / 2];
    for (i = 0; i < beats; i++) at.push(i);
    return at;
  }

  /* El acorde que suena en el tiempo `inBar`: la misma cuenta que ilumina la parte (beatTarget). */
  function partAt(parts, inBar, beats) {
    var total = 0, acc = 0;
    parts.forEach(function (p) { total += p.weight; });
    var slot = Math.floor(inBar * total / beats);
    for (var k = 0; k < parts.length; k++) { acc += parts[k].weight; if (slot < acc) return parts[k]; }
    return parts[parts.length - 1];
  }

  /* El metrónomo la llama en cada tiempo agendado (no en la cuenta inicial). */
  function beat(ctx, when, bar, inBar, beats, mode) {
    if (!enabled || !ctx || !bar) return;
    var parts = partsOf(bar);
    if (hits(parts, beats).indexOf(inBar) < 0) return;
    var part = partAt(parts, inBar, beats);
    var frets = part.chord ? firstForm(part.chord, mode) : null;
    if (!frets) { muteAll(when); return; }
    strum(ctx, frets, when);
  }

  function stop(ctx) { if (ctx && outCtx === ctx) muteAll(ctx.currentTime); }

  function setVolume(v) {
    volume = Math.min(1, Math.max(0, v));
    if (out) out.gain.value = volume;
    try { localStorage.setItem("ac-vol-guitar", String(volume)); } catch (e) { /* sin almacenamiento */ }
  }

  window.AcordiaGuitar = {
    beat: beat, stop: stop, prepare: loadSamples,
    isOn: function () { return enabled; },
    _hits: hits, _partAt: partAt, // para las pruebas del laboratorio
  };

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.querySelector("[data-ac-met-guitar]");
    if (!btn) return;
    var slider = document.querySelector("[data-ac-vol-guitar]");
    try { var saved = parseFloat(localStorage.getItem("ac-vol-guitar")); if (isFinite(saved)) volume = Math.min(1, Math.max(0, saved)); } catch (e) { /* sin almacenamiento */ }
    var out100 = slider && slider.parentNode.querySelector("[data-ac-vol-out]");
    var card = btn.closest(".ac-snd-card");
    function showVolume() { if (out100) out100.textContent = Math.round(volume * 100) + "%"; }
    if (slider) {
      slider.value = Math.round(volume * 100);
      showVolume();
      slider.addEventListener("input", function () { setVolume(slider.value / 100); showVolume(); });
    }
    btn.addEventListener("click", function () {
      enabled = !enabled;
      btn.setAttribute("aria-pressed", enabled ? "true" : "false");
      /* Apagada: el volumen se atenúa y no responde (S40). */
      if (slider) slider.disabled = !enabled;
      if (card) card.classList.toggle("is-off", !enabled);
      if (!enabled && outCtx) muteAll(outCtx.currentTime);
      if (enabled) document.dispatchEvent(new CustomEvent("acordia-guitar-on"));
    });
  });
})();

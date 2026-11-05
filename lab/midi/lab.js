/* Laboratorio de guitarra (S37). Solo local: no es parte del sitio ni del render.
   Forma de guitarra -> notas MIDI -> rasgueo con dos motores (Karplus-Strong o muestras FluidR3_GM). */
"use strict";

const DATA_URL = "datos-chords-guitar.json"; // enlace a src/musicsite/data/chords-guitar.json (servir.sh)
const SAMPLE_DIR = "muestras/FluidR3_GM";
const SAMPLE_MIN = 40, SAMPLE_MAX = 88; // E2 a E6: cubre las 6 cuerdas hasta el traste 24
const AHEAD = 0.12, TICK = 25; // igual que el metrónomo del sitio: agenda con el reloj del audio

const SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const ROOT_ALIAS = { Db: "C#", "D#": "Eb", Gb: "F#", "G#": "Ab", "A#": "Bb", Cb: "B", Fb: "E", "E#": "F", "B#": "C" };
const SUFFIX = {
  "": "major", m: "minor", min: "minor", dim: "dim", "°": "dim", dim7: "dim7", sus2: "sus2", sus4: "sus4",
  sus: "sus4", sus2sus4: "sus2sus4", "7sus4": "7sus4", aug: "aug", "+": "aug", 6: "6", 7: "7", 9: "9",
  maj7: "maj7", M7: "maj7", maj9: "maj9", m6: "m6", m7: "m7", m7b5: "m7b5", "ø": "m7b5", m9: "m9", m69: "m69",
  m11: "m11", mmaj7: "mmaj7", mmaj7b5: "mmaj7b5", mmaj9: "mmaj9", mmaj11: "mmaj11", add9: "add9", madd9: "madd9",
};

const $ = (id) => document.getElementById(id);
let db = null, tuning = [40, 45, 50, 55, 59, 64];
let ctx = null, busKs = null, busSmp = null, master = null, bodyLow = null, bodyMid = null;
const ksCache = new Map();
const samples = { key: "", buffers: new Map(), bytes: 0, ms: 0 };
const voices = [null, null, null, null, null, null]; // una nota viva por cuerda
let formIndex = 0;
const metrics = {};

/* ---------- Teoría mínima: nombre -> formas -> MIDI ---------- */

function midiName(m) { return SHARP[m % 12] + (Math.floor(m / 12) - 1); }
function fileName(m) { return FLAT[m % 12] + (Math.floor(m / 12) - 1); }
function toMidi(frets) { return frets.map((f, i) => (f < 0 ? null : tuning[i] + f)); }

function parseChord(name) {
  const m = /^([A-G])([#b]?)(.*)$/.exec(name.trim());
  if (!m) return { error: "no entiendo el acorde «" + name + "»" };
  if (m[3].includes("/")) return { error: "los acordes con bajo («" + name + "») quedan fuera del laboratorio" };
  let root = m[1] + m[2];
  root = ROOT_ALIAS[root] || root;
  const suffix = SUFFIX[m[3]];
  if (!suffix) return { error: "no conozco la variante «" + m[3] + "» de «" + name + "»" };
  return { root, suffix };
}

function baseFret(frets) {
  const pressed = frets.filter((f) => f > 0);
  return pressed.length ? Math.min(...pressed) : 0;
}

/* Misma regla que chordtheory.nearest_barre_first (S27): si la primera forma empieza en el traste 3
   o más, se ordenan por traste base ascendente, conservando el orden en los empates. */
function nearestBarreFirst(list) {
  if (!list.length || baseFret(list[0].frets) < 3) return list;
  return list.map((f, i) => [f, i]).sort((a, b) => baseFret(a[0].frets) - baseFret(b[0].frets) || a[1] - b[1]).map((p) => p[0]);
}

function parseThemeForms(text) {
  const forms = {}, errors = [];
  text.split("\n").forEach((raw, n) => {
    const line = raw.replace(/(^|\s)#.*$/, "").trim(); // comentario TOML; el # de F# no cuenta
    if (!line || line === "[formas]") return;
    const m = /^"?([^"=]+?)"?\s*=\s*"?([^"]+?)"?$/.exec(line);
    if (!m) { errors.push("línea " + (n + 1) + ": se espera \"ACORDE\" = \"6 valores\""); return; }
    const vals = m[2].trim().split(/\s+/);
    if (vals.length !== 6) { errors.push("«" + m[1] + "»: deben ser 6 valores"); return; }
    const frets = [];
    for (const v of vals) {
      if (v === "x" || v === "X") { frets.push(-1); continue; }
      if (!/^\d+$/.test(v) || +v > 24) { errors.push("«" + m[1] + "»: «" + v + "» debe ser x o un traste de 0 a 24"); return; }
      frets.push(+v);
    }
    if (frets.filter((f) => f >= 0).length < 3) { errors.push("«" + m[1] + "»: deben sonar al menos 3 cuerdas"); return; }
    forms[m[1].trim()] = frets;
  });
  return { forms, errors };
}

function themeForms() { return parseThemeForms($("theme-forms").value).forms; }

/* Orden del panel del sitio: forma del tema primero, después chords-db con la regla de cejilla. */
function formsFor(name) {
  const parsed = parseChord(name);
  const list = [], seen = new Set();
  const add = (frets, kind) => {
    const key = frets.join(",");
    if (seen.has(key)) return;
    seen.add(key);
    list.push({ frets, kind });
  };
  const own = themeForms()[name.trim()];
  if (own) add(own, "Forma de este tema");
  if (!parsed.error) {
    const std = ((db.acordes[parsed.root] || {})[parsed.suffix] || []).map((p) => ({ frets: p.f }));
    nearestBarreFirst(std).forEach((p) => add(p.frets, ""));
  }
  if (!list.length) return { error: parsed.error || "no hay formas para «" + name + "»" };
  return { list };
}

/* ---------- Audio ---------- */

function ensureAudio() {
  if (ctx) { if (ctx.state === "suspended") ctx.resume(); return ctx; }
  // iOS: que suene con el interruptor de silencio puesto (Safari 16.4+), como el metrónomo del sitio.
  try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch (e) { /* sin soporte */ }
  const Ctor = window.AudioContext || window.webkitAudioContext;
  ctx = new Ctor();
  master = ctx.createGain();
  master.gain.value = +$("vol").value;
  master.connect(ctx.destination);
  // Motor A pasa por un "cuerpo" simple: dos resonancias graves sobre la cuerda.
  bodyLow = ctx.createBiquadFilter(); bodyLow.type = "peaking"; bodyLow.frequency.value = 105; bodyLow.Q.value = 1.2;
  bodyMid = ctx.createBiquadFilter(); bodyMid.type = "peaking"; bodyMid.frequency.value = 240; bodyMid.Q.value = 1.6;
  const air = ctx.createBiquadFilter(); air.type = "lowpass"; air.frequency.value = 6500;
  busKs = ctx.createGain();
  busKs.connect(bodyLow); bodyLow.connect(bodyMid); bodyMid.connect(air); air.connect(master);
  busSmp = ctx.createGain();
  busSmp.connect(master);
  applyBody();
  showMetrics();
  return ctx;
}

function applyBody() {
  if (!ctx) return;
  const b = +$("ks-body").value;
  bodyLow.gain.value = b * 8;
  bodyMid.gain.value = b * 4;
}

function engine() { return document.querySelector("input[name=engine]:checked").value; }

/* Karplus-Strong con filtro pasa-todo para afinar la fracción del retardo (sin desafinar los agudos). */
function ksBuffer(midi) {
  const bright = +$("ks-bright").value, sustain = +$("ks-sustain").value;
  const key = midi + "|" + bright + "|" + sustain + "|" + ctx.sampleRate;
  if (ksCache.has(key)) return ksCache.get(key);
  const sr = ctx.sampleRate, freq = 440 * Math.pow(2, (midi - 69) / 12);
  let delay = sr / freq - 0.5, n = Math.floor(delay), frac = delay - n;
  if (frac < 0.1) { n -= 1; frac += 1; }
  const c = (1 - frac) / (1 + frac);
  const len = Math.floor(sr * 3);
  const buf = ctx.createBuffer(1, len, sr), out = buf.getChannelData(0);
  const line = new Float32Array(n);
  let lp = 0, mean = 0;
  for (let i = 0; i < n; i++) { const x = Math.random() * 2 - 1; lp = bright * x + (1 - bright) * lp; line[i] = lp; mean += lp; }
  mean /= n;
  for (let i = 0; i < n; i++) line[i] -= mean; // sin componente continua
  let idx = 0, prev = 0, apX = 0, apY = 0, peak = 0;
  for (let t = 0; t < len; t++) {
    const y = line[idx];
    out[t] = y;
    const avg = sustain * 0.5 * (y + prev);
    prev = y;
    const ap = c * avg + apX - c * apY;
    apX = avg; apY = ap;
    line[idx] = ap;
    idx = idx + 1 === n ? 0 : idx + 1;
    if (Math.abs(y) > peak) peak = Math.abs(y);
  }
  const g = peak > 0 ? 0.35 / peak : 1;
  for (let t = 0; t < len; t++) out[t] *= g;
  ksCache.set(key, buf);
  return buf;
}

function sampleNotes() {
  const step = $("smp-set").value === "light" ? 3 : 1;
  const notes = [];
  for (let m = SAMPLE_MIN; m <= SAMPLE_MAX; m += step) notes.push(m);
  return notes;
}

async function loadSamples() {
  ensureAudio();
  const bank = $("smp-bank").value, set = $("smp-set").value, key = bank + "|" + set;
  if (samples.key === key) return true;
  $("smp-status").textContent = "Cargando…";
  $("smp-load").disabled = true;
  const t0 = performance.now();
  const buffers = new Map();
  let bytes = 0, missing = 0;
  await Promise.all(sampleNotes().map(async (m) => {
    try {
      const res = await fetch(SAMPLE_DIR + "/" + bank + "/" + fileName(m) + ".mp3");
      if (!res.ok) { missing++; return; }
      const data = await res.arrayBuffer();
      bytes += data.byteLength;
      buffers.set(m, await new Promise((ok, ko) => ctx.decodeAudioData(data, ok, ko)));
    } catch (e) { missing++; }
  }));
  $("smp-load").disabled = false;
  if (!buffers.size) {
    $("smp-status").innerHTML = '<span class="bad">No hay muestras: corre <span class="mono">lab/midi/bajar-muestras.sh</span></span>';
    return false;
  }
  Object.assign(samples, { key, buffers, bytes, ms: performance.now() - t0 });
  $("smp-status").textContent = buffers.size + " notas, " + Math.round(bytes / 1024) + " KB, " + Math.round(samples.ms) + " ms" + (missing ? " (" + missing + " faltan)" : "");
  metrics["Muestras (" + bank.replace("acoustic_guitar_", "") + ", " + (set === "light" ? "ligero" : "completo") + ")"] =
    buffers.size + " notas · " + Math.round(bytes / 1024) + " KB · carga y decodificación " + Math.round(samples.ms) + " ms";
  showMetrics();
  return true;
}

function nearestSample(midi) {
  let best = null;
  for (const m of samples.buffers.keys()) if (best === null || Math.abs(m - midi) < Math.abs(best - midi)) best = m;
  return best;
}

function stopString(s, when) {
  const v = voices[s];
  if (!v) return;
  v.gain.gain.cancelScheduledValues(when);
  v.gain.gain.setTargetAtTime(0, when, 0.015);
  try { v.src.stop(when + 0.2); } catch (e) { /* ya detenida */ }
  voices[s] = null;
}

function playNote(s, midi, when, velocity) {
  let buffer, rate = 1, bus;
  if (engine() === "ks") { buffer = ksBuffer(midi); bus = busKs; }
  else {
    const base = nearestSample(midi);
    if (base === null) return;
    buffer = samples.buffers.get(base);
    rate = Math.pow(2, (midi - base) / 12);
    bus = busSmp;
  }
  stopString(s, when); // una cuerda solo suena una nota a la vez
  const src = ctx.createBufferSource();
  src.buffer = buffer;
  src.playbackRate.value = rate;
  const gain = ctx.createGain();
  gain.gain.value = velocity;
  src.connect(gain); gain.connect(bus);
  src.start(when);
  voices[s] = { src, gain };
}

function strum(frets, dir, when, velocity) {
  const midi = toMidi(frets);
  let order = [0, 1, 2, 3, 4, 5];
  if (dir === "U") { order = order.reverse(); if ($("up-top").checked) order = order.filter((s) => s >= 2); }
  const spread = +$("spread").value / 1000, human = $("humanize").checked ? 0.003 : 0;
  let k = 0;
  order.forEach((s) => {
    if (midi[s] === null) { stopString(s, when); return; } // cuerda muda: se apaga
    const jitter = human ? (Math.random() * 2 - 1) * human : 0;
    playNote(s, midi[s], Math.max(ctx.currentTime, when + k * spread + jitter), velocity * (dir === "U" ? 0.75 : 1));
    k++;
  });
}

function muteAll(when) { for (let s = 0; s < 6; s++) stopString(s, when); }

function click(when, strong) {
  const osc = ctx.createOscillator(), g = ctx.createGain();
  osc.frequency.value = strong ? 1600 : 1100;
  g.gain.setValueAtTime(0.0001, when);
  g.gain.exponentialRampToValueAtTime(strong ? 0.5 : 0.3, when + 0.002);
  g.gain.exponentialRampToValueAtTime(0.0001, when + 0.05);
  osc.connect(g); g.connect(ctx.destination);
  osc.start(when); osc.stop(when + 0.06);
}

async function ready() {
  ensureAudio();
  if (engine() === "samples") return loadSamples();
  return true;
}

/* ---------- Acorde suelto ---------- */

function currentForms() { return formsFor($("chord").value); }

function renderChord() {
  const r = currentForms();
  const cells = (attr) => document.querySelectorAll("[" + attr + "]");
  $("chord-error").textContent = r.error || "";
  if (r.error) {
    ["data-fret", "data-midi", "data-name"].forEach((a) => cells(a).forEach((c) => { c.textContent = ""; }));
    $("form-label").textContent = "";
    return;
  }
  formIndex = ((formIndex % r.list.length) + r.list.length) % r.list.length;
  const form = r.list[formIndex], midi = toMidi(form.frets);
  cells("data-fret").forEach((c, i) => { c.textContent = form.frets[i] < 0 ? "x" : form.frets[i]; });
  cells("data-midi").forEach((c, i) => { c.textContent = midi[i] === null ? "–" : midi[i]; });
  cells("data-name").forEach((c, i) => { c.textContent = midi[i] === null ? "–" : midiName(midi[i]); });
  $("form-label").textContent = "Forma " + (formIndex + 1) + " de " + r.list.length + (form.kind ? " · " + form.kind : "");
}

async function playChord(mode) {
  const t0 = performance.now();
  if (!(await ready())) return;
  const r = currentForms();
  if (r.error) return;
  const frets = r.list[formIndex].frets;
  const prep0 = performance.now();
  const when = ctx.currentTime + 0.01;
  if (mode === "arp") {
    toMidi(frets).forEach((m, s) => { if (m !== null) playNote(s, m, when + s * 0.25, 0.9); });
  } else {
    strum(frets, mode, when, 1);
  }
  const prep = performance.now() - prep0;
  const lat = ((ctx.baseLatency || 0) + (ctx.outputLatency || 0)) * 1000;
  metrics["Último golpe (" + (engine() === "ks" ? "A" : "B") + ")"] =
    "preparación " + prep.toFixed(1) + " ms · demora estimada " + Math.round(prep + 10 + lat) + " ms" +
    (performance.now() - t0 > prep + 50 ? " (incluye carga: " + Math.round(performance.now() - t0) + " ms)" : "");
  showMetrics();
}

/* ---------- Progresión con agenda anticipada ---------- */

const prog = { timer: null, bars: [], pattern: "", slot: 0, next: 0, slotDur: 0, slotsPerBar: 0, countSlots: 0 };

function patternValue() {
  const v = $("pattern").value === "custom" ? $("pattern-custom").value.trim().toUpperCase() : $("pattern").value;
  if (!/^[DU-]{4,16}$/.test(v) || v.length % 2) return { error: "el patrón usa D, U y - en corcheas: largo par entre 4 y 16" };
  return { value: v };
}

function parseProgression() {
  const tokens = $("prog").value.trim().split(/\s+/).filter(Boolean);
  const bars = [];
  let last = null, error = "";
  tokens.forEach((t) => {
    if (t === "%") { bars.push({ label: "%", frets: last ? last.frets : null, rest: !last }); return; }
    if (t === ".") { bars.push({ label: "·", rest: true }); last = null; return; }
    const r = formsFor(t);
    if (r.error) { bars.push({ label: t, error: true, rest: true }); error = error || r.error; return; }
    last = { label: t, frets: r.list[0].frets }; // la primera forma, como el panel del sitio
    bars.push(last);
  });
  return { bars, error };
}

function renderProgression() {
  const { bars, error } = parseProgression();
  const view = $("prog-view");
  view.textContent = "";
  bars.forEach((b) => {
    const s = document.createElement("span");
    s.textContent = b.label;
    if (b.error) s.className = "err";
    view.appendChild(s);
  });
  $("prog-error").textContent = error;
}

function highlight(barIndex, when) {
  setTimeout(() => {
    if (!prog.timer) return;
    const spans = $("prog-view").children;
    for (let i = 0; i < spans.length; i++) spans[i].classList.toggle("now", i === barIndex);
  }, Math.max(0, (when - ctx.currentTime) * 1000));
}

function countLabel(n, when) {
  setTimeout(() => { if (prog.timer) $("prog-count").textContent = n ? "Cuenta: " + n : ""; },
    Math.max(0, (when - ctx.currentTime) * 1000));
}

function schedule() {
  while (prog.next < ctx.currentTime + AHEAD) {
    const t = prog.next, i = prog.slot, beatSlot = i % 2 === 0;
    if (i < 0) { // cuenta inicial: solo clic
      if (beatSlot) {
        const n = (i + prog.countSlots) / 2 + 1;
        click(t, n === 1);
        countLabel(n, t);
      }
    } else {
      const barN = Math.floor(i / prog.slotsPerBar), inBar = i % prog.slotsPerBar;
      if (barN >= prog.bars.length && !$("loop").checked) {
        muteAll(t);
        setTimeout(stopProgression, Math.max(0, (t - ctx.currentTime) * 1000) + 300);
        prog.next = Infinity;
        return;
      }
      const bar = prog.bars[barN % prog.bars.length];
      if (inBar === 0) { highlight(barN % prog.bars.length, t); if (i === 0) countLabel(0, t); }
      if (beatSlot && $("click").checked) click(t, inBar === 0);
      const hit = prog.pattern[inBar];
      if (bar.rest || !bar.frets) { if (inBar === 0) muteAll(t); }
      else if (hit === "D" || hit === "U") strum(bar.frets, hit, t, 1);
    }
    prog.slot++;
    prog.next += prog.slotDur;
  }
}

async function startProgression() {
  const p = patternValue();
  const { bars, error } = parseProgression();
  $("prog-error").textContent = p.error || error;
  if (p.error || !bars.length) return;
  const t0 = performance.now();
  if (!(await ready())) return;
  if (engine() === "ks") bars.forEach((b) => { if (b.frets) toMidi(b.frets).forEach((m) => { if (m !== null) ksBuffer(m); }); });
  metrics["Preparar la progresión (" + (engine() === "ks" ? "A" : "B") + ")"] = Math.round(performance.now() - t0) + " ms";
  showMetrics();
  const bpm = +$("bpm").value;
  Object.assign(prog, {
    bars, pattern: p.value, slotDur: 60 / bpm / 2, slotsPerBar: p.value.length,
    countSlots: $("countin").checked ? p.value.length : 0,
  });
  prog.slot = -prog.countSlots;
  prog.next = ctx.currentTime + 0.05;
  prog.timer = setInterval(schedule, TICK);
  schedule();
  $("prog-play").disabled = true;
  $("prog-stop").disabled = false;
}

function stopProgression() {
  if (prog.timer) clearInterval(prog.timer);
  prog.timer = null;
  if (ctx) muteAll(ctx.currentTime);
  Array.prototype.forEach.call($("prog-view").children, (s) => s.classList.remove("now"));
  $("prog-count").textContent = "";
  $("prog-play").disabled = false;
  $("prog-stop").disabled = true;
}

/* ---------- Mediciones y comprobación ---------- */

function showMetrics() {
  const rows = [];
  if (ctx) {
    rows.push(["Frecuencia de muestreo", ctx.sampleRate + " Hz"]);
    rows.push(["Latencia base / de salida", ((ctx.baseLatency || 0) * 1000).toFixed(1) + " / " + ((ctx.outputLatency || 0) * 1000).toFixed(1) + " ms"]);
  } else rows.push(["Audio", "se activa con el primer toque"]);
  rows.push(["Peso del motor A", "0 KB de audio (se sintetiza en el navegador)"]);
  Object.keys(metrics).forEach((k) => rows.push([k, metrics[k]]));
  const table = $("metrics");
  table.textContent = "";
  rows.forEach(([k, v]) => {
    const tr = document.createElement("tr"), th = document.createElement("th"), td = document.createElement("td");
    th.textContent = k; td.textContent = v;
    tr.appendChild(th); tr.appendChild(td); table.appendChild(tr);
  });
}

/* Tres acordes comprobados a mano: G abierto, C abierto y F con cejilla. */
function selfCheck() {
  const cases = [
    ["G", [43, 47, 50, 55, 59, 67]],
    ["C", [null, 48, 52, 55, 60, 64]],
    ["F", [41, 48, 53, 57, 60, 65]],
  ];
  const lines = cases.map(([name, want]) => {
    const r = formsFor(name);
    const got = r.error ? r.error : toMidi(r.list[0].frets);
    const ok = !r.error && JSON.stringify(got) === JSON.stringify(want);
    const fmt = (a) => (Array.isArray(a) ? a.map((x) => (x === null ? "x" : x)).join(" ") : a);
    return '<div class="' + (ok ? "ok" : "bad") + '">' + (ok ? "✓" : "✗") + " " + name + " → " + fmt(got) + (ok ? "" : " (esperado " + fmt(want) + ")") + "</div>";
  });
  const t = '<div class="' + (JSON.stringify(tuning) === "[40,45,50,55,59,64]" ? "ok" : "bad") + '">Afinación ' + tuning.map(midiName).join(" ") + "</div>";
  $("selfcheck").innerHTML = t + lines.join("");
  $("selfcheck").dataset.ok = String(!$("selfcheck").querySelector(".bad"));
}

/* ---------- Arranque ---------- */

async function init() {
  try {
    const res = await fetch(DATA_URL);
    db = await res.json();
    tuning = db.afinacion;
  } catch (e) {
    $("selfcheck").innerHTML = '<span class="bad">No pude leer ' + DATA_URL + ": corre el laboratorio con lab/midi/servir.sh</span>";
    return;
  }
  selfCheck();
  renderChord();
  renderProgression();
  showMetrics();

  document.querySelectorAll("input[name=engine]").forEach((r) => r.addEventListener("change", () => {
    $("ks-opts").hidden = engine() !== "ks";
    $("smp-opts").hidden = engine() !== "samples";
    muteAll(ctx ? ctx.currentTime : 0);
  }));
  ["ks-bright", "ks-sustain"].forEach((id) => $(id).addEventListener("change", () => ksCache.clear()));
  $("ks-body").addEventListener("input", applyBody);
  $("vol").addEventListener("input", () => { if (master) master.gain.value = +$("vol").value; });
  $("spread").addEventListener("input", () => { $("spread-v").textContent = $("spread").value + " ms"; });
  $("bpm").addEventListener("input", () => { $("bpm-v").textContent = $("bpm").value; if (prog.timer) prog.slotDur = 60 / +$("bpm").value / 2; });
  $("smp-load").addEventListener("click", loadSamples);
  ["smp-bank", "smp-set"].forEach((id) => $(id).addEventListener("change", () => { $("smp-status").textContent = ""; }));
  $("chord").addEventListener("input", () => { formIndex = 0; renderChord(); });
  $("form-prev").addEventListener("click", () => { formIndex--; renderChord(); });
  $("form-next").addEventListener("click", () => { formIndex++; renderChord(); });
  $("theme-forms").addEventListener("input", () => {
    const box = $("theme-errors");
    box.textContent = "";
    parseThemeForms($("theme-forms").value).errors.forEach((e) => {
      const d = document.createElement("div"); d.className = "bad"; d.textContent = e; box.appendChild(d);
    });
    formIndex = 0; renderChord(); renderProgression();
  });
  $("play-down").addEventListener("click", () => playChord("D"));
  $("play-up").addEventListener("click", () => playChord("U"));
  $("play-arp").addEventListener("click", () => playChord("arp"));
  $("prog").addEventListener("input", renderProgression);
  $("pattern").addEventListener("change", () => { $("pattern-custom").hidden = $("pattern").value !== "custom"; });
  $("prog-play").addEventListener("click", startProgression);
  $("prog-stop").addEventListener("click", stopProgression);
}

init();

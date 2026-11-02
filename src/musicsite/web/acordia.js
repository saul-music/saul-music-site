/* Acordia · utilidades compartidas (sin dependencias, aparte de Bootstrap) */
(function () {
  "use strict";
  var root = document.documentElement;
  var KEY = "acordia-tema";

  /* Tema: el script en <head> ya aplicó el guardado; aquí solo el botón */
  function setTheme(t) {
    root.setAttribute("data-bs-theme", t);
    try { localStorage.setItem(KEY, t); } catch (e) {}
    document.querySelectorAll("[data-ac-theme-toggle]").forEach(function (b) {
      b.setAttribute("aria-label", t === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
    });
  }
  document.querySelectorAll("[data-ac-theme-toggle]").forEach(function (b) {
    b.addEventListener("click", function () {
      setTheme(root.getAttribute("data-bs-theme") === "light" ? "dark" : "light");
    });
  });
  setTheme(root.getAttribute("data-bs-theme") || "dark");

  /* Diagramas de acorde.
     <div class="ac-chord" data-name="G" data-frets="3 2 0 0 0 3"></div>
     frets de 6ª a 1ª cuerda: número = traste, 0 = al aire, x = no suena. */
  var NS = "http://www.w3.org/2000/svg";
  function el(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  document.querySelectorAll(".ac-chord[data-frets]").forEach(function (box) {
    var frets = box.getAttribute("data-frets").split(/\s+/);
    var nums = frets.filter(function (f) { return /^\d+$/.test(f) && +f > 0; }).map(Number);
    var max = nums.length ? Math.max.apply(null, nums) : 1;
    var base = max > 4 ? Math.min.apply(null, nums) : 1;
    var x0 = 14, y0 = 22, sx = 14, sy = 18, rows = 4;
    var svg = el("svg", { viewBox: "0 0 98 120", role: "img",
      "aria-label": "Acorde " + box.getAttribute("data-name") });
    for (var s = 0; s < 6; s++)
      svg.appendChild(el("line", { x1: x0 + s * sx, y1: y0, x2: x0 + s * sx, y2: y0 + rows * sy, class: "grid", "stroke-width": 1.5 }));
    for (var r = 0; r <= rows; r++)
      svg.appendChild(el("line", { x1: x0, y1: y0 + r * sy, x2: x0 + 5 * sx, y2: y0 + r * sy,
        class: r === 0 && base === 1 ? "nut" : "grid", "stroke-width": r === 0 && base === 1 ? 4 : 1.5 }));
    if (base > 1) {
      var t = el("text", { x: 2, y: y0 + sy * .7, "font-size": 11, fill: "currentColor" });
      t.textContent = base; svg.appendChild(t);
    }
    frets.forEach(function (f, i) {
      var cx = x0 + i * sx;
      if (f === "x") {
        svg.appendChild(el("path", { d: "M" + (cx - 4) + " 6l8 8M" + (cx + 4) + " 6l-8 8", class: "mute", "stroke-width": 1.8 }));
      } else if (f === "0") {
        svg.appendChild(el("circle", { cx: cx, cy: 10, r: 4.5, class: "open", "stroke-width": 1.8 }));
      } else {
        var row = +f - base;
        svg.appendChild(el("circle", { cx: cx, cy: y0 + row * sy + sy / 2, r: 5.5, class: "dot" }));
      }
    });
    var name = document.createElement("span");
    name.className = "ac-chord-name";
    name.textContent = box.getAttribute("data-name");
    box.appendChild(name);
    box.appendChild(svg);
  });

  /* Lista de práctica con progreso (se recuerda en este navegador) */
  document.querySelectorAll("[data-ac-practice]").forEach(function (list) {
    var id = "acordia-practica-" + list.getAttribute("data-ac-practice");
    var boxes = list.querySelectorAll("input[type=checkbox]");
    var bar = document.querySelector(list.getAttribute("data-ac-progress"));
    var label = document.querySelector(list.getAttribute("data-ac-progress-label"));
    var saved = [];
    try { saved = JSON.parse(localStorage.getItem(id) || "[]"); } catch (e) {}
    boxes.forEach(function (b, i) { b.checked = saved[i] === true; });
    function update() {
      var done = 0, state = [];
      boxes.forEach(function (b) { if (b.checked) done++; state.push(b.checked); });
      var pct = Math.round(done / boxes.length * 100);
      if (bar) { bar.style.width = pct + "%"; bar.parentElement.setAttribute("aria-valuenow", pct); }
      if (label) label.textContent = done + " de " + boxes.length + " pasos";
      try { localStorage.setItem(id, JSON.stringify(state)); } catch (e) {}
    }
    boxes.forEach(function (b) { b.addEventListener("change", update); });
    update();
  });

  /* Filtro de guías.
     <form data-ac-filter="#resultados" data-ac-count="#conteo" data-ac-empty="#sin-resultados">
       <select data-ac-key="barrio">…  <input type="checkbox" data-ac-key="hoy" value="1">
     Cada tarjeta: <div class="col" data-barrio="Rock,Pop" data-hoy="1">
     Un valor coincide si está en la lista separada por comas de la tarjeta.
     Con ?tema=slug en la URL solo quedan las tarjetas cuyo data-temas incluye ese tema. */
  document.querySelectorAll("form[data-ac-filter]").forEach(function (form) {
    var items = document.querySelectorAll(form.getAttribute("data-ac-filter") + " > *");
    var count = document.querySelector(form.getAttribute("data-ac-count"));
    var empty = document.querySelector(form.getAttribute("data-ac-empty"));
    var fields = form.querySelectorAll("[data-ac-key]");
    var tema = new URLSearchParams(window.location.search).get("tema");
    var aviso = document.getElementById("aviso-tema");
    if (tema && aviso) aviso.classList.remove("d-none");
    function run() {
      var n = 0;
      items.forEach(function (it) {
        var ok = true;
        if (tema && (it.getAttribute("data-temas") || "").split(",").indexOf(tema) === -1) ok = false;
        fields.forEach(function (f) {
          var v = f.type === "checkbox" ? (f.checked ? f.value : "") : f.value;
          if (!v) return;
          var list = (it.getAttribute("data-" + f.getAttribute("data-ac-key")) || "").split(",");
          if (list.indexOf(v) === -1) ok = false;
        });
        it.hidden = !ok;
        if (ok) n++;
      });
      if (count) count.textContent = n === 1 ? "1 guía" : n + " guías";
      if (empty) empty.classList.toggle("d-none", n > 0);
    }
    fields.forEach(function (f) { f.addEventListener("change", run); });
    form.addEventListener("submit", function (e) { e.preventDefault(); });
    run();
    /* Enlace directo a una guía (#guia-id): el filtro cambia el alto de la página, así que se
       desplaza a su tarjeta después de filtrar y se la marca. */
    var target = window.location.hash ? document.getElementById(window.location.hash.slice(1)) : null;
    if (target && !target.hidden) {
      target.classList.add("is-target");
      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      target.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
    }
  });

  /* Modal de conexión: copia nombre y precio del botón que lo abrió */
  document.querySelectorAll(".modal[data-ac-connect]").forEach(function (modal) {
    modal.addEventListener("show.bs.modal", function (e) {
      var b = e.relatedTarget; if (!b) return;
      var n = modal.querySelector("[data-guia-nombre]");
      var p = modal.querySelector("[data-guia-precio]");
      if (n) n.textContent = b.getAttribute("data-guia") || "tu guía";
      if (p) p.textContent = b.getAttribute("data-precio") || "—";
    });
  });

  /* Formularios del prototipo: no envían nada a ningún servidor */
  document.querySelectorAll("form[data-ac-demo]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      var go = f.getAttribute("data-ac-demo");
      if (go) window.location.href = go;
    });
  });
  /* Bloque fijo de la canción: se pega justo bajo la barra de navegación, cuya altura varía. */
  (function () {
    var nav = document.querySelector(".navbar.sticky-top");
    if (!nav) return;
    function set() { document.documentElement.style.setProperty("--ac-nav-h", nav.offsetHeight + "px"); }
    set();
    window.addEventListener("resize", set);
    if (window.ResizeObserver) new ResizeObserver(set).observe(nav);
  })();
  /* Una sola entrada a las guías que cambia de forma: la franja de arriba mientras se ve; al salir de
     pantalla, un botón corto en la barra fija, para tentarse cuando una parte se complica. */
  (function () {
    var strip = document.querySelector(".ac-met-strip");
    var help = document.querySelector("[data-ac-met-help]");
    if (!strip || !help || !window.IntersectionObserver) return;
    new IntersectionObserver(function (entries) {
      help.hidden = entries[entries.length - 1].isIntersecting;
    }).observe(strip);
  })();
  /* Desplegable de guías: se cierra con Escape o al tocar fuera, y se trae a la vista al abrir. */
  (function () {
    var panel = document.getElementById("guias-panel");
    if (!panel || !window.bootstrap) return;
    var collapse = window.bootstrap.Collapse.getOrCreateInstance(panel, { toggle: false });
    panel.addEventListener("shown.bs.collapse", function () {
      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      panel.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") collapse.hide(); });
    document.addEventListener("click", function (e) {
      if (!panel.classList.contains("show")) return;
      if (e.target.closest("#guias-panel, [data-bs-target='#guias-panel']")) return;
      collapse.hide();
    });
  })();
  /* Metrónomo de la página de canción: Web Audio con agenda anticipada (el reloj del audio, no
     setInterval, decide cuándo suena cada clic). Arranca en el bpm del tema. */
  document.querySelectorAll("[data-ac-metronome]").forEach(function (box) {
    var home = +box.getAttribute("data-bpm") || 90;
    var beats = +box.getAttribute("data-beats") || 4;
    var MIN = 30, MAX = 240, AHEAD = 0.12, TICK = 25;
    var bpm = home, playing = false, muted = false, ctx = null, timer = null, nextTime = 0, beat = 0, count = 0;
    var cur = { pane: null, seq: [], idx: -1, counter: null, group: null };
    var MUTE_KEY = "acordia-sin-sonido";
    var toggle = box.querySelector("[data-ac-met-toggle]");
    var mute = box.querySelector("[data-ac-met-mute]");
    var input = box.querySelector("[data-ac-met-bpm]");
    var range = box.querySelector("[data-ac-met-range]");
    var dotsBox = box.querySelector("[data-ac-met-dots]");
    var dots = [];
    for (var i = 0; i < beats; i++) {
      var d = document.createElement("span");
      d.className = "ac-met-dot" + (i === 0 ? " is-first" : "");
      dotsBox.appendChild(d);
      dots.push(d);
    }

    function clamp(v) {
      v = Math.round(+v);
      if (!isFinite(v)) return bpm;
      return Math.min(MAX, Math.max(MIN, v));
    }
    function setBpm(v) {
      bpm = clamp(v);
      input.value = bpm;
      range.value = bpm;
    }
    function click(time, accent) {
      var osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.frequency.value = accent ? 1568 : 1047;
      gain.gain.setValueAtTime(0.0001, time);
      gain.gain.exponentialRampToValueAtTime(accent ? 0.9 : 0.55, time + 0.002);
      gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.06);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(time);
      osc.stop(time + 0.07);
    }
    /* Cursor de compás: aplana las secciones de la pestaña visible (cada una × sus repeticiones) y
       marca el compás por el que va el pulso, con una flecha encima y su "n / N". */
    function activePane() { return document.querySelector(".tab-pane.active") || document; }
    function buildSeq(pane) {
      var seq = [];
      pane.querySelectorAll(".ac-bars").forEach(function (g) {
        var reps = +g.getAttribute("data-reps") || 1;
        var bars = g.querySelectorAll(".ac-bar");
        for (var r = 1; r <= reps; r++) {
          bars.forEach(function (el) { seq.push({ el: el, group: g, rep: r, reps: reps }); });
        }
      });
      return seq;
    }
    function clearCounter() {
      if (cur.counter) cur.counter.remove();
      cur.counter = null;
      cur.group = null;
    }
    function clearCursor() {
      document.querySelectorAll(".ac-bar.is-current, .ac-bar.is-beat").forEach(function (b) {
        b.classList.remove("is-current", "is-beat", "is-downbeat");
      });
      clearCounter();
      cur.pane = null; cur.seq = []; cur.idx = -1;
    }
    function keepInView(el) {
      var tools = document.querySelector(".ac-sticky-tools");
      var top = (tools ? tools.getBoundingClientRect().bottom : 0) + 12;
      var r = el.getBoundingClientRect();
      if (r.top >= top && r.bottom <= window.innerHeight - 12) return;
      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      var target = top + (window.innerHeight - top) / 3;
      window.scrollTo({ top: window.scrollY + r.top - target, behavior: reduce ? "auto" : "smooth" });
    }
    function cursor(n) {
      var pane = activePane();
      if (pane !== cur.pane) { clearCursor(); cur.pane = pane; cur.seq = buildSeq(pane); }
      if (!cur.seq.length) return;
      var i = Math.floor(n / beats) % cur.seq.length;
      var step = cur.seq[i];
      if (i !== cur.idx) {
        if (cur.idx >= 0) cur.seq[cur.idx].el.classList.remove("is-current");
        if (cur.group !== step.group) {
          clearCounter();
          var h = step.group.previousElementSibling;
          if (step.reps > 1 && h) {
            cur.counter = document.createElement("span");
            cur.counter.className = "ac-rep-count ac-mono";
            h.appendChild(cur.counter);
            cur.group = step.group;
          }
        }
        if (cur.counter) cur.counter.textContent = step.rep + " / " + step.reps;
        step.el.classList.add("is-current");
        cur.idx = i;
        keepInView(step.el);
      }
      var el = step.el, first = n % beats === 0;
      el.classList.add("is-beat");
      el.classList.toggle("is-downbeat", first);
      setTimeout(function () { el.classList.remove("is-beat", "is-downbeat"); },
        Math.min(160, 60000 / bpm * 0.55));
    }
    /* Reloj: con sonido, el del audio (preciso); en "sin sonido", el del navegador, que no depende
       de ninguna salida de audio. Los tiempos de agenda están en el reloj del modo vigente. */
    function clock() { return muted || !ctx ? performance.now() / 1000 : ctx.currentTime; }
    function flash(index, time, n) {
      setTimeout(function () {
        if (!playing) return;
        dots.forEach(function (x, k) { x.classList.toggle("is-on", k === index); });
        cursor(n);
      }, Math.max(0, (time - clock()) * 1000));
    }
    function schedule() {
      if (!muted) {
        /* Safari: con el contexto suspendido (o "interrupted" en iOS) el reloj no corre; no se agenda. */
        if (!ctx || ctx.state !== "running") {
          if (ctx && ctx.resume) ctx.resume();
          return;
        }
      }
      var now = clock();
      if (nextTime < now) nextTime = now + 0.06;
      while (nextTime < now + AHEAD) {
        if (!muted) click(nextTime, beat === 0);
        flash(beat, nextTime, count);
        count++;
        nextTime += 60 / bpm;
        beat = (beat + 1) % beats;
      }
    }
    /* iOS silencia Web Audio con el interruptor de silencio; "playback" lo evita (Safari 16.4+).
       Sin sonido no se toca: así no interrumpe la música que el usuario escucha en otra app. */
    function unlockIOS() {
      try {
        if (navigator.audioSession) navigator.audioSession.type = "playback";
      } catch (e) { /* sin soporte */ }
    }
    function ensureAudio() {
      var Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) return null;
      unlockIOS();
      if (!ctx) ctx = new Ctor();
      /* resume() es asíncrono en Safari: se agenda cuando el reloj ya corre. */
      var p = ctx.resume ? ctx.resume() : null;
      return p && p.then ? p : { then: function (f) { f(); } };
    }
    function begin() {
      if (!playing) return;
      beat = 0;
      count = 0;
      nextTime = clock() + 0.06;
      schedule();
    }
    function start() {
      if (!muted && !(window.AudioContext || window.webkitAudioContext)) return;
      playing = true;
      clearInterval(timer);
      timer = setInterval(schedule, TICK);
      toggle.textContent = "Detener";
      toggle.setAttribute("aria-pressed", "true");
      if (muted) { begin(); return; }
      var audio = ensureAudio();
      audio.then(begin, begin);
    }
    function stop() {
      playing = false;
      clearInterval(timer);
      dots.forEach(function (x) { x.classList.remove("is-on"); });
      clearCursor();
      toggle.textContent = "Reproducir";
      toggle.setAttribute("aria-pressed", "false");
    }
    /* Cambia de modo sin cortar ni descompasar: se conserva lo que falta para el próximo pulso. */
    function setMuted(value, save) {
      var remaining = playing ? Math.max(nextTime - clock(), 0.02) : 0;
      muted = !!value;
      if (mute) mute.setAttribute("aria-pressed", muted ? "true" : "false");
      if (save) { try { localStorage.setItem(MUTE_KEY, muted ? "1" : "0"); } catch (e) {} }
      if (!playing) return;
      if (muted) { nextTime = clock() + remaining; return; }
      var audio = ensureAudio();
      if (!audio) { muted = true; return; }
      audio.then(function () { nextTime = clock() + remaining; });
    }

    if (mute) {
      var saved = null;
      try { saved = localStorage.getItem(MUTE_KEY); } catch (e) {}
      if (saved === "1") setMuted(true, false);
      mute.addEventListener("click", function () { setMuted(!muted, true); });
    }
    toggle.addEventListener("click", function () { playing ? stop() : start(); });
    input.addEventListener("change", function () { setBpm(input.value); });
    range.addEventListener("input", function () { setBpm(range.value); });
    box.querySelectorAll("[data-ac-met-step]").forEach(function (b) {
      b.addEventListener("click", function () { setBpm(bpm + +b.getAttribute("data-ac-met-step")); });
    });
    box.querySelector("[data-ac-met-reset]").addEventListener("click", function () { setBpm(home); });
    document.addEventListener("visibilitychange", function () { if (document.hidden && playing) stop(); });
  });
})();

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

  /* Diagramas de acorde. guitarSVG recibe los trastes absolutos de la 6ª a la 1ª cuerda
     (0 = al aire, -1 = no suena) y, si hay, los dedos y las cejillas. */
  var NS = "http://www.w3.org/2000/svg";
  function el(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function guitarSVG(frets, fingers, barres, label) {
    var played = frets.filter(function (f) { return f > 0; });
    var max = played.length ? Math.max.apply(null, played) : 1;
    var base = max > 4 ? Math.min.apply(null, played) : 1;
    var x0 = 14, y0 = 22, sx = 14, sy = 18, rows = Math.max(4, max - base + 1);
    var svg = el("svg", { viewBox: "0 0 98 " + (y0 + rows * sy + 6), role: "img",
      "aria-label": "Acorde " + label });
    for (var s = 0; s < 6; s++)
      svg.appendChild(el("line", { x1: x0 + s * sx, y1: y0, x2: x0 + s * sx, y2: y0 + rows * sy, class: "grid", "stroke-width": 1.5 }));
    for (var r = 0; r <= rows; r++)
      svg.appendChild(el("line", { x1: x0, y1: y0 + r * sy, x2: x0 + 5 * sx, y2: y0 + r * sy,
        class: r === 0 && base === 1 ? "nut" : "grid", "stroke-width": r === 0 && base === 1 ? 4 : 1.5 }));
    if (base > 1) {
      var t = el("text", { x: 2, y: y0 + sy * .7, "font-size": 11, fill: "currentColor" });
      t.textContent = base; svg.appendChild(t);
    }
    (barres || []).forEach(function (b) {
      var idx = [];
      frets.forEach(function (f, i) { if (f === b) idx.push(i); });
      if (idx.length < 2) return;
      var cy = y0 + (b - base) * sy + sy / 2;
      svg.appendChild(el("rect", { x: x0 + idx[0] * sx - 5.5, y: cy - 5.5, width: (idx[idx.length - 1] - idx[0]) * sx + 11,
        height: 11, rx: 5.5, class: "dot" }));
    });
    frets.forEach(function (f, i) {
      var cx = x0 + i * sx;
      if (f < 0) {
        svg.appendChild(el("path", { d: "M" + (cx - 4) + " 6l8 8M" + (cx + 4) + " 6l-8 8", class: "mute", "stroke-width": 1.8 }));
      } else if (f === 0) {
        svg.appendChild(el("circle", { cx: cx, cy: 10, r: 4.5, class: "open", "stroke-width": 1.8 }));
      } else {
        var cy = y0 + (f - base) * sy + sy / 2;
        svg.appendChild(el("circle", { cx: cx, cy: cy, r: 5.5, class: "dot" }));
        if (fingers && fingers[i] > 0) {
          var n = el("text", { x: cx, y: cy + 3.5, "text-anchor": "middle", "font-size": 9, class: "finger" });
          n.textContent = fingers[i]; svg.appendChild(n);
        }
      }
    });
    return svg;
  }
  /* Dos octavas desde un do: `keys` son las teclas del acorde (0 a 23) y `bass`, el bajo (0 a 11). */
  function pianoSVG(keys, bass, label) {
    var WHITE = [0, 2, 4, 5, 7, 9, 11], BLACK = { 1: 0, 3: 1, 6: 3, 8: 4, 10: 5 };
    var w = 13, h = 64, svg = el("svg", { viewBox: "0 0 " + 14 * w + " " + (h + 4), role: "img",
      "aria-label": "Teclas del acorde " + label });
    function cls(k) { return "key" + (keys.indexOf(k) >= 0 ? " on" : "") + (bass === k ? " bass" : ""); }
    for (var o = 0; o < 2; o++) {
      WHITE.forEach(function (pc, i) {
        svg.appendChild(el("rect", { x: (o * 7 + i) * w, y: 2, width: w, height: h, rx: 1.5, class: cls(o * 12 + pc) }));
      });
    }
    for (var o2 = 0; o2 < 2; o2++) {
      for (var pc in BLACK) {
        var k = o2 * 12 + +pc;
        svg.appendChild(el("rect", { x: (o2 * 7 + BLACK[pc]) * w + w * .65, y: 2, width: w * .7, height: h * .6,
          rx: 1.2, class: cls(k) + " black" }));
      }
    }
    return svg;
  }
  document.querySelectorAll(".ac-chord[data-frets]").forEach(function (box) {
    var frets = box.getAttribute("data-frets").split(/\s+/).map(function (f) { return f === "x" ? -1 : +f; });
    var name = document.createElement("span");
    name.className = "ac-chord-name";
    name.textContent = box.getAttribute("data-name");
    box.appendChild(name);
    box.appendChild(guitarSVG(frets, null, null, box.getAttribute("data-name")));
  });

  /* Panel de acorde en la página de canción: al pasar el cursor (escritorio) o al tocar. Los datos
     vienen del JSON de la página: forma estándar de guitarra, teclas y la forma propia de la versión. */
  (function () {
    var dataEl = document.getElementById("acordes-data");
    var buttons = document.querySelectorAll(".ac-chord-btn");
    if (!dataEl || !buttons.length) return;
    var data;
    try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
    var KEY = "acordia-instrumento";
    var instrument = "guitarra";
    try { var saved = localStorage.getItem(KEY); if (saved === "teclado" || saved === "guitarra") instrument = saved; } catch (e) {}
    var panel, nameEl, notesEl, tabs = {}, body, tabEl, badge, next, noteEl;
    var anchor = null, pinned = false, form = 0, timer = null;
    var phone = window.matchMedia ? window.matchMedia("(max-width: 575.98px)") : { matches: false };

    function node(tag, cls, text) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text) n.textContent = text;
      return n;
    }
    function build() {
      panel = node("div", "ac-chord-panel");
      panel.setAttribute("role", "dialog");
      panel.hidden = true;
      var head = node("div", "ac-cp-head");
      nameEl = node("strong", "ac-cp-name");
      notesEl = node("span", "ac-cp-notes");
      var close = node("button", "btn-close");
      close.type = "button";
      close.setAttribute("aria-label", "Cerrar");
      close.addEventListener("click", function () { hide(true); });
      head.appendChild(nameEl); head.appendChild(notesEl); head.appendChild(close);
      var tabBar = node("div", "ac-cp-tabs");
      [["guitarra", "Guitarra"], ["teclado", "Teclado"]].forEach(function (pair) {
        var b = node("button", "btn btn-sm", pair[1]);
        b.type = "button";
        b.addEventListener("click", function () {
          instrument = pair[0];
          try { localStorage.setItem(KEY, instrument); } catch (e) {}
          render();
        });
        tabs[pair[0]] = b; tabBar.appendChild(b);
      });
      body = node("div", "ac-chord ac-cp-body");
      tabEl = node("pre", "ac-mono ac-cp-tab");
      noteEl = node("p", "ac-cp-note");
      var foot = node("div", "ac-cp-foot");
      badge = node("span", "ac-chip ac-chip-ok", "Forma de esta versión");
      next = node("button", "btn btn-sm btn-outline-primary ac-cp-next");
      next.type = "button";
      next.addEventListener("click", function () { form++; render(); });
      foot.appendChild(badge); foot.appendChild(next);
      [head, tabBar, body, tabEl, noteEl, foot].forEach(function (n) { panel.appendChild(n); });
      panel.addEventListener("pointerenter", function () { clearTimeout(timer); });
      panel.addEventListener("pointerleave", function (e) { if (e.pointerType === "mouse" && !pinned) schedule(); });
      document.body.appendChild(panel);
    }
    function forms() {
      var name = anchor.getAttribute("data-chord");
      var mode = (anchor.closest(".tab-pane") || {}).id || "";
      mode = mode.replace(/^p-/, "");
      var own = (data.own[mode] || {})[name];
      var list = own ? [{ frets: own.frets, tab: own.tab, own: true }] : [];
      return list.concat((data.chords[name] || {}).guitar || []);
    }
    function render() {
      var name = anchor.getAttribute("data-chord");
      var chord = data.chords[name];
      if (!chord) return hide(true);
      nameEl.textContent = chord.label;
      notesEl.textContent = chord.notes.join(" · ");
      panel.setAttribute("aria-label", "Acorde " + chord.label);
      for (var k in tabs) {
        tabs[k].className = "btn btn-sm " + (k === instrument ? "btn-primary" : "btn-outline-primary");
        tabs[k].setAttribute("aria-pressed", k === instrument ? "true" : "false");
      }
      body.textContent = "";
      var list = forms();
      if (instrument === "teclado") {
        body.appendChild(pianoSVG(chord.keys, chord.bass, chord.label));
        tabEl.hidden = true; noteEl.hidden = true; badge.hidden = true; next.hidden = true;
      } else if (!list.length) {
        tabEl.hidden = true; badge.hidden = true; next.hidden = true;
        noteEl.hidden = false;
        noteEl.textContent = "Sin diagrama de guitarra para este acorde. Mira el teclado.";
      } else {
        form = ((form % list.length) + list.length) % list.length;
        var f = list[form];
        body.appendChild(guitarSVG(f.frets, f.fingers, f.barres, chord.label));
        tabEl.hidden = false; tabEl.textContent = f.tab.join("\n");
        noteEl.hidden = true;
        badge.hidden = !f.own;
        next.hidden = list.length < 2;
        next.textContent = "Otra forma (" + (form + 1) + "/" + list.length + ")";
      }
      place();
    }
    function place() {
      if (phone.matches) { panel.style.top = ""; panel.style.left = ""; return; }
      var r = anchor.getBoundingClientRect();
      var w = panel.offsetWidth, h = panel.offsetHeight;
      var left = Math.max(8, Math.min(r.left + window.scrollX + r.width / 2 - w / 2,
        document.documentElement.clientWidth - w - 8));
      var below = r.bottom + 8, top = below + window.scrollY;
      if (below + h > window.innerHeight && r.top - h - 8 > 0) top = r.top - h - 8 + window.scrollY;
      panel.style.left = left + "px";
      panel.style.top = top + "px";
    }
    function show(btn, hold) {
      clearTimeout(timer);
      if (!panel) build();
      if (anchor && anchor !== btn) anchor.setAttribute("aria-expanded", "false");
      if (anchor !== btn) form = 0;
      anchor = btn;
      pinned = !!hold;
      panel.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      render();
    }
    function hide(restoreFocus) {
      clearTimeout(timer);
      if (!panel || panel.hidden) return;
      panel.hidden = true;
      if (anchor) {
        anchor.setAttribute("aria-expanded", "false");
        if (restoreFocus) anchor.focus();
      }
      pinned = false;
    }
    function schedule() { clearTimeout(timer); timer = setTimeout(function () { hide(false); }, 250); }

    buttons.forEach(function (btn) {
      btn.setAttribute("aria-expanded", "false");
      btn.addEventListener("pointerenter", function (e) {
        if (e.pointerType !== "mouse" || (panel && !panel.hidden && pinned)) return;
        clearTimeout(timer);
        timer = setTimeout(function () { show(btn, false); }, 120);
      });
      btn.addEventListener("pointerleave", function (e) {
        if (e.pointerType === "mouse" && !pinned) schedule();
      });
      btn.addEventListener("click", function (e) {
        if (panel && !panel.hidden && anchor === btn && pinned) return hide(false);
        show(btn, true);
        if (e.detail === 0 && tabs.guitarra) tabs[instrument].focus();  // con teclado, al panel
      });
    });
    document.addEventListener("click", function (e) {
      if (!panel || panel.hidden) return;
      if (e.target.closest(".ac-chord-panel, .ac-chord-btn")) return;
      hide(false);
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(true); });
    window.addEventListener("resize", function () { if (panel && !panel.hidden) place(); });
  })();

  /* Título y artista fijos: aparecen en la barra fija cuando el encabezado sale de pantalla. */
  (function () {
    var strip = document.querySelector("[data-ac-sticky-title]");
    var heading = document.querySelector("main header h1");
    if (!strip || !heading || !window.IntersectionObserver) return;
    new IntersectionObserver(function (entries) {
      strip.hidden = entries[entries.length - 1].isIntersecting;
    }).observe(heading);
  })();

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
    var COUNT_IN = 4, countIn = true, pre = 0;
    var cur = { pane: null, seq: [], idx: -1, counter: null, group: null };
    var MUTE_KEY = "acordia-sin-sonido", COUNT_KEY = "acordia-cuenta-inicial";
    var toggle = box.querySelector("[data-ac-met-toggle]");
    var mute = box.querySelector("[data-ac-met-mute]");
    var countBtn = box.querySelector("[data-ac-met-countin]");
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
    function flash(index, time, n, isCount) {
      setTimeout(function () {
        if (!playing) return;
        dots.forEach(function (x, k) { x.classList.toggle("is-on", k === index); });
        if (!isCount) cursor(n);
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
        /* Cuenta inicial: suena (si hay sonido) y parpadea, pero el cursor de compases no avanza. */
        var isCount = pre > 0;
        if (!muted) click(nextTime, isCount ? pre === COUNT_IN : beat === 0);
        flash(isCount ? COUNT_IN - pre : beat, nextTime, count, isCount);
        nextTime += 60 / bpm;
        if (isCount) { pre--; continue; }
        count++;
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
      pre = countIn ? COUNT_IN : 0;
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
    /* La cuenta inicial (4 clics) viene activada; se puede desactivar y la elección se recuerda. */
    function setCountIn(value, save) {
      countIn = !!value;
      if (countBtn) countBtn.setAttribute("aria-pressed", countIn ? "true" : "false");
      if (save) { try { localStorage.setItem(COUNT_KEY, countIn ? "1" : "0"); } catch (e) {} }
    }
    if (countBtn) {
      var savedCount = null;
      try { savedCount = localStorage.getItem(COUNT_KEY); } catch (e) {}
      if (savedCount === "0") setCountIn(false, false);
      countBtn.addEventListener("click", function () { setCountIn(!countIn, true); });
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

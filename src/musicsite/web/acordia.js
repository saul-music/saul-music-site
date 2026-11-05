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
    /* Formas de guitarra de un acorde en un nivel, en este orden (S27): forma propia del nivel (S8),
       forma por defecto del tema, y las estándar (ya ordenadas por la regla de cejilla). */
    function formsFor(name, mode) {
      var list = [], seen = {};
      function add(f, kind) {
        var key = f.frets.join(",");
        if (seen[key]) return;
        seen[key] = true;
        f.kind = kind;
        list.push(f);
      }
      var own = (data.own[mode] || {})[name];
      if (own) add({ frets: own.frets, tab: own.tab }, "own");
      var def = (data.default || {})[name];
      if (def) add({ frets: def.frets, tab: def.tab }, "default");
      ((data.chords[name] || {}).guitar || []).forEach(function (g) { add(g, ""); });
      return list;
    }
    function modeOf(el) {
      el = el.classList.contains("tab-pane") ? el : el.closest(".tab-pane");
      return ((el || {}).id || "").replace(/^p-/, "");
    }
    function forms() {
      return formsFor(anchor.getAttribute("data-chord"), modeOf(anchor));
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
        var gn = chord.guitar_note;  // diagrama del acorde base: el bajo no está dibujado (S19)
        var bassNote = chord.bass !== null && chord.bass !== undefined && chord.label.indexOf("/") >= 0 ? chord.label.split("/").pop() : "";
        noteEl.hidden = !((gn && !f.kind) || bassNote);
        if (gn && !f.kind) noteEl.textContent = "Diagrama de " + gn.base + ". El bajo (" + gn.bass + ") no está dibujado, pero si activas la guitarra suena como bajo.";
        else if (bassNote) noteEl.textContent = "El bajo (" + bassNote + ") suena aparte, como bajo, si activas la guitarra.";
        badge.hidden = !f.kind;
        badge.textContent = f.kind === "default" ? "Forma de este tema" : "Forma de esta versión";
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

    /* Resumen plegado de posiciones (S28): al inicio de cada pestaña, un <details> cerrado con la guitarra
       y el piano de todos los acordes de ESA pestaña, con la forma que se vería al tocarlos (formsFor).
       Se dibuja la primera vez que se abre, así la carga de la página no cambia. */
    function chordsOfPane(pane) {
      var seen = {}, names = [];
      pane.querySelectorAll(".ac-chord-btn").forEach(function (b) {
        var n = b.getAttribute("data-chord");
        if (!seen[n] && data.chords[n]) { seen[n] = true; names.push(n); }
      });
      return names;
    }
    function summaryItem(name, mode) {
      var chord = data.chords[name];
      var item = node("figure", "ac-sum-item");
      item.appendChild(node("figcaption", "ac-sum-name", chord.label));
      var g = formsFor(name, mode)[0];
      var guitar = node("div", "ac-chord ac-sum-guitar");
      if (g) guitar.appendChild(guitarSVG(g.frets, g.fingers, g.barres, chord.label));
      else guitar.appendChild(node("span", "ac-sum-none", "Sin diagrama de guitarra"));
      item.appendChild(guitar);
      var piano = node("div", "ac-sum-piano");
      piano.appendChild(pianoSVG(chord.keys, chord.bass, chord.label));
      item.appendChild(piano);
      return item;
    }
    document.querySelectorAll(".tab-pane").forEach(function (pane) {
      var names = chordsOfPane(pane);
      var intro = pane.querySelector(":scope > .d-grid > p");
      if (!names.length || !intro) return;
      var mode = modeOf(pane);
      var det = node("details", "ac-summary");
      var sum = node("summary", "", "Posiciones de los acordes (" + names.length + ")");
      var grid = node("div", "ac-sum-grid");
      det.appendChild(sum); det.appendChild(grid);
      det.addEventListener("toggle", function () {
        if (!det.open || grid.childNodes.length) return;
        var frag = document.createDocumentFragment();
        names.forEach(function (n) { frag.appendChild(summaryItem(n, mode)); });
        grid.appendChild(frag);
      });
      intro.insertAdjacentElement("afterend", det);
    });

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

  /* Buscadores de la Biblioteca: el de la portada pasa su texto al de la galería, que es el que queda lleno.
     Filtra tarjetas por título o artista (sin tildes ni mayúsculas, todas las palabras); desde la portada,
     buscar además lleva a la Biblioteca con solo los grupos que coinciden. */
  (function () {
    var form = document.querySelector("form[data-ac-search]");
    var lib = document.getElementById("biblioteca");
    var inner = document.getElementById("buscar-biblioteca");
    if (!lib || !inner) return;
    var hero = form && form.querySelector("input");
    var empty = document.getElementById("sin-resultados");
    var count = document.getElementById("lib-count");
    var clear = document.getElementById("lib-clear");
    function norm(t) { return (t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(); }
    function filter(value) {
      var words = norm(value).split(/\s+/).filter(Boolean);
      var shown = 0, total = 0, head = null, headHas = false;
      function closeHead() { if (head) head.hidden = !headHas; }
      Array.prototype.forEach.call(lib.querySelectorAll(".row > .col, .row > .ac-artist-head"), function (el) {
        if (el.classList.contains("ac-artist-head")) { closeHead(); head = el; headHas = false; return; }
        var text = norm(Array.prototype.map.call(el.querySelectorAll("h4, p"), function (n) { return n.textContent; }).join(" "));
        var ok = words.every(function (w) { return text.indexOf(w) !== -1; });
        el.hidden = !ok;
        total++;
        if (ok) { shown++; headHas = true; }
      });
      closeHead();
      if (empty) empty.hidden = shown > 0 || !words.length;
      if (count) count.textContent = words.length ? shown + " de " + total + " temas" : "";
      if (clear) clear.hidden = !words.length;
    }
    /* El texto vive en el campo de la galería; el de la portada solo lo escribe y, al buscar, se vacía. */
    function apply() { filter(inner.value); }
    inner.addEventListener("input", apply);
    if (hero) hero.addEventListener("input", function () { inner.value = hero.value; apply(); });
    if (clear) clear.addEventListener("click", function () { inner.value = ""; apply(); inner.focus(); });
    /* Enlace con búsqueda (?q=Artista, p. ej. desde la sección Artistas): llena el buscador de la galería
       y deja la Biblioteca a la vista. Es solo texto del buscador: se asigna como valor, nunca como HTML. */
    try {
      var q = new URLSearchParams(window.location.search).get("q");
      if (q) {
        inner.value = q.slice(0, 100);
        apply();
        window.addEventListener("load", function () { lib.scrollIntoView({ block: "start" }); });
      }
    } catch (e) { /* sin URLSearchParams: la Biblioteca queda sin filtrar */ }
    if (form) form.addEventListener("submit", function (e) {
      e.preventDefault();
      inner.value = hero.value;
      hero.value = "";
      apply();
      var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      lib.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "start" });
    });
  })();
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
  /* Tips entre secciones: se abren con un toque; los ya vistos dejan de brillar (se recuerda aquí). */
  (function () {
    var KEY = "acordia-tips-vistos", seen = [];
    try { seen = JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) {}
    document.querySelectorAll("[data-ac-tip]").forEach(function (tip) {
      var id = tip.getAttribute("data-ac-tip");
      var btn = tip.querySelector(".ac-tip-btn"), body = tip.querySelector(".ac-tip-body");
      if (seen.indexOf(id) >= 0) tip.classList.add("is-seen");
      btn.addEventListener("click", function () {
        var open = btn.getAttribute("aria-expanded") !== "true";
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        body.hidden = !open;
        if (open && seen.indexOf(id) < 0) {
          seen.push(id);
          tip.classList.add("is-seen");
          try { localStorage.setItem(KEY, JSON.stringify(seen)); } catch (e) {}
        }
      });
    });
  })();
  /* Metrónomo de la página de canción: Web Audio con agenda anticipada (el reloj del audio, no
     setInterval, decide cuándo suena cada clic). Arranca en el bpm del tema. */
  document.querySelectorAll("[data-ac-metronome]").forEach(function (box) {
    var home = +box.getAttribute("data-bpm") || 90;
    var beats = +box.getAttribute("data-beats") || 4;
    var MIN = 30, MAX = 240, AHEAD = 0.12, TICK = 25;
    var bpm = home, playing = false, muted = false, ctx = null, timer = null, nextTime = 0, beat = 0, count = 0;
    var COUNT_IN = 4, countIn = true, pre = 0, endTimer = null;
    var cur = { pane: null, seq: [], idx: -1, counter: null, group: null };
    var MUTE_KEY = "acordia-sin-sonido", COUNT_KEY = "acordia-cuenta-inicial";
    var toggle = box.querySelector("[data-ac-met-toggle]");
    var mute = box.querySelector("[data-ac-met-mute]");
    var countBtn = box.querySelector("[data-ac-met-countin]");
    var input = box.querySelector("[data-ac-met-bpm]");
    var range = box.querySelector("[data-ac-met-range]");
    var dotsBox = box.querySelector("[data-ac-met-dots]");
    var label = toggle.querySelector("[data-ac-met-label]");
    var countBox = toggle.querySelector("[data-ac-met-count]");
    var countNums = [];
    /* Cuenta inicial: mientras cuenta, el botón muestra 1 2 3 4 con el actual resaltado. Los
       números solo existen en el DOM durante la cuenta (el texto del botón queda limpio). */
    function showCount(index) {
      if (index < 0) {
        if (countNums.length) { countBox.textContent = ""; countNums = []; }
        toggle.classList.remove("is-counting");
        toggle.style.width = toggle.style.height = "";
        return;
      }
      if (!countNums.length) {
        /* El botón conserva el tamaño que tenía: la barra fija no puede crecer ni cambiar de fila. */
        var w = toggle.offsetWidth, h = toggle.offsetHeight;
        for (var k = 1; k <= COUNT_IN; k++) {
          var s = document.createElement("span");
          s.textContent = k;
          countBox.appendChild(s);
          countNums.push(s);
        }
        toggle.style.width = w + "px";
        toggle.style.height = h + "px";
        toggle.classList.add("is-counting");
      }
      countNums.forEach(function (x, k) { x.classList.toggle("is-on", k === index); });
    }
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
    /* Volumen del metrónomo (0 a 1, S39): se recuerda por dispositivo. */
    var metVol = 1;
    var volMet = box.querySelector("[data-ac-vol-met]");
    try { var savedVol = parseFloat(localStorage.getItem("ac-vol-met")); if (isFinite(savedVol)) metVol = Math.min(1, Math.max(0, savedVol)); } catch (e) { /* sin almacenamiento */ }
    if (volMet) {
      var volMetOut = volMet.parentNode.querySelector("[data-ac-vol-out]");
      var showMetVol = function () { if (volMetOut) volMetOut.textContent = Math.round(metVol * 100) + "%"; };
      volMet.value = Math.round(metVol * 100);
      showMetVol();
      volMet.addEventListener("input", function () {
        metVol = volMet.value / 100;
        showMetVol();
        try { localStorage.setItem("ac-vol-met", String(metVol)); } catch (e) { /* sin almacenamiento */ }
      });
    }
    function click(time, accent) {
      if (metVol <= 0) return;
      var osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.frequency.value = accent ? 1568 : 1047;
      gain.gain.setValueAtTime(0.0001, time);
      gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, (accent ? 0.9 : 0.55) * metVol), time + 0.002);
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
    /* Laboratorio S37: el compás que suena en el pulso n, en el momento de agendarlo (el cursor va después). */
    var audioSeq = { pane: null, seq: [] };
    function barAt(n) {
      var pane = activePane();
      if (audioSeq.pane !== pane) { audioSeq.pane = pane; audioSeq.seq = buildSeq(pane); }
      var seq = audioSeq.seq;
      if (!seq.length) return null;
      return seq[(startIndex(seq) + Math.floor(n / beats)) % seq.length].el;
    }
    function clearCounter() {
      if (cur.counter) cur.counter.remove();
      cur.counter = null;
      cur.group = null;
    }
    function clearCursor() {
      document.querySelectorAll(".ac-bar.is-current, .ac-bar.is-beat, .ac-part.is-beat").forEach(function (b) {
        b.classList.remove("is-current", "is-beat", "is-downbeat");
      });
      clearCounter();
      cur.pane = null; cur.seq = []; cur.idx = -1;
    }
    /* El compás actual se mantiene centrado entre la barra fija y el borde de la ventana. Si la
       persona hace scroll a mano (rueda, dedo o teclado), el seguimiento se pausa unos segundos. */
    var PAUSE_MS = 4000, pausedUntil = 0;
    function userScrolled() { pausedUntil = Date.now() + PAUSE_MS; }
    ["wheel", "touchmove", "keydown"].forEach(function (ev) {
      window.addEventListener(ev, userScrolled, { passive: true });
    });
    function keepInView(el, instant) {
      if (!instant && Date.now() < pausedUntil) return;
      var tools = document.querySelector(".ac-sticky-tools");
      var top = (tools ? tools.getBoundingClientRect().bottom : 0) + 12;
      var r = el.getBoundingClientRect();
      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      var target = top + (window.innerHeight - top - r.height) / 2;
      if (Math.abs(r.top - target) < 2) return;
      window.scrollTo({ top: window.scrollY + r.top - target, behavior: reduce || instant ? "auto" : "smooth" });
    }
    /* Qué se ilumina en este pulso: la casilla entera, o, si trae varios acordes, solo la parte que
       dura ese pulso (las partes se reparten el compás en proporción a su duración). */
    function beatTarget(bar, inBar) {
      var parts = bar.querySelectorAll(".ac-part");
      if (!parts.length) return bar;
      var total = 0, w = [];
      parts.forEach(function (p) { var v = +p.getAttribute("data-weight") || 1; w.push(v); total += v; });
      var slot = Math.floor(inBar * total / beats), acc = 0;
      for (var k = 0; k < parts.length; k++) {
        acc += w[k];
        if (slot < acc) return parts[k];
      }
      return parts[parts.length - 1];
    }
    /* Compás de partida: la bandera elegida, si está en la pestaña visible (en su primera pasada). */
    var startBar = null;
    function startIndex(seq) {
      if (!startBar || !seq.length) return 0;
      for (var k = 0; k < seq.length; k++) {
        if (seq[k].el === startBar && seq[k].rep === 1) return k;
      }
      return 0;
    }
    /* Al cambiar de nivel la bandera pasa al mismo número de compás del panel nuevo. */
    function moveStart(pane) {
      if (!startBar) return;
      var from = startBar.closest(".tab-pane");
      if (!from || from === pane) return;
      var n = Array.prototype.indexOf.call(from.querySelectorAll(".ac-bar"), startBar);
      var to = pane.querySelectorAll(".ac-bar")[n] || null;
      setStart(to);
    }
    function setStart(bar) {
      hideRestart();
      if (startBar) {
        startBar.classList.remove("is-start");
        var old = startBar.querySelector(".ac-start-flag");
        if (old) old.setAttribute("aria-pressed", "false");
      }
      startBar = bar === startBar ? null : bar;
      if (startBar) {
        startBar.classList.add("is-start");
        startBar.querySelector(".ac-start-flag").setAttribute("aria-pressed", "true");
      }
    }
    document.querySelectorAll(".ac-bars .ac-bar").forEach(function (bar) {
      var flag = document.createElement("button");
      flag.type = "button";
      flag.className = "ac-start-flag";
      flag.setAttribute("aria-pressed", "false");
      flag.setAttribute("aria-label", "Partir desde este compás");
      flag.title = "Partir desde aquí";
      flag.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">'
        + '<path d="M6 3v18h2v-7h9l-2-4 2-4H8V3z"/></svg>';
      flag.addEventListener("click", function (e) { e.stopPropagation(); setStart(bar); });
      bar.appendChild(flag);
    });
    function cursor(n) {
      var pane = activePane();
      if (pane !== cur.pane) { clearCursor(); cur.pane = pane; cur.seq = buildSeq(pane); }
      if (!cur.seq.length) return;
      var i = (startIndex(cur.seq) + Math.floor(n / beats)) % cur.seq.length;
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
      var inBar = n % beats, first = inBar === 0;
      var el = beatTarget(step.el, inBar);
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
        showCount(isCount ? index : -1);
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
        /* Fin de la pasada: tras el último pulso del último compás (última repetición) se detiene todo. */
        if (pre === 0 && count >= passBeats()) {
          clearInterval(timer);
          clearTimeout(endTimer);
          endTimer = setTimeout(finish, Math.max(0, (nextTime - clock()) * 1000));
          return;
        }
        /* Cuenta inicial: suena (si hay sonido) y parpadea, pero el cursor de compases no avanza. */
        var isCount = pre > 0;
        if (!muted) click(nextTime, isCount ? pre === COUNT_IN : beat === 0);
        flash(isCount ? COUNT_IN - pre : beat, nextTime, count, isCount);
        /* Laboratorio S37: la guitarra recibe cada tiempo (no la cuenta) con su compás. */
        if (!isCount && !muted && window.AcordiaGuitar) {
          var gp = activePane();
          window.AcordiaGuitar.beat(ctx, nextTime, barAt(count), count % beats, beats, (gp.id || "").replace(/^p-/, ""));
        }
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
    /* Al activar «Guitarra» se crea el audio (hay un toque del usuario) y se bajan las muestras,
       para que el primer acorde ya suene con nailon. */
    document.addEventListener("acordia-guitar-on", function () {
      ensureAudio();
      if (ctx && window.AcordiaGuitar) window.AcordiaGuitar.prepare(ctx);
    });
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
      pausedUntil = 0;
      if (startBar && activePane().contains(startBar)) keepInView(startBar);
      clearInterval(timer);
      timer = setInterval(schedule, TICK);
      label.textContent = "Detener";
      toggle.setAttribute("aria-pressed", "true");
      if (muted) { begin(); return; }
      var audio = ensureAudio();
      audio.then(begin, begin);
    }
    function stop() {
      playing = false;
      if (window.AcordiaGuitar) window.AcordiaGuitar.stop(ctx);
      clearInterval(timer);
      clearTimeout(endTimer);
      dots.forEach(function (x) { x.classList.remove("is-on"); });
      showCount(-1);
      clearCursor();
      label.textContent = "Reproducir";
      toggle.setAttribute("aria-pressed", "false");
    }
    /* Total de pulsos de una pasada en el nivel visible: compases desde el de partida, con repeticiones. */
    function passBeats() {
      var seq = buildSeq(activePane());
      return Math.max(0, seq.length - startIndex(seq)) * beats;
    }
    var restart = box.querySelector("[data-ac-met-restart]");
    var statusBox = box.querySelector("[data-ac-met-status]");
    function hideRestart() {
      if (!restart || restart.hidden) return;
      restart.hidden = true;
      toggle.hidden = false;
      if (statusBox) statusBox.textContent = "";
    }
    function finish() {
      if (!playing) return;
      stop();
      setStart(null);  // terminó el tema: ningún compás queda marcado, ni cursor ni bandera
      toggle.hidden = true;
      restart.hidden = false;
      if (statusBox) statusBox.textContent = "Terminó la pasada";
      restart.focus({ preventScroll: true });
    }
    /* «Volver al inicio»: lleva el scroll al primer compás del nivel visible, sin reproducir. */
    if (restart) restart.addEventListener("click", function () {
      hideRestart();
      var seq = buildSeq(activePane());
      if (seq.length) { pausedUntil = 0; keepInView(seq[0].el, true); }
      toggle.focus({ preventScroll: true });
    });
    /* Cambiar de nivel (barra o hash) no corta la reproducción: el cursor sigue en el mismo compás. */
    document.addEventListener("shown.bs.tab", function (e) {
      var target = e.target && e.target.getAttribute("data-bs-target");
      var pane = target && document.querySelector(target);
      if (!pane) return;
      moveStart(pane);
      hideRestart();
    });
    /* Cambia de modo sin cortar ni descompasar: se conserva lo que falta para el próximo pulso. */
    /* «Opciones» (celular) avisa que «Sin sonido» está activo aunque el panel esté plegado. */
    var optMute = box.querySelector("[data-ac-met-options-mute]");
    function syncOptionsMute() {
      if (optMute) optMute.hidden = !muted;
      var ob = box.querySelector("[data-ac-met-options]");
      if (!ob) return;
      ob.setAttribute("aria-label", muted ? "Opciones (sin sonido activado)" : "Opciones");
      if (muted) ob.setAttribute("title", "Sin sonido activado"); else ob.removeAttribute("title");
    }
    function setMuted(value, save) {
      var remaining = playing ? Math.max(nextTime - clock(), 0.02) : 0;
      muted = !!value;
      if (mute) mute.setAttribute("aria-pressed", muted ? "true" : "false");
      syncOptionsMute();
      if (save) { try { localStorage.setItem(MUTE_KEY, muted ? "1" : "0"); } catch (e) {} }
      if (!playing) return;
      if (muted) { if (window.AcordiaGuitar) window.AcordiaGuitar.stop(ctx); nextTime = clock() + remaining; return; }
      var audio = ensureAudio();
      if (!audio) { muted = true; syncOptionsMute(); return; }
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
    /* Opciones (celular): el botón existe siempre pero solo se muestra en ≤ 575 px (CSS). Despliega y
       repliega los controles secundarios; no toca el estado del metrónomo. Escape lo cierra si el foco está dentro. */
    var optBtn = box.querySelector("[data-ac-met-options]");
    var extra = box.querySelector("[data-ac-met-extra]");
    if (optBtn && extra) {
      var setOptions = function (open) {
        extra.classList.toggle("is-open", open);
        optBtn.setAttribute("aria-expanded", open ? "true" : "false");
      };
      optBtn.addEventListener("click", function () { setOptions(optBtn.getAttribute("aria-expanded") !== "true"); });
      extra.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && optBtn.getAttribute("aria-expanded") === "true") { setOptions(false); optBtn.focus(); }
      });
    }
    document.addEventListener("visibilitychange", function () { if (document.hidden && playing) stop(); });
  });
  /* Nivel en la URL: #basico, #intermedio o #avanzado abre ese nivel y compartirlo lleva a él. */
  (function () {
    var buttons = document.querySelectorAll("#tabs [data-bs-toggle=pill]");
    if (!buttons.length || !window.bootstrap) return;
    function keyOf(btn) { return btn.id.replace(/^t-/, ""); }
    function show(key) {
      for (var k = 0; k < buttons.length; k++) {
        if (keyOf(buttons[k]) === key) { window.bootstrap.Tab.getOrCreateInstance(buttons[k]).show(); return; }
      }
    }
    var first = window.location.hash.slice(1);
    if (first) show(first);
    document.addEventListener("shown.bs.tab", function (e) {
      if (!e.target.closest || !e.target.closest("#tabs")) return;
      try { history.replaceState(null, "", "#" + keyOf(e.target)); } catch (err) {}
    });
    window.addEventListener("hashchange", function () { show(window.location.hash.slice(1)); });
  })();
})();

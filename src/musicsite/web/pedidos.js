/* Pide una canción (DEMO, S25): formularios que no envían nada y una lista de pedidos de ejemplo cuyos
   estados cambian solos. Todo es ficticio: sin nombres, correos ni datos reales.

   Punto de conexión futuro: la lista lee de una "fuente" (createSource). Hoy es DemoSource, que simula
   cambios con un temporizador. Una fuente real en tiempo real solo debe cumplir lo mismo:
       source.subscribe(onChange) -> unsubscribe
   donde onChange recibe la lista completa [{id, title, artist, level, status}] cada vez que algo cambia.
   Ni la lista ni el resto de la página saben de dónde vienen los datos; no hay red ni dependencias. */
(function () {
  var STATUSES = [
    { key: "received", label: "Recibida" },
    { key: "review", label: "En revisión" },
    { key: "preparing", label: "En preparación" },
    { key: "published", label: "Publicada" }
  ];

  /* --- Fuente de datos (el único lugar a reemplazar) --- */
  function DemoSource(intervalMs) {
    /* Canciones del repertorio ya público o genéricas; sin letras ni acordes. */
    var pool = [
      ["Bailando solo", "Los Bunkers", "Básico"],
      ["Ven aquí", "Los Bunkers", "Intermedio"],
      ["Cámara lenta", "Javiera Mena", "Avanzado"],
      ["Déjate caer", "Los Tres", "Básico"],
      ["Una canción de cuna (ejemplo)", "Tradicional", "Básico"],
      ["Un vals criollo (ejemplo)", "Tradicional", "Intermedio"],
      ["Una balada de fogata (ejemplo)", "Autor de ejemplo", "Básico"],
      ["Una cueca para guitarra (ejemplo)", "Tradicional", "Avanzado"]
    ];
    var items = [], next = 0, turn = 0, listeners = [], timer = null, serial = 0;
    function add(status) {
      var p = pool[next++ % pool.length];
      serial++;
      items.unshift({ id: "demo-" + serial, title: p[0], artist: p[1], level: p[2], status: status });
    }
    [3, 2, 1, 0].forEach(add); /* hay un pedido en cada etapa al empezar */
    function snapshot() { return items.map(function (i) { return Object.assign({}, i); }); }
    function emit(change) { var s = snapshot(); listeners.forEach(function (fn) { fn(s, change); }); }
    function tick() {
      var item = items[turn % items.length];
      turn++;
      if (item.status < 3) {
        item.status++;
        emit({ id: item.id, title: item.title, status: item.status });
      } else {
        /* un pedido publicado sale de la lista y entra uno nuevo como recibido */
        items.splice(items.indexOf(item), 1);
        add(0);
        emit({ id: items[0].id, title: items[0].title, status: 0, isNew: true });
      }
    }
    return {
      subscribe: function (fn) {
        listeners.push(fn);
        fn(snapshot(), null);
        if (!timer) timer = setInterval(tick, intervalMs);
        return function () {
          listeners = listeners.filter(function (l) { return l !== fn; });
          if (!listeners.length && timer) { clearInterval(timer); timer = null; }
        };
      }
    };
  }

  function createSource() { return new DemoSource(5000); }

  /* --- Lista (no depende de la fuente) --- */
  function reduced() { return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches; }

  function build(item) {
    var li = document.createElement("li");
    li.className = "ac-req card";
    li.dataset.reqId = item.id;
    var body = document.createElement("div");
    body.className = "card-body d-grid gap-2";
    var top = document.createElement("div");
    top.className = "d-flex flex-wrap align-items-center gap-2 justify-content-between";
    var name = document.createElement("div");
    var h = document.createElement("h3");
    h.className = "h5 m-0";
    h.textContent = item.title;
    var meta = document.createElement("p");
    meta.className = "m-0 small text-body-secondary";
    meta.textContent = item.artist + " · Nivel " + item.level.toLowerCase();
    name.append(h, meta);
    var badges = document.createElement("div");
    badges.className = "d-flex flex-wrap gap-2 align-items-center";
    var state = document.createElement("span");
    state.className = "ac-req-state";
    var demo = document.createElement("span");
    demo.className = "ac-demo-badge ac-demo-badge-sm";
    demo.textContent = "Demo / datos de ejemplo";
    badges.append(state, demo);
    top.append(name, badges);
    var bar = document.createElement("div");
    bar.className = "ac-req-bar";
    bar.setAttribute("role", "img");
    for (var i = 0; i < STATUSES.length; i++) {
      var seg = document.createElement("span");
      seg.className = "ac-req-seg";
      bar.appendChild(seg);
    }
    body.append(top, bar);
    li.appendChild(body);
    return li;
  }

  function paint(li, item) {
    var s = STATUSES[item.status];
    var state = li.querySelector(".ac-req-state");
    state.textContent = s.label;
    state.dataset.status = s.key;
    var bar = li.querySelector(".ac-req-bar");
    bar.setAttribute("aria-label", "Etapa " + (item.status + 1) + " de " + STATUSES.length + ": " + s.label);
    Array.prototype.forEach.call(bar.children, function (seg, i) { seg.classList.toggle("on", i <= item.status); });
    li.dataset.status = s.key;
  }

  function flash(li) {
    if (reduced()) return;
    li.classList.remove("ac-req-flash");
    void li.offsetWidth; /* reinicia la animación */
    li.classList.add("ac-req-flash");
  }

  function mountList(list, source, announce) {
    var nodes = {};
    source.subscribe(function (items, change) {
      var seen = {};
      items.forEach(function (item, index) {
        seen[item.id] = true;
        var li = nodes[item.id];
        var created = !li;
        if (created) { li = nodes[item.id] = build(item); }
        paint(li, item);
        if (list.children[index] !== li) list.insertBefore(li, list.children[index] || null);
        if (change && change.id === item.id) {
          flash(li);
          if (announce) {
            announce.textContent = change.isNew
              ? "Nuevo pedido de ejemplo: " + item.title + ", recibido."
              : "Pedido de ejemplo «" + item.title + "»: " + STATUSES[item.status].label + ".";
          }
        }
      });
      Object.keys(nodes).forEach(function (id) {
        if (!seen[id]) { nodes[id].remove(); delete nodes[id]; }
      });
    });
  }

  /* --- Formularios de muestra: no leen ni envían nada --- */
  document.querySelectorAll("form[data-ac-mock-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var note = form.querySelector("[data-ac-mock-note]");
      if (note) note.textContent = "Esto es una demostración: no se envió ni se guardó nada.";
    });
  });

  var list = document.querySelector("[data-ac-requests]");
  if (list) {
    var announce = document.querySelector("[data-ac-req-announce]");
    mountList(list, createSource(), announce);
  }
})();

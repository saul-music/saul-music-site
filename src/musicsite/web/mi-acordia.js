// Mi cuenta (S104, S106, C30). Todo texto entra al DOM con textContent, nunca con innerHTML. Lee la sesión de Firebase (la
// misma de /entrar.html y de Aprende) y habla solo con /api/me/*: el navegador nunca toca Firestore.
import { initializeApp } from "https://www.gstatic.com/firebasejs/13.4.0/firebase-app.js";
import { deleteUser, getAuth, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/13.4.0/firebase-auth.js";

const $ = (id) => document.getElementById(id);
const apiKey = document.querySelector('meta[name="firebase-api-key"]').content;
const SESSION_HINT = "acordia-session"; // «hay una sesión»: las páginas de tema solo cargan Firebase si existe (S105)
const INSTRUMENTS = { guitarra: "Guitarra", teclado: "Teclado", bajo: "Bajo", otro: "Otro instrumento" };
const LEVELS = { inicial: "Nivel inicial", medio: "Nivel medio", avanzado: "Nivel avanzado" };

const h = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null && v !== false) node.setAttribute(k, v);
  node.append(...children.flat().filter((c) => c !== "" && c != null && c !== false));
  return node;
};
const fail = (message) => { $("error").textContent = message; $("error").hidden = !message; };
const hint = (on) => { try { on ? localStorage.setItem(SESSION_HINT, "1") : localStorage.removeItem(SESSION_HINT); } catch { /* sin almacenamiento */ } };
const stars = (n) => h("span", { class: "ac-stars", role: "img", "aria-label": `${n} de 3 estrellas` }, "★".repeat(n) + "☆".repeat(3 - n));
const prettySong = (slug) => slug.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

let titles = {};
const titleOf = (slug) => titles[slug] ?? prettySong(slug);
let auth = null;
let leaving = false; // al borrar o cerrar sesión, el aviso de «sin sesión» no debe pisar el mensaje propio
const data = { profile: {}, cont: {}, progress: {}, catalog: [], favorites: [], repertoires: [] };

async function api(path, options = {}) {
  const token = await auth.currentUser.getIdToken();
  const response = await fetch(path ? `/api/me/${path}` : "/api/me", {
    ...options,
    headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw Object.assign(new Error(`api ${response.status}`), { status: response.status });
  return response.status === 204 ? null : response;
}

// --- lo que se calcula con lo guardado (sin datos nuevos)
function paths() {
  const { catalog, progress } = data;
  return catalog.length ? catalog : Object.keys(progress).map((id) => ({ id, title: id, lessons: Object.keys(progress[id]).map((l) => ({ id: l, title: l })) }));
}

function totals() {
  let played = 0, total = 0, starsGot = 0, points = 0, threeStars = 0;
  for (const p of paths()) {
    const mine = data.progress[p.id] ?? {};
    total += p.lessons.length;
    for (const l of p.lessons) {
      const r = mine[l.id];
      if (!r) continue;
      played += 1; starsGot += r.stars; points += r.points;
      if (r.stars === 3) threeStars += 1;
    }
  }
  return { played, total, stars: starsGot, maxStars: total * 3, points, threeStars, complete: total > 0 && played === total };
}

const BADGES = [
  { icon: "▶", name: "Primera lección", how: "Juega una lección", earned: (t) => t.played >= 1 },
  { icon: "★", name: "Tres estrellas", how: "Saca 3 estrellas en una lección", earned: (t) => t.threeStars >= 1 },
  { icon: "◐", name: "A mitad de camino", how: "Juega la mitad de las lecciones", earned: (t) => t.total > 0 && t.played * 2 >= t.total },
  { icon: "✓", name: "Ruta completa", how: "Juega todas las lecciones", earned: (t) => t.complete },
  { icon: "♥", name: "Primer favorito", how: "Marca un tema como favorito", earned: (_t, d) => d.favorites.length >= 1 },
  { icon: "♪", name: "Primer repertorio", how: "Crea un repertorio", earned: (_t, d) => d.repertoires.length >= 1 },
];

// --- pantalla
function renderHeader() {
  const { name, instrument, level } = data.profile;
  $("saludo").textContent = name ? `Hola, ${name}` : "Tu cuenta";
  const chips = [INSTRUMENTS[instrument], LEVELS[level]].filter(Boolean);
  $("chips").replaceChildren(...chips.map((c) => h("li", {}, c)));
  $("chips").hidden = chips.length === 0;
}

function renderContinue() {
  const { cont, catalog } = data;
  const cards = [];
  if (cont.lesson) {
    const lesson = catalog.find((p) => p.id === cont.lesson.path)?.lessons.find((l) => l.id === cont.lesson.lesson);
    cards.push(h("a", { href: `/aprende/#/${cont.lesson.path}/${cont.lesson.lesson}` }, h("small", {}, "Tu última lección"), h("strong", {}, lesson?.title ?? cont.lesson.lesson), h("span", {}, "Seguir →")));
  }
  if (cont.song) {
    cards.push(h("a", { href: `cancion-${cont.song}.html` }, h("small", {}, "Tu último tema"), h("strong", {}, titleOf(cont.song)), h("span", {}, "Abrir →")));
  }
  if (!cards.length) {
    cards.push(h("a", { href: "/aprende/" }, h("small", {}, "Para empezar"), h("strong", {}, "Tu primera lección en Aprende"), h("span", {}, "Empezar →")));
  }
  $("continuar").replaceChildren(...cards);
}

function renderStats() {
  const t = totals();
  const stat = (value, label) => h("li", { class: "ac-stat" }, h("b", {}, String(value)), h("span", {}, label));
  $("cifras").replaceChildren(
    stat(`${t.played}/${t.total}`, "lecciones jugadas"),
    stat(`${t.stars}/${t.maxStars}`, "estrellas"),
    stat(t.points, "puntos"),
    stat(data.favorites.length, plural(data.favorites.length, "favorito", "favoritos")),
    stat(data.repertoires.length, plural(data.repertoires.length, "repertorio", "repertorios")));
}

function renderBadges() {
  const t = totals();
  $("insignias").replaceChildren(...BADGES.map((b) => {
    const on = b.earned(t, data);
    return h("li", { class: `ac-badge ${on ? "is-on" : "is-off"}`, "aria-label": `Insignia ${b.name}: ${on ? "lograda" : "por lograr"}` },
      h("i", { "aria-hidden": "true" }, b.icon), h("strong", {}, b.name), h("small", {}, on ? "¡Lograda!" : b.how));
  }));
}

function renderProgress() {
  $("avance").replaceChildren(...paths().map((p) => {
    const mine = data.progress[p.id] ?? {};
    const played = p.lessons.filter((l) => mine[l.id]);
    const starsGot = played.reduce((n, l) => n + mine[l.id].stars, 0);
    const points = played.reduce((n, l) => n + mine[l.id].points, 0);
    const pct = p.lessons.length ? Math.round((played.length / p.lessons.length) * 100) : 0;
    const bar = (value, label) => h("div", { class: "progress", role: "progressbar", "aria-label": label, "aria-valuenow": String(value), "aria-valuemin": "0", "aria-valuemax": "100" },
      h("div", { class: "progress-bar", style: `width:${value}%` }));
    return h("section", { class: "ac-card ac-path-card", "aria-label": `Ruta ${p.title}` },
      h("div", { class: "d-flex flex-wrap justify-content-between align-items-baseline gap-2" },
        h("strong", { class: "fs-5" }, p.title), h("span", {}, `${played.length}/${p.lessons.length} lecciones · ${starsGot}/${p.lessons.length * 3} estrellas · ${points} puntos`)),
      bar(pct, `Avance de ${p.title}`),
      h("div", { class: "ac-lesson-grid" }, p.lessons.map((l, i) => {
        const r = mine[l.id];
        return h("a", { class: `ac-lesson-card${r ? " is-played" : ""}`, href: `/aprende/#/${p.id}/${l.id}` },
          h("div", { class: "ac-lesson-head" }, h("strong", {}, `${i + 1}. ${l.title}`), r ? stars(r.stars) : ""),
          bar(r ? r.points : 0, `Puntos de ${l.title}`),
          h("span", { class: "small text-body-secondary" }, r ? `${r.points} pts · ${plural(r.plays, "vez", "veces")} jugada` : "Sin jugar · Empezar →"));
      })));
  }));
}

function renderFavorites() {
  $("favoritos").replaceChildren(...(data.favorites.length ? data.favorites.map((slug) => {
    const remove = h("button", { type: "button", class: "btn btn-sm btn-outline-secondary", "aria-label": `Quitar ${titleOf(slug)} de favoritos` }, "Quitar");
    remove.addEventListener("click", async () => {
      fail("");
      try {
        data.favorites = (await (await api("favorites", { method: "PUT", body: JSON.stringify({ song: slug, favorite: false }) })).json()).favorites;
        renderFavorites(); renderStats(); renderBadges();
      } catch { fail("No se pudo quitar. Intenta de nuevo."); }
    });
    return h("li", {}, h("a", { href: `cancion-${slug}.html` }, titleOf(slug)), remove);
  }) : [h("li", {}, h("span", { class: "text-body-secondary" }, "Aún no tienes favoritos. Márcalos con «♡ Favorito» en cada tema."))]));
}

function renderRepertoires() {
  $("repertorios").replaceChildren(...(data.repertoires.length ? data.repertoires.map((r) =>
    h("li", {}, h("a", { href: `repertorio.html?id=${r.id}` }, r.name), h("span", { class: "text-body-secondary" }, plural(r.songs.length, "tema", "temas"))))
    : [h("li", {}, h("span", { class: "text-body-secondary" }, "Aún no tienes repertorios."))]));
}

function fillProfile() {
  $("p-nombre").value = data.profile.name ?? "";
  $("p-instrumento").value = data.profile.instrument ?? "";
  $("p-nivel").value = data.profile.level ?? "";
  renderHeader();
}

function renderAll() {
  fillProfile();
  renderContinue();
  renderStats();
  renderBadges();
  renderProgress();
  renderFavorites();
  renderRepertoires();
}

async function loadAll() {
  const [profile, cont, progress, catalog, favorites, repertoires, songs] = await Promise.all([
    api("profile").then((r) => r.json()).then((b) => b.profile),
    api("continue").then((r) => r.json()).then((b) => b.continue),
    api("progress").then((r) => r.json()).then((b) => b.progress),
    // Aprende publica la lista de sus rutas y lecciones; si no está, se muestra solo lo que hay guardado.
    fetch("/aprende/lessons.json").then((r) => (r.ok ? r.json() : [])).catch(() => []),
    api("favorites").then((r) => r.json()).then((b) => b.favorites),
    api("repertoires").then((r) => r.json()).then((b) => b.repertoires),
    fetch("/songs.json").then((r) => (r.ok ? r.json() : [])).catch(() => []),
  ]);
  titles = Object.fromEntries(songs.map((s) => [s.slug, s.artist ? `${s.title} · ${s.artist}` : s.title]));
  Object.assign(data, { profile, cont, progress, catalog, favorites, repertoires });
  renderAll();
}

// --- pestañas: Resumen y Configuración (el borrado vive solo en Configuración)
function selectTab(name) {
  const tab = name === "configuracion" ? "configuracion" : "resumen";
  for (const id of ["resumen", "configuracion"]) {
    $(`panel-${id}`).hidden = id !== tab;
    $(`tab-${id}`).setAttribute("aria-selected", String(id === tab));
    $(`tab-${id}`).tabIndex = id === tab ? 0 : -1;
  }
  fail("");
}

function wire() {
  for (const id of ["resumen", "configuracion"]) {
    $(`tab-${id}`).addEventListener("click", () => { selectTab(id); history.replaceState(null, "", id === "resumen" ? location.pathname : "#configuracion"); });
  }
  $("tab-resumen").parentElement.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    const next = $("tab-resumen").getAttribute("aria-selected") === "true" ? "configuracion" : "resumen";
    selectTab(next);
    $(`tab-${next}`).focus();
  });
  addEventListener("hashchange", () => selectTab(location.hash.slice(1)));

  $("perfil").addEventListener("submit", async (event) => {
    event.preventDefault();
    fail("");
    $("perfil-estado").textContent = "Guardando…";
    try {
      const body = { name: $("p-nombre").value, instrument: $("p-instrumento").value, level: $("p-nivel").value };
      data.profile = (await (await api("profile", { method: "PUT", body: JSON.stringify(body) })).json()).profile;
      fillProfile();
      $("perfil-estado").textContent = "Guardado.";
    } catch (error) {
      $("perfil-estado").textContent = error.status === 422 ? "Revisa el nombre: hasta 40 letras, sin < ni >." : "No se pudo guardar. Intenta de nuevo.";
    }
  });
  $("nuevo-repertorio").addEventListener("submit", async (event) => {
    event.preventDefault();
    fail("");
    const id = Array.from(crypto.getRandomValues(new Uint8Array(6)), (b) => (b % 36).toString(36)).join("") + "x";
    try {
      await api(`repertoires/${id}`, { method: "PUT", body: JSON.stringify({ name: $("nr-nombre").value, songs: [] }) });
      location.href = `repertorio.html?id=${id}`;
    } catch (error) {
      fail(error.status === 422 ? "Revisa el nombre (hasta 60 letras, sin < ni >) o el máximo de 20 repertorios." : "No se pudo crear. Intenta de nuevo.");
    }
  });
  $("descargar").addEventListener("click", async () => {
    fail("");
    try {
      const url = URL.createObjectURL(await (await api("export")).blob());
      const link = h("a", { href: url, download: "acordia-mis-datos.json" });
      link.click();
      URL.revokeObjectURL(url);
    } catch { fail("No se pudieron preparar tus datos. Intenta de nuevo."); }
  });
  const box = $("borrar-confirmar");
  $("borrar").addEventListener("click", () => { box.hidden = false; $("borrar-si").focus(); });
  $("borrar-no").addEventListener("click", () => { box.hidden = true; });
  // Primero se borra lo nuestro y después la cuenta de Firebase: si el navegador falla en el medio, queda sin consentimiento y
  // `auth-cleanup-unconsented.sh` la recoge (S102).
  $("borrar-si").addEventListener("click", async () => {
    fail("");
    box.hidden = true;
    try { await api("", { method: "DELETE" }); } catch { return fail("No se pudieron eliminar tus datos. No se tocó tu cuenta."); }
    leaving = true;
    try {
      await deleteUser(auth.currentUser);
      hint(false);
      show("sin-sesion", "Eliminamos tu cuenta y tus datos.");
    } catch (error) {
      await signOut(auth);
      hint(false);
      show("sin-sesion", "");
      fail(error?.code === "auth/requires-recent-login"
        ? "Borramos tus datos, pero por seguridad Firebase pide una sesión reciente para eliminar la cuenta. Entra de nuevo y elige «No acepto: eliminar mi cuenta»."
        : "Borramos tus datos, pero no pudimos eliminar la cuenta. Escríbenos a contacto@saulapp.com y la borramos.");
    }
  });
  $("salir").addEventListener("click", async () => { leaving = true; await signOut(auth); hint(false); show("sin-sesion", "Cerraste tu sesión."); });
}

function show(which, message = "") {
  for (const id of ["sin-sesion", "sin-consentimiento", "contenido"]) $(id).hidden = id !== which;
  $("estado").textContent = message;
  $("chips").hidden = which !== "contenido" || $("chips").children.length === 0;
  if (which !== "contenido") $("saludo").textContent = "Tu cuenta";
}

async function start(user) {
  if (!user) { hint(false); return show("sin-sesion", "Entra para ver tu avance."); }
  hint(true);
  try {
    const consent = await (await api("consent")).json();
    if (consent.accepted !== consent.current) return show("sin-consentimiento", "Un paso más.");
    // El contenido se muestra cuando los datos ya están: si no, al terminar de cargar pisarían lo que la persona ya escribió.
    $("estado").textContent = "Cargando tu cuenta…";
    await loadAll();
    selectTab(location.hash.slice(1));
    show("contenido", "");
  } catch (error) {
    show("sin-sesion", "");
    fail(error.status === 404 ? "El sitio no reconoció tu sesión. Entra de nuevo." : "No se pudo consultar tu cuenta. Intenta de nuevo en un minuto.");
  }
}

if (!apiKey) {
  show("sin-sesion", "Tu cuenta no está disponible por ahora.");
  $("entrar").hidden = true;
} else {
  auth = getAuth(initializeApp({ apiKey, authDomain: location.host }));
  wire();
  let first = true;
  onAuthStateChanged(auth, (user) => { if (!leaving && (first || !user)) { first = false; start(user); } });
}

// Mi cuenta (S104, C30). Todo texto entra al DOM con textContent, nunca con innerHTML. Lee la sesión de Firebase (la misma
// de /entrar.html y de Aprende) y habla solo con /api/me/*: el navegador nunca toca Firestore.
import { initializeApp } from "https://www.gstatic.com/firebasejs/13.4.0/firebase-app.js";
import { deleteUser, getAuth, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/13.4.0/firebase-auth.js";

const $ = (id) => document.getElementById(id);
const apiKey = document.querySelector('meta[name="firebase-api-key"]').content;
const SESSION_HINT = "acordia-session"; // «hay una sesión»: las páginas de tema solo cargan Firebase si existe (S105)

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

let auth = null;
let leaving = false; // al borrar o cerrar sesión, el aviso de «sin sesión» no debe pisar el mensaje propio
async function api(path, options = {}) {
  const token = await auth.currentUser.getIdToken();
  const response = await fetch(path ? `/api/me/${path}` : "/api/me", {
    ...options,
    headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw Object.assign(new Error(`api ${response.status}`), { status: response.status });
  return response.status === 204 ? null : response;
}

function renderContinue(cont, catalog) {
  const items = [];
  if (cont.lesson) {
    const path = catalog.find((p) => p.id === cont.lesson.path);
    const lesson = path?.lessons.find((l) => l.id === cont.lesson.lesson);
    items.push(h("li", {}, h("span", {}, "Tu última lección: ", h("strong", {}, lesson?.title ?? cont.lesson.lesson)),
      h("a", { href: `/aprende/#/${cont.lesson.path}/${cont.lesson.lesson}` }, "Seguir →")));
  }
  if (cont.song) {
    items.push(h("li", {}, h("span", {}, "Tu último tema: ", h("strong", {}, prettySong(cont.song))),
      h("a", { href: `cancion-${cont.song}.html` }, "Abrir →")));
  }
  $("continuar").replaceChildren(...(items.length ? items : [h("li", {}, h("span", {}, "Aún no hay nada para continuar. Empieza en "), h("a", { href: "/aprende/" }, "Aprende"), h("span", {}, " o abre un tema de la Biblioteca."))]));
}

function renderProgress(progress, catalog) {
  const paths = catalog.length ? catalog : Object.keys(progress).map((id) => ({ id, title: id, lessons: Object.keys(progress[id]).map((l) => ({ id: l, title: l })) }));
  $("avance").replaceChildren(...paths.map((p) => {
    const mine = progress[p.id] ?? {};
    const played = p.lessons.filter((l) => mine[l.id]);
    const total = played.reduce((n, l) => ({ s: n.s + mine[l.id].stars, p: n.p + mine[l.id].points }), { s: 0, p: 0 });
    return h("div", { class: "d-grid gap-2" },
      h("p", { class: "m-0" }, h("strong", {}, p.title), ` · ${played.length}/${p.lessons.length} lecciones · ${total.s}/${p.lessons.length * 3} estrellas · ${total.p} puntos`),
      h("ul", { class: "ac-lessons" }, p.lessons.map((l) => {
        const r = mine[l.id];
        return h("li", {}, h("a", { href: `/aprende/#/${p.id}/${l.id}` }, l.title),
          r ? h("span", {}, stars(r.stars), ` ${r.points} pts`) : h("span", { class: "text-body-secondary" }, "Sin jugar"));
      })));
  }));
}

function fillProfile(profile) {
  $("p-nombre").value = profile.name ?? "";
  $("p-instrumento").value = profile.instrument ?? "";
  $("p-nivel").value = profile.level ?? "";
  $("saludo").textContent = profile.name ? `Hola, ${profile.name}` : "Tu cuenta";
}

async function loadAll() {
  const [profile, cont, progress, catalog] = await Promise.all([
    api("profile").then((r) => r.json()).then((b) => b.profile),
    api("continue").then((r) => r.json()).then((b) => b.continue),
    api("progress").then((r) => r.json()).then((b) => b.progress),
    // Aprende publica la lista de sus rutas y lecciones; si no está, se muestra solo lo que hay guardado.
    fetch("/aprende/lessons.json").then((r) => (r.ok ? r.json() : [])).catch(() => []),
  ]);
  fillProfile(profile);
  renderContinue(cont, catalog);
  renderProgress(progress, catalog);
}

function wire() {
  $("perfil").addEventListener("submit", async (event) => {
    event.preventDefault();
    fail("");
    $("perfil-estado").textContent = "Guardando…";
    try {
      const body = { name: $("p-nombre").value, instrument: $("p-instrumento").value, level: $("p-nivel").value };
      const saved = (await (await api("profile", { method: "PUT", body: JSON.stringify(body) })).json()).profile;
      fillProfile(saved);
      $("perfil-estado").textContent = "Guardado.";
    } catch (error) {
      $("perfil-estado").textContent = error.status === 422 ? "Revisa el nombre: hasta 40 letras, sin < ni >." : "No se pudo guardar. Intenta de nuevo.";
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

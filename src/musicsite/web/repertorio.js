// Repertorios (S105, C30, C31): la lista ordenable y el reproductor del tema dentro de un iframe del propio sitio
// (`?embed=1`). Cambiar de tema reemplaza el iframe, que corta el audio del anterior. Todo texto con textContent.
import { initializeApp } from "https://www.gstatic.com/firebasejs/13.4.0/firebase-app.js";
import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/13.4.0/firebase-auth.js";

const $ = (id) => document.getElementById(id);
const apiKey = document.querySelector('meta[name="firebase-api-key"]').content;
const h = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null && v !== false) node.setAttribute(k, v);
  node.append(...children.flat().filter((c) => c !== "" && c != null && c !== false));
  return node;
};
const fail = (message) => { $("error").textContent = message; $("error").hidden = !message; };
const newId = () => Array.from(crypto.getRandomValues(new Uint8Array(6)), (b) => (b % 36).toString(36)).join("") + "x";
const prettySong = (slug) => slug.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());

let auth = null;
let titles = {};
let repertoires = [];
let current = null; // el repertorio abierto
let at = 0; // el tema que suena (posición en la lista)

async function api(path, options = {}) {
  const token = await auth.currentUser.getIdToken();
  const response = await fetch(`/api/me/${path}`, {
    ...options,
    headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw Object.assign(new Error(`api ${response.status}`), { status: response.status });
  return response.status === 204 ? null : response.json();
}
const titleOf = (slug) => titles[slug] ?? prettySong(slug);

function view(which, message = "") {
  for (const id of ["sin-sesion", "sin-consentimiento", "lista-repertorios", "uno"]) $(id).hidden = id !== which;
  $("estado").textContent = message;
}

async function save(next) {
  fail("");
  try {
    const saved = await api(`repertoires/${current.id}`, { method: "PUT", body: JSON.stringify({ name: next.name, songs: next.songs }) });
    Object.assign(current, saved);
    return true;
  } catch (error) {
    fail(error.status === 422 ? "No se pudo guardar: revisa el nombre o la lista." : "No se pudo guardar. Intenta de nuevo.");
    return false;
  }
}

function play(index) {
  const songs = current.songs;
  at = Math.min(Math.max(0, index), Math.max(0, songs.length - 1));
  $("marco").hidden = songs.length === 0;
  $("vacio").hidden = songs.length !== 0;
  if (songs.length) {
    // Un iframe nuevo por tema: así el audio del anterior se corta (C31).
    const frame = $("marco");
    frame.removeAttribute("src");
    frame.setAttribute("src", `cancion-${songs[at]}.html?embed=1`);
    $("actual").textContent = `${at + 1}/${songs.length} · ${titleOf(songs[at])}`;
  } else {
    $("actual").textContent = "—";
    $("marco").removeAttribute("src");
  }
  $("anterior").disabled = at === 0;
  $("siguiente").disabled = at >= songs.length - 1;
  paintList();
}

function paintList() {
  $("temas").replaceChildren(...current.songs.map((slug, i) => {
    return h("li", { class: `ac-rep-item${i === at ? " is-actual" : ""}` },
      h("button", { type: "button", class: "btn btn-sm btn-outline-secondary ac-rep-tema", "data-i": String(i) }, titleOf(slug)),
      h("button", { type: "button", class: "btn btn-sm btn-outline-secondary", "aria-label": `Subir ${titleOf(slug)}`, "data-move": "up", disabled: i === 0 ? "" : null }, "▲"),
      h("button", { type: "button", class: "btn btn-sm btn-outline-secondary", "aria-label": `Bajar ${titleOf(slug)}`, "data-move": "down", disabled: i === current.songs.length - 1 ? "" : null }, "▼"),
      h("button", { type: "button", class: "btn btn-sm btn-outline-danger", "aria-label": `Quitar ${titleOf(slug)}`, "data-remove": "1" }, "✕"));
  }));
  // Los oyentes se enlazan aquí: `h` solo pone atributos, no funciones.
  [...$("temas").children].forEach((li, i) => {
    li.querySelector("[data-i]").addEventListener("click", () => play(i));
    li.querySelector("[data-move=up]").addEventListener("click", async () => {
      const songs = [...current.songs]; [songs[i - 1], songs[i]] = [songs[i], songs[i - 1]];
      if (await save({ name: current.name, songs })) play(at === i ? i - 1 : at === i - 1 ? i : at);
    });
    li.querySelector("[data-move=down]").addEventListener("click", async () => {
      const songs = [...current.songs]; [songs[i + 1], songs[i]] = [songs[i], songs[i + 1]];
      if (await save({ name: current.name, songs })) play(at === i ? i + 1 : at === i + 1 ? i : at);
    });
    li.querySelector("[data-remove]").addEventListener("click", async () => {
      const songs = current.songs.filter((_, k) => k !== i);
      if (await save({ name: current.name, songs })) play(i < at ? at - 1 : at);
    });
  });
}

function openOne(rep) {
  current = rep;
  view("uno", "");
  $("titulo").textContent = rep.name;
  $("r-nombre").value = rep.name;
  play(0);
}

function openList() {
  view("lista-repertorios", "Elige un repertorio o crea uno nuevo.");
  $("titulo").textContent = "Tus repertorios";
  $("repertorios").replaceChildren(...(repertoires.length ? repertoires.map((r) =>
    h("li", {}, h("a", { href: `repertorio.html?id=${r.id}` }, r.name), ` · ${r.songs.length} ${r.songs.length === 1 ? "tema" : "temas"}`))
    : [h("li", {}, "Aún no tienes repertorios. Crea uno aquí o desde el botón «＋ Repertorio» de cualquier tema.")]));
}

function wire() {
  $("nuevo").addEventListener("submit", async (event) => {
    event.preventDefault();
    fail("");
    try {
      const made = await api(`repertoires/${newId()}`, { method: "PUT", body: JSON.stringify({ name: $("nuevo-nombre").value, songs: [] }) });
      location.href = `repertorio.html?id=${made.id}`;
    } catch (error) {
      fail(error.status === 422 ? "Revisa el nombre (hasta 60 letras, sin < ni >) o el máximo de 20 repertorios." : "No se pudo crear. Intenta de nuevo.");
    }
  });
  $("r-renombrar").addEventListener("click", async () => {
    if (await save({ name: $("r-nombre").value, songs: current.songs })) { $("titulo").textContent = current.name; $("r-nombre").value = current.name; }
  });
  $("anterior").addEventListener("click", () => play(at - 1));
  $("siguiente").addEventListener("click", () => play(at + 1));
  $("r-borrar").addEventListener("click", () => { $("r-confirmar").hidden = false; $("r-borrar-si").focus(); });
  $("r-borrar-no").addEventListener("click", () => { $("r-confirmar").hidden = true; });
  $("r-borrar-si").addEventListener("click", async () => {
    fail("");
    try { await api(`repertoires/${current.id}`, { method: "DELETE" }); location.href = "repertorio.html"; }
    catch { fail("No se pudo eliminar. Intenta de nuevo."); }
  });
}

async function start(user) {
  if (!user) return view("sin-sesion", "Entra para ver tus repertorios.");
  try {
    const consent = await api("consent");
    if (consent.accepted !== consent.current) return view("sin-consentimiento", "Un paso más.");
    const [reps, songs] = await Promise.all([
      api("repertoires"),
      fetch("/songs.json").then((r) => (r.ok ? r.json() : [])).catch(() => []),
    ]);
    repertoires = reps.repertoires;
    titles = Object.fromEntries(songs.map((s) => [s.slug, s.artist ? `${s.title} · ${s.artist}` : s.title]));
    const id = new URLSearchParams(location.search).get("id");
    const rep = id ? repertoires.find((r) => r.id === id) : null;
    if (id && !rep) { openList(); return fail("No encontramos ese repertorio."); }
    rep ? openOne(rep) : openList();
  } catch (error) {
    view("sin-sesion", "");
    fail(error.status === 404 ? "El sitio no reconoció tu sesión. Entra de nuevo." : "No se pudo consultar tu cuenta. Intenta de nuevo en un minuto.");
  }
}

if (!apiKey) {
  view("sin-sesion", "Tu cuenta no está disponible por ahora.");
  $("entrar").hidden = true;
} else {
  auth = getAuth(initializeApp({ apiKey, authDomain: location.host }));
  wire();
  let first = true;
  onAuthStateChanged(auth, (user) => { if (first || !user) { first = false; start(user); } });
}

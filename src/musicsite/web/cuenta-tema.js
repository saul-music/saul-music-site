// Cuenta en las páginas de tema (S105, C30, C31): continuar, favorito, repertorios y preferencias del reproductor.
// Solo hace algo si hay una sesión: sin la marca `acordia-session` ni siquiera carga Firebase (quien no tiene cuenta no hace
// ninguna llamada a Google desde aquí). Todo texto entra al DOM con textContent. Habla solo con /api/me/*.
const HINT = "acordia-session";
const SDK = "https://www.gstatic.com/firebasejs/13.4.0";
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const read = (key) => { try { return localStorage.getItem(key); } catch { return null; } };
const slug = (location.pathname.match(/\/cancion-([a-z0-9]+(?:-[a-z0-9]+)*)\.html$/) ?? [])[1];
const apiKey = document.querySelector('meta[name="firebase-api-key"]')?.content;

// Cada preferencia de la cuenta con la clave que usa el reproductor y cómo se convierte (null = valor no válido, se omite).
const PREFS = {
  muted: { key: "acordia-sin-sonido", toApi: (v) => (v === "1" ? true : v === "0" ? false : null), toLocal: (v) => (v ? "1" : "0") },
  countIn: { key: "acordia-cuenta-inicial", toApi: (v) => (v === "1" ? true : v === "0" ? false : null), toLocal: (v) => (v ? "1" : "0") },
  instrument: { key: "acordia-instrumento", toApi: (v) => (v === "guitarra" || v === "teclado" ? v : null), toLocal: String },
  studyMode: { key: "acordia-estudio-modo", toApi: (v) => (/^[a-z][a-z-]{0,23}$/.test(v ?? "") ? v : null), toLocal: String },
  theme: { key: "acordia-tema", toApi: (v) => (/^[a-z][a-z-]{0,23}$/.test(v ?? "") ? v : null), toLocal: String },
  volMetronome: { key: "ac-vol-met", toApi: (v) => { const n = parseFloat(v); return Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : null; }, toLocal: String },
};

function localPrefs() {
  const out = {};
  for (const [field, { key, toApi }] of Object.entries(PREFS)) {
    const value = read(key) === null ? null : toApi(read(key));
    if (value !== null) out[field] = value;
  }
  return out;
}

async function main() {
  if (!read(HINT) || !apiKey) return;
  const [{ initializeApp }, { getAuth, onAuthStateChanged }] = await Promise.all([
    import(/* @vite-ignore */ `${SDK}/firebase-app.js`),
    import(/* @vite-ignore */ `${SDK}/firebase-auth.js`),
  ]);
  const auth = getAuth(initializeApp({ apiKey, authDomain: location.host }));
  const user = await new Promise((resolve) => {
    let off = null;
    let done = false;
    off = onAuthStateChanged(auth, (u) => { if (done) return; done = true; off?.(); resolve(u); });
  });
  if (!user) { try { localStorage.removeItem(HINT); } catch { /* sin almacenamiento */ } return; }

  const api = async (path, options = {}) => {
    const token = await auth.currentUser.getIdToken();
    const response = await fetch(`/api/me/${path}`, {
      ...options,
      headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw Object.assign(new Error(`api ${response.status}`), { status: response.status });
    return response.status === 204 ? null : response.json();
  };
  const consent = await api("consent").catch(() => null);
  if (!consent || consent.accepted !== consent.current) return; // sin el aviso vigente, nada se guarda

  if (slug) api("continue", { method: "PUT", body: JSON.stringify({ song: slug }) }).catch(() => {});
  await syncPreferences(api);
  if (slug) await addButtons(api);
}

// --- preferencias: la cuenta manda; la primera vez, lo de este navegador se sube
async function syncPreferences(api) {
  let remote = {};
  try { remote = (await api("preferences")).preferences ?? {}; } catch { return; }
  const local = localPrefs();
  if (Object.keys(remote).length === 0) {
    if (Object.keys(local).length) await api("preferences", { method: "PUT", body: JSON.stringify({ preferences: local }) }).catch(() => {});
  } else {
    let changed = false;
    for (const [field, { key, toLocal }] of Object.entries(PREFS)) {
      if (!(field in remote)) continue;
      const want = toLocal(remote[field]);
      if (read(key) !== want) { try { localStorage.setItem(key, want); changed = true; } catch { /* sin almacenamiento */ } }
    }
    // El reproductor ya arrancó con lo viejo: se recarga una sola vez para que arranque con lo de la cuenta.
    if (changed && !sessionStorage.getItem("acordia-prefs-aplicadas")) {
      sessionStorage.setItem("acordia-prefs-aplicadas", "1");
      location.reload();
      return;
    }
  }
  // Desde aquí, lo que la persona cambie en el reproductor se guarda en su cuenta (con una pausa para no saturar).
  const keys = new Set(Object.values(PREFS).map((p) => p.key));
  const original = Storage.prototype.setItem;
  let timer = null;
  Storage.prototype.setItem = function (key, value) {
    original.call(this, key, value);
    if (this === localStorage && keys.has(key)) {
      clearTimeout(timer);
      timer = setTimeout(() => api("preferences", { method: "PUT", body: JSON.stringify({ preferences: localPrefs() }) }).catch(() => {}), 1500);
    }
  };
}

// --- favorito y repertorios, en la franja de utilidades del tema
const h = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null && v !== false) node.setAttribute(k, v);
  node.append(...children.flat().filter((c) => c !== "" && c != null && c !== false));
  return node;
};
const newId = () => Array.from(crypto.getRandomValues(new Uint8Array(6)), (b) => (b % 36).toString(36)).join("") + "x";

async function addButtons(api) {
  const strip = document.querySelector(".ac-util-btns");
  if (!strip || !SLUG.test(slug)) return;
  let favorites = (await api("favorites").catch(() => ({ favorites: [] }))).favorites;
  const favBtn = h("button", { type: "button", class: "btn btn-outline-secondary ac-util-btn", "aria-pressed": "false" });
  const paintFav = () => {
    const on = favorites.includes(slug);
    favBtn.setAttribute("aria-pressed", String(on));
    favBtn.textContent = on ? "♥ Favorito" : "♡ Favorito";
  };
  paintFav();
  favBtn.addEventListener("click", async () => {
    const want = !favorites.includes(slug);
    try { favorites = (await api("favorites", { method: "PUT", body: JSON.stringify({ song: slug, favorite: want }) })).favorites; } catch { /* queda como estaba */ }
    paintFav();
  });

  const repBtn = h("button", { type: "button", class: "btn btn-outline-secondary ac-util-btn", "aria-expanded": "false" }, "＋ Repertorio");
  const panel = h("div", { class: "card card-body mt-2 gap-2", hidden: "" });
  const note = h("p", { class: "small m-0", role: "status" });
  const list = h("div", { class: "d-grid gap-1" });
  const nameInput = h("input", { class: "form-control form-control-sm", type: "text", maxlength: "60", placeholder: "Nombre del repertorio nuevo", "aria-label": "Nombre del repertorio nuevo" });
  const createBtn = h("button", { type: "button", class: "btn btn-sm btn-outline-primary" }, "Crear con este tema");
  const createBox = h("div", { class: "d-flex gap-2" }, nameInput, createBtn);
  // Si ya hay repertorios, lo principal es elegir uno: crear uno nuevo es una acción secundaria, que se abre a pedido.
  const newToggle = h("button", { type: "button", class: "btn btn-link btn-sm p-0 text-start" }, "＋ Crear un repertorio nuevo");
  panel.append(h("strong", {}, "Tus repertorios"), list, newToggle, createBox, note, h("a", { href: "mi-acordia.html", class: "small" }, "Ver mi cuenta"));

  let repertoires = [];
  let creating = false;
  newToggle.addEventListener("click", () => { creating = true; paintList(); nameInput.focus(); });
  const paintList = () => {
    createBox.hidden = repertoires.length > 0 && !creating; // sin repertorios, crear el primero es lo principal
    newToggle.hidden = repertoires.length === 0 || creating;
    list.replaceChildren(...(repertoires.length ? repertoires.map((r) => {
      const box = h("input", { type: "checkbox", class: "form-check-input", id: `rep-${r.id}` });
      box.checked = r.songs.includes(slug);
      box.addEventListener("change", async () => {
        const songs = box.checked ? [...r.songs, slug] : r.songs.filter((s) => s !== slug);
        try {
          const saved = await api(`repertoires/${r.id}`, { method: "PUT", body: JSON.stringify({ name: r.name, songs }) });
          r.songs = saved.songs;
          note.textContent = box.checked ? `Agregado a «${r.name}».` : `Quitado de «${r.name}».`;
        } catch (error) {
          box.checked = !box.checked;
          note.textContent = error.status === 422 ? "Ese repertorio ya tiene el máximo de temas." : "No se pudo guardar. Intenta de nuevo.";
        }
      });
      return h("div", { class: "form-check" }, box, h("label", { class: "form-check-label", for: `rep-${r.id}` }, r.name),
        " ", h("a", { href: `repertorio.html?id=${r.id}`, class: "small" }, "abrir"));
    }) : [h("span", { class: "small text-body-secondary" }, "Aún no tienes repertorios: crea el primero con este tema.")]));
  };
  repBtn.addEventListener("click", async () => {
    panel.hidden = !panel.hidden;
    repBtn.setAttribute("aria-expanded", String(!panel.hidden));
    if (!panel.hidden) {
      try { repertoires = (await api("repertoires")).repertoires; } catch { note.textContent = "No se pudieron leer tus repertorios."; }
      paintList();
    }
  });
  createBtn.addEventListener("click", async () => {
    const name = nameInput.value;
    try {
      const made = await api(`repertoires/${newId()}`, { method: "PUT", body: JSON.stringify({ name, songs: [slug] }) });
      repertoires.push(made);
      creating = false;
      nameInput.value = "";
      note.textContent = `Creaste «${made.name}» con este tema.`;
      paintList();
    } catch (error) {
      note.textContent = error.status === 422 ? "Revisa el nombre (hasta 60 letras, sin < ni >) o el máximo de 20 repertorios." : "No se pudo crear. Intenta de nuevo.";
    }
  });

  strip.append(favBtn, repBtn);
  strip.after(panel);
}

main().catch(() => { /* la cuenta es un extra: si algo falla, el tema sigue funcionando */ });

// Analítica con consentimiento previo (S116, C51). El servidor solo inyecta este script en páginas públicas y en los hosts
// con medición. Hasta que la persona acepta no se carga nada de Google: ni gtag.js ni cookies. Rechazar, o retirar el permiso
// desde «Preferencias de cookies» en el pie, borra las cookies de Analytics y deja de medir. Todo texto entra con textContent.
// Con permiso, además de las visitas, envía tres eventos de uso (S124): reproducir un tema, llegar a su final y lo que se
// busca en la Biblioteca. Los avisa la librería (`acordia:uso`, RD56); aquí se normalizan y se filtran.
(() => {
  const script = document.currentScript;
  const ID = script?.dataset.id;
  const VERSION = script?.dataset.version;
  if (!ID || !VERSION || !/^G-[A-Z0-9]+$/.test(ID)) return;

  // Navegadores del equipo (S124): `?interno=1` los marca y desde ahí no se carga nada de Google, ni banner ni enlace del
  // pie; `?interno=0` quita la marca. Se guarda por dominio: acordia.io y web.app se marcan por separado.
  const INTERNAL = "acordia-interno";
  try {
    const flag = new URLSearchParams(location.search).get("interno");
    if (flag === "1") localStorage.setItem(INTERNAL, "1");
    else if (flag === "0") localStorage.removeItem(INTERNAL);
  } catch { /* sin almacenamiento: no hay marca */ }
  const internal = () => { try { return localStorage.getItem(INTERNAL) === "1"; } catch { return false; } };

  const KEY = "acordia-analitica";
  const read = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || "null");
      return saved && saved.v === VERSION && (saved.d === "granted" || saved.d === "denied") ? saved.d : null;
    } catch { return null; }
  };
  const save = (decision) => {
    try { localStorage.setItem(KEY, JSON.stringify({ v: VERSION, d: decision })); } catch { /* sin almacenamiento: se pregunta de nuevo */ }
  };

  let loaded = false;
  let send = null;  // gtag, una vez que la persona aceptó
  function load() {
    window["ga-disable-" + ID] = false;  // también si se rechazó y se vuelve a aceptar en la misma página
    if (loaded) return;
    loaded = true;
    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    send = gtag;
    // Solo analítica de uso: nada de publicidad ni personalización (Google Signals también está apagado en la propiedad).
    gtag("consent", "default", { analytics_storage: "granted", ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied" });
    gtag("js", new Date());
    gtag("config", ID, { allow_google_signals: false, allow_ad_personalization_signals: false, cookie_flags: "SameSite=Lax;Secure" });
    const tag = document.createElement("script");
    tag.async = true;
    tag.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(ID);
    document.head.appendChild(tag);
  }

  function clearCookies() {
    window["ga-disable-" + ID] = true;
    const parts = location.hostname.split(".");
    const domains = [""];
    for (let i = 0; i < parts.length - 1; i++) {
      const domain = parts.slice(i).join(".");
      domains.push("; domain=" + domain, "; domain=." + domain);
    }
    for (const cookie of document.cookie.split(";")) {
      const name = cookie.split("=")[0].trim();
      if (name === "_ga" || name.startsWith("_ga_") || name === "_gid" || name.startsWith("_gat")) {
        for (const domain of domains) document.cookie = name + "=; Max-Age=0; path=/" + domain;
      }
    }
  }

  let banner = null;
  function closeBanner() { banner?.remove(); banner = null; }

  function decide(decision) {
    save(decision);
    closeBanner();
    if (decision === "granted") load();
    else clearCookies();
  }

  function openBanner() {
    if (banner) return;
    banner = document.createElement("div");
    banner.setAttribute("role", "dialog");
    banner.setAttribute("aria-label", "Cookies");
    banner.style.cssText = "position:fixed;left:0;right:0;bottom:0;z-index:1080;background:#191430;color:#f4f1ff;" +
      "border-top:1px solid #4a3f7a;padding:.9rem 1rem;box-shadow:0 -4px 18px rgba(0,0,0,.35)";
    const inner = document.createElement("div");
    inner.className = "container d-flex flex-wrap align-items-center gap-3";
    const text = document.createElement("p");
    text.className = "m-0 small flex-grow-1";
    text.style.maxWidth = "48rem";
    text.append("Usamos cookies para entender cómo se usa el sitio y mejorarlo. Puedes aceptarlas o rechazarlas; el sitio funciona igual. ");
    const more = document.createElement("a");
    more.href = "privacidad.html#analitica";
    more.textContent = "Más información";
    more.style.color = "inherit";
    text.append(more);
    const buttons = document.createElement("div");
    buttons.className = "d-flex gap-2";
    const reject = document.createElement("button");
    reject.type = "button";
    reject.className = "btn btn-sm btn-outline-light";
    reject.textContent = "Rechazar";
    reject.addEventListener("click", () => decide("denied"));
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "btn btn-sm btn-light";
    accept.textContent = "Aceptar";
    accept.addEventListener("click", () => decide("granted"));
    buttons.append(reject, accept);
    inner.append(text, buttons);
    banner.append(inner);
    document.body.append(banner);
  }

  function footerLink() {
    const nav = document.querySelector('nav[aria-label="Pie de página"]');
    if (!nav || nav.querySelector("[data-analitica]")) return;
    const link = document.createElement("a");
    link.href = "#analitica";
    link.dataset.analitica = "1";
    link.textContent = "Preferencias de cookies";
    link.addEventListener("click", (event) => { event.preventDefault(); openBanner(); });
    nav.append(link);
  }

  // Avisos de uso (RD56) → eventos. Sin permiso (`send` vacío) o con el permiso retirado (`ga-disable`) no sale nada.
  // La búsqueda se envía cuando la persona deja de escribir 1,5 s (o al salir de la página), normalizada y una vez por
  // término en la visita; se descarta si es muy corta o parece un dato personal (un correo o un número largo).
  const SEARCH_WAIT = 1500;
  const sentTerms = new Set();
  let pendingTerm = "";
  let searchTimer = null;
  const active = () => send && !window["ga-disable-" + ID];
  function normalize(term) {
    return String(term || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/\s+/g, " ").trim().slice(0, 40).trim();
  }
  function personal(term) { return term.includes("@") || (term.match(/\d/g) || []).length >= 6; }
  function flushSearch() {
    clearTimeout(searchTimer);
    searchTimer = null;
    const term = pendingTerm;
    pendingTerm = "";
    if (!active() || term.length < 2 || personal(term) || sentTerms.has(term)) return;
    sentTerms.add(term);
    send("event", "search", { search_term: term });
  }
  document.addEventListener("acordia:uso", (event) => {
    const detail = event.detail || {};
    if (!active()) return;
    if (detail.action === "play") send("event", "song_play");
    else if (detail.action === "complete") send("event", "song_complete");
    else if (detail.action === "search") {
      pendingTerm = normalize(detail.term);
      clearTimeout(searchTimer);
      searchTimer = setTimeout(flushSearch, SEARCH_WAIT);
    }
  });
  window.addEventListener("pagehide", flushSearch);

  function main() {
    if (internal()) { clearCookies(); return; }  // equipo: nada de Google, ni banner ni enlace del pie
    footerLink();
    const decision = read();
    if (decision === "granted") load();
    else if (decision === null) openBanner();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", main);
  else main();
})();

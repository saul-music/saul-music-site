// Entrar a Acordia (S101, C40). Todo texto entra al DOM con textContent, nunca con innerHTML.
// El SDK de Firebase se carga desde el CDN de Google con la versión fija (C40): subirla es un cambio de este archivo.
import { initializeApp } from "https://www.gstatic.com/firebasejs/13.4.0/firebase-app.js";
import {
  GoogleAuthProvider,
  deleteUser,
  getAuth,
  getRedirectResult,
  isSignInWithEmailLink,
  onAuthStateChanged,
  sendSignInLinkToEmail,
  signInWithEmailLink,
  signInWithRedirect,
  signOut,
} from "https://www.gstatic.com/firebasejs/13.4.0/firebase-auth.js";

// El retorno de Google y el enlace por correo solo están autorizados en la dirección web.app del sitio (C20) y en el dominio
// propio (S113): en otra dirección el SDK avisa y no entra. `www` redirige al dominio raíz antes de llegar aquí.
const allowedHost = () => location.hostname.endsWith(".web.app") || location.hostname === "acordia.io";
const $ = (id) => document.getElementById(id);
const apiKey = document.querySelector('meta[name="firebase-api-key"]').content;
const STEPS = ["paso-entrar", "paso-confirmar", "paso-consentimiento"];

// Navegadores dentro de apps (Instagram, Facebook, TikTok, LinkedIn, Snapchat, Line y las vistas web de Android): Google
// rechaza ahí el inicio de sesión (403 disallowed_useragent). Se avisa y queda el correo, que sí funciona (S114).
const IN_APP = /Instagram|FBAN|FBAV|FB_IAB|musical_ly|Bytedance|TikTok|LinkedInApp|Snapchat|\bLine\/|; wv\)/i;
const inAppBrowser = IN_APP.test(navigator.userAgent);

// Título y bajada según de dónde viene la persona (`?volver`, ya validado por returnTo): solo textos fijos (S112).
const HEADINGS = {
  inicio: ["Tu cuenta", "Entra a Acordia", "Guarda tus temas favoritos, arma repertorios y sigue tu avance en Aprende."],
  aprende: ["Aprende", "Guarda tu avance", "Entra para que tus lecciones, tus puntos y tus estrellas queden guardados y puedas seguir desde cualquier dispositivo."],
  cuenta: ["Mi cuenta", "Entra a tu cuenta", "Tus favoritos, tus repertorios y tu avance, en un solo lugar."],
  repertorio: ["Repertorios", "Abre tus repertorios", "Entra para ver tus listas de temas y tocarlas una tras otra."],
  confirmar: ["Tu cuenta", "Confirma tu correo", "Abriste el enlace en otro dispositivo o navegador. Escribe el correo al que te lo enviamos para terminar de entrar."],
  consentimiento: ["Tu cuenta", "Antes de seguir", "Confirma estos dos puntos y tu cuenta queda lista."],
};
const context = () => {
  const target = returnTo();
  if (target.startsWith("/aprende/")) return "aprende";
  if (target.startsWith("/repertorio.html")) return "repertorio";
  return target === "/mi-acordia.html" ? "cuenta" : "inicio";
};
const setHeading = (key) => {
  const [eyebrow, title, lead] = HEADINGS[key];
  $("login-eyebrow").textContent = eyebrow;
  $("login-title").textContent = title;
  $("login-lead").textContent = lead;
};

const HEADING_OF_STEP = { "paso-confirmar": "confirmar", "paso-consentimiento": "consentimiento" };
const show = (step, message = "") => {
  for (const id of STEPS) $(id).hidden = id !== step;
  $("estado").textContent = message;
  setHeading(HEADING_OF_STEP[step] ?? context());
};

// Mientras el navegador va a Google, el botón lo dice y no se puede volver a tocar; el correo tampoco (S112).
// En el navegador de una app el botón de Google queda desactivado siempre: el aviso explica por qué.
const setLoading = (active = false) => {
  const button = $("entrar-google");
  button.disabled = active || inAppBrowser;
  button.classList.toggle("is-loading", active);
  button.setAttribute("aria-busy", String(active));
  button.querySelector(".ac-idp-label").textContent = active ? "Abriendo Google…" : "Continuar con Google";
  $("correo-enviar").disabled = active;
};
const fail = (message) => { $("error").textContent = message; $("error").hidden = !message; };

async function api(path, options = {}) {
  const token = await getAuth().currentUser.getIdToken();
  return fetch(path ? `/api/me/${path}` : "/api/me", {
    ...options,
    headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), Authorization: `Bearer ${token}` },
  });
}

async function afterSignIn() {
  fail("");
  const response = await api("consent");
  if (response.status === 404) {
    show("paso-entrar", "No se pudo verificar tu sesión.");
    return fail("El servidor no reconoció tu sesión (404). Cierra sesión y vuelve a entrar.");
  }
  if (!response.ok) return fail("No se pudo consultar tu cuenta. Intenta de nuevo en un minuto.");
  const state = await response.json();
  if (state.accepted !== state.current) {
    $("c-edad").checked = false;
    $("c-aviso").checked = false;
    $("aceptar").disabled = true;
    // El perfil se pide solo la primera vez: quien vuelve a aceptar un aviso nuevo ya pasó por aquí (S110).
    $("c-perfil").hidden = Boolean(state.returning);
    for (const id of ["c-nombre", "c-instrumento", "c-nivel"]) $(id).value = "";
    $("paso-consentimiento").dataset.version = state.current;
    show("paso-consentimiento");
    if (state.returning) $("login-lead").textContent = "Actualizamos el Aviso de privacidad. Revísalo y acéptalo para seguir.";
    return;
  }
  showReady();
}
// Una sola consulta a la vez: el cambio de sesión y el fin del enlace pueden pedirla juntos.
let checking = null;
const checkAccount = () => (checking ??= afterSignIn().finally(() => { checking = null; }));

// Aprende manda a entrar con `?volver=/aprende/…` y Mi cuenta con `?volver=/mi-acordia.html`; aquí se regresa al terminar
// (S103, S104). Solo a esas rutas del mismo sitio: nunca una dirección completa ni `//`, para que no sirva de redirección abierta.
const returnTo = () => {
  const target = new URLSearchParams(location.search).get("volver") ?? "";
  const allowed = /^\/(aprende\/[A-Za-z0-9\-_./#?=&]*|mi-acordia\.html|repertorio\.html(\?[A-Za-z0-9\-_=&]*)?)$/;
  return allowed.test(target) && !target.includes("..") ? target : "";
};
// La dirección de esta página conservando solo `?volver`: así vuelve el enlace del correo y así queda al usarlo.
const loginUrl = () => {
  const target = returnTo();
  return `${location.pathname}${target ? `?volver=${encodeURIComponent(target)}` : ""}`;
};

// Con sesión y consentimiento al día no hay nada que hacer aquí: se vuelve a donde se venía o, si no, a «Mi cuenta».
function showReady() {
  location.replace(returnTo() || "/mi-acordia.html");
}

// --- Entrar con el correo (S114): Firebase envía un enlace de un solo uso, sin contraseña.
// El correo queda en este navegador mientras tanto (Firebase lo exige para no pedirlo de nuevo) y se borra al entrar.
const PENDING = "acordia-correo-pendiente";
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const RESEND_SECONDS = 60;
const SEND_ERRORS = {
  "auth/invalid-email": "Revisa tu correo: no parece una dirección válida.",
  "auth/too-many-requests": "Pediste muchos enlaces seguidos. Espera unos minutos y vuelve a intentarlo.",
  "auth/quota-exceeded": "Hoy no podemos enviar más enlaces. Entra con Google o intenta mañana.",
  "auth/network-request-failed": "No hay conexión. Revisa tu internet e intenta de nuevo.",
};
const LINK_USED = "Este enlace ya no sirve: venció o ya se usó. Pide uno nuevo.";
const LINK_ERRORS = {
  "auth/invalid-action-code": LINK_USED,
  "auth/expired-action-code": LINK_USED,
  "auth/network-request-failed": "No hay conexión. Revisa tu internet y vuelve a abrir el enlace.",
};
const readPending = () => { try { return localStorage.getItem(PENDING); } catch { return null; } };
const writePending = (email) => {
  try { email ? localStorage.setItem(PENDING, email) : localStorage.removeItem(PENDING); } catch { /* sin almacenamiento */ }
};

let resendTimer = 0;
const startCooldown = () => {
  const button = $("correo-reenviar");
  const until = Date.now() + RESEND_SECONDS * 1000;
  const tick = () => {
    const left = Math.ceil((until - Date.now()) / 1000);
    button.disabled = left > 0;
    button.textContent = left > 0 ? `Reenviar el enlace (${left} s)` : "Reenviar el enlace";
    if (left <= 0) clearInterval(resendTimer);
  };
  clearInterval(resendTimer);
  tick();
  resendTimer = setInterval(tick, 1000);
};
const showEmailForm = () => {
  clearInterval(resendTimer);
  $("correo-enviado").hidden = true;
  $("form-correo").hidden = false;
};

setHeading(context()); // antes de saber si hay sesión, para que el título no cambie a la vista

if (inAppBrowser) {
  $("aviso-app").hidden = false;
  if (/Android/i.test(navigator.userAgent)) {
    const link = $("abrir-chrome");
    link.href = `intent://${location.host}${location.pathname}${location.search}#Intent;scheme=https;package=com.android.chrome;end`;
    link.hidden = false;
  }
}

if (!apiKey) {
  show("paso-entrar", "El inicio de sesión no está disponible por ahora.");
  $("entrar-google").disabled = true;
  $("correo-enviar").disabled = true;
} else {
  const auth = getAuth(initializeApp({ apiKey, authDomain: location.host }));
  auth.languageCode = "es"; // el correo con el enlace llega en español
  // Fuera de la dirección oficial no hay aviso a la vista (nadie llega ahí): solo un mensaje si se toca un botón (S114).
  const allowed = allowedHost();
  setLoading();

  $("entrar-google").addEventListener("click", async () => {
    fail("");
    if (!allowed) return fail("Entra desde la dirección oficial del sitio.");
    setLoading(true);
    try {
      await signInWithRedirect(auth, new GoogleAuthProvider());
    } catch {
      setLoading();
      fail("No se pudo iniciar el acceso. Intenta de nuevo.");
    }
  });
  // Volver con «Atrás» desde Google puede restaurar la página tal como quedó: los botones vuelven a estar listos.
  addEventListener("pageshow", (event) => { if (event.persisted) setLoading(); });

  const sendLink = async (email) => {
    fail("");
    if (!allowed) return fail("Entra desde la dirección oficial del sitio.");
    if (!EMAIL.test(email)) return fail("Revisa tu correo: parece incompleto.");
    $("correo-enviar").disabled = true;
    $("correo-reenviar").disabled = true;
    try {
      await sendSignInLinkToEmail(auth, email, { url: `${location.origin}${loginUrl()}`, handleCodeInApp: true });
    } catch (error) {
      $("correo-enviar").disabled = false;
      $("correo-reenviar").disabled = false;
      return fail(SEND_ERRORS[error?.code] ?? "No pudimos enviar el enlace. Intenta de nuevo o entra con Google.");
    }
    writePending(email);
    $("correo-destino").textContent = email;
    $("form-correo").hidden = true;
    $("correo-enviado").hidden = false;
    $("correo-enviar").disabled = false;
    startCooldown();
  };
  $("form-correo").addEventListener("submit", (event) => {
    event.preventDefault();
    sendLink($("correo").value.trim());
  });
  $("correo-reenviar").addEventListener("click", () => sendLink($("correo-destino").textContent));
  $("correo-otro").addEventListener("click", () => { fail(""); showEmailForm(); $("correo").focus(); });

  // Al volver por el enlace: con el correo guardado en este navegador entra solo; si no (otro dispositivo, otro navegador
  // o un revisor automático de correo que abrió el enlace), lo pide antes de usarlo.
  let linkState = allowed && isSignInWithEmailLink(auth, location.href) ? "finishing" : "";
  const finishLink = async (email) => {
    fail("");
    linkState = "finishing";
    try {
      await signInWithEmailLink(auth, email, location.href);
    } catch (error) {
      if (error?.code === "auth/invalid-email") {
        linkState = "confirm";
        show("paso-confirmar");
        return fail("Ese no es el correo al que enviamos el enlace. Revísalo.");
      }
      linkState = "";
      history.replaceState(null, "", loginUrl());
      show("paso-entrar");
      return fail(LINK_ERRORS[error?.code] ?? "No se pudo entrar con el enlace. Pide uno nuevo.");
    }
    writePending("");
    linkState = "";
    history.replaceState(null, "", loginUrl());
    checkAccount().catch(() => fail("No se pudo consultar tu cuenta."));
  };
  if (linkState) {
    const pending = readPending();
    if (pending) finishLink(pending);
    else { linkState = "confirm"; show("paso-confirmar"); }
  }
  $("paso-confirmar").addEventListener("submit", (event) => {
    event.preventDefault();
    const email = $("confirmar-correo").value.trim();
    if (!EMAIL.test(email)) return fail("Revisa tu correo: parece incompleto.");
    $("confirmar-entrar").disabled = true;
    finishLink(email).finally(() => { $("confirmar-entrar").disabled = false; });
  });
  $("confirmar-volver").addEventListener("click", () => {
    fail("");
    linkState = "";
    history.replaceState(null, "", loginUrl());
    show("paso-entrar");
  });

  for (const id of ["c-edad", "c-aviso"]) {
    $(id).addEventListener("change", () => { $("aceptar").disabled = !($("c-edad").checked && $("c-aviso").checked); });
  }

  $("paso-consentimiento").addEventListener("submit", async (event) => {
    event.preventDefault();
    fail("");
    const version = $("paso-consentimiento").dataset.version;
    const response = await api("consent", { method: "PUT", body: JSON.stringify({ version, adult: true }) });
    if (!response.ok) return fail("No se pudo guardar tu consentimiento. Intenta de nuevo.");
    // Perfil opcional: solo se guarda si hay algo escrito. El consentimiento ya quedó; reenviar es inocuo.
    const profile = { name: $("c-nombre").value, instrument: $("c-instrumento").value, level: $("c-nivel").value };
    if (!$("c-perfil").hidden && Object.values(profile).some((value) => value.trim())) {
      const saved = await api("profile", { method: "PUT", body: JSON.stringify(profile) });
      if (saved.status === 422) return fail("Revisa el nombre: hasta 40 letras, sin < ni >.");
      if (!saved.ok) return fail("No se pudo guardar tu perfil. Puedes completarlo después en Mi cuenta.");
    }
    showReady();
  });

  // «No acepto»: la cuenta ya existe en Firebase (se crea al iniciar sesión), así que se elimina.
  $("rechazar").addEventListener("click", async () => {
    fail("");
    try {
      await deleteUser(auth.currentUser);
      show("paso-entrar", "Eliminamos tu cuenta. No guardamos nada.");
    } catch {
      await signOut(auth);
      show("paso-entrar", "");
      fail("Cerramos tu sesión, pero no pudimos eliminar la cuenta. Escríbenos a contacto@saulapp.com y la borramos.");
    }
  });

  if (allowed) getRedirectResult(auth).catch((error) => {
    fail(error.code === "auth/account-exists-with-different-credential"
      ? "Ese correo ya tiene una cuenta con otro método de acceso. Entra con el que usaste antes (Google o tu correo): es la misma cuenta y conserva tus datos."
      : "No se pudo completar el acceso. Intenta de nuevo.");
  });
  onAuthStateChanged(auth, (user) => {
    // «Hay una sesión»: las páginas de tema solo cargan Firebase si existe esta marca (S105); no guarda nada personal.
    try { user ? localStorage.setItem("acordia-session", "1") : localStorage.removeItem("acordia-session"); } catch { /* sin almacenamiento */ }
    if (linkState === "finishing") return; // el enlace termina de entrar y después consulta la cuenta
    if (user) checkAccount().catch(() => fail("No se pudo consultar tu cuenta."));
    else if (linkState !== "confirm") show("paso-entrar", "");
  });
}

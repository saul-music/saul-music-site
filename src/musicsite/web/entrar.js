// Entrar a Acordia (S101, C40). Todo texto entra al DOM con textContent, nunca con innerHTML.
// El SDK de Firebase se carga desde el CDN de Google con la versión fija (C40): subirla es un cambio de este archivo.
import { initializeApp } from "https://www.gstatic.com/firebasejs/13.4.0/firebase-app.js";
import {
  FacebookAuthProvider,
  GoogleAuthProvider,
  deleteUser,
  getAuth,
  getRedirectResult,
  onAuthStateChanged,
  signInWithRedirect,
  signOut,
} from "https://www.gstatic.com/firebasejs/13.4.0/firebase-auth.js";

// El retorno de Google y Facebook solo está autorizado en la dirección web.app del sitio (C20): el SDK avisa si no lo es.
const allowedHost = () => location.hostname.endsWith(".web.app");
const $ = (id) => document.getElementById(id);
const apiKey = document.querySelector('meta[name="firebase-api-key"]').content;
const STEPS = ["paso-entrar", "paso-consentimiento"];

const show = (step, message = "") => {
  for (const id of STEPS) $(id).hidden = id !== step;
  $("estado").textContent = message;
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
    return show("paso-consentimiento", "Un paso más.");
  }
  showReady();
}

// Aprende manda a entrar con `?volver=/aprende/…` y Mi cuenta con `?volver=/mi-acordia.html`; aquí se regresa al terminar
// (S103, S104). Solo a esas rutas del mismo sitio: nunca una dirección completa ni `//`, para que no sirva de redirección abierta.
const returnTo = () => {
  const target = new URLSearchParams(location.search).get("volver") ?? "";
  const allowed = /^\/(aprende\/[A-Za-z0-9\-_./#?=&]*|mi-acordia\.html|repertorio\.html(\?[A-Za-z0-9\-_=&]*)?)$/;
  return allowed.test(target) && !target.includes("..") ? target : "";
};

// Con sesión y consentimiento al día no hay nada que hacer aquí: se vuelve a donde se venía o, si no, a «Mi cuenta».
function showReady() {
  location.replace(returnTo() || "/mi-acordia.html");
}

if (!apiKey) {
  show("paso-entrar", "El inicio de sesión no está disponible por ahora.");
  $("entrar-google").disabled = true;
  $("entrar-facebook").disabled = true;
} else {
  const auth = getAuth(initializeApp({ apiKey, authDomain: location.host }));
  const allowed = allowedHost();
  $("aviso-host").hidden = allowed;

  const start = (provider) => async () => {
    fail("");
    if (!allowed) return fail("Entra desde la dirección web.app oficial del sitio.");
    try { await signInWithRedirect(auth, provider()); } catch { fail("No se pudo iniciar el acceso. Intenta de nuevo."); }
  };
  $("entrar-google").addEventListener("click", start(() => new GoogleAuthProvider()));
  $("entrar-facebook").addEventListener("click", start(() => new FacebookAuthProvider()));
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
      ? "Ese correo ya tiene una cuenta con otro método de acceso. Entra con Google o con Facebook, el que usaste antes: es la misma cuenta y conserva tus datos."
      : "No se pudo completar el acceso. Intenta de nuevo.");
  });
  onAuthStateChanged(auth, (user) => {
    // «Hay una sesión»: las páginas de tema solo cargan Firebase si existe esta marca (S105); no guarda nada personal.
    try { user ? localStorage.setItem("acordia-session", "1") : localStorage.removeItem("acordia-session"); } catch { /* sin almacenamiento */ }
    if (user) afterSignIn().catch(() => fail("No se pudo consultar tu cuenta."));
    else show("paso-entrar", "");
  });
}

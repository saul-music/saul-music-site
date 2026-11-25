"""La página de entrada (S108): solo login; con sesión lleva a «Mi cuenta», en un navegador real.

El SDK de Firebase (gstatic) se reemplaza por un doble que simula una sesión abierta o ninguna, y la
API es la del sitio con un almacén en memoria: no hay red ni cuentas reales. Solo en local.

    uv run pytest tests/e2e/test_cuenta.py --browser chromium
"""

from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page, expect

from musicsite.accounts import (
    NOTICE_VERSION,
    Accounts,
    RateLimiter,
    identity_from_claims,
    uid_from_claims,
)
from musicsite.app import create_app

CLAIMS = {
    "uid": "uid1",
    "email": "persona.sintetica@example.test",
    "firebase": {"sign_in_provider": "google.com"},
}

APP_JS = "export function initializeApp() { return {}; }"
AUTH_JS = """
const calls = (window.__calls = []);
const user = { getIdToken: async () => "p1" };
const auth = { currentUser: user };
export const getAuth = () => auth;
export const onAuthStateChanged = (_a, callback) => { callback(window.__noUser ? null : user); };
export const getRedirectResult = async () => null;
export const signInWithRedirect = async () => {
  calls.push("redirect");
  if (window.__failRedirect) throw new Error("x");
};
export const signOut = async () => { calls.push("signOut"); };
export const deleteUser = async () => {
  calls.push("deleteUser");
  if (window.__failDelete) { const e = new Error("x"); e.code = window.__failDelete; throw e; }
};
export class GoogleAuthProvider {}
export class FacebookAuthProvider {}
"""


class Verifier:
    def verify(self, token):
        return uid_from_claims(CLAIMS) if token == "p1" else None

    def identity(self, token):
        return identity_from_claims(CLAIMS) if token == "p1" else None


class Store:
    def __init__(self):
        self.docs = {"uid1": {"muted": True}}
        self.consents = {"uid1": NOTICE_VERSION}
        self.profile = {}

    def get(self, uid):
        return dict(self.docs.get(uid, {}))

    def put(self, uid, preferences):
        self.docs[uid] = dict(preferences)

    def get_consent(self, uid):
        return self.consents.get(uid)

    def put_consent(self, uid, version):
        self.consents[uid] = version

    def get_profile(self, uid):
        return dict(self.profile)

    def put_profile(self, uid, profile):
        self.profile = dict(profile)

    def get_continue(self, uid):
        return {}

    def put_continue(self, uid, value):
        pass

    def get_favorites(self, uid):
        return []

    def put_favorite(self, uid, song, favorite):
        return []

    def get_repertoires(self, uid):
        return {}

    def put_repertoire(self, uid, rid, value):
        return True

    def delete_repertoire(self, uid, rid):
        pass

    def get_progress(self, uid):
        return {}

    def put_result(self, uid, path, lesson, points, stars):
        return {"points": points, "stars": stars, "plays": 1}

    def export(self, uid):
        consent = self.consents.get(uid)
        return {
            "consent": {"version": consent, "adult": True, "at": None} if consent else None,
            "preferences": dict(self.docs.get(uid, {})),
            "progress": {},
            "profile": {},
            "continue": {},
        }

    def delete(self, uid):
        self.docs.pop(uid, None)
        self.consents.pop(uid, None)


@pytest.fixture
def store():
    return Store()


@pytest.fixture
def account_url(store, serve_local):
    accounts = Accounts(Verifier(), store, RateLimiter(limit=100, window=60))
    return serve_local(create_app(accounts=accounts, firebase_api_key="clave-de-prueba"))


DESTINATIONS = ("/mi-acordia.html", "/repertorio.html")


def open_login(page: Page, account_url: str, query: str = "", signed_in: bool = True) -> Page:
    def route(r):
        url = r.request.url
        if "firebase-app.js" in url:
            return r.fulfill(body=APP_JS, content_type="text/javascript")
        if "firebase-auth.js" in url:
            return r.fulfill(body=AUTH_JS, content_type="text/javascript")
        if urlparse(url).path in DESTINATIONS:
            return r.fulfill(body="<title>destino</title>", content_type="text/html")
        return r.abort()  # nada sale a Internet (Bootstrap, fuentes)

    page.route(
        lambda url: not url.startswith(account_url) or urlparse(url).path in DESTINATIONS, route
    )
    if not signed_in:
        page.add_init_script("window.__noUser = true")
    page.goto(account_url + "/entrar.html" + query)
    return page


def test_a_signed_in_person_goes_to_my_account(page: Page, account_url: str):
    open_login(page, account_url)
    page.wait_for_url("**/mi-acordia.html")


def test_a_signed_in_person_goes_back_to_where_they_came_from(page: Page, account_url: str):
    open_login(page, account_url, "?volver=/repertorio.html")
    page.wait_for_url("**/repertorio.html")


def test_without_a_session_it_is_a_plain_login(page: Page, account_url: str):
    open_login(page, account_url, signed_in=False)
    expect(page.locator("#paso-entrar")).to_be_visible()
    expect(page.locator("#entrar-google")).to_be_visible()
    # Facebook queda oculto mientras la app de Meta no pase a Live (S112).
    expect(page.locator("#entrar-facebook")).to_be_hidden()
    # La cuenta es opcional: la página dice que la Biblioteca se usa sin entrar y lleva a ella.
    expect(page.locator("#sin-cuenta")).to_contain_text("No necesitas cuenta")
    expect(page.locator("#sin-cuenta a")).to_have_attribute("href", "index.html#biblioteca")
    expect(page.locator("#paso-consentimiento")).to_be_hidden()
    expect(page.get_by_text("Tus datos")).to_have_count(0)
    assert "entrar.html" in page.url


def fill_consent(page: Page):
    page.check("#c-edad")
    page.check("#c-aviso")


def test_a_new_account_is_asked_for_the_profile_next_to_the_consent(
    page: Page, account_url: str, store
):
    store.consents.clear()
    open_login(page, account_url)
    expect(page.locator("#paso-consentimiento")).to_be_visible()
    expect(page.locator("#c-perfil")).to_be_visible()
    fill_consent(page)
    page.fill("#c-nombre", "Ana")
    page.select_option("#c-instrumento", "guitarra")
    page.select_option("#c-nivel", "inicial")
    page.click("#aceptar")
    page.wait_for_url("**/mi-acordia.html")
    assert store.consents["uid1"] == NOTICE_VERSION
    assert store.profile == {"name": "Ana", "instrument": "guitarra", "level": "inicial"}


def test_an_empty_profile_is_not_saved_and_never_blocks_the_account(
    page: Page, account_url: str, store
):
    store.consents.clear()
    store.profile = {"name": "Previo"}
    open_login(page, account_url)
    fill_consent(page)
    page.click("#aceptar")
    page.wait_for_url("**/mi-acordia.html")
    assert store.profile == {"name": "Previo"}  # nada escrito: no se toca


def test_a_bad_name_stays_on_the_step_and_explains_it(page: Page, account_url: str, store):
    store.consents.clear()
    open_login(page, account_url)
    fill_consent(page)
    page.fill("#c-nombre", "<b>")
    page.click("#aceptar")
    expect(page.locator("#error")).to_contain_text("Revisa el nombre")
    assert "mi-acordia" not in page.url
    assert store.consents["uid1"] == NOTICE_VERSION  # el consentimiento ya quedó


def test_someone_accepting_a_new_notice_is_not_asked_again(page: Page, account_url: str, store):
    store.consents["uid1"] = "2025-01-01-v1"
    open_login(page, account_url)
    expect(page.locator("#paso-consentimiento")).to_be_visible()
    expect(page.locator("#c-perfil")).to_be_hidden()
    expect(page.locator("#login-lead")).to_contain_text("Actualizamos el Aviso de privacidad")


# --- rediseño (S112): título según de dónde se viene, pasos y estado de carga
@pytest.mark.parametrize(
    ("query", "title"),
    [
        ("", "Entra a Acordia"),
        ("?volver=/aprende/", "Guarda tu avance"),
        ("?volver=/aprende/%23basico/do-es-c", "Guarda tu avance"),
        ("?volver=/mi-acordia.html", "Entra a tu cuenta"),
        ("?volver=/repertorio.html?id=r1", "Abre tus repertorios"),
        ("?volver=https://otro.example/aprende/", "Entra a Acordia"),  # destino no permitido
        ("?volver=//otro.example/aprende/", "Entra a Acordia"),
    ],
)
def test_the_title_says_why_you_are_asked_to_sign_in(
    page: Page, account_url: str, query: str, title: str
):
    open_login(page, account_url, query, signed_in=False)
    expect(page.locator("#login-title")).to_have_text(title)
    expect(page.locator("#paso-entrar")).to_be_visible()
    expect(page.locator("#estado")).to_be_hidden()  # sin mensaje, el estado no ocupa lugar


def test_the_consent_step_shows_where_you_are(page: Page, account_url: str, store):
    store.consents.clear()
    open_login(page, account_url, "?volver=/aprende/")
    expect(page.locator("#login-title")).to_have_text("Antes de seguir")
    expect(page.locator('.ac-steps [aria-current="step"]')).to_contain_text("Un paso más")
    expect(page.locator("#paso-entrar")).to_be_hidden()


def test_outside_web_app_the_buttons_explain_instead_of_loading(page: Page, account_url: str):
    open_login(page, account_url, signed_in=False)
    expect(page.locator("#aviso-host")).to_be_visible()
    page.click("#entrar-google")
    expect(page.locator("#error")).to_contain_text("dirección oficial")
    expect(page.locator("#entrar-google")).to_be_enabled()
    assert "redirect" not in page.evaluate("window.__calls")


WEB_APP = "https://prueba.web.app"


def open_on_web_app(page: Page, account_url: str, fail_redirect: bool = False) -> Page:
    """La página servida como si fuera la dirección web.app: ahí los botones inician el acceso."""

    def route(r):
        url = r.request.url
        if "firebase-app.js" in url:
            return r.fulfill(body=APP_JS, content_type="text/javascript")
        if "firebase-auth.js" in url:
            return r.fulfill(body=AUTH_JS, content_type="text/javascript")
        if url.startswith(WEB_APP + "/"):
            return r.fulfill(response=r.fetch(url=account_url + url[len(WEB_APP) :]))
        return r.abort()  # nada sale a Internet (Bootstrap, fuentes)

    page.route("**/*", route)
    page.add_init_script("window.__noUser = true")
    if fail_redirect:
        page.add_init_script("window.__failRedirect = true")
    page.goto(WEB_APP + "/entrar.html")
    return page


def test_a_button_shows_it_is_opening_the_provider(page: Page, account_url: str):
    open_on_web_app(page, account_url)
    expect(page.locator("#aviso-host")).to_be_hidden()
    page.click("#entrar-google")
    google = page.locator("#entrar-google")
    expect(google).to_have_text("Abriendo Google…")
    expect(google).to_be_disabled()
    expect(google).to_have_attribute("aria-busy", "true")
    expect(page.locator("#entrar-facebook")).to_be_disabled()
    assert page.evaluate("window.__calls") == ["redirect"]


def test_if_the_provider_cannot_open_the_buttons_come_back(page: Page, account_url: str):
    open_on_web_app(page, account_url, fail_redirect=True)
    page.click("#entrar-google")
    expect(page.locator("#error")).to_contain_text("No se pudo iniciar el acceso")
    google = page.locator("#entrar-google")
    expect(google).to_have_text("Continuar con Google")
    expect(google).to_be_enabled()
    expect(google).to_have_attribute("aria-busy", "false")

"""Tus datos en la página de entrada (S102): descargar y eliminar, en un navegador real.

El SDK de Firebase (gstatic) se reemplaza por un doble que simula una sesión abierta, y la API es la
del sitio con un almacén en memoria: no hay red ni cuentas reales. Solo en local.

    uv run pytest tests/e2e/test_cuenta.py --browser chromium
"""

import json

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
export const onAuthStateChanged = (_a, callback) => { callback(user); };
export const getRedirectResult = async () => null;
export const signInWithRedirect = async () => {};
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

    def get(self, uid):
        return dict(self.docs.get(uid, {}))

    def put(self, uid, preferences):
        self.docs[uid] = dict(preferences)

    def get_consent(self, uid):
        return self.consents.get(uid)

    def put_consent(self, uid, version):
        self.consents[uid] = version

    def get_profile(self, uid):
        return {}

    def put_profile(self, uid, profile):
        pass

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


@pytest.fixture
def ready(page: Page, account_url: str) -> Page:
    def route(r):
        url = r.request.url
        if "firebase-app.js" in url:
            return r.fulfill(body=APP_JS, content_type="text/javascript")
        if "firebase-auth.js" in url:
            return r.fulfill(body=AUTH_JS, content_type="text/javascript")
        return r.abort()  # nada sale a Internet (Bootstrap, fuentes)

    page.route(lambda url: not url.startswith(account_url), route)
    page.goto(account_url + "/entrar.html")
    expect(page.locator("#paso-listo")).to_be_visible()
    return page


def test_download_gives_a_json_with_the_persons_data(ready: Page):
    with ready.expect_download() as info:
        ready.click("#descargar")
    download = info.value
    assert download.suggested_filename == "acordia-mis-datos.json"
    body = json.loads(open(download.path(), encoding="utf-8").read())
    assert body["stored"]["preferences"] == {"muted": True}
    assert body["firebaseAuthentication"]["email"] == "persona.sintetica@example.test"


def test_delete_always_asks_first_and_cancelling_touches_nothing(ready: Page, store):
    ready.click("#borrar")
    expect(ready.locator("#borrar-confirmar")).to_be_visible()
    assert store.docs and ready.evaluate("window.__calls") == []  # un clic no borra nada
    ready.click("#borrar-no")
    expect(ready.locator("#borrar-confirmar")).to_be_hidden()
    assert store.docs and store.consents


def test_confirming_deletes_our_data_and_then_the_account(ready: Page, store):
    ready.click("#borrar")
    ready.click("#borrar-si")
    expect(ready.locator("#estado")).to_have_text("Eliminamos tu cuenta y tus datos.")
    assert store.docs == {} and store.consents == {}
    assert ready.evaluate("window.__calls") == ["deleteUser"]
    expect(ready.locator("#paso-entrar")).to_be_visible()


def test_an_old_session_still_deletes_our_data_and_says_what_to_do(ready: Page, store):
    ready.evaluate("window.__failDelete = 'auth/requires-recent-login'")
    ready.click("#borrar")
    ready.click("#borrar-si")
    expect(ready.locator("#error")).to_contain_text("sesión reciente")
    expect(ready.locator("#error")).to_contain_text("No acepto")
    assert store.docs == {} and store.consents == {}  # lo nuestro ya se borró
    assert ready.evaluate("window.__calls") == ["deleteUser", "signOut"]

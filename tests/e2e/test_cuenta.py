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
    expect(page.locator("#entrar-facebook")).to_be_visible()
    expect(page.locator("#paso-consentimiento")).to_be_hidden()
    expect(page.get_by_text("Tus datos")).to_have_count(0)
    assert "entrar.html" in page.url

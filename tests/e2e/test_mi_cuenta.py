"""«Mi cuenta» en un navegador real (S104): continuar, avance, perfil y tus datos.

El SDK de Firebase (gstatic) es un doble y la API es la del sitio con un almacén en memoria:
sin red ni cuentas reales. Solo local.

    uv run pytest tests/e2e/test_mi_cuenta.py -m e2e --browser chromium
"""

import json

import pytest
from playwright.sync_api import Page, expect

from musicsite.accounts import (
    NOTICE_VERSION,
    Accounts,
    RateLimiter,
    clean_progress,
    identity_from_claims,
    merge_result,
    uid_from_claims,
)
from musicsite.app import create_app

CLAIMS = {
    "uid": "uid1",
    "email": "persona.sintetica@example.test",
    "firebase": {"sign_in_provider": "google.com"},
}
CATALOG = [
    {
        "id": "basico",
        "title": "Básico",
        "lessons": [{"id": "do-es-c", "title": "Do es C"}, {"id": "pulso", "title": "Pulso"}],
    }
]
APP_JS = "export function initializeApp() { return {}; }"
AUTH_JS = """
const calls = (window.__calls = []);
const user = { getIdToken: async () => "p1" };
const auth = { get currentUser() { return window.__signedOut ? null : user; } };
export const getAuth = () => auth;
export const onAuthStateChanged = (_a, cb) => {
  setTimeout(() => cb(window.__signedOut ? null : user), 0);
  return () => {};
};
export const signOut = async () => { calls.push("signOut"); };
export const deleteUser = async () => { calls.push("deleteUser"); };
"""


class Verifier:
    def verify(self, token):
        return uid_from_claims(CLAIMS) if token == "p1" else None

    def identity(self, token):
        return identity_from_claims(CLAIMS) if token == "p1" else None


class Store:
    def __init__(self, consented=True):
        self.consents = {"uid1": NOTICE_VERSION} if consented else {}
        self.profile, self.cont, self.progress, self.deleted = {}, {}, {}, False

    def get(self, uid):
        return {}

    def put(self, uid, preferences):
        pass

    def get_consent(self, uid):
        return self.consents.get(uid)

    def put_consent(self, uid, version):
        self.consents[uid] = version

    def get_profile(self, uid):
        return dict(self.profile)

    def put_profile(self, uid, profile):
        self.profile = dict(profile)

    def get_continue(self, uid):
        return json.loads(json.dumps(self.cont))

    def put_continue(self, uid, value):
        self.cont.update(value)

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
        return clean_progress(self.progress)

    def put_result(self, uid, path, lesson, points, stars):
        merged = merge_result(self.progress, path, lesson, points, stars)
        if merged is not None:
            self.progress.setdefault(path, {})[lesson] = merged
        return merged

    def export(self, uid):
        return {
            "consent": None,
            "preferences": {},
            "progress": self.progress,
            "profile": self.profile,
            "continue": self.cont,
            "favorites": [],
            "repertoires": {},
        }

    def delete(self, uid):
        self.deleted = True
        self.profile, self.cont, self.progress, self.consents = {}, {}, {}, {}


@pytest.fixture
def store():
    s = Store()
    s.cont = {"lesson": {"path": "basico", "lesson": "pulso"}, "song": "camara-lenta"}
    s.progress = {"basico": {"do-es-c": {"points": 90, "stars": 3, "plays": 2}}}
    return s


@pytest.fixture
def account_url(store, serve_local):
    accounts = Accounts(Verifier(), store, RateLimiter(limit=200, window=60))
    return serve_local(create_app(accounts=accounts, firebase_api_key="clave-de-prueba"))


def open_page(page: Page, account_url: str, signed_out=False):
    def route(r):
        url = r.request.url
        if "firebase-app.js" in url:
            return r.fulfill(body=APP_JS, content_type="text/javascript")
        if "firebase-auth.js" in url:
            return r.fulfill(body=AUTH_JS, content_type="text/javascript")
        if url.endswith("/aprende/lessons.json"):
            return r.fulfill(body=json.dumps(CATALOG), content_type="application/json")
        if url.startswith(account_url):
            return r.continue_()
        return r.abort()

    page.route("**/*", route)
    if signed_out:
        page.add_init_script("window.__signedOut = true")
    page.goto(account_url + "/mi-acordia.html")


def test_without_a_session_it_asks_to_enter_and_comes_back_here(page: Page, account_url):
    open_page(page, account_url, signed_out=True)
    expect(page.locator("#sin-sesion")).to_be_visible()
    expect(page.locator("#contenido")).to_be_hidden()
    assert page.get_attribute("#entrar", "href") == "entrar.html?volver=/mi-acordia.html"


def test_without_consent_it_sends_to_accept_the_notice(page: Page, account_url, store):
    store.consents = {}
    open_page(page, account_url)
    expect(page.locator("#sin-consentimiento")).to_be_visible()
    expect(page.locator("#contenido")).to_be_hidden()


def test_it_shows_where_to_continue_and_the_progress_with_real_titles(page: Page, account_url):
    open_page(page, account_url)
    expect(page.locator("#contenido")).to_be_visible()
    expect(page.locator("#continuar")).to_contain_text("Pulso")
    assert page.get_attribute("#continuar a >> nth=0", "href") == "/aprende/#/basico/pulso"
    expect(page.locator("#continuar")).to_contain_text(
        "Cámara lenta · Javiera Mena"
    )  # título real, de /songs.json
    assert page.get_attribute("#continuar a >> nth=1", "href") == "cancion-camara-lenta.html"
    avance = page.locator("#avance")
    expect(avance).to_contain_text("Básico")
    expect(avance).to_contain_text("1/2 lecciones · 3/6 estrellas · 90 puntos")
    expect(avance.locator(".ac-lesson-card", has_text="Do es C")).to_contain_text("90 pts")
    expect(avance.locator(".ac-lesson-card", has_text="Pulso")).to_contain_text("Sin jugar")


def test_with_nothing_yet_it_invites_to_start(page: Page, account_url, store):
    store.cont, store.progress = {}, {}
    open_page(page, account_url)
    expect(page.locator("#continuar")).to_contain_text("Tu primera lección en Aprende")
    expect(page.locator("#avance")).to_contain_text("0/2 lecciones")


def test_the_form_only_appears_once_the_data_is_loaded(page: Page, account_url, store):
    """Lo escrito no queda pisado por una carga tardía: el contenido espera a los datos."""
    store.profile = {"name": "Ana"}
    open_page(page, account_url)
    expect(page.locator("#contenido")).to_be_visible()
    expect(page.locator("#p-nombre")).to_have_value(
        "Ana"
    )  # ya cargado en cuanto se ve el formulario


def settings(page: Page):
    page.click("#tab-configuracion")
    expect(page.locator("#panel-configuracion")).to_be_visible()


def test_the_profile_is_saved_and_greets_by_name(page: Page, account_url, store):
    open_page(page, account_url)
    settings(page)
    page.fill("#p-nombre", "  Ana   María ")
    page.select_option("#p-instrumento", "guitarra")
    page.select_option("#p-nivel", "medio")
    page.click("#perfil button[type=submit]")
    expect(page.locator("#perfil-estado")).to_have_text("Guardado.")
    expect(page.locator("#saludo")).to_have_text("Hola, Ana María")
    assert store.profile == {"name": "Ana María", "instrument": "guitarra", "level": "medio"}
    page.reload()
    expect(page.locator("#p-nombre")).to_have_value("Ana María")
    expect(page.locator("#p-nivel")).to_have_value("medio")


def test_a_hostile_name_is_rejected_and_never_becomes_html(page: Page, account_url, store):
    open_page(page, account_url)
    settings(page)
    page.fill("#p-nombre", "<img src=x onerror=alert(1)>")
    page.click("#perfil button[type=submit]")
    expect(page.locator("#perfil-estado")).to_contain_text("Revisa el nombre")
    assert store.profile == {}
    assert page.locator("#saludo img").count() == 0


def test_a_name_with_html_stored_elsewhere_is_shown_as_text(page: Page, account_url, store):
    store.profile = {
        "name": "Ana & <Co>"
    }  # algo que ya estuviera guardado: igual se muestra como texto
    open_page(page, account_url)
    expect(page.locator("#saludo")).to_have_text("Hola, Ana & <Co>")
    assert page.locator("#saludo *").count() == 0


def test_deleting_always_asks_and_then_removes_our_data_and_the_account(
    page: Page, account_url, store
):
    open_page(page, account_url)
    settings(page)
    page.click("#borrar")
    expect(page.locator("#borrar-confirmar")).to_be_visible()
    assert not store.deleted and page.evaluate("window.__calls") == []
    page.click("#borrar-no")
    expect(page.locator("#borrar-confirmar")).to_be_hidden()
    page.click("#borrar")
    page.click("#borrar-si")
    expect(page.locator("#estado")).to_have_text("Eliminamos tu cuenta y tus datos.")
    assert store.deleted and page.evaluate("window.__calls") == ["deleteUser"]
    expect(page.locator("#contenido")).to_be_hidden()


def test_signing_out_clears_the_session_hint(page: Page, account_url):
    open_page(page, account_url)
    expect(page.locator("#contenido")).to_be_visible()
    settings(page)
    assert page.evaluate("localStorage.getItem('acordia-session')") == "1"
    page.click("#salir")
    expect(page.locator("#estado")).to_have_text("Cerraste tu sesión.")
    assert page.evaluate("localStorage.getItem('acordia-session')") is None
    assert page.evaluate("window.__calls") == ["signOut"]


def test_download_has_the_new_data(page: Page, account_url, store):
    store.profile = {"name": "Ana"}
    open_page(page, account_url)
    settings(page)
    with page.expect_download() as info:
        page.click("#descargar")
    body = json.loads(open(info.value.path(), encoding="utf-8").read())
    assert body["stored"]["profile"] == {"name": "Ana"}
    assert body["stored"]["continue"]["song"] == "camara-lenta"


# --- el panel: submenú, cifras, insignias y avance con barras (S106)
def test_the_summary_is_the_default_and_the_dangerous_controls_live_only_in_settings(
    page: Page, account_url
):
    open_page(page, account_url)
    expect(page.locator("#panel-resumen")).to_be_visible()
    expect(page.locator("#panel-configuracion")).to_be_hidden()
    for hidden in ("#borrar", "#descargar", "#perfil", "#salir"):
        expect(page.locator(hidden)).to_be_hidden()  # en el resumen no hay nada para borrar
    expect(page.locator("#tab-resumen")).to_have_attribute("aria-selected", "true")
    settings(page)
    expect(page.locator("#panel-resumen")).to_be_hidden()
    expect(page.locator("#tab-configuracion")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#borrar")).to_be_visible()
    page.click("#tab-resumen")
    expect(page.locator("#panel-resumen")).to_be_visible()


def test_the_settings_tab_opens_from_the_address_and_with_the_arrow_keys(page: Page, account_url):
    open_page(page, account_url)
    expect(page.locator("#contenido")).to_be_visible()
    page.focus("#tab-resumen")
    page.keyboard.press("ArrowRight")
    expect(page.locator("#panel-configuracion")).to_be_visible()
    page.keyboard.press("ArrowLeft")
    expect(page.locator("#panel-resumen")).to_be_visible()
    page.goto(account_url + "/mi-acordia.html#configuracion")
    expect(page.locator("#panel-configuracion")).to_be_visible()


def test_the_danger_zone_is_the_last_thing_in_settings(page: Page, account_url):
    open_page(page, account_url)
    settings(page)
    titles = page.locator("#panel-configuracion h2").all_inner_texts()
    assert titles == ["Tu perfil", "Tus datos y tu sesión", "Zona de peligro"]


def test_the_panel_shows_the_numbers_and_the_profile_chips(page: Page, account_url, store):
    store.profile = {"name": "Ana", "instrument": "guitarra", "level": "medio"}
    open_page(page, account_url)
    stats = page.locator("#cifras")
    expect(stats).to_contain_text("1/2")  # lecciones jugadas
    expect(stats).to_contain_text("3/6")  # estrellas
    expect(stats).to_contain_text("90")  # puntos
    expect(page.locator("#chips")).to_contain_text("Guitarra")
    expect(page.locator("#chips")).to_contain_text("Nivel medio")


def test_badges_light_up_only_for_what_was_done(page: Page, account_url, store):
    store.progress = {"basico": {"do-es-c": {"points": 100, "stars": 3, "plays": 1}}}
    open_page(page, account_url)
    expect(page.locator("#contenido")).to_be_visible()
    on = page.locator("#insignias .is-on")
    off = page.locator("#insignias .is-off")
    assert on.count() == 3 and off.count() == 3
    expect(on).to_contain_text(["Primera lección", "Tres estrellas", "A mitad de camino"])
    expect(off).to_contain_text(["Ruta completa", "Primer favorito", "Primer repertorio"])
    assert page.locator('#insignias [aria-label="Insignia Primera lección: lograda"]').count() == 1


def test_a_finished_route_and_a_favorite_unlock_their_badges(page: Page, account_url, store):
    store.progress = {
        "basico": {
            "do-es-c": {"points": 90, "stars": 3, "plays": 1},
            "pulso": {"points": 40, "stars": 1, "plays": 1},
        }
    }
    open_page(page, account_url)
    expect(page.locator("#insignias .is-on", has_text="Ruta completa")).to_have_count(1)
    assert page.locator("#insignias .is-on").count() == 4


def test_each_lesson_card_has_a_progress_bar_with_its_points(page: Page, account_url):
    open_page(page, account_url)
    card = page.locator(".ac-lesson-card", has_text="Do es C")
    bar = card.locator('[role="progressbar"]')
    assert bar.get_attribute("aria-valuenow") == "90"
    assert (
        page.locator('[aria-label="Avance de Básico"]').get_attribute("aria-valuenow") == "50"
    )  # 1 de 2 lecciones
    assert (
        page.locator(".ac-lesson-card", has_text="Pulso")
        .locator('[role="progressbar"]')
        .get_attribute("aria-valuenow")
        == "0"
    )


def test_with_no_progress_the_bars_are_empty_and_no_badge_is_lit(page: Page, account_url, store):
    store.progress = {}
    open_page(page, account_url)
    expect(page.locator("#contenido")).to_be_visible()
    assert page.locator("#insignias .is-on").count() == 0
    assert page.locator("#insignias .is-off").count() == 6  # las seis, apagadas: ya se dibujaron
    assert page.locator('[aria-label="Avance de Básico"]').get_attribute("aria-valuenow") == "0"

"""Tanda 2 de «Mi Acordia» en un navegador real (S105): cuenta en temas, favoritos y repertorios.

El SDK de Firebase (gstatic) es un doble y la API es la del sitio con un almacén en memoria:
sin red ni cuentas reales.
Solo local.

    uv run pytest tests/e2e/test_cuenta_completa.py -m e2e --browser chromium
"""

import json

import pytest
from playwright.sync_api import Page, expect

from musicsite.accounts import (
    NOTICE_VERSION,
    Accounts,
    RateLimiter,
    clean_favorites_stored,
    clean_preferences,
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
const auth = { get currentUser() { return window.__signedOut ? null : user; } };
export const getAuth = () => auth;
export const onAuthStateChanged = (_a, cb) => {
  setTimeout(() => cb(window.__signedOut ? null : user), 0);
  return () => {};
};
export const signOut = async () => { calls.push("signOut"); };
export const deleteUser = async () => { calls.push("deleteUser"); };
"""
SONG = "camara-lenta"
OTHER = "2022"


class Verifier:
    def verify(self, token):
        return uid_from_claims(CLAIMS) if token == "p1" else None

    def identity(self, token):
        return identity_from_claims(CLAIMS) if token == "p1" else None


class Store:
    def __init__(self):
        self.consents = {"uid1": NOTICE_VERSION}
        self.prefs, self.favorites, self.repertoires, self.cont = {}, set(), {}, {}
        self.pref_puts = []

    def get(self, uid):
        return dict(self.prefs)

    def put(self, uid, preferences):
        self.pref_puts.append(dict(preferences))
        self.prefs.update(preferences)

    def get_consent(self, uid):
        return self.consents.get(uid)

    def put_consent(self, uid, version):
        self.consents[uid] = version

    def get_profile(self, uid):
        return {}

    def put_profile(self, uid, profile):
        pass

    def get_continue(self, uid):
        return dict(self.cont)

    def put_continue(self, uid, value):
        self.cont.update(value)

    def get_favorites(self, uid):
        return clean_favorites_stored({s: True for s in self.favorites})

    def put_favorite(self, uid, song, favorite):
        self.favorites.add(song) if favorite else self.favorites.discard(song)
        return sorted(self.favorites)

    def get_repertoires(self, uid):
        return json.loads(json.dumps(self.repertoires))

    def put_repertoire(self, uid, rid, value):
        self.repertoires[rid] = json.loads(json.dumps(value))
        return True

    def delete_repertoire(self, uid, rid):
        self.repertoires.pop(rid, None)

    def get_progress(self, uid):
        return {}

    def put_result(self, uid, path, lesson, points, stars):
        return {"points": points, "stars": stars, "plays": 1}

    def export(self, uid):
        return {"consent": None, "preferences": clean_preferences(self.prefs), "progress": {}}

    def delete(self, uid):
        self.__init__()


@pytest.fixture
def store():
    return Store()


@pytest.fixture
def url(store, serve_local):
    accounts = Accounts(Verifier(), store, RateLimiter(limit=1000, window=60))
    return serve_local(create_app(accounts=accounts, firebase_api_key="clave-de-prueba"))


def until(page: Page, expression: str, seconds: float = 8):
    """Espera a que una expresión de la página sea verdadera.

    `wait_for_function` evalúa texto en la página y la política
    de seguridad del sitio (sin `unsafe-eval`) lo prohíbe; `evaluate` no pasa por ella."""
    for _ in range(int(seconds * 10)):
        if page.evaluate(expression):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"no se cumplió: {expression}")


def prepare(page: Page, url: str, *, signed_out=False, hint=True, local=None):
    """Instala el doble de Firebase y la marca de sesión; devuelve la lista de pedidos a gstatic."""
    gstatic = []

    def route(r):
        u = r.request.url
        if "gstatic.com" in u:
            gstatic.append(u)
            body = APP_JS if "firebase-app.js" in u else AUTH_JS
            return r.fulfill(body=body, content_type="text/javascript")
        return r.continue_() if u.startswith(url) else r.abort()

    page.route("**/*", route)
    script = ["window.__signedOut = %s;" % ("true" if signed_out else "false")]
    if hint:
        script.append("try { localStorage.setItem('acordia-session', '1'); } catch (e) {}")
    for key, value in (local or {}).items():
        # solo la primera vez: así una recarga no pisa lo que la página ya guardó
        script.append(
            f"if (!sessionStorage.getItem('sembrado-{key}')) {{"
            f" localStorage.setItem('{key}', '{value}');"
            f" sessionStorage.setItem('sembrado-{key}', '1'); }}"
        )
    page.add_init_script("\n".join(script))
    return gstatic


# --- la cuenta en una página de tema
def test_without_a_session_hint_the_song_page_never_loads_firebase(page: Page, url):
    gstatic = prepare(page, url, hint=False)
    page.goto(f"{url}/cancion-{SONG}.html")
    page.wait_for_timeout(800)
    assert gstatic == [] and page.locator(".ac-util-btns >> text=Favorito").count() == 0


def test_the_embedded_song_page_has_no_account_script_nor_site_chrome(page: Page, url):
    gstatic = prepare(page, url)
    page.goto(f"{url}/cancion-{SONG}.html?embed=1")
    page.wait_for_timeout(800)
    assert (
        gstatic == []
        and page.locator(".navbar").is_hidden()
        and page.locator("footer.ac-footer").is_hidden()
    )


def test_a_signed_in_person_can_favorite_and_the_last_song_is_remembered(page: Page, url, store):
    prepare(page, url)
    page.goto(f"{url}/cancion-{SONG}.html")
    button = page.get_by_role("button", name="Favorito")
    expect(button).to_have_attribute("aria-pressed", "false")
    button.click()
    expect(button).to_have_attribute("aria-pressed", "true")
    assert store.favorites == {SONG} and store.cont == {"song": SONG}
    button.click()
    expect(button).to_have_attribute("aria-pressed", "false")
    assert store.favorites == set()


def test_a_stale_session_hint_without_a_session_is_cleared(page: Page, url):
    prepare(page, url, signed_out=True)
    page.goto(f"{url}/cancion-{SONG}.html")
    until(page, "localStorage.getItem('acordia-session') === null")


def test_repertoire_panel_creates_adds_and_removes(page: Page, url, store):
    prepare(page, url)
    page.goto(f"{url}/cancion-{SONG}.html")
    page.get_by_role("button", name="Repertorio").click()
    page.get_by_label("Nombre del repertorio nuevo").fill("Para ensayar")
    page.get_by_role("button", name="Crear con este tema").click()
    expect(page.get_by_text("Creaste «Para ensayar» con este tema.")).to_be_visible()
    (rid,) = store.repertoires
    assert store.repertoires[rid] == {"name": "Para ensayar", "songs": [SONG]}
    box = page.get_by_label("Para ensayar")
    expect(box).to_be_checked()
    box.uncheck()
    expect(page.get_by_text("Quitado de «Para ensayar».")).to_be_visible()
    assert store.repertoires[rid]["songs"] == []
    box.check()
    expect(page.get_by_text("Agregado a «Para ensayar».")).to_be_visible()
    assert store.repertoires[rid]["songs"] == [SONG]


def test_a_hostile_repertoire_name_is_refused_with_a_message(page: Page, url, store):
    prepare(page, url)
    page.goto(f"{url}/cancion-{SONG}.html")
    page.get_by_role("button", name="Repertorio").click()
    page.get_by_label("Nombre del repertorio nuevo").fill("<img src=x onerror=alert(1)>")
    page.get_by_role("button", name="Crear con este tema").click()
    expect(page.get_by_text("Revisa el nombre")).to_be_visible()
    assert store.repertoires == {} and page.locator("img[src=x]").count() == 0


# --- preferencias del reproductor, sincronizadas con la cuenta
def test_account_preferences_win_and_the_page_reloads_once_to_use_them(page: Page, url, store):
    store.prefs = {"muted": True, "volMetronome": 0.3, "theme": "light"}
    prepare(page, url, local={"acordia-sin-sonido": "0"})
    page.goto(f"{url}/cancion-{SONG}.html")
    until(page, "localStorage.getItem('acordia-sin-sonido') === '1'")
    until(page, "localStorage.getItem('ac-vol-met') === '0.3'")
    until(page, "localStorage.getItem('acordia-tema') === 'light'")
    assert (
        page.evaluate("sessionStorage.getItem('acordia-prefs-aplicadas')") == "1"
    )  # se recargó una sola vez


def test_the_first_time_this_browsers_preferences_go_up_to_the_account(page: Page, url, store):
    prepare(
        page,
        url,
        local={"acordia-sin-sonido": "1", "acordia-cuenta-inicial": "0", "ac-vol-met": "0.5"},
    )
    page.goto(f"{url}/cancion-{SONG}.html")
    page.wait_for_timeout(300)
    for _ in range(40):
        if store.prefs:
            break
        page.wait_for_timeout(100)
    # el tema «dark» lo guarda la propia librería al cargar la página: viaja con lo demás
    assert store.prefs == {"muted": True, "countIn": False, "volMetronome": 0.5, "theme": "dark"}


def test_changing_a_player_setting_saves_it_in_the_account_after_a_short_pause(
    page: Page, url, store
):
    store.prefs = {"muted": False}
    prepare(page, url, local={"acordia-sin-sonido": "0"})
    page.goto(f"{url}/cancion-{SONG}.html")
    expect(page.get_by_role("button", name="Favorito")).to_be_visible()  # la cuenta ya está lista
    page.evaluate("localStorage.setItem('acordia-sin-sonido', '1')")
    for _ in range(50):
        if store.prefs.get("muted") is True:
            break
        page.wait_for_timeout(100)
    assert store.prefs["muted"] is True


def test_invalid_local_preference_values_are_not_sent(page: Page, url, store):
    prepare(
        page,
        url,
        local={
            "acordia-instrumento": "tuba",
            "ac-vol-met": "no-es-numero",
            "acordia-sin-sonido": "1",
        },
    )
    page.goto(f"{url}/cancion-{SONG}.html")
    for _ in range(40):
        if store.prefs:
            break
        page.wait_for_timeout(100)
    assert store.prefs == {"muted": True, "theme": "dark"}  # ni «tuba» ni «no-es-numero» salen


# --- Mi cuenta con favoritos y repertorios
def test_my_account_lists_favorites_with_real_titles_and_removes_them(page: Page, url, store):
    store.favorites = {SONG, OTHER}
    prepare(page, url)
    page.goto(f"{url}/mi-acordia.html")
    favs = page.locator("#favoritos")
    expect(favs).to_contain_text("Cámara lenta · Javiera Mena")
    page.get_by_role("button", name="Quitar Cámara lenta · Javiera Mena de favoritos").click()
    expect(favs).not_to_contain_text("Cámara lenta")
    assert store.favorites == {OTHER}


def test_my_account_lists_repertoires_and_creates_one_and_opens_it(page: Page, url, store):
    store.repertoires = {"abc123": {"name": "Mi lista", "songs": [SONG]}}
    prepare(page, url)
    page.goto(f"{url}/mi-acordia.html")
    expect(page.locator("#repertorios")).to_contain_text("Mi lista")
    expect(page.locator("#repertorios")).to_contain_text("1 tema")
    page.fill("#nr-nombre", "Otro")
    page.click("#nuevo-repertorio button")
    page.wait_for_url("**/repertorio.html?id=*")
    assert {r["name"] for r in store.repertoires.values()} == {"Mi lista", "Otro"}


# --- la página del repertorio con su reproductor
@pytest.fixture
def with_repertoire(store):
    store.repertoires = {"abc123": {"name": "Para ensayar", "songs": [SONG, OTHER, "moizefala"]}}
    return store


def test_the_repertoire_page_plays_each_song_in_an_embedded_player(
    page: Page, url, with_repertoire
):
    prepare(page, url)
    page.goto(f"{url}/repertorio.html?id=abc123")
    expect(page.locator("#titulo")).to_have_text("Para ensayar")
    expect(page.locator("#temas li")).to_have_count(3)
    frame = page.locator("#marco")
    assert frame.get_attribute("src") == f"cancion-{SONG}.html?embed=1"
    expect(page.locator("#actual")).to_contain_text("1/3 · Cámara lenta")
    expect(page.frame_locator("#marco").locator("h1")).to_have_text(
        "Cámara lenta"
    )  # el tema carga dentro del iframe
    expect(page.frame_locator("#marco").locator(".navbar")).to_be_hidden()
    page.click("#siguiente")
    assert frame.get_attribute("src") == f"cancion-{OTHER}.html?embed=1"
    expect(page.locator("#actual")).to_contain_text("2/3")
    page.click("#anterior")
    assert frame.get_attribute("src") == f"cancion-{SONG}.html?embed=1"
    expect(page.locator("#anterior")).to_be_disabled()


def test_a_repertoire_can_be_reordered_and_songs_removed_and_it_is_saved(
    page: Page, url, with_repertoire
):
    prepare(page, url)
    page.goto(f"{url}/repertorio.html?id=abc123")
    expect(page.locator("#temas li")).to_have_count(3)
    page.locator("#temas li").nth(0).locator("[data-move=down]").click()
    expect(page.locator("#actual")).to_contain_text(
        "2/3 · Cámara lenta"
    )  # el que suena se mueve con su lugar
    assert with_repertoire.repertoires["abc123"]["songs"] == [OTHER, SONG, "moizefala"]
    page.locator("#temas li").nth(2).locator("[data-remove]").click()
    expect(page.locator("#temas li")).to_have_count(2)
    assert with_repertoire.repertoires["abc123"]["songs"] == [OTHER, SONG]


def test_a_repertoire_is_renamed_and_deleted_only_after_confirming(
    page: Page, url, with_repertoire
):
    prepare(page, url)
    page.goto(f"{url}/repertorio.html?id=abc123")
    page.fill("#r-nombre", "Nuevo nombre")
    page.click("#r-renombrar")
    expect(page.locator("#titulo")).to_have_text("Nuevo nombre")
    assert with_repertoire.repertoires["abc123"]["name"] == "Nuevo nombre"
    page.click("#r-borrar")
    expect(page.locator("#r-confirmar")).to_be_visible()
    assert "abc123" in with_repertoire.repertoires  # un clic no borra
    page.click("#r-borrar-no")
    expect(page.locator("#r-confirmar")).to_be_hidden()
    page.click("#r-borrar")
    page.click("#r-borrar-si")
    page.wait_for_url("**/repertorio.html")
    assert with_repertoire.repertoires == {}


def test_an_unknown_repertoire_id_shows_the_list_with_a_message(page: Page, url, with_repertoire):
    prepare(page, url)
    page.goto(f"{url}/repertorio.html?id=nadie99")
    expect(page.locator("#error")).to_have_text("No encontramos ese repertorio.")
    expect(page.locator("#lista-repertorios")).to_be_visible()


def test_the_repertoire_page_asks_to_enter_without_a_session(page: Page, url):
    prepare(page, url, signed_out=True)
    page.goto(f"{url}/repertorio.html")
    expect(page.locator("#sin-sesion")).to_be_visible()
    assert page.get_attribute("#entrar", "href") == "entrar.html?volver=/repertorio.html"

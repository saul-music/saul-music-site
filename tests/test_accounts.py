"""Cuentas del sitio (C26, S99): tokens, preferencias y límites. Todo sintético."""

import json
import logging
import re

import pytest
from fastapi.testclient import TestClient

from musicsite.accounts import (
    MAX_BODY_BYTES,
    MAX_FAVORITES,
    MAX_REPERTOIRES,
    MAX_SONGS_PER_REPERTOIRE,
    MAX_TRACKED_PEOPLE,
    NOTICE_VERSION,
    Accounts,
    InvalidPreferences,
    RateLimiter,
    accounts_from_env,
    clean_continue,
    clean_favorite,
    clean_preferences,
    clean_profile,
    clean_progress,
    clean_repertoire,
    identity_from_claims,
    merge_result,
    uid_from_claims,
)
from musicsite.app import create_app

PUBLIC = {
    "uid": "uid1",
    "email": "persona.sintetica@example.test",
    "name": "Persona Sintética",
    "firebase": {"sign_in_provider": "google.com"},
}
OTHER = {"uid": "uid2", "firebase": {"sign_in_provider": "facebook.com"}}
TEAM = {"uid": "uid3", "firebase": {"sign_in_provider": "password", "tenant": "equipo-x"}}
TENANT_GOOGLE = {
    "uid": "uid4",
    "firebase": {"sign_in_provider": "google.com", "tenant": "equipo-x"},
}
TOKENS = {"p1": PUBLIC, "p2": OTHER, "team": TEAM, "tenant-google": TENANT_GOOGLE}


class FakeVerifier:
    def verify(self, token):
        claims = TOKENS.get(token)
        return uid_from_claims(claims) if claims else None

    def identity(self, token):
        claims = TOKENS.get(token)
        return identity_from_claims(claims) if claims else None


class FakeStore:
    def __init__(self, consents=None):
        self.docs = {}
        self.consents = dict(consents or {})
        self.progress = {}
        self.profiles = {}
        self.continues = {}
        self.favorites = {}
        self.repertoires = {}

    def get(self, uid):
        return dict(self.docs.get(uid, {}))

    def put(self, uid, preferences):
        self.docs[uid] = dict(preferences)

    def get_consent(self, uid):
        return self.consents.get(uid)

    def put_consent(self, uid, version):
        self.consents[uid] = version

    def get_profile(self, uid):
        return dict(self.profiles.get(uid, {}))

    def put_profile(self, uid, profile):
        self.profiles[uid] = dict(profile)

    def get_continue(self, uid):
        return json.loads(json.dumps(self.continues.get(uid, {})))

    def put_continue(self, uid, value):
        self.continues.setdefault(uid, {}).update(value)

    def get_favorites(self, uid):
        return sorted(self.favorites.get(uid, set()))

    def put_favorite(self, uid, song, favorite):
        mine = self.favorites.setdefault(uid, set())
        if favorite and song not in mine and len(mine) >= MAX_FAVORITES:
            return None
        mine.add(song) if favorite else mine.discard(song)
        return sorted(mine)

    def get_repertoires(self, uid):
        return json.loads(json.dumps(self.repertoires.get(uid, {})))

    def put_repertoire(self, uid, rid, value):
        mine = self.repertoires.setdefault(uid, {})
        if rid not in mine and len(mine) >= MAX_REPERTOIRES:
            return False
        mine[rid] = json.loads(json.dumps(value))
        return True

    def delete_repertoire(self, uid, rid):
        self.repertoires.get(uid, {}).pop(rid, None)

    def get_progress(self, uid):
        return json.loads(json.dumps(self.progress.get(uid, {})))

    def put_result(self, uid, path, lesson, points, stars):
        mine = self.progress.setdefault(uid, {})
        merged = merge_result(mine, path, lesson, points, stars)
        if merged is not None:
            mine.setdefault(path, {})[lesson] = merged
        return merged

    def export(self, uid):
        consent = self.consents.get(uid)
        return {
            "consent": {"version": consent, "adult": True, "at": None} if consent else None,
            "preferences": dict(self.docs.get(uid, {})),
            "progress": self.get_progress(uid),
            "profile": self.get_profile(uid),
            "continue": self.get_continue(uid),
            "favorites": self.get_favorites(uid),
            "repertoires": self.get_repertoires(uid),
        }

    def delete(self, uid):
        self.docs.pop(uid, None)
        self.consents.pop(uid, None)
        self.progress.pop(uid, None)
        self.profiles.pop(uid, None)
        self.continues.pop(uid, None)
        self.favorites.pop(uid, None)
        self.repertoires.pop(uid, None)


@pytest.fixture
def store():
    # Las personas de las pruebas de preferencias ya aceptaron el aviso vigente.
    return FakeStore({"uid1": NOTICE_VERSION, "uid2": NOTICE_VERSION})


def make_client(store):
    accounts = Accounts(FakeVerifier(), store, RateLimiter(limit=5, window=60))
    return TestClient(create_app(accounts=accounts))


@pytest.fixture
def client(store):
    return make_client(store)


@pytest.fixture
def bare():
    """Nadie ha aceptado nada."""
    store = FakeStore()
    return make_client(store), store


def bearer(token="p1"):
    return {"Authorization": f"Bearer {token}"}


def put(client, preferences, token="p1", **kwargs):
    return client.put(
        "/api/me/preferences", headers=bearer(token), json={"preferences": preferences}, **kwargs
    )


# --- quién llama
@pytest.mark.parametrize("claims", [PUBLIC, OTHER])
def test_public_group_people_are_accepted(claims):
    assert uid_from_claims(claims) == claims["uid"]


@pytest.mark.parametrize(
    "claims",
    [
        TEAM,
        TENANT_GOOGLE,
        {"uid": "u", "firebase": {"sign_in_provider": "password"}},
        {"uid": "u", "firebase": {"sign_in_provider": "anonymous"}},
        {"uid": "u", "firebase": {"sign_in_provider": "custom"}},
        {"uid": "u", "firebase": {}},
        {"uid": "u", "firebase": "google.com"},
        {"uid": "u"},
        {"firebase": {"sign_in_provider": "google.com"}},
        {"uid": 7, "firebase": {"sign_in_provider": "google.com"}},
        {"uid": "../otro", "firebase": {"sign_in_provider": "google.com"}},
        {"uid": "", "firebase": {"sign_in_provider": "google.com"}},
    ],
)
def test_everyone_else_is_rejected(claims):
    assert uid_from_claims(claims) is None


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer"}, {"Authorization": "Basic p1"}, bearer("malo")]
)
def test_no_valid_token_is_404_without_body(client, headers):
    for call in (
        client.get("/api/me/preferences", headers=headers),
        client.put("/api/me/preferences", headers=headers, json={}),
    ):
        assert call.status_code == 404 and call.content == b""


@pytest.mark.parametrize("token", ["team", "tenant-google"])
def test_the_teams_tokens_do_not_open_the_site_api(client, store, token):
    assert client.get("/api/me/preferences", headers=bearer(token)).status_code == 404
    assert put(client, {"muted": True}, token).status_code == 404
    assert store.docs == {}


# --- preferencias
def test_empty_at_first_and_reading_creates_nothing(client, store):
    response = client.get("/api/me/preferences", headers=bearer())
    assert response.status_code == 200 and response.json() == {"preferences": {}}
    assert store.docs == {}


def test_write_then_read_back(client, store):
    prefs = {
        "muted": True,
        "countIn": False,
        "instrument": "guitarra",
        "studyMode": "vertical",
        "theme": "oscuro",
        "volMetronome": 0.5,
    }
    assert put(client, prefs).json() == {"preferences": prefs}
    assert client.get("/api/me/preferences", headers=bearer()).json() == {"preferences": prefs}
    assert store.docs == {"uid1": prefs}


def test_write_replaces_and_empty_clears(client, store):
    put(client, {"muted": True, "theme": "claro"})
    put(client, {"muted": False})
    assert store.docs["uid1"] == {"muted": False}
    put(client, {})
    assert store.docs["uid1"] == {}


def test_people_never_see_each_others_data(client):
    put(client, {"muted": True}, "p1")
    put(client, {"theme": "claro"}, "p2")
    assert client.get("/api/me/preferences", headers=bearer("p1")).json() == {
        "preferences": {"muted": True}
    }
    assert client.get("/api/me/preferences", headers=bearer("p2")).json() == {
        "preferences": {"theme": "claro"}
    }


def test_the_uid_comes_from_the_token_never_from_the_request(client, store):
    client.put(
        "/api/me/preferences?uid=uid2",
        headers={**bearer("p1"), "X-Uid": "uid2"},
        json={"preferences": {"muted": True}},
    )
    assert list(store.docs) == ["uid1"]


@pytest.mark.parametrize(
    "preferences",
    [
        {"correo": "a@b.cl"},
        {"muted": "si"},
        {"muted": 1},
        {"countIn": None},
        {"instrument": "bajo"},
        {"instrument": ["guitarra"]},
        {"studyMode": "Vertical"},
        {"studyMode": "x" * 40},
        {"theme": "<script>"},
        {"volMetronome": 1.5},
        {"volMetronome": -0.1},
        {"volMetronome": True},
        {"volMetronome": float("nan")},
        {"volMetronome": "0.5"},
        [],
        "texto",
        None,
    ],
)
def test_invalid_preferences_are_422_and_not_stored(client, store, preferences):
    body = json.dumps({"preferences": preferences}, allow_nan=True)
    response = client.put(
        "/api/me/preferences",
        headers={**bearer(), "Content-Type": "application/json"},
        content=body,
    )
    assert response.status_code == 422 and response.content == b""
    assert store.docs == {}


@pytest.mark.parametrize(
    "raw", [b"", b"no es json", b"[]", b"null", b'{"otra": 1}', b'{"preferences": 3}']
)
def test_malformed_bodies_are_422(client, store, raw):
    response = client.put(
        "/api/me/preferences", headers={**bearer(), "Content-Type": "application/json"}, content=raw
    )
    assert response.status_code == 422 and store.docs == {}


def test_oversized_body_is_rejected_before_parsing(client, store):
    big = json.dumps({"preferences": {"theme": "a" * (MAX_BODY_BYTES + 10)}})
    response = client.put(
        "/api/me/preferences", headers={**bearer(), "Content-Type": "application/json"}, content=big
    )
    assert response.status_code == 413 and store.docs == {}


def test_oversized_body_without_length_is_also_rejected(store):
    with pytest.raises(InvalidPreferences):
        from musicsite.accounts import parse_body

        parse_body(b"x" * (MAX_BODY_BYTES + 1))


# --- caché y frecuencia
def test_responses_are_private_and_never_cached(client):
    for response in (
        client.get("/api/me/preferences", headers=bearer()),
        put(client, {"muted": True}),
    ):
        assert response.headers["cache-control"] == "private, no-store"
        assert "authorization" in response.headers["vary"].lower()


def test_rate_limit_is_per_person(client):
    codes = [client.get("/api/me/preferences", headers=bearer("p1")).status_code for _ in range(7)]
    assert codes == [200] * 5 + [429] * 2
    assert client.get("/api/me/preferences", headers=bearer("p2")).status_code == 200


def test_rate_limit_recovers_after_the_window():
    now = [0.0]
    limiter = RateLimiter(limit=2, window=60, clock=lambda: now[0])
    assert [limiter.allow("a") for _ in range(3)] == [True, True, False]
    now[0] = 61
    assert limiter.allow("a") is True


def test_rate_limit_memory_is_bounded():
    limiter = RateLimiter(limit=1, window=3600)
    for i in range(MAX_TRACKED_PEOPLE + 50):
        limiter.allow(f"u{i}")
    assert len(limiter._hits) <= MAX_TRACKED_PEOPLE


def test_invalid_tokens_are_not_counted_against_anyone(client):
    for _ in range(10):
        assert client.get("/api/me/preferences", headers=bearer("malo")).status_code == 404
    assert client.get("/api/me/preferences", headers=bearer("p1")).status_code == 200


# --- sin cuentas
def test_without_accounts_the_api_does_not_exist():
    client = TestClient(create_app())
    assert client.get("/api/me/preferences", headers=bearer()).status_code == 404
    put_status = client.put("/api/me/preferences", headers=bearer(), json={}).status_code
    assert put_status == 405  # como cualquier otra ruta


def test_accounts_need_a_project(monkeypatch):
    assert accounts_from_env({}) is None
    assert accounts_from_env({"FIREBASE_PROJECT_ID": "  "}) is None


def test_the_site_still_serves_pages_with_accounts_on(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/otra-cosa", headers=bearer()).status_code == 404


def test_no_token_or_uid_reaches_the_logs(client, caplog):
    with caplog.at_level(logging.DEBUG):
        put(client, {"muted": True})
        client.get("/api/me/preferences", headers=bearer("malo"))
    assert "p1" not in caplog.text and "uid1" not in caplog.text


def test_clean_preferences_keeps_only_valid_values():
    assert clean_preferences({"volMetronome": 1, "muted": False}) == {
        "volMetronome": 1.0,
        "muted": False,
    }


def test_firebase_is_not_touched_until_the_first_request(monkeypatch):
    import firebase_admin

    calls = []
    monkeypatch.setattr(firebase_admin, "initialize_app", lambda *a, **k: calls.append("init"))
    monkeypatch.setattr(
        firebase_admin, "get_app", lambda *a, **k: (_ for _ in ()).throw(ValueError())
    )
    accounts = accounts_from_env({"FIREBASE_PROJECT_ID": "proyecto"})
    assert accounts is not None and calls == []  # arrancar no inicializa nada
    assert (
        accounts.verifier.verify("token") is None
    )  # sin credenciales reales, "no"; la app se pidió aquí
    assert calls == ["init"]


# --- consentimiento (C39)
def accept(client, token="p1", **changes):
    body = {"version": NOTICE_VERSION, "adult": True, **changes}
    return client.put("/api/me/consent", headers=bearer(token), json=body)


def test_nothing_is_read_or_stored_before_consenting(bare):
    client, store = bare
    assert client.get("/api/me/preferences", headers=bearer()).status_code == 403
    assert put(client, {"muted": True}).status_code == 403
    assert store.docs == {} and store.consents == {}


def test_consent_state_starts_empty_and_reading_it_stores_nothing(bare):
    client, store = bare
    response = client.get("/api/me/consent", headers=bearer())
    assert response.status_code == 200
    assert response.json() == {"current": NOTICE_VERSION, "accepted": None, "returning": False}
    assert store.consents == {}


def test_accepting_unlocks_the_preferences(bare):
    client, store = bare
    assert accept(client).json() == {
        "current": NOTICE_VERSION,
        "accepted": NOTICE_VERSION,
        "returning": True,
    }
    assert store.consents == {"uid1": NOTICE_VERSION}
    assert put(client, {"muted": True}).status_code == 200
    assert client.get("/api/me/preferences", headers=bearer()).json() == {
        "preferences": {"muted": True}
    }


def test_accepting_twice_is_harmless(bare):
    client, store = bare
    assert accept(client).status_code == 200 and accept(client).status_code == 200
    assert store.consents == {"uid1": NOTICE_VERSION}


@pytest.mark.parametrize(
    "body",
    [
        {"version": NOTICE_VERSION, "adult": False},
        {"version": NOTICE_VERSION},
        {"adult": True},
        {"version": NOTICE_VERSION, "adult": "true"},
        {"version": NOTICE_VERSION, "adult": 1},
        {"version": "2020-01-01-v1", "adult": True},
        {"version": 1, "adult": True},
        {"version": NOTICE_VERSION, "adult": True, "extra": 1},
        [],
        "texto",
    ],
)
def test_consent_needs_the_current_version_and_the_over_14_box(bare, body):
    client, store = bare
    response = client.put("/api/me/consent", headers=bearer(), json=body)
    assert response.status_code == 422 and response.content == b""
    assert store.consents == {}


def test_an_old_version_must_be_accepted_again():
    store = FakeStore({"uid1": "2025-01-01-v1"})
    client = make_client(store)
    state = client.get("/api/me/consent", headers=bearer()).json()
    assert (
        state["accepted"] is None and state["returning"] is True
    )  # reacepta: no se le pide el perfil
    assert client.get("/api/me/preferences", headers=bearer()).status_code == 403
    assert accept(client).status_code == 200
    assert client.get("/api/me/preferences", headers=bearer()).status_code == 200


def test_consent_is_per_person(bare):
    client, store = bare
    accept(client, "p1")
    assert client.get("/api/me/preferences", headers=bearer("p1")).status_code == 200
    assert client.get("/api/me/preferences", headers=bearer("p2")).status_code == 403
    assert store.consents == {"uid1": NOTICE_VERSION}


@pytest.mark.parametrize("token", ["team", "tenant-google", "malo"])
def test_the_team_and_invalid_tokens_cannot_consent(bare, token):
    client, store = bare
    assert accept(client, token).status_code == 404
    assert client.get("/api/me/consent", headers=bearer(token)).status_code == 404
    assert store.consents == {}


def test_consent_responses_are_private_and_the_body_is_bounded(bare):
    client, store = bare
    assert (
        client.get("/api/me/consent", headers=bearer()).headers["cache-control"]
        == "private, no-store"
    )
    big = json.dumps({"version": "x" * (MAX_BODY_BYTES + 10), "adult": True})
    response = client.put(
        "/api/me/consent", headers={**bearer(), "Content-Type": "application/json"}, content=big
    )
    assert response.status_code == 413 and store.consents == {}


# --- la página del aviso
def test_the_public_notice_matches_the_version_the_server_asks_for(client):
    page = client.get("/privacidad.html")
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert NOTICE_VERSION in page.text
    assert "contacto@saulapp.com" in page.text and "14 años o más" in page.text
    assert "noindex" not in page.text


@pytest.mark.parametrize(
    "path",
    ["/", "/guias.html", "/ser-guia.html", "/artistas.html", "/pedidos.html", "/mi-acordia.html"],
)
def test_every_footer_links_to_the_notice(client, path):
    assert 'href="privacidad.html"' in client.get(path).text, path


# --- la página de entrada (S101, C40)
from musicsite.app import HEADERS, LOGIN_CSP, WEB_DIR  # noqa: E402


def login_client(key="llave-publica-de-prueba"):
    return TestClient(create_app(firebase_api_key=key))


def test_login_page_is_served_hidden_and_with_the_key_injected():
    page = login_client('abc&"<x').get("/entrar.html")
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert "__API_KEY__" not in page.text
    assert 'content="abc&amp;&quot;&lt;x"' in page.text  # escapada: nunca rompe el HTML
    assert 'name="robots" content="noindex, nofollow"' in page.text


def test_without_a_key_the_page_still_loads_and_the_script_says_unavailable():
    page = login_client("").get("/entrar.html")
    assert page.status_code == 200 and 'name="firebase-api-key" content=""' in page.text


def test_only_the_login_page_gets_the_wider_security_policy():
    client = login_client()
    login = client.get("/entrar.html").headers["content-security-policy"]
    assert login == LOGIN_CSP
    for host in (
        "https://www.gstatic.com",
        "https://apis.google.com",
        "https://identitytoolkit.googleapis.com",
        "https://securetoken.googleapis.com",
    ):
        assert host in login
    assert (
        "frame-ancestors 'none'" in login
        and "base-uri 'none'" in login
        and "form-action 'none'" in login
    )
    for path in ("/", "/privacidad.html", "/guias.html", "/entrar.js"):
        policy = client.get(path).headers["content-security-policy"]
        assert policy == HEADERS["Content-Security-Policy"], path
        assert "gstatic.com/firebasejs" not in policy and "googleapis.com" not in policy.replace(
            "fonts.googleapis.com", ""
        )


def test_my_account_is_linked_from_the_menu_and_the_footer_and_the_login_page_only_from_there(
    client,
):
    pages = (
        "/",
        "/guias.html",
        "/ser-guia.html",
        "/artistas.html",
        "/pedidos.html",
        "/privacidad.html",
    )
    for path in pages:
        html = client.get(path).text
        assert 'href="mi-acordia.html">Mi cuenta</a>' in html, path
        assert 'href="/aprende/">Aprende</a>' in html, path
        assert "entrar.html" not in html, path  # a la página de entrada se llega desde «Mi cuenta»


def test_login_script_is_pinned_and_safe():
    source = (WEB_DIR / "entrar.js").read_text(encoding="utf-8")
    versions = set(re.findall(r"firebasejs/([0-9.]+)/", source))
    assert len(versions) == 1 and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", versions.pop())
    assert "latest" not in source
    assert not re.search(r"\.innerHTML\s*=|insertAdjacentHTML|document\.write|eval\(", source)
    assert (
        "signInWithRedirect" in source
        and "deleteUser" in source
        and "authDomain: location.host" in source
    )
    assert "saulapp-music" not in source  # el sitio público no nombra el proyecto interno


def test_login_is_allowed_on_the_own_domain_and_on_web_app_and_nowhere_else():
    # S113: el login solo está autorizado en acordia.io y en *.web.app.
    source = (WEB_DIR / "entrar.js").read_text(encoding="utf-8")
    assert '.endsWith(".web.app")' in source and '=== "acordia.io"' in source
    assert "www.acordia.io" not in source  # www redirige al raíz antes del login
    assert 'includes("acordia.io")' not in source  # nada de coincidencias parciales
    page = (WEB_DIR / "entrar.html").read_text(encoding="utf-8")
    assert "acordia.io" in page and "web.app" not in page


def test_login_script_is_served_as_javascript():
    response = login_client().get("/entrar.js")
    assert response.status_code == 200 and response.headers["content-type"].startswith(
        "text/javascript"
    )


# --- exportar y borrar (S102)
def test_export_gives_everything_stored_plus_what_firebase_knows(client, store):
    put(client, {"muted": True})
    response = client.get("/api/me/export", headers=bearer())
    assert response.status_code == 200
    body = response.json()
    assert body["stored"]["preferences"] == {"muted": True}
    assert body["stored"]["consent"]["version"] == NOTICE_VERSION
    assert body["firebaseAuthentication"] == {
        "provider": "google.com",
        "email": "persona.sintetica@example.test",
        "name": "Persona Sintética",
    }
    assert set(body) == {"generatedAt", "stored", "firebaseAuthentication", "note"}


def test_export_is_a_private_download(client):
    headers = client.get("/api/me/export", headers=bearer()).headers
    assert headers["cache-control"] == "private, no-store"
    assert headers["vary"] == "Authorization"
    assert headers["content-disposition"] == 'attachment; filename="acordia-mis-datos.json"'


def test_export_works_without_ever_consenting_and_stores_nothing(bare):
    client, store = bare
    response = client.get("/api/me/export", headers=bearer())
    assert response.status_code == 200
    assert response.json()["stored"] == {
        "consent": None,
        "preferences": {},
        "progress": {},
        "profile": {},
        "continue": {},
        "favorites": [],
        "repertoires": {},
    }
    assert store.docs == {} and store.consents == {}


def test_export_never_includes_the_token_or_anyone_elses_data(client, store):
    put(client, {"muted": True}, token="p2")
    text = client.get("/api/me/export", headers=bearer("p1")).text
    assert "p1" not in json.loads(text)["note"] and '"muted": true' not in text.lower()
    assert "uid2" not in text


def test_delete_removes_the_document_and_the_consent(client, store):
    put(client, {"muted": True})
    assert client.delete("/api/me", headers=bearer()).status_code == 204
    assert "uid1" not in store.docs and "uid1" not in store.consents
    assert client.get("/api/me/consent", headers=bearer()).json()["accepted"] is None
    assert client.get("/api/me/preferences", headers=bearer()).status_code == 403


def test_delete_is_idempotent_and_needs_no_consent(bare):
    client, _ = bare
    assert client.delete("/api/me", headers=bearer()).status_code == 204
    assert client.delete("/api/me", headers=bearer()).status_code == 204


def test_delete_only_touches_the_callers_data(client, store):
    put(client, {"muted": True}, token="p2")
    client.delete("/api/me", headers=bearer("p1"))
    assert store.docs.get("uid2") == {"muted": True} and "uid2" in store.consents


@pytest.mark.parametrize("token", ["malo", "team", "tenant-google"])
def test_export_and_delete_are_404_without_a_public_session(client, store, token):
    headers = bearer(token)
    assert client.get("/api/me/export", headers=headers).status_code == 404
    assert client.delete("/api/me", headers=headers).status_code == 404
    assert "uid1" in store.consents  # nadie borró nada


def test_export_and_delete_without_authorization_are_404(client):
    assert client.get("/api/me/export").status_code == 404
    assert client.delete("/api/me").status_code == 404


def test_export_and_delete_share_the_rate_limit(client):
    for _ in range(5):
        client.get("/api/me/export", headers=bearer())
    assert client.get("/api/me/export", headers=bearer()).status_code == 429
    assert client.delete("/api/me", headers=bearer()).status_code == 429


def test_identity_keeps_only_known_short_text_fields():
    claims = {
        "uid": "uid1",
        "email": "a@example.test",
        "name": "x" * 1000,
        "picture": 5,  # no es texto: se ignora
        "phone_number": "+000",  # no se pide: no sale
        "firebase": {"sign_in_provider": "facebook.com"},
    }
    found = identity_from_claims(claims)
    assert found["provider"] == "facebook.com" and found["email"] == "a@example.test"
    assert len(found["name"]) == 300 and "picture" not in found and "phone_number" not in found


def test_identity_is_none_for_the_team():
    assert identity_from_claims(TEAM) is None and identity_from_claims(TENANT_GOOGLE) is None


class FakeSnapshot:
    def __init__(self, data):
        self.exists = data is not None
        self._data = data

    def to_dict(self):
        return self._data


class FakeFirestore:
    """Una colección `users` en memoria, con la misma forma que el cliente real."""

    def __init__(self, docs):
        self.docs, self.deleted = docs, []

    def collection(self, name):
        assert name == "users"
        return self

    def document(self, uid):
        self.uid = uid
        return self

    def get(self):
        return FakeSnapshot(self.docs.get(self.uid))

    def delete(self):
        self.deleted.append(self.uid)
        self.docs.pop(self.uid, None)

    def set(self, data, merge=False):
        from google.cloud.firestore import DELETE_FIELD

        def deep(into, new):
            for key, value in new.items():
                if value is DELETE_FIELD:
                    into.pop(key, None)
                elif isinstance(value, dict) and isinstance(into.get(key), dict):
                    deep(into[key], value)
                else:
                    into[key] = value

        doc = self.docs.setdefault(self.uid, {})
        if isinstance(merge, list):  # merge=["campo"]: esos campos se reemplazan enteros
            for field in merge:
                doc[field] = data[field]
        else:
            deep(doc, data)


def firestore_store(docs):
    from musicsite.accounts import FirestoreUserStore

    store = FirestoreUserStore(app=None)
    store._db = FakeFirestore(docs)
    return store, None


def test_firestore_export_reads_the_document_and_makes_the_time_text():
    from datetime import UTC, datetime

    when = datetime(2026, 11, 23, 7, 0, tzinfo=UTC)
    store, _ = firestore_store(
        {
            "u": {
                "consent": {"version": NOTICE_VERSION, "adult": True, "at": when},
                "preferences": {"muted": True},
                "updatedAt": when,
            }
        }
    )
    assert store.export("u") == {
        "consent": {"version": NOTICE_VERSION, "adult": True, "at": "2026-11-23T07:00:00+00:00"},
        "preferences": {"muted": True},
        "progress": {},
        "profile": {},
        "continue": {},
        "favorites": [],
        "repertoires": {},
    }


def test_firestore_export_of_nobody_is_empty_and_creates_nothing():
    store, _ = firestore_store({})
    assert store.export("nadie") == {
        "consent": None,
        "preferences": {},
        "progress": {},
        "profile": {},
        "continue": {},
        "favorites": [],
        "repertoires": {},
    }
    assert store._db.docs == {}


def test_firestore_delete_removes_the_document_and_repeating_is_harmless():
    store, _ = firestore_store({"u": {"preferences": {}}})
    store.delete("u")
    store.delete("u")
    assert store._db.docs == {} and store._db.deleted == ["u", "u"]


def test_the_consent_step_offers_the_optional_profile_for_a_first_account():
    page = (WEB_DIR / "entrar.html").read_text()
    for element in ("c-perfil", "c-nombre", "c-instrumento", "c-nivel"):
        assert f'id="{element}"' in page
    # Oculto hasta saber si es la primera vez.
    assert 'id="c-perfil" class="ac-login-profile" hidden' in page


def test_the_login_page_is_only_a_login_and_sends_a_signed_in_person_to_my_account():
    page = (WEB_DIR / "entrar.html").read_text()
    script = (WEB_DIR / "entrar.js").read_text()
    for element in ("paso-listo", "descargar", "borrar", "prefs", "guardar", "salir"):
        assert f'id="{element}"' not in page  # los datos y la cuenta viven en «Mi cuenta»
    assert 'location.replace(returnTo() || "/mi-acordia.html")' in script


# --- avance de Aprende (S103, C44)
def result(path="basico", lesson="do-es-c", points=80, stars=2):
    return {"path": path, "lesson": lesson, "points": points, "stars": stars}


def post_result(client, token="p1", **changes):
    return client.put("/api/me/progress", headers=bearer(token), json={**result(), **changes})


def test_progress_needs_consent_like_everything_else(bare):
    client, store = bare
    assert client.get("/api/me/progress", headers=bearer()).status_code == 403
    assert post_result(client).status_code == 403
    assert store.progress == {}


def test_a_new_lesson_is_stored_and_read_back(client):
    assert client.get("/api/me/progress", headers=bearer()).json() == {"progress": {}}
    response = post_result(client)
    assert response.status_code == 200
    assert response.json() == {
        "path": "basico",
        "lesson": "do-es-c",
        "points": 80,
        "stars": 2,
        "plays": 1,
    }
    assert client.get("/api/me/progress", headers=bearer()).json() == {
        "progress": {"basico": {"do-es-c": {"points": 80, "stars": 2, "plays": 1}}}
    }


def test_only_the_best_result_is_kept_and_plays_are_counted(client):
    post_result(client, points=80, stars=2)
    worse = post_result(client, points=40, stars=1).json()
    better = post_result(client, points=100, stars=3).json()
    assert (worse["points"], worse["stars"], worse["plays"]) == (80, 2, 2)
    assert (better["points"], better["stars"], better["plays"]) == (100, 3, 3)


def test_progress_is_per_person_and_per_lesson(client):
    post_result(client, token="p1")
    post_result(client, token="p2", lesson="pulso", points=10, stars=0)
    assert set(
        client.get("/api/me/progress", headers=bearer("p1")).json()["progress"]["basico"]
    ) == {"do-es-c"}
    assert set(
        client.get("/api/me/progress", headers=bearer("p2")).json()["progress"]["basico"]
    ) == {"pulso"}


@pytest.mark.parametrize(
    "changes",
    [
        {"points": 101},
        {"points": -1},
        {"points": 80.5},
        {"points": True},
        {"points": "80"},
        {"stars": 4},
        {"stars": -1},
        {"path": "Basico"},
        {"path": "../x"},
        {"lesson": ""},
        {"lesson": "a" * 40},
        {"lesson": ["x"]},
    ],
)
def test_invalid_results_are_422_and_store_nothing(client, store, changes):
    assert post_result(client, **changes).status_code == 422
    assert store.progress == {}


@pytest.mark.parametrize("body", [{}, {"path": "basico"}, {**result(), "extra": 1}, [1], "x"])
def test_malformed_progress_bodies_are_422(client, body):
    response = client.put("/api/me/progress", headers=bearer(), json=body)
    assert response.status_code == 422


@pytest.mark.parametrize("token", ["malo", "team", "tenant-google"])
def test_progress_is_404_without_a_public_session(client, token):
    assert client.get("/api/me/progress", headers=bearer(token)).status_code == 404
    assert post_result(client, token=token).status_code == 404


def test_progress_responses_are_private(client):
    headers = post_result(client).headers
    assert headers["cache-control"] == "private, no-store"


def test_export_and_delete_cover_the_progress(client, store):
    post_result(client)
    assert client.get("/api/me/export", headers=bearer()).json()["stored"]["progress"] == {
        "basico": {"do-es-c": {"points": 80, "stars": 2, "plays": 1}}
    }
    client.delete("/api/me", headers=bearer())
    assert "uid1" not in store.progress


def test_progress_has_caps_so_a_document_cannot_grow_forever():
    full = {f"ruta{i}": {"a": {"points": 1, "stars": 0, "plays": 1}} for i in range(20)}
    assert merge_result(full, "otra", "a", 1, 0) is None  # una ruta de más
    assert (
        merge_result(full, "ruta0", "b", 1, 0) is not None
    )  # una lección nueva en una ruta existente
    lots = {"basico": {f"l{i}": {"points": 1, "stars": 0, "plays": 1} for i in range(200)}}
    assert merge_result(lots, "basico", "nueva", 1, 0) is None
    assert (
        merge_result(lots, "basico", "l0", 5, 0)["plays"] == 2
    )  # mejorar una existente siempre se puede


def test_clean_progress_ignores_anything_that_is_not_the_expected_shape():
    raw = {
        "basico": {
            "bien": {"points": 10, "stars": 1, "plays": 2},
            "mal": {"points": 999, "stars": 1, "plays": 2},
            "peor": "x",
            "Mayuscula": {"points": 1, "stars": 1, "plays": 1},
        },
        "Otra": {"a": {"points": 1, "stars": 1, "plays": 1}},
        "texto": "x",
    }
    assert clean_progress(raw) == {"basico": {"bien": {"points": 10, "stars": 1, "plays": 2}}}
    assert clean_progress(None) == {} and clean_progress([1]) == {}


def test_firestore_progress_is_merged_not_replaced():
    store, _ = firestore_store({"u": {"preferences": {"muted": True}}})
    store.put_result("u", "basico", "do-es-c", 80, 2)
    store.put_result("u", "basico", "pulso", 50, 1)
    store.put_result("u", "basico", "do-es-c", 60, 1)  # peor: se conserva el mejor
    assert store.get_progress("u")["basico"] == {
        "do-es-c": {"points": 80, "stars": 2, "plays": 2},
        "pulso": {"points": 50, "stars": 1, "plays": 1},
    }
    assert store._db.docs["u"]["preferences"] == {"muted": True}  # no pisa lo demás


def _return_pattern():
    """El regex de `returnTo` de entrar.js, tomado del propio archivo: se prueba lo que corre."""
    source = (WEB_DIR / "entrar.js").read_text(encoding="utf-8")
    assert "volver" in source and "location.replace(returnTo() ||" in source
    found = re.search(r"const allowed = /(.+)/;", source)
    assert found, "no se encontró el regex de retorno"
    return re.compile(found.group(1)), 'target.includes("..")' in source


@pytest.mark.parametrize(
    "target",
    [
        "/aprende/",
        "/aprende/#/basico/pulso",
        "/mi-acordia.html",
        "/repertorio.html",
        "/repertorio.html?id=abc123",
    ],
)
def test_the_login_page_returns_to_our_own_pages(target):
    pattern, _ = _return_pattern()
    assert pattern.fullmatch(target)


@pytest.mark.parametrize(
    "target",
    [
        "",
        "//evil.example",
        "https://evil.example",
        "javascript:alert(1)",
        "/aprendex/",
        "/mi-acordia.html.evil",
        "/mi-acordia.htmlx",
        "/mi-acordia.html?x=1",
        "/repertorio.html?id=<script>",
        "/repertorio.html/../x",
        "/entrar.html",
        "\\evil.example",
    ],
)
def test_the_login_page_never_returns_anywhere_else(target):
    pattern, rejects_parent = _return_pattern()
    assert rejects_parent
    assert not pattern.fullmatch(target)


# --- perfil y «continuar» (S104, C30)
def put_profile(client, body, token="p1"):
    return client.put("/api/me/profile", headers=bearer(token), json=body)


def put_continue(client, body, token="p1"):
    return client.put("/api/me/continue", headers=bearer(token), json=body)


def test_profile_needs_consent_and_starts_empty(bare):
    client, store = bare
    assert client.get("/api/me/profile", headers=bearer()).status_code == 403
    assert put_profile(client, {"name": "Ana"}).status_code == 403
    assert store.profiles == {}


def test_profile_is_saved_read_back_and_replaced_whole(client, store):
    assert client.get("/api/me/profile", headers=bearer()).json() == {"profile": {}}
    full = {"name": "  Ana   María ", "instrument": "guitarra", "level": "medio"}
    assert put_profile(client, full).json() == {
        "profile": {"name": "Ana María", "instrument": "guitarra", "level": "medio"}
    }
    # un PUT con menos campos borra los que faltan: reemplaza, no mezcla
    assert put_profile(client, {"level": "inicial"}).json() == {"profile": {"level": "inicial"}}
    assert client.get("/api/me/profile", headers=bearer()).json() == {
        "profile": {"level": "inicial"}
    }
    assert put_profile(client, {}).json() == {"profile": {}}


def test_profile_empty_values_clear_the_field(client):
    put_profile(client, {"name": "Ana", "instrument": "bajo"})
    assert put_profile(client, {"name": "   ", "instrument": "", "level": None}).json() == {
        "profile": {}
    }


@pytest.mark.parametrize(
    "body",
    [
        {"name": "x" * 41},
        {"name": "<script>alert(1)</script>"},
        {"name": "Ana\u0000"},
        {"name": "Ana\nPérez" + "\x07"},
        {"name": 5},
        {"name": ["Ana"]},
        {"instrument": "tuba"},
        {"instrument": ["guitarra"]},
        {"level": "experto"},
        {"level": 1},
        {"email": "a@example.test"},
        {"name": "Ana", "foto": "https://example.test/x.png"},
        [1],
        "x",
    ],
)
def test_invalid_profiles_are_422_and_store_nothing(client, store, body):
    assert put_profile(client, body).status_code == 422
    assert store.profiles == {}


def test_profile_names_keep_accents_and_ordinary_punctuation():
    assert clean_profile({"name": "María-José O'Brien Ñandú"}) == {
        "name": "María-José O'Brien Ñandú"
    }


def test_profile_is_private_per_person_and_404_without_a_public_session(client, store):
    put_profile(client, {"name": "Ana"}, token="p1")
    assert client.get("/api/me/profile", headers=bearer("p2")).json() == {"profile": {}}
    for token in ("malo", "team", "tenant-google"):
        assert client.get("/api/me/profile", headers=bearer(token)).status_code == 404
        assert put_profile(client, {"name": "X"}, token=token).status_code == 404
    assert (
        client.get("/api/me/profile", headers=bearer("p1")).headers["cache-control"]
        == "private, no-store"
    )


def test_continue_keeps_the_last_lesson_and_the_last_song_apart(client):
    assert client.get("/api/me/continue", headers=bearer()).json() == {"continue": {}}
    assert put_continue(client, {"song": "camara-lenta"}).json() == {
        "continue": {"song": "camara-lenta"}
    }
    both = put_continue(client, {"lesson": {"path": "basico", "lesson": "pulso"}}).json()
    assert both == {
        "continue": {"song": "camara-lenta", "lesson": {"path": "basico", "lesson": "pulso"}}
    }
    again = put_continue(client, {"song": "2022"}).json()[
        "continue"
    ]  # cambia el tema y conserva la lección
    assert again == {"song": "2022", "lesson": {"path": "basico", "lesson": "pulso"}}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"song": "a", "lesson": {"path": "basico", "lesson": "pulso"}},
        {"song": "Camara Lenta"},
        {"song": "../x"},
        {"song": "a" * 61},
        {"song": 7},
        {"lesson": {"path": "basico"}},
        {"lesson": {"path": "basico", "lesson": "Pulso"}},
        {"lesson": {"path": "basico", "lesson": "pulso", "extra": 1}},
        {"lesson": "pulso"},
        {"otro": "x"},
        [1],
    ],
)
def test_invalid_continue_bodies_are_422(client, store, body):
    assert put_continue(client, body).status_code == 422
    assert store.continues == {}


def test_continue_needs_consent_and_a_public_session(bare):
    client, store = bare
    assert client.get("/api/me/continue", headers=bearer()).status_code == 403
    assert put_continue(client, {"song": "a"}).status_code == 403
    assert put_continue(client, {"song": "a"}, token="team").status_code == 404
    assert store.continues == {}


def test_export_and_delete_cover_the_profile_and_the_last_seen(client, store):
    put_profile(client, {"name": "Ana", "level": "medio"})
    put_continue(client, {"song": "camara-lenta"})
    stored = client.get("/api/me/export", headers=bearer()).json()["stored"]
    assert stored["profile"] == {"name": "Ana", "level": "medio"}
    assert stored["continue"] == {"song": "camara-lenta"}
    client.delete("/api/me", headers=bearer())
    assert "uid1" not in store.profiles and "uid1" not in store.continues


def test_clean_continue_returns_only_the_shape_it_expects():
    assert clean_continue({"song": "a-b"}) == {"song": "a-b"}


def test_firestore_profile_is_replaced_and_continue_is_merged():
    store, _ = firestore_store({"u": {"preferences": {"muted": True}}})
    store.put_profile("u", {"name": "Ana", "level": "medio"})
    store.put_profile("u", {"instrument": "bajo"})  # reemplaza: el nombre y el nivel ya no están
    assert store.get_profile("u") == {"instrument": "bajo"}
    store.put_continue("u", {"song": "a"})
    store.put_continue("u", {"lesson": {"path": "basico", "lesson": "pulso"}})
    assert store.get_continue("u") == {"song": "a", "lesson": {"path": "basico", "lesson": "pulso"}}
    assert store._db.docs["u"]["preferences"] == {"muted": True}  # no pisa lo demás


def test_firestore_ignores_a_corrupted_profile_or_continue():
    store, _ = firestore_store(
        {"u": {"profile": {"name": 5, "x": 1}, "continue": {"song": "MAL", "lesson": 3}}}
    )
    assert store.get_profile("u") == {}
    assert store.get_continue("u") == {}


# --- Mi cuenta, redirecciones de «Aprender» y ajustes de las páginas de canción (S104, C28, C45)
@pytest.mark.parametrize(
    "path",
    [
        "/aprender.html",
        "/aprender.css",
        "/aprender-basicos-clave-americana.html",
        "/aprender-acordes-intervalos.html",
    ],
)
def test_the_retired_learn_pages_redirect_permanently_to_aprende(client, path):
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 301 and response.headers["location"] == "/aprende/"


def test_other_pages_that_look_alike_are_not_redirected(client):
    for path in ("/aprender", "/aprendex.html", "/aprender-.js", "/aprende.html"):
        assert client.get(path, follow_redirects=False).status_code == 404, path


def test_my_account_page_gets_the_key_the_wider_policy_and_stays_out_of_the_index(client):
    from musicsite.app import create_app

    page = TestClient(create_app(firebase_api_key="clave-de-prueba")).get("/mi-acordia.html")
    assert page.status_code == 200 and 'content="clave-de-prueba"' in page.text
    assert (
        "__API_KEY__" not in page.text and 'name="robots" content="noindex, nofollow"' in page.text
    )
    assert page.headers["content-security-policy"] == LOGIN_CSP
    assert client.get("/privacidad.html").headers["content-security-policy"] != LOGIN_CSP


def test_my_account_script_is_pinned_safe_and_deletes_our_data_before_the_account():
    source = (WEB_DIR / "mi-acordia.js").read_text(encoding="utf-8")
    versions = set(re.findall(r"firebasejs/([0-9.]+)/", source))
    assert len(versions) == 1 and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", versions.pop())
    assert not re.search(r"\.innerHTML\s*=|insertAdjacentHTML|document\.write|eval\(", source)
    delete_call = source.index('api("", { method: "DELETE" })')
    assert delete_call < source.index("deleteUser(auth.currentUser)", delete_call)
    assert "requires-recent-login" in source


def test_song_pages_get_the_account_links_and_the_theory_button_goes_to_aprende():
    from musicsite.songpage import decorate

    page = (
        '<ul><li class="nav-item">'
        '<a class="nav-link" href="pedidos.html">Pide una canción</a></li></ul>'
        '<nav>\n          <a href="guias.html">Guías</a>'
        '<a href="pedidos.html">Pide una canción</a>\n        </nav>'
        '<a class="btn" href="aprender.html" target="_blank">Aprende teoría</a>'
    ).encode()
    out = decorate(page).decode()
    assert out.count('href="mi-acordia.html">Mi cuenta</a>') == 2  # menú y pie
    assert out.count('href="/aprende/">Aprende</a>') == 2
    assert 'href="aprender.html"' not in out and 'class="btn" href="/aprende/"' in out
    assert (
        decorate(b"<p>otra cosa</p>") == b"<p>otra cosa</p>"
    )  # sin esos fragmentos, no cambia nada


def test_a_served_song_page_has_the_links(client):
    page = client.get("/cancion-camara-lenta.html").text
    assert 'href="mi-acordia.html">Mi cuenta</a>' in page and "aprender.html" not in page


# --- favoritos y repertorios (S105, C30)
SONG_A, SONG_B, SONG_C = "camara-lenta", "2022", "moizefala"  # temas de respaldo, publicados


@pytest.fixture
def big(store):
    """Un cliente con un límite de frecuencia amplio: estas pruebas hacen muchas llamadas."""
    accounts = Accounts(FakeVerifier(), store, RateLimiter(limit=1000, window=60))
    return TestClient(create_app(accounts=accounts))


def fav(big, song, favorite=True, token="p1"):
    return big.put(
        "/api/me/favorites", headers=bearer(token), json={"song": song, "favorite": favorite}
    )


def rep(big, rid, name="Para ensayar", songs=(SONG_A,), token="p1"):
    return big.put(
        f"/api/me/repertoires/{rid}",
        headers=bearer(token),
        json={"name": name, "songs": list(songs)},
    )


def test_favorites_need_consent_and_start_empty(bare):
    big, store = bare
    assert big.get("/api/me/favorites", headers=bearer()).status_code == 403
    assert fav(big, SONG_A).status_code == 403
    assert store.favorites == {}


def test_favorites_are_marked_listed_sorted_and_unmarked(big):
    assert big.get("/api/me/favorites", headers=bearer()).json() == {"favorites": []}
    assert fav(big, SONG_C).json() == {"favorites": [SONG_C]}
    assert fav(big, SONG_A).json() == {"favorites": [SONG_A, SONG_C]}
    assert fav(big, SONG_A).json() == {"favorites": [SONG_A, SONG_C]}  # repetir no duplica
    assert fav(big, SONG_C, favorite=False).json() == {"favorites": [SONG_A]}
    assert fav(big, SONG_C, favorite=False).json() == {"favorites": [SONG_A]}  # ni falla
    assert big.get("/api/me/favorites", headers=bearer()).json() == {"favorites": [SONG_A]}


def test_only_published_songs_can_be_marked_but_any_can_be_unmarked(big, store):
    assert fav(big, "no-existe").status_code == 422
    store.favorites["uid1"] = {"ya-retirado"}
    assert fav(big, "ya-retirado", favorite=False).json() == {"favorites": []}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"song": SONG_A},
        {"favorite": True},
        {"song": SONG_A, "favorite": "si"},
        {"song": SONG_A, "favorite": 1},
        {"song": "Camara Lenta", "favorite": True},
        {"song": "../x", "favorite": True},
        {"song": ["a"], "favorite": True},
        {"song": SONG_A, "favorite": True, "extra": 1},
        [1],
    ],
)
def test_invalid_favorite_bodies_are_422(big, store, body):
    assert big.put("/api/me/favorites", headers=bearer(), json=body).status_code == 422
    assert store.favorites == {}


def test_the_favorites_cap_is_422_and_unmarking_still_works():
    store, _ = firestore_store({"u": {}})
    for i in range(MAX_FAVORITES):
        assert store.put_favorite("u", f"tema-{i}", True) is not None
    assert store.put_favorite("u", "uno-mas", True) is None  # pasa el tope
    assert (
        len(store.put_favorite("u", "tema-0", True)) == MAX_FAVORITES
    )  # uno que ya estaba, no cuenta
    assert len(store.put_favorite("u", "tema-0", False)) == MAX_FAVORITES - 1
    assert store.put_favorite("u", "uno-mas", True) is not None  # ahora cabe


def test_favorites_are_per_person_and_404_without_a_public_session(big):
    fav(big, SONG_A, token="p1")
    assert big.get("/api/me/favorites", headers=bearer("p2")).json() == {"favorites": []}
    for token in ("malo", "team", "tenant-google"):
        assert big.get("/api/me/favorites", headers=bearer(token)).status_code == 404
        assert fav(big, SONG_A, token=token).status_code == 404


def test_a_repertoire_is_created_listed_replaced_and_deleted(big):
    assert big.get("/api/me/repertoires", headers=bearer()).json() == {"repertoires": []}
    made = rep(big, "abc123", "  Para   ensayar ", [SONG_B, SONG_A])
    assert made.json() == {
        "id": "abc123",
        "name": "Para ensayar",
        "songs": [SONG_B, SONG_A],
    }  # el orden se conserva
    rep(big, "zzz999", "Algo")
    names = [
        r["name"] for r in big.get("/api/me/repertoires", headers=bearer()).json()["repertoires"]
    ]
    assert names == ["Algo", "Para ensayar"]  # por nombre
    assert rep(big, "abc123", "Para ensayar", [SONG_A]).json()["songs"] == [SONG_A]  # reemplaza
    assert big.delete("/api/me/repertoires/abc123", headers=bearer()).status_code == 204
    assert (
        big.delete("/api/me/repertoires/abc123", headers=bearer()).status_code == 204
    )  # idempotente
    assert [
        r["id"] for r in big.get("/api/me/repertoires", headers=bearer()).json()["repertoires"]
    ] == ["zzz999"]


@pytest.mark.parametrize("rid", ["ABC123", "abc", "a" * 21, "abc 123", "../abc123", "abc_123"])
def test_repertoire_ids_are_validated(big, store, rid):
    # 404/405 cuando la ruta normalizada ni existe para ese método; 422 cuando llega y se valida
    assert rep(big, rid).status_code in (404, 405, 422)
    assert big.delete(f"/api/me/repertoires/{rid}", headers=bearer()).status_code in (404, 405, 422)
    assert store.repertoires == {}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": "A"},
        {"songs": []},
        {"name": "", "songs": []},
        {"name": "   ", "songs": []},
        {"name": "x" * 61, "songs": []},
        {"name": "<b>hola</b>", "songs": []},
        {"name": 5, "songs": []},
        {"name": "Ok", "songs": "camara-lenta"},
        {"name": "Ok", "songs": [SONG_A, SONG_A]},
        {"name": "Ok", "songs": ["no-existe"]},
        {"name": "Ok", "songs": ["Mal Slug"]},
        {"name": "Ok", "songs": [1]},
        {"name": "Ok", "songs": [], "extra": 1},
        [1],
    ],
)
def test_invalid_repertoires_are_422_and_store_nothing(big, store, body):
    response = big.put("/api/me/repertoires/abc123", headers=bearer(), json=body)
    assert response.status_code == 422
    assert store.repertoires == {}


def test_a_repertoire_keeps_songs_that_are_no_longer_published_but_cannot_add_new_unknown_ones(
    big, store
):
    store.repertoires["uid1"] = {"abc123": {"name": "Viejo", "songs": ["ya-retirado", SONG_A]}}
    assert rep(big, "abc123", "Viejo", [SONG_A, "ya-retirado"]).status_code == 200  # reordenar
    assert rep(big, "abc123", "Viejo", [SONG_A, "ya-retirado", "inventado"]).status_code == 422


def test_a_repertoire_can_be_big_but_not_over_the_cap_or_the_body_limit(big, store):
    many = [f"t{i}" for i in range(MAX_SONGS_PER_REPERTOIRE + 1)]
    assert (
        big.put(
            "/api/me/repertoires/abc123", headers=bearer(), json={"name": "x", "songs": many}
        ).status_code
        == 422
    )
    huge = {"name": "x", "songs": ["a" * 59] * 400}
    assert big.put("/api/me/repertoires/abc123", headers=bearer(), json=huge).status_code == 413
    assert store.repertoires == {}


def test_the_repertoires_cap_is_422_but_replacing_one_still_works(big, store):
    for i in range(MAX_REPERTOIRES):
        assert rep(big, f"rep{i:03d}x", f"R{i}").status_code == 200
    assert rep(big, "otronuevo", "Uno más").status_code == 422
    assert rep(big, "rep000x"[:7] + "", "Renombrado").status_code in (200, 422)
    assert rep(big, "rep001x", "Renombrado").status_code == 200
    assert big.delete("/api/me/repertoires/rep001x", headers=bearer()).status_code == 204
    assert rep(big, "otronuevo", "Ahora sí").status_code == 200


def test_repertoires_are_private_and_404_without_a_public_session(big):
    rep(big, "abc123", token="p1")
    assert big.get("/api/me/repertoires", headers=bearer("p2")).json() == {"repertoires": []}
    assert big.delete("/api/me/repertoires/abc123", headers=bearer("p2")).status_code == 204
    assert (
        len(big.get("/api/me/repertoires", headers=bearer("p1")).json()["repertoires"]) == 1
    )  # no lo borró
    for token in ("malo", "team", "tenant-google"):
        assert big.get("/api/me/repertoires", headers=bearer(token)).status_code == 404
        assert rep(big, "abc123", token=token).status_code == 404


def test_export_and_delete_cover_favorites_and_repertoires(big, store):
    fav(big, SONG_A)
    rep(big, "abc123", "Mi lista", [SONG_A])
    stored = big.get("/api/me/export", headers=bearer()).json()["stored"]
    assert stored["favorites"] == [SONG_A]
    assert stored["repertoires"] == {"abc123": {"name": "Mi lista", "songs": [SONG_A]}}
    big.delete("/api/me", headers=bearer())
    assert "uid1" not in store.favorites and "uid1" not in store.repertoires


def test_clean_functions_for_favorites_and_repertoires():
    assert clean_favorite({"song": "a-b", "favorite": False}) == ("a-b", False)
    assert clean_repertoire({"name": " X  Y ", "songs": ["a", "b"]}) == {
        "name": "X Y",
        "songs": ["a", "b"],
    }


def test_firestore_favorites_and_repertoires_are_merged_and_deleted_without_touching_the_rest():
    store, _ = firestore_store({"u": {"preferences": {"muted": True}}})
    store.put_favorite("u", "a", True)
    store.put_favorite("u", "b", True)
    store.put_favorite("u", "a", False)
    assert store.get_favorites("u") == ["b"]
    assert store.put_repertoire("u", "abc123", {"name": "Uno", "songs": ["x", "y"]})
    assert store.put_repertoire(
        "u", "abc123", {"name": "Uno", "songs": ["y"]}
    )  # reemplaza la lista
    assert store.get_repertoires("u") == {"abc123": {"name": "Uno", "songs": ["y"]}}
    store.delete_repertoire("u", "abc123")
    assert store.get_repertoires("u") == {}
    assert store._db.docs["u"]["preferences"] == {"muted": True}


def test_firestore_ignores_damaged_favorites_and_repertoires():
    store, _ = firestore_store(
        {
            "u": {
                "favorites": {"ok": True, "Mal": True, "x": False, "y": "si"},
                "repertoires": {
                    "abc123": {"name": "Bien", "songs": ["a"]},
                    "ABC": {"name": "mal id", "songs": []},
                    "def456": {"name": 5, "songs": []},
                    "ghi789": "no es un mapa",
                },
            }
        }
    )
    assert store.get_favorites("u") == ["ok"]
    assert store.get_repertoires("u") == {"abc123": {"name": "Bien", "songs": ["a"]}}


# --- tema dentro de un iframe, cuenta en los temas y listado público (S105, C31)
def test_embed_mode_hides_the_site_chrome_and_allows_only_our_own_frames(client):
    from musicsite.app import EMBED_CSP

    page = client.get("/cancion-camara-lenta.html?embed=1")
    assert page.status_code == 200
    assert ".navbar,.ac-footer" in page.text and "cuenta-tema.js" not in page.text
    assert page.headers["content-security-policy"] == EMBED_CSP
    assert "frame-ancestors 'self'" in EMBED_CSP and "frame-ancestors 'none'" not in EMBED_CSP
    assert (
        "frame-ancestors 'none'"
        in client.get("/cancion-camara-lenta.html").headers["content-security-policy"]
    )


def test_only_the_exact_embed_value_enables_embed_mode(client):
    for query in ("?embed=0", "?embed=true", "?embed=", "?embed=1x"):
        page = client.get("/cancion-camara-lenta.html" + query)
        assert ".navbar,.ac-footer" not in page.text, query
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"], query


def test_song_pages_get_the_account_script_and_policy_only_when_accounts_are_on():
    from musicsite.app import LOGIN_CSP, create_app

    on = TestClient(create_app(firebase_api_key="clave-de-prueba")).get(
        "/cancion-camara-lenta.html"
    )
    assert (
        'src="cuenta-tema.js"' in on.text
        and 'name="firebase-api-key" content="clave-de-prueba"' in on.text
    )
    assert on.headers["content-security-policy"] == LOGIN_CSP
    off = TestClient(create_app()).get("/cancion-camara-lenta.html")
    assert "cuenta-tema.js" not in off.text and "firebase-api-key" not in off.text
    assert off.headers["content-security-policy"] == HEADERS["Content-Security-Policy"]


def test_the_key_is_escaped_in_song_pages():
    from musicsite.songpage import decorate

    out = decorate(
        b"<html><head></head><body></body></html>", api_key='"><script>x</script>'
    ).decode()
    assert "<script>x</script>" not in out and "&quot;&gt;&lt;script&gt;" in out


def test_the_public_song_listing_has_titles_and_artists_and_nothing_else(client):
    response = client.get("/songs.json")
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "public, max-age=300"
    )
    songs = response.json()
    by_slug = {s["slug"]: s for s in songs}
    assert by_slug["camara-lenta"] == {
        "slug": "camara-lenta",
        "title": "Cámara lenta",
        "artist": "Javiera Mena",
    }
    assert all(set(s) == {"slug", "title", "artist"} for s in songs)
    assert songs == sorted(songs, key=lambda s: (s["artist"].casefold(), s["title"].casefold()))


@pytest.mark.parametrize("script", ["cuenta-tema.js", "repertorio.js"])
def test_the_new_account_scripts_are_pinned_safe_and_only_talk_to_our_api(script):
    source = (WEB_DIR / script).read_text(encoding="utf-8")
    versions = set(re.findall(r"firebasejs/([0-9.]+)", source))
    assert len(versions) == 1 and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", versions.pop())
    assert not re.search(r"\.innerHTML\s*=|insertAdjacentHTML|document\.write|eval\(", source)
    assert "latest" not in source
    # solo hablan con /api/me/*, /songs.json y las páginas del propio sitio
    assert not re.search(r"fetch\(\s*[\"'`]https?:", source)


def test_the_song_script_only_loads_firebase_when_there_is_a_session_hint():
    source = (WEB_DIR / "cuenta-tema.js").read_text(encoding="utf-8")
    gate = source.index("if (!read(HINT) || !apiKey) return;")
    assert gate < source.index("import(/* @vite-ignore */")  # la puerta va antes de cargar Firebase
    assert "acordia-prefs-aplicadas" in source  # una sola recarga por sesión: sin bucles


def test_the_repertoire_player_only_embeds_our_own_song_pages():
    lines = (WEB_DIR / "repertorio.js").read_text(encoding="utf-8").splitlines()
    code = "\n".join(
        line for line in lines if not line.lstrip().startswith("//")
    )  # sin comentarios
    assert code.count("?embed=1") == 1 and "`cancion-${songs[at]}.html?embed=1`" in code


def test_the_notice_says_song_pages_load_firebase_only_with_a_session(client):
    text = client.get("/privacidad.html").text
    assert "si no tienes sesión, las páginas de los temas no hacen ninguna llamada a Google" in text

"""Cuentas del sitio (C26, S99): tokens, preferencias y límites. Todo sintético."""

import json
import logging
import re

import pytest
from fastapi.testclient import TestClient

from musicsite.accounts import (
    MAX_BODY_BYTES,
    MAX_TRACKED_PEOPLE,
    NOTICE_VERSION,
    Accounts,
    InvalidPreferences,
    RateLimiter,
    accounts_from_env,
    clean_preferences,
    uid_from_claims,
)
from musicsite.app import create_app

PUBLIC = {"uid": "uid1", "firebase": {"sign_in_provider": "google.com"}}
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


class FakeStore:
    def __init__(self, consents=None):
        self.docs = {}
        self.consents = dict(consents or {})

    def get(self, uid):
        return dict(self.docs.get(uid, {}))

    def put(self, uid, preferences):
        self.docs[uid] = dict(preferences)

    def get_consent(self, uid):
        return self.consents.get(uid)

    def put_consent(self, uid, version):
        self.consents[uid] = version


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
    assert response.json() == {"current": NOTICE_VERSION, "accepted": None}
    assert store.consents == {}


def test_accepting_unlocks_the_preferences(bare):
    client, store = bare
    assert accept(client).json() == {"current": NOTICE_VERSION, "accepted": NOTICE_VERSION}
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
    assert client.get("/api/me/consent", headers=bearer()).json()["accepted"] is None
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
    ["/", "/guias.html", "/ser-guia.html", "/artistas.html", "/pedidos.html", "/aprender.html"],
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


def test_login_page_is_not_linked_from_the_site(client):
    for path in (
        "/",
        "/guias.html",
        "/ser-guia.html",
        "/artistas.html",
        "/pedidos.html",
        "/privacidad.html",
        "/aprender.html",
    ):
        assert "entrar.html" not in client.get(path).text, path


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


def test_login_script_is_served_as_javascript():
    response = login_client().get("/entrar.js")
    assert response.status_code == 200 and response.headers["content-type"].startswith(
        "text/javascript"
    )

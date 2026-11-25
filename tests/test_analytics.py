"""Analítica con consentimiento (S116, C51): dónde va el script y cómo cambia la CSP."""

import re

import pytest
from fastapi.testclient import TestClient

from musicsite import analytics, seo
from musicsite.app import HEADERS, create_app

TEST_HOST = "saulapp-music.web.app"
OTHER = {"host": "acordia.io"}
ON = {"host": TEST_HOST}
SNIPPET = f'<script src="/analitica.js" data-id="{analytics.MEASUREMENT_ID}"'


@pytest.fixture(scope="module")
def off() -> TestClient:
    return TestClient(create_app(analytics_hosts=()))  # sin ningún host con medición


@pytest.fixture(scope="module")
def on() -> TestClient:
    return TestClient(create_app(analytics_hosts=(TEST_HOST,)))


def song(client: TestClient) -> str:
    return client.get("/songs.json").json()[0]["slug"]


def test_production_measures_only_the_test_host_until_the_notice_is_published():
    assert analytics.ANALYTICS_HOSTS == (TEST_HOST,)
    default = TestClient(create_app())
    assert SNIPPET in default.get("/", headers=ON).text
    assert "analitica.js" not in default.get("/", headers=OTHER).text  # acordia.io: aún no


@pytest.mark.parametrize("path", ["/", "/artistas.html", "/guias.html", "/privacidad.html"])
def test_nothing_changes_when_off(off, path):
    response = off.get(path, headers=ON)
    assert SNIPPET not in response.text
    assert "googletagmanager" not in response.headers.get("content-security-policy", "")
    assert "analitica.js" not in response.text


def test_song_pages_unchanged_when_off(off):
    response = off.get(f"/cancion-{song(off)}.html", headers=ON)
    assert "analitica.js" not in response.text
    assert "googletagmanager" not in response.headers["content-security-policy"]


@pytest.mark.parametrize("path", ["/", "/artistas.html", "/guias.html", "/privacidad.html"])
def test_public_pages_get_the_script_on_the_test_host(on, path):
    response = on.get(path, headers=ON)
    assert response.text.count(SNIPPET) == 1
    assert response.text.index(SNIPPET) < response.text.index("</body>")
    csp = response.headers["content-security-policy"]
    assert "https://www.googletagmanager.com" in csp
    assert "connect-src 'self' https://*.google-analytics.com" in csp


def test_song_pages_get_the_script_and_keep_their_own_policy(on):
    response = on.get(f"/cancion-{song(on)}.html", headers=ON)
    assert response.text.count(SNIPPET) == 1
    csp = response.headers["content-security-policy"]
    assert "https://www.googletagmanager.com" in csp
    assert "frame-ancestors 'none'" in csp  # sigue sin enmarcarse


def test_other_hosts_are_not_measured(on):
    for headers in (OTHER, {"host": "musicsite-ufi63f4rva-tl.a.run.app"}):
        assert "analitica.js" not in on.get("/", headers=headers).text


def test_forwarded_host_decides(on):
    headers = {"host": "musicsite-ufi63f4rva-tl.a.run.app", "x-forwarded-host": TEST_HOST}
    assert SNIPPET in on.get("/", headers=headers).text


@pytest.mark.parametrize(
    "path",
    [
        "/entrar.html",
        "/mi-acordia.html",
        "/repertorio.html",
        "/pedidos.html",
        "/ser-guia.html",
        "/cancion.html",
    ],
)
def test_account_and_demo_pages_are_never_measured(on, path):
    response = on.get(path, headers=ON)
    assert "analitica.js" not in response.text
    assert "googletagmanager" not in response.headers.get("content-security-policy", "")


def test_embedded_song_is_never_measured(on):
    response = on.get(f"/cancion-{song(on)}.html?embed=1", headers=ON)
    assert "analitica.js" not in response.text
    assert "googletagmanager" not in response.headers["content-security-policy"]


def test_the_script_is_served_and_has_no_hardcoded_id(on):
    response = on.get("/analitica.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert "G-" not in re.sub(r"\^G-\[A-Z0-9\]\+", "", response.text)  # el ID llega por data-id


def test_policy_only_adds_what_google_needs():
    base = HEADERS["Content-Security-Policy"]
    out = analytics.csp(base)
    assert "script-src 'self' https://www.googletagmanager.com 'unsafe-inline'" in out
    assert out.count("connect-src") == 1
    assert "frame-ancestors 'none'" in out
    assert "default-src 'self'" in out


def test_policy_extends_an_existing_connect_src():
    base = "default-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self' https://x.test"
    out = analytics.csp(base)
    assert out.count("connect-src") == 1
    assert "https://*.google-analytics.com" in out
    assert "https://x.test" in out


def test_measurement_id_has_the_expected_shape():
    assert re.fullmatch(r"G-[A-Z0-9]+", analytics.MEASUREMENT_ID)
    assert seo.host_of  # la misma lectura del host que el SEO

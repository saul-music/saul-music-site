"""Google Analytics 4 con consentimiento previo (S116, C51).

El script `analitica.js` se inyecta al servir, solo en las páginas públicas y solo en los
hosts de `ANALYTICS_HOSTS` (hoy vacío en producción = apagado: el HTML y la CSP no cambian).
No carga nada de Google hasta que la persona acepta en el banner. Nunca se mide en cuenta,
`pedidos`, `ser-guia`, `cancion.html` ni `?embed=1`.
"""

from fastapi import Request

from musicsite import seo

MEASUREMENT_ID = (
    "G-5KLRKGHGTN"  # no es secreto: va en el HTML de todas formas (propiedad Acordia, infra I27)
)
CONSENT_VERSION = "analitica-2026-11-25"  # una versión nueva vuelve a pedir la decisión
# Hosts donde se mide. Se prueba primero en el de Hosting; `acordia.io` se agrega
# con el aviso de privacidad publicado.
ANALYTICS_HOSTS: tuple[str, ...] = ("saulapp-music.web.app",)

SCRIPT_TAG = (
    f'<script src="/analitica.js" data-id="{MEASUREMENT_ID}" '
    f'data-version="{CONSENT_VERSION}" defer></script>'
)
GOOGLE_CONNECT = (
    "https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com"
)


def is_enabled(request: Request, hosts: tuple[str, ...] = ANALYTICS_HOSTS) -> bool:
    """Host con medición, página pública (portada, artistas, guías, tema) y sin iframe."""
    if seo.host_of(request) not in hosts:
        return False
    if request.query_params.get("embed") == "1":
        return False
    path = request.url.path
    return path in seo.INDEXABLE_PATHS or bool(seo.SONG_PATH.fullmatch(path))


def inject(body: bytes) -> bytes:
    return body.decode("utf-8").replace("</body>", SCRIPT_TAG + "</body>", 1).encode("utf-8")


def csp(base: str) -> str:
    """La política de la página más lo que pide Google Analytics, y nada más."""
    out = base.replace("script-src 'self'", "script-src 'self' https://www.googletagmanager.com", 1)
    out = out.replace("img-src 'self' data:", f"img-src 'self' data: {GOOGLE_CONNECT}", 1)
    if "connect-src 'self'" in out:
        return out.replace("connect-src 'self'", f"connect-src 'self' {GOOGLE_CONNECT}", 1)
    return out + f"; connect-src 'self' {GOOGLE_CONNECT}"

"""Ajustes del sitio a las páginas de canción que arma la librería `acordia_render` (S104).

La librería es compartida con el admin y no conoce las cuentas ni Aprende: el sitio le agrega,
al servir, lo suyo. Son reemplazos de texto sobre HTML propio y conocido; si la plantilla cambia
y un fragmento no está, no pasa nada.
"""

PEDIDOS_NAV = (
    '<li class="nav-item"><a class="nav-link" href="pedidos.html">Pide una canción</a></li>'
)
ACCOUNT_NAV = (
    '\n          <li class="nav-item"><a class="nav-link" href="/aprende/">Aprende</a></li>'
    '\n          <li class="nav-item"><a class="nav-link" href="mi-acordia.html">Mi cuenta</a></li>'
)
PEDIDOS_FOOT = '<a href="pedidos.html">Pide una canción</a>'
ACCOUNT_FOOT = '<a href="/aprende/">Aprende</a><a href="mi-acordia.html">Mi cuenta</a>'


def decorate(page: bytes) -> bytes:
    """Menú y pie con «Aprende» y «Mi cuenta»; «Aprende teoría» va a `/aprende/` (C28)."""
    text = page.decode("utf-8")
    text = text.replace(PEDIDOS_NAV, PEDIDOS_NAV + ACCOUNT_NAV, 1)
    text = text.replace(PEDIDOS_FOOT + "\n", PEDIDOS_FOOT + ACCOUNT_FOOT + "\n", 1)
    text = text.replace('href="aprender.html"', 'href="/aprende/"')
    return text.encode("utf-8")

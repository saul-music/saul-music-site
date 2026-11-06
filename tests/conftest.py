"""Las guías de ejemplo son del sitio: la librería las pide a `musicsite.profes` (R1).

`create_app` lo registra; los tests que renderizan páginas sin crear la app lo necesitan igual."""

import pytest
from acordia_render import guides

from musicsite import profes


@pytest.fixture(autouse=True)
def site_guides():
    guides.use(profes)
    yield
    guides.use(None)

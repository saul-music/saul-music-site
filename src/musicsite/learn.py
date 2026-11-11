"""«Aprender» (S65): rutas de aprendizaje con artículos pedagógicos.

Hoy el contenido es estático y vive en el repo: `aprender/rutas.toml` (el árbol de rutas) y un
fragmento HTML por artículo en `aprender/<ruta>/<slug>.html`. Las figuras se piden con
`[[fig:nombre]]` y salen de `learn_figures.FIGURES` (calculadas, no escritas a mano).

Las páginas se arman una vez al arrancar y se sirven como los demás archivos del sitio:
  /aprender.html                     el árbol de rutas
  /aprender-<ruta>-<slug>.html       un artículo
  /aprender.css                      estilos de estas páginas

FUTURO (decisión S65, sin construir): que el admin de research agregue artículos. Seguiría el patrón de los
temas (M17 y M20): el admin publica `rutas.json` más los artículos a un bucket, con `format` y `index.json`,
y el sitio los relee cada 60 s. Cambiar la fuente de esta carpeta al bucket no toca las plantillas.
Antes hay que decidir un formato restringido (por ejemplo Markdown acotado) y sanear el HTML: hoy el
contenido es nuestro y se escribe como HTML, mañana podría venir de otras manos.
"""

import re
import tomllib
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from musicsite.learn_figures import FIGURES

LEARN_DIR = Path(__file__).parent / "aprender"
TOKEN = re.compile(r"\[\[fig:([a-z0-9-]+)\]\]")
HTML = "text/html; charset=utf-8"
CSS = "text/css; charset=utf-8"


@dataclass(frozen=True)
class Article:
    route: str
    slug: str
    title: str
    summary: str
    description: str
    minutes: int
    body: str  # fragmento HTML con [[fig:...]] aún sin resolver

    @property
    def url(self) -> str:
        return f"aprender-{self.route}-{self.slug}.html"


@dataclass(frozen=True)
class Route:
    id: str
    title: str
    summary: str
    articles: list[Article] = field(default_factory=list)


def load(directory: Path = LEARN_DIR) -> list[Route]:
    """Las rutas con sus artículos, en el orden de `rutas.toml`. Falla fuerte si falta un fragmento."""
    data = tomllib.loads((directory / "rutas.toml").read_text(encoding="utf-8"))
    routes = []
    for item in data["ruta"]:
        articles = [
            Article(
                route=item["id"],
                slug=entry["slug"],
                title=entry["titulo"],
                summary=entry["resumen"],
                description=entry["descripcion"],
                minutes=int(entry["lectura"]),
                body=(directory / item["id"] / f"{entry['slug']}.html").read_text(encoding="utf-8"),
            )
            for entry in item.get("articulo", [])
        ]
        routes.append(Route(item["id"], item["titulo"], item["resumen"], articles))
    return routes


def resolve_figures(body: str) -> str:
    """Cambia cada `[[fig:nombre]]` por su figura; una figura que no existe es un error, no un hueco."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in FIGURES:
            raise KeyError(f"figura desconocida: {name}")
        return FIGURES[name]()

    return TOKEN.sub(replace, body)


def _tree(routes: list[Route], current: Article | None = None, summaries: bool = True) -> str:
    items = []
    for route in routes:
        opened = " open" if current is None or current.route == route.id else ""
        rows = []
        for article in route.articles:
            here = article is current or (current is not None and article.url == current.url)
            attrs = ' aria-current="page"' if here else ""
            extra = (
                f'<span class="d-block small text-body-secondary">{escape(article.summary)}'
                f" · {article.minutes} min de lectura</span>"
                if summaries
                else ""
            )
            rows.append(
                f'<li><a class="ac-tree-link" href="{article.url}"{attrs}>{escape(article.title)}</a>{extra}</li>'
            )
        count = len(route.articles)
        noun = "tópico" if count == 1 else "tópicos"
        intro = (
            f'<p class="m-0 text-body-secondary">{escape(route.summary)}</p>' if summaries else ""
        )
        items.append(
            f"<li><details{opened}><summary><strong>{escape(route.title)}</strong>"
            f'<span class="ac-learn-meta">Ruta · {count} {noun}</span></summary>'
            f'<div class="ac-tree-body">{intro}<ol>{"".join(rows)}</ol></div></details></li>'
        )
    items.append('<li class="ac-tree-soon">Más rutas, pronto.</li>')
    return f'<ul class="ac-tree">{"".join(items)}</ul>'


def _hub_main(routes: list[Route]) -> str:
    return f"""    <section class="ac-hero">
      <div class="container"><div class="d-grid gap-4" style="max-width: 46rem">
        <span class="ac-eyebrow">Aprender</span>
        <h1>Rutas de aprendizaje</h1>
        <p class="lead m-0">Teoría explicada para tocar: textos cortos, con diagramas del mástil y ejemplos de guitarra. Elige una ruta y avanza en orden.</p>
      </div></div>
    </section>
    <div class="ac-frieze" aria-hidden="true"></div>
    <section class="ac-section">
      <div class="container"><div style="max-width: 52rem">
        <div class="ac-section-head">
          <span class="ac-eyebrow">Mapa</span>
          <h2>Por dónde empezar</h2>
        </div>
        {_tree(routes)}
      </div></div>
    </section>"""


def _article_main(routes: list[Route], route: Route, article: Article) -> str:
    index = route.articles.index(article)
    # «Anterior» y «Siguiente» siguen el orden de lectura aunque cambie de ruta (Básicos → Acordes).
    flat = [(r, a) for r in routes for a in r.articles]
    position = next(i for i, (_, a) in enumerate(flat) if a.url == article.url)
    previous = flat[position - 1] if position > 0 else None
    following = flat[position + 1] if position + 1 < len(flat) else None

    def label(entry: tuple[Route, Article]) -> str:
        other, target = entry
        suffix = f" ({escape(other.title)})" if other.id != route.id else ""
        return escape(target.title) + suffix

    links = []
    if previous:
        links.append(
            f'<a class="btn btn-outline-secondary" href="{previous[1].url}" rel="prev">← {label(previous)}</a>'
        )
    else:
        links.append("<span></span>")
    if following:
        links.append(
            f'<a class="btn btn-primary" href="{following[1].url}" rel="next">{label(following)} →</a>'
        )
    else:
        links.append(
            '<a class="btn btn-outline-secondary" href="aprender.html">Volver al mapa de rutas</a>'
        )
    return f"""    <div class="container py-4 py-lg-5">
      <nav aria-label="Migas de pan"><ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="aprender.html">Aprender</a></li>
        <li class="breadcrumb-item">{escape(route.title)}</li>
        <li class="breadcrumb-item active" aria-current="page">Tópico {index + 1} de {len(route.articles)}</li>
      </ol></nav>
      <div class="row g-4 g-xl-5">
        <article class="col-lg-8 order-1 order-lg-0">
          <div class="ac-article">
            <span class="ac-eyebrow">Ruta · {escape(route.title)}</span>
            <h1>{escape(article.title)}</h1>
            <p class="ac-learn-meta">{article.minutes} min de lectura</p>
            {resolve_figures(article.body)}
            <div class="ac-learn-nav">{"".join(links)}</div>
          </div>
        </article>
        <aside class="col-lg-4 order-2 order-lg-1" aria-label="Mapa de la ruta">
          <div class="ac-learn-side">
            <h2 class="h5 mb-3">Rutas de aprendizaje</h2>
            {_tree(routes, current=article, summaries=False)}
          </div>
        </aside>
      </div>
    </div>"""


def _page(shell: str, title: str, description: str, main: str) -> bytes:
    page = (
        shell.replace("@@TITLE@@", escape(title))
        .replace("@@DESCRIPTION@@", escape(description, quote=True))
        .replace("@@MAIN@@", main)
    )
    return page.encode("utf-8")


def build_pages(directory: Path = LEARN_DIR) -> dict[str, tuple[bytes, str]]:
    """Ruta pública -> (contenido, tipo) de la página del árbol, cada artículo y los estilos."""
    routes = load(directory)
    shell = (directory / "shell.html").read_text(encoding="utf-8")
    pages = {
        "/aprender.html": (
            _page(
                shell,
                "Aprender",
                "Rutas de aprendizaje de Acordia: teoría explicada para tocar, con diagramas del mástil.",
                _hub_main(routes),
            ),
            HTML,
        ),
        "/aprender.css": ((directory / "aprender.css").read_bytes(), CSS),
    }
    for route in routes:
        for article in route.articles:
            pages["/" + article.url] = (
                _page(
                    shell, article.title, article.description, _article_main(routes, route, article)
                ),
                HTML,
            )
    return pages

# saul-music-site

Sitio público estático de SAÚL música, publicado con GitHub Pages.

- Contenido: ver la sección "Páginas". Este repo es público: nada de datos de usuarios ni de
  investigación entra aquí.
- Despliegue: el pipeline publica en cada push a `main`. Los cambios van por rama y PR.
- Activar Pages (una vez): `bootstrap/github-pages.sh`.

## Páginas

| Archivo | Qué es |
|---|---|
| `index.html` | Inicio de Acordia |
| `cancion.html` | Página de una canción (mockup) |
| `guias.html` | Directorio de guías (mockup) |
| `style.css` | Tema de marca sobre Bootstrap 5.3.3 |
| `acordia.js` | Tema, diagramas de acorde, práctica, filtro y modal |

Para publicar una página o asset nuevo, agrégalo al paso "preparar solo los archivos
públicos" del deploy **y** a la variable `PUBLICOS` del paso "revisar". Si no, no se publica.
`PROMPTS.md` explica el sistema y trae la plantilla para páginas nuevas.

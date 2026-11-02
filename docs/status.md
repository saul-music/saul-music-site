# Estado del sitio

> Registro vivo. Última actualización: 2026-11-02 (S9: el sitio muestra lo publicado desde el admin).

## Paso actual

**Etapa A cerrada (2026-10-30).** El sitio se sirve desde Cloud Run, `musicsite`, en
`https://musicsite-ufi63f4rva-tl.a.run.app` (URL de `run.app`, sin dominio propio). GitHub Pages
está desactivado. Siguiente: S2 (derechos de la canción de ejemplo) antes de anunciar, y decidir la
etapa B. No se adelanta.

## Plan de la etapa A (ejecutado; PR #2)

| Archivo | Contenido |
|---|---|
| `pyproject.toml`, `uv.lock` | fastapi, uvicorn; dev: pytest, ruff, httpx2. `uv --no-config`; `grep -c artifactory uv.lock` = 0 |
| `src/musicsite/app.py` | Sirve los archivos con GET y HEAD; sin `/docs`, `/redoc`, `/openapi.json`; 404 sin cuerpo; cabeceras `nosniff`, `Referrer-Policy`, `frame-ancestors` |
| `src/musicsite/web/` | `index.html`, `cancion.html`, `guias.html`, `style.css`, `acordia.js` (`git mv`) |
| `Dockerfile` | uv fijado, solo PyPI, usuario no root; copia solo `src/` |
| `tests/test_app.py` | 200 en las 3 páginas y tipos correctos; HEAD; 404 en `/docs`, `/openapi.json`, rutas inexistentes y path traversal; cabeceras |
| `tests/test_public_content.py` | Los archivos servidos no contienen referencias a servicios internos ni a investigación; todo enlace interno resuelve |
| `bootstrap/gcp.sh`, `bootstrap/README.md` | Cuentas de servicio propias, repositorio de imágenes, WIF restringido a este repo y a `main` |
| `.github/workflows/pipeline.yml` | lint ∥ test → image → publish → deploy; acciones fijadas por SHA; prueba de humo final |
| `README.md`, `PROMPTS.md` | Rutas nuevas; se elimina `bootstrap/github-pages.sh` al final |

Orden: mergear mockups → PR de la etapa A (verde hasta `image`) → ejecutar `bootstrap/gcp.sh`
(con confirmación) → merge y despliegue → verificar URL → bajar Pages (con OK) → actualizar este
archivo y `decisions.md`.

## Criterios de aceptación

| Criterio | Estado |
|---|---|
| Pruebas y `ruff` pasan | Cumplido: 39 pruebas, ruff y format en verde en el CI (PR #2 y `main`) |
| `/`, `/cancion.html`, `/guias.html` responden 200 en la URL pública | Cumplido (comprobado con `curl` tras el despliegue) |
| `/docs` y `/dashboard/latest` responden 404 | Cumplido (`curl`) |
| `min-instances=0` y región `southamerica-west1` | Cumplido (`gcloud run services describe`: sin `minScale`, región correcta) |
| La imagen construye, sirve y arranca en Cloud Run con Python 3.14 | Cumplido: smoke del CI y del despliegue |
| Runtime sin roles, imagen con tag de git sha | Cumplido (`describe` del servicio) |
| `bootstrap/gcp.sh` recrea el entorno desde cero | **Pendiente**: se ejecutó sobre un proyecto con el pool `github` ya creado y se reintentó una vez por cuota de lecturas; no se probó en un proyecto vacío |
| Contraste, aspecto y celular | **Pendiente** (a ojo, por el usuario) |
| GitHub Pages desactivado | Cumplido (la API de Pages responde 404) |

## Puntos abiertos

1. **S2:** canción ajena en `cancion.html` se mantiene; derechos de autor pendientes antes de anunciar. La verificación global V2 (derechos de autor) se lleva en el repo de control.
2. El deployer tiene `run.admin` a nivel de proyecto (necesario para fijar la política pública), así que también podría administrar otros servicios del mismo proyecto. Riesgo aceptado como en el otro nicho.
3. Dominio propio: hoy sería una URL `*.run.app`; un dominio es una decisión aparte.
4. No anunciar el sitio antes de resolver S2 y de proteger cualquier servicio interno vinculado.
5. Etapa B (primera interacción, "pide una canción"): requiere decidir datos, almacenamiento en
   `southamerica-west1`, consentimiento, aviso de privacidad y límite de envíos. No se adelanta.

## Bitácora

```text
AAAA-MM-DD · paso · qué se hizo · qué quedó pendiente · decisiones nuevas
2026-10-30 · mockups · Acordia (index, cancion, guias) sobre Bootstrap, PR pendiente · S2 abierta
2026-10-30 · mockups mergeados · PR #1 a main; GitHub Pages desactivado por el usuario (sin URL pública hasta Cloud Run) · pendiente: despliegue · S1
2026-10-30 · código etapa A · app FastAPI, 39 tests, Dockerfile, pipeline ci→image→publish→deploy, bootstrap/gcp.sh (dry-run) en feat/cloud-run · pendiente: ejecutar bootstrap, CI, despliegue real, Python 3.14 en Cloud Run
2026-10-30 · despliegue · bootstrap/gcp.sh ejecutado en saulapp-music (un reintento por cuota de lecturas), variable GCP_WIF_PROVIDER, PR #2 mergeado, pipeline ci→image→publish→deploy verde en main, servicio musicsite en Cloud Run verificado con curl · pendiente: S2, revisión visual, bootstrap desde cero · S1
2026-10-30 · plan etapa A · decisión de desplegar en Cloud Run desde este repo y plan documentado; sin código · pendiente: aprobación del plan · S1, S2
2026-10-30 · panel de guías · rama feat/panel-profes: profes.toml (reglas por artista, tema o todo), musicsite.profes, panel en las 16 páginas de tema y guias.html generado con filtro ?tema= (216 tests, ruff limpio) · pendiente: revisión visual por el usuario, merge · S3
2026-10-30 · migración a la organización saul-music · remotos movidos; condición del proveedor WIF y binding de la cuenta del deployer cambiados a saul-music/<repo> en GCP (los dos), y GITHUB_REPO del bootstrap actualizado · pendiente: comprobar el pipeline en el repo nuevo
2026-10-30 · Cámara lenta Intermedio · notación de varios acordes por compás (F#-F#7, F#-%-F#7-B7; PR #16, 224 tests) y página regenerada con el modo Intermedio; el panel de guías (PR #14) quedó revisado y mergeado · pendiente: Avanzado de Cámara lenta, V2 (asesoría legal)
2026-10-31 · templates y metrónomo · rama feat/metronomo-templates: Jinja2 (S4), base.html y cancion.html reemplazan 16 HTML generados; songs/ con los 16 TOML publicables, comando publish; metrónomo (Web Audio, 30–240 bpm, +/-, deslizante, restablecer, pulso visual) en cada tema con bpm; 231 tests, ruff limpio · pendiente: oír el clic y revisar el pulso y el celular (usuario), PR siguiente con Playwright en matriz de navegadores · S4
2026-10-31 · Playwright · rama feat/e2e-playwright: 9 pruebas de navegador (metrónomo, pestañas, tema, 404, sin desborde) en 5 configuraciones locales verdes (chromium, firefox, webkit, Pixel 7, iPhone 14); job e2e en matriz antes de la imagen · la suite halló un desborde horizontal de 15 px en celular por el panel de guías (PR #14), corregido · pendiente: ver el job e2e en verde en el CI, oír el clic · S5
2026-11-01 · metrónomo en Safari · rama fix/metronomo-safari: el audio solo sonaba en Chrome porque el primer clic se agendaba antes de que resume() terminara (reloj detenido en Safari) y iOS silenciaba Web Audio con el interruptor de silencio; ahora se espera a `running`, se reanuda si se suspende y se fija audioSession=playback; prueba e2e con contexto suspendido (falla sin el arreglo) · el usuario confirmó el sonido en Safari de Mac y en iPhone · pendiente: nada de este tema
2026-11-01 · audio real en CI · test_audio_real.py mide señal en la salida de un AudioContext real con un AnalyserNode; el pipeline arranca un sink nulo de PulseAudio (+7 s por job); 5 de 5 corridas verdes en las 5 configuraciones y, sin PulseAudio, Firefox falla con el contexto suspended (control); el pulso de test_site.py usa un contexto simulado para no depender del runner (PR #20, experimento PR #21) · pendiente: lo audible sigue siendo de oído
2026-11-01 · cursor de compases, metrónomo fijo y tipografía · rama feat/cursor-compases: los compases de la pestaña visible parpadean al pulso con flecha ▼ y contador «n / N» de repeticiones; el metrónomo queda fijo junto a los compases y las guías van arriba; acordes en Petaluma Script (SIL OFL 1.1, alojada en el sitio, CSP font-src 'self') con ♯/♭ solo al mostrar; el deslizante del metrónomo recupera una pista visible; 233 tests y 13 e2e en las 5 configuraciones · revisión visual hecha por el usuario · pendiente: S6 (SEO y medición antes de anunciar)
2026-11-02 · sin sonido, guías y %  · rama feat/sin-sonido-y-guias: «Sin sonido» sigue el tempo con reloj propio y sin tocar audioSession (recuerda la elección); franja de guías arriba que, al salir de pantalla, pasa a un botón corto en la barra fija; ambos abren un desplegable con las 5 guías mejor puntuadas (nota, cobertura del tema y precio por clase) y cada una enlaza a su tarjeta en guias.html (#guia-id, resaltada); puntuación solo en perfiles de ejemplo, las personas reales figuran como «Nuevo»; el % repite el acorde anterior atenuado; barra más compacta (sin puntos de pulso ni íconos de más) · 243 tests y 20 e2e en las 5 configuraciones · pendiente: oír el modo sin sonido en Safari/iPhone y revisar a ojo el desplegable en celular; página de perfil propia por guía (no existe), S6
2026-11-02 · diagramas de acorde · rama feat/diagramas-acordes (sin PR): cada acorde abre un panel con guitarra + tab y teclado (escritorio: cursor, foco o clic; celular: panel inferior), con «Otra forma»; formas estándar de chords-db (MIT, 893 formas vendorizadas, aviso en THIRD_PARTY_NOTICES.md) y formas propias opcionales en [intermedio.formas]/[avanzado.formas] con validación; teclado calculado con teoría propia (notas por grado); título y artista quedan fijos al bajar · 283 tests y 23 e2e en las 5 configuraciones · pendiente: revisión a ojo de los 23 acordes y del panel en Safari/iPhone (usuario), replicar la regla en el validador y el editor de research (M16), S8
2026-11-02 · lo publicado llega al sitio (rama feat/editorial-bucket, sin PR) · S9: catalog.py lee la publicación vigente del bucket editorial (puntero, relectura cada 60 s, una publicación inválida nunca reemplaza a la buena, respaldo en songs/); la Biblioteca del inicio también sale de lo publicado, con «Próximamente» solo con título y artista; bootstrap: musicsite-runtime con objectViewer en el bucket (aplicado) y volumen de solo lectura en el despliegue; 295 tests, y probado con la publicación real del bucket (16 temas, edición de dejate-caer visible) · pendiente: merge y despliegue, comprobar en producción, retirar songs/ cuando sea estable, artistas.html/guias.html siguen estáticos · S9
2026-11-02 · cuenta inicial del metrónomo (rama feat/cuenta-inicial, sin PR) · S10: 4 clics antes del compás 1, activada por defecto, botón «Cuenta inicial» para desactivarla y preferencia en localStorage; suena si hay sonido, visual en «Sin sonido»; tests de unidad y e2e · pendiente: revisión a ojo y de oído por el usuario, PR y merge, oírla en Safari/iPhone · S10
2026-11-02 · arreglo de la barra del metrónomo en escritorio (rama fix/barra-metronomo-escritorio) · el PR #26 (cuenta inicial) se mergeó con e2e firefox en rojo: en el CI de Linux la barra fija pasaba a dos filas y tapaba las pestañas (test_difficulty_tabs_switch); el despliegue no corrió; se achica el mínimo del deslizador (8 a 5 rem) y la barra vuelve a una fila · pendiente: merge y verificar el despliegue de S10
2026-11-02 · parpadeo por subdivisión (rama feat/parpadeo-subdivisiones, sin PR) · S11: en un compás con varios acordes parpadea solo la parte que suena (data-weight en .ac-part, beatTarget en acordia.js); tests de unidad y e2e en los 5 navegadores · pendiente: revisión a ojo del usuario, PR y merge · S11
2026-11-02 · partir desde un compás y compás centrado (misma rama feat/parpadeo-subdivisiones, sin PR) · S12: bandera «Partir desde aquí» en cada compás (una marca por página) y centrado del compás actual con pausa de 4 s si la persona hace scroll; tests e2e en los 5 navegadores; un test existente con igualdad exacta de flotantes se pasó a tolerancia (firefox) · pendiente: revisión a ojo y de oído del usuario, PR y merge (incluye S11) · S12
2026-11-02 · indicador de la cuenta inicial (misma rama, sin PR) · el botón principal muestra 1 2 3 4 durante la cuenta; la barra no crece · en el camino un `git checkout` del CSS borró estilos sin commit (bandera y parpadeo); se rehicieron y los tests los cubren · pendiente: revisión a ojo del usuario, PR y merge (S10, S11, S12)
2026-11-02 · tips entre secciones (rama feat/tips, sin PR) · S13: línea `> Título | Texto` en la partitura, tarjeta con ícono que brilla y se despliega, validación y límites, cursor del metrónomo las ignora; tests de unidad y e2e; guía de edición con la sección «Tips» · pendiente: revisión a ojo del usuario, PR y merge, sincronizar el validador de research para publicarlos desde el admin · S13
2026-11-02 · contrato del validador (rama feat/contrato-validador) · tests/fixtures/acordes/contract.json copiado de research (con 9 casos de tips) y tests/test_contract.py lo prueba contra musicsite.acordes: 24 casos en verde, 328 tests de unidad; si las copias divergen, falla · pendiente: PR · research M28
```

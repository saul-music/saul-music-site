# Estudio: posiciones de guitarra como MIDI y sonido de guitarra acústica en el reproductor

> Investigación abierta en la rama `feat/investigacion-midi` (S37). Fecha: 2026-11-05. Sin código todavía:
> nada de esto se implementa sin plan y aprobación explícita.

## Pregunta

¿Cuánto cuesta que el reproductor de la página de canción, además del clic del metrónomo, **toque los acordes**
con la posición de guitarra que muestra el panel, como notas MIDI y con un sonido básico de guitarra acústica?

## Respuesta corta

- **Barato en lo técnico.** Lo difícil ya existe: el metrónomo agenda con el reloj de Web Audio (S10 a S12) y
  `data/chords-guitar.json` trae la afinación como números MIDI (`[40,45,50,55,59,64]`, E2 a E4). Pasar una forma
  a notas MIDI es una suma por cuerda: `nota = afinación[cuerda] + traste` (`-1` = cuerda que no suena).
- **Infra ≈ 0.** Todo corre en el navegador del visitante. No hay servidor nuevo, ni API, ni costo en reposo.
  Lo único que se sirve son archivos estáticos (de 0 a ~750 KB según la opción, con caché inmutable).
- **El costo real es organizativo:** por R1, cualquier cambio en `acordia.js` empieza migrando el render a
  `saul-music-render`. Esa migración pesa más que el audio en sí.
- **Estimación:** prototipo aislado en 1 a 2 días; integración al reproductor en 3 a 5 días más; más 1 a 2 semanas
  si antes hay que hacer los pasos 2 y 3 de R1. Rasgueos por tema (contenido editorial) aparte.

## Lo que ya hay (comprobado en el código, 2026-11-05)

| Pieza | Dónde | Qué aporta |
| --- | --- | --- |
| Metrónomo con agenda anticipada | `web/acordia.js` (`AHEAD = 0.12 s`, `TICK = 25 ms`) | El reloj del audio decide cuándo suena cada golpe; sirve igual para notas |
| Secuencia de compases, partes y silencios | `acordia.js` (`cur.seq`, `beatTarget`), S16, S22 | Ya sabe qué acorde suena en cada pulso, incluidos los compases partidos y `.` |
| Formas de guitarra | `data/chords-guitar.json` (chords-db, MIT), `[formas]` por tema (S27), «Otra forma» | Trastes por cuerda; la afinación viene en MIDI |
| Bajos `G/B` | S19 (`chordtheory.guitar_positions`) | Forma con bajo, o la del acorde base sin el bajo |
| Notas de acordes sin guitarra | S21 (teclado de `add#11`) | Respaldo: se puede tocar un voicing cerrado con las notas del teclado |
| iOS y «Sin sonido» | `acordia.js` (sesión de audio `playback`), S32 | El desbloqueo del audio y el modo mudo ya resueltos |
| Audio real en CI | PR #20 (rama `test/audio-real`) | Base para probar que suena, no solo que no falla |

## Opciones de sonido

| Opción | Qué es | Peso | Licencia | Calidad | Esfuerzo |
| --- | --- | --- | --- | --- | --- |
| **A. Síntesis Karplus-Strong** | Cuerda pulsada sintetizada (ruido + retardo filtrado), en un `AudioBuffer` por nota o en un `AudioWorklet` | 0 KB de audio; ~2 a 4 KB de código | Propia, sin terceros | «Guitarra básica» reconocible, algo metálica | 1 a 2 días |
| **B. Muestras propias de FluidR3_GM** (`acoustic_guitar_steel` o `_nylon`), una MP3 por nota, servidas desde el sitio | Notas grabadas, afinadas con `playbackRate` | ~17 a 21 KB por nota (medido); 40 notas (E2 a G5) ≈ 750 KB; una de cada 3 semitonos ≈ 14 notas ≈ 270 KB | **CC BY 3.0** según `gleitz/midi-js-soundfonts`; el `.sf2` original de FluidR3 circula como MIT: **verificar (L1)** y atribuir en `THIRD_PARTY_NOTICES.md` | Más natural | 2 a 3 días |
| C. Igual que B con MusyngKite | Otro banco | Similar (medido) | **CC BY-SA 3.0**: share-alike, evitar | Mejor | — |
| D. Librería (`smplr`, MIT; `Tone.js`, MIT, con `PluckSynth`) | Reproductor de soundfonts ya hecho | Código de terceros + muestras | MIT, más la de las muestras | Igual que A o B | Menos código propio, pero es una **tecnología nueva** (decisión aparte) y `smplr` carga por defecto desde `gleitz.github.io` (tercero; cambiaría la CSP y enviaría la IP del visitante a GitHub) |

**Recomendación:** prototipar **A** primero (cero peso, cero licencias, cero dependencias) y compararla a oído con **B**
autoalojada. D no hace falta: lo que resuelve, el sitio ya lo tiene (agenda, decodificación, iOS).

## MIDI: qué significa aquí

1. **Notas MIDI internas (necesario).** Forma → seis números MIDI → voces de audio. Es la base de todo.
2. **Exportar un `.mid` del tema (opcional, ~1 día).** Archivo de acompañamiento para abrir en un DAW o GarageBand.
   Es un archivo generado en el navegador; no toca el servidor. Ojo con V2: distribuir un archivo del tema es otra forma
   de publicar sus acordes.
3. **Salida Web MIDI a un teclado o DAW (opcional, ~1 día).** No existe en Safari ni en iOS, así que sería un extra de
   escritorio, nunca la vía principal.

## Diseño mínimo propuesto (para el prototipo)

- **Rasgueo:** un golpe por parte del compás (S16), hacia abajo, con 10 a 20 ms entre cuerdas, de grave a aguda.
  Variante de prueba: abajo en los tiempos, arriba en los contratiempos.
- **Qué forma suena:** la que está viendo el usuario (primera forma, `[formas]` del tema, o la elegida con «Otra forma»).
  `G/B` sin forma con bajo: la forma base más la nota del bajo. Sin forma de guitarra (p. ej. `add#11`): voicing cerrado con
  las notas del teclado (S21), o silencio con aviso; se decide en el prototipo.
- **Silencios (`.`):** cortan las cuerdas (rampa corta de volumen); `%` repite el golpe.
- **Controles:** un interruptor «Guitarra» junto al metrónomo, con volumen relativo al clic. «Sin sonido» apaga ambos.
  La cuenta inicial sigue siendo solo clic.
- **Celular:** 6 voces por golpe y decaimiento de ~1,5 s dan a lo más ~24 voces vivas: bajo para cualquier teléfono.
  Las muestras de B se decodifican al primer toque de «Reproducir», no al cargar la página.

## Costos

### Infra y dinero

- **Servidor:** ninguno nuevo. `musicsite` sigue con `min-instances=0`.
- **Transferencia:** A no suma nada; B suma ~270 a 750 KB la primera vez por visitante (luego caché del navegador,
  con nombre con hash). Del orden de 1 GB cada 1.300 a 3.700 primeras visitas: centavos de dólar al mes con el tráfico
  de hoy (precio exacto de salida de Cloud Run sin verificar).
- **CSP:** sin cambios si todo se sirve desde el propio sitio (`default-src 'self'` cubre `fetch` y un `AudioWorklet`).

### Trabajo (una persona con Claude; estimación, no medido)

| Paso | Esfuerzo | Notas |
| --- | --- | --- |
| 0. Prototipo aislado: página de laboratorio local (no publicada) con forma → MIDI, opciones A y B, rasgueo simple | 1 a 2 días | Puede vivir en esta rama sin tocar `acordia.js` |
| 1. Requisito R1: mover contrato, validador y render a `saul-music-render` (pasos 2 y 3) | 1 a 2 semanas | Lo impone el disparador de R1 al tocar `acordia.js` (ver abajo) |
| 2. Integración al reproductor: interruptor, forma visible, partes, silencios, iOS, «Sin sonido» | 3 a 5 días | Incluye tests unitarios de forma → MIDI y e2e con audio real |
| 3. (Opcional) Exportar `.mid` | ~1 día | Revisar V2 antes |
| 4. (Opcional) Rasgueos por tema (`ritmo = "D-DU-UDU"` u otro) | 3 a 5 días + tiempo editorial | Cambia el contrato y el editor de research (M-ID nuevo) |

## Bloqueos y riesgos

1. **R1 (el más caro).** `acordia.js` está en `SITE_MANIFEST.json` de research: tocarlo exige migrar antes el render
   a la librería. Alternativa a evaluar con una decisión: un archivo aparte (`acordia-audio.js`) fuera del manifiesto, con
   un enganche mínimo en el metrónomo. Igual toca `acordia.js` (el enganche) y la vista previa del admin dejaría de ser fiel,
   así que **no evita R1**, solo la achica. No se decide aquí.
2. **Legal (V2, D-C25).** Tocar en el navegador los acordes que ya se publican no agrega una obra nueva, pero sí es una
   «interpretación» automática del tema. D-C25 permite audio sintético de acompañamiento **sin melodía ni riff literal**:
   por eso los **tabs y riffs de Avanzado (S17) quedan fuera** de este estudio. Sumar la pregunta a la consulta legal.
3. **Licencia de muestras (L1).** Si se usa B, aclarar si rige CC BY 3.0 (gleitz) o MIT (`.sf2` original) y atribuir.
4. **Calidad percibida.** Un rasgueo mecánico puede sonar a juguete y restar confianza (posicionamiento por confianza,
   D-C17). Mitigación: prueba a oído con 3 a 5 músicos antes de publicar.
5. **Rama larga.** Se separa de `main` (S37): hay que traer `main` a la rama seguido para que no diverja.

## Qué medir en la investigación

- A vs. B a oído, en parlante de celular y con audífonos (Safari/iPhone y Chrome/Android).
- Latencia del primer golpe en iOS tras tocar «Reproducir».
- Si los músicos lo usan para practicar (pregunta en el feedback de usuarios) antes de pagar el costo de R1.

## Laboratorio (2026-11-05)

Página local `lab/midi/` (ver `lab/midi/README.md`). Lee `chords-guitar.json` del sitio por un enlace, sin copiarlo, y
replica el orden de formas del panel (forma del tema primero y después la regla de cejilla, S27). Tiene los motores A y B,
rasgueo configurable, progresiones con patrón y las mediciones en pantalla.

**Primeras mediciones** (Mac, navegadores automáticos sin parlante; falta el oído y el iPhone real):

| Medición | Chromium | WebKit (Safari) | Firefox |
| --- | --- | --- | --- |
| Comprobación MIDI (G, C, F con cejilla) | ✓ | ✓ | ✓ |
| Muestras acero, conjunto ligero (17 notas) | 297 KB · 36 ms | 297 KB · 160 ms | — |
| Muestras acero, conjunto completo (49 notas, E2 a E6) | 855 KB · 47 ms | 855 KB · 253 a 285 ms | — |
| Preparar un rasgueo con A (sintetizar ~6 notas de 3 s) | ~26 ms | ~9 ms | — |
| Preparar un rasgueo con B | < 1 ms | < 1 ms | — |
| Latencia que informa el navegador | 5,8 ms | 3,2 ms | — |

Lectura: B cuesta 0,3 a 0,9 MB por banco y unos 0,3 s de decodificación en Safari, una sola vez. A no pesa nada y prepara
un acorde nuevo en milisegundos. Las dos son viables en lo técnico; la elección es de oído.

**Pendiente:** escucharlo (A vs. B, acero vs. nailon, ligero vs. completo) en el Mac y en el iPhone, y anotar aquí el juicio.

## Prueba en el reproductor (2026-11-05)

Regla de rasgueo y botón descritos en S37. Prueba automática en WebKit, Chromium y Firefox sobre los 17 temas del catálogo
local (`releases/20261105-005059-94ea`) y todos sus niveles: empieza apagada en todos; apagada, 0 notas; encendida, suena
en cada nivel con compases (Intermedio y Avanzado vacíos no suenan, como corresponde); sin errores de JavaScript. Ningún
acorde de los temas publicados queda sin forma de guitarra. **Pendiente:** escucharlo en el Mac y en el iPhone.

## Fuentes

- `gleitz/midi-js-soundfonts` (licencias por banco): https://github.com/gleitz/midi-js-soundfonts
- Tamaños medidos con `curl -I` en `gleitz.github.io/midi-js-soundfonts/<banco>/acoustic_guitar_steel-mp3/<nota>.mp3`
  (2026-11-05): E2 17 KB, A3 20 KB, E4 21 KB, C5 17 KB (FluidR3_GM); el banco completo en un `.js` pesa ~1,9 MB.
- `smplr` (MIT, carga por defecto desde gleitz): https://github.com/danigb/smplr

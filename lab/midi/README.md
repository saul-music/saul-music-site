# Laboratorio de guitarra (S37)

Página local para estudiar el sonido: posiciones de guitarra → notas MIDI → rasgueo, con dos motores para comparar a oído.
**No es parte del sitio**: no entra a la imagen, no toca `acordia.js` y esta rama nunca se mergea (`docs/decisions.md`, S37).

## Uso

```bash
lab/midi/bajar-muestras.sh   # una vez: muestras FluidR3_GM (acero y nailon, ~1,8 MB) a lab/midi/muestras/, ignorada por git
lab/midi/servir.sh           # http://localhost:8090/ y la IP de la Mac para el celular (misma wifi)
```

En el iPhone, el primer toque de un botón activa el audio. Suena con el interruptor de silencio puesto (Safari 16.4 o más nuevo).

## Qué se puede probar

- **Motor A** (Karplus-Strong): cuerda sintetizada en el navegador, con controles de brillo, sustain y cuerpo. 0 KB de audio.
- **Motor B** (FluidR3_GM): notas grabadas de acero o nailon, en conjunto completo (1 por semitono) o ligero (1 cada 3, afinado con `playbackRate`).
- **Rasgueo:** milisegundos entre cuerdas, arriba solo con las 4 agudas, humanizar.
- **Formas del tema:** mismo formato que `[formas]`; van primero, como en el panel del sitio (S27).
- **Acorde suelto:** «Otra forma» recorre las formas; muestra trastes, MIDI y nombres de notas.
- **Progresión:** un acorde por compás, `%` repite y `.` es silencio; patrones en corcheas (`D`, `U`, `-`), clic, cuenta inicial y repetir.
- **Mediciones:** KB, tiempos de carga y preparación, y latencias del navegador.

Fuera de alcance: acordes con bajo (`G/B`), tabs y riffs (D-C25), exportar `.mid` e integrar al reproductor.

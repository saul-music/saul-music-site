# Avisos de terceros

Política de licencias L1 (repo de control): solo MIT, BSD, ISC o Apache-2.0; nada GPL, AGPL ni «no
comercial». Lo que se copia al repo conserva su aviso aquí.

## chords-db — formas de guitarra de los diagramas de acorde

- Qué: formas de acordes de guitarra, recortadas a los acordes que sabemos interpretar y a las que
  solo suenan notas del acorde (`src/musicsite/data/chords-guitar.json`, generado con
  `python -m musicsite.chordsdb vendor`).
- Fuente: <https://github.com/tombatossals/chords-db> (paquete npm `@tombatossals/chords-db` 0.5.1).
- Licencia: MIT, Copyright (c) 2016 David Rubert. Texto completo en
  `src/musicsite/data/LICENSE-chords-db.txt`.
- Origen de los datos: obra de su autor y de colaboradores por PR; el repositorio no declara una
  fuente externa (revisado el 2026-11-02).

## Petaluma Script — tipografía de los acordes

- Licencia: SIL Open Font License 1.1, Copyright (c) 2018 Steinberg Media Technologies GmbH. Texto
  en `src/musicsite/web/PetalumaScript-OFL.txt`.
- Fuente: <https://github.com/steinbergmedia/petaluma>.

## FluidR3_GM — muestras de guitarra de nailon y contrabajo del botón «Guitarra»

- Qué: 49 notas de guitarra de nailon (E2 a E6) y 12 de contrabajo (E1 a Eb2) en mp3, una por semitono
  (`src/musicsite/web/guitarra-nylon-*.mp3` y `bajo-*.mp3`).
- Fuente: <https://github.com/gleitz/midi-js-soundfonts> (carpeta `FluidR3_GM`, `acoustic_guitar_nylon-mp3` y
  `acoustic_bass-mp3`), generadas a partir del banco FluidR3_GM.sf2 de Frank Wen.
- Licencia: Creative Commons Attribution 3.0 (CC BY 3.0, <https://creativecommons.org/licenses/by/3.0/us/>), según el README
  de ese proyecto; el repositorio del proyecto es MIT. Atribución: «FluidR3_GM, Frank Wen; muestras convertidas a mp3 por
  Benjamin Gleitz (midi-js-soundfonts)». Se copiaron sin modificar.
- **Excepción a L1:** CC BY no está en la lista de L1 (MIT, BSD, ISC, Apache-2.0). La incluye el usuario por decisión del
  2026-11-05 (S37), con esta atribución. Revisada solo la licencia declarada por el distribuidor (2026-11-05).

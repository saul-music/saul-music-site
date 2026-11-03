"""Recorta chords-db (MIT) a las formas de guitarra que usa el sitio.

Herramienta de desarrollo, sin red. Se baja el archivo a mano y se pasa su ruta:

    curl -o /tmp/guitar.json \\
      https://cdn.jsdelivr.net/npm/@tombatossals/chords-db@0.5.1/lib/guitar.json
    python -m musicsite.chordsdb vendor /tmp/guitar.json

Escribe `data/chords-guitar.json` con trastes absolutos, solo para los sufijos que sabemos
interpretar (chordtheory.INTERVALS) y descartando toda forma que suene una nota ajena al acorde.
"""

import argparse
import json
from pathlib import Path

from musicsite import chordtheory as theory

OUT = Path(__file__).with_name("data") / "chords-guitar.json"
SOURCE = "https://github.com/tombatossals/chords-db (npm @tombatossals/chords-db 0.5.1)"
KEY_NAMES = {"Csharp": "C#", "Fsharp": "F#"}


def absolute(position: dict) -> list[int]:
    """chords-db numera los trastes desde `baseFret`; aquí son absolutos."""
    base = position["baseFret"]
    return [f + base - 1 if f > 0 else f for f in position["frets"]]


def vendor(db_path: Path, out: Path = OUT, only_slash: bool = False) -> dict:
    """Con `only_slash` se parte del archivo ya vendorizado y solo se agregan las formas con bajo
    (G/B): lo demás no se toca (S19)."""
    db = json.loads(db_path.read_text(encoding="utf-8"))
    existing = json.loads(out.read_text(encoding="utf-8")) if only_slash else {}
    chords: dict[str, dict] = existing.get("acordes", {})
    kept = dropped = 0
    for raw_key, entries in db["chords"].items():
        key = KEY_NAMES.get(raw_key, raw_key)
        root = theory.parse(key)
        if root is None:
            continue
        for entry in entries:
            suffix = entry["suffix"]
            if (
                "/" in suffix
            ):  # forma con bajo (G/B): se guarda como «major/11» (sufijo/clase del bajo)
                chord = theory.parse(key + suffix)
                if chord is None:
                    continue
                suffix = f"{chord.suffix}/{chord.bass}"
            elif only_slash:
                continue
            elif suffix in theory.INTERVALS:
                chord = theory.Chord(key, root.root, None, suffix, root.flats)
            else:
                continue
            positions = []
            for position in entry["positions"]:
                frets = absolute(position)
                if not theory.position_ok(chord, frets):
                    dropped += 1
                    continue
                barres = sorted({b + position["baseFret"] - 1 for b in position.get("barres", [])})
                positions.append({"f": frets, "d": position["fingers"], "b": barres})
                kept += 1
            if positions:
                chords.setdefault(key, {})[suffix] = positions
    data = {
        "fuente": existing.get("fuente", SOURCE),
        "licencia": "MIT (ver THIRD_PARTY_NOTICES.md)",
        "afinacion": list(theory.TUNING),
        "acordes": chords,
    }
    out.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"{kept} formas escritas en {out}; {dropped} descartadas por sonar notas ajenas")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="musicsite.chordsdb", description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["vendor"])
    parser.add_argument("source", type=Path, help="guitar.json de chords-db")
    parser.add_argument(
        "--only-slash", action="store_true", help="agrega solo las formas con bajo (G/B)"
    )
    args = parser.parse_args(argv)
    vendor(args.source, only_slash=args.only_slash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

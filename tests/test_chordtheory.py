"""Teoría de acordes y formas de guitarra: datos y reglas sintéticos, sin red."""

import json
from pathlib import Path

import pytest

from musicsite import chordsdb
from musicsite import chordtheory as theory
from musicsite.app import SONGS_DIR
from musicsite.songpages import chords_payload, load_song


def chord(token: str) -> theory.Chord:
    parsed = theory.parse(token)
    assert parsed is not None, token
    return parsed


@pytest.mark.parametrize(
    ("token", "suffix", "root", "bass"),
    [
        ("G", "major", 7, None),
        ("F#m", "minor", 6, None),
        ("Bbmaj7", "maj7", 10, None),
        ("Dsus4", "sus4", 2, None),
        ("G/B", "major", 7, 11),
        ("C#m7b5", "m7b5", 1, None),
        ("Bm11", "m11", 11, None),
        ("Bm69", "m69", 11, None),
        ("BmM7", "mmaj7", 11, None),
        ("Bmmaj9", "mmaj9", 11, None),
        ("Bmmaj11", "mmaj11", 11, None),
        ("Bmmaj7b5", "mmaj7b5", 11, None),
        ("Bsus4add9", "sus2sus4", 11, None),
        ("Bsus2sus4", "sus2sus4", 11, None),
        ("Bm/F#", "minor", 11, 6),
    ],
)
def test_parse_reads_root_quality_and_bass(token, suffix, root, bass):
    parsed = chord(token)
    assert (parsed.suffix, parsed.root, parsed.bass) == (suffix, root, bass)


@pytest.mark.parametrize("token", ["%", "H", "Gmaj13", "Cadd9b5", "", "g", "Bmadd11", "Bm13"])
def test_parse_returns_none_for_what_we_cannot_draw(token):
    assert theory.parse(token) is None


@pytest.mark.parametrize(
    ("token", "notes"),
    [
        ("Cm", ["C", "Eb", "G"]),
        ("F#", ["F#", "A#", "C#"]),
        ("Bbm7", ["Bb", "Db", "F", "Ab"]),
        ("Cdim7", ["C", "Eb", "Gb", "Bbb"]),
        ("D#m", ["D#", "F#", "A#"]),
        ("Bm11", ["B", "D", "F#", "A", "C#", "E"]),
        ("Bm69", ["B", "D", "F#", "G#", "C#"]),
        ("BmM7", ["B", "D", "F#", "A#"]),
        ("Bmmaj7b5", ["B", "D", "F", "A#"]),
        ("Bsus4add9", ["B", "C#", "E", "F#"]),
        ("G/B", ["G", "B", "D"]),
        ("C/D", ["D", "C", "E", "G"]),
    ],
)
def test_notes_are_spelled_by_degree(token, notes):
    assert theory.note_names(chord(token)) == notes


def test_piano_keys_and_bass():
    assert theory.piano_keys(chord("C")) == ([0, 4, 7], None)
    assert theory.piano_keys(chord("Cadd9")) == ([0, 4, 7, 14], None)  # novena en la 2ª octava
    assert theory.piano_keys(chord("B")) == ([11, 15, 18], None)
    assert theory.piano_keys(chord("G/B")) == ([7, 11, 14], 11)
    for token in ("Bmaj9", "B9", "Bm9"):
        assert all(0 <= k <= 23 for k in theory.piano_keys(chord(token))[0])


def test_parse_shape_and_tab_lines():
    assert theory.parse_shape("x 3 2 0 1 0") == [-1, 3, 2, 0, 1, 0]
    with pytest.raises(ValueError, match="no es un traste"):
        theory.parse_shape("x 3 2 0 1 h")
    assert theory.tab_lines([-1, 3, 2, 0, 1, 0]) == ("E A D G B e", "x 3 2 0 1 0")
    top, bottom = theory.tab_lines([8, 10, 10, 9, 8, 8])
    assert len(top.split()) == len(bottom.split()) == 6


def test_a_valid_shape_has_no_errors_and_foreign_notes_are_caught():
    assert theory.check_shape(chord("C"), [-1, 3, 2, 0, 1, 0]) == []
    errors = theory.check_shape(chord("C"), [-1, 3, 2, 0, 1, 1])
    assert errors and "F" in errors[0] and "no es del acorde C" in errors[0]


def test_basic_shape_rules():
    c = chord("C")
    assert "6 valores" in theory.check_shape(c, [0, 0, 0])[0]
    assert "fuera de 0 a 24" in theory.check_shape(c, [-1, 25, 2, 0, 1, 0])[0]
    assert "al menos en 3 cuerdas" in theory.check_shape(c, [-1, 3, -1, -1, -1, 0])[0]


def test_slash_chord_needs_the_bass_as_lowest_note():
    g_over_b = chord("G/B")
    assert theory.check_shape(g_over_b, [-1, 2, 0, 0, 3, 3]) == []
    assert "más grave debe ser B" in theory.check_shape(g_over_b, [3, 2, 0, 0, 3, 3])[0]


def test_vendored_shapes_only_sound_notes_of_their_chord():
    data = json.loads(theory.DATA_FILE.read_text(encoding="utf-8"))
    assert data["afinacion"] == list(theory.TUNING) and "MIT" in data["licencia"]
    total = 0
    for key, by_suffix in data["acordes"].items():
        for suffix, positions in by_suffix.items():
            root = chord(key)
            c = theory.Chord(key, root.root, None, suffix, root.flats, root.letter, root.accidental)
            for position in positions:
                total += 1
                assert theory.position_ok(c, position["f"]), (key, suffix, position)
                assert len(position["f"]) == len(position["d"]) == 6
    assert total > 500


NEW_MINORS = ["m11", "m69", "mmaj7", "mmaj7b5", "mmaj9", "mmaj11"]


@pytest.mark.parametrize("suffix", NEW_MINORS)
def test_every_minor_has_a_standard_shape_in_the_twelve_keys(suffix):
    data = json.loads(theory.DATA_FILE.read_text(encoding="utf-8"))["acordes"]
    assert [k for k, by_suffix in data.items() if suffix not in by_suffix] == []
    assert theory.standard_positions(chord("Bm" + suffix[1:])) is not None


def test_sus4add9_has_shapes_in_all_but_ab():
    data = json.loads(theory.DATA_FILE.read_text(encoding="utf-8"))["acordes"]
    assert [k for k, by_suffix in data.items() if "sus2sus4" not in by_suffix] == ["Ab"]


def test_every_chord_in_the_repertoire_has_a_standard_shape():
    for path in sorted(Path(SONGS_DIR).glob("*.toml")):
        payload = chords_payload(load_song(path))
        for name, info in payload["chords"].items():
            assert info["guitar"], (path.stem, name)
            assert info["keys"] and info["notes"], (path.stem, name)


def test_vendoring_keeps_only_valid_shapes_with_absolute_frets(tmp_path):
    db = {
        "chords": {
            "C": [
                {
                    "suffix": "major",
                    "positions": [
                        {
                            "frets": [-1, 3, 2, 0, 1, 0],
                            "fingers": [0, 3, 2, 0, 1, 0],
                            "baseFret": 1,
                        },
                        {
                            "frets": [1, 1, 3, 3, 3, 1],
                            "fingers": [1, 1, 2, 3, 4, 1],
                            "baseFret": 3,
                            "barres": [1],
                        },
                        {
                            "frets": [-1, 3, 2, 0, 1, 1],
                            "fingers": [0, 3, 2, 0, 1, 1],
                            "baseFret": 1,
                        },
                    ],
                },
                {
                    "suffix": "7sg",
                    "positions": [{"frets": [0] * 6, "fingers": [0] * 6, "baseFret": 1}],
                },
            ]
        }
    }
    source = tmp_path / "guitar.json"
    source.write_text(json.dumps(db), encoding="utf-8")
    data = chordsdb.vendor(source, tmp_path / "out.json")
    positions = data["acordes"]["C"]["major"]
    assert [p["f"] for p in positions] == [[-1, 3, 2, 0, 1, 0], [3, 3, 5, 5, 5, 3]]
    assert positions[1]["b"] == [3]  # cejilla en el traste 3, no en el 1 relativo
    assert "7sg" not in data["acordes"]["C"]  # sufijo que no sabemos interpretar

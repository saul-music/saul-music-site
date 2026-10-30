"""Plantillas y validador de acordes: solo reglas, con datos sintéticos."""

import pytest

from musicsite import acordes
from musicsite.acordes import BASIC_CHORD, REPERTOIRE, init, main, validate, validate_file


def write(tmp_path, name, body):
    path = tmp_path / f"{name}.toml"
    path.write_text(body, encoding="utf-8")
    return path


GOOD = """
slug = "tema"
titulo = "Tema"
artista = "Artista"
tipo = "cancion"
tono = "Sol mayor"
cejilla = "Sin cejilla"
compas = "4/4"
bpm = 92
nivel = "inicial"
acordes = ["G", "D", "Em", "C"]

[[secciones]]
nombre = "Estrofa"
repeticiones = 2
compases = ["G", "%", "D", "Em", "C"]

[procedencia]
metodo = "de oído"
autor = "Persona del equipo"
fecha = "2026-10-30"

[revision]
revisado = true
v2_resuelto = false
"""


@pytest.mark.parametrize("chord", ["G", "Em", "C#m", "Bb", "F#", "Abm"])
def test_basic_chords_are_accepted(chord):
    assert BASIC_CHORD.match(chord)


@pytest.mark.parametrize("chord", ["G7", "Dsus4", "Am9", "Cadd9", "E5", "Gmaj7", "H", "", "g"])
def test_extended_or_invalid_chords_are_rejected(chord):
    assert not BASIC_CHORD.match(chord)


def test_repertoire_has_twenty_unique_slugs():
    slugs = [slug for slug, *_ in REPERTOIRE]
    assert len(slugs) == 20 and len(set(slugs)) == 20


def test_init_creates_templates_and_never_overwrites(tmp_path):
    created = init(tmp_path)
    assert len(created) == 20
    existing = tmp_path / "otra-era.toml"
    existing.write_text("# editado por una persona\n", encoding="utf-8")
    assert init(tmp_path) == []
    assert existing.read_text(encoding="utf-8") == "# editado por una persona\n"


def test_fresh_templates_are_valid_and_empty(tmp_path):
    init(tmp_path)
    reports = validate(tmp_path)
    assert len(reports) == 20
    assert all(report.status == "vacío" and not report.errors for report in reports)


def test_complete_file_is_reviewed_but_not_publishable_until_v2(tmp_path):
    report = validate_file(write(tmp_path, "tema", GOOD))
    assert report.errors == [] and report.status == "revisado"


def test_publishable_needs_v2_resolved(tmp_path):
    body = GOOD.replace("v2_resuelto = false", "v2_resuelto = true")
    assert validate_file(write(tmp_path, "tema", body)).status == "publicable"


def test_v2_cannot_be_resolved_without_review(tmp_path):
    body = GOOD.replace("revisado = true", "revisado = false").replace(
        "v2_resuelto = false", "v2_resuelto = true"
    )
    errors = validate_file(write(tmp_path, "tema", body)).errors
    assert any("v2_resuelto exige revisado" in error for error in errors)


def test_extension_chord_is_reported(tmp_path):
    body = GOOD.replace('acordes = ["G", "D", "Em", "C"]', 'acordes = ["G", "D", "Em", "G7"]')
    errors = validate_file(write(tmp_path, "tema", body)).errors
    assert any("«G7» no es un acorde básico" in error for error in errors)


def test_bar_must_use_declared_chords(tmp_path):
    body = GOOD.replace('compases = ["G", "%", "D", "Em", "C"]', 'compases = ["G", "A"]')
    errors = validate_file(write(tmp_path, "tema", body)).errors
    assert any("«A» no está en la lista de acordes" in error for error in errors)


def test_repeat_cannot_open_a_section(tmp_path):
    body = GOOD.replace('compases = ["G", "%", "D", "Em", "C"]', 'compases = ["%", "G"]')
    errors = validate_file(write(tmp_path, "tema", body)).errors
    assert any("no puede ser el primer compás" in error for error in errors)


def test_reviewed_requires_origin(tmp_path):
    body = GOOD.replace('autor = "Persona del equipo"', 'autor = ""')
    errors = validate_file(write(tmp_path, "tema", body)).errors
    assert any("procedencia («autor»)" in error for error in errors)


def test_slug_must_match_filename(tmp_path):
    errors = validate_file(write(tmp_path, "otro", GOOD)).errors
    assert any("no coincide con el nombre del archivo" in error for error in errors)


def test_invalid_toml_is_reported(tmp_path):
    report = validate_file(write(tmp_path, "tema", "esto no es toml ["))
    assert report.status == "inválido" and report.errors


def test_cli_exit_codes(tmp_path, capsys):
    assert main(["init", "--dir", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["validate", "--dir", str(tmp_path)]) == 0
    assert "20 archivos, 0 con errores" in capsys.readouterr().out
    write(tmp_path, "tema", GOOD.replace('"G", "D", "Em", "C"]', '"G7", "D", "Em", "C"]'))
    assert main(["validate", "--dir", str(tmp_path)]) == 1
    assert "21 archivos, 1 con errores" in capsys.readouterr().out


def test_module_reads_no_network_or_external_sites():
    source = acordes.__file__
    text = open(source, encoding="utf-8").read().lower()
    for word in ("http://", "https://", "urllib", "requests", "httpx", "socket"):
        assert word not in text


def test_parse_score_reads_compact_notation():
    sections, errors = acordes.parse_score("Intro x2: G Em\n# nota\n\nEstrofa: G % D\n")
    assert errors == []
    assert sections == [
        {"nombre": "Intro", "repeticiones": 2, "compases": ["G", "Em"]},
        {"nombre": "Estrofa", "repeticiones": 1, "compases": ["G", "%", "D"]},
    ]


def test_parse_score_reports_bad_lines():
    _, errors = acordes.parse_score("sin dos puntos")
    assert errors and "línea 1" in errors[0]


def test_compact_score_is_validated_like_sections(tmp_path):
    body = GOOD.split("[[secciones]]")[0] + "partitura = '''\nEstrofa x2: G % D Em G7\n'''\n\n"
    body += "[procedencia]" + GOOD.split("[procedencia]")[1]
    errors = validate_file(write(tmp_path, "tema", body)).errors
    assert any("«G7» no es un acorde básico" in error for error in errors)


def test_instrumental_without_stable_harmony_can_be_reviewed(tmp_path):
    body = (
        GOOD.split("acordes = ")[0].replace('tipo = "cancion"', 'tipo = "instrumental"')
        + "acordes = []\nsin_base_armonica = true\n\n[procedencia]"
        + GOOD.split("[procedencia]")[1]
    )
    assert validate_file(write(tmp_path, "tema", body)).errors == []

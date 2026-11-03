"""Contrato con el validador del admin de research (copia): mismos casos, mismos errores.

`tests/fixtures/acordes/contract.json` es idéntico al de `saul-music-research`; si una regla
cambia en un repo, se actualiza el archivo en los dos y esta prueba avisa si divergen."""

import json
from pathlib import Path

import pytest

from musicsite.acordes import validate_file

CONTRACT = json.loads((Path(__file__).parent / "fixtures/acordes/contract.json").read_text())
VALID = CONTRACT["valido"]["song"]
SLUG = "tema-de-prueba"


def toml_value(value):
    """JSON sirve para escalares; las tablas pasan a tabla en línea de TOML."""
    if isinstance(value, dict):
        return (
            "{ " + ", ".join(f"{json.dumps(k)} = {toml_value(v)}" for k, v in value.items()) + " }"
        )
    return json.dumps(value)


def to_toml(song: dict) -> str:
    """Solo para pruebas: valores simples y tablas de un nivel (JSON ya escapa como TOML)."""
    flat = [
        f"{key} = {json.dumps(value)}" for key, value in song.items() if not isinstance(value, dict)
    ]
    tables = [
        f"[{key}]\n" + "\n".join(f"{k} = {toml_value(v)}" for k, v in value.items())
        for key, value in song.items()
        if isinstance(value, dict)
    ]
    return "\n".join(flat) + "\n\n" + "\n\n".join(tables) + "\n"


def errors_of(tmp_path, song: dict):
    path = tmp_path / f"{SLUG}.toml"
    path.write_text(to_toml(song), encoding="utf-8")
    return validate_file(path)


def test_contract_valid_song(tmp_path):
    report = errors_of(tmp_path, VALID)
    assert (report.status, report.errors) == (CONTRACT["valido"]["status"], [])


@pytest.mark.parametrize("case", CONTRACT["casos"], ids=lambda c: json.dumps(c["cambio"])[:40])
def test_contract_cases(tmp_path, case):
    errors = errors_of(tmp_path, {**VALID, **case["cambio"]}).errors
    if "contiene" in case:
        assert any(case["contiene"] in error for error in errors), errors
    else:
        assert len(errors) == case["errores"], errors

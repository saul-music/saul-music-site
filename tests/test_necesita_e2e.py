"""scripts/necesita-e2e.sh (S48): los navegadores corren solo si cambia algo propio del sitio."""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "necesita-e2e.sh"
PYPROJECT = 'dependencies = [\n    "fastapi==1.0",\n    "saul-music-render==0.2.1",\n]\n'

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="sin git")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    (tmp_path / "uv.lock").write_text("version = 1\n")
    (tmp_path / "app.py").write_text("x = 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def needs(repo: Path, changes: dict[str, str]) -> str:
    for name, text in changes.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "cambio")
    out = subprocess.run(
        [str(SCRIPT), "HEAD~1..HEAD"], cwd=repo, check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def test_render_bump_with_docs_skips_the_browsers(repo):
    bump = PYPROJECT.replace("0.2.1", "0.3.0")
    changes = {"pyproject.toml": bump, "uv.lock": "version = 2\n", "docs/status.md": "x\n"}
    assert needs(repo, changes) == "false"


def test_site_code_runs_the_browsers(repo):
    assert needs(repo, {"app.py": "x = 2\n"}) == "true"


def test_e2e_tests_run_the_browsers(repo):
    assert needs(repo, {"tests/e2e/test_x.py": "pass\n"}) == "true"


def test_another_dependency_runs_the_browsers(repo):
    other = PYPROJECT.replace("fastapi==1.0", "fastapi==2.0")
    assert needs(repo, {"pyproject.toml": other, "uv.lock": "version = 2\n"}) == "true"

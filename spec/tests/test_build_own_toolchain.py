"""build.sh compiles this checkout's library with this checkout's code (#561).

Every build stage runs a tool by path, which puts `spec/tools/portrayal` on
sys.path[0] and leaves `import portrayal` to the editable install, which is
whichever checkout ran `pip install -e .`. That compiler then succeeds against
the local library and the build exits 0, so the exit code gives no signal.
`spec/tools/toolchain.sh` pins the path and refuses a foreign answer. These tests
put a decoy `portrayal` in the way and check both halves.

CI installs from the checkout it tests, so the defect cannot show there on its
own. Hence the decoy.
"""
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
HELPER = ROOT / "spec/tools/toolchain.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def decoy(tmp_path):
    d = tmp_path / "foreign"
    (d / "portrayal").mkdir(parents=True)
    (d / "portrayal/__init__.py").write_text("")
    return d


def run(cwd, script, pythonpath, **extra):
    env = {**os.environ, "PYTHONPATH": str(pythonpath), **extra}
    return subprocess.run(["bash", "-c", f"set -euo pipefail\n{script}"], cwd=cwd,
                          env=env, capture_output=True, text=True, timeout=60)


# What a by-path tool sees: its own directory at sys.path[0].
BY_PATH = ('python3 -c "import sys; sys.path[0] = \'spec/tools/portrayal\'; '
           'import portrayal; print(portrayal.__file__)"')


def test_a_by_path_tool_imports_this_checkout_even_past_a_foreign_one(tmp_path):
    """The common case made right. The decoy stands in for the other worktree
    and is on the caller's PYTHONPATH, so it would win without the pin."""
    r = run(ROOT, f". spec/tools/toolchain.sh\n{BY_PATH}", decoy(tmp_path))
    assert r.returncode == 0, r.stderr
    got = pathlib.Path(r.stdout.strip()).resolve()
    assert got == (ROOT / "spec/tools/portrayal/__init__.py").resolve(), got


def test_the_guard_stops_the_build_when_portrayal_resolves_elsewhere(tmp_path):
    """The broken case made loud. The copied checkout's `portrayal` has no
    `__init__.py`, so the pinned path holds only a namespace portion and the
    decoy's regular package beats it. That is a foreign answer, and the build
    must stop at the helper and name both paths."""
    fake = tmp_path / "checkout"
    (fake / "spec/tools/portrayal").mkdir(parents=True)
    shutil.copy(HELPER, fake / "spec/tools/toolchain.sh")
    foreign = decoy(tmp_path)
    r = run(fake, ". spec/tools/toolchain.sh\necho REACHED", foreign)
    assert r.returncode != 0, r.stdout
    assert "REACHED" not in r.stdout
    assert "refusing to build" in r.stderr, r.stderr
    assert str(foreign.resolve() / "portrayal") in r.stderr, r.stderr
    assert str((fake / "spec/tools/portrayal").resolve()) in r.stderr, r.stderr


def test_the_guard_passes_a_correct_build_under_pythonsafepath(tmp_path):
    """PYTHONSAFEPATH drops the '' that `python3 -c` would put first, so
    sys.path[0] is the pin itself. A guard that overwrote sys.path[0] deleted the
    pin it was checking and refused a build whose stages resolve correctly."""
    env = {"PYTHONSAFEPATH": "1"}
    r = run(ROOT, ". spec/tools/toolchain.sh\necho REACHED", decoy(tmp_path), **env)
    assert r.returncode == 0, r.stderr
    assert "REACHED" in r.stdout


@pytest.mark.parametrize("script", ["build.sh", "publish.sh"])
def test_the_entry_points_source_it_before_any_python(script):
    """Before the first python3 line, and exactly once. A stage placed above the
    helper would run the installed compiler again."""
    lines = [ln.strip() for ln in (ROOT / script).read_text().splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    src = [i for i, ln in enumerate(lines) if ln == ". spec/tools/toolchain.sh"]
    assert len(src) == 1, src
    py = [i for i, ln in enumerate(lines) if "python3" in ln]
    assert py, f"{script} runs no python3, so this test measured nothing"
    assert src[0] < py[0], (lines[src[0]], lines[py[0]])

"""`python -m portrayal` answers for the checkout you are in, or refuses (#346).

`__main__` found the repository from the imported package. An editable install
points at whichever checkout ran `pip install -e .` - often another worktree -
so `lint`, `lock` and `test` run inside worktree B reported on worktree A, and
said "no change against the baseline" about a change they never read. The
build scripts were fixed the same way in #615 (spec/tools/toolchain.sh); this
is the driver's half.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from portrayal import __main__ as driver

ROOT = Path(__file__).resolve().parents[2]


def fake_checkout(tmp_path):
    """A directory that looks like another Portrayal checkout."""
    other = tmp_path / "other-worktree"
    (other / "library").mkdir(parents=True)
    (other / "spec/tools/portrayal").mkdir(parents=True)
    return other


def test_a_gate_refuses_to_report_on_another_checkout(tmp_path):
    """Run from inside checkout B while `portrayal` imports from this one - the
    exact mismatch an editable install makes. It stops, names both trees and
    says how to run it on the one you are in."""
    other = fake_checkout(tmp_path)
    r = subprocess.run([sys.executable, "-m", "portrayal", "lint"], cwd=other / "library",
                       env={**os.environ, "PYTHONPATH": str(ROOT / "spec/tools")},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert str(other) in r.stderr and str(ROOT) in r.stderr, r.stderr
    assert f"PYTHONPATH={other / 'spec/tools'}" in r.stderr, r.stderr


@pytest.fixture
def ran(monkeypatch):
    calls = []
    monkeypatch.setattr(driver.subprocess, "call",
                        lambda argv, cwd=None, env=None: calls.append((argv, cwd, env)) or 0)
    return calls


def test_from_its_own_checkout_the_gate_runs_on_that_tree(ran, monkeypatch):
    monkeypatch.chdir(ROOT / "spec")
    assert driver.main(["lint"]) == 0
    [(argv, cwd, env)] = ran
    assert Path(cwd) == ROOT
    # and the gate's own process imports this tree first, whatever else is installed
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(ROOT / "spec/tools")


def test_from_outside_any_checkout_the_imported_one_answers(ran, monkeypatch, tmp_path):
    """Nothing to disagree with: no checkout contains the directory, so the one
    the package lives in is the only answer, as before."""
    monkeypatch.chdir(tmp_path)
    assert driver.main(["lock"]) == 0
    assert Path(ran[0][1]) == ROOT

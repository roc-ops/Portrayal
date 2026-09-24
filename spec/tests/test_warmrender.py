"""warmrender answers exactly what a cold `python render.py` answers.

The B3 tests build through warmrender.run, a fork of a server that has already
parsed the library, instead of a fresh interpreter per render (see its
docstring for the cost). That is only a saving if nothing else changes, so the
claim is checked here against a real subprocess, both ways, on every output:
the same files byte for byte, the same stdout and stderr, the same status - on
a real device that builds, on one that fails with the renderer's own message,
and on one that fails with a traceback.
"""
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import warmrender

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"

needs_fork = pytest.mark.skipif(not hasattr(__import__("os"), "fork"),
                                reason="no fork: warmrender is subprocess.run here")


def _both(tmp_path, dev, *extra):
    """(warm result, cold result), each rendering `dev` into its own `out`
    - and the same path text in both, so stdout and stderr compare whole."""
    got = {}
    for how in ("warm", "cold"):
        out = tmp_path / "out"
        cmd = [sys.executable, str(RENDER), str(dev), "--library", str(LIB),
               "--out", str(out), *extra]
        run = warmrender.run if how == "warm" else subprocess.run
        got[how] = run(cmd, capture_output=True, text=True)
        if out.exists():
            out.rename(tmp_path / how)
    return got["warm"], got["cold"]


@needs_fork
def test_a_real_build_is_the_same_files_and_the_same_words(tmp_path):
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp_path / "src") / "device.yaml"
    warm, cold = _both(tmp_path, dev)
    assert cold.returncode == 0, cold.stderr[-800:]
    assert (warm.returncode, warm.stdout, warm.stderr) == (cold.returncode, cold.stdout, cold.stderr)
    files = sorted(p.name for p in (tmp_path / "cold").iterdir())
    assert len(files) > 4 and sorted(p.name for p in (tmp_path / "warm").iterdir()) == files
    same, diff, errs = filecmp.cmpfiles(tmp_path / "warm", tmp_path / "cold", files, shallow=False)
    assert (diff, errs) == ([], []) and same == files


@needs_fork
@pytest.mark.parametrize("edit,says", [
    (lambda t: t.replace("fs/fhd-1mtp6lcd-os2-a@", "fs/no-such-cassette@"),
     "component ref not found"),
    (lambda t: "", "Traceback (most recent call last)"),
], ids=["a missing ref", "a traceback"])
def test_a_failed_build_fails_the_same_way(tmp_path, edit, says):
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp_path / "src") / "device.yaml"
    dev.write_text(edit(dev.read_text()))
    warm, cold = _both(tmp_path, dev)
    assert cold.returncode != 0 and says in cold.stderr, cold.stderr[-800:]
    assert (warm.returncode, warm.stdout, warm.stderr) == (cold.returncode, cold.stdout, cold.stderr)


def test_the_cold_switch_and_anything_else_is_a_real_subprocess(monkeypatch):
    """A command that is not a portrayal tool, and every command under
    PORTRAYAL_TESTS_COLD_RENDER, goes to subprocess.run unchanged."""
    seen = []
    monkeypatch.setattr(warmrender.subprocess, "run", lambda cmd, **kw: seen.append(cmd))
    warmrender.run(["node", "--version"], capture_output=True, text=True)
    monkeypatch.setenv("PORTRAYAL_TESTS_COLD_RENDER", "1")
    warmrender.run([sys.executable, str(RENDER), "x.yaml"], capture_output=True, text=True)
    assert seen == [["node", "--version"], [sys.executable, str(RENDER), "x.yaml"]]

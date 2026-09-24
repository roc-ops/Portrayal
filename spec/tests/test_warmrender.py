"""warmrender answers exactly what a cold `python render.py` answers.

The B3 tests build through warmrender.run, a fork of a server that has already
parsed the library, instead of a fresh interpreter per render (see its
docstring for the cost). That is only a saving if nothing else changes, so the
claim is checked here against a real subprocess, both ways, on every output:
the same files byte for byte, the same stdout and stderr, the same status - on
a real device that builds, on one that fails with the renderer's own message,
on one that fails with a traceback, and on `python -m portrayal.components_index`
failing with a traceback of its own.

EACH WARM HALF PROVES IT RAN WARM. A comparison of cold with cold passes too,
and it would, silently, the day `_target` or `_same_portrayal` stopped matching
- so during the warm half `subprocess.run` is made to raise, the cold switch is
removed from the environment, and the server must report one more call served.
"""
import filecmp
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import warmrender

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"

needs_fork = pytest.mark.skipif(not hasattr(os, "fork"),
                                reason="no fork: warmrender is subprocess.run here")


def _no_subprocess(*a, **kw):
    raise AssertionError("the warm half fell back to subprocess.run")


def warm(monkeypatch, cmd):
    """warmrender.run(cmd), refusing any way of answering but the server."""
    with monkeypatch.context() as m:
        m.delenv("PORTRAYAL_TESTS_COLD_RENDER", raising=False)
        m.setattr(warmrender.subprocess, "run", _no_subprocess)
        before = warmrender._SERVER.served if warmrender._SERVER else 0
        if warmrender._SERVER is not None and warmrender._SERVER.p.poll() is not None:
            before = 0                      # a dead server is replaced by a new one
        r = warmrender.run(cmd, capture_output=True, text=True)
    srv = warmrender._SERVER
    assert srv is not None and srv.p.poll() is None, "no live warm server answered"
    assert srv.served == before + 1, "the warm server did not serve this call"
    return r


def _both(monkeypatch, tmp_path, cmd_for):
    """(warm result, cold result) for `cmd_for(out)`, each into its own `out`
    and renamed after - the same path text in both, so stdout and stderr
    compare whole."""
    got = {}
    for how in ("warm", "cold"):
        out = tmp_path / "out"
        cmd = cmd_for(out)
        got[how] = (warm(monkeypatch, cmd) if how == "warm"
                    else subprocess.run(cmd, capture_output=True, text=True))
        if out.exists():
            out.rename(tmp_path / how)
    return got["warm"], got["cold"]


def _render(dev, *extra):
    return lambda out: [sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(out), *extra]


@needs_fork
def test_a_real_build_is_the_same_files_and_the_same_words(monkeypatch, tmp_path):
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp_path / "src") / "device.yaml"
    w, cold = _both(monkeypatch, tmp_path, _render(dev))
    assert cold.returncode == 0, cold.stderr[-800:]
    assert (w.returncode, w.stdout, w.stderr) == (cold.returncode, cold.stdout, cold.stderr)
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
def test_a_failed_build_fails_the_same_way(monkeypatch, tmp_path, edit, says):
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp_path / "src") / "device.yaml"
    dev.write_text(edit(dev.read_text()))
    w, cold = _both(monkeypatch, tmp_path, _render(dev))
    assert cold.returncode != 0 and says in cold.stderr, cold.stderr[-800:]
    assert (w.returncode, w.stdout, w.stderr) == (cold.returncode, cold.stdout, cold.stderr)


@needs_fork
def test_a_failed_module_run_fails_the_same_way(monkeypatch, tmp_path):
    """`python -m portrayal.components_index` over a root holding a contract
    that is not YAML: the same status and the same traceback, `<frozen runpy>`
    frames and all."""
    bad = tmp_path / "lib" / "components" / "test" / "bad" / "v1" / "contract.yaml"
    bad.parent.mkdir(parents=True)
    bad.write_text("name: bad\n: x: [\n")
    w, cold = _both(monkeypatch, tmp_path, lambda out: [
        sys.executable, "-m", "portrayal.components_index",
        "--library", str(tmp_path / "lib"), "--library", str(LIB), "--out", str(out)])
    assert cold.returncode != 0, cold.stderr[-800:]
    assert "Traceback (most recent call last)" in cold.stderr and "<frozen runpy>" in cold.stderr
    assert (w.returncode, w.stdout, w.stderr) == (cold.returncode, cold.stdout, cold.stderr)


def test_the_cold_switch_and_anything_else_is_a_real_subprocess(monkeypatch):
    """A command that is not a portrayal tool, a PYTHONHASHSEED the fork could
    not honour, and every command under PORTRAYAL_TESTS_COLD_RENDER go to
    subprocess.run unchanged."""
    seen = []
    monkeypatch.setattr(warmrender.subprocess, "run", lambda cmd, **kw: seen.append(cmd))
    tool = [sys.executable, str(RENDER), "x.yaml"]
    warmrender.run(["node", "--version"], capture_output=True, text=True)
    warmrender.run(tool, capture_output=True, text=True,
                   env={**os.environ, "PYTHONHASHSEED": "7"})
    monkeypatch.setenv("PORTRAYAL_TESTS_COLD_RENDER", "1")
    warmrender.run(tool, capture_output=True, text=True)
    assert seen == [["node", "--version"], tool, tool]

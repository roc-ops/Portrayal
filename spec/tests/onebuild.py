"""One run per test session of the things many tests each ran for themselves.

WHAT IT COST. Four tests linted the whole library, three of them with the same
command, at about 45 seconds a time; and sixteen fixtures across fourteen files
each ran the component indexer over the whole library, at about six. Every one
of them was right to want the real thing rather than `library/dist` - a stale
dist is a stale answer, and nothing about the test would say so - and none of
them needed a run of its own to get it.

WHAT THIS KEEPS. The lint and the index a test reads are still built IN THIS
SESSION, FROM THIS TREE, BY THE BUILD'S OWN TOOLS - the same command lines the
tests ran before. Nothing here reads `library/dist`. The only change is that
the second test to ask is handed what the first one built.

ACROSS WORKERS TOO. Under xdist a module-scoped fixture runs once per worker
that is given one of the module's tests, so "once per module" was already up to
once per worker. The result lives in a directory every worker shares (conftest
names it in PORTRAYAL_TEST_SHARED), behind a file lock: the first to ask
builds, the rest wait and read.

THE TESTS THAT READ THE LINT RUN SHARE A WORKER, and that is the other half of
the saving. A test that asks while the lint is still running waits for it, and
a waiting worker is an idle core: three tests waiting side by side cost the
same wall clock as three lints. They carry `xdist_group("full-lint")`, and
pyproject asks for `--dist loadgroup`, so one worker runs the lint and reads it
twice more while the others carry on. The index needs no group - its readers
are spread through the run, and the wait is at most one six-second build.

A FAILED BUILD IS NOT KEPT. `make` writes into a scratch directory that is
renamed into place only when it returns, so a build that raises leaves nothing
behind and the next test to ask runs it again and fails the same way, with the
same message.

READ-ONLY, like libdata: `components_index()` is shared, so a test that wants
to write beside the index takes its own copy with `components_index_into`.
"""
import atexit
import contextlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types

import warmrender

try:
    import fcntl
except ImportError:          # no flock: each process builds for itself
    fcntl = None

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = ROOT / "spec"
LIB = ROOT / "library"

_OWN = None


def _shared():
    """The session's shared directory, or this process's own when a test file
    is run without conftest's fixture having named one."""
    global _OWN
    named = os.environ.get("PORTRAYAL_TEST_SHARED")
    if named and fcntl is not None:
        d = pathlib.Path(named)
        d.mkdir(parents=True, exist_ok=True)
        return d
    if _OWN is None:
        # NOT UNDER PYTEST'S BASETEMP, so nothing else will remove it: a copy
        # of the index is tens of megabytes, and one left per process per run
        # is how a shared temp directory fills.
        _OWN = pathlib.Path(tempfile.mkdtemp(prefix="portrayal-onebuild-"))
        atexit.register(shutil.rmtree, _OWN, ignore_errors=True)
    return _OWN


@contextlib.contextmanager
def _locked(path):
    if fcntl is None:
        yield
        return
    with open(path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def once(name, make):
    """The directory `make(dir)` filled, built at most once per session."""
    root = _shared()
    done = root / name
    with _locked(root / f"{name}.lock"):
        if not done.is_dir():
            scratch = root / f"{name}.building"
            shutil.rmtree(scratch, ignore_errors=True)
            scratch.mkdir()
            make(scratch)
            scratch.rename(done)
    return done


def full_lint():
    """The whole library linted, as `lint.py --schemas ... --library ...` with no
    other argument: `.returncode`, `.stdout`, `.stderr`."""
    def make(d):
        r = subprocess.run([sys.executable, str(SPEC / "tools/portrayal/lint.py"),
                            "--schemas", str(SPEC / "schemas"), "--library", str(LIB)],
                           capture_output=True, text=True)
        (d / "lint.json").write_text(json.dumps(
            {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}))
    return types.SimpleNamespace(**json.loads((once("full-lint", make) / "lint.json").read_text()))


def components_index():
    """`components.json` and every compiled skin, as the indexer the build runs
    writes them for this library. SHARED: read it, do not write into it."""
    def make(d):
        r = warmrender.run([sys.executable, "-m", "portrayal.components_index",
                            "--library", str(LIB), "--out", str(d)],
                           capture_output=True, text=True,
                           env={**os.environ, "PYTHONPATH": str(SPEC / "tools")})
        assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
        assert json.loads((d / "components.json").read_text())["components"], \
            "the indexer published no component at all"
    return once("components-index", make)


def components_index_into(out):
    """A private copy of the index at `out`, for a test that renders beside it
    or hands the directory to a tool that may write there."""
    shutil.copytree(components_index(), out, dirs_exist_ok=True)
    return pathlib.Path(out)

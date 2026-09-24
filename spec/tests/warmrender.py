"""`subprocess.run` for the build's own tools, from a process that has already
read the library.

WHAT IT COST. A render of one device is about 2.5 CPU seconds, and 95% of that
is not rendering: `capability.report` asks lint for the device's derived gaps,
L62's `_id_corpus` reads every contract in the library to learn its vocabulary,
and so each `render.py` a test spawned parsed all 694 contracts before drawing
anything (render_view itself is 0.07s of a 6.3s profiled run). The B3 tests
spawn a few hundred of them, and that parse was most of the ~6 minutes they
added to CI's `tests` step - the step that went over the job's 30 minutes.

WHAT THIS DOES INSTEAD. One server per pytest worker imports the tools and
parses the library ONCE, through `manifest.load_yaml` - the build's own cache,
keyed by (path, mtime_ns). Each call then FORKS that server: the child is a
fresh copy of a process that has read the library and done nothing else, and it
runs the tool exactly as `python <tool> args...` would - `runpy` executes the
script as `__main__` with `sys.argv` set, its stdout and stderr on files, stdin
on /dev/null, in the caller's cwd and environment - and exits with the status
the interpreter would have: 0, SystemExit's code, or 1 after printing a
traceback. The caller gets a `subprocess.CompletedProcess` back.

WHY IT IS STILL A REAL BUILD, AND NOT AN IN-PROCESS SHORTCUT:

  - NO STATE CROSSES BETWEEN CALLS. Every render is a new child and every child
    exits, so nothing one render leaves in a module global - lint's per-ref
    caches, `_ID_VOCAB_CACHE`, `_SLOT_CORE`, a mutated parse - reaches the next.
    Calling `render.main()` inside the test process would share all of those
    with every lint test the worker has run (lint.main fills `STANDARDS`, which
    a fresh render never has), and that is the difference a fork keeps out.
  - THE ONLY THING A CHILD INHERITS BEYOND A FRESH INTERPRETER is the parse of
    each unchanged library file, keyed by its mtime: exactly the document a
    cold `load_yaml` would have returned. A tmp copy a test writes is a
    different path, so it is parsed fresh in the child.
  - THE SAME CODE RUNS. The script is executed from its file, as `__main__`,
    so `_cli()` and its error handling are what a test sees, and a tool test
    that asserts on stderr or a non-zero status still asserts on the real ones.

Anything this cannot serve faithfully falls back to a real `subprocess.run`: a
platform without `fork`, a command that is not `python <portrayal tool>` or
`python -m portrayal.<tool>`, a keyword this does not model, or an environment
whose PYTHONPATH would import a different `portrayal` than the server did.

PORTRAYAL_TESTS_COLD_RENDER=1 sends every call to `subprocess.run` instead, so
a suspicion that the server changed an answer is one run away from settled.
"""
import atexit
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
TOOLS = ROOT / "spec" / "tools"
SCHEMAS = ROOT / "spec" / "schemas"

_SERVER = None


# --- the client --------------------------------------------------------------------

def _target(cmd):
    """("path", script) or ("module", name) for a python invocation of a
    portrayal tool, else None."""
    if len(cmd) < 2 or str(cmd[0]) != sys.executable:
        return None
    if str(cmd[1]) == "-m":
        mod = str(cmd[2]) if len(cmd) > 2 else ""
        return ("module", mod, 3) if mod.startswith("portrayal.") else None
    script = Path(str(cmd[1]))
    if script.suffix == ".py" and script.is_file() \
            and script.resolve().parent == _package_dir():
        return ("path", str(script), 2)
    return None


def _package_dir():
    import portrayal
    return Path(portrayal.__file__).resolve().parent


def _same_portrayal(env):
    """Whether `env` would import the portrayal package the server imported."""
    if env is None:
        return True
    pp = env.get("PYTHONPATH")
    if pp == os.environ.get("PYTHONPATH"):
        return True
    for entry in (pp or "").split(os.pathsep):
        if entry and (Path(entry) / "portrayal" / "__init__.py").is_file():
            return (Path(entry) / "portrayal").resolve() == _package_dir()
    return False


def run(cmd, *, capture_output=False, text=False, env=None, cwd=None, **kw):
    """`subprocess.run(cmd, capture_output=True, text=True, env=..., cwd=...)`,
    served by a fork of the warm server when `cmd` runs a portrayal tool."""
    target = _target(cmd)
    if (kw or not (capture_output and text) or target is None
            or os.environ.get("PORTRAYAL_TESTS_COLD_RENDER")
            or not hasattr(os, "fork") or not _same_portrayal(env)):
        return subprocess.run(cmd, capture_output=capture_output, text=text,
                              env=env, cwd=cwd, **kw)
    kind, what, n = target
    with tempfile.TemporaryDirectory(prefix="warmrender-") as d:
        out, err = Path(d) / "stdout", Path(d) / "stderr"
        req = {"kind": kind, "what": what, "argv": [str(a) for a in cmd[n:]],
               "cwd": str(cwd) if cwd is not None else os.getcwd(),
               "env": dict(env if env is not None else os.environ),
               "stdout": str(out), "stderr": str(err)}
        code = _server().call(req)
        return subprocess.CompletedProcess(
            [str(c) for c in cmd], code,
            out.read_text(errors="replace") if out.exists() else "",
            err.read_text(errors="replace") if err.exists() else "")


class _Server:
    def __init__(self):
        self.p = subprocess.Popen([sys.executable, __file__, "--serve"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, cwd=str(ROOT))
        ready = self.p.stdout.readline()
        try:
            served = json.loads(ready)["ready"]
        except (ValueError, KeyError, TypeError):
            raise RuntimeError(f"warmrender server did not start: {ready!r}") from None
        # the server must have imported the package this process would hand a
        # subprocess, or its answers are about some other tree
        if Path(served) != _package_dir():
            raise RuntimeError(f"warmrender server imported {served}, not {_package_dir()}")

    def call(self, req):
        self.p.stdin.write(json.dumps(req) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("warmrender server exited")
        return json.loads(line)["returncode"]

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def _server():
    global _SERVER
    if _SERVER is None or _SERVER.p.poll() is not None:
        _SERVER = _Server()
        atexit.register(_SERVER.close)
    return _SERVER


# --- the server --------------------------------------------------------------------

def _warm():
    """Import the tools and parse every library and schema YAML once, through
    the build's own cache. Nothing else: no rule runs, no global is filled."""
    import portrayal.capability  # noqa: F401
    import portrayal.lint  # noqa: F401
    import portrayal.render  # noqa: F401
    from portrayal.manifest import load_yaml
    for sub in ("components", "devices", "labs"):
        for f in sorted((LIB / sub).rglob("*.yaml")):
            load_yaml(f)
    for f in sorted(SCHEMAS.glob("*.yaml")):
        load_yaml(f)


def _child(req):
    """Become `python <tool> argv...` and never return."""
    import runpy
    import traceback
    code = 1
    try:
        os.chdir(req["cwd"])
        os.environ.clear()
        os.environ.update(req["env"])
        null = os.open(os.devnull, os.O_RDONLY)
        os.dup2(null, 0)
        for fd, path in ((1, req["stdout"]), (2, req["stderr"])):
            f = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            os.dup2(f, fd)
            os.close(f)
        sys.stdin = open(0, "r", closefd=False)
        sys.stdout = open(1, "w", encoding="utf-8", closefd=False)
        sys.stderr = open(2, "w", encoding="utf-8", errors="backslashreplace", closefd=False)
        code = 0
        # sys.path[0] is what the interpreter would have put there: the
        # script's directory, or the cwd for `-m`. The server's own entry
        # (this directory) is replaced, not kept.
        sys.argv = [req["what"], *req["argv"]]
        if req["kind"] == "path":
            # the interpreter runs a script from its absolute path
            main = os.path.abspath(req["what"])
            sys.path[0] = os.path.dirname(main)
        else:
            # `-m` finds the module first, and it is not imported until it runs
            import importlib.util
            sys.path[0] = os.getcwd()
            sys.modules.pop(req["what"], None)
            main = importlib.util.find_spec(req["what"]).origin
        try:
            if req["kind"] == "path":
                runpy.run_path(main, run_name="__main__")
            else:
                runpy.run_module(req["what"], run_name="__main__", alter_sys=True)
        except SystemExit as e:
            # what the interpreter does with an uncaught SystemExit
            if e.code is None:
                code = 0
            elif isinstance(e.code, int):
                code = e.code
            else:
                print(e.code, file=sys.stderr)
                code = 1
        except BaseException as e:
            # the traceback the interpreter prints: from the tool's own frame,
            # not from this function's call into runpy
            tb = e.__traceback__
            while tb is not None and tb.tb_frame.f_code.co_filename != main:
                tb = tb.tb_next
            traceback.print_exception(type(e), e, tb or e.__traceback__)
            code = 1
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os._exit(code & 0xFF)


def serve():
    _warm()
    sys.stdout.write(json.dumps({"ready": str(_package_dir())}) + "\n")
    sys.stdout.flush()
    for line in sys.stdin:
        req = json.loads(line)
        pid = os.fork()
        if pid == 0:
            _child(req)
        _pid, status = os.waitpid(pid, 0)
        sys.stdout.write(json.dumps({"returncode": os.waitstatus_to_exitcode(status)}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__" and sys.argv[1:] == ["--serve"]:
    serve()

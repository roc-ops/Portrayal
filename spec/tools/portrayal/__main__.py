"""`python -m portrayal <gate>` - the gates, without remembering a path.

WHY A DRIVER AT ALL. The gates are `./build.sh`, `./publish.sh` and two long
`python3 spec/tools/portrayal/...` invocations, and a contributor's first
problem was knowing they existed and what order they run in. CONTRIBUTING says
so, and so does this, from inside the thing they just installed (#178).

IT WRAPS THE SHELL SCRIPTS RATHER THAN REPLACING THEM. `build.sh` runs one
renderer process per device under `xargs -P` and waits on six indexer pids by
hand; reimplementing that here would be a second copy of the build, which is the
failure this repository has a whole page about. So the scripts stay the build
and this stays a door to it - which makes the gates macOS and Linux only, and
README and CONTRIBUTING say so rather than leaving it to be discovered.
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys

# THE REPOSITORY, FOUND FROM THE PACKAGE. An editable install leaves the package
# inside the checkout, so this resolves; a wheel installed somewhere else does
# not carry `library/` or the shell scripts at all, and saying that plainly beats
# a FileNotFoundError three frames down.
ROOT = pathlib.Path(__file__).resolve().parents[3]



def checkout_of(path):
    """The Portrayal checkout `path` is in - the nearest directory at or above
    it holding both `library/` and `spec/tools/portrayal/` - or None."""
    for d in [path, *path.parents]:
        if (d / "library").is_dir() and (d / "spec/tools/portrayal").is_dir():
            return d
    return None


GATES = {
    "lint": ("python", ["-m", "portrayal.lint", "--schemas", "spec/schemas",
                        "--library", "library"]),
    "lock": ("python", ["-m", "portrayal.devicelock", "--library", "library"]),
    "build": ("script", ["./build.sh"]),
    "publish": ("script", ["./publish.sh"]),
    "test": ("python", ["-m", "pytest", "spec/tests", "-q"]),
}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m portrayal",
        description="Run a Portrayal gate from the repository root.",
        epilog="The order CONTRIBUTING gives is: lint, lock, build (or publish), test.")
    p.add_argument("gate", choices=sorted(GATES))
    p.add_argument("rest", nargs=argparse.REMAINDER,
                   help="arguments passed straight through to the gate")
    args = p.parse_args(argv)

    if not (ROOT / "library").is_dir():
        p.error(f"no library/ under {ROOT} - the gates run against a checkout, "
                "and this looks like an installed copy without one. Clone the "
                "repository and `pip install -e .` from inside it.")

    # THE CHECKOUT YOU ARE IN IS THE ONE THAT ANSWERS, OR NONE DOES (#346).
    # ROOT is where the imported package lives: an editable install points at
    # whichever checkout ran `pip install -e .`, often another worktree, and
    # `lint`, `lock` and `test` then reported on that tree - "no change
    # against the baseline" about a change they never read. Run from inside a
    # different checkout, this stops and says which is which. Run from outside
    # any checkout, ROOT is the only answer and is used, as before.
    here = checkout_of(pathlib.Path.cwd().resolve())
    if here is not None and here != ROOT:
        print(f"python -m portrayal: refusing to run {args.gate!r}.\n"
              f"  you are in the checkout  {here}\n"
              f"  but portrayal imports from {ROOT}\n"
              f"so the gate would report on the other tree. Run it with this "
              f"checkout's tools first on the path:\n"
              f"  PYTHONPATH={here / 'spec/tools'} python -m portrayal {args.gate}",
              file=sys.stderr)
        return 2

    kind, cmd = GATES[args.gate]
    if kind == "script":
        if os.name == "nt":
            p.error(f"{cmd[0]} is a shell script; the build gates are macOS and "
                    "Linux only. `lint`, `lock` and `test` are pure Python and "
                    "run anywhere.")
        if not shutil.which("bash"):
            p.error("bash is not on PATH, and the build gates are shell scripts")
        argv_ = ["bash", *cmd]
    else:
        argv_ = [sys.executable, *cmd]
    # and the gate's own processes import the same tree, whatever else is
    # installed: a child that re-resolved `portrayal` could drift again
    env = {**os.environ,
           "PYTHONPATH": os.pathsep.join(filter(None, [str(ROOT / "spec/tools"),
                                                       os.environ.get("PYTHONPATH")]))}
    return subprocess.call([*argv_, *args.rest], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())

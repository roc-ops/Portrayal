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
    return subprocess.call([*argv_, *args.rest], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())

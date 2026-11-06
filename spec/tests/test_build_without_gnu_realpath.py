"""The overlay branch of build.sh runs where `realpath` has no `-m`.

`-m` (resolve a path that does not exist yet) is GNU coreutils. The `realpath`
macOS ships refuses it, so the overlay build has to resolve its output folder
another way: through python3, which the build already needs
(CONTRIBUTING.md, "An overlay library").

This holds the Linux path only. A `realpath` that refuses `-m` as macOS's does is
put first on PATH, and the overlay branch must get past the line that used to
call it. It does not prove a build on macOS.
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "spec" / "tests" / "fixtures" / "overlay-example"

# behaves as macOS's realpath does: no -m, everything else as the system one
REALPATH = """#!/bin/sh
if [ "$1" = "-m" ]; then
  echo "realpath: illegal option -- m" >&2
  exit 1
fi
exec /usr/bin/realpath "$@"
"""


def test_the_overlay_branch_does_not_call_realpath_with_m(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "realpath"
    shim.write_text(REALPATH)
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    overlay = tmp_path / "overlay"
    shutil.copytree(FIXTURE, overlay)
    # inside library/, so the script's own check refuses it before anything is built
    out = ROOT / "library" / "dist-overlay-test"
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    r = subprocess.run(
        ["bash", str(ROOT / "build.sh"), "--overlay-library", str(overlay),
         "--overlay-out", str(out)],
        capture_output=True, text=True, timeout=120, cwd=ROOT, env=env)
    assert "realpath: illegal option" not in r.stderr, r.stderr[-2000:]
    assert r.returncode == 2, r.stdout[-2000:] + r.stderr[-2000:]
    assert "must be a folder of its own" in r.stderr, r.stderr[-2000:]
    assert not out.exists()

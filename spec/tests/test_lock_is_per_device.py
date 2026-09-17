"""A device's fingerprint travels in that device's directory.

The lock was one 906 KB alphabetically sorted JSON file, and every device PR
inserted a 74-996 line entry into it (median 279). Cross-vendor inserts merged
cleanly; **two same-vendor devices that sort adjacently conflicted in JSON the
contributor never wrote**, and a component version bump rewrote the entry of
every device that seats it - which is why the RJ45 family change needed ten
stacked PRs, roc-ops/Portrayal#131-#140 (#182).

Three things this holds: the per-device file is the source, `--update` touches
only what moved, and the one-file view is a BUILD OUTPUT that cannot drift
because it is derived.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

from portrayal import devicelock as dl   # noqa: E402
from portrayal import libwalk            # noqa: E402


def test_every_device_carries_its_own_lock():
    missing = [dl.slug(p, LIB) for p in libwalk.iter_devices([LIB])
               if not dl.lock_path(LIB, dl.slug(p, LIB)).exists()]
    assert not missing, f"no device.lock.json for: {missing}"


def test_no_device_lock_is_orphaned():
    """A device that is gone takes its lock with it. With one file this was a
    key to delete; now it is a file, and one left behind fingerprints a device
    that no longer exists."""
    live = {dl.slug(p, LIB) for p in libwalk.iter_devices([LIB])}
    orphans = [str(f.relative_to(LIB)) for f in sorted(LIB.glob("devices/*/*/device.lock.json"))
               if f"{f.parent.parent.name}/{f.parent.name}" not in live]
    assert not orphans, orphans


def test_the_single_file_is_gone_from_the_sources():
    """It is a build output now. Leaving a copy in the tree would give the
    fingerprint two homes, and the stale one would be the one people read."""
    assert not (LIB / "devices.lock.json").exists()


def test_each_lock_carries_the_format_and_the_buckets():
    for p in sorted(LIB.glob("devices/*/*/device.lock.json")):
        d = json.loads(p.read_text())
        assert d.get("format") == dl.FORMAT, p
        for bucket in ("shape", "names", "surface", "gaps", "version"):
            assert bucket in d, (p, bucket)


def test_the_assembled_view_matches_the_files():
    got = dl.load_lock(LIB)["devices"]
    assert len(got) == len(list(libwalk.iter_devices([LIB])))
    for name, ent in got.items():
        assert ent == json.loads(dl.lock_path(LIB, name).read_text())


def test_the_build_writes_the_aggregate():
    dist = LIB / "dist/devices.lock.json"
    if not dist.exists():
        pytest.skip("no build; run ./build.sh")
    built = json.loads(dist.read_text())
    assert built["format"] == dl.FORMAT
    assert built["devices"] == dl.load_lock(LIB)["devices"], (
        "the aggregate has drifted from the per-device files - it is derived and "
        "build.sh writes it, so this means the build did not run")


def test_update_rewrites_only_the_device_that_moved(tmp_path):
    """THE CLAUSE THE ISSUE IS ABOUT, measured by mtime rather than asserted.

    `--update` used to rewrite the whole file whatever changed, so a one-word
    provenance fix produced a diff against a 906 KB artefact and a reviewer had
    to take on trust that the other 88 entries were untouched.
    """
    import shutil
    lib = tmp_path / "library"
    shutil.copytree(LIB, lib, ignore=shutil.ignore_patterns("dist", "exports"))
    locks = sorted(lib.glob("devices/*/*/device.lock.json"))
    assert len(locks) > 80
    old = time.time() - 3600
    for f in locks:
        os.utime(f, (old, old))

    victim = lib / "devices/juniper/mx204/device.yaml"
    if not victim.exists():
        pytest.skip("the MX204 is not in this library")
    s = victim.read_text()
    victim.write_text(re.sub(r"^version: (\d+)\.(\d+)\.(\d+)$",
                             lambda m: f"version: {m[1]}.{m[2]}.{int(m[3]) + 1}",
                             s, count=1, flags=re.M))
    r = subprocess.run([sys.executable, "-m", "portrayal.devicelock",
                        "--library", str(lib), "--update"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    touched = sorted(str(f.relative_to(lib)) for f in locks if f.stat().st_mtime > old + 1)
    assert touched == ["devices/juniper/mx204/device.lock.json"], touched

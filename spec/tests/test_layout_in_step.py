"""Every layout.yaml still expands to the device.yaml beside it.

roc-ops/Portrayal#168. `expand.py` turns a compact `layout.yaml` into the longhand
`device.yaml` every consumer reads, and it has a `--check` that re-expands and
compares so the pair cannot drift. NOTHING EVER RAN IT. Not CI, not the suite,
not publish.sh - and by the time this test was written both of the library's two
layouts had drifted so far that regenerating from them would have been
destructive:

  - the non-view keys were months stale. `cor580`'s layout carried version 0.1.0
    against the device's 1.0.9, an older provenance block, and no `profile:` at
    all - a key #170 made required. Expanding would have deleted the lot.
  - longhand items carried figures the library had since corrected. Five RJ45
    cutouts were 16 x 14, the registry figure #61 removed after finding no source
    ever gave it; the devices were fixed and the layouts were not. The expansion
    reproduced the old number, and `test_cutout_derivation` rejects it - so the
    generated file would have failed two rules the committed one passes.
  - two silkscreen marks on the DCS510 had gained `filled: true` in the device
    and not in the layout.

A GENERATOR NOBODY CHECKS IS A SECOND COPY, and a second copy of a file that
gets hand-edited is a worse problem than the repetition it was written to
remove. That is what this test exists to stop, and it is why it runs over every
layout rather than a named pair: the next one added is guarded on the day it
lands.
"""
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
TOOL = ROOT / "spec/tools/portrayal/expand.py"
LAYOUTS = sorted(LIB.glob("devices/*/*/layout.yaml"))


def test_there_are_layouts_to_check():
    """NON-VACUITY. `--check` over no layouts reports `0/0 in step` and exits 0,
    which is exactly what a broken glob looks like."""
    assert LAYOUTS, "no layout.yaml found - the walk is broken or they were removed"


def test_every_layout_expands_to_the_device_beside_it():
    r = subprocess.run([sys.executable, str(TOOL), "--check",
                        "--library", str(LIB), "--schemas", str(ROOT / "spec/schemas")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    tail = r.stdout.strip().splitlines()[-1]
    assert f"{len(LAYOUTS)}/{len(LAYOUTS)} in step" in tail, r.stdout


@pytest.mark.parametrize("layout", LAYOUTS, ids=lambda p: f"{p.parts[-3]}/{p.parts[-2]}")
def test_the_non_view_keys_are_the_same_in_both(layout):
    """The drift that would have been destructive, asserted directly rather than
    only through the expansion. Everything but `views` passes through expand.py
    untouched, so a layout carrying an older copy of them is a layout that will
    quietly undo whatever was written to the device since."""
    lay = yaml.safe_load(layout.read_text())
    dev = yaml.safe_load((layout.parent / "device.yaml").read_text())
    for key in dev:
        if key == "views":
            continue
        assert lay.get(key) == dev[key], (
            f"{layout.parent.name}: `{key}` differs between layout and device - "
            "expanding would overwrite the device's copy with the layout's")


@pytest.mark.parametrize("layout", LAYOUTS, ids=lambda p: f"{p.parts[-3]}/{p.parts[-2]}")
def test_the_layout_is_the_smaller_file(layout):
    """The whole point of authoring the compact one. If a layout ever grows past
    the device it generates, the generator is no longer earning its place."""
    lay = layout.stat().st_size
    dev = (layout.parent / "device.yaml").stat().st_size
    assert lay < dev, f"{layout.parent.name}: layout {lay} bytes, device {dev}"

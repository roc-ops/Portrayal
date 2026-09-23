"""Every face the explorer's merged tree lists carries the swaps, not only the
mounted one.

In 3D the tree is merged - one section per face - and the faces that are not
on screen are parsed straight from the build, which knows only the
configuration. The mounted face is seated by the shell's `reseat()`; the others
were never seated at all, so on fhd-1ufce with two cassettes swapped in, the
REAR section listed their backs (the mounted face) while the FRONT section
listed bay-1 and bay-2 as "open", the base build's state.

The pass a detached face needs is swap.js's `seatFace`: bays and cages as the
3D scene applies them (`applyFaceOverrides`), then the rear holes that show a
swapped front bay's back (`applyRearOverrides`). It is run in node on the fake
DOM the other seating scripts use; the shell's wiring - that `loadFaces` and a
later swap actually route the detached faces through it - is read off
kit/shell.js, since the shell itself needs a browser.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
SCRIPT = SPEC / "tests/js/merged-faces.mjs"
SHELL = SPEC.parent / "kit/shell.js"

A, B = "fs/cas-a@2", "fs/cas-b@1"


def run(mode):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT), mode], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_detached_face_is_seated_with_the_swaps():
    out = run("swapped")
    assert out["map"] == {"bay-1": A, "bay-2": B}
    assert out["front"] == {"bay-1": A, "bay-2": B, "bay-3": None, "bay-4": None}, \
        "the front lists the swapped bays as open"
    assert out["rear"] == {"bay-1": ["with-port"], "bay-2": ["with-port"],
                           "bay-3": None, "bay-4": None}, \
        "the rear holes do not show the swapped cassettes' backs"
    assert out["frontApplied"] == 2 and out["rearApplied"] == 2
    assert out["rearHoles"] == 2


def test_a_bay_the_reader_emptied_is_empty_on_every_face():
    out = run("emptied")
    assert out["map"] == {"bay-1": None}
    assert out["front"] == {"bay-1": None, "bay-2": None, "bay-3": B, "bay-4": None}
    assert out["rear"] == {"bay-1": None, "bay-2": None, "bay-3": ["bare"], "bay-4": None}, \
        "the build's back of bay-3 must be left alone"


def test_a_later_swap_replaces_what_the_face_was_seated_with():
    out = run("again")
    assert out["front"]["bay-1"] == B
    assert out["modules"] == 1, "the first swap's cassette is still in the bay"
    assert out["rear"]["bay-1"] == ["with-port"], "two backs, or the old one, in the hole"


def test_no_swaps_leave_the_build_untouched():
    out = run("none")
    assert out["map"] == {}
    assert out["applied"] == 0
    assert out["front"]["bay-1"] == A and out["rear"]["bay-1"] == ["bare"]


def _body(js, name):
    """The source of `function name(...) { ... }` in the shell, up to its close
    at the shell's own two-space indent."""
    m = re.search(r"\n  (?:async )?function %s\(.*?\n  \}\n" % re.escape(name), js, re.S)
    assert m, f"no function {name} in kit/shell.js"
    return m.group(0)


def test_the_shell_seats_the_faces_it_does_not_mount():
    js = SHELL.read_text()
    # loadFaces parses each face from the build and must seat it before
    # anything reads it
    assert "seatFace(" in _body(js, "loadFaces"), \
        "loadFaces keeps the build's faces without seating the swaps"
    # a swap made after the faces are held reaches them too, not only the
    # mounted face seat() works on
    assert "seatFace(" in _body(js, "seatDetached")
    for caller in ("swapBay", "swapCage", "applySwaps"):
        assert "seatDetached(" in _body(js, caller), \
            f"{caller} changes the mounted face and leaves the others as they were"

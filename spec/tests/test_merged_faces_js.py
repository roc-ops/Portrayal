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
swapped front bay's back (`applyRearOverrides`). The shell keeps its held
faces seated through swap.js's `faceQueue`: one ordered queue, a record of what
each face was seated with, and a `live()` check after every await. Both run in
node on the fake DOM the other seating scripts use; the shell's wiring - that
`loadFaces` and a later swap go through them - is read off kit/shell.js, since
the shell itself needs a browser.
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


def test_a_swapped_back_lands_where_its_own_body_stands():
    # bay-1 is seen through back-1 at x 332.97: a cassette's 99-wide body is
    # centred in the 108.97 bay, an adapter panel's 88-wide one is too, and
    # both are mirrored - so each back's centre is the hole's, 387.455
    out = run("positions")["positions"]
    assert out["a"] == {"transform": "translate(337.955,6.5)", "at": "337.955,6.5"}
    assert out["b"] == {"transform": "translate(343.455,4.6)", "at": "343.455,4.6"}, \
        "the panel's back was placed at the cassette's offset"
    assert out["emptied"] is None, "an empty hole still says where a back is"


def test_no_swaps_leave_the_build_untouched():
    out = run("none")
    assert out["map"] == {}
    assert out["applied"] == 0
    assert out["front"]["bay-1"] == A and out["rear"]["bay-1"] == ["bare"]


def test_a_swap_made_while_faces_load_reaches_them_once():
    out = run("queue")
    assert out["loaded"] == 2 and out["during"] == 1
    assert out["afterLoad"]["front"] == {"bay-1": A, "bay-2": B, "bay-3": A, "bay-4": None}
    assert out["afterLoad"]["rear"] == {"bay-1": ["with-port"], "bay-2": ["with-port"],
                                        "bay-3": ["with-port"], "bay-4": None}
    # the rear arrived before the swap and took it after; the front arrived
    # after and was seated with it - neither was seated with bay-2 twice
    assert out["callsAfterLoad"] == ["rear:bay-1,bay-3", "front:bay-1,bay-2,bay-3",
                                     "rear:bay-2"]


def test_a_job_loads_each_skin_once():
    # bay-1 and bay-3 hold one cassette: two seats of it, one fetch of its skin
    assert run("queue")["skinAsks"] == ["fs/cas-a-rear@1", A, "fs/cas-b-rear@1", B]


def test_an_entry_a_face_already_holds_is_not_seated_again():
    out = run("queue")
    assert out["same"] == 0 and out["sameCalls"] == 0
    assert out["changed"] == 2
    assert out["changedCalls"] == ["rear:bay-1", "front:bay-1"]
    assert out["afterChange"]["front"]["bay-1"] == B


def test_a_face_the_queue_never_seated_takes_every_entry():
    assert run("queue")["unrecorded"] == ["front:bay-1"]


def test_a_job_on_faces_no_longer_held_changes_nothing():
    out = run("queue")
    assert out["staleSwap"] == 0 and out["staleLoad"] == 0
    assert out["staleCalls"] == 0 and out["staleStored"] == []


def test_a_failed_job_does_not_stop_the_next():
    assert run("queue")["failed"] == ["boom", 0]


def _body(js, name):
    """The source of `function name(...) { ... }` in the shell, up to its close
    at the shell's own two-space indent."""
    m = re.search(r"\n  (?:async )?function %s\(.*?\n  \}\n" % re.escape(name), js, re.S)
    assert m, f"no function {name} in kit/shell.js"
    return m.group(0)


def test_the_shell_seats_the_faces_it_does_not_mount():
    js = SHELL.read_text()
    # every held face is seated by the queue, through seatFace
    assert re.search(r"faceQueue\(\{.*?seatFace\(", js, re.S), \
        "the shell's face queue does not seat through seatFace"
    # loadFaces seats each face it fetches with the state's whole delta
    load = _body(js, "loadFaces")
    assert "faceWork.load(" in load and "delta: swapDelta" in load, \
        "loadFaces keeps the build's faces without seating the swaps"
    # a later swap reaches the held faces, on the faces held when it was made
    detached = _body(js, "seatDetached")
    assert "faceWork.swap(" in detached
    assert detached.index("const key = state.facesFor") < detached.index("faceWork.swap("), \
        "seatDetached must name the faces it means when it is called, not when it runs"
    for caller in ("swapBay", "swapCage", "applySwaps"):
        assert "seatDetached(" in _body(js, caller), \
            f"{caller} changes the mounted face and leaves the others as they were"


def test_the_page_hands_3d_the_delta_the_tree_is_seated_with():
    page = (SPEC.parent / "kit/index.html").read_text()
    assert "shell.swapDelta()" in page
    assert "swapOverrides as" not in page, "the page builds its own copy of the delta"

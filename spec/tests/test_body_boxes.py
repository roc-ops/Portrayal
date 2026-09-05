"""A body can be several boxes, and the riser's is.

One box the size of the face hid the chassis interior; a box cut to the plate
left the riser's PCB behind - in the top view, as a part of its own - when the
riser was ejected. `body.boxes` lists the pieces in the face's frame, the kit
resolves either form through one function, and L71 holds each box inside the
reach the part declares.
"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))
import lint  # noqa: E402


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_kit_resolves_both_body_forms_to_one_list():
    script = SPEC / "tests/js/body-boxes.mjs"
    p = subprocess.run(["node", str(script)], capture_output=True, text=True, cwd=str(script.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])
    # the one-box body is the face, at the plane, its depth deep
    assert out["one"] == [{"id": "body", "x": 0, "y": 0, "w": 86.3, "h": 39.1,
                           "z0": 0, "z1": 195.5, "color": "#222"}]
    # a footprint trims it
    assert out["fp"][0]["w"] == 40 and out["fp"][0]["x"] == 2 and out["fp"][0]["z1"] == 60
    # the pieces keep their own place, start and colour, and inherit the body's
    pcb, c = out["riser"]
    assert (pcb["x"], pcb["z0"], pcb["z1"], pcb["color"]) == (-0.75, 13.9, 184.8, "#1f5138")
    assert (c["z0"], c["z1"], c["color"]) == (47.9, 138.9, "#4a5057")


def _caught(code, fn, *a):
    saved_w, saved_e = lint.WARNINGS[:], lint.ERRORS[:]
    lint.WARNINGS.clear(); lint.ERRORS.clear()
    try:
        fn(*a)
        return [m for m in lint.WARNINGS + lint.ERRORS if f"[{code}]" in m]
    finally:
        lint.WARNINGS[:] = saved_w; lint.ERRORS[:] = saved_e


def test_a_box_cannot_reach_past_the_part_s_own_depth():
    part = lambda d, bd, frm: {"size": {"w": 100.0, "h": 60.0, "d": d},
                               "body": {"depth": bd, "boxes": [
                                   {"id": "pcb", "at": [0, 0], "size": [1.6, 77.0],
                                    "from": frm, "depth": 170.9, "confidence": "measured"}]}}
    hits = _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part(170.9, 170.9, 13.9))
    assert hits and "184.8" in hits[0], hits
    assert not _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part(184.8, 184.8, 13.9))
    # and the pull distance is read from body.depth, so that has to be the reach too
    hits = _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part(184.8, 20.0, 13.9))
    assert hits and "body.depth" in hits[0], hits


def test_every_riser_carries_its_pcb_and_a_connector_per_card_slot():
    """The point of the exercise: the riser IS its PCB, and a slot that takes
    a card has a connector behind it while one that takes only a filler has
    none - riser 1A's middle opening."""
    for p in sorted((LIB / "components/dell").glob("riser-[123][a-f]-14g/v1/contract.yaml")):
        c = yaml.safe_load(p.read_text())
        boxes = {b["id"]: b for b in c["body"]["boxes"]}
        assert "pcb" in boxes, p
        pcb = boxes["pcb"]
        assert abs(pcb["from"] + pcb["depth"] - c["size"]["d"]) < 0.05, (p, "the PCB is the reach")
        assert c["body"]["depth"] == c["size"]["d"], p
        for slot, b in (c.get("bays") or {}).items():
            takes_card = any("bracket" in a for a in b["accepts"])
            assert (f"{slot}-connector" in boxes) == takes_card, (p, slot)

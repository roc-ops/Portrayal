"""Belden 9510-1901 ring panel and 9512-1903 lacing bar: what each data sheet's photograph shows is drawn.

The 9510-1901 photograph shows two slotted holes in each ear, a flange folded back along the panel's top
edge and a tan liner under the top bar of the rings. The 9512-1903 photograph shows a thin flat strip with
one slotted hole near each end. Each is drawn, estimated from the photograph, and none is left as a gap.
These tests read the device files and the panel's skin, so they need no build.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
PANEL = LIB / "components" / "belden" / "9510-1901-panel" / "v1"


def device(name):
    return yaml.safe_load((LIB / "devices" / "belden" / name / "device.yaml").read_text())


def decor(doc, view):
    return {d["id"]: d for d in doc["views"][view]["panel"]["decor"]}


def test_each_ear_of_the_ring_panel_has_two_slotted_holes_in_its_skin():
    svg = (PANEL / "skins" / "default.svg").read_text()
    holes = re.findall(r'<rect id="ear-hole-(left|right)-(top|bottom)" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="([\d.]+)"', svg)
    assert sorted((a, b) for a, b, *_ in holes) == [("left", "bottom"), ("left", "top"), ("right", "bottom"), ("right", "top")]
    for side, _, x, y, w, h, rx in holes:
        assert (float(w), float(h)) == (12.0, 5.0) and float(rx) == 2.5, "a stadium 12 by 5"
        centre = float(x) + 6 if side == "left" else 482.6 - (float(x) + 6)
        assert abs(centre - 12) < 0.01, "12 from the panel's end"
    ys = sorted({float(y) for *_, y, _, _, _ in holes})
    assert abs((ys[1] - ys[0]) - 32) < 0.01, "the two holes of an ear are 32 apart"


def test_the_ring_panel_draws_its_top_flange_and_the_liner_and_leaves_neither_as_a_gap():
    doc = device("9510-1901")
    top = decor(doc, "top")["top-flange"]
    assert top["at"] == [29, 0] and top["size"] == [424.6, 6]
    for view in ("left", "right"):
        d = decor(doc, view)
        assert d["top-flange"]["size"] == [6, 1.5]
        assert d["ring-liner"]["size"] == [49.7, 2.5] and d["ring-liner"]["fill"] == "#807969"
    rear = [d for d in doc["views"]["rear"]["panel"]["decor"] if d["kind"] == "ear-hole"]
    assert len(rear) == 4 and all(d["size"] == [12, 5] and d["shape"] == "slot" for d in rear), "through the panel"
    gaps = {g["what"] for g in doc["gaps"]}
    assert not gaps & {"top-flange", "ring-liner", "ear-holes"}
    assert "ring-screws" in gaps, "the screw on each ring's back leg is hidden on every face"


def test_the_lacing_bar_draws_two_end_holes_and_a_flat_strip():
    doc = device("9512-1903")
    assert doc["chassis"]["depth"] == 12.7, "the data sheet's depth stays the overall size"
    for view in ("front", "rear"):
        d = decor(doc, view)
        assert d["bar"]["size"] == [482.6, 12.7]
        left, right = d["end-hole-left"], d["end-hole-right"]
        assert left["size"] == right["size"] == [10, 4] and left["shape"] == right["shape"] == "slot"
        assert abs((left["at"][0] + 5) - 13) < 0.01 and abs(482.6 - (right["at"][0] + 5) - 13) < 0.01
        assert abs(left["at"][1] + 2 - 6.35) < 0.01
    assert decor(doc, "top")["strip"]["size"] == [482.6, 1.5] == decor(doc, "bottom")["strip"]["size"]
    assert decor(doc, "left")["strip"]["size"] == decor(doc, "right")["strip"]["size"] == [1.5, 12.7]
    gaps = {g["what"] for g in doc["gaps"]}
    assert "end-holes" not in gaps and {"tie-points", "cross-section"} <= gaps

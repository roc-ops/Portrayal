"""The marks the data sheet photographs show at the ends of the APC 1U rack PDUs AP7821B and AP7921B.

The p.1 photograph of each outlet face shows two small round marks at each end of the face, one above the other.
The AP7921B's angled photograph also shows its display end: six marks in two rows of three. What is true of the
library once they are drawn:

  - the outlet face draws four round marks, two within 8 mm of each end, at two heights;
  - the display end (the `left` view, seen from behind) draws six, in two rows of three, inside the end;
  - the inlet end (the `right` view) stays undrawn, because no held photograph shows it;
  - every mark is declared an estimate and says how its position was read.

These read the device sources. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SKUS = {"ap7821b": (444, 44, 102), "ap7921b": (445, 44, 108)}


def device(sku):
    return yaml.safe_load((LIB / "devices" / "apc" / sku / "device.yaml").read_text())


def marks(sku, view):
    decor = (device(sku)["views"][view].get("panel") or {}).get("decor") or []
    return [d for d in decor if d.get("kind") == "end-screw"]


def centre(d):
    return (d["at"][0] + d["size"][0] / 2, d["at"][1] + d["size"][1] / 2)


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_outlet_face_draws_two_round_marks_at_each_end(sku):
    width = SKUS[sku][0]
    drawn = marks(sku, "rear")
    assert len(drawn) == 4
    for d in drawn:
        assert d["rx"] == d["size"][0] / 2 == d["size"][1] / 2, "round"
    cx = sorted(centre(d)[0] for d in drawn)
    assert all(x <= 8 for x in cx[:2]) and all(x >= width - 8 for x in cx[2:])
    assert len({round(centre(d)[1]) for d in drawn}) == 2, "two heights"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_display_end_draws_six_marks_in_two_rows_of_three(sku):
    _, height, depth = SKUS[sku]
    drawn = marks(sku, "left")
    assert len(drawn) == 6
    assert len({round(centre(d)[1]) for d in drawn}) == 2
    assert len({round(centre(d)[0]) for d in drawn}) == 3
    for d in drawn:
        x, y = centre(d)
        assert 0 < x < depth and 0 < y < height


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_inlet_end_stays_undrawn_and_says_why(sku):
    right = device(sku)["views"]["right"]
    assert not marks(sku, "right")
    assert len(str(right.get("empty", ""))) > 40


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_every_mark_is_an_estimate_with_its_method(sku):
    for view in ("rear", "left"):
        for d in marks(sku, view):
            assert d["confidence"] == "estimated", f"{sku} {view} {d['id']}"
            assert "photograph" in d["source"] and len(d["source"]) > 30

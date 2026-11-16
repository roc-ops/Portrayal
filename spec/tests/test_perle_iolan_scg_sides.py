"""The IOLAN SCG R chassis draws what the maker's outline drawing shows of its sides, top, bottom and ears.

Perle, IOLAN SCG Hardware Installation Guide, Expandable Models (5500427-10), Appendix D page 35.
Each side shows two rows of 32 vent slots. It shows a rack-ear bracket with six round holes and six slotted ovals.
It shows two more round holes and two ringed holes beyond the bracket. The plan shows a seam 10.8 mm behind the
front, and the bracket's leg. The front view shows a flange 22 mm past each end of the body with two slotted holes.

On the right view x = 0 is the front. On the left view x = 0 is the rear. On the top and bottom views y = 0 is
the rear. The drawing's side view has its front at the left. So the right side is the drawing, and the left is its
mirror about the depth.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MODELS = ["iolan-scg18-r", "iolan-scg34-r", "iolan-scg50-r"]
DEPTH, BODY_W, EAR_W = 262.0, 436.0, 22.1


def _layout(model):
    path = ROOT / "library" / "devices" / "perle" / model / "layout.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _decor(model, face):
    return _layout(model)["views"][face]["panel"]["decor"]


def _kind(decor, kind):
    return [d for d in decor if d.get("kind") == kind]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("face", ["left", "right"])
def test_a_side_draws_what_the_drawing_shows(model, face):
    decor = _decor(model, face)
    for row in (1, 2):
        rects = [d for d in _kind(decor, "vent-field") if d["id"].split("-")[2] == str(row)]
        assert sum(round(v["size"][0] / v["pattern-pitch"][0]) for v in rects) == 32, "32 slots in a row"
    assert len(_kind(decor, "ear-bracket")) == 1
    assert len(_kind(decor, "bracket-slot")) == 6
    holes = _kind(decor, "hole")
    assert len([h for h in holes if h["id"].startswith("bracket-hole")]) == 6
    assert len([h for h in holes if h["id"].startswith("hole-")]) == 2
    assert len([h for h in holes if h["id"].startswith("ring-") and "-bore-" in h["id"]]) == 2


@pytest.mark.parametrize("model", MODELS)
def test_the_vent_pattern_starts_at_each_rect_corner(model):
    """The motif pattern is anchored to the face's origin, so each vent rect carries its own corner as its offset."""
    for face in ("left", "right"):
        vents = _kind(_decor(model, face), "vent-field")
        assert len(vents) == 10, "two rows, each with four ovals showing two slots and one field beyond the plate"
        for v in vents:
            assert v["pattern-offset"][0] == v["at"][0], v["id"]
            assert v["pattern-offset"][1] <= v["at"][1], "a row cut by the bracket keeps the whole slot's own top"


@pytest.mark.parametrize("model", MODELS)
def test_the_right_side_is_the_drawing_and_the_left_is_its_mirror(model):
    left, right = _decor(model, "left"), _decor(model, "right")
    bracket = _kind(right, "ear-bracket")[0]
    assert bracket["at"][0] == 0.0, "the bracket is at the front, and x = 0 is the front on the right view"
    mirrored = _kind(left, "ear-bracket")[0]
    assert mirrored["at"][0] + mirrored["size"][0] == pytest.approx(DEPTH, abs=0.02)
    assert len(_kind(right, "bracket-slot")) == 6, "a vacuous mirror test would pass on an empty side"
    for a in right:
        if a.get("kind") in ("envelope",):
            continue
        b = next(d for d in left if d["id"] == a["id"].replace("-right", "-left"))
        assert (a["at"][0] + a["size"][0]) + b["at"][0] == pytest.approx(DEPTH, abs=0.02), a["id"]
        assert a["at"][1] == b["at"][1] and a["size"] == b["size"]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("face", ["top", "bottom"])
def test_the_top_and_bottom_draw_the_front_seam_and_the_bracket_legs(model, face):
    decor = _decor(model, face)
    view = _layout(model)["views"][face]
    assert view["size"] == {"w": BODY_W, "h": DEPTH}, "the plan is the body: the renderer paints the whole view"
    (seam,) = _kind(decor, "seam")
    assert seam["size"][0] == BODY_W and seam["at"][0] == 0.0
    behind_front = DEPTH - (seam["at"][1] + seam["size"][1] / 2)
    assert behind_front == pytest.approx(10.8, abs=0.02), "10.8 mm behind the front, and y = 0 is the rear"
    legs = _kind(decor, "bracket-leg")
    assert len(legs) == 2
    for leg in legs:
        assert leg["size"][1] == 94.7, "the plan's leg line runs 2.2 to 96.9 behind the front"
        assert leg["at"][1] + leg["size"][1] == pytest.approx(DEPTH - 2.2, abs=0.02)
    assert sorted(leg["at"][0] for leg in legs) == [0.0, pytest.approx(BODY_W - legs[0]["size"][0])]
    assert not _kind(decor, "ear-flange"), "the flanges stand outside the 436 mm view and are a named gap"


@pytest.mark.parametrize("model", MODELS)
def test_the_front_is_the_body_between_two_ear_flanges(model):
    layout = _layout(model)
    front = layout["views"]["front"]
    assert front["size"]["w"] == pytest.approx(BODY_W + 2 * EAR_W, abs=0.01) == pytest.approx(480.2)
    assert layout["chassis"]["width"] == 436 and layout["views"]["rear"]["size"]["w"] == 436
    placed = {p["id"]: p for p in front["components"]["placements"]}
    left, right = placed["ear-left"], placed["ear-right"]
    assert left["ref"] == right["ref"] == "perle/scg-rack-ear@1"
    assert (left["skin"], right["skin"]) == ("left", "right")
    assert left["at"][0] == 0.0 and right["at"][0] == pytest.approx(BODY_W + EAR_W, abs=0.01)
    (plate,) = [d for d in front["panel"]["decor"] if d["id"] == "faceplate"]
    assert plate["at"][0] == pytest.approx(EAR_W) and plate["size"][0] == BODY_W
    for pid, p in placed.items():
        if not pid.startswith("ear-"):
            assert EAR_W <= p["at"][0] <= EAR_W + BODY_W, f"{pid} stays on the body"


def test_the_ear_is_one_component_with_two_slotted_holes_in_each_skin():
    base = ROOT / "library" / "components" / "perle" / "scg-rack-ear" / "v1"
    contract = yaml.safe_load((base / "contract.yaml").read_text(encoding="utf-8"))
    assert contract["class"] == "ear" and contract["size"]["w"] == EAR_W and contract["size"]["h"] == 43.0
    assert set(contract["provenance"]) >= {"size", "size-holes"}
    for skin in ("left", "right"):
        svg = (base / "skins" / f"{skin}.svg").read_text(encoding="utf-8")
        (slots,) = re.findall(r'id="slots"[^>]* d="([^"]+)"', svg)
        assert slots.count("M") == 2, f"two slotted holes in the {skin} skin"

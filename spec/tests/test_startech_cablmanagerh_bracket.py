"""StarTech.com CABLMANAGERH: each of the five D-rings stands on a bracket across the panel's height.
Each of the four holes has a raised collar, as the maker's own drawing draws them.

The sizes are scaled off the drawing (it says "DO NOT SCALE"). They are estimated.
The tests pin the count, the pitch and the place of each part, not a figure the drawing does not state.
The rivet is a dome centred on its ring and the collar is a dome. Each is a rounded rectangle.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEV = yaml.safe_load((LIB / "devices/startech/cablmanagerh/device.yaml").read_text())
PANEL = LIB / "components/startech/cablmanagerh-panel/v1"
CONTRACT = yaml.safe_load((PANEL / "contract.yaml").read_text())
FRONT_DECOR = {d["id"]: d for d in DEV["views"]["front"]["panel"]["decor"]}
RINGS = [p for p in DEV["views"]["front"]["components"]["placements"] if "cablmanagerh-ring@" in p["ref"]]
NS = "{http://www.w3.org/2000/svg}"


def test_five_brackets_stand_under_the_five_rings_at_the_ring_pitch():
    elements = [CONTRACT["elements"][f"bracket-{k}"] for k in range(1, 6)]
    assert len(RINGS) == 5
    for e, r in zip(elements, RINGS):
        assert abs((e["at"][0] + e["size"][0] / 2) - (r["at"][0] + 4.55)) < 0.01, "the ring is centred on its bracket"
    assert [round(b["at"][0] - a["at"][0], 1) for a, b in zip(elements, elements[1:])] == [100.0] * 4


def test_a_bracket_spans_nearly_the_panels_whole_height_and_stands_7_4_out():
    for k in range(1, 6):
        e = CONTRACT["elements"][f"bracket-{k}"]
        assert 0.9 * DEV["chassis"]["height"] <= e["size"][1] <= DEV["chassis"]["height"]
        feature = next(f for f in CONTRACT["relief"]["features"] if f["node"] == f"bracket-{k}")
        assert feature["out"] == 7.4 and feature["confidence"] == "estimated"


def test_the_panel_skin_draws_the_five_brackets_each_with_a_strap_and_a_rivet():
    root = ET.parse(PANEL / "skins/default.svg").getroot()
    groups = {g.get("id"): g for g in root.iter(f"{NS}g") if (g.get("id") or "").startswith("bracket-")}
    assert sorted(groups) == [f"bracket-{k}" for k in range(1, 6)]
    for g in groups.values():
        assert len(g.findall(f"{NS}rect")) == 2 and len(g.findall(f"{NS}circle")) == 1


def test_four_collars_sit_on_the_four_holes_the_rear_draws():
    holes = [d for d in DEV["views"]["rear"]["panel"]["decor"] if d["id"].startswith("hole-")]
    assert len(holes) == 4
    for k, h in enumerate(holes, 1):
        c = FRONT_DECOR[f"collar-{k}"]
        assert c["at"] == h["at"] and c["size"] == h["size"] and c["rx"] == 14.5
        inner = FRONT_DECOR[f"collar-{k}-inner"]
        assert inner["size"] == [21.2, 21.2] and "fill" not in inner and "stroke" in inner, "an outline, no bore"


def test_the_bracket_gap_is_gone_and_the_waist_gap_stays():
    gaps = {g["what"] for g in DEV["gaps"]}
    assert "ring-bracket" not in gaps and "ring-waist" in gaps


@pytest.mark.parametrize("view", ["top", "bottom"])
def test_the_top_and_bottom_views_draw_the_brackets_and_collars(view):
    ids = {d["id"] for d in DEV["views"][view]["panel"]["decor"]}
    assert {f"bracket-{k}-side" for k in range(1, 6)} <= ids and {f"collar-{k}-side" for k in range(1, 5)} <= ids


@pytest.mark.parametrize("view", ["top", "bottom"])
def test_the_collar_dome_is_3_6_high_the_mean_of_the_four_readings(view):
    decor = {d["id"]: d for d in DEV["views"][view]["panel"]["decor"]}
    for k in range(1, 5):
        assert decor[f"collar-{k}-side"]["size"] == [29.0, 3.6]
        assert decor[f"collar-{k}-side"]["rx"] == 1.8, "a rounded rectangle is the kit's nearest to a dome"


@pytest.mark.parametrize("view", ["top", "bottom"])
def test_the_rivet_is_a_dome_centred_on_each_ring_at_the_foot_base(view):
    decor = {d["id"]: d for d in DEV["views"][view]["panel"]["decor"]}
    for k in range(1, 6):
        rivet = decor[f"rivet-{k}-side"]
        assert rivet["size"] == [8.4, 2.5] and rivet["rx"] == 1.25
        assert abs(rivet["at"][0] + rivet["size"][0] / 2 - (41.3 + 100.0 * (k - 1))) < 0.01, "centred on the ring"
        assert rivet["at"][1] == 7.41, "standing on the plate"


@pytest.mark.parametrize("view", ["top", "bottom"])
def test_each_foot_draws_the_inner_box_of_its_stepped_lip(view):
    decor = {d["id"]: d for d in DEV["views"][view]["panel"]["decor"]}
    lips = [d for i, d in decor.items() if i.startswith("foot-lip-")]
    assert len(lips) == 5
    for k in range(1, 6):
        foot, lip = decor[f"bracket-{k}-side"], decor[f"foot-lip-{k}-side"]
        assert lip["size"] == [32.0, 4.1] and "fill" not in lip and "stroke" in lip, "an outline"
        assert foot["at"][0] < lip["at"][0] and lip["at"][0] + 32.0 < foot["at"][0] + foot["size"][0]
        assert foot["at"][1] <= lip["at"][1] and lip["at"][1] + 4.1 <= foot["at"][1] + foot["size"][1]


def test_the_panels_folded_strip_is_the_side_views_strip_and_the_gap_says_so():
    flange = yaml.safe_load((LIB / "components/startech/cablmanagerh-flange/v1/contract.yaml").read_text())
    at = next(p for p in DEV["views"]["top"]["components"]["placements"] if "flange" in p["ref"])["at"][0]
    assert abs(at - 29.6) < 3.0 and abs((482.6 - at - flange["size"]["w"]) - 30.0) < 3.0, "extent along the panel"
    assert abs((flange["size"]["h"] - 1.2) - 6.21) < 0.5, "depth: the printed 6.21"
    gap = next(g for g in DEV["gaps"] if g["what"] == "front-edge-strip")
    assert "side view" in gap["note"] and "fold" in gap["note"]


def test_the_strap_is_centred_on_the_bracket():
    root = ET.parse(PANEL / "skins/default.svg").getroot()
    for g in root.iter(f"{NS}g"):
        if (g.get("id") or "").startswith("bracket-"):
            plate, strap = g.findall(f"{NS}rect")
            centre = lambda r: float(r.get("y")) + float(r.get("height")) / 2
            assert abs(centre(plate) - centre(strap)) < 0.01


@pytest.mark.parametrize("view", ["left", "right"])
def test_the_end_views_draw_the_bracket_foot(view):
    assert any(d["id"] == "bracket-foot" for d in DEV["views"][view]["panel"]["decor"])

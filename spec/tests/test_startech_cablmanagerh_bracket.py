"""StarTech.com CABLMANAGERH: each of the five D-rings stands on a bracket across the panel's height
and each of the four holes has a raised collar, as the maker's own drawing draws them.

The sizes are scaled off the drawing (it says "DO NOT SCALE") and are estimated; the tests pin the
count, the pitch and the place of each part, not a figure the drawing does not state.
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


@pytest.mark.parametrize("view", ["left", "right"])
def test_the_end_views_draw_the_bracket_foot(view):
    assert any(d["id"] == "bracket-foot" for d in DEV["views"][view]["panel"]["decor"])

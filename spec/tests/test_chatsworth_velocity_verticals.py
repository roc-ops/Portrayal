"""Chatsworth Velocity 6 in single-sided vertical cable managers: 13902-701, 13902-703 and 13902-715.

Every figure is what the Velocity Cable Management data sheet (ordering table, "Single-Sided Vertical
Cable Managers") prints, in the units it prints them: height, width and depth with the rack height each
part is sold for. What no held page dimensions (a finger, the section of a wall or a door, the rear
openings) is estimated in the device and is held here only to what the model itself declares.

The part is a `rack-side` manager, drawn as it stands beside a rack: portrait, taking no rack unit, with a
`duct` guide run down its height and a finger to each rack unit down both sides of the channel.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

from portrayal import labs

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
EXPORTS = LIB / "exports"
RU = 44.45

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# part -> (height mm, rack units, shipping weight kg): the ordering table, "H x W x D in (mm)", for 6'H 38U,
# 7'H 45U and 8'H 51U racks. Every row is 152 wide and 249 deep.
PARTS = {
    "13902-701": (1778.0, 38, 8.2),
    "13902-703": (2045.0, 45, 9.1),
    "13902-715": (2311.0, 51, 9.1),
}
WIDTH, DEPTH = 152.0, 249.0
USABLE_WIDTH = 152.0 - 33.0      # "Usable width is 1.3 inches (33 mm) less than overall width."
DEPTH_WITHOUT_DOORS = 241.0      # "9.5 inches deep (241 mm) without doors"
USABLE_DEPTH = 191.0             # "Usable depth is 7.5 inches (191 mm)."


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "chatsworth" / name / "device.yaml").read_text())


def contract(ref):
    return yaml.safe_load((LIB / "components" / ref.split("@")[0] / "v1" / "contract.yaml").read_text())


def placements(doc, stem):
    return [p for p in doc["views"]["front"]["components"]["placements"] if p["id"].startswith(stem)]


@pytest.mark.parametrize("name", list(PARTS))
def test_the_envelope_is_the_size_the_ordering_table_prints(name):
    h, ru, kg = PARTS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "Chatsworth Products" and doc["model"] == name
    assert close(c["width"], WIDTH) and close(c["height"], h) and close(c["depth"], DEPTH)
    assert c["mount"] == "rack-side" and c["shell"] == "sheet" and c["ru"] == ru
    assert c["height"] > c["width"], "a vertical manager is drawn as it stands, portrait"
    assert close(c["weight-kg"], kg, 0.0005) and close(doc["attrs"]["physical"]["weight-kg"], kg, 0.0005)
    assert doc["views"]["front"]["size"] == {"w": WIDTH, "h": h}


@pytest.mark.parametrize("name", list(PARTS))
def test_the_channel_is_the_usable_width_and_the_doors_stand_at_the_overall_depth(name):
    """The table's note: 241 deep without doors, 191 usable, 33 off the width for the usable width. The well
    the walls stand in is 249 less the 50 behind the floor; the channel is 119 wide, 16.5 a wall."""
    h = PARTS[name][0]
    doc = device_yaml(name)
    duct = doc["views"]["front"]["guides"][0]
    assert duct["kind"] == "duct" and duct["run"] == "y"
    assert close(duct["size"][0], USABLE_WIDTH) and close(duct["size"][1], h)
    assert close(duct["at"][0], (WIDTH - USABLE_WIDTH) / 2) and close(duct["finger-pitch"], RU)
    base = contract(f"chatsworth/velocity-{name}-base")
    assert close(base["size"]["d"], DEPTH - (DEPTH_WITHOUT_DOORS - USABLE_DEPTH))
    door = contract(f"chatsworth/velocity-{name}-door")
    assert door["lid"] is True and door["behaviour"] == "mounts"
    assert max(f["out"] for f in door["relief"]["features"]) == base["size"]["d"], "the door is the front of the 249"
    finger = contract("chatsworth/velocity-vcm-finger")
    assert max(f["out"] for f in finger["relief"]["features"]) == USABLE_DEPTH, "the guides end at the 241"


@pytest.mark.parametrize("name", list(PARTS))
def test_a_finger_to_each_rack_unit_down_both_sides_one_rack_unit_apart(name):
    _, ru, _ = PARTS[name]
    doc = device_yaml(name)
    for side in ("left", "right"):
        ps = placements(doc, f"finger-{side}-")
        assert len(ps) == ru, (name, side)
        ys = [p["at"][1] for p in ps]
        assert [round(b - a, 2) for a, b in zip(ys, ys[1:])] == [RU] * (ru - 1)
        assert {p["ref"] for p in ps} == {"chatsworth/velocity-vcm-finger@1"}
    left, right = placements(doc, "finger-left-"), placements(doc, "finger-right-")
    assert {p["at"][0] for p in left} == {0.0} and {p["at"][0] for p in right} == {WIDTH - 16.5}


@pytest.mark.parametrize("name", list(PARTS))
def test_two_half_height_doors_cover_the_whole_height(name):
    h = PARTS[name][0]
    doc = device_yaml(name)
    doors = placements(doc, "door-")
    assert [p["at"][1] for p in doors] == [0.0, h / 2]
    comp = contract(doors[0]["ref"])
    assert close(comp["size"]["h"] * 2, h) and comp["size"]["w"] == WIDTH


@pytest.mark.parametrize("name", list(PARTS))
def test_the_gaps_say_what_the_pages_do_not(name):
    doc = device_yaml(name)
    gaps = {g["what"] for g in doc["gaps"]}
    assert {"rear-openings", "finger-shape", "section-joint", "door-hinge", "door-bevel"} <= gaps
    assert "performance" not in doc["attrs"], "the data sheet points to a cable fill table and states no figure"


def test_no_model_name_the_pages_do_not_print_is_used():
    """The held pages say 'Velocity Single-Sided Vertical Cable Manager'; the issue's own name for another
    line is not a model name here."""
    text = ""
    for p in list((LIB / "devices" / "chatsworth").glob("13902-7*/device.yaml")) + \
            list((LIB / "components" / "chatsworth").glob("velocity-*/v1/contract.yaml")):
        text += p.read_text()
    assert text and "G3" not in text


@pytest.mark.parametrize("name", list(PARTS))
def test_the_part_stands_beside_a_rack_on_either_side_and_two_on_one_side_overlap(name):
    _, ru, _ = PARTS[name]
    lab = {"format": 1, "kind": "lab", "name": "velocity-verticals", "rack": {"height-ru": ru},
           "devices": [{"id": "l", "ref": name, "side": "left"}, {"id": "r", "ref": name, "side": "right"}],
           "links": []}
    assert labs.schema_errors(lab) == []
    found, placed = labs.check(lab, [LIB])
    assert [c for c, sev, _ in found if sev == "error"] == [], found
    got = {p["id"]: p for p in placed}
    assert (got["l"]["side"], got["l"]["mount"], got["l"]["ru"]) == ("left", "rack-side", 1)
    assert got["r"]["side"] == "right"
    lab["devices"] = [{"id": "a", "ref": name, "side": "left"}, {"id": "b", "ref": name, "side": "left"}]
    found, _ = labs.check(lab, [LIB])
    assert [c for c, sev, _ in found if sev == "error"] == ["L154"], found


@pytest.mark.parametrize("name", list(PARTS))
def test_the_dcim_device_types_export_no_rack_unit_and_not_full_depth(name):
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Chatsworth Products" / f"{name}.yaml"
        assert path.is_file(), f"{path} is missing: run preflight.py --write-exports"
        out = yaml.safe_load(path.read_text())
        assert out["manufacturer"] == "Chatsworth Products" and out["model"] == name
        assert out["u_height"] == 0.0 and out["is_full_depth"] is False


@needs_dist
@pytest.mark.parametrize("name", list(PARTS))
def test_the_built_front_publishes_the_vertical_duct_and_the_rack_catalogue_the_part(name):
    h, ru, _ = PARTS[name]
    root = ET.parse(DIST / f"{name}.base.front.svg").getroot()
    el = {e.get("id"): e for e in root.iter() if e.get("id")}["guide--duct"]
    assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "y"
    assert float(el.get("data-guide-finger-pitch")) == RU
    assert close(float(el.get("width")), USABLE_WIDTH) and close(float(el.get("height")), h)
    r = json.loads((DIST / "rack.json").read_text())["devices"][name]
    assert r["mount"] == "rack-side" and r["ru"] == ru and close(r["w"], WIDTH, 0.01)

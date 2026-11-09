"""Chatsworth Velocity single-sided vertical cable managers 13901, 13904 and 13905 (3.6, 10 and 12 in wide), each
for 6, 7 and 8 ft racks.

Every figure is what the Velocity Cable Management data sheet (ordering table, "Single-Sided Vertical Cable
Managers") prints, in the units it prints them: height, width and depth with the rack height each part is sold for.
What no held page dimensions (a finger, the section of a wall or a door, the rear openings) is estimated in the
device and is held here only to what the model itself declares.

Each part is a `rack-side` manager, drawn as it stands beside a rack: portrait, taking no rack unit, with a `duct`
guide run down its height and a finger to each rack unit down both sides of the channel. The finger and the wall of
a given height are the parts the 6 in managers place; they are not copied for another width.
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
WALL = 16.5

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# part -> (height mm, rack units, width mm, depth mm, shipping weight kg): the ordering table, "H x W x D in (mm)",
# for 6'H 38U, 7'H 45U and 8'H 51U racks.
PARTS = {
    "13901-701": (1778.0, 38, 91.0, 246.0, 7.7),
    "13901-703": (2045.0, 45, 91.0, 246.0, 8.2),
    "13901-715": (2311.0, 51, 91.0, 246.0, 8.2),
    "13904-701": (1778.0, 38, 254.0, 262.0, 13.6),
    "13904-703": (2045.0, 45, 254.0, 262.0, 14.5),
    "13904-715": (2311.0, 51, 254.0, 262.0, 14.5),
    "13905-701": (1778.0, 38, 305.0, 264.0, 14.5),
    "13905-703": (2045.0, 45, 305.0, 264.0, 15.4),
    "13905-715": (2311.0, 51, 305.0, 264.0, 15.4),
}
DEPTH_WITHOUT_DOORS = 241.0      # "9.5 inches deep (241 mm) without doors"
USABLE_DEPTH = 191.0             # "Usable depth is 7.5 inches (191 mm)."
# "covers on 3.6 in (91 mm) and 6 in (152 mm) managers are plastic; covers on 10 in (254 mm) and 12 in (305 mm)
# managers are steel with plastic hinges"
DOOR_MATERIAL = {91.0: "Plastic", 254.0: "Steel", 305.0: "Steel"}


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
    h, ru, w, d, kg = PARTS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "Chatsworth Products" and doc["model"] == name
    assert close(c["width"], w) and close(c["height"], h) and close(c["depth"], d)
    assert c["mount"] == "rack-side" and c["shell"] == "sheet" and c["ru"] == ru
    assert c["height"] > c["width"], "a vertical manager is drawn as it stands, portrait"
    assert close(c["weight-kg"], kg, 0.0005) and close(doc["attrs"]["physical"]["weight-kg"], kg, 0.0005)
    assert doc["views"]["front"]["size"] == {"w": w, "h": h}


@pytest.mark.parametrize("name", list(PARTS))
def test_the_channel_is_the_usable_width_and_the_doors_stand_at_the_overall_depth(name):
    """The table's note: 241 deep without doors, 191 usable, 33 off the width for the usable width. The well the
    walls stand in is the table's depth less the 50 behind the floor; the channel is the width less 33."""
    h, _, w, d, _ = PARTS[name]
    doc = device_yaml(name)
    duct = doc["views"]["front"]["guides"][0]
    assert duct["kind"] == "duct" and duct["run"] == "y"
    assert close(duct["size"][0], w - 33.0) and close(duct["size"][1], h)
    assert close(duct["at"][0], 16.5) and close(duct["finger-pitch"], RU)
    base = contract(f"chatsworth/velocity-{name}-base")
    assert close(base["size"]["w"], w) and close(base["size"]["h"], h)
    assert close(base["size"]["d"], d - (DEPTH_WITHOUT_DOORS - USABLE_DEPTH))
    door = contract(f"chatsworth/velocity-{name}-door")
    assert door["lid"] is True and door["behaviour"] == "mounts"
    assert max(f["out"] for f in door["relief"]["features"]) == base["size"]["d"], "the door is the front of the table's depth"
    assert min(f["lift"] for f in door["relief"]["features"]) == USABLE_DEPTH, "the door's rails start where the guides end"
    finger = contract("chatsworth/velocity-vcm-finger")
    assert max(f["out"] for f in finger["relief"]["features"]) == USABLE_DEPTH, "the guides end at the 241"


@pytest.mark.parametrize("name", list(PARTS))
def test_a_finger_to_each_rack_unit_down_both_sides_one_rack_unit_apart(name):
    _, ru, w, _, _ = PARTS[name]
    doc = device_yaml(name)
    for side in ("left", "right"):
        ps = placements(doc, f"finger-{side}-")
        assert len(ps) == ru, (name, side)
        ys = [p["at"][1] for p in ps]
        assert [round(b - a, 2) for a, b in zip(ys, ys[1:])] == [RU] * (ru - 1)
        assert {p["ref"] for p in ps} == {"chatsworth/velocity-vcm-finger@1"}
    left, right = placements(doc, "finger-left-"), placements(doc, "finger-right-")
    assert {p["at"][0] for p in left} == {0.0} and {p["at"][0] for p in right} == {w - WALL}


@pytest.mark.parametrize("name", list(PARTS))
def test_the_finger_and_the_wall_are_the_ones_the_six_inch_managers_place(name):
    """A wall is 16.5 wide and the height of the manager on every width, so a height has one wall and the whole
    family has one finger: neither is drawn again under another part number."""
    h, _, w, _, _ = PARTS[name]
    doc = device_yaml(name)
    walls = placements(doc, "wall-")
    assert {p["ref"] for p in walls} == {f"chatsworth/velocity-13902-{name[6:]}-wall@1"}
    assert sorted(p["at"][0] for p in walls) == [0.0, w - WALL]
    wall = contract(walls[0]["ref"])
    assert close(wall["size"]["w"], WALL) and close(wall["size"]["h"], h)
    comps = LIB / "components" / "chatsworth"
    assert [p.name for p in comps.glob("velocity-*finger*")] == ["velocity-vcm-finger"]
    assert not list(comps.glob(f"velocity-{name}-wall")) and not list(comps.glob(f"velocity-{name}-finger"))


@pytest.mark.parametrize("name", list(PARTS))
def test_two_half_height_doors_cover_the_whole_height(name):
    h, _, w, _, _ = PARTS[name]
    doc = device_yaml(name)
    doors = placements(doc, "door-")
    assert [p["at"][1] for p in doors] == [0.0, h / 2]
    comp = contract(doors[0]["ref"])
    assert close(comp["size"]["h"] * 2, h) and comp["size"]["w"] == w


@pytest.mark.parametrize("name", list(PARTS))
def test_the_door_is_plastic_on_the_narrow_managers_and_steel_on_the_wide_ones(name):
    w = PARTS[name][2]
    assert contract(f"chatsworth/velocity-{name}-door")["attrs"]["material"] == DOOR_MATERIAL[w]
    assert DOOR_MATERIAL[w].lower() in device_yaml(name)["attrs"]["physical"]["material"].lower()


@pytest.mark.parametrize("name", list(PARTS))
def test_the_gaps_say_what_the_pages_do_not(name):
    doc = device_yaml(name)
    gaps = {g["what"] for g in doc["gaps"]}
    assert {"rear-openings", "finger-shape", "section-joint", "door-hinge", "door-bevel", "width-construction"} <= gaps
    assert "performance" not in doc["attrs"], "the data sheet points to a cable fill table and states no figure"


def test_no_model_name_the_pages_do_not_print_is_used():
    """The held pages say 'Velocity Single-Sided Vertical Cable Manager'; the issue's own name for another
    line is not a model name here."""
    text = ""
    for fam in ("13901", "13904", "13905"):
        for p in (LIB / "devices" / "chatsworth").glob(f"{fam}-7*/device.yaml"):
            text += p.read_text()
        for p in (LIB / "components" / "chatsworth").glob(f"velocity-{fam}-*/v1/contract.yaml"):
            text += p.read_text()
    assert text and "G3" not in text


@pytest.mark.parametrize("name", list(PARTS))
def test_the_part_stands_beside_a_rack_on_either_side_and_two_on_one_side_overlap(name):
    _, ru, _, _, _ = PARTS[name]
    lab = {"format": 1, "kind": "lab", "name": "velocity-single-sided", "rack": {"height-ru": ru},
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
    h, ru, w, _, _ = PARTS[name]
    root = ET.parse(DIST / f"{name}.base.front.svg").getroot()
    el = {e.get("id"): e for e in root.iter() if e.get("id")}["guide--duct"]
    assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "y"
    assert float(el.get("data-guide-finger-pitch")) == RU
    assert close(float(el.get("width")), w - 33.0) and close(float(el.get("height")), h)
    r = json.loads((DIST / "rack.json").read_text())["devices"][name]
    assert r["mount"] == "rack-side" and r["ru"] == ru and close(r["w"], w, 0.01)

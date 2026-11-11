"""Chatsworth Velocity double-sided vertical cable managers 13911, 13912, 13914 and 13915 (3.6, 6, 10 and 12 in
wide), each for 6, 7 and 8 ft racks.

Every figure is what the Velocity Cable Management data sheet (ordering table, "Double-Sided Vertical Cable
Managers") prints, in the units it prints them: height, width and depth with the rack height each part is sold for,
and the table's note: 16 in (406 mm) deep without doors, usable depth 191 mm at the front and 140 mm at the rear,
usable width 33 mm less than overall. What no held page dimensions (a finger, the section of a wall or a door, the
mid panel between the two channels) is estimated in the device and is held here only to what the model itself
declares.

Each part is a `rack-side` manager, drawn as it stands beside a rack: portrait, taking no rack unit, with two
channels back to back, each with a `duct` guide run down its height, a finger to each rack unit down both sides and
a door in two halves.
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
DOOR_T = 3.0

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# part -> (height mm, rack units, width mm, depth mm, shipping weight kg): the ordering table, "H x W x D in (mm)",
# for 6'H 38U, 7'H 45U and 8'H 51U racks.
PARTS = {
    "13911-701": (1778.0, 38, 91.0, 417.0, 10.4),
    "13911-703": (2045.0, 45, 91.0, 417.0, 11.8),
    "13911-715": (2311.0, 51, 91.0, 417.0, 12.2),
    "13912-701": (1778.0, 38, 152.0, 422.0, 11.8),
    "13912-703": (2045.0, 45, 152.0, 422.0, 12.7),
    "13912-715": (2311.0, 51, 152.0, 422.0, 13.6),
    "13914-701": (1778.0, 38, 254.0, 445.0, 16.8),
    "13914-703": (2045.0, 45, 254.0, 445.0, 18.1),
    "13914-715": (2311.0, 51, 254.0, 445.0, 20.0),
    "13915-701": (1778.0, 38, 305.0, 446.0, 18.1),
    "13915-703": (2045.0, 45, 305.0, 446.0, 19.5),
    "13915-715": (2311.0, 51, 305.0, 446.0, 21.3),
}
DEPTH_WITHOUT_DOORS = 406.0      # "16 inches deep (406 mm) without doors"
FRONT_USABLE = 191.0             # "Usable depth in the front of the manager is 7.5 inches (191 mm)."
REAR_USABLE = 140.0              # "Usable depth at the rear of the manager is 5.5 inches (140 mm)."
MID = DEPTH_WITHOUT_DOORS - FRONT_USABLE - REAR_USABLE
# "covers on 3.6 in (91 mm) and 6 in (152 mm) managers are plastic; covers on 10 in (254 mm) and 12 in (305 mm)
# managers are steel with plastic hinges"
DOOR_MATERIAL = {91.0: "Plastic", 152.0: "Plastic", 254.0: "Steel", 305.0: "Steel"}
FACES = {"front": FRONT_USABLE, "rear": REAR_USABLE}


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "chatsworth" / name / "device.yaml").read_text())


def contract(ref):
    return yaml.safe_load((LIB / "components" / ref.split("@")[0] / "v1" / "contract.yaml").read_text())


def placements(doc, view, stem):
    return [p for p in doc["views"][view]["components"]["placements"] if p["id"].startswith(stem)]


def bevel(depth):
    """What each door stands past the ends of the guides: the table's depth less the 406, shared by the two doors."""
    return (depth - DEPTH_WITHOUT_DOORS) / 2


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
    for view in ("front", "rear"):
        assert doc["views"][view]["size"] == {"w": w, "h": h}
    for view in ("left", "right", "top", "bottom"):
        assert doc["views"][view]["size"] == ({"w": d, "h": h} if view in ("left", "right") else {"w": w, "h": d})


@pytest.mark.parametrize("name", list(PARTS))
def test_each_channel_is_the_usable_width_and_the_two_wells_leave_the_mid_panel(name):
    """The table's note: 406 deep without doors, 191 usable at the front, 140 at the rear, 33 off the width for the
    usable width. Each well runs from the outside of its door to its floor; what is left of the 406 between the two
    floors is the mid panel."""
    h, _, w, d, _ = PARTS[name]
    doc = device_yaml(name)
    for view, duct_id in (("front", "duct"), ("rear", "rear-duct")):
        duct = doc["views"][view]["guides"][0]
        assert duct["id"] == duct_id and duct["kind"] == "duct" and duct["run"] == "y"
        assert close(duct["size"][0], w - 33.0) and close(duct["size"][1], h)
        assert close(duct["at"][0], WALL) and close(duct["finger-pitch"], RU)
    wells = {}
    for face, usable in FACES.items():
        base = contract(f"chatsworth/velocity-{name}-{face}-base")
        assert close(base["size"]["w"], w) and close(base["size"]["h"], h)
        assert close(base["size"]["d"], usable + bevel(d)), face
        wells[face] = base["size"]["d"]
    assert close(d - sum(wells.values()), MID), "the two floors stand 75 apart, the 406 less the two usable depths"


@pytest.mark.parametrize("name", list(PARTS))
def test_each_door_stands_at_the_front_of_its_well_and_its_rails_start_where_the_guides_end(name):
    _, _, _, d, _ = PARTS[name]
    for face, usable in FACES.items():
        base = contract(f"chatsworth/velocity-{name}-{face}-base")
        door = contract(f"chatsworth/velocity-{name}-{face}-door")
        assert door["lid"] is True and door["behaviour"] == "mounts"
        assert close(max(f["out"] for f in door["relief"]["features"]), base["size"]["d"]), face
        assert close(min(f["lift"] for f in door["relief"]["features"]), usable), face
        plate = [f for f in door["relief"]["features"] if f["node"] == "plate"][0]
        assert close(plate["out"] - plate["lift"], DOOR_T)


@pytest.mark.parametrize("name", list(PARTS))
def test_a_finger_to_each_rack_unit_down_both_sides_of_both_channels(name):
    _, ru, w, _, _ = PARTS[name]
    doc = device_yaml(name)
    refs = {"front": "chatsworth/velocity-vcm-finger@1", "rear": "chatsworth/velocity-vcm-tguide-rear@1"}
    ys = {}
    for face in FACES:
        for side in ("left", "right"):
            ps = placements(doc, face, f"{face}-finger-{side}-")
            assert len(ps) == ru, (name, face, side)
            col = [p["at"][1] for p in ps]
            assert [round(b - a, 2) for a, b in zip(col, col[1:])] == [RU] * (ru - 1)
            assert {p["ref"] for p in ps} == {refs[face]}
            ys[(face, side)] = col
            assert {p["at"][0] for p in ps} == ({0.0} if side == "left" else {w - WALL})
    assert len({tuple(v) for v in ys.values()}) == 1, "the rear fingers stand level with the front ones"
    for face, usable in FACES.items():
        finger = contract(refs[face])
        assert close(max(f["out"] for f in finger["relief"]["features"]), usable), "the guides end where the usable depth does"


@pytest.mark.parametrize("name", list(PARTS))
def test_the_walls_are_the_height_of_the_manager_on_both_faces(name):
    h, _, w, _, _ = PARTS[name]
    doc = device_yaml(name)
    for face in FACES:
        walls = placements(doc, face, f"{face}-wall-")
        assert {p["ref"] for p in walls} == {f"chatsworth/velocity-13902-{name[6:]}-wall@1"}
        assert sorted(p["at"][0] for p in walls) == [0.0, w - WALL]
        wall = contract(walls[0]["ref"])
        assert close(wall["size"]["w"], WALL) and close(wall["size"]["h"], h)


@pytest.mark.parametrize("name", list(PARTS))
def test_two_half_height_doors_cover_the_whole_height_on_each_face(name):
    h, _, w, _, _ = PARTS[name]
    doc = device_yaml(name)
    for face in FACES:
        doors = placements(doc, face, f"{face}-door-")
        assert [p["at"][1] for p in doors] == [0.0, h / 2]
        comp = contract(doors[0]["ref"])
        assert close(comp["size"]["h"] * 2, h) and comp["size"]["w"] == w


@pytest.mark.parametrize("name", list(PARTS))
def test_the_door_is_plastic_on_the_narrow_managers_and_steel_on_the_wide_ones(name):
    w = PARTS[name][2]
    for face in FACES:
        assert contract(f"chatsworth/velocity-{name}-{face}-door")["attrs"]["material"] == DOOR_MATERIAL[w]
    assert DOOR_MATERIAL[w].lower() in device_yaml(name)["attrs"]["physical"]["material"].lower()


@pytest.mark.parametrize("name", list(PARTS))
def test_the_gaps_say_what_the_pages_do_not(name):
    doc = device_yaml(name)
    gaps = {g["what"] for g in doc["gaps"]}
    assert {"mid-panel", "rear-channel", "finger-shape", "section-joint", "door-hinge", "door-bevel",
            "usable-split", "construction-source"} <= gaps
    assert "performance" not in doc["attrs"], "the data sheet points to a cable fill table and states no figure"


def test_the_two_figures_the_table_prints_twice_are_stated_with_both():
    """13911-703 prints 25 lb (11.8 kg) and 25 lb is 11.3 kg; 13915 prints 17.8 in (446 mm) and 17.8 in is 452 mm.
    Each part says so and draws the figure in millimetres as printed."""
    weight = device_yaml("13911-703")["provenance"]["weight"]["note"]
    assert "25 lb" in weight and "11.8" in weight and "11.3" in weight
    for suf in ("701", "703", "715"):
        note = device_yaml(f"13915-{suf}")["provenance"]["chassis"]["note"]
        assert "17.8" in note and "446" in note and "452" in note
        assert "depth" in {g["what"] for g in device_yaml(f"13915-{suf}")["gaps"]}


def test_no_model_name_the_pages_do_not_print_is_used():
    """The held pages say 'Velocity Double-Sided Vertical Cable Manager'; a name for another product line,
    which no held page uses, is not a model name here."""
    text = ""
    for fam in ("13911", "13912", "13914", "13915"):
        for p in (LIB / "devices" / "chatsworth").glob(f"{fam}-7*/device.yaml"):
            text += p.read_text()
        for p in (LIB / "components" / "chatsworth").glob(f"velocity-{fam}-*/v1/contract.yaml"):
            text += p.read_text()
    assert text and "G3" not in text


@pytest.mark.parametrize("name", list(PARTS))
def test_the_part_stands_beside_a_rack_on_either_side_and_two_on_one_side_overlap(name):
    _, ru, _, _, _ = PARTS[name]
    lab = {"format": 1, "kind": "lab", "name": "velocity-double-sided", "rack": {"height-ru": ru},
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
def test_the_built_faces_publish_a_vertical_duct_each_and_the_rack_catalogue_the_part(name):
    h, ru, w, _, _ = PARTS[name]
    for view, guide in (("front", "guide--duct"), ("rear", "guide--rear-duct")):
        root = ET.parse(DIST / f"{name}.base.{view}.svg").getroot()
        el = {e.get("id"): e for e in root.iter() if e.get("id")}[guide]
        assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "y"
        assert float(el.get("data-guide-finger-pitch")) == RU
        assert close(float(el.get("width")), w - 33.0) and close(float(el.get("height")), h)
    r = json.loads((DIST / "rack.json").read_text())["devices"][name]
    assert r["mount"] == "rack-side" and r["ru"] == ru and close(r["w"], w, 0.01)

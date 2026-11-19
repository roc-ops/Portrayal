"""Chatsworth Motive single-sided vertical cable managers 32610 to 32614 (6, 8, 10, 12 and 15 in wide), 7 ft, in black
and in Glacier White, with black fingers.

The Motive Cable Management data sheet (ordering matrix, "Choose Manager Style, Width, Color, and Height") prints a
width and a height as a nominal size and the overall depth of a single-sided manager, 15.5 in (392 mm), once. So the
depth is the data sheet's, the width and the height are the matrix's nominal figures taken as the overall size, and the
count and the shape of the T-shaped cable guides, the section of the frame and the door, and the central track are
estimated in the device and held here only to what the model itself declares.

Each part is a `rack-side` manager, drawn as it stands beside a rack: portrait, taking no rack unit, with a `duct`
guide run down its height, a T-shaped cable guide to each rack unit down both sides of it and one full-height door.
The guide is the one part every width and both colours place: it is not copied for another width.
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
HEIGHT = 2133.6                  # the matrix's 7' (2.1 m), 84 in
UNITS = 48                       # 84 in over one rack unit; no page counts them
DEPTH = 392.0                    # "Overall depth for Single-Sided manager is 15.5"D (392 mm)"
GUIDE_W = 20.0                   # estimated: no held page dimensions a guide
WIDTHS = {0: 150.0, 1: 200.0, 2: 250.0, 3: 300.0, 4: 380.0}   # the matrix's "6" (150)" to "15" (380)"
COLOURS = {"7": "Black", "E": "Glacier White"}
PARTS = {f"3261{w}-{c}03": (mm, COLOURS[c]) for w, mm in WIDTHS.items() for c in COLOURS}

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "chatsworth" / name.lower() / "device.yaml").read_text())


def contract(ref):
    """A component's contract: the major its ref names, else the newest the library holds."""
    name, _, major = ref.partition("@")
    folder = LIB / "components" / name
    major = f"v{major}" if major else max((p.name for p in folder.glob("v*")), key=lambda v: int(v[1:]))
    return yaml.safe_load((folder / major / "contract.yaml").read_text())


def placements(doc, stem):
    return [p for p in doc["views"]["front"]["components"]["placements"] if p["id"].startswith(stem)]


def test_the_ten_part_numbers_are_the_matrix_ones():
    assert sorted(PARTS) == ["32610-703", "32610-E03", "32611-703", "32611-E03", "32612-703", "32612-E03",
                             "32613-703", "32613-E03", "32614-703", "32614-E03"]
    assert sorted(p.name for p in (LIB / "devices" / "chatsworth").glob("3261*")) == sorted(p.lower() for p in PARTS)


@pytest.mark.parametrize("name", list(PARTS))
def test_the_envelope_is_the_nominal_size_and_the_printed_depth(name):
    w, colour = PARTS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "Chatsworth Products" and doc["model"] == name
    assert close(c["width"], w) and close(c["height"], HEIGHT) and close(c["depth"], DEPTH)
    assert c["mount"] == "rack-side" and c["shell"] == "sheet" and c["ru"] == UNITS
    assert c["height"] > c["width"], "a vertical manager is drawn as it stands, portrait"
    assert doc["views"]["front"]["size"] == {"w": w, "h": HEIGHT}
    chassis = doc["provenance"]["chassis"]
    assert chassis["confidence"] == "estimated" and "nominal" in chassis["note"].lower(), \
        "the width and the height are the matrix's nominal sizes, which the device says"
    assert doc["attrs"]["physical"]["color"] == colour
    assert "weight-kg" not in doc["attrs"]["physical"], "no held page gives the weight of a manager"


@pytest.mark.parametrize("name", list(PARTS))
def test_the_channel_is_the_width_less_a_guide_each_side_and_the_door_stands_at_the_depth(name):
    w, _ = PARTS[name]
    doc = device_yaml(name)
    duct = doc["views"]["front"]["guides"][0]
    assert duct["kind"] == "duct" and duct["run"] == "y" and duct["confidence"] == "estimated"
    assert close(duct["size"][0], w - 2 * GUIDE_W) and close(duct["size"][1], HEIGHT)
    assert close(duct["at"][0], GUIDE_W) and close(duct["finger-pitch"], RU)
    door = contract(f"chatsworth/motive-{name.lower()}-door")
    assert door["lid"] is True and door["behaviour"] == "mounts"
    assert max(f["out"] for f in door["relief"]["features"]) == DEPTH, "the door is the front of the printed depth"
    guide = contract("chatsworth/motive-vcm-guide")
    assert max(f["out"] for f in guide["relief"]["features"]) <= min(f["lift"] for f in door["relief"]["features"])


@pytest.mark.parametrize("name", list(PARTS))
def test_a_guide_to_each_rack_unit_down_both_sides_one_rack_unit_apart(name):
    w, _ = PARTS[name]
    doc = device_yaml(name)
    for side in ("left", "right"):
        ps = placements(doc, f"guide-{side}-")
        assert len(ps) == UNITS, (name, side)
        ys = [p["at"][1] for p in ps]
        assert [round(b - a, 2) for a, b in zip(ys, ys[1:])] == [RU] * (UNITS - 1)
        assert {p["ref"] for p in ps} == {"chatsworth/motive-vcm-guide@1"}
    left, right = placements(doc, "guide-left-"), placements(doc, "guide-right-")
    assert {p["at"][0] for p in left} == {0.0} and {p["at"][0] for p in right} == {w - GUIDE_W}
    count = doc["provenance"]["fingers"]
    assert count["confidence"] == "estimated" and "rack unit" in count["note"].lower()


def test_one_guide_serves_every_width_and_both_colours():
    comps = LIB / "components" / "chatsworth"
    assert [p.name for p in comps.glob("motive-*guide*")] == ["motive-vcm-guide"]
    guide = contract("chatsworth/motive-vcm-guide")
    assert guide["attrs"]["material"] == "Plastic"
    assert guide["size-confidence"]["w"] == "estimated"
    assert guide["size"]["w"] == GUIDE_W and close(guide["size"]["h"], RU)
    refs = {p["ref"] for name in PARTS for p in placements(device_yaml(name), "guide-")}
    assert refs == {"chatsworth/motive-vcm-guide@1"}, "a part number draws no guide of its own"


@pytest.mark.parametrize("name", list(PARTS))
def test_one_full_height_door_covers_the_front(name):
    w, _ = PARTS[name]
    doc = device_yaml(name)
    doors = placements(doc, "door")
    assert [p["at"] for p in doors] == [[0.0, 0.0]], "the data sheet lists one dual-hinged front door"
    comp = contract(doors[0]["ref"])
    assert comp["size"]["w"] == w and close(comp["size"]["h"], HEIGHT)
    assert "door-hinge" in {g["what"] for g in doc["gaps"]}


def test_the_two_colours_differ_in_the_frame_and_the_door_and_agree_in_the_guide():
    for width in WIDTHS:
        black, white = f"3261{width}-703", f"3261{width}-E03"
        for part in ("frame", "door"):
            a = contract(f"chatsworth/motive-{black.lower()}-{part}")
            b = contract(f"chatsworth/motive-{white.lower()}-{part}")
            assert a["size"] == b["size"] and a != b
        assert device_yaml(black)["chassis"]["color"] != device_yaml(white)["chassis"]["color"]
        assert "Black powder coat" in device_yaml(black)["attrs"]["physical"]["finish"]
        assert "Glacier White powder coat" in device_yaml(white)["attrs"]["physical"]["finish"]


@pytest.mark.parametrize("name", list(PARTS))
def test_the_gaps_say_what_the_pages_do_not(name):
    doc = device_yaml(name)
    gaps = {g["what"] for g in doc["gaps"]}
    assert {"cable-capacity", "door-hinge", "finger-shape", "finger-count", "nominal-size", "central-track",
            "accessories", "color-shade"} <= gaps
    assert all(g["reason"] == "vendor-silent" for g in doc["gaps"])
    assert "performance" not in doc["attrs"], "the data sheet points to a cable fill table and states no figure"


@pytest.mark.parametrize("name", list(PARTS))
def test_the_part_stands_beside_a_rack_on_either_side_and_two_on_one_side_overlap(name):
    lab = {"format": 1, "kind": "lab", "name": "motive-single-sided", "rack": {"height-ru": UNITS},
           "devices": [{"id": "l", "ref": name.lower(), "side": "left"}, {"id": "r", "ref": name.lower(), "side": "right"}],
           "links": []}
    assert labs.schema_errors(lab) == []
    found, placed = labs.check(lab, [LIB])
    assert [c for c, sev, _ in found if sev == "error"] == [], found
    got = {p["id"]: p for p in placed}
    assert (got["l"]["side"], got["l"]["mount"], got["l"]["ru"]) == ("left", "rack-side", 1)
    assert got["r"]["side"] == "right"
    lab["devices"] = [{"id": "a", "ref": name.lower(), "side": "left"}, {"id": "b", "ref": name.lower(), "side": "left"}]
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
    w, _ = PARTS[name]
    root = ET.parse(DIST / f"{name.lower()}.base.front.svg").getroot()
    el = {e.get("id"): e for e in root.iter() if e.get("id")}["guide--duct"]
    assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "y"
    assert float(el.get("data-guide-finger-pitch")) == RU
    assert close(float(el.get("width")), w - 2 * GUIDE_W) and close(float(el.get("height")), HEIGHT)
    r = json.loads((DIST / "rack.json").read_text())["devices"][name.lower()]
    assert r["mount"] == "rack-side" and r["ru"] == UNITS and close(r["w"], w, 0.01)

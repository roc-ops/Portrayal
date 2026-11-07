"""Eaton Tripp Lite series SmartRack horizontal cable ducts (roc-ops/Portrayal#1094, part of #1091):
the three 1U finger ducts SRCABLEDUCT1U, SRCABLEDUCT1UHD and SRCABLEDUCT1UFC.

Every figure below is what the maker's own spec sheet or submittal drawing states, in inches as
printed and converted here, so a model that drifts from its source fails by name. The rack kit's
half of the features (a cable laid along a duct, through a pass, a part on the rear face) is
`spec/tests/js/rack-tripplite-ducts.mjs`, run by `test_rack_kit_js.py`.

These read the build (`library/dist`, `library/exports`) and skip without it, like the other
sweeps over compiled drawings.
"""
import json
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
EXPORTS = LIB / "exports"
MM = 25.4

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# name -> (width in, height in, depth in, weight kg)
# 1U: the spec sheet "1.720 x 19.000 x 2.660" (hwd) and the submittal drawing 43.69 x 482.60 x 67.71 mm
# 1UHD: the spec sheet's INCH row "2.040 x 19.000 x 4.660" (its cm row disagrees and is not used)
# 1UFC: "4.130 x 2.170 x 19.480" is printed out of order: 19.48 is the width, and the part being 1U
#       the height is the 2.170 and the depth the 4.130
SIZES = {
    "srcableduct1u": (19.00, 1.72, 2.67, 0.59),
    "srcableduct1uhd": (19.00, 2.04, 4.66, 1.18),
    "srcableduct1ufc": (19.48, 2.17, 4.13, 0.68),
}
# name -> (slots a wall, slot gap, finger pitch, walls, face width mm, duct length mm)
FINGERS = {
    "srcableduct1u": (24, 8.0, 18.0, 2, 482.6, 431.8),
    "srcableduct1uhd": (9, 34.0, 46.0, 2, 482.6, 431.8),
    "srcableduct1ufc": (24, 8.0, 18.0, 2, 494.79, 431.8),
}
COMPONENT = {"srcableduct1u": "tripplite-duct-1u", "srcableduct1uhd": "tripplite-duct-1uhd",
             "srcableduct1ufc": "tripplite-duct-1ufc"}
ALL = list(SIZES)
DARK, WHITE = "#101214", "#ffffff"


def svg(name, view, config="base"):
    return ET.parse(DIST / f"{name}.{config}.{view}.svg").getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "eaton" / name / "device.yaml").read_text())


def contract(name, part):
    return yaml.safe_load((LIB / "components/eaton" / f"{COMPONENT[name]}-{part}" / "v1/contract.yaml").read_text())


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def luminance(hexcolour):
    c = [int(hexcolour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def shade(hexcolour):
    """the kit's outline shade of a fill: each channel times 61/100, rounded half up"""
    return "#" + "".join(f"{(int(hexcolour[i:i + 2], 16) * 61 + 50) // 100:02x}" for i in (1, 3, 5))


# --- each device's envelope against its source ----------------------------------------------------

@pytest.mark.parametrize("name", ALL)
def test_each_duct_is_the_size_its_maker_states(name):
    w, h, d, kg = SIZES[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    # the drawing prints millimetres, so its 2.67 in is 67.71 and not 67.82: within a tenth of an inch's rounding
    assert close(c["width"], w * MM, 0.15) and close(c["height"], h * MM, 0.15) and close(c["depth"], d * MM, 0.15)
    assert c["ru"] == 1 and c["mount"] == "rack-face" and c["shell"] == "sheet"
    assert doc["manufacturer"] == "Eaton" and doc["model"] == name.upper()
    assert doc["attrs"]["physical"]["weight-kg"] == kg == c["weight-kg"]
    # a rack-face part states neither a full depth nor ears (L125)
    assert "full-depth" not in c and "ears" not in c


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_rack_catalogue_carries_the_unit_and_the_face(name):
    w, h, d, _kg = SIZES[name]
    r = rack(name)
    assert r["ru"] == 1 and close(r["w"], w * MM, 0.15) and close(r["d"], d * MM, 0.15)
    assert r["mount"] == "rack-face"


def test_the_1u_depth_and_ear_line_are_the_drawings_dimensions():
    """The top view of the submittal drawing: 67.71 overall, 62.71 from the front of the cover to the
    ears' flange, so the back plate stands 5.0 behind it and the slots are 49.78 long."""
    doc = device_yaml("srcableduct1u")
    top = doc["views"]["top"]["panel"]["decor"]
    back = next(e for e in top if e["id"] == "back")
    slot = next(e for e in top if e["id"] == "slot-1")
    assert doc["chassis"]["depth"] == 67.71 and back["size"][1] == 5.0
    assert close(doc["chassis"]["depth"] - back["size"][1], 62.71, 0.001)
    assert slot["size"][1] == 49.78 and slot["size"][0] == 8.0
    # the bar between two slots is the drawing's 10 mm
    nxt = next(e for e in top if e["id"] == "slot-2")
    assert close(nxt["at"][0] - slot["at"][0] - slot["size"][0], 10.0, 1e-6)


def test_the_1u_size_conflict_is_settled_on_the_makers_own_documents():
    note = device_yaml("srcableduct1u")["provenance"]["size-conflict"]["note"]
    assert "1.77 x 3.9 x 19.13" in note and "submittal drawing" in note and "not used" in note


@pytest.mark.parametrize("name,what", [("srcableduct1uhd", "dimensions"), ("srcableduct1ufc", "dimensions")])
def test_a_conflicting_spec_sheet_is_a_gap_and_the_inch_figure_is_in_the_note(name, what):
    doc = device_yaml(name)
    gap = next(g for g in doc["gaps"] if g["what"] == what)
    assert gap["reason"] == "sources-disagree"
    assert doc["provenance"]["size-conflict"]["confidence"] == "estimated"
    # no drawing was found for either: they say so, and what is estimated
    assert any(g["what"] == "drawing" and g["reason"] == "needs-drawing" for g in doc["gaps"])


# --- the fingers: a duct guide, the slots drawn on its pitch, a wall each of top and bottom ------------

@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_each_duct_publishes_its_duct_with_the_counted_pitch_and_gap(name):
    slots, gap, pitch, _walls, face_w, length = FINGERS[name]
    el = by_id(svg(name, "front"))["guide--duct"]
    assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "x"
    assert float(el.get("data-guide-finger-pitch")) == pitch and float(el.get("data-guide-finger-gap")) == gap
    assert float(el.get("width")) == length and close(float(el.get("x")), (face_w - length) / 2, 0.01)
    # the clear height between the two walls, inside the part
    assert 0 < float(el.get("height")) < device_yaml(name)["chassis"]["height"]
    assert rack(name)["guides"] == {"front": ["duct"]}
    guide = device_yaml(name)["views"]["front"]["guides"][0]
    assert guide["confidence"] == "estimated", "the pitch is counted on a picture, never dimensioned"


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_slots_are_counted_on_the_stated_pitch_in_both_walls(name):
    slots, gap, pitch, *_ = FINGERS[name]
    for view in ("top", "bottom"):
        el = by_id(svg(name, view))
        found = sorted((e for i, e in el.items() if re.fullmatch(r"slot-\d+", i)), key=lambda e: float(e.get("x")))
        assert len(found) == slots, view
        assert [round(float(b.get("x")) - float(a.get("x")), 3) for a, b in zip(found, found[1:])] == [pitch] * (slots - 1)
        assert all(float(s.get("width")) == gap for s in found)


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_each_wall_is_its_fingers_end_on_with_a_slot_between_each_pair(name):
    slots = FINGERS[name][0]
    el = by_id(svg(name, "front", "cover-off"))
    for wall in ("fingers-upper", "fingers-lower"):
        assert wall in el
        fingers = [i for i in el if re.fullmatch(wall + r"--f\d+", i)]
        assert len(fingers) == slots + 1, wall


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_fingers_are_attached_to_the_body_at_their_real_depth(name):
    """A finger stands from the root, the root from the floor of the well, and the rim runs from the
    finger tips to the front: no finger is a flat tongue, none floats, and the slot is closed at both
    ends (the maker draws punched slots)."""
    el = by_id(svg(name, "front", "cover-off"))
    well = float(el["base"].get("data-depth"))

    def out(node):    # height above the floor of the well, from the compiled relief
        return well + float(node.get("data-z-out"))

    for wall in ("fingers-upper", "fingers-lower"):
        root, rim = el[f"{wall}--root"], el[f"{wall}--rim"]
        bars = [e for i, e in el.items() if re.fullmatch(wall + r"--f\d+", i)]
        assert root.get("data-z-lift") is None, "the root stands on the floor"
        assert {round(float(b.get("data-z-lift")), 2) for b in bars} == {round(out(root), 2)}, "fingers stand on the root"
        assert {round(out(b), 2) for b in bars} == {round(float(rim.get("data-z-lift")), 2)}, "and carry the rim"
        assert close(out(rim), well, 0.01), "the rim runs to the front"
        # the slot is the stated length: the 1U's dimensioned 49.78 mm
    if name == "srcableduct1u":
        root, bar = el["fingers-upper--root"], el["fingers-upper--f1"]
        assert close(out(bar) - out(root), 49.78, 0.01)


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_back_plate_runs_the_full_width_on_the_front_and_the_rear(name):
    face_w = FINGERS[name][4]
    front = by_id(svg(name, "front"))
    rear = svg(name, "rear")
    assert close(float(front["base"].get("data-depth")) + 5.2, device_yaml(name)["chassis"]["depth"], 0.01)
    contract_size = contract(name, "base")["size"]
    assert close(contract_size["w"], face_w, 0.001), "the well's floor is the whole face, ears included"
    # the rear paints the plate from end to end: its plates (or the one back plate) reach both edges
    rects = [e for e in rear.iter() if e.tag.endswith("rect") and e.get("data-kind") in ("base",)]
    assert rects and min(float(r.get("x")) for r in rects) == 0
    assert close(max(float(r.get("x")) + float(r.get("width")) for r in rects), face_w, 0.01)


# --- passes: only where a source states them -----------------------------------------------------------

@needs_dist
def test_the_fibre_duct_draws_two_open_rear_windows_the_cable_crosses():
    root = svg("srcableduct1ufc", "rear")
    passes = [e for e in root.iter() if e.get("data-class") == "pass"]
    assert [p.get("data-pass") for p in passes] == ["rear-window-1", "rear-window-2"]
    assert {p.get("data-pass-shape") for p in passes} == {"rect"} and {p.get("data-pass-cover") for p in passes} == {"open"}
    assert rack("srcableduct1ufc")["passes"]["rear"] == ["rear-window-1", "rear-window-2"]
    # the floor of the well is open there, so the front sees through it with the cover off
    floor = by_id(svg("srcableduct1ufc", "front", "cover-off"))["base--floor"]
    assert floor.get("d").count("M") >= 7, "the plate, four ear slots and the two windows are one path"
    # the windows stand inside the plate and apart from each other
    a, b = passes
    assert float(a.get("x")) + float(a.get("width")) < float(b.get("x"))
    assert all(float(p.get("y")) > 0 and float(p.get("y")) + float(p.get("height")) < 55.12 for p in passes)


@pytest.mark.parametrize("name", ["srcableduct1u", "srcableduct1uhd"])
def test_the_other_two_draw_no_pass_through_because_no_source_shows_one(name):
    assert "passes" not in json.dumps(device_yaml(name)["views"])


# --- covers: ship fitted, come off, no hinge invented --------------------------------------------------

@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_cover_ships_fitted_and_is_a_removable_part(name):
    cfgs = device_yaml(name)["configurations"]
    assert cfgs["base"]["default"] is True and cfgs["cover-off"]["kind"] == "example"
    on, off = by_id(svg(name, "front")), by_id(svg(name, "front", "cover-off"))
    assert "cover" in on and on["cover"].get("data-behaviour") == "mounts", "fitted as it ships, with a pull handle"
    assert "cover" not in off and not any(i.startswith("cover") for i in off)
    assert contract(name, "cover")["lid"] is True
    # the fingers and the channel are there with it off
    assert "fingers-upper--f1" in off and "guide--duct" in off


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_taking_the_cover_off_takes_it_off_every_face_and_leaves_the_fingers(name):
    for view in ("top", "bottom", "left", "right"):
        on, off = by_id(svg(name, view)), by_id(svg(name, view, "cover-off"))
        assert any(i.startswith("cover") for i in on), view
        assert not any(i.startswith("cover") for i in off), view
    for view in ("top", "bottom"):
        slots = [i for i in by_id(svg(name, view, "cover-off")) if re.fullmatch(r"slot-\d+", i)]
        assert len(slots) == FINGERS[name][0], f"{view}: the slots show with the cover off"


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_cover_is_drawn_as_a_plate_with_lips_at_the_walls_depth_not_a_slab(name):
    el = by_id(svg(name, "front"))
    well = float(el["base"].get("data-depth"))
    plate, lip_t, lip_b = el["cover--plate"], el["cover--lip-top"], el["cover--lip-bottom"]
    rim = by_id(svg(name, "front", "cover-off"))["fingers-upper--rim"]
    # the plate is at the front face; the lips reach back to where the rim begins (the finger tips)
    assert close(well + float(plate.get("data-z-out")), well, 0.01)
    assert close(well + float(lip_t.get("data-z-out")), well, 0.01)
    assert close(float(lip_t.get("data-z-lift")), float(rim.get("data-z-lift")), 0.01)
    assert close(float(lip_b.get("data-z-lift")), float(lip_t.get("data-z-lift")), 0.01)
    # the lips lie outside the walls (above the upper, below the lower) and the plate spans both
    wall_u = float(el["fingers-upper"].get("transform").split(",")[1].rstrip(")"))
    assert float(el["cover"].get("transform").split(",")[1].rstrip(")")) < wall_u


@pytest.mark.parametrize("name", ALL)
def test_no_mechanism_is_invented_for_a_cover_hinge_or_clip(name):
    doc = device_yaml(name)
    text = json.dumps({"views": doc["views"], "chassis": doc["chassis"]}).lower()
    assert "hinge" not in text and "clip" not in text and "latch" not in text
    for part in ("cover", "cover-plan", "cover-side"):
        elements = json.dumps(contract(name, part).get("elements", {})).lower()
        assert "hinge" not in elements and "clip" not in elements
    if name == "srcableduct1uhd":
        assert any(g["what"] == "cover-hinge" for g in doc["gaps"]), "the dual hinge is a gap, never drawn"


def test_the_snap_on_cover_of_the_fibre_duct_is_a_removable_part_not_a_hinge():
    doc = device_yaml("srcableduct1ufc")
    c = contract("srcableduct1ufc", "cover")
    assert c["lid"] is True and c["behaviour"] == "mounts"
    assert "snap-on" in c["provenance"]["lid"] and "snaps off" in doc["description"]
    assert not any(g["what"] == "cover-hinge" for g in doc["gaps"])


# --- front or rear mounting (1UFC) ------------------------------------------------------------------------

def test_the_fibre_duct_is_one_part_for_either_face_and_says_so():
    note = device_yaml("srcableduct1ufc")["provenance"]["mount"]["note"]
    assert "front or" in note and "rear" in note and "rack-face" in note
    # no front-only and rear-only twins: the face is the placement's to say (the kit test places it)
    assert not (LIB / "devices/eaton/srcableduct1ufc-rear").exists()


# --- bend radius and cable capacity: only what a source states ---------------------------------------------

@pytest.mark.parametrize("name", ALL)
def test_no_capacity_or_bend_radius_is_recorded_because_no_source_states_one(name):
    doc = device_yaml(name)
    perf = doc["attrs"].get("performance") or {}
    assert "cable-capacity" not in perf and "bend-radius" not in json.dumps(doc["attrs"])
    assert any(g["what"] == "cable-capacity" and g["reason"] == "vendor-silent" for g in doc["gaps"])
    if name == "srcableduct1ufc":
        assert any(g["what"] == "bend-radius" and g["reason"] == "vendor-silent" for g in doc["gaps"])


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_rack_catalogue_has_no_capacity_to_compare(name):
    assert rack(name).get("capacity") in (None, {})


# --- colour: a field the configuration sets, readable on both stages -----------------------------------------

@pytest.mark.parametrize("name", ALL)
def test_the_finish_is_a_field_each_part_declares_and_the_base_configuration_sets(name):
    prefix = COMPONENT[name]
    attrs = device_yaml(name)["configurations"]["base"]["component-attrs"]
    assert set(attrs) == {f"{prefix}-{p}" for p in ("base", "fingers", "cover", "cover-plan", "cover-side")}
    for part in ("base", "fingers", "cover", "cover-plan", "cover-side"):
        c = contract(name, part)
        assert c["fields"]["finish"]["default"] == attrs[f"{prefix}-{part}"]["finish"]
        # a relief feature on a node painted from the finish states no colour: its 3D sides follow
        # the field (lint L73 holds this)
        skin = (LIB / "components/eaton" / f"{prefix}-{part}" / "v1/skins/default.svg").read_text()
        assert "data-fill-from=\"finish\"" in skin


def test_the_fibre_duct_is_yellow_and_reads_on_the_light_and_the_dark_stage():
    attrs = device_yaml("srcableduct1ufc")["configurations"]["base"]["component-attrs"]
    yellow = attrs["tripplite-duct-1ufc-cover"]["finish"]
    r, g, b = (int(yellow[i:i + 2], 16) for i in (1, 3, 5))
    assert r > 200 and g > 160 and b < 40, "yellow"
    assert contrast(yellow, DARK) >= 3, "the fill against the dark stage"
    assert contrast(shade(yellow), WHITE) >= 3, "its outline, which the kit derives, against the light one"
    skin = (LIB / "components/eaton/tripplite-duct-1ufc-cover/v1/skins/default.svg").read_text()
    assert 'data-stroke-derive="finish"' in skin and f'stroke="{shade(yellow)}"' in skin


@pytest.mark.parametrize("name", ["srcableduct1u", "srcableduct1uhd"])
def test_the_black_ducts_read_on_both_stages_by_the_lit_edge_and_the_plate(name):
    cover = contract(name, "cover")
    plate = cover["fields"]["finish"]["default"]
    lip = next(f for f in cover["relief"]["features"] if f["node"] == "lip-top")["color"]
    assert contrast(plate, WHITE) >= 4.5, "the plate against the light stage"
    assert contrast(lip, DARK) >= 3 and contrast(lip, WHITE) >= 3, "the lit lip is an edge on either stage"
    bars = contract(name, "fingers")["fields"]["finish"]["default"]
    assert contrast(bars, WHITE) >= 4.5


# --- the DCIM device types: parts that occupy no rack unit and not the depth ---------------------------------

@pytest.mark.parametrize("name", ALL)
def test_the_dcim_device_types_export_zero_u_and_not_full_depth(name):
    model = device_yaml(name)["model"]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Eaton" / f"{model}.yaml"
        assert path.is_file(), f"{path} is missing: run dcim_export.py --device {name}"
        doc = yaml.safe_load(path.read_text())
        assert doc["manufacturer"] == "Eaton" and doc["model"] == model
        assert doc["u_height"] == 0 and doc["is_full_depth"] is False

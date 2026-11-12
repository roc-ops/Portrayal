"""A housing whose end is a stepped profile: `chassis.section`.

A cast housing that is an extrusion of one end profile (a narrower upper
casting, a flange the full depth, a narrower lower casting) cannot be a plain
box. `chassis.section` states the profile as a closed polygon in the right end
face's frame; the right face is drawn as that polygon, the left face as its
mirror, and the rest of each end face is transparent. This module holds what is
now true of the format: the schema key, the lint rules, what the lock asks for,
what the compiled faces and `configs.json` carry. The test device is
`spec/tests/fixtures/section`, a synthetic box, never a library device.

Lint codes are read from `lint.SECTION_CODES`, so the numbers can change at
merge without touching this module.
"""
import copy
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml
from jsonschema import Draft202012Validator

import warmrender
from portrayal import devicelock as dl
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FIXTURE_LIB = ROOT / "spec/tests/fixtures/section/lib"
DEVICE = FIXTURE_LIB / "devices/fixture/stepped/device.yaml"
RENDER = ROOT / "spec/tools/portrayal/render.py"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
SVG = "{http://www.w3.org/2000/svg}"

DEPTH, HEIGHT, WIDTH = 281.0, 288.0, 600.0


def device():
    """The fixture device, as a fresh document a test may edit."""
    return copy.deepcopy(yaml.safe_load(DEVICE.read_text()))


def section_of(doc):
    return doc["chassis"]["section"]


def schema_errors(doc):
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(doc)]


def found(doc):
    """`{code: [message]}` over the errors and warnings of the section rules."""
    with lint.collecting() as got:
        lint.lint_device_section("device.yaml", doc, [])
    out = {}
    for m in got.errors + got.warnings:
        code = m.split("[", 1)[1].split("]", 1)[0]
        out.setdefault(code, []).append(m.split("] ", 1)[1])
    return out


def severity(doc, code):
    """('error' | 'warning') for the first finding of `code`, or None."""
    with lint.collecting() as got:
        lint.lint_device_section("device.yaml", doc, [])
    if any(f"[{code}]" in m for m in got.errors):
        return "error"
    if any(f"[{code}]" in m for m in got.warnings):
        return "warning"
    return None


def codes():
    return lint.SECTION_CODES


def with_bay(doc, view, at, size=(10.0, 10.0)):
    doc["views"][view].setdefault("components", {}).setdefault("bays", []).append(
        {"id": "probe", "at": list(at), "size": {"w": size[0], "h": size[1]}})
    return doc


# --- the schema ----------------------------------------------------------------------------

def test_the_fixture_validates():
    assert schema_errors(device()) == []


def test_the_schema_names_the_key_and_says_what_it_is():
    chassis = SCHEMA["properties"]["chassis"]["properties"]
    assert "section" in chassis
    text = chassis["section"]["description"]
    for word in ("envelope", "clockwise", "axis-aligned", "mirror"):
        assert word in text.lower(), word


@pytest.mark.parametrize("section", [
    "stepped",                                        # not a list
    [[0, 0], [1, 0], [1, 1]],                         # fewer than four points
    [[0, 0], [1, 0], [1, 1], [0]],                    # a point of one number
    [[0, 0], [1, 0], [1, 1], [0, 1, 2]],              # a point of three
    [[0, 0], [1, 0], [1, 1], ["a", "b"]],             # not numbers
])
def test_a_section_that_is_not_a_list_of_points_is_refused(section):
    doc = device()
    doc["chassis"]["section"] = section
    assert schema_errors(doc)


# --- lint: the polygon ---------------------------------------------------------------------

def test_the_fixture_is_quiet():
    assert found(device()) == {}


def test_a_device_with_no_section_is_quiet():
    doc = device()
    del doc["chassis"]["section"]
    assert found(doc) == {}


def test_the_rules_are_in_the_catalogue():
    for code in set(codes().values()):
        assert code in lint.RULES, code
        assert lint.RULES[code][0] == "device"


def _crossing(doc):
    section_of(doc)[:] = [[0, 0], [200, 0], [200, 200], [100, 200], [100, 100], [281, 100],
                          [281, 288], [0, 288]]


def _repeated(doc):
    section_of(doc).insert(3, list(section_of(doc)[2]))


def _collinear(doc):
    section_of(doc).insert(1, [100.0, 0.0])


def _anticlockwise(doc):
    section_of(doc).reverse()


def _slanted(doc):
    section_of(doc)[3] = [270.0, 140.0]


@pytest.mark.parametrize("edit,word", [
    (_crossing, "crosses"),
    (_repeated, "repeated"),
    (_collinear, "collinear"),
    (_anticlockwise, "clockwise"),
    (_slanted, "axis-aligned"),
])
def test_a_polygon_that_is_not_simple_clockwise_and_axis_aligned_is_an_error(edit, word):
    doc = device()
    edit(doc)
    assert codes()["polygon"] in found(doc)
    assert severity(doc, codes()["polygon"]) == "error"
    assert any(word in m for m in found(doc)[codes()["polygon"]]), found(doc)


def test_a_clockwise_polygon_is_judged_by_the_sign_of_its_area_with_y_down():
    doc = device()
    # the same twelve points the other way round: the area changes sign, and that alone
    _anticlockwise(doc)
    assert any("clockwise" in m for m in found(doc)[codes()["polygon"]])
    doc = device()
    assert codes()["polygon"] not in found(doc)


# --- lint: the polygon against the box -----------------------------------------------------

def _outside(doc):
    section_of(doc)[4] = [300.0, 155.0]
    section_of(doc)[3] = [300.0, 132.0]


def _not_touching(doc):
    section_of(doc)[9] = [5.0, 155.0]       # the left flange no longer reaches x = 0
    section_of(doc)[10] = [5.0, 132.0]


def _notched_top(doc):
    section_of(doc)[1:2] = [[100.0, 0.0], [100.0, 10.0], [130.0, 10.0], [130.0, 0.0], [250.0, 0.0]]


def _notched_bottom(doc):
    pts = section_of(doc)
    i = pts.index([253.0, 288.0])
    pts[i:i + 2] = [[253.0, 288.0], [200.0, 288.0], [200.0, 278.0], [150.0, 278.0],
                    [150.0, 288.0], [28.0, 288.0]]


def _end_view_at_another_size(doc):
    doc["views"]["right"]["size"] = {"w": 300.0, "h": 288.0}


@pytest.mark.parametrize("edit,word", [
    (_outside, "outside"),
    (_not_touching, "touch"),
    (_notched_top, "top"),
    (_notched_bottom, "bottom"),
    (_end_view_at_another_size, "size"),
])
def test_a_polygon_that_does_not_fill_its_box_is_an_error(edit, word):
    doc = device()
    edit(doc)
    assert codes()["fit"] in found(doc)
    assert severity(doc, codes()["fit"]) == "error"
    assert any(word in m for m in found(doc)[codes()["fit"]]), found(doc)


# --- lint: where a section may be stated ---------------------------------------------------

@pytest.mark.parametrize("edit", [
    lambda c: c.update(mount="rack"),
    lambda c: c.update(mount="rack-face"),
    lambda c: c.update(mount="rack-side"),
    lambda c: c.pop("mount"),                                        # a rack device by default
    lambda c: c.update(bevel=[{"edges": ["front-left"], "size": 5}]),
    lambda c: c.update(rounded={"radius": 10}),
    lambda c: c.update(shell="sheet"),
    lambda c: c.update(ears={"h": 20}),
    lambda c: c.update(overhang={"left": 5}),
    lambda c: c.update(kits=[{"ref": "fixture/rail@1", "supply": "in-box"}]),
])
def test_a_section_with_a_mount_or_a_key_that_cannot_go_with_it_is_an_error(edit):
    doc = device()
    edit(doc["chassis"])
    assert codes()["kind"] in found(doc)
    assert severity(doc, codes()["kind"]) == "error"


@pytest.mark.parametrize("mount", ["strand", "pedestal", "wall", "desktop", "din-rail", "ceiling"])
def test_a_section_on_a_box_that_is_not_racked_is_allowed(mount):
    doc = device()
    doc["chassis"]["mount"] = mount
    assert codes()["kind"] not in found(doc)


# --- lint: parts on a stepped body ---------------------------------------------------------

def test_a_part_inside_the_end_outline_is_quiet():
    doc = with_bay(device(), "right", (60.0, 20.0))
    with_bay(doc, "left", (60.0, 190.0))
    assert found(doc) == {}


def test_a_part_in_a_transparent_corner_of_the_right_face_is_an_error():
    doc = with_bay(device(), "right", (0.0, 0.0))
    assert codes()["parts"] in found(doc)
    assert severity(doc, codes()["parts"]) == "error"


def test_a_part_that_runs_out_of_the_outline_over_a_step_is_an_error():
    """A box whose corners are all in the profile, but whose edge crosses the
    notch the flange leaves above the upper casting: x 5 to 20 is inside from
    y 132 and outside above it."""
    doc = with_bay(device(), "right", (5.0, 125.0), (15.0, 15.0))
    assert codes()["parts"] in found(doc)


def test_the_left_face_is_judged_against_the_mirror():
    """x 255 to 265 is outside the right face's upper casting (14 to 250) and
    inside the left face's (31 to 267)."""
    assert codes()["parts"] in found(with_bay(device(), "right", (255.0, 5.0)))
    assert found(with_bay(device(), "left", (255.0, 5.0))) == {}
    assert codes()["parts"] in found(with_bay(device(), "left", (20.0, 5.0)))


def test_a_part_on_the_top_face_must_not_straddle_a_step():
    """From above, the body is high from 14 to 250 across the depth and at the
    flange outside that. The top face is drawn with the front at the bottom, so
    the step at 250 is at 281 - 250 = 31 down the drawing."""
    assert found(with_bay(device(), "top", (100.0, 100.0), (40.0, 40.0))) == {}
    doc = with_bay(device(), "top", (100.0, 20.0), (40.0, 25.0))
    assert codes()["parts"] in found(doc)
    assert severity(doc, codes()["parts"]) == "error"


def test_a_part_on_the_bottom_face_must_not_straddle_a_step():
    assert found(with_bay(device(), "bottom", (100.0, 100.0), (40.0, 40.0))) == {}
    doc = with_bay(device(), "bottom", (100.0, 240.0), (40.0, 25.0))
    assert codes()["parts"] in found(doc)


def test_a_part_on_the_front_or_the_rear_is_not_judged():
    doc = with_bay(device(), "front", (0.0, 0.0))
    with_bay(doc, "rear", (590.0, 278.0))
    assert found(doc) == {}


# --- lint: a PLACED part (a component placement), not a bay ---------------------------------
#
# The tests above put a bay on each face. The rule also measures a placement, by the size
# of the component it names, so these place std/db9@1 (20.47 x 11.40) and need the library
# to resolve it. A part that cannot be sized is not measured, so each refusal below is also
# a proof that the size was found.

PART = "std/db9@1"


def placed(doc, view, at, pid="probe"):
    doc["views"][view].setdefault("components", {}).setdefault("placements", []).append(
        {"ref": PART, "id": pid, "at": list(at)})
    return doc


def found_placed(doc):
    """`{code: [message]}` as `found`, with the library to size the placements from."""
    with lint.collecting() as got:
        lint.lint_device_section("device.yaml", doc, [str(LIB)])
    out = {}
    for m in got.errors + got.warnings:
        code = m.split("[", 1)[1].split("]", 1)[0]
        out.setdefault(code, []).append(m.split("] ", 1)[1])
    return out


def test_the_fixtures_own_placed_parts_are_quiet():
    assert found_placed(device()) == {}


def test_a_placed_part_inside_the_end_outline_is_quiet():
    assert found_placed(placed(device(), "right", (100.0, 30.0))) == {}
    assert found_placed(placed(device(), "left", (100.0, 200.0))) == {}


def test_a_placed_part_in_a_clear_corner_of_an_end_face_is_refused():
    for view, at in (("right", (0.0, 0.0)), ("left", (0.0, 0.0)), ("right", (255.0, 5.0))):
        got = found_placed(placed(device(), view, at))
        assert codes()["parts"] in got, (view, at)
        assert any("probe" in m for m in got[codes()["parts"]])


def test_a_placed_part_across_a_step_of_an_end_face_is_refused():
    """5 to 25.47 across, 125 to 136.4 down: the corners are inside the profile, the edge is not."""
    assert codes()["parts"] in found_placed(placed(device(), "right", (5.0, 125.0)))


def test_a_placed_part_on_the_top_face_must_not_straddle_a_step():
    """The step at 250 is 31 down the top drawing (front at the bottom); 20 to 31.4 crosses it."""
    assert found_placed(placed(device(), "top", (100.0, 100.0))) == {}
    got = found_placed(placed(device(), "top", (100.0, 20.0)))
    assert codes()["parts"] in got
    assert any("probe" in m for m in got[codes()["parts"]])
    assert severity_placed(placed(device(), "top", (100.0, 20.0)), codes()["parts"]) == "error"


def test_a_placed_part_on_the_bottom_face_must_not_straddle_a_step():
    """The bottom's step at 253 across the depth is 28 down the drawing from the rear, and the
    drawing is mirrored: 245 to 256.4 crosses the step at 253."""
    assert found_placed(placed(device(), "bottom", (100.0, 100.0))) == {}
    assert codes()["parts"] in found_placed(placed(device(), "bottom", (100.0, 245.0)))


def test_a_placed_part_on_the_front_is_not_judged_across_the_flange():
    """The stated gap: a front or rear part over rows 132 to 155 has two depths under it and the
    rule does not refuse it. The kit seats it at the depth under its centre row."""
    assert found_placed(placed(device(), "front", (100.0, 125.0))) == {}
    assert found_placed(placed(device(), "rear", (100.0, 125.0))) == {}


def severity_placed(doc, code):
    with lint.collecting() as got:
        lint.lint_device_section("device.yaml", doc, [str(LIB)])
    if any(f"[{code}]" in m for m in got.errors):
        return "error"
    return "warning" if any(f"[{code}]" in m for m in got.warnings) else None


# --- the helper that reads the polygon -----------------------------------------------------

def test_the_left_outline_is_the_right_one_mirrored_with_the_winding_reversed():
    from portrayal import section
    pts = [tuple(p) for p in section_of(device())]
    right = section.outline("right", pts, DEPTH)
    left = section.outline("left", pts, DEPTH)
    assert right == pts
    assert left == [(DEPTH - x, y) for x, y in reversed(pts)]
    assert section.area2(right) > 0 and section.area2(left) > 0      # both still clockwise


def test_front_is_at_the_left_of_the_right_face():
    """The right face is drawn with the front at its left edge (bevel.DRAW_AXES),
    so a point of the section at x = 0 is at the front."""
    from portrayal import bevel
    right, _down = bevel.DRAW_AXES["right"]
    assert right == (0, 0, -1)               # drawing x grows toward the rear


# --- the lock ------------------------------------------------------------------------------

def _without_section():
    doc = device()
    del doc["chassis"]["section"]
    return doc


def _bump(old_doc, new_doc):
    return dl.required_bump(dl.entry(old_doc), dl.entry(new_doc))


def test_the_section_is_a_shape_class_key():
    assert "section" in dl.CHASSIS_SHAPE
    assert "section" not in dl.CHASSIS_SURFACE


def test_the_section_enters_the_shape_digest():
    assert dl.buckets(device())["shape"] != dl.buckets(_without_section())["shape"]
    assert dl.buckets(device())["surface"] == dl.buckets(_without_section())["surface"]


def test_stating_a_section_on_a_released_device_is_a_major():
    assert _bump(_without_section(), device()) == "major"


def test_moving_a_point_of_the_section_is_a_major():
    new = device()
    section_of(new)[1] = [240.0, 0.0]
    section_of(new)[2] = [240.0, 132.0]
    assert _bump(device(), new) == "major"


def test_taking_the_section_away_is_a_major():
    assert _bump(device(), _without_section()) == "major"


# --- the compiled faces and configs.json ---------------------------------------------------

@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("section-build") / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(DEVICE), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    """The same box with no section: the faces the section leaves alone are these."""
    tmp = tmp_path_factory.mktemp("section-plain")
    dev = tmp / "stepped" / "device.yaml"
    dev.parent.mkdir()
    dev.write_text(yaml.safe_dump(_without_section(), sort_keys=False))
    out = tmp / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


def _faceplate(out, view):
    root = ET.parse(out / f"stepped.base.{view}.svg").getroot()
    return next(e for e in root.iter() if e.get("id") == "chassis-faceplate")


def _path_points(el):
    return [tuple(float(v) for v in pair.split(",")) for pair in re.findall(r"[-\d.]+,[-\d.]+", el.get("d"))]


@pytest.mark.heavy
def test_the_right_face_is_a_path_of_the_polygon(built):
    el = _faceplate(built, "right")
    assert el.tag == f"{SVG}path"
    assert [tuple(p) for p in section_of(device())] == _path_points(el)
    assert el.get("d").rstrip().endswith("Z")


@pytest.mark.heavy
def test_the_left_face_is_the_mirror_with_the_winding_reversed(built):
    el = _faceplate(built, "left")
    assert el.tag == f"{SVG}path"
    want = [(DEPTH - x, y) for x, y in reversed([tuple(p) for p in section_of(device())])]
    assert _path_points(el) == want
    assert _path_points(el) != _path_points(_faceplate(built, "right"))


@pytest.mark.heavy
@pytest.mark.parametrize("view", ["left", "right"])
def test_an_end_faceplate_keeps_its_id_and_its_paint(built, view):
    el = _faceplate(built, view)
    assert el.get("id") == "chassis-faceplate"
    assert el.get("data-path") == "chassis" and el.get("data-class") == "chassis"
    assert el.get("fill") not in (None, "none")
    for k in ("x", "y", "width", "height", "rx"):
        assert el.get(k) is None, k


@pytest.mark.heavy
@pytest.mark.parametrize("view", ["front", "rear", "top", "bottom"])
def test_the_other_four_faces_are_unchanged(built, plain, view):
    el = _faceplate(built, view)
    assert el.tag == f"{SVG}rect"
    name = f"stepped.base.{view}.svg"
    # the one thing that must differ is the hash of the source file each face records
    drawn = lambda p: re.sub(rb'"source-sha256":"[0-9a-f]+"', b"", (p / name).read_bytes())
    assert drawn(built) == drawn(plain)


@pytest.mark.heavy
def test_configs_json_carries_the_section(built):
    cfg = json.loads((built / "stepped.configs.json").read_text())
    assert cfg["chassis"]["section"] == section_of(device())
    assert cfg["chassis"]["mount"] == "strand"


@pytest.mark.heavy
def test_a_device_with_no_section_publishes_no_key(plain):
    cfg = json.loads((plain / "stepped.configs.json").read_text())
    assert "section" not in cfg["chassis"]


def test_the_index_contract_stays_2():
    from portrayal import devices_index
    assert devices_index.CONTRACT == 2

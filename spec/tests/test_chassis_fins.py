"""The ribs of a cast housing: `chassis.fins`.

A cast housing whose end profile is `chassis.section` carries thick ribs on its top and its
bottom. `chassis.fins` is a list of rib fields, one per edge of the section that lies on the
top or the bottom of the box: where the field runs along the length, how far the casting's own
surface is from the edge (`core`, which is also the height of the tallest rib), the rib and the
gap, and optionally steps that lower the tips. A field may instead stand its ribs out of the
edge (`outside: true`, with a `height` and no `core`). This module holds what is now true of the
format: the schema key, the lint rules, what the lock asks for, what the compiled faces and
`configs.json` carry. The test devices are `spec/tests/fixtures/fins`, synthetic boxes, never
library devices.

Lint codes are read from `lint.FINS_CODES`, so the numbers can change at merge without touching
this module.
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
from portrayal import fins as fins_mod
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FIXTURE_LIB = ROOT / "spec/tests/fixtures/fins/lib"
DEVICE = FIXTURE_LIB / "devices/fixture/finned/device.yaml"
OUTSIDE = FIXTURE_LIB / "devices/fixture/finned-outside/device.yaml"
STEPPED = ROOT / "spec/tests/fixtures/section/lib/devices/fixture/stepped/device.yaml"
RENDER = ROOT / "spec/tools/portrayal/render.py"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
SVG = "{http://www.w3.org/2000/svg}"

WIDTH, HEIGHT, DEPTH = 600.0, 288.0, 281.0


def device(path=DEVICE):
    """A fixture device, as a fresh document a test may edit."""
    return copy.deepcopy(yaml.safe_load(path.read_text()))


def fields_of(doc):
    return doc["chassis"]["fins"]


def schema_errors(doc):
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(doc)]


def found(doc, libs=()):
    """`{code: [message]}` over the errors and warnings of the fins rules."""
    with lint.collecting() as got:
        lint.lint_device_fins("device.yaml", doc, [str(p) for p in libs])
    out = {}
    for m in got.errors + got.warnings:
        code = m.split("[", 1)[1].split("]", 1)[0]
        out.setdefault(code, []).append(m.split("] ", 1)[1])
    return out


def severity(doc, code, libs=()):
    with lint.collecting() as got:
        lint.lint_device_fins("device.yaml", doc, [str(p) for p in libs])
    if any(f"[{code}]" in m for m in got.errors):
        return "error"
    if any(f"[{code}]" in m for m in got.warnings):
        return "warning"
    return None


def codes():
    return lint.FINS_CODES


# --- the schema ----------------------------------------------------------------------------

def test_the_fixtures_validate():
    assert schema_errors(device()) == []
    assert schema_errors(device(OUTSIDE)) == []


def test_the_schema_names_the_key_and_says_what_it_is():
    chassis = SCHEMA["properties"]["chassis"]["properties"]
    assert "fins" in chassis
    text = chassis["fins"]["description"].lower()
    for word in ("rib", "core", "steps", "outside", "surface", "section"):
        assert word in text, word
    item = chassis["fins"]["items"]
    assert set(item["properties"]) == {"on", "span", "core", "rib", "gap", "steps", "outside", "height"}
    assert item["additionalProperties"] is False
    assert item["properties"]["on"]["enum"] == ["top", "bottom"]


@pytest.mark.parametrize("edit", [
    lambda f: f.update(on="left"),                      # only the top or the bottom
    lambda f: f.update(span=[1.0]),                     # a span is two numbers
    lambda f: f.update(span="all"),
    lambda f: f.update(rib="thick"),
    lambda f: f.update(extra=1),                        # a closed object
    lambda f: f.update(steps=[{"span": [1.0, 2.0]}]),   # a step has a height
    lambda f: f.update(steps=[{"span": [1.0, 2.0], "height": 3.0, "x": 1}]),
    lambda f: f.update(outside="yes"),
])
def test_a_field_the_schema_cannot_read_is_refused(edit):
    doc = device()
    edit(fields_of(doc)[0])
    assert schema_errors(doc)


def test_fins_is_a_list_and_a_field_has_its_keys():
    doc = device()
    doc["chassis"]["fins"] = {"on": "top"}
    assert schema_errors(doc)
    doc = device()
    del fields_of(doc)[0]["rib"]
    assert schema_errors(doc)


# --- lint: the catalogue -------------------------------------------------------------------

def test_the_fixtures_are_quiet():
    assert found(device(), [LIB]) == {}
    assert found(device(OUTSIDE), [LIB]) == {}


def test_a_device_with_no_fins_is_quiet():
    doc = device()
    del doc["chassis"]["fins"]
    assert found(doc) == {}


def test_the_rules_are_in_the_catalogue_with_a_why():
    assert set(codes()) == {"needs", "edge", "numbers", "steps", "count", "leftover", "fit",
                            "overlap", "parts"}
    assert len(set(codes().values())) == 9
    for code in set(codes().values()):
        assert code in lint.RULES, code
        assert lint.RULES[code][0] == "device"
        assert lint.RULES[code][3].strip()


# --- lint: a field needs a section and an edge ---------------------------------------------

def test_fins_without_a_section_is_an_error():
    doc = device()
    del doc["chassis"]["section"]
    assert codes()["needs"] in found(doc)
    assert severity(doc, codes()["needs"]) == "error"


def _no_bottom_edge(doc):
    # the section's bottom run is lifted off the bottom of the box: no edge lies on that side
    pts = doc["chassis"]["section"]
    pts[6] = [253.0, 280.0]
    pts[7] = [28.0, 280.0]


def test_a_field_on_a_side_with_no_edge_is_an_error():
    doc = device()
    _no_bottom_edge(doc)
    got = found(doc)
    assert codes()["edge"] in got and any("bottom" in m for m in got[codes()["edge"]])
    assert severity(doc, codes()["edge"]) == "error"


@pytest.mark.parametrize("span", [[-1.0, 100.0], [20.0, 601.0], [300.0, 300.0], [400.0, 300.0]])
def test_a_span_outside_the_box_or_backwards_is_an_error(span):
    doc = device()
    fields_of(doc)[0]["span"] = span
    assert codes()["edge"] in found(doc)
    assert severity(doc, codes()["edge"]) == "error"


# --- lint: the numbers and the mode of a field ---------------------------------------------

@pytest.mark.parametrize("edit,word", [
    (lambda f: f.update(rib=0.0), "rib"),
    (lambda f: f.update(gap=0.0), "gap"),
    (lambda f: f.update(gap=-3.0), "gap"),
    (lambda f: f.update(core=0.0), "core"),
    (lambda f: f.pop("core"), "core"),
    (lambda f: f.update(height=5.0), "height"),        # an inside field has a core, not a height
])
def test_a_field_with_a_number_that_is_not_positive_or_a_key_that_is_missing_is_an_error(edit, word):
    doc = device()
    edit(fields_of(doc)[0])
    got = found(doc)
    assert codes()["numbers"] in got, got
    assert severity(doc, codes()["numbers"]) == "error"
    assert any(word in m for m in got[codes()["numbers"]]), got


@pytest.mark.parametrize("edit,word", [
    (lambda f: f.update(core=5.0), "core"),             # an outside field has a height, not a core
    (lambda f: f.pop("height"), "height"),
    (lambda f: f.update(height=0.0), "height"),
    (lambda f: f.update(height=61.0, steps=[{"span": [4.0, 56.0], "height": 61.0}]), "60"),
])
def test_an_outside_field_has_a_height_no_core_and_at_most_60_mm(edit, word):
    doc = device(OUTSIDE)
    edit(fields_of(doc)[1])
    got = found(doc)
    assert codes()["numbers"] in got, got
    assert any(word in m for m in got[codes()["numbers"]]), got


def test_an_outside_field_of_60_mm_is_allowed():
    doc = device(OUTSIDE)
    fields_of(doc)[1]["height"] = 60.0
    assert codes()["numbers"] not in found(doc)


# --- lint: steps ---------------------------------------------------------------------------

def _gap_between_steps(f):
    f["steps"][1]["span"] = [200.0, 420.0]


def _overlap_between_steps(f):
    f["steps"][1]["span"] = [180.0, 420.0]


def _short_of_the_end(f):
    f["steps"][2]["span"] = [420.0, 580.0]


def _starts_late(f):
    f["steps"][0]["span"] = [30.0, 190.0]


def _too_tall(f):
    f["steps"][1]["height"] = 60.0


def _none_at_core(f):
    f["steps"][0]["height"] = 40.0
    f["steps"][2]["height"] = 40.0


def _not_positive(f):
    f["steps"][1]["height"] = 0.0


@pytest.mark.parametrize("edit", [_gap_between_steps, _overlap_between_steps, _short_of_the_end,
                                  _starts_late, _too_tall, _none_at_core, _not_positive])
def test_steps_that_do_not_tile_the_span_or_reach_the_core_are_an_error(edit):
    doc = device()
    edit(fields_of(doc)[1])
    assert codes()["steps"] in found(doc)
    assert severity(doc, codes()["steps"]) == "error"


def test_steps_tile_to_a_hundredth_of_a_millimetre():
    doc = device()
    fields_of(doc)[1]["steps"][1]["span"] = [190.004, 420.0]
    fields_of(doc)[1]["steps"][0]["span"] = [20.0, 190.0]
    assert codes()["steps"] not in found(doc)
    fields_of(doc)[1]["steps"][1]["span"] = [190.02, 420.0]
    assert codes()["steps"] in found(doc)


# --- lint: the number of ribs and the end of a span ----------------------------------------

def test_more_than_400_ribs_on_a_device_is_an_error():
    doc = device()
    for f in fields_of(doc):
        f.pop("steps", None)
        f["span"] = [0.0, 600.0]
        f["rib"], f["gap"] = 1.0, 0.5
    # 600 / 1.5 = 400 a field, 800 in all
    assert fins_mod.rib_count(fields_of(doc)[0]) == 400
    assert codes()["count"] in found(doc)
    assert severity(doc, codes()["count"]) == "error"


def test_exactly_400_ribs_is_allowed():
    doc = device()
    doc["chassis"]["fins"] = doc["chassis"]["fins"][:1]
    f = fields_of(doc)[0]
    f["span"] = [0.0, 600.0]
    f["rib"], f["gap"] = 1.0, 0.5
    assert codes()["count"] not in found(doc)


def test_a_leftover_part_of_a_pitch_at_the_end_of_a_span_is_a_warning():
    doc = device()
    fields_of(doc)[0]["span"] = [20.0, 580.0]      # 560 is 40 pitches of 14, so 40 ribs and 7 over
    assert fins_mod.rib_count(fields_of(doc)[0]) == 40
    assert codes()["leftover"] in found(doc)
    assert severity(doc, codes()["leftover"]) == "warning"
    assert found(device()) == {}                    # 567 is 40 pitches and one last rib: no leftover


# --- lint: a rib may not overhang the profile ----------------------------------------------

def test_a_core_deeper_than_the_section_is_wide_is_an_error():
    """The top edge runs from 14 to 250. From the edge down to 132 the section is that wide or
    wider; at 155 the lower casting (28 to 253) is narrower than the edge, so a core of 160
    puts the ribs' root where the casting is not."""
    doc = device()
    fields_of(doc)[0]["core"] = 160.0
    got = found(doc)
    assert codes()["fit"] in got and severity(doc, codes()["fit"]) == "error"
    fields_of(doc)[0]["core"] = 132.0
    assert codes()["fit"] not in found(doc)


def test_a_bottom_core_deeper_than_the_lower_casting_is_wide_is_an_error():
    """The bottom edge runs from 28 to 253. Up to 150 from it the section is the lower casting
    or the flange, both at least that wide; at 160 the upper casting (14 to 250) is narrower than
    the edge's right end, so a core of 160 puts the ribs' root where the casting is not."""
    doc = device()
    fields_of(doc)[1]["core"] = 150.0
    fields_of(doc)[1]["steps"] = [{"span": [20.0, 587.0], "height": 150.0}]
    assert codes()["fit"] not in found(doc)
    fields_of(doc)[1]["core"] = 160.0
    fields_of(doc)[1]["steps"] = [{"span": [20.0, 587.0], "height": 160.0}]
    got = found(doc)
    assert codes()["fit"] in got and any("bottom" in m for m in got[codes()["fit"]])


def test_an_outside_field_is_not_judged_against_the_width_of_the_section():
    """Its ribs stand beyond the edge, not inside the casting, so there is nothing to overhang."""
    doc = device(OUTSIDE)
    fields_of(doc)[0]["height"] = 20.0
    assert codes()["fit"] not in found(doc)


# --- lint: fields on one edge ---------------------------------------------------------------

def test_two_fields_on_one_edge_may_not_overlap():
    doc = device()
    fields_of(doc).append({**copy.deepcopy(fields_of(doc)[0]), "span": [500.0, 600.0]})
    got = found(doc)
    assert codes()["overlap"] in got and severity(doc, codes()["overlap"]) == "error"


def test_an_outside_field_may_not_overlap_an_inside_field_on_the_same_edge():
    doc = device()
    fields_of(doc).append({"on": "top", "outside": True, "span": [100.0, 200.0], "height": 10.0,
                           "rib": 4.0, "gap": 4.0})
    assert codes()["overlap"] in found(doc)


def test_two_outside_fields_side_by_side_on_one_edge_are_allowed():
    doc = device(OUTSIDE)
    fields_of(doc).append({"on": "top", "outside": True, "span": [56.0, 60.0], "height": 10.0,
                           "rib": 4.0, "gap": 4.0})
    assert codes()["overlap"] not in found(doc)


def test_an_inside_field_stands_alone_on_its_edge():
    """The body is one extrusion, so a field that cuts the casting back cuts it back along the
    whole width: a field of another kind beside it, even clear of its span, has nothing to stand on."""
    doc = device()
    fields_of(doc).append({"on": "top", "outside": True, "span": [0.0, 10.0], "height": 10.0,
                           "rib": 4.0, "gap": 4.0})
    assert codes()["overlap"] in found(doc)


# --- lint: parts on the front and the rear -------------------------------------------------

PART = "std/db9@1"


def placed(doc, view, at, pid="probe"):
    doc["views"][view].setdefault("components", {}).setdefault("placements", []).append(
        {"ref": PART, "id": pid, "at": list(at)})
    return doc


def test_the_fixtures_own_parts_are_quiet():
    assert found(device(), [LIB]) == {}


def test_a_part_below_the_ribs_is_quiet():
    assert found(placed(device(), "front", (200.0, 120.0)), [LIB]) == {}
    assert found(placed(device(), "rear", (200.0, 120.0)), [LIB]) == {}


@pytest.mark.parametrize("view,at", [
    ("front", (100.0, 10.0)),            # over the top field: above its tip line
    ("front", (100.0, 255.0)),           # over the bottom field's root
    ("rear", (100.0, 10.0)),
    ("rear", (300.0, 255.0)),
    ("front", (3.0, 5.0)),               # in the end margin above the core: nothing is there
    ("rear", (3.0, 5.0)),
    ("front", (100.0, 20.0)),            # straddling the core line, half over the field
])
def test_a_part_above_the_tip_line_or_over_a_fin_field_is_an_error(view, at):
    got = found(placed(device(), view, at), [LIB])
    assert codes()["parts"] in got, (view, at)
    assert any("probe" in m for m in got[codes()["parts"]])
    assert severity(placed(device(), view, at), codes()["parts"], [LIB]) == "error"


def test_a_bay_over_a_fin_field_is_an_error_too():
    doc = device()
    doc["views"]["front"].setdefault("components", {})["bays"] = [
        {"id": "slot", "at": [100.0, 5.0], "size": {"w": 30.0, "h": 15.0}}]
    assert codes()["parts"] in found(doc)


def test_a_part_on_the_top_face_is_not_judged_by_the_fins_rule():
    """The ribs are the top; a part there is the section rule's to judge, not this one's."""
    doc = device()
    doc["views"]["top"].setdefault("components", {})["bays"] = [
        {"id": "slot", "at": [100.0, 100.0], "size": {"w": 30.0, "h": 15.0}}]
    assert codes()["parts"] not in found(doc)


def test_the_silhouette_of_the_rear_is_the_front_mirrored():
    chassis = device()["chassis"]
    front = fins_mod.silhouette("front", chassis)
    rear = fins_mod.silhouette("rear", chassis)
    assert sorted(rear) == sorted((WIDTH - x, y) for x, y in front)


# --- the helper that reads the fields ------------------------------------------------------

def test_the_ribs_of_a_field_take_the_height_of_the_step_that_holds_their_centre():
    f = fields_of(device())[1]
    ribs = fins_mod.ribs(f)
    assert len(ribs) == 41
    assert ribs[0][:2] == (20.0, 27.0) and ribs[-1][:2] == (580.0, 587.0)
    heights = [h for _a, _b, h in ribs]
    assert heights.count(48.0) == 24 and heights.count(32.0) == 17
    # rib 12 is 188 to 195, its centre 191.5 is in the middle step: the first of the low ones
    assert heights[11] == 48.0 and heights[12] == 32.0
    # half open: a centre exactly on a boundary belongs to the step that starts there
    assert fins_mod.step_height(f, 190.0) == 32.0 and fins_mod.step_height(f, 419.999) == 32.0
    assert fins_mod.step_height(f, 420.0) == 48.0


def test_a_field_with_no_steps_has_every_tip_at_its_core():
    f = fields_of(device())[0]
    assert {h for _a, _b, h in fins_mod.ribs(f)} == {29.0}
    assert len(fins_mod.ribs(f)) == 41


def test_the_edge_of_the_section_on_a_side():
    pts = [tuple(p) for p in device()["chassis"]["section"]]
    assert fins_mod.edge_extent(pts, "top", HEIGHT) == (14.0, 250.0)
    assert fins_mod.edge_extent(pts, "bottom", HEIGHT) == (28.0, 253.0)


# --- the lock ------------------------------------------------------------------------------

def _without_fins():
    doc = device()
    del doc["chassis"]["fins"]
    return doc


def _bump(old_doc, new_doc):
    return dl.required_bump(dl.entry(old_doc), dl.entry(new_doc))


def test_fins_is_a_surface_class_key():
    assert "fins" in dl.CHASSIS_SURFACE
    assert "fins" not in dl.CHASSIS_SHAPE


def test_fins_enter_the_surface_digest_and_not_the_shape_digest():
    assert dl.buckets(device())["surface"] != dl.buckets(_without_fins())["surface"]
    assert dl.buckets(device())["shape"] == dl.buckets(_without_fins())["shape"]


def test_stating_fins_on_a_released_device_is_a_patch():
    assert _bump(_without_fins(), device()) == "patch"


def test_retuning_a_fin_height_on_a_released_device_is_a_patch():
    new = device()
    fields_of(new)[0]["core"] = 27.0
    assert _bump(device(), new) == "patch"
    new = device()
    fields_of(new)[1]["steps"][1]["height"] = 30.0
    assert _bump(device(), new) == "patch"


def test_taking_the_fins_away_is_a_patch():
    assert _bump(device(), _without_fins()) == "patch"


def test_moving_a_point_of_the_section_under_fins_is_still_a_major():
    new = device()
    new["chassis"]["section"][1] = [240.0, 0.0]
    new["chassis"]["section"][2] = [240.0, 132.0]
    assert _bump(device(), new) == "major"


# --- the compiled faces and configs.json ---------------------------------------------------

def build(path, tmp_path_factory, name):
    out = tmp_path_factory.mktemp(name) / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(path), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build(DEVICE, tmp_path_factory, "fins-build")


@pytest.fixture(scope="module")
def built_outside(tmp_path_factory):
    return build(OUTSIDE, tmp_path_factory, "fins-outside-build")


@pytest.fixture(scope="module")
def stepped(tmp_path_factory):
    """The section fixture, which states no fins: the faces the fins must leave alone."""
    return build(STEPPED, tmp_path_factory, "fins-stepped-build")


def root_of(out, name, view):
    return ET.parse(out / f"{name}.base.{view}.svg").getroot()


def faceplate(out, name, view):
    return next(e for e in root_of(out, name, view).iter() if e.get("id") == "chassis-faceplate")


def path_points(el):
    return [tuple(float(v) for v in pair.split(",")) for pair in re.findall(r"[-\d.]+,[-\d.]+", el.get("d"))]


def profile(points, x):
    """(top, bottom) of the solid a closed polygon of vertical and horizontal edges draws at `x`:
    the lowest and highest y of the horizontal edges that span it."""
    ys = []
    n = len(points)
    for i in range(n):
        (x0, y0), (x1, y1) = points[i], points[(i + 1) % n]
        if y0 == y1 and min(x0, x1) < x < max(x0, x1):
            ys.append(y0)
    return min(ys), max(ys)


def viewbox(root):
    return tuple(float(v) for v in root.get("viewBox").split())


def fin_group(out, name, view):
    return next((e for e in root_of(out, name, view).iter() if e.get("id") == "chassis-fins"), None)


def stripes(out, name, view):
    g = fin_group(out, name, view)
    return [] if g is None else [e for e in g if e.tag == f"{SVG}rect"]


def expected_front_profile(x):
    """What the fields of the finned fixture should give at `x` along the front, written out
    by hand: the top is at the core outside its span and at the tip line within it; the bottom is
    at the core outside the span and at the step's tip line within it."""
    inside = 20.0 < x < 587.0
    top = 0.0 if inside else 29.0
    if not inside:
        bottom = 288.0 - 48.0
    elif x < 190.0 or x > 420.0:
        bottom = 288.0
    else:
        bottom = 288.0 - 48.0 + 32.0
    return top, bottom


@pytest.mark.heavy
def test_the_front_outline_follows_the_fin_steps(built):
    el = faceplate(built, "finned", "front")
    assert el.tag == f"{SVG}path" and el.get("data-path") == "chassis" and el.get("data-class") == "chassis"
    pts = path_points(el)
    assert el.get("d").rstrip().endswith("Z")
    for x in [0.5, 10.0, 19.5, 20.5, 100.0, 189.5, 190.5, 300.0, 419.5, 420.5, 586.5, 587.5, 599.5]:
        assert profile(pts, x) == expected_front_profile(x), x


@pytest.mark.heavy
def test_the_rear_outline_is_the_front_mirrored(built):
    pts = path_points(faceplate(built, "finned", "rear"))
    for x in [0.5, 12.5, 13.5, 100.0, 179.5, 180.5, 300.0, 409.5, 410.5, 579.5, 580.5, 599.5]:
        assert profile(pts, x) == expected_front_profile(WIDTH - x), x


@pytest.mark.heavy
def test_the_front_and_rear_paint_a_rib_for_every_rib_inside_the_silhouette(built):
    for view in ("front", "rear"):
        rects = stripes(built, "finned", view)
        assert len(rects) == 82, view
        top = [r for r in rects if float(r.get("y")) < 100]
        assert len(top) == 41
        assert {float(r.get("width")) for r in rects} == {7.0}
        # each top rib runs from the tip line (0) to the core (29)
        assert {(float(r.get("y")), float(r.get("height"))) for r in top} == {(0.0, 29.0)}
    front = stripes(built, "finned", "front")
    xs = sorted(float(r.get("x")) for r in front if float(r.get("y")) < 100)
    assert xs == [20.0 + 14.0 * i for i in range(41)]
    rear = stripes(built, "finned", "rear")
    assert sorted(float(r.get("x")) for r in rear if float(r.get("y")) < 100) == \
        sorted(WIDTH - 27.0 - 14.0 * i for i in range(41))


@pytest.mark.heavy
def test_the_bottom_ribs_of_the_front_stand_at_their_step_heights(built):
    rects = [r for r in stripes(built, "finned", "front") if float(r.get("y")) > 100]
    by_height = {}
    for r in rects:
        by_height.setdefault(float(r.get("height")), []).append(r)
    assert sorted(by_height) == [32.0, 48.0]
    assert len(by_height[32.0]) == 17 and len(by_height[48.0]) == 24
    # every rib stands on the core line (240) and its tip is at 240 + 48 - height... the root at 240
    assert {float(r.get("y")) + float(r.get("height")) for r in by_height[48.0]} == {288.0}
    assert {float(r.get("y")) for r in by_height[32.0]} == {240.0}


@pytest.mark.heavy
@pytest.mark.parametrize("view", ["top", "bottom"])
def test_the_top_and_bottom_carry_a_stripe_for_each_rib(built, view):
    el = faceplate(built, "finned", view)
    assert el.tag == f"{SVG}rect"                      # the face stays the full rectangle
    rects = stripes(built, "finned", view)
    assert len(rects) == 41
    assert {float(r.get("width")) for r in rects} == {7.0}
    # the top field's ribs fill the edge's extent, 14 to 250 across the depth; the face is drawn
    # with the front at the bottom, so across the depth x is row DEPTH - x
    want = (DEPTH - 250.0, 236.0) if view == "top" else (DEPTH - 253.0, 225.0)
    assert {(float(r.get("y")), float(r.get("height"))) for r in rects} == {want}


@pytest.mark.heavy
def test_the_bottom_stripes_are_toned_by_their_step_and_the_top_ones_alike(built):
    bottom = stripes(built, "finned", "bottom")
    tones = {}
    for r in bottom:
        tones.setdefault(r.get("fill"), 0)
        tones[r.get("fill")] += 1
    assert sorted(tones.values()) == [17, 24]
    assert len({r.get("fill") for r in stripes(built, "finned", "top")}) == 1


@pytest.mark.heavy
@pytest.mark.parametrize("view", ["right", "left"])
def test_an_end_face_keeps_the_section_and_draws_the_band_where_the_cap_has_no_body(built, view):
    el = faceplate(built, "finned", view)
    assert el.tag == f"{SVG}path"
    rects = stripes(built, "finned", view)
    assert len(rects) == 2                              # one band per field
    boxes = sorted((float(r.get("x")), float(r.get("y")), float(r.get("width")), float(r.get("height")))
                   for r in rects)
    if view == "right":
        assert boxes == [(14.0, 0.0, 236.0, 29.0), (28.0, 240.0, 225.0, 48.0)]
    else:
        # the left face is the right face mirrored in x across the depth
        assert boxes == sorted([(DEPTH - 250.0, 0.0, 236.0, 29.0), (DEPTH - 253.0, 240.0, 225.0, 48.0)])
    assert len({r.get("fill") for r in rects}) == 1     # a rib tone, one for both bands


@pytest.mark.heavy
def test_the_rib_tone_differs_from_the_casting(built):
    band = stripes(built, "finned", "right")[0].get("fill")
    assert band and band != faceplate(built, "finned", "right").get("fill")


@pytest.mark.heavy
def test_an_inside_field_keeps_the_viewbox_of_the_face(built):
    for view in ("front", "rear", "right", "left", "top", "bottom"):
        root = root_of(built, "finned", view)
        assert root.get("data-face-w") is None and root.get("data-face-h") is None, view
        w, h = {"front": (600, 288), "rear": (600, 288), "right": (281, 288), "left": (281, 288),
                "top": (600, 281), "bottom": (600, 281)}[view]
        assert viewbox(root) == (0.0, 0.0, float(w), float(h)), view


@pytest.mark.heavy
def test_the_ids_of_the_faceplate_are_the_same_with_and_without_fins(built):
    for view in ("front", "rear", "top", "bottom", "right", "left"):
        assert faceplate(built, "finned", view).get("id") == "chassis-faceplate"
        assert faceplate(built, "finned", view).get("data-path") == "chassis"


@pytest.mark.heavy
def test_configs_json_carries_the_fins_as_written(built):
    cfg = json.loads((built / "finned.configs.json").read_text())
    assert cfg["chassis"]["fins"] == fields_of(device())
    assert cfg["chassis"]["section"] == device()["chassis"]["section"]


@pytest.mark.heavy
def test_a_device_with_no_fins_publishes_no_key_and_draws_no_ribs(stepped):
    cfg = json.loads((stepped / "stepped.configs.json").read_text())
    assert "fins" not in cfg["chassis"]
    for view in ("front", "rear", "top", "bottom", "right", "left"):
        assert fin_group(stepped, "stepped", view) is None, view
    assert faceplate(stepped, "stepped", "front").tag == f"{SVG}rect"


def test_the_index_contract_stays_2():
    from portrayal import devices_index
    assert devices_index.CONTRACT == 2


# --- ribs that stand outside the box -------------------------------------------------------

@pytest.mark.heavy
def test_an_outside_field_stands_out_of_the_edge_and_grows_the_viewbox(built_outside):
    root = root_of(built_outside, "finned-outside", "front")
    # up 20 over the top, down 10 under the bottom: y runs -20 to 50
    assert viewbox(root) == (0.0, -20.0, 60.0, 70.0)
    assert root.get("data-face-w") == "60" and root.get("data-face-h") == "40"
    pts = path_points(faceplate(built_outside, "finned-outside", "front"))
    assert profile(pts, 10.0) == (-20.0, 50.0)       # rib 1 centre at 6: 3 ribs of 20 (4 to 30)
    assert profile(pts, 40.0) == (-12.0, 50.0)       # the second step: 12
    assert profile(pts, 2.0) == (0.0, 40.0)          # before the span: the casting's own edge
    assert profile(pts, 58.0) == (0.0, 40.0)


@pytest.mark.heavy
def test_an_outside_field_paints_its_ribs_beyond_the_box_and_leaves_the_casting_whole(built_outside):
    rects = stripes(built_outside, "finned-outside", "front")
    assert len(rects) == 14
    tips = sorted({float(r.get("y")) for r in rects if float(r.get("y")) < 0})
    assert tips == [-20.0, -12.0]
    assert sorted({float(r.get("height")) for r in rects}) == [10.0, 12.0, 20.0]


@pytest.mark.heavy
def test_the_top_of_an_outside_box_keeps_its_face_and_stripes_the_ribs(built_outside):
    root = root_of(built_outside, "finned-outside", "top")
    assert viewbox(root) == (0.0, 0.0, 60.0, 50.0) and root.get("data-face-w") is None
    assert len(stripes(built_outside, "finned-outside", "top")) == 7


@pytest.mark.heavy
def test_the_ends_of_an_outside_box_grow_to_hold_the_ribs_seen_end_on(built_outside):
    root = root_of(built_outside, "finned-outside", "right")
    assert viewbox(root) == (0.0, -20.0, 50.0, 70.0)
    assert root.get("data-face-w") == "50" and root.get("data-face-h") == "40"


@pytest.mark.heavy
def test_the_box_an_outside_device_publishes_is_the_castings(built_outside):
    cfg = json.loads((built_outside / "finned-outside.configs.json").read_text())
    ch = cfg["chassis"]
    assert (ch["w"], ch["h"], ch["d"]) == (60.0, 40.0, 50.0)
    assert ch["fins"] == fields_of(device(OUTSIDE))

"""A housing whose top view is not a rectangle: `chassis.plan-outline`.

A cast housing has rounded corners and lobes when it is seen from above. The end profile
(`chassis.section`) is extruded along the width, so its plan is always a rectangle;
`plan-outline` states the outline seen from above, a polygon for each band of heights. This
module holds what is true of the key now that it is in the format: the schema, the structural
lint rules (the ones that need no clipping), what the lock asks for and what `configs.json`
carries. Nothing is drawn from it yet. The test device is `spec/tests/fixtures/plan_outline`,
a synthetic box, never a library device.

Lint codes are read from `lint.PLAN_OUTLINE_CODES`, so the numbers can change at merge without
touching this module.
"""
import copy
import json
import math
import pathlib
import sys

import pytest
import yaml
from jsonschema import Draft202012Validator

import warmrender
from portrayal import devicelock as dl
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FIXTURE_LIB = ROOT / "spec/tests/fixtures/plan_outline/lib"
DEVICE = FIXTURE_LIB / "devices/fixture/rounded/device.yaml"
RENDER = ROOT / "spec/tools/portrayal/render.py"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())

WIDTH, DEPTH, HEIGHT = 600.0, 281.0, 288.0


def device():
    """The fixture device, as a fresh document a test may edit."""
    return copy.deepcopy(yaml.safe_load(DEVICE.read_text()))


def bands_of(doc):
    return doc["chassis"]["plan-outline"]


def schema_errors(doc):
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(doc)]


def found(doc):
    """`{code: [message]}` over the errors and warnings of the plan-outline rules."""
    with lint.collecting() as got:
        lint.lint_device_plan_outline("device.yaml", doc)
    out = {}
    for m in got.errors + got.warnings:
        code = m.split("[", 1)[1].split("]", 1)[0]
        out.setdefault(code, []).append(m.split("] ", 1)[1])
    return out


def severity(doc, code):
    """('error' | 'warning') for the first finding of `code`, or None."""
    with lint.collecting() as got:
        lint.lint_device_plan_outline("device.yaml", doc)
    if any(f"[{code}]" in m for m in got.errors):
        return "error"
    if any(f"[{code}]" in m for m in got.warnings):
        return "warning"
    return None


def codes():
    return lint.PLAN_OUTLINE_CODES


def ring(n, cx=300.0, cy=140.0, r=100.0):
    """n points on a circle, clockwise with y down, each edge well over 0.1 mm."""
    return [[round(cx + r * math.cos(2 * math.pi * i / n), 3),
             round(cy + r * math.sin(2 * math.pi * i / n), 3)] for i in range(n)]


def banded(n_bands, points):
    """n_bands bands that tile the height, each a ring of `points` points."""
    step = 16.0
    out = []
    for i in range(n_bands):
        lo = i * step
        hi = HEIGHT if i == n_bands - 1 else lo + step
        out.append({"heights": [lo, hi], "points": ring(points)})
    return out


# --- the schema ----------------------------------------------------------------------------

def test_the_fixture_validates():
    assert schema_errors(device()) == []


def test_the_schema_names_the_key_and_says_what_it_is():
    chassis = SCHEMA["properties"]["chassis"]["properties"]
    assert "plan-outline" in chassis
    text = chassis["plan-outline"]["description"]
    assert "seen from above: a top view, not a bay's plan" in text.lower()
    for word in ("clockwise", "band", "section"):
        assert word in text.lower(), word


@pytest.mark.parametrize("value", [
    "rounded",                                                    # not a list
    [],                                                           # no band
    [{"heights": [0, 288]}],                                      # no points
    [{"points": [[0, 0], [1, 0], [1, 1]]}],                       # no heights
    [{"heights": [0], "points": [[0, 0], [1, 0], [1, 1]]}],       # one height
    [{"heights": [0, 288], "points": [[0, 0], [1, 0]]}],          # two points
    [{"heights": [0, 288], "points": [[0, 0], [1, 0], [1]]}],     # a point of one number
    [{"heights": [0, 288], "points": [[0, 0], [1, 0], [1, 1, 1]]}],   # a point of three
    [{"heights": [0, 288], "points": [[0, 0], [1, 0], ["a", 1]]}],    # not a number
    [{"heights": [0, 288], "points": [[0, 0], [1, 0], [1, 1]], "radius": 3}],   # an unknown key
])
def test_a_plan_outline_that_is_not_a_list_of_bands_is_refused(value):
    doc = device()
    doc["chassis"]["plan-outline"] = value
    assert schema_errors(doc)


@pytest.mark.parametrize("value", [
    [{"heights": [0.0, HEIGHT], "points": []}],                           # no point at all
    [{"heights": [0.0, HEIGHT], "points": [[0, 0], [1, 0]]}],             # two points
    [{"heights": [0.0, HEIGHT], "points": [[0, 0], [1]]}],                # not number pairs
    [{"heights": [0.0], "points": [[0, 0], [1, 0], [1, 1]]}],             # one height
    ["band"],                                                             # not a band
])
def test_lint_does_not_crash_on_bands_the_schema_refuses(value):
    """The lint walk goes on after a schema error, so it has to read what the schema refuses."""
    doc = device()
    doc["chassis"]["plan-outline"] = value
    found(doc)


# --- lint: the fixture and the catalogue ---------------------------------------------------

def test_the_fixture_is_quiet():
    assert found(device()) == {}


def test_a_device_with_no_plan_outline_is_quiet():
    doc = device()
    del doc["chassis"]["plan-outline"]
    assert found(doc) == {}


def test_slanted_edges_are_allowed():
    """The flange band's lobes and arcs are slanted; the section's rule against them is its own."""
    pts = bands_of(device())[1]["points"]
    assert any(a[0] != b[0] and a[1] != b[1] for a, b in zip(pts, pts[1:]))
    assert found(device()) == {}


def test_the_rules_are_in_the_catalogue_with_a_severity():
    assert set(codes()) == {"needs", "kind", "tile", "polygon", "caps", "box"}
    for code in set(codes().values()):
        assert code in lint.RULES, code
        assert lint.RULES[code][0] == "device"
        assert lint.RULES[code][4] == lint.ERROR, code


# --- lint: it needs a section --------------------------------------------------------------

def test_a_plan_outline_without_a_section_is_an_error():
    doc = device()
    del doc["chassis"]["section"]
    assert codes()["needs"] in found(doc)
    assert severity(doc, codes()["needs"]) == "error"


# --- lint: where it may be stated ----------------------------------------------------------

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
def test_a_plan_outline_with_a_mount_or_a_key_that_cannot_go_with_it_is_an_error(edit):
    doc = device()
    edit(doc["chassis"])
    assert codes()["kind"] in found(doc)
    assert severity(doc, codes()["kind"]) == "error"


@pytest.mark.parametrize("mount", ["strand", "pedestal", "wall", "desktop", "din-rail", "ceiling"])
def test_a_plan_outline_on_a_box_that_is_not_racked_is_allowed(mount):
    doc = device()
    doc["chassis"]["mount"] = mount
    assert codes()["kind"] not in found(doc)


@pytest.mark.parametrize("edit", [
    lambda c: c.update(halves={"base": {"outer": "top", "stands": 144.0},
                               "lid": {"hinge": "rear", "angle": 180.0, "stands": 144.0}}),
    lambda c: c.update(fins=[{"on": "top", "span": [20, 580], "core": 20, "rib": 7, "gap": 7}]),
])
def test_halves_and_fins_may_go_with_a_plan_outline(edit):
    doc = device()
    edit(doc["chassis"])
    assert codes()["kind"] not in found(doc)


# --- lint: the bands tile the height -------------------------------------------------------

def _gap(doc):
    bands_of(doc)[1]["heights"] = [140.0, 155.0]


def _overlap(doc):
    bands_of(doc)[1]["heights"] = [120.0, 155.0]


def _not_from_the_top(doc):
    bands_of(doc)[0]["heights"] = [5.0, 132.0]


def _not_to_the_bottom(doc):
    bands_of(doc)[2]["heights"] = [155.0, 280.0]


def _backwards(doc):
    bands_of(doc)[1]["heights"] = [155.0, 132.0]


def _out_of_order(doc):
    bands_of(doc).reverse()


@pytest.mark.parametrize("edit,word", [
    (_gap, "gap"),
    (_overlap, "overlap"),
    (_not_from_the_top, "start"),
    (_not_to_the_bottom, "end"),
    (_backwards, "forward"),
    (_out_of_order, "order"),
])
def test_bands_that_do_not_tile_the_height_are_an_error(edit, word):
    doc = device()
    edit(doc)
    assert codes()["tile"] in found(doc)
    assert severity(doc, codes()["tile"]) == "error"
    assert any(word in m for m in found(doc)[codes()["tile"]]), found(doc)


def test_bands_tile_to_a_hundredth_of_a_millimetre():
    doc = device()
    bands_of(doc)[1]["heights"] = [132.009, 155.0]       # inside the tolerance
    assert codes()["tile"] not in found(doc)
    bands_of(doc)[1]["heights"] = [132.02, 155.0]        # outside it
    assert codes()["tile"] in found(doc)


def test_one_band_for_the_whole_height_is_allowed():
    doc = device()
    doc["chassis"]["plan-outline"] = [{"heights": [0.0, HEIGHT], "points": bands_of(device())[1]["points"]}]
    assert found(doc) == {}


# --- lint: each polygon --------------------------------------------------------------------

def _crossing(doc):
    bands_of(doc)[1]["points"] = [[10, 10], [500, 200], [500, 10], [10, 200]]


def _repeated(doc):
    pts = bands_of(doc)[1]["points"]
    pts.insert(3, list(pts[2]))


def _closed_by_repeating_the_first(doc):
    pts = bands_of(doc)[1]["points"]
    pts.append(list(pts[0]))


def _short_edge(doc):
    pts = bands_of(doc)[1]["points"]
    pts.insert(5, [pts[4][0] + 0.05, pts[4][1]])


def _anticlockwise(doc):
    bands_of(doc)[1]["points"].reverse()


def _touching_itself(doc):
    bands_of(doc)[1]["points"] = [[10, 10], [300, 10], [300, 200], [150, 10.0], [10, 200]]


@pytest.mark.parametrize("edit,word", [
    (_crossing, "crosses"),
    (_repeated, "repeated"),
    (_closed_by_repeating_the_first, "repeated"),
    (_short_edge, "shorter"),
    (_anticlockwise, "clockwise"),
    (_touching_itself, "crosses"),
])
def test_a_polygon_that_is_not_simple_or_not_clockwise_is_an_error(edit, word):
    doc = device()
    edit(doc)
    assert codes()["polygon"] in found(doc)
    assert severity(doc, codes()["polygon"]) == "error"
    assert any(word in m for m in found(doc)[codes()["polygon"]]), found(doc)


def test_a_polygon_is_judged_by_the_sign_of_its_area_with_y_down():
    doc = device()
    _anticlockwise(doc)
    assert any("clockwise" in m for m in found(doc)[codes()["polygon"]])
    assert codes()["polygon"] not in found(device())


def test_an_edge_of_a_tenth_of_a_millimetre_is_allowed():
    doc = device()
    pts = bands_of(doc)[1]["points"]
    pts.insert(5, [pts[4][0] + 0.1, pts[4][1]])
    assert codes()["polygon"] not in found(doc)


def test_the_message_names_the_band():
    doc = device()
    _anticlockwise(doc)
    assert any("band 1" in m for m in found(doc)[codes()["polygon"]])


# --- lint: the caps ------------------------------------------------------------------------

def test_five_hundred_and_twelve_points_in_a_band_are_allowed():
    doc = device()
    doc["chassis"]["plan-outline"] = [{"heights": [0.0, HEIGHT], "points": ring(512)}]
    assert found(doc) == {}


def test_more_than_five_hundred_and_twelve_points_in_a_band_is_an_error():
    doc = device()
    doc["chassis"]["plan-outline"] = [{"heights": [0.0, HEIGHT], "points": ring(513)}]
    assert codes()["caps"] in found(doc)
    assert severity(doc, codes()["caps"]) == "error"
    assert any("512" in m for m in found(doc)[codes()["caps"]])


def test_sixteen_bands_of_a_hundred_and_twenty_eight_points_are_allowed():
    doc = device()
    doc["chassis"]["plan-outline"] = banded(16, 128)
    assert found(doc) == {}


def test_more_than_sixteen_bands_is_an_error():
    doc = device()
    doc["chassis"]["plan-outline"] = banded(17, 8)
    assert codes()["caps"] in found(doc)
    assert any("16" in m for m in found(doc)[codes()["caps"]])


def test_more_than_two_thousand_and_forty_eight_points_in_all_is_an_error():
    doc = device()
    doc["chassis"]["plan-outline"] = banded(16, 129)
    assert codes()["caps"] in found(doc)
    assert any("2048" in m for m in found(doc)[codes()["caps"]])


# --- lint: inside the box ------------------------------------------------------------------

def _right_of_the_box(doc):
    bands_of(doc)[1]["points"][15][0] = 600.02          # the lobe's tip


def _left_of_the_box(doc):
    bands_of(doc)[0]["points"][0][0] = -0.5


def _above_the_box(doc):
    bands_of(doc)[1]["points"][6][1] = -0.5


def _below_the_box(doc):
    bands_of(doc)[2]["points"][9][1] = 281.5


@pytest.mark.parametrize("edit", [_right_of_the_box, _left_of_the_box, _above_the_box, _below_the_box])
def test_a_polygon_outside_the_box_is_an_error(edit):
    doc = device()
    edit(doc)
    assert codes()["box"] in found(doc)
    assert severity(doc, codes()["box"]) == "error"


def test_the_box_is_judged_to_a_hundredth_of_a_millimetre():
    doc = device()
    bands_of(doc)[1]["points"][15][0] = 600.009
    assert codes()["box"] not in found(doc)


def test_the_plan_is_judged_against_width_by_depth_not_depth_by_width():
    doc = device()
    doc["chassis"]["width"], doc["chassis"]["depth"] = 280.0, 600.0
    assert codes()["box"] in found(doc)


# --- the lock ------------------------------------------------------------------------------

def _without_plan():
    doc = device()
    del doc["chassis"]["plan-outline"]
    return doc


def _bump(old_doc, new_doc):
    return dl.required_bump(dl.entry(old_doc), dl.entry(new_doc))


def test_the_plan_outline_is_a_shape_class_key():
    assert "plan-outline" in dl.CHASSIS_SHAPE
    assert "plan-outline" not in dl.CHASSIS_SURFACE


def test_the_plan_outline_enters_the_shape_digest():
    assert dl.buckets(device())["shape"] != dl.buckets(_without_plan())["shape"]
    assert dl.buckets(device())["surface"] == dl.buckets(_without_plan())["surface"]


def test_stating_a_plan_outline_on_a_released_device_is_a_major():
    assert _bump(_without_plan(), device()) == "major"


def test_moving_a_point_is_a_major():
    new = device()
    bands_of(new)[1]["points"][5][0] = 197.0
    assert _bump(device(), new) == "major"


def test_changing_a_band_is_a_major():
    new = device()
    bands_of(new)[0]["heights"] = [0.0, 130.0]
    bands_of(new)[1]["heights"] = [130.0, 155.0]
    assert _bump(device(), new) == "major"


def test_taking_the_plan_outline_away_is_a_major():
    assert _bump(device(), _without_plan()) == "major"


# --- configs.json --------------------------------------------------------------------------

def _build(tmp_path, dev):
    out = tmp_path / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("plan-outline-build"), DEVICE)


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    """The same box with no plan outline: its faces are the rectangles."""
    tmp = tmp_path_factory.mktemp("plan-outline-plain")
    dev = tmp / "rounded" / "device.yaml"
    dev.parent.mkdir()
    dev.write_text(yaml.safe_dump(_without_plan(), sort_keys=False))
    return _build(tmp, dev)


@pytest.mark.heavy
def test_configs_json_carries_the_bands_as_written(built):
    cfg = json.loads((built / "rounded.configs.json").read_text())
    assert cfg["chassis"]["plan-outline"] == bands_of(device())
    assert cfg["chassis"]["section"] == device()["chassis"]["section"]


@pytest.mark.heavy
def test_a_device_with_no_plan_outline_publishes_no_key(plain):
    cfg = json.loads((plain / "rounded.configs.json").read_text())
    assert "plan-outline" not in cfg["chassis"]


@pytest.mark.heavy
@pytest.mark.parametrize("view", ["front", "rear", "left", "right", "top", "bottom"])
def test_every_face_follows_the_plan_outline(built, plain, view):
    """The plan outline is drawn from now on (test_plan_faces.py says how); the same box without
    it is the rectangles it was."""
    name = f"rounded.base.{view}.svg"
    import re
    drawn = lambda p: re.sub(rb'"source-sha256":"[0-9a-f]+"', b"", (p / name).read_bytes())
    assert drawn(built) != drawn(plain)


def test_the_index_contract_stays_2():
    from portrayal import devices_index
    assert devices_index.CONTRACT == 2

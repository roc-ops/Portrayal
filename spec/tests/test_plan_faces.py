"""A housing whose plan is not a rectangle, drawn: the faces that follow `chassis.plan-outline`.

The top and bottom faceplate is a path of the union of the bands' polygons with the corners left
transparent, the step between bands is a line, the rib stripes are cut to what the plan leaves,
the front and rear outline is the body's extent at each row of the section, and an end face
shades the part of its silhouette the plan leaves no cap on. The test device is the synthetic box in
`fixtures/plan_outline`, never a library device.
"""
import copy
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import warmrender
from portrayal import plan as P

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FIXTURE_LIB = ROOT / "spec/tests/fixtures/plan_outline/lib"
DEVICE = FIXTURE_LIB / "devices/fixture/rounded/device.yaml"
RENDER = ROOT / "spec/tools/portrayal/render.py"
SVG = "{http://www.w3.org/2000/svg}"
W, D, H = 600.0, 281.0, 288.0


def device():
    return copy.deepcopy(yaml.safe_load(DEVICE.read_text()))


def _build(tmp, doc):
    dev = tmp / "rounded" / "device.yaml"
    dev.parent.mkdir(parents=True)
    dev.write_text(yaml.safe_dump(doc, sort_keys=False))
    out = tmp / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


def _svg(out, face):
    return ET.fromstring((out / f"rounded.base.{face}.svg").read_text())


def _faceplate(out, face):
    return next(e for e in _svg(out, face).iter() if e.get("id") == "chassis-faceplate")


def _points(d):
    """The loops of a path of M, L and Z as lists of (x, y)."""
    loops = []
    for sub in re.findall(r"M[^Z]*Z", d):
        loops.append([(float(a), float(b)) for a, b in re.findall(r"(-?[\d.]+),(-?[\d.]+)", sub)])
    return loops


def _area(loops):
    return sum(P.loop_area2(lp) for lp in loops) / 2.0


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("plan-faces"), device())


def _with_fins():
    doc = device()
    doc["chassis"]["fins"] = [
        {"on": "top", "span": [20.0, 580.0], "core": 20.0, "rib": 7.0, "gap": 7.0},
        {"on": "bottom", "span": [30.0, 570.0], "core": 30.0, "rib": 7.0, "gap": 7.0}]
    return doc


@pytest.fixture(scope="module")
def finned(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("plan-fins"), _with_fins())


def _plan():
    return P.Plan(device()["chassis"])


# --- the top and the bottom ----------------------------------------------------------------

@pytest.mark.heavy
def test_the_top_faceplate_is_a_path_of_the_union_outline_with_the_same_id(built):
    el = _faceplate(built, "top")
    assert el.tag == SVG + "path" and el.get("id") == "chassis-faceplate"
    assert not {"x", "y", "width", "height", "rx"} & set(el.attrib)
    loops = _points(el.get("d"))
    assert len(loops) == 1
    assert _area(loops) == pytest.approx(P.loop_area2(_plan().outline()[0]) / 2.0, rel=1e-4)
    assert (204.0, 0.0) in loops[0] and (600.0, 112.0) in loops[0]       # the lobes
    corner = (0.0, 0.0)
    assert corner not in loops[0]                                         # the corner is not painted


@pytest.mark.heavy
def test_the_bottom_faceplate_is_the_x_mirror_with_the_order_reversed(built):
    top = _points(_faceplate(built, "top").get("d"))[0]
    bottom = _points(_faceplate(built, "bottom").get("d"))[0]
    assert sorted((round(W - x, 3), y) for x, y in top) == sorted(bottom)
    assert P.loop_area2(bottom) > 0 and P.loop_area2(top) > 0              # both clockwise with y down
    assert bottom != [(W - x, y) for x, y in top]                          # reversed, not only mirrored


@pytest.mark.heavy
def test_the_step_between_bands_is_drawn_as_a_line_inside_the_outline(built):
    group = next(e for e in _svg(built, "top").iter() if e.get("id") == "chassis-plan")
    steps = [e for e in group if e.get("data-class") == "plan-step"]
    assert len(steps) == 2                                                 # the upper casting's edge and the lower one's
    assert all(e.get("fill") == "none" and "Z" not in e.get("d") for e in steps)
    xs = {float(x) for e in steps for x, _ in re.findall(r"(-?[\d.]+),(-?[\d.]+)", e.get("d"))}
    assert {20.0, 580.0, 32.0, 566.0} <= xs
    bottom = next(e for e in _svg(built, "bottom").iter() if e.get("id") == "chassis-plan")
    bxs = {float(x) for e in bottom for x, _ in re.findall(r"(-?[\d.]+),(-?[\d.]+)", e.get("d"))}
    assert {W - 20.0, W - 580.0} <= bxs                                    # the bottom's steps are mirrored


@pytest.mark.heavy
def test_no_clip_element_is_written(finned):
    for face in ("top", "bottom", "front", "rear", "left", "right"):
        text = (finned / f"rounded.base.{face}.svg").read_text()
        assert "clipPath" not in text and "clip-path" not in text and "<mask" not in text


# --- the stripes ---------------------------------------------------------------------------

def _fins(out, face):
    return [e for e in _svg(out, face).iter() if e.get("data-class") == "fin"]


@pytest.mark.heavy
def test_a_stripe_is_one_path_cut_to_what_the_plan_leaves(finned):
    paths = _fins(finned, "top")
    assert paths and all(e.tag == SVG + "path" for e in paths)
    first = _points(paths[0].get("d"))[0]
    assert paths[0].get("id") == "fin-0"
    assert min(x for x, _ in first) == pytest.approx(20.0)
    # the first rib, 20 to 27 across the upper casting's depth, loses the rounded corner
    assert _area([first]) < 7.0 * 236.0
    middle = _points(next(e for e in paths if e.get("id") == "fin-10").get("d"))[0]
    assert _area([middle]) == pytest.approx(7.0 * 236.0)


@pytest.mark.heavy
def test_a_stripe_in_several_pieces_has_numbered_ids():
    doc = _with_fins()
    doc["chassis"]["plan-outline"][0]["points"] = [[20, 31], [568, 31], [568, 267], [20, 267], [20, 200],
                                                   [400, 200], [400, 100], [20, 100]]
    plan = P.Plan(doc["chassis"])
    rect = (310.0, 31.0, 317.0, 267.0)
    assert len(plan.stripe(rect, 0.0, 20.0)) == 2


@pytest.mark.heavy
def test_a_rib_the_plan_removes_keeps_its_number_and_is_not_drawn(tmp_path_factory):
    doc = _with_fins()
    doc["chassis"]["fins"][0]["span"] = [0.0, 100.0]
    out = _build(tmp_path_factory.mktemp("plan-removed"), doc)
    ids = [e.get("id") for e in _fins(out, "top")]
    assert "fin-0" not in ids and "fin-1" in ids                           # the rib at 0 to 7 is off the casting


@pytest.mark.heavy
def test_the_bottom_stripes_are_the_mirror_of_the_top_ones(finned):
    bottom = _fins(finned, "bottom")
    first = _points(bottom[0].get("d"))[0]
    # the field starts at x 30, the lower casting at 32: the first rib is cut there, and mirrored
    assert max(x for x, _ in first) == pytest.approx(W - 32.0)
    assert P.loop_area2(first) > 0


# --- the front and the rear ----------------------------------------------------------------

@pytest.mark.heavy
def test_the_front_outline_is_narrower_at_the_castings(built):
    loops = _points(_faceplate(built, "front").get("d"))
    assert len(loops) == 1
    pts = loops[0]
    assert set(pts) == {(0.0, 132.0), (20.0, 132.0), (20.0, 0.0), (580.0, 0.0), (580.0, 132.0),
                        (600.0, 132.0), (600.0, 155.0), (566.0, 155.0), (566.0, 288.0), (32.0, 288.0),
                        (32.0, 155.0), (0.0, 155.0)}
    assert _faceplate(built, "front").get("id") == "chassis-faceplate"


@pytest.mark.heavy
def test_the_rear_outline_is_the_front_mirrored_in_x(built):
    front = _points(_faceplate(built, "front").get("d"))[0]
    rear = _points(_faceplate(built, "rear").get("d"))[0]
    assert sorted((W - x, y) for x, y in front) == sorted(rear)
    assert P.loop_area2(rear) > 0


@pytest.mark.heavy
def test_ribs_on_the_front_are_cut_to_the_outline(tmp_path_factory):
    doc = _with_fins()
    doc["chassis"]["fins"] = [{"on": "top", "span": [0.0, 100.0], "height": 10.0, "rib": 7.0, "gap": 7.0,
                               "outside": True}]
    out = _build(tmp_path_factory.mktemp("plan-front-ribs"), doc)
    paths = _fins(out, "front")
    assert paths
    assert min(x for e in paths for lp in _points(e.get("d")) for x, _ in lp) >= 20.0 - 1e-6   # held to the casting's ends
    assert not any(e.get("id") == "fin-0" for e in paths)                                    # the rib at 0 to 7 is gone


# --- the end faces -------------------------------------------------------------------------

def _nocap(out, face):
    return next(e for e in _svg(out, face).iter() if e.get("data-class") == "plan-no-cap")


@pytest.mark.heavy
def test_an_end_face_stays_the_section_s_outline_and_shades_where_no_cap_exists(built):
    plate = _points(_faceplate(built, "left").get("d"))[0]
    assert len(plate) == 12                                                  # the section's twelve points
    shade = _nocap(built, "left")
    assert shade.get("fill") == "#3a3f45" and shade.get("stroke") == "none"   # the plain tone
    loops = _points(shade.get("d"))
    full = P.loop_area2(plate) / 2.0
    assert _area(loops) == pytest.approx(full - (257.0 - 32.0) * 23.0, rel=1e-4)


@pytest.mark.heavy
def test_the_right_end_has_a_cap_on_the_lobe_only(built):
    loops = _points(_nocap(built, "right").get("d"))
    plate = _points(_faceplate(built, "right").get("d"))[0]
    assert _area(loops) == pytest.approx(P.loop_area2(plate) / 2.0 - 56.0 * 23.0, rel=1e-4)


@pytest.mark.heavy
def test_the_shading_is_painted_over_the_art(built):
    kids = [e.get("id") or e.get("data-class") for e in _svg(built, "right")]
    assert kids.index("chassis-plan") > kids.index("--decor")


# --- a housing without the key is drawn as it was ------------------------------------------

@pytest.mark.heavy
def test_a_housing_without_a_plan_outline_keeps_its_rectangles(tmp_path_factory):
    doc = device()
    del doc["chassis"]["plan-outline"]
    out = _build(tmp_path_factory.mktemp("plan-none"), doc)
    for face in ("top", "bottom"):
        assert _faceplate(out, face).tag == SVG + "rect"
    assert not any(e.get("id") == "chassis-plan" for e in _svg(out, "right").iter())


@pytest.mark.heavy
def test_a_plan_lint_refuses_is_not_drawn(tmp_path_factory):
    doc = device()
    doc["chassis"]["plan-outline"][1]["points"].reverse()                    # not clockwise: L223
    out = _build(tmp_path_factory.mktemp("plan-refused"), doc)
    assert _faceplate(out, "top").tag == SVG + "rect"

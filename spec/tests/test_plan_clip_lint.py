"""What the plan outline leaves of the body, judged: the lint rules that need the plan cut against
the section (L226 to L234).

`test_chassis_plan_outline.py` holds the rules that need no clipping. These cut each band's polygon
against the section's rows (portrayal.plan) and say what is lost: the box the body no longer
reaches, a part on a surface the body does not have, a seam that has no rim to turn on, and the
warnings for what the plan removes without saying so. The test device is the synthetic three-band
box in `fixtures/plan_outline`; the seam tests use a small box of their own.

Lint codes are read from `lint.PLAN_CLIP_CODES`.
"""
import copy
import pathlib

import pytest
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "spec/tests/fixtures/plan_outline/lib/devices/fixture/rounded/device.yaml"

HALVES = {"base": {"outer": "top", "stands": 144.0},
          "lid": {"hinge": "rear", "angle": 180.0, "stands": 144.0}}


def device():
    return copy.deepcopy(yaml.safe_load(DEVICE.read_text()))


def bands_of(doc):
    return doc["chassis"]["plan-outline"]


def codes():
    return lint.PLAN_CLIP_CODES


def _run(doc):
    with lint.collecting() as got:
        lint.lint_device_plan_clip("device.yaml", doc, [])
    return got


def found(doc):
    """`{code: [message]}` over the errors and warnings of the clipping rules."""
    got = _run(doc)
    out = {}
    for m in got.errors + got.warnings:
        code = m.split("[", 1)[1].split("]", 1)[0]
        out.setdefault(code, []).append(m.split("] ", 1)[1])
    return out


def severity(doc, code):
    got = _run(doc)
    if any(f"[{code}]" in m for m in got.errors):
        return "error"
    if any(f"[{code}]" in m for m in got.warnings):
        return "warning"
    return None


def with_bay(doc, view, at, size=(10.0, 10.0)):
    doc["views"][view].setdefault("components", {}).setdefault("bays", []).append(
        {"id": "probe", "at": list(at), "size": {"w": size[0], "h": size[1]}})
    return doc


def small(band_two, hinge="rear", seam=25.0):
    """A 100 by 80 by 40 box whose lower half is only 30 deep (the rear part of the plan is
    open below the step) and that opens at `seam`. Its first band is the whole plan."""
    return {"chassis": {
        "width": 100.0, "depth": 80.0, "height": 40.0, "mount": "strand",
        "section": [[0, 0], [80, 0], [80, 20], [30, 20], [30, 40], [0, 40]],
        "halves": {"base": {"outer": "top", "stands": seam}, "lid": {"hinge": hinge, "stands": 40.0 - seam}},
        "plan-outline": [{"heights": [0, 20], "points": [[0, 0], [100, 0], [100, 80], [0, 80]]},
                         {"heights": [20, 40], "points": band_two}]}}


# --- the catalogue ---------------------------------------------------------------------------

ERRORS = ("contact", "part", "cap", "hinge")
WARNINGS = ("rib", "outside", "snap", "ledge", "unreached")


def test_the_rules_are_in_the_catalogue_with_a_severity_a_why_and_a_fix():
    assert set(codes()) == set(ERRORS) | set(WARNINGS)
    assert len(set(codes().values())) == len(codes())
    for name, code in codes().items():
        assert code in lint.RULES, code
        scope, rule, fix, why, sev = lint.RULES[code]
        assert scope == "device" and rule and fix and len(why) > 40, code
        assert sev == (lint.ERROR if name in ERRORS else lint.WARNING), code


def test_the_codes_follow_the_structural_ones():
    assert all(int(c[1:]) > 225 for c in codes().values())


# --- the fixture and where the rules stay silent ---------------------------------------------

def test_the_fixture_is_quiet():
    assert found(device()) == {}


def test_a_device_with_no_plan_outline_is_quiet():
    doc = device()
    del doc["chassis"]["plan-outline"]
    assert found(doc) == {}


@pytest.mark.parametrize("edit", [
    lambda c: c.pop("section"),
    lambda c: bands_of({"chassis": c})[1]["points"].reverse(),                      # not clockwise
    lambda c: bands_of({"chassis": c})[1].update(heights=[140.0, 155.0]),           # a gap in the bands
    lambda c: bands_of({"chassis": c})[0]["points"].__setitem__(0, [-5.0, 43.0]),   # outside the box
])
def test_a_plan_the_structural_rules_refuse_is_not_clipped(edit):
    doc = device()
    edit(doc["chassis"])
    assert found(doc) == {}


# --- the box is reached by the clipped body --------------------------------------------------

def test_a_plan_that_stops_short_of_a_side_of_the_box_is_an_error():
    doc = device()
    for p in bands_of(doc)[1]["points"]:
        if p[0] == 600.0:
            p[0] = 596.0                                      # the lobe on the right end, trimmed
        if p[0] == 590.0:
            p[0] = 586.0
    assert codes()["contact"] in found(doc)
    assert severity(doc, codes()["contact"]) == "error"
    assert any("right" in m for m in found(doc)[codes()["contact"]])


def test_the_box_is_reached_by_the_body_that_is_left_not_by_the_points():
    """The flange's lobe reaches the right side of the box on paper, but the section has no flange
    there: the body is what the section leaves of it."""
    doc = device()
    doc["chassis"]["section"] = [[14, 0], [281, 0], [281, 132], [60, 132], [60, 155], [253, 155],
                                 [253, 288], [28, 288], [28, 155], [0, 155], [0, 132], [14, 132]]
    got = found(doc)
    assert codes()["contact"] in got
    assert any("right" in m for m in got[codes()["contact"]])


def test_a_lobe_that_is_a_single_vertex_on_the_side_counts():
    assert codes()["contact"] not in found(device())    # the lobe on the rear is a flat; the box's side is reached
    doc = device()
    pts = bands_of(doc)[1]["points"]
    i = pts.index([600.0, 112.0])
    pts[i:i + 2] = [[600.0, 140.0]]                       # a point, not a flat
    assert codes()["contact"] not in found(doc)


def test_the_contact_is_judged_on_the_snapped_plan_to_a_hundredth_of_a_millimetre():
    """A side within half a millimetre is snapped onto, so what reaches the contact test is on it;
    one further off is a real gap."""
    doc = device()
    for p in bands_of(doc)[1]["points"]:
        if p[0] == 600.0:
            p[0] = 599.8
    assert codes()["contact"] not in found(doc)
    for p in bands_of(doc)[1]["points"]:
        if p[0] == 599.8:
            p[0] = 599.4
    assert codes()["contact"] in found(doc)


# --- a part in its present region ------------------------------------------------------------

@pytest.mark.parametrize("view,at,size", [
    ("top", (0.0, 0.0), (10.0, 10.0)),                        # the transparent corner
    ("top", (300.0, 100.0), (400.0, 20.0)),                   # runs off the right end
    ("bottom", (0.0, 0.0), (10.0, 10.0)),
    ("top", (20.0, 32.0), (10.0, 10.0)),                      # on the upper casting, past its rounded corner
])
def test_a_part_outside_the_outline_of_the_top_or_bottom_is_an_error(view, at, size):
    doc = with_bay(device(), view, at, size)
    assert codes()["part"] in found(doc)
    assert severity(doc, codes()["part"]) == "error"


@pytest.mark.parametrize("view,at", [
    ("top", (100.0, 100.0)),
    ("bottom", (100.0, 100.0)),
    ("top", (100.0, 10.0)),             # on the flange, in the strip behind the upper casting
    ("top", (580.0, 120.0)),            # on the flange, between the upper casting's end and the lobe's tip
    ("bottom", (590.0, 100.0)),         # mirrored: the flange at the left end, below the lower casting
])
def test_a_part_inside_the_outline_is_fine(view, at):
    doc = with_bay(device(), view, at)
    assert codes()["part"] not in found(doc), found(doc)


def test_the_bottom_face_is_the_top_face_mirrored_in_x():
    on_top = with_bay(device(), "top", (590.0, 90.0))
    on_bottom = with_bay(device(), "bottom", (590.0, 90.0))
    assert codes()["part"] in found(on_top)        # off the flange's right end, above the lobe
    assert codes()["part"] not in found(on_bottom)  # the left end, where the flange is straight


def test_a_part_across_a_step_between_two_levels_is_an_error():
    """The flange's polygon holds this part, and so does the upper casting's in part, but the
    casting stops at x 580: the part runs from its top onto the flange's."""
    doc = with_bay(device(), "top", (570.0, 120.0), (20.0, 10.0))
    msgs = found(doc)[codes()["part"]]
    assert any("one level" in m for m in msgs), msgs


def test_a_part_on_the_upper_casting_is_judged_by_that_band_s_polygon():
    """The flange polygon would hold this part, the upper casting's does not: its top is what the
    part stands on."""
    doc = with_bay(device(), "top", (22.0, 36.0), (8.0, 4.0))
    msgs = found(doc)[codes()["part"]]
    assert any("one level" in m for m in msgs), msgs


@pytest.mark.parametrize("view,at,ok", [
    ("front", (100.0, 10.0), True),
    ("front", (10.0, 10.0), False),         # the upper casting's front wall starts at x 32
    ("front", (560.0, 10.0), False),        # and ends at 568
    ("front", (100.0, 140.0), True),
    ("rear", (40.0, 10.0), True),
    ("rear", (560.0, 10.0), False),         # the rear is the front mirrored in x
    ("rear", (100.0, 140.0), False),        # the flange's rear wall is only on its lobe (x 204 to 276)
    ("rear", (330.0, 140.0), True),         # mirrored: 600 - 340 .. 600 - 330
])
def test_a_part_on_the_front_or_rear_is_where_its_wall_is(view, at, ok):
    doc = with_bay(device(), view, at)
    assert (codes()["part"] not in found(doc)) == ok, found(doc)


def test_a_part_across_two_rows_needs_the_wall_in_both():
    doc = with_bay(device(), "front", (24.0, 120.0), (10.0, 30.0))      # x 24 to 34: flange yes, casting no
    assert codes()["part"] in found(doc)


@pytest.mark.parametrize("view,at,ok", [
    ("right", (120.0, 135.0), True),        # on the lobe's cap
    ("right", (20.0, 135.0), False),        # on the flange but where no cap exists
    ("right", (100.0, 20.0), False),        # an inset casting has no cap at the end
    ("left", (100.0, 135.0), True),
    ("left", (10.0, 135.0), False),
    ("left", (100.0, 20.0), False),
])
def test_a_part_on_an_end_face_is_where_a_cap_exists(view, at, ok):
    doc = with_bay(device(), view, at)
    assert (codes()["part"] not in found(doc)) == ok, found(doc)


def test_the_message_names_the_view_and_the_part():
    doc = with_bay(device(), "top", (0.0, 0.0))
    assert any(m.startswith("top/probe") for m in found(doc)[codes()["part"]])


# --- the seam ---------------------------------------------------------------------------------

def test_the_small_box_is_quiet_when_its_seam_cap_is_one_piece_on_the_hinge_line():
    doc = small([[0, 50], [100, 50], [100, 80], [0, 80]])
    assert found(doc) == {}


def test_a_seam_whose_cap_is_empty_is_an_error():
    doc = small([[0, 0], [100, 0], [100, 40], [0, 40]])      # the lower band is where the section is open
    got = found(doc)
    assert codes()["cap"] in got
    assert severity(doc, codes()["cap"]) == "error"
    assert any("empty" in m for m in got[codes()["cap"]])


def test_a_seam_whose_cap_is_in_two_pieces_is_an_error():
    doc = small([[0, 0], [100, 0], [100, 80], [70, 80], [70, 30], [30, 30], [30, 80], [0, 80]])
    got = found(doc)
    assert any("2 pieces" in m for m in got[codes()["cap"]]), got


@pytest.mark.parametrize("hinge,points,reaches", [
    ("rear", [[0, 55], [100, 55], [100, 80], [0, 80]], False),     # the rear wall of the lower row is at y 50
    ("rear", [[0, 50], [100, 50], [100, 80], [0, 80]], True),
    ("front", [[0, 50], [100, 50], [100, 75], [0, 75]], False),    # the front wall is at y 80
    ("front", [[0, 50], [100, 50], [100, 80], [0, 80]], True),
])
def test_a_seam_band_that_does_not_reach_the_hinge_line_is_an_error(hinge, points, reaches):
    doc = small(points, hinge=hinge)
    assert (codes()["hinge"] in found(doc)) == (not reaches), found(doc)
    if not reaches:
        assert severity(doc, codes()["hinge"]) == "error"


def test_the_seam_rules_name_the_half():
    got = found(small([[0, 0], [100, 0], [100, 40], [0, 40]]))
    assert any("base" in m for m in got[codes()["cap"]]) and any("lid" in m for m in got[codes()["cap"]])


def test_a_seam_on_a_horizontal_edge_is_the_section_rules_to_report():
    doc = small([[0, 50], [100, 50], [100, 80], [0, 80]], seam=20.0)
    assert codes()["cap"] not in found(doc) and codes()["hinge"] not in found(doc)


def test_the_seam_rules_need_halves():
    doc = small([[0, 0], [100, 0], [100, 40], [0, 40]])
    del doc["chassis"]["halves"]
    assert codes()["cap"] not in found(doc)


# --- the warnings -----------------------------------------------------------------------------

def with_ribs(doc, span, core=20.0):
    doc["chassis"]["fins"] = [{"on": "top", "span": list(span), "core": core, "rib": 7.0, "gap": 7.0}]
    return doc


def test_a_rib_the_plan_cuts_is_a_warning():
    doc = with_ribs(device(), [20.0, 580.0])                  # the first rib is in the rounded corner
    assert severity(doc, codes()["rib"]) == "warning"
    assert any("cuts 2 more" in m for m in found(doc)[codes()["rib"]])


def test_a_rib_the_plan_removes_is_named():
    doc = with_ribs(device(), [0.0, 100.0])                   # the first rib is off the upper casting's end
    msgs = found(doc)[codes()["rib"]]
    assert any("removes 1 of its 7 ribs entirely" in m for m in msgs), msgs


def test_ribs_the_plan_leaves_whole_are_quiet():
    assert codes()["rib"] not in found(with_ribs(device(), [40.0, 572.0]))


def _reach_out(doc):
    bands_of(doc)[0]["points"][3] = [32.0, 20.0]


def test_a_polygon_that_reaches_outside_the_section_is_a_warning_that_names_the_point():
    doc = device()
    _reach_out(doc)
    assert severity(doc, codes()["outside"]) == "warning"
    msg = found(doc)[codes()["outside"]][0]
    assert "band 0" in msg and "[32, 20]" in msg


def test_a_polygon_inside_the_section_is_quiet():
    assert codes()["outside"] not in found(device())


def test_a_plan_edge_a_few_tenths_off_a_section_edge_is_a_warning_that_names_the_snap():
    doc = device()
    for p in bands_of(doc)[0]["points"]:
        if p[1] == 31.0:
            p[1] = 31.3
    assert severity(doc, codes()["snap"]) == "warning"
    msg = found(doc)[codes()["snap"]][0]
    assert "band 0" in msg and "31.3" in msg and "31" in msg


def test_a_move_of_a_hundredth_is_not_named():
    doc = device()
    for p in bands_of(doc)[0]["points"]:
        if p[1] == 31.0:
            p[1] = 31.005
    assert codes()["snap"] not in found(doc)


def test_a_snap_leaves_the_contact_and_the_other_rules_as_the_snapped_plan_reads():
    doc = device()
    for p in bands_of(doc)[1]["points"]:
        if p[0] == 600.0:
            p[0] = 599.8                                       # the lobe is 0.2 mm short of the side
    got = found(doc)
    assert codes()["snap"] in got and codes()["contact"] not in got


def _two_polygons(doc):
    pts = bands_of(doc)[0]["points"]
    bands_of(doc)[0]["heights"] = [0.0, 100.0]
    bands_of(doc).insert(1, {"heights": [100.0, 132.0],
                             "points": [[x + 2 if x == 20.0 else x, y] for x, y in pts]})


def test_a_band_edge_that_is_not_a_section_row_where_the_polygons_differ_is_a_warning():
    doc = device()
    _two_polygons(doc)
    assert severity(doc, codes()["ledge"]) == "warning"
    assert any("100" in m for m in found(doc)[codes()["ledge"]])


def test_a_band_edge_between_equal_polygons_is_quiet():
    doc = device()
    _two_polygons(doc)
    bands_of(doc)[1]["points"] = copy.deepcopy(bands_of(doc)[0]["points"])
    assert codes()["ledge"] not in found(doc)


def test_a_band_edge_on_a_section_row_is_quiet():
    assert codes()["ledge"] not in found(device())      # the fixture's bands change at 132 and 155, the section's rows


def test_section_no_x_reaches_is_a_warning_that_says_where():
    doc = device()
    bands_of(doc)[0]["points"] = [[x, 35.0 if y == 31.0 else (260.0 if y == 267.0 else y)]
                                  for x, y in bands_of(doc)[0]["points"]]
    msgs = found(doc)[codes()["unreached"]]
    assert severity(doc, codes()["unreached"]) == "warning"
    assert any("0 to 132" in m for m in msgs), msgs


def test_a_plan_that_fills_the_section_rows_is_quiet_of_it():
    assert codes()["unreached"] not in found(device())

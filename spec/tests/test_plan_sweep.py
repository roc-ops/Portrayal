"""The x-sweep that cuts a plan outline against a section (portrayal.plan).

The cases are in `fixtures/plan_outline/sweep-cases.json`, worked by hand, and the kit's
JavaScript version reads the same file. This module checks Python against them and then what the
rest of the module builds from the sweep, on the synthetic three-band box.
"""
import copy
import json
import pathlib

import pytest
import yaml

from portrayal import plan as P
from portrayal import plan_outline as plan_outline
from portrayal import section as section_mod

ROOT = pathlib.Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "spec/tests/fixtures/plan_outline/sweep-cases.json").read_text())["cases"]
DEVICE = ROOT / "spec/tests/fixtures/plan_outline/lib/devices/fixture/rounded/device.yaml"
EPS = 1e-6


def _close(a, b):
    """Nested lists of numbers equal to a millionth of a millimetre."""
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    return abs(a - b) <= EPS


def _pts(poly):
    return [list(p) for p in poly]


def _case(kind):
    return [pytest.param(c, id=c["name"]) for c in CASES if c["kind"] == kind]


def _rects(intervals, width):
    return [[(0.0, a), (float(width), a), (float(width), b), (0.0, b)] for a, b in intervals]


def chassis():
    return yaml.safe_load(DEVICE.read_text())["chassis"]


def plan():
    return P.Plan(chassis())


def test_the_fixture_file_has_the_cases_the_order_names():
    names = " ".join(c["name"] for c in CASES)
    for needle in ("lobe on an end", "crossing", "near-coincident", "asymmetric", "snap"):
        assert needle in names, needle
    assert {c["kind"] for c in CASES} == {"abscissae", "clip", "union", "snap", "body"}


@pytest.mark.parametrize("case", _case("abscissae"))
def test_abscissae_within_a_thousandth_of_a_millimetre_are_one(case):
    assert _close(P.merge_abscissae(case["input"]), case["expected"])


def test_the_merge_keeps_the_smallest_of_a_cluster_and_measures_from_the_one_kept():
    assert P.merge_abscissae([1.0, 1.0009, 1.0018]) == [1.0, 1.0018]
    assert P.merge_abscissae([1.0, 1.001]) == [1.0]
    assert P.merge_abscissae([1.0, 1.0011]) == [1.0, 1.0011]


@pytest.mark.parametrize("case", _case("clip"))
def test_a_polygon_cut_to_the_intervals_is_the_pieces_worked_by_hand(case):
    polygon = [tuple(p) for p in case["polygon"]]
    got = [_pts(P.polygon(p)) for p in P.sweep([[polygon], _rects(case["intervals"], case["width"])])]
    assert _close(got, case["expected"]), got


@pytest.mark.parametrize("case", _case("union"))
def test_a_union_is_the_outline_worked_by_hand(case):
    polys = [[tuple(p) for p in poly] for poly in case["polygons"]]
    got = [_pts(lp) for lp in P.union_loops(polys)]
    assert _close(got, case["expected"]), got


@pytest.mark.parametrize("case", _case("snap"))
def test_a_snap_is_the_polygon_and_the_list_worked_by_hand(case):
    pts, snaps = P.snap_polygon([tuple(p) for p in case["polygon"]],
                                case["targets"]["x"], case["targets"]["y"])
    assert _close(_pts(pts), case["expected"]), pts
    assert _close([list(s) for s in snaps], case["snaps"]), snaps


@pytest.mark.parametrize("case", _case("body"))
def test_a_stepped_body_is_cut_into_the_pieces_worked_by_hand(case):
    ch = {"width": case["width"], "depth": case["depth"], "height": case["height"],
          "section": case["section"], "plan-outline": case["plan"]}
    got = P.Plan(ch)
    assert got.snaps == []
    listed = [{"band": s["band"], "heights": list(s["heights"]),
               "pieces": [_pts(P.polygon(p)) for p in s["pieces"]]} for s in got.solid]
    assert _close(listed, case["expected"]), listed


def test_a_band_edge_within_a_hundredth_of_a_row_is_on_the_row():
    case = next(c for c in CASES if c["kind"] == "body")
    ch = {"width": case["width"], "depth": case["depth"], "height": case["height"],
          "section": case["section"], "plan-outline": copy.deepcopy(case["plan"])}
    ch["plan-outline"][0]["heights"] = [0, 2.004]
    ch["plan-outline"][1]["heights"] = [2.004, 6]
    heights = [list(s["heights"]) for s in P.Plan(ch).solid]
    assert heights == [[0, 2], [2, 4], [4, 6]]


def test_an_empty_clip_has_no_pieces():
    far = [(20.0, 0.0), (22.0, 0.0), (22.0, 3.0), (20.0, 3.0)]
    assert P.sweep([[far], _rects([(0, 6)], 12)]) == []


def test_one_group_is_the_union_and_several_are_the_intersection():
    a = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0.0, 4.0)]
    b = [(3.0, 2.0), (9.0, 2.0), (9.0, 6.0), (3.0, 6.0)]
    both = sum(P.area(p) for p in P.sweep([[a], [b]]))
    either = sum(P.area(p) for p in P.sweep([[a, b]]))
    assert both == pytest.approx(3 * 2)
    assert either == pytest.approx(24 + 24 - 6)


def test_a_group_can_be_taken_away():
    a = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0.0, 4.0)]
    b = [(3.0, 2.0), (9.0, 2.0), (9.0, 6.0), (3.0, 6.0)]
    left = sum(P.area(p) for p in P.sweep([[a]], minus=[[b]]))
    assert left == pytest.approx(24 - 6)


# --- the snap on the box ---------------------------------------------------------------------

def test_a_run_a_few_tenths_inside_a_wall_is_snapped_onto_it():
    ch = chassis()
    ch["plan-outline"][0]["points"] = [[x, 31.3 if y == 31.0 else y] for x, y in ch["plan-outline"][0]["points"]]
    got = P.Plan(ch)
    assert {y for _, y in got.bands[0]["points"]} >= {31.0}
    assert any(s[2] == "y" and s[3] == pytest.approx(31.3) and s[4] == 31.0 for s in got.snaps), got.snaps


def test_the_snap_looks_at_the_walls_of_the_band_s_own_heights():
    """Band 0 is the upper casting, whose front wall is 14 mm in: 281 - 14 = 267. A point 0.3 mm
    from that line snaps in band 0 and does not in band 2, whose walls are at 28 and 253."""
    ch = chassis()
    for b in (0, 2):
        ch["plan-outline"][b]["points"][8] = [ch["plan-outline"][b]["points"][8][0], 267.3]
    got = P.Plan(ch)
    assert any(s[0] == 0 and s[3] == pytest.approx(267.3) for s in got.snaps)
    assert not any(s[0] == 2 for s in got.snaps)


# --- the three-band box ----------------------------------------------------------------------

def test_the_box_is_reached_on_all_four_sides_by_the_clipped_body():
    x0, x1, y0, y1 = P.reach(plan().solid)
    assert (x0, x1, y0, y1) == (0.0, 600.0, 0.0, 281.0)


def test_the_union_outline_is_one_loop_that_follows_the_flange_and_its_lobes():
    loops = plan().outline()
    assert len(loops) == 1
    xs = [x for x, _ in loops[0]]
    ys = [y for _, y in loops[0]]
    assert (min(xs), max(xs), min(ys), max(ys)) == (0.0, 600.0, 0.0, 281.0)
    assert P.loop_area2(loops[0]) > 0                     # clockwise with y down
    assert (600.0, 112.0) in loops[0] and (204.0, 0.0) in loops[0]    # the two lobes


def test_the_step_lines_are_the_castings_edges_inside_the_flange_and_nothing_on_the_outline():
    steps = plan().steps()
    assert steps, "the inset castings leave step lines inside the flange"
    outline = [s for lp in plan().outline() for s in zip(lp, lp[1:] + lp[:1])]
    for run in steps:
        for a, b in zip(run, run[1:]):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            assert all(P._dist(mid, s0, s1) > P.TOL for s0, s1 in outline), (a, b)
    xs = {x for run in steps for x, _ in run}
    assert 20.0 in xs and 580.0 in xs and 32.0 in xs      # the upper casting's and the lower one's ends


def test_a_stripe_is_cut_where_the_plan_removes_the_rib():
    got = plan()
    whole = (100.0, 31.0, 107.0, 267.0)         # a rib across the upper casting's depth
    lps, kept = P.ribs_clipped(got, whole, 0.0, 29.0)
    assert kept == pytest.approx(1.0) and len(lps) == 1
    beyond = (3.0, 31.0, 10.0, 267.0)           # off the upper casting's end (x 20 to 580), in the flange
    _lps, kept = P.ribs_clipped(got, beyond, 0.0, 29.0)
    assert kept == 0.0


def test_a_stripe_at_a_rounded_corner_keeps_the_part_the_corner_leaves():
    got = plan()
    lps, kept = P.ribs_clipped(got, (20.0, 31.0, 27.0, 267.0), 0.0, 29.0)
    assert 0.5 < kept < 1.0
    assert min(x for lp in lps for x, _ in lp) == pytest.approx(20.0)


def test_a_stripe_in_two_pieces_is_two_loops():
    ch = chassis()
    # a slot cut into the upper casting from its left end, 100 mm wide and 380 long, leaves a
    # stripe that crosses it in two pieces
    ch["plan-outline"][0]["points"] = [[20, 31], [568, 31], [568, 267], [20, 267], [20, 200], [400, 200],
                                       [400, 100], [20, 100]]
    assert plan_outline.polygon_problems([tuple(p) for p in ch["plan-outline"][0]["points"]]) == []
    lps, kept = P.ribs_clipped(P.Plan(ch), (310.0, 31.0, 330.0, 267.0), 0.0, 29.0)
    assert len(lps) == 2
    assert kept == pytest.approx((69 + 67) / 236)


def test_the_front_outline_is_narrower_at_the_castings_than_at_the_flange():
    got = plan()
    lps = got.elevation()
    assert len(lps) == 1
    widths = {}
    for (x0, y0), (x1, y1) in zip(lps[0], lps[0][1:] + lps[0][:1]):
        if x0 == x1:
            widths.setdefault((min(y0, y1), max(y0, y1)), set()).add(x0)
    xs_at = lambda y: sorted(x for (a, b), v in widths.items() if a <= y <= b for x in v)
    assert xs_at(143.0) == [0.0, 600.0]                    # the flange rows reach both ends
    assert xs_at(60.0) == [20.0, 580.0]                    # the upper casting stops short of them
    assert xs_at(200.0) == [32.0, 566.0]                   # the lower one stops shorter, on the left too


def test_the_front_outline_is_the_union_of_the_runs_and_not_their_hull():
    """A U-shaped plan on a section whose lower part is only as deep as the arms: at those
    heights the body is two runs of x, and the outline keeps the gap between them."""
    ch = {"width": 100.0, "depth": 80.0, "height": 40.0,
          "section": [[0, 0], [80, 0], [80, 20], [40, 20], [40, 40], [0, 40]],
          "plan-outline": [{"heights": [0, 40], "points": [[0, 0], [100, 0], [100, 80], [70, 80], [70, 30],
                                                           [30, 30], [30, 80], [0, 80]]}]}
    got = P.Plan(ch)
    assert got._x_runs(10.0) == [(0.0, 100.0)]
    assert got._x_runs(30.0) == [(0.0, 30.0), (70.0, 100.0)]
    (loop,) = got.elevation()
    assert (30.0, 40.0) in loop and (70.0, 40.0) in loop
    assert P.loop_area2(loop) / 2.0 == pytest.approx(100 * 20 + 60 * 20)      # the hull would be 4000


def test_an_elevation_follows_the_silhouette_of_the_fins_inside_the_body():
    sil = [(0.0, -10.0), (600.0, -10.0), (600.0, 288.0), (0.0, 288.0)]      # a rib that stands above the box
    lps = plan().elevation(sil)
    ys = [y for lp in lps for _, y in lp]
    assert min(ys) == -10.0
    xs_top = sorted({x for lp in lps for x, y in lp if y == -10.0})
    assert xs_top == [20.0, 580.0]                          # the rib is held to the upper casting's ends


# --- walls and caps --------------------------------------------------------------------------

def test_the_front_wall_of_the_upper_casting_is_there_between_the_corners():
    runs = plan().wall_runs("front", 10.0, 100.0)
    assert runs == [(32.0, 568.0)]
    assert plan().wall_runs("rear", 10.0, 100.0) == [(32.0, 568.0)]


def test_the_flange_s_rear_wall_is_only_where_the_lobe_reaches_it():
    """The flange's rear edge is 8 mm in from the section's wall except on the lobe, whose flat
    top is on it."""
    assert plan().wall_runs("rear", 135.0, 150.0) == [(204.0, 276.0)]
    assert plan().wall_runs("front", 135.0, 150.0) == [(24.0, 566.0)]


def test_a_part_across_two_rows_needs_the_wall_in_both():
    assert plan().wall_runs("front", 100.0, 150.0) == [(32.0, 566.0)]
    assert plan().wall_runs("front", 160.0, 200.0) == [(41.0, 557.0)]


def test_the_caps_are_where_the_body_has_a_wall_on_the_end():
    got = plan()
    left = got.cap("left")
    assert left == [(132.0, 155.0, 32.0, 257.0)]
    right = got.cap("right")
    assert right == [(132.0, 155.0, 112.0, 168.0)]          # only the lobe reaches the right end


def test_an_end_face_shades_what_the_cap_does_not_reach():
    got = plan()
    loops = got.no_cap("left")
    covered = sum(P.loop_area2(lp) / 2.0 for lp in loops)
    outline = section_mod.outline("left", got.section, got.depth)
    full = P.loop_area2(outline) / 2.0
    cap = (257.0 - 32.0) * 23.0
    assert covered == pytest.approx(full - cap)


def test_the_cap_polygons_are_in_the_end_face_s_own_frame():
    got = plan()
    (left,) = got.cap_polygons("left")
    assert [p[0] for p in left] == [32.0, 257.0, 257.0, 32.0]      # the left face's x is the plan's y
    (right,) = got.cap_polygons("right")
    assert [p[0] for p in right] == [281.0 - 168.0, 281.0 - 112.0, 281.0 - 112.0, 281.0 - 168.0]


# --- the seam --------------------------------------------------------------------------------

HALVES = {"base": {"outer": "top", "stands": 144.0}, "lid": {"hinge": "rear", "angle": 180.0, "stands": 144.0}}


def test_each_half_takes_the_band_on_its_own_side_of_the_seam():
    got = plan()
    assert got.seam(HALVES, "base")["band"] == 1
    assert got.seam(HALVES, "lid")["band"] == 1
    split = chassis()                    # the flange band cut in two at the seam, 144 mm down
    flange = split["plan-outline"][1]
    split["plan-outline"][1:2] = [{"heights": [132.0, 144.0], "points": flange["points"]},
                                  {"heights": [144.0, 155.0], "points": flange["points"]}]
    cut = P.Plan(split)
    assert cut.seam(HALVES, "base")["band"] == 1        # above the seam: the band that ends at it
    assert cut.seam(HALVES, "lid")["band"] == 2         # below it: the band that starts at it


def test_a_seam_with_the_base_below_swaps_the_sides():
    split = chassis()
    flange = split["plan-outline"][1]
    split["plan-outline"][1:2] = [{"heights": [132.0, 144.0], "points": flange["points"]},
                                  {"heights": [144.0, 155.0], "points": flange["points"]}]
    halves = {"base": {"outer": "bottom", "stands": 144.0}, "lid": {"hinge": "rear", "stands": 144.0}}
    cut = P.Plan(split)
    assert cut.seam(halves, "base")["band"] == 2 and cut.seam(halves, "lid")["band"] == 1


def test_the_seam_cap_is_the_band_cut_to_the_section_at_the_seam():
    cap = plan().seam(HALVES, "base")
    assert len(P.outer_loops(cap["pieces"])) == 1
    flange = [tuple(p) for p in chassis()["plan-outline"][1]["points"]]
    assert sum(P.area(p) for p in cap["pieces"]) == pytest.approx(P.loop_area2(flange) / 2.0, abs=0.01)


# --- the shape of the answer -----------------------------------------------------------------

def test_valid_says_what_lint_will_not_clip():
    assert P.valid(chassis())
    bad = chassis()
    del bad["section"]
    assert not P.valid(bad)
    bad = chassis()
    bad["plan-outline"][1]["points"].reverse()
    assert not P.valid(bad)


def test_path_d_mirrors_and_reverses_so_the_bottom_stays_clockwise():
    loop = [(0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (0.0, 2.0)]
    mirrored = P.path_d([loop], mirror=10.0)
    assert mirrored == "M10.000,2.000 L6.000,2.000 L6.000,0.000 L10.000,0.000 Z"
    pts = [(10.0 - x, y) for x, y in reversed(loop)]
    assert P.loop_area2(pts) > 0

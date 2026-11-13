"""The five Catalyst 2960-S: the rear's stamped marks, tabs, hole and corner edge, the left wall's openings and the RPS plate's notch.

The rear figures are read off the NetBox rear photograph of the WS-C2960S-48LPD-L at 3.41 px per mm.
The left wall is placed from two photographs of the product. Figure 1-10 of the Catalyst 2960-S Switch Hardware
Installation Guide (OL-19732-04) gives its pattern. Every figure is estimated.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
RPS = ROOT / "library/components/cisco/rps2300-connector/v2"
LONG = ["ws-c2960s-48fpd", "ws-c2960s-48lpd", "ws-c2960s-24pd"]
SHORT = ["ws-c2960s-48td", "ws-c2960s-24td"]
NAMES = LONG + SHORT
DEPTH = {n: 386.0 for n in LONG} | {n: 299.0 for n in SHORT}


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def decor(d, view):
    return {x["id"]: x for x in d["views"][view]["panel"].get("decor") or [] if x.get("id")}


def silk(d, view):
    return {x["id"]: x for x in d["views"][view].get("silkscreen") or [] if x.get("id")}


def numbers(path):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", path)]


def corners(mark):
    """Absolute points of a path made of `M 0 0 L dx dy ...` anchored at the mark's `at`."""
    n = numbers(mark["path"])
    pts = [(n[i], n[i + 1]) for i in range(0, len(n) - 1, 2)]
    return [(mark["at"][0] + x, mark["at"][1] + y) for x, y in pts]


@pytest.mark.parametrize("name", NAMES)
def test_rear_has_the_lit_top_edge_the_inlet_rim_the_two_tabs_and_the_round_hole(name):
    r = decor(device(name), "rear")
    assert r["rear-lid-edge"]["size"] == [444.5, 1.2] and r["rear-lid-edge"]["at"] == [0, 0]
    assert r["rear-inlet-rim"]["at"] == r["inlet-surround"]["at"] and r["rear-inlet-rim"]["size"] == r["inlet-surround"]["size"]
    top, bottom = r["rear-tab-top"], r["rear-tab-bottom"]
    assert top["at"][0] == bottom["at"][0] == 386.0 and top["size"] == bottom["size"] == [10.2, 3.0]
    assert top["at"][1] == pytest.approx(3.0) and bottom["at"][1] == pytest.approx(33.7)
    assert top["rx"] == bottom["rx"] == 1.4
    rim, hole = r["rear-hole-rim"], r["rear-hole"]
    for part in (rim, hole):
        assert part["size"][0] == part["size"][1] and part["rx"] == part["size"][0] / 2, "round: rx is half the size"
    centre = (rim["at"][0] + rim["size"][0] / 2, rim["at"][1] + rim["size"][1] / 2)
    assert centre == pytest.approx((149.6, 28.9), abs=0.05), "centre read at 3.41 px per mm"


@pytest.mark.parametrize("name", NAMES)
def test_rear_stamped_marks_are_two_groups_of_six_each_with_a_lit_edge(name):
    s = silk(device(name), "rear")
    marks = [s[f"rear-stamp-{i}"] for i in range(1, 13)]
    lits = [s[f"rear-stamp-{i}-lit"] for i in range(1, 13)]
    assert len(lits) == 12
    first = [m for m in marks if m["at"][0] < 200]
    second = [m for m in marks if m["at"][0] > 200]
    assert len(first) == 6 and len(second) == 6
    for m in first:
        assert all(108.0 <= x <= 154.0 for x, _ in corners(m)), "between the module and the fan"
    for m in second:
        assert all(228.0 <= x <= 271.0 for x, _ in corners(m)), "between the fan and the RPS plate"
    for m in marks:
        assert len(corners(m)) == 4 and m["filled"] is False and m["fill"] == "#34383b"
        assert all(0.0 <= y <= 44.45 for _, y in corners(m))


@pytest.mark.parametrize("name", NAMES)
def test_rear_diagonal_edge_runs_to_the_top_right_and_the_steps_stand_under_it(name):
    d = device(name)
    line = silk(d, "rear")["rear-diagonal"]
    (x0, y0), (x1, y1) = corners(line)
    assert (x0, y0) == pytest.approx((422.8, 18.2), abs=0.05) and (x1, y1) == pytest.approx((443.9, 0.3), abs=0.1)
    assert line["fill"] == "#5c6061" and line["stroke-width"] == 0.6
    r = decor(d, "rear")
    steps = [r[k] for k in ("rear-corner-slot", "rear-corner-lip-1", "rear-corner-line", "rear-corner-lip-2",
                            "rear-corner-gap", "rear-corner-foot")]
    assert all(416.0 <= s["at"][0] and s["at"][0] + s["size"][0] <= 425.0 for s in steps)
    assert [s["at"][1] for s in steps] == sorted(s["at"][1] for s in steps), "the steps run down the edge in order"
    assert steps[-1]["at"][1] + steps[-1]["size"][1] <= 44.45


@pytest.mark.parametrize("name", NAMES)
def test_left_wall_draws_the_figures_29_openings_inside_the_face(name):
    d = device(name)
    left = d["views"]["left"]
    assert "empty" not in left and left["size"]["w"] == DEPTH[name]
    marks = [m for k, m in silk(d, "left").items() if k.startswith("side-opening-")]
    assert len(marks) == 29
    for m in marks:
        assert m["filled"] is True and m["fill"] == "#141414"
        for x, y in corners(m):
            assert 0.0 <= x <= DEPTH[name] and 0.0 <= y <= 44.45, (m["id"], x, y)
    if DEPTH[name] == 386.0:
        rear_cluster = [m for m in marks if m["at"][0] < 200]
        assert len(rear_cluster) == 20, "20 openings stand in the rear 200 mm, the figure's first group"


DIST = ROOT / "library/dist"
# The centre of each of the 29 openings on a 299 mm model's flat left face, in millimetres from the rear edge and the top.
# It is the middle of the opening's bounding box, placed from two photographs of the product.
# The openings run rear to front, in the order Figure 1-10 lists them.
CENTRES = [
    (17.3, 6.0), (14.0, 19.0), (23.9, 22.1), (52.6, 38.5), (46.4, 24.3), (45.9, 10.7), (53.7, 17.5),
    (61.6, 24.3), (61.1, 10.4), (68.9, 17.5), (76.4, 10.5), (83.4, 22.2), (93.0, 11.1), (100.8, 17.9),
    (108.6, 24.8), (108.3, 11.0), (116.2, 17.8), (123.9, 24.7), (123.7, 11.0), (131.5, 17.8), (183.4, 33.1),
    (197.3, 5.1), (205.9, 21.9), (217.6, 33.4), (233.1, 38.1), (264.8, 10.2), (265.1, 31.4), (266.6, 21.8),
    (280.5, 5.4),
]
TOP_ROW = [6, 9, 11, 13, 16, 19]  # the six peanut slots along the top, as numbered in CENTRES
SHIFT = 87.0  # a 386 mm model's front group (openings 21 to 29) sits 87 mm farther from the rear than a 299 mm model's


def built_svg(name, face):
    return (DIST / f"{name}.{face}.svg").read_text()


def built_openings(name):
    """Centre of each built opening: the middle of its outline's bounding box, after the element's translate."""
    svg = built_svg(name, "left")
    found = {}
    for tag in re.findall(r"<path [^>]*>", svg):
        ident = re.search(r' id="(side-opening-\d+)"', tag)
        if not ident:
            continue
        move = re.search(r'transform="translate\(([-\d.]+) ([-\d.]+)\)"', tag)
        n = numbers(re.search(r' d="([^"]+)"', tag).group(1))
        xs = [float(move.group(1)) + n[i] for i in range(0, len(n) - 1, 2)]
        ys = [float(move.group(2)) + n[i + 1] for i in range(0, len(n) - 1, 2)]
        found[ident.group(1)] = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    return found


def drawn_centres(name):
    """Centre of each left-face opening in the device file: the middle of its outline's bounding box."""
    marks = silk(device(name), "left")
    out = []
    for i in range(1, 30):
        pts = corners(marks[f"side-opening-{i:02d}"])
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    return out


@pytest.mark.parametrize("name", NAMES)
def test_left_wall_openings_sit_where_the_photographs_put_them(name):
    for i, ((x, y), (dx, dy)) in enumerate(zip(CENTRES, drawn_centres(name)), 1):
        if i >= 21:
            x += DEPTH[name] - 299.0
        assert abs(dx - x) <= 0.1 and abs(dy - y) <= 0.1, (i, (dx, dy), (x, y))


@pytest.mark.parametrize("name", NAMES)
def test_left_wall_top_row_of_slots_is_15_mm_apart(name):
    row = [drawn_centres(name)[i - 1][0] for i in TOP_ROW]
    pitches = [b - a for a, b in zip(row, row[1:])]
    assert abs(sum(pitches) / len(pitches) - 15.0) <= 1.0, "the photographs put the slots about 15 mm apart"
    assert all(abs(p - 15.0) <= 2.0 for p in pitches), pitches


def plain_stretch(name):
    """Distance along the wall from the rear group's last edge to the front group's first edge."""
    marks = silk(device(name), "left")
    edges = {i: [x for x, _ in corners(marks[f"side-opening-{i:02d}"])] for i in range(1, 30)}
    return min(min(edges[i]) for i in range(21, 30)) - max(max(edges[i]) for i in range(1, 21))


def test_a_386_mm_model_has_a_plain_stretch_87_mm_longer_than_a_299_mm_model():
    short = {plain_stretch(n) for n in SHORT}
    assert len(short) == 1 and abs(short.pop() - 44.0) <= 0.3
    for n in LONG:
        assert abs(plain_stretch(n) - plain_stretch(SHORT[0]) - SHIFT) <= 0.05, n
        assert abs(plain_stretch(n) - 131.0) <= 0.3, n


@pytest.mark.heavy
@pytest.mark.parametrize("name", ["ws-c2960s-48lpd", "ws-c2960s-24td"])
def test_built_left_face_centres_each_of_the_29_openings_within_a_tenth_of_a_millimetre(name):
    built = built_openings(name)
    assert sorted(built) == [f"side-opening-{i:02d}" for i in range(1, 30)], "29 openings, counted in the build"
    for i, (x, y) in enumerate(CENTRES, 1):
        if name == "ws-c2960s-48lpd" and i >= 21:
            x += SHIFT
        bx, by = built[f"side-opening-{i:02d}"]
        assert abs(bx - x) <= 0.1 and abs(by - y) <= 0.1, (i, (bx, by), (x, y))


@pytest.mark.heavy
def test_built_top_row_is_15_mm_apart_and_a_386_mm_model_has_an_87_mm_longer_plain_stretch():
    long, short = built_openings("ws-c2960s-48lpd"), built_openings("ws-c2960s-24td")
    for built in (long, short):
        row = [built[f"side-opening-{i:02d}"][0] for i in TOP_ROW]
        pitches = [b - a for a, b in zip(row, row[1:])]
        assert abs(sum(pitches) / len(pitches) - 15.0) <= 1.0, pitches
    gap = lambda built: built["side-opening-21"][0] - built["side-opening-20"][0]
    assert abs((gap(long) - gap(short)) - SHIFT) <= 0.2, (gap(long), gap(short))


@pytest.mark.heavy
def test_built_rear_of_the_48lpd_draws_the_marks_hole_tabs_and_edge_and_no_text_is_added():
    svg = built_svg("ws-c2960s-48lpd", "rear")
    ids = re.findall(r' id="(rear-[a-z0-9-]+)"', svg)
    assert len([i for i in ids if re.fullmatch(r"rear-stamp-\d+", i)]) == 12
    assert len([i for i in ids if re.fullmatch(r"rear-stamp-\d+-lit", i)]) == 12
    assert len([i for i in ids if i.startswith("rear-corner-")]) == 6
    for one in ("rear-hole-rim", "rear-hole", "rear-tab-top", "rear-tab-bottom", "rear-lid-edge", "rear-diagonal",
                "rear-inlet-rim"):
        assert ids.count(one) == 1, one
    drawn = re.findall(r"<text[^>]*>([^<]*)</text>", svg)
    assert "RATING" not in drawn and not [t for t in drawn if "11.25" in t], "no printed legend is drawn on this rear"


def test_rps_plate_has_the_notch_in_its_left_edge_and_the_patch_is_stated():
    skin = (RPS / "skins/default.svg").read_text()
    plate = re.search(r'<path id="plate" d="([^"]+)"', skin)
    assert plate, "the plate is a path with the notch, not a rectangle"
    assert "V 11 H 2.6 V 4.4 H 0" in plate.group(1), "2.6 mm deep, from 4.4 to 11.0 below the top"
    assert 'id="stub-top"' in skin and 'id="stub-bottom"' in skin, "the notch's two light stubs"
    c = yaml.safe_load((RPS / "contract.yaml").read_text())
    assert c["version"] == "2.0.2" and "notch" in c["provenance"]
    assert c["size"]["w"] == 72.8 and c["size"]["h"] == 22.6, "the part's size is unchanged"

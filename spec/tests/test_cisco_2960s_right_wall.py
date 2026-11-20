"""The right wall of the Catalyst 2960S-24TD-L and -48TD-L, placed from photographs of the product.

A right view has x = 0 at the front. The wall is not a copy of the left wall. It has 7 round holes, 6 peanut slots and
5 small rectangles, and one light tab. Every figure is estimated, good to about 3 mm along the wall and 2 mm across.
The scale comes from the 299 mm length (Table 1-3 of the Catalyst 2960-S Switch Hardware Installation Guide, OL-19732-04)
and the printed 44.45 mm height.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
DIST = ROOT / "library/dist"
NAMES = ["ws-c2960s-24td", "ws-c2960s-48td"]
DEPTH, HEIGHT = 299.0, 44.45

# kind, centre from the front, centre from the top; the front-to-rear order of the 18 openings
OPENINGS = [
    ("hole", 22.4, 4.5), ("rect", 30.9, 22.1), ("slot", 32.4, 31.0), ("slot", 32.9, 10.3), ("slot", 50.2, 25.1),
    ("hole", 58.1, 39.4), ("hole", 78.3, 34.3), ("rect", 90.6, 22.0), ("hole", 103.3, 5.4), ("hole", 115.1, 34.6),
    ("slot", 135.4, 17.1), ("slot", 144.3, 9.2), ("slot", 145.1, 24.8), ("rect", 214.5, 22.5), ("hole", 240.5, 39.2),
    ("rect", 274.6, 22.1), ("rect", 285.5, 18.8), ("hole", 287.7, 4.5),
]


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def right_marks(d):
    marks = d["views"]["right"].get("silkscreen") or []
    return {m["id"]: m for m in marks if m.get("id")}


def numbers(path):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", path)]


def kind_of(path):
    if " a " in path:
        return "hole"
    return "rect" if path.count("L") == 3 else "slot"


def centre(at, path):
    """Middle of the outline's bounding box; a hole's outline is a circle whose centre is its anchor."""
    if kind_of(path) == "hole":
        return at[0], at[1]
    n = numbers(path)
    xs, ys = n[0::2], n[1::2]
    return at[0] + (min(xs) + max(xs)) / 2, at[1] + (min(ys) + max(ys)) / 2


def openings(d):
    marks = right_marks(d)
    out = []
    for i in range(1, 19):
        m = marks[f"side-right-opening-{i:02d}"]
        out.append((kind_of(m["path"]),) + centre(m["at"], m["path"]))
    return out


@pytest.mark.parametrize("name", NAMES)
def test_right_wall_is_drawn_with_18_openings_and_one_tab(name):
    d = device(name)
    right = d["views"]["right"]
    assert "empty" not in right and right["size"]["w"] == DEPTH
    marks = right_marks(d)
    ids = sorted(k for k in marks if k.startswith("side-right-opening-"))
    assert ids == [f"side-right-opening-{i:02d}" for i in range(1, 19)]
    kinds = [kind_of(marks[i]["path"]) for i in ids]
    assert (kinds.count("hole"), kinds.count("slot"), kinds.count("rect")) == (7, 6, 5)
    assert "side-right-tab-01" in marks
    for m in marks.values():
        assert m["filled"] is True and m.get("for") == "chassis"


@pytest.mark.parametrize("name", NAMES)
def test_right_wall_openings_stand_where_the_photographs_put_them(name):
    for i, ((kind, x, y), (dk, dx, dy)) in enumerate(zip(OPENINGS, openings(device(name))), 1):
        assert dk == kind, (i, dk, kind)
        assert abs(dx - x) <= 0.1 and abs(dy - y) <= 0.1, (i, (dx, dy), (x, y))


@pytest.mark.parametrize("name", NAMES)
def test_right_wall_runs_from_the_front_and_every_opening_is_inside_the_face(name):
    d = device(name)
    marks = right_marks(d)
    for m in marks.values():
        n = numbers(m["path"])
        if kind_of(m["path"]) == "hole":
            r = n[0]
            xs, ys = [m["at"][0] - r, m["at"][0] + r], [m["at"][1] - r, m["at"][1] + r]
        else:
            xs = [m["at"][0] + v for v in n[0::2]]
            ys = [m["at"][1] + v for v in n[1::2]]
        assert min(xs) >= 0.0 and max(xs) <= DEPTH and min(ys) >= 0.0 and max(ys) <= HEIGHT, m["id"]
    cx = [x for _, x, _ in openings(d)]
    slots = [x for k, x, _ in openings(d) if k == "slot"]
    assert min(slots[:3]) < 55 and 130 < min(slots[3:]) and max(slots[3:]) < 150, "two groups of three, the first near the front"
    assert max(cx) > 285, "the last opening stands near the rear, 285 mm from the front"


@pytest.mark.parametrize("name", NAMES)
def test_right_wall_tab_lies_inside_the_rectangle_at_285_mm(name):
    marks = right_marks(device(name))
    rect = marks["side-right-opening-17"]
    n = numbers(rect["path"])
    x0, y0 = rect["at"]
    x1, y1 = x0 + max(n[0::2]), y0 + max(n[1::2])
    tab = marks["side-right-tab-01"]
    t = numbers(tab["path"])
    tx0, ty0 = tab["at"]
    tx1, ty1 = tx0 + max(t[0::2]), ty0 + max(t[1::2])
    assert x0 - 0.1 <= tx0 and tx1 <= x1 + 0.1 and y0 - 0.1 <= ty0 and ty1 <= y1 + 0.1
    assert tab["fill"] != rect["fill"], "the tab is light metal against the dark opening"


def test_the_right_wall_is_not_a_copy_of_the_left_wall():
    for name in NAMES:
        d = device(name)
        left = [m for m in d["views"]["left"]["silkscreen"] if m["id"].startswith("side-opening-")]
        assert len(left) == 29 and len(openings(d)) == 18


def test_the_two_devices_draw_one_pattern():
    a, b = (openings(device(n)) for n in NAMES)
    assert a == b


@pytest.mark.parametrize("name", NAMES)
def test_the_notes_and_gaps_say_what_the_right_wall_is(name):
    d = device(name)
    note = d["provenance"]["side-right"]
    assert note["confidence"] == "estimated"
    for word in ("photographs", "299 mm", "44.45", "front", "9 openings"):
        assert word in note["note"], word
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["the-undrawn-faces"]["scope"] == ["top", "bottom"]
    assert gaps["right-wall-rims-and-waists"]["scope"] == ["right"]


def built_centres(name):
    svg = (DIST / f"{name}.right.svg").read_text()
    found = {}
    for tag in re.findall(r"<path [^>]*>", svg):
        ident = re.search(r' id="(side-right-opening-\d+)"', tag)
        if not ident:
            continue
        move = re.search(r'transform="translate\(([-\d.]+) ([-\d.]+)\)"', tag)
        d_attr = re.search(r' d="([^"]+)"', tag).group(1)
        n = numbers(d_attr)
        if " a " in d_attr or "A" in d_attr:
            found[ident.group(1)] = (float(move.group(1)), float(move.group(2)))
            continue
        xs = [float(move.group(1)) + n[i] for i in range(0, len(n) - 1, 2)]
        ys = [float(move.group(2)) + n[i + 1] for i in range(0, len(n) - 1, 2)]
        found[ident.group(1)] = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    return found


@pytest.mark.heavy
@pytest.mark.parametrize("name", NAMES)
def test_built_right_face_centres_each_opening_within_a_tenth_of_a_millimetre(name):
    built = built_centres(name)
    assert sorted(built) == [f"side-right-opening-{i:02d}" for i in range(1, 19)], "18 openings, counted in the build"
    for i, (_, x, y) in enumerate(OPENINGS, 1):
        bx, by = built[f"side-right-opening-{i:02d}"]
        assert abs(bx - x) <= 0.1 and abs(by - y) <= 0.1, (i, (bx, by), (x, y))

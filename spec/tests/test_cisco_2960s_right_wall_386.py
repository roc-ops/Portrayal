"""The right wall of the Catalyst 2960S-24PD-L, -48FPD-L and -48LPD-L, the three 386 mm models.

A right view has x = 0 at the front and y = 0 at the top of the wall.
Two ends of the wall are drawn from Figure 1-12 of the Catalyst 2960-S Switch Hardware Installation Guide, OL-19732-04.
The figure's first drawing shows a PoE model's right wall isometrically, with the rack bracket over the middle.
Each place below was read on a 600 dpi render and mapped to millimetres by the wall's 386 mm length and 44.45 mm height.
Three openings behind the bracket take the photographed 299 mm pattern. Every figure is estimated.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
DIST = ROOT / "library/dist"
NAMES = ["ws-c2960s-24pd", "ws-c2960s-48fpd", "ws-c2960s-48lpd"]
DEPTH, HEIGHT = 386.0, 44.45
ALONG, ACROSS = 0.3, 0.3  # what the drawn centre may differ from the table: the path is rounded to 0.1 mm

# kind, tilt (slots), centre along the wall from the front, centre down from the top, width, height, source.
# Slash: the upper end is to the right; backslash: the upper end is to the left.
# Fig: read on Figure 1-12; fig-end: only one end of the slot shows beside the bracket; photo: the 299 mm photographs.
TABLE = [
    ("hole", None, 33.7, 3.4, 3.4, 3.4, "fig"),
    ("slot", "slash", 46.6, 9.3, 16.1, 11.3, "fig"),
    ("slot", "slash", 46.9, 33.4, 16.1, 11.3, "fig"),
    ("rect", None, 47.4, 21.95, 14.8, 2.9, "fig"),
    ("slot", "slash", 68.4, 9.3, 16.1, 11.3, "fig"),
    ("slot", "slash", 68.8, 24.1, 16.1, 11.3, "fig"),
    ("slot", "backslash", 79.9, 17.0, 15.8, 11.3, "fig"),
    ("slot", "slash", 90.6, 9.3, 16.1, 11.3, "fig"),
    ("slot", "slash", 90.6, 24.1, 16.1, 11.3, "fig"),
    ("slot", "slash", 113.5, 9.3, 16.1, 11.3, "fig"),
    ("hole", None, 115.1, 34.6, 4.4, 4.4, "photo"),
    ("slot", "backslash", 135.4, 17.15, 11.4, 10.1, "photo"),
    ("hole", None, 137.7, 4.7, 3.4, 3.4, "fig"),
    ("slot", "slash", 145.1, 24.8, 11.4, 10.2, "photo"),
    ("slot", "slash", 155.2, 9.7, 16.1, 11.3, "fig"),
    ("slot", "slash", 177.4, 9.6, 16.1, 11.3, "fig"),
    ("slot", "slash", 199.6, 9.8, 16.1, 11.3, "fig"),
    ("slot", "slash", 209.0, 20.5, 16.1, 11.3, "fig-seen-through"),
    ("slot", "slash", 222.4, 9.8, 16.1, 11.3, "fig"),
    ("slot", "slash", 222.6, 26.0, 16.1, 11.3, "fig-end"),
    ("slot", "backslash", 234.5, 17.2, 15.8, 11.3, "fig"),
    ("slot", "slash", 245.3, 9.5, 16.1, 11.3, "fig"),
    ("rect", None, 262.1, 23.65, 15.2, 2.9, "fig"),
    ("hole", None, 265.4, 41.6, 3.4, 3.4, "fig"),
    ("slot", "slash", 266.1, 9.05, 16.1, 11.3, "fig"),
    ("slot", "backslash", 277.2, 16.8, 15.8, 11.3, "fig"),
    ("slot", "slash", 288.0, 24.5, 16.1, 11.3, "fig"),
    ("slot", "slash", 288.15, 9.05, 16.1, 11.3, "fig"),
    ("slot", "backslash", 300.1, 16.8, 15.8, 11.3, "fig"),
    ("slot", "slash", 310.85, 9.1, 16.1, 11.3, "fig"),
    ("slot", "slash", 312.9, 24.8, 16.1, 11.3, "fig"),
    ("rect", None, 333.7, 23.75, 15.2, 2.9, "fig"),
    ("rect", None, 346.8, 19.85, 6.4, 6.7, "fig"),
    ("hole", None, 352.3, 4.9, 3.4, 3.4, "fig"),
]
# The tab: at and size. It lies inside the last rectangle. The figure draws no tab, but the photographs do.
TAB = (343.6, 16.9, 4.0, 5.9)
BRACKET = (92.5, 229.3)  # the stretch of the wall the rack bracket covers below the top strip


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


def box(m):
    """Bounding box of a mark in wall millimetres: x0, y0, x1, y1."""
    n = numbers(m["path"])
    if kind_of(m["path"]) == "hole":
        r = n[0]
        return m["at"][0] - r, m["at"][1] - r, m["at"][0] + r, m["at"][1] + r
    xs, ys = n[0::2], n[1::2]
    return m["at"][0] + min(xs), m["at"][1] + min(ys), m["at"][0] + max(xs), m["at"][1] + max(ys)


def tilt_of(m):
    """slash when the topmost point of the outline lies right of the middle, else backslash."""
    n = numbers(m["path"])
    pts = list(zip(n[0::2], n[1::2]))
    top = min(pts, key=lambda p: p[1])
    mid = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    return "slash" if top[0] > mid else "backslash"


def openings(d):
    marks = right_marks(d)
    out = []
    for i in range(1, len(TABLE) + 1):
        m = marks[f"side-right-opening-{i:02d}"]
        x0, y0, x1, y1 = box(m)
        out.append((kind_of(m["path"]), tilt_of(m) if kind_of(m["path"]) == "slot" else None,
                    (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0))
    return out


@pytest.mark.parametrize("name", NAMES)
def test_right_wall_is_drawn_with_34_openings_and_one_tab(name):
    d = device(name)
    right = d["views"]["right"]
    assert "empty" not in right and right["size"]["w"] == DEPTH
    marks = right_marks(d)
    ids = sorted(k for k in marks if k.startswith("side-right-opening-"))
    assert ids == [f"side-right-opening-{i:02d}" for i in range(1, len(TABLE) + 1)]
    kinds = [kind_of(marks[i]["path"]) for i in ids]
    assert (kinds.count("slot"), kinds.count("hole"), kinds.count("rect")) == (25, 5, 4)
    assert "side-right-tab-01" in marks
    for m in marks.values():
        assert m["filled"] is True and m.get("for") == "chassis"


@pytest.mark.parametrize("name", NAMES)
def test_every_opening_stands_where_the_measured_table_puts_it(name):
    for i, (row, got) in enumerate(zip(TABLE, openings(device(name))), 1):
        kind, tilt, x, y, w, h, _ = row
        gk, gt, gx, gy, gw, gh = got
        assert (gk, gt) == (kind, tilt), (i, got, row)
        assert abs(gx - x) <= ALONG and abs(gy - y) <= ACROSS, (i, (gx, gy), (x, y))
        assert abs(gw - w) <= 0.3 and abs(gh - h) <= 0.3, (i, (gw, gh), (w, h))


def test_the_table_counts_the_slots_of_the_figure():
    slots = [r for r in TABLE if r[0] == "slot"]
    assert len([r for r in slots if r[6] in ("fig", "fig-end", "fig-seen-through")]) == 23
    assert len([r for r in slots if r[6] == "photo"]) == 2
    assert len([r for r in slots if r[1] == "backslash" and r[6] != "photo"]) == 4
    assert len([r for r in TABLE if r[0] == "hole" and r[6] == "fig"]) == 4


@pytest.mark.parametrize("name", NAMES)
def test_the_marks_stay_inside_the_wall_and_the_photographed_ones_are_behind_the_bracket(name):
    d = device(name)
    for m in right_marks(d).values():
        x0, y0, x1, y1 = box(m)
        assert x0 >= 0.0 and x1 <= DEPTH and y0 >= 0.0 and y1 <= HEIGHT, m["id"]
    for row, got in zip(TABLE, openings(d)):
        if row[6] == "photo":
            assert BRACKET[0] < got[2] < BRACKET[1] and got[3] > 11.0, row
    last = max(g[2] + g[4] / 2 for g in openings(d))
    assert DEPTH - last > 30.0, "the figure leaves 30 mm of plain wall behind the last opening"


@pytest.mark.parametrize("name", NAMES)
def test_right_wall_tab_lies_inside_the_last_rectangle(name):
    marks = right_marks(device(name))
    rect = marks["side-right-opening-33"]
    rx0, ry0, rx1, ry1 = box(rect)
    tab = marks["side-right-tab-01"]
    tx0, ty0, tx1, ty1 = box(tab)
    assert (tx0, ty0, tx1 - tx0, ty1 - ty0) == pytest.approx(TAB, abs=0.15)
    assert rx0 - 0.1 <= tx0 and tx1 <= rx1 + 0.1 and ry0 - 0.1 <= ty0 and ty1 <= ry1 + 0.1
    assert tab["fill"] != rect["fill"], "the tab is light metal against the dark opening"


def test_the_right_wall_is_not_a_copy_of_the_left_wall():
    for name in NAMES:
        d = device(name)
        left = [m for m in d["views"]["left"]["silkscreen"] if m["id"].startswith("side-opening-")]
        assert len(left) == 29 and len(openings(d)) == 34


def test_the_three_devices_draw_one_pattern():
    a, b, c = (openings(device(n)) for n in NAMES)
    assert a == b == c


@pytest.mark.parametrize("name", NAMES)
def test_the_notes_and_gaps_say_what_the_right_wall_is(name):
    d = device(name)
    note = d["provenance"]["side-right"]
    assert note["confidence"] == "estimated"
    for word in ("Figure 1-12", "OL-19732-04", "386 mm", "44.45 mm", "8 mm", "bracket", "299 mm", "second drawing", "not a copy of the left wall"):
        assert word in note["note"], word
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["the-undrawn-faces"]["scope"] == ["top", "bottom"]
    assert gaps["right-wall-rims-and-waists"]["scope"] == ["right"]
    assert gaps["right-wall-behind-the-bracket"]["scope"] == ["right"]
    assert "8 mm" in gaps["right-wall-behind-the-bracket"]["wanted"]
    assert "right-wall-between-the-groups" not in gaps and "right-wall-pattern-on-the-poe-models" not in gaps


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
def test_built_right_face_centres_each_opening_within_the_table(name):
    built = built_centres(name)
    assert sorted(built) == [f"side-right-opening-{i:02d}" for i in range(1, len(TABLE) + 1)], "34 openings, counted in the build"
    for i, row in enumerate(TABLE, 1):
        bx, by = built[f"side-right-opening-{i:02d}"]
        assert abs(bx - row[2]) <= ALONG and abs(by - row[3]) <= ACROSS, (i, (bx, by), row[2:4])

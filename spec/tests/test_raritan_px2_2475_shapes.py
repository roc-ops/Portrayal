"""The Raritan PX2-2475 draws the shapes its specification's pictures show.

The specification's controller-panel picture shows rounded corners on the panel and on both display windows; its
elevation shows two rows of two seven-segment digits in one window and three rows of two in the other (ten digits,
each about 5.5 mm wide and 8.3 mm high, with one point at the upper right of each row) and a small ring beside each of
the 24 outlets; the panel picture also shows a T-shaped line between the two round buttons, a ring round each of the
console jack's two screw holes, one outline round the FEATURE and ETHERNET jacks and a ring for the reset button; its
rear view prints the first mounting button 145.0 mm from the end; its depth dimension, 65.3 mm, ends on the outermost
body line of the side view. What is true of the library once the device draws them:

  - the panel and the two display windows have rounded corners;
  - the windows carry ten digits, each wholly inside its own window: four in the first, in two rows of two, and six in
    the second, in three rows of two; each row has one point, at the right-hand digit;
  - the T line stands in the gap between the two round buttons, the screw-hole rings are centred on the holes, one
    outline holds both stacked jacks, and the reset button is a plain ring with no pinhole part;
  - each outlet has one ring of the same size, at the same place beside it, and it stands between its outlet and the
    one before (or the end of the strip);
  - the side faces draw the lines of the profile up to the outermost body line, put their front plane at 65.3 mm, and
    hold nothing that lies wholly beyond the 65 mm depth;
  - the two mounting buttons are centred 145.0 and 1389.0 mm from the top end.

These read the device source and its contracts. They read no library/dist and render nothing.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "raritan" / "px2-2475" / "device.yaml"


def device():
    return yaml.safe_load(DEVICE.read_text())


def front_decor():
    return {d["id"]: d for d in device()["views"]["front"]["panel"]["decor"]}


def front_placements():
    return {p["id"]: p for p in device()["views"]["front"]["components"]["placements"]}


def front_marks():
    return {m["id"]: m for m in device()["views"]["front"]["silkscreen"] if m.get("id")}


def test_the_panel_and_both_display_windows_have_rounded_corners():
    decor = front_decor()
    for i in ("controller-panel", "display-window-1", "display-window-2"):
        assert decor[i].get("rx", 0) > 0, i


def digit_parts(mark):
    """(box of the segments, number of points) of one digit path, in the view's frame."""
    parts = [p for p in re.split(r"(?=M )", mark["path"]) if p.strip()]
    segments = [p for p in parts if " a " not in p]
    points = [p for p in parts if " a " in p]
    xs, ys = [], []
    for p in segments:
        for x, y in re.findall(r"[ML] (-?\d+\.?\d*) (-?\d+\.?\d*)", p):
            xs.append(float(x))
            ys.append(float(y))
    x0, y0 = mark["at"]
    return (x0 + min(xs), y0 + min(ys), x0 + max(xs), y0 + max(ys)), len(points)


def test_each_window_carries_its_digits_inside_it():
    decor = front_decor()
    marks = {i: m for i, m in front_marks().items() if i.startswith("digit-")}
    assert sorted(marks, key=lambda i: int(i.split("-")[1])) == [f"digit-{n}" for n in range(1, 11)]
    inside = {"display-window-1": [], "display-window-2": []}
    for i, m in marks.items():
        (bx0, by0, bx1, by1), _ = digit_parts(m)
        for w in inside:
            wx, wy = decor[w]["at"]
            ww, wh = decor[w]["size"]
            if wx <= bx0 and bx1 <= wx + ww and wy <= by0 and by1 <= wy + wh:
                inside[w].append(i)
    assert (len(inside["display-window-1"]), len(inside["display-window-2"])) == (4, 6)


def test_the_digits_stand_in_rows_of_two_and_each_row_has_one_point():
    marks = {i: m for i, m in front_marks().items() if i.startswith("digit-")}
    rows = {}
    for i, m in marks.items():
        box, points = digit_parts(m)
        # the view runs the drawing a quarter turn: a row of the drawing is one x of the view, a digit in it one y
        rows.setdefault((round(box[0], 2), "window-1" if box[1] < 450 else "window-2"), []).append((box[1], i, box, points))
    assert sorted(len(r) for r in rows.values()) == [2, 2, 2, 2, 2]
    assert sum(1 for k in rows if k[1] == "window-1") == 2 and sum(1 for k in rows if k[1] == "window-2") == 3
    for key, row in rows.items():
        row.sort()
        assert [p for *_, p in row] == [0, 1], key  # the point is at the right-hand digit of the row
        for _, _, box, _ in row:
            assert 5.4 <= box[3] - box[1] <= 5.6 and 8.2 <= box[2] - box[0] <= 8.4, box
        assert abs((row[1][2][1] - row[0][2][1]) - 5.5) < 0.05, key  # the two digits of a row touch
    for window in ("window-1", "window-2"):
        xs = sorted(k[0] for k in rows if k[1] == window)
        assert all(abs((b - a) - 10.6) < 0.05 for a, b in zip(xs, xs[1:])), window  # the row pitch the picture gives


def test_the_t_line_stands_between_the_two_round_buttons():
    decor = front_decor()
    up, down = decor["nav-button-up"], decor["nav-button-down"]
    t = front_marks()["button-t-line"]
    xs = [float(n) for n in re.findall(r"-?\d+\.?\d*", t["path"])[0::2]]
    ys = [float(n) for n in re.findall(r"-?\d+\.?\d*", t["path"])[1::2]]
    x0, y0, x1, y1 = t["at"][0] + min(xs), t["at"][1] + min(ys), t["at"][0] + max(xs), t["at"][1] + max(ys)
    assert up["at"][1] + up["size"][1] - 0.05 <= y0 and y1 <= down["at"][1] + 0.05  # in the gap along the strip
    assert up["at"][0] - 0.05 <= x0 and x1 <= up["at"][0] + up["size"][0] + 0.05  # no taller than the buttons
    assert 2.5 <= y1 - y0 <= 3.1 and 5.5 <= x1 - x0 <= 6.7  # a bar 2.8 across and a stem 6.3 long


def test_each_console_screw_hole_has_a_ring_round_it():
    decor = front_decor()
    for n in (1, 2):
        hole, ring = decor[f"console-screw-hole-{n}"], decor[f"console-screw-ring-{n}"]
        hole_c = (hole["at"][0] + hole["size"][0] / 2, hole["at"][1] + hole["size"][1] / 2)
        ring_c = (ring["at"][0] + ring["size"][0] / 2, ring["at"][1] + ring["size"][1] / 2)
        assert abs(hole_c[0] - ring_c[0]) < 0.01 and abs(hole_c[1] - ring_c[1]) < 0.01
        assert ring["size"] == [4.2, 4.2] and ring["rx"] == 2.1 and ring["fill"] == "none"
        assert ring["size"][0] > hole["size"][0]


def jack_box(placement):
    ns, rest = placement["ref"].split("@")[0].rsplit("/", 1)
    version = placement["ref"].split("@")[1]
    size = yaml.safe_load((LIB / "components" / ns / rest / f"v{version}" / "contract.yaml").read_text())["size"]
    x, y, w, h = placement["at"][0], placement["at"][1], size["w"], size["h"]
    if placement.get("rotate") in (90, 270):
        cx, cy = x + w / 2, y + h / 2
        return (cx - h / 2, cy - w / 2, cx + h / 2, cy + w / 2)
    return (x, y, x + w, y + h)


def test_one_outline_holds_the_feature_jack_over_the_ethernet_jack():
    placed = front_placements()
    plate = front_decor()["feature-ethernet-plate"]
    px0, py0 = plate["at"]
    px1, py1 = px0 + plate["size"][0], py0 + plate["size"][1]
    for jack in ("feature", "eth"):
        x0, y0, x1, y1 = jack_box(placed[jack])
        assert px0 <= x0 and px1 >= x1 and py0 <= y0 and py1 >= y1, jack
    assert plate["fill"] == "none"
    assert 33.0 <= plate["size"][0] <= 36.0 and 16.0 <= plate["size"][1] <= 18.0  # 34.4 x 16.9 read from the drawing


def test_the_reset_button_is_a_ring_with_no_pinhole():
    placed = front_placements()
    assert "reset" not in placed
    assert not [p for p in placed.values() if p["ref"] == "common/reset-button@1"]
    ring = front_decor()["reset-ring"]
    assert ring["size"] == [2.4, 2.4] and ring["rx"] == 1.2 and ring["fill"] == "none"
    assert not [i for i in front_decor() if "pinhole" in i]


def test_each_outlet_has_one_ring_of_one_size_at_one_place_beside_it():
    decor = front_decor()
    placed = front_placements()
    rings = {i: d for i, d in decor.items() if i.startswith("outlet-lamp-")}
    assert sorted(rings, key=lambda i: int(i.rsplit("-", 1)[1])) == [f"outlet-lamp-{n}" for n in range(1, 25)]
    offsets = set()
    for n in range(1, 25):
        ring, outlet = rings[f"outlet-lamp-{n}"], placed[f"outlet-{n}"]
        assert ring["size"][0] == ring["size"][1] == 4.3 and ring["rx"] == 2.15
        centre_x, centre_y = ring["at"][0] + 2.15, ring["at"][1] + 2.15
        offsets.add((round(centre_x, 2), round(centre_y - (outlet["at"][1] + 13.5), 2)))
        # stands in the gap before the outlet: past the previous outlet's far edge, short of this one's near edge
        assert centre_y + 2.15 < outlet["at"][1] and ring["at"][1] > outlet["at"][1] - 35.0 + 27.0 - 0.01
    assert len(offsets) == 1


def side_decor(view):
    return {d["id"]: d for d in device()["views"][view]["panel"]["decor"]}


def test_the_side_views_hold_nothing_wholly_beyond_the_65_mm_depth():
    # the depth dimension's extension lines end on the outermost body line, 65.3 from the rear; the outlet bodies,
    # their rings and the panel steps stand on it, so they lie beyond the depth the face is drawn to
    for view in ("left", "right"):
        decor = side_decor(view)
        depth = device()["views"][view]["size"]["w"]
        assert depth == 65 == device()["chassis"]["depth"]
        for i, d in decor.items():
            x0, x1 = d["at"][0], d["at"][0] + d["size"][0]
            assert x1 > 0 and x0 < depth, (view, i)
        assert not [i for i in decor if i.startswith(("outlet-body-", "outlet-lamp-edge-", "panel-step-"))], view
        assert len([i for i in decor if i.startswith("outlet-fixing-")]) == 24, view


def test_the_side_faces_put_the_front_plane_at_65_3_mm_from_the_rear():
    left, right = side_decor("left"), side_decor("right")
    for end in ("end-plate-top", "end-plate-bottom"):
        assert round(left[end]["at"][0] + left[end]["size"][0], 2) == 65.3, end  # from the rear (x 0) to the plane
        assert round(right[end]["at"][0], 2) == -0.3 and round(right[end]["at"][0] + right[end]["size"][0], 2) == 65.0, end
    # the body line 63.5 from the rear is a line of the profile, drawn on both faces
    assert round(left["profile-line-6"]["at"][0], 2) == 63.5 and round(right["profile-line-6"]["at"][0], 2) == 1.35
    lines = sorted(round(d["at"][0], 2) for i, d in left.items() if i.startswith("profile-line-"))
    assert lines == [2.0, 6.5, 8.7, 59.95, 61.5, 63.5]


def test_the_depth_gap_gives_the_plane_and_the_height_the_bodies_stand_over_it():
    gaps = {g["what"]: g for g in device()["gaps"]}
    note = gaps["side-reach"]["note"]
    assert "65.3" in note and "3.5" in note and "overhang" in note
    assert "63.44" not in DEVICE.read_text()


def test_the_front_shows_a_fixing_block_at_each_outlet_on_both_long_edges():
    decor = front_decor()
    placed = front_placements()
    for side in ("left", "right"):
        for n in range(1, 25):
            block = decor[f"edge-fixing-{side}-{n}"]
            assert abs(block["at"][1] + 1.3 - (placed[f"outlet-{n}"]["at"][1] + 13.5)) < 0.05 and block["size"][1] == 2.6


def test_the_console_jack_has_its_flange_and_two_holes_25_mm_apart():
    decor = front_decor()
    one, two = decor["console-screw-hole-1"], decor["console-screw-hole-2"]
    assert round(two["at"][1] - one["at"][1], 1) == 25.0 and one["size"] == [3.1, 3.1]
    flange = decor["console-flange"]
    assert flange["size"] == [6.6, 31.5] and flange["rx"] == 3.3


def test_the_round_marks_are_on_the_left_face_only():
    left = side_decor("left")
    right = side_decor("right")
    assert len([i for i in left if i.startswith("round-mark-") and i.endswith("-outer")]) == 12
    assert not [i for i in right if i.startswith("round-mark-")]
    assert len([m for m in device()["views"]["left"]["silkscreen"] if m["id"].endswith("-triangle")]) == 12


def test_the_mounting_buttons_are_centred_where_the_rear_view_prints_them():
    rear = {p["id"]: p for p in device()["views"]["rear"]["components"]["placements"]}
    size = yaml.safe_load((LIB / "components" / "raritan" / "px3-mounting-button" / "v1" / "contract.yaml").read_text())["size"]
    first = rear["button-1"]["at"][1] + size["h"] / 2
    second = rear["button-2"]["at"][1] + size["h"] / 2
    assert round(first, 1) == 145.0 and round(second - first, 1) == 1244.0

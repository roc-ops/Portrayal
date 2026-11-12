"""The Raritan PX2-2475 draws the shapes its specification's pictures show.

The specification's controller-panel picture shows rounded corners on the panel and on both display windows; its
elevation shows a seven-segment digit outline in each window (two in the LINE / CB / UB window, three in the other)
and a small ring beside each of the 24 outlets; its rear view prints the first mounting button 145.0 mm from the end.
What is true of the library once the device draws them:

  - the panel and the two display windows have rounded corners;
  - the windows carry five digits, each wholly inside its own window, two in the first and three in the second;
  - each outlet has one ring of the same size, at the same place beside it, and it stands between its outlet and the
    one before (or the end of the strip);
  - the two mounting buttons are centred 145.0 and 1389.0 mm from the top end.

These read the device source and one contract. They read no library/dist and render nothing.
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


def test_the_panel_and_both_display_windows_have_rounded_corners():
    decor = front_decor()
    for i in ("controller-panel", "display-window-1", "display-window-2"):
        assert decor[i].get("rx", 0) > 0, i


def path_points(path):
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", path)]
    return nums


def test_each_window_carries_its_digits_inside_it():
    decor = front_decor()
    marks = {m["id"]: m for m in device()["views"]["front"]["silkscreen"] if str(m.get("id", "")).startswith("digit-")}
    assert sorted(marks) == [f"digit-{n}" for n in range(1, 6)]
    inside = {"display-window-1": [], "display-window-2": []}
    for m in marks.values():
        x, y = m["at"]
        for w in inside:
            wx, wy = decor[w]["at"]
            ww, wh = decor[w]["size"]
            if wx <= x and x + 8.1 <= wx + ww and wy <= y and y + 11.0 <= wy + wh:
                inside[w].append(m["id"])
    assert (len(inside["display-window-1"]), len(inside["display-window-2"])) == (2, 3)


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


def test_the_side_views_show_the_24_outlet_bodies_on_the_printed_pitch():
    placed = front_placements()
    for view in ("left", "right"):
        decor = side_decor(view)
        bodies = [decor[f"outlet-body-{n}"] for n in range(1, 25)]
        for n, body in enumerate(bodies, start=1):
            centre = body["at"][1] + body["size"][1] / 2
            assert abs(centre - (placed[f"outlet-{n}"]["at"][1] + 13.5)) < 0.3, (view, n)
        assert {round(b["size"][0], 1) for b in bodies} == {5.2}


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

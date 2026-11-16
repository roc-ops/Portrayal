"""The shapes a held picture shows on the Digi PortServer TS 1, 2 and 4 and the Connect IT 4.

What the pictures fix, and so what these tests hold.
PortServer TS line art: an inner outline inside each end.
PortServer TS line art: tabs under each end.
PortServer TS photograph: four holes in the left wall, a pair near each end, and the cover seam.
Connect IT 4 photographs: a rounded inner panel on the front.
Connect IT 4 photographs: one metal frame round the four serial jacks.

The tests read these four devices and nothing else.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/digi"

TS = ["portserver-ts-1", "portserver-ts-2", "portserver-ts-4"]
TS_DEPTH, TS_WIDTH = 133.4, 84.6


def device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def decor(name, view):
    return {d["id"]: d for d in ((device(name)["views"][view].get("panel") or {}).get("decor") or []) if "id" in d}


@pytest.mark.parametrize("name", TS)
@pytest.mark.parametrize("view,at,size", [("front", [1.5, 1.5], [81.6, 21.2]), ("rear", [2.0, 2.3], [80.6, 20.5])])
def test_each_end_carries_the_inner_outline_the_line_art_draws(name, view, at, size):
    rim = decor(name, view)["end-rim"]
    assert rim["at"] == at and rim["size"] == size
    assert rim.get("stroke") and rim.get("stroke-width")


@pytest.mark.parametrize("name", TS)
def test_the_rear_legend_sits_inside_the_rear_outline(name):
    rim = decor(name, "rear")["end-rim"]
    legend = [s for s in device(name)["views"]["rear"]["silkscreen"] if s.get("text") == "RJ-45 Serial"][0]
    assert legend["at"][1] < rim["at"][1] + rim["size"][1]


@pytest.mark.parametrize("name", TS)
def test_the_left_wall_has_its_four_holes(name):
    holes = {k: v for k, v in decor(name, "left").items() if k.startswith("wall-hole-")}
    assert sorted(holes) == ["wall-hole-front-a", "wall-hole-front-b", "wall-hole-rear-a", "wall-hole-rear-b"]
    for hole in holes.values():
        x, y = hole["at"]
        w, h = hole["size"]
        assert 0 <= x and x + w <= TS_DEPTH and 0 <= y and y + h <= 24.2
        assert hole["rx"] == min(w, h) / 2, "a round or oval hole is a decor rectangle with corners rounded to half its short side"
    # a left view runs from the rear: two holes in the rear fifth of the wall, two in the front fifth
    rear = [h["at"][0] for k, h in holes.items() if "rear" in k]
    front = [h["at"][0] for k, h in holes.items() if "front" in k]
    assert max(rear) < TS_DEPTH / 5 < TS_DEPTH * 4 / 5 < min(front)


@pytest.mark.parametrize("name", TS)
def test_the_larger_wall_holes_are_ovals_long_along_the_wall(name):
    holes = decor(name, "left")
    for key in ("wall-hole-rear-a", "wall-hole-front-a"):
        w, h = holes[key]["size"]
        assert w > h, key
    for key in ("wall-hole-rear-b", "wall-hole-front-b"):
        w, h = holes[key]["size"]
        assert w == h, key


@pytest.mark.parametrize("name", TS)
def test_the_left_wall_carries_the_cover_seam_near_its_top(name):
    seam = decor(name, "left")["cover-seam"]
    x, y = seam["at"]
    w, h = seam["size"]
    assert seam["kind"] == "seam" and seam["confidence"] == "estimated"
    assert x == 0 and w == TS_DEPTH and h <= 0.6
    assert 0 < y < 24.2 / 4


@pytest.mark.parametrize("name", TS)
def test_the_underside_carries_three_tabs_at_the_front_end_and_four_at_the_rear(name):
    tabs = {k: v for k, v in decor(name, "bottom").items() if k.startswith("tab-")}
    assert sorted(k for k in tabs if k.startswith("tab-front")) == ["tab-front-1", "tab-front-2", "tab-front-3"]
    assert sorted(k for k in tabs if k.startswith("tab-rear")) == ["tab-rear-1", "tab-rear-2", "tab-rear-3", "tab-rear-4"]
    for k, t in tabs.items():
        x, y = t["at"]
        w, h = t["size"]
        assert 0 <= x and x + w <= TS_WIDTH + 1e-6, k
        assert t["confidence"] == "estimated", k
        assert (y == 0) if "rear" in k else (round(y + h, 1) == TS_DEPTH), k


@pytest.mark.parametrize("name", TS)
def test_the_right_wall_is_still_a_stated_gap(name):
    assert device(name)["views"]["right"].get("empty")


def note(name, key):
    return device(name)["provenance"][key]["note"]


@pytest.mark.parametrize("name", TS)
def test_the_front_outline_note_states_its_insets_as_ranges(name):
    text = note(name, "end-rim")
    assert "one inset of 1.5 mm on all four sides" in text
    assert "1.5 to 2.0 mm" in text and "1.0 to 2.0 mm" in text
    assert "good to about 0.5 mm" in text
    assert "1.6 to 1.9" not in text and "0.6 mm" not in text


@pytest.mark.parametrize("name", TS)
def test_the_tab_note_states_the_front_depth_as_a_range(name):
    text = note(name, "tabs")
    assert "The front tabs read 1.5 to 4 mm deep" in text
    assert "The underside draws no depth." in text
    assert "2.5 to 4" not in text


@pytest.mark.parametrize("name", TS)
def test_the_oval_note_calls_its_orientation_a_convention(name):
    text = note(name, "side-wall")
    assert "a convention" in text
    assert "perspective gives" not in text


def test_the_connect_it_4_note_states_the_right_inset_as_a_range():
    text = note("connect-it-4", "front-panel")
    assert "4.5 to 5.4 mm" in text and "drawn at 5.9 mm" in text
    assert "least certain figure" in text


def test_the_connect_it_4_front_has_its_rounded_inner_panel():
    d = device("connect-it-4")
    panel = decor("connect-it-4", "front")["face-panel"]
    assert panel["rx"] == 2.0
    x, y = panel["at"]
    w, h = panel["size"]
    face = d["views"]["front"]["size"]
    assert 0 < x and x + w < face["w"] and 0 < y and y + h < face["h"]


def test_the_connect_it_4_serial_jacks_stand_in_one_frame():
    d = device("connect-it-4")
    frame = decor("connect-it-4", "rear")["serial-frame"]
    jacks = [p for p in d["views"]["rear"]["components"]["placements"] if p["id"].startswith("serial-")]
    assert len(jacks) == 4
    fx, fy = frame["at"]
    fw, fh = frame["size"]
    for p in jacks:
        assert fx <= p["at"][0] and p["at"][0] + 12.7 <= fx + fw
        assert fy <= p["at"][1] <= fy + fh

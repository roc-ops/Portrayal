"""The top and the left side of the WTI CPM-800, CPM-1600 and DSM-8 families.

The maker's one-page dimensional drawing of each family shows the top cover with its screws and one side with a row of vent slots,
a cover plate and screws. What is true of the library once those faces are drawn:

  - the top carries one screw head per screw the drawing shows, each with its cross mark;
  - the left carries the vent slots in the count the drawing shows, the plate, and the screws, each with its cross mark;
  - the slots form one row at a fixed pitch inside the depth of the box;
  - the underside and the right side stay bare and say so, and the gaps name what is still missing;
  - the old `sides` gap is gone.

These read the device sources. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# model: (vent slots on the side, screws on the top, screws on the side)
DRAWN = {
    "cpm-800-1": (31, 4, 4),
    "cpm-800-2": (31, 4, 4),
    "cpm-1600-1": (39, 5, 8),
    "cpm-1600-2": (39, 5, 8),
    "dsm-8": (22, 4, 4),
}


def device(name):
    return yaml.safe_load((LIB / "devices" / "wti" / name / "device.yaml").read_text())


def decor(name, view, kind):
    return [d for d in (device(name)["views"][view].get("panel") or {}).get("decor", []) if d.get("kind") == kind]


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_the_side_carries_the_vent_slots_the_drawing_shows(name):
    slots = decor(name, "left", "vent-slot")
    assert len(slots) == DRAWN[name][0]


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_the_slots_are_one_row_at_one_pitch_inside_the_depth(name):
    d = device(name)
    slots = decor(name, "left", "vent-slot")
    xs = [s["at"][0] for s in slots]
    ys = {s["at"][1] for s in slots}
    gaps = {round(b - a, 1) for a, b in zip(xs, xs[1:])}
    assert len(ys) == 1
    assert len(gaps) == 1
    assert xs[0] > 0 and xs[-1] + slots[-1]["size"][0] < d["chassis"]["depth"]


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_each_screw_head_has_its_cross_mark(name):
    for view, count in (("top", DRAWN[name][1]), ("left", DRAWN[name][2])):
        heads = decor(name, view, "screw")
        crosses = [s for s in (device(name)["views"][view].get("silkscreen") or []) if "path" in s]
        assert len(heads) == count
        assert len(crosses) == count
        for h in heads:
            cx, cy = h["at"][0] + h["size"][0] / 2, h["at"][1] + h["size"][1] / 2
            assert any(abs(c["at"][0] - cx) < 0.01 and abs(c["at"][1] - cy) < 0.01 for c in crosses)


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_the_faces_are_the_size_of_the_box(name):
    d = device(name)
    ch = d["chassis"]
    assert d["views"]["top"]["size"] == {"w": ch["width"], "h": ch["depth"]}
    assert d["views"]["left"]["size"] == {"w": ch["depth"], "h": ch["height"]}


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_the_underside_and_the_right_side_stay_bare_and_say_why(name):
    views = device(name)["views"]
    for view in ("bottom", "right"):
        assert len(views[view]["empty"]) > 40
        assert not (views[view].get("panel") or {}).get("decor")


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_the_gaps_name_what_is_missing_and_the_old_one_is_gone(name):
    gaps = {g["what"]: g for g in device(name)["gaps"]}
    assert "sides" not in gaps
    assert gaps["underside"]["scope"] == ["bottom"]
    assert gaps["right-side"]["scope"] == ["right"]
    assert gaps["side-identity"]["scope"] == ["left"]


# Where the side view stands on the maker's sheet: below the top view on the four CPM sheets, beside it on the DSM-8 sheet.
SHEET_PLACE = {
    "cpm-800-1": "below the top view and lines up with it",
    "cpm-800-2": "below the top view and lines up with it",
    "cpm-1600-1": "below the top view and lines up with it",
    "cpm-1600-2": "below the top view and lines up with it",
    "dsm-8": "beside the top view",
}


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_the_side_identity_hint_says_where_the_view_stands_on_the_sheet(name):
    note = " ".join({g["what"]: g for g in device(name)["gaps"]}["side-identity"]["note"].split())
    assert SHEET_PLACE[name] in note
    assert ("stands beside" in note) == (name == "dsm-8")


@pytest.mark.parametrize("name", ["cpm-1600-1", "cpm-1600-2"])
def test_the_cpm_1600_note_states_the_printed_and_the_drawn_depth(name):
    note = " ".join(device(name)["provenance"]["top-and-left"]["note"].split())
    assert "good to about one millimetre" in note
    assert "12.50" in note and "10.4" in note


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_the_slots_are_outlines_as_the_drawings_show_them(name):
    assert {s.get("fill") for s in decor(name, "left", "vent-slot")} == {"none"}

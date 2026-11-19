"""Eaton SRCABLEDUCT1U: what the submittal drawing's back view and side view show is drawn.

The back view shows four small holes round each of five bosses. It shows four dimples with a slot set to
one side of each, and the bosses' inner rings. The side view shows the plate with a flange along each edge.
It shows the rounded channel floor, a boss pressed out behind the plate and a stud inside the channel.
It also shows the cover's return lips and snap tongues. Each is drawn, estimated, and none is left as a gap.
These tests read the device file and the two parts, so they need no build.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
PARTS = LIB / "components" / "eaton"
BOSS_CENTRES = [41.3 + 100 * i for i in range(5)]
CENTRE_Y = 21.845


def device():
    return yaml.safe_load((LIB / "devices" / "eaton" / "srcableduct1u" / "device.yaml").read_text())


def decor(view):
    return {d["id"]: d for d in device()["views"][view]["panel"]["decor"]}


def centre(d):
    return d["at"][0] + d["size"][0] / 2, d["at"][1] + d["size"][1] / 2


def test_each_boss_has_four_small_holes_round_it_on_the_rear():
    holes = [d for d in decor("rear").values() if d.get("kind") == "hole"]
    assert len(holes) == 20, "four round each of five bosses"
    for d in holes:
        assert d["size"] == [4.5, 4.5] and d["rx"] == 2.25, "a round hole 4.5 mm across"
    for c in BOSS_CENTRES:
        near = sorted(centre(d) for d in holes if abs(centre(d)[0] - c) < 13)
        assert len(near) == 4
        for x, y in near:
            assert abs(abs(x - c) - 12.7) < 0.01 and abs(abs(y - CENTRE_Y) - 12.7) < 0.01, "12.7 mm from the boss centre"


def test_the_bosses_and_dimples_are_drawn_at_the_back_views_figures():
    d = decor("rear")
    for i, c in enumerate(BOSS_CENTRES, 1):
        assert d[f"boss-{i}"]["size"] == [11.9, 11.9] and d[f"boss-ring-{i}"]["size"] == [8.9, 8.9]
        assert abs(centre(d[f"boss-{i}"])[0] - c) < 0.01 and abs(centre(d[f"boss-ring-{i}"])[0] - c) < 0.01
    for i in range(1, 5):
        dimple, slot = d[f"dimple-{i}"], d[f"dimple-slot-{i}"]
        assert dimple["size"] == [25.6, 25.6] and slot["size"] == [15, 5]
        assert abs(centre(dimple)[0] - (91.3 + 100 * (i - 1))) < 0.01
        assert abs((centre(dimple)[0] - centre(slot)[0]) - 5.0) < 0.01, "the slot sits 5 mm to the left of the dimple's centre"
    ends = [d[f"dimple-slot-{i}"] for i in (1, 4)]
    assert abs((centre(ends[1])[0] - centre(ends[0])[0]) - 300) < 0.01, "the drawing's 300 mm, slot centre to slot centre"


def test_each_slot_of_both_walls_has_the_small_ring_the_isometric_shows():
    for view in ("top", "bottom"):
        d = decor(view)
        rings = [d[f"slot-ring-{n}"] for n in range(1, 25)]
        assert len(rings) == 24 and len([i for i in d if i.startswith("slot-ring-")]) == 24
        for n, ring in enumerate(rings, 1):
            slot = d[f"slot-{n}"]
            assert ring["size"] == [3.5, 3.5] and ring["rx"] == 1.75 and "fill" not in ring and ring["stroke"]
            assert abs(centre(ring)[0] - centre(slot)[0]) < 0.01, "centred on its slot"
            assert abs((slot["at"][1] + slot["size"][1]) - centre(ring)[1] - 1.75) < 0.01, "1.75 mm in from the cover end"


def test_the_end_views_place_the_rear_part_and_no_longer_draw_a_solid_back():
    doc = device()
    for view, ident, rotate in (("left", "end-left", None), ("right", "end-right", 180)):
        assert "back" not in decor(view), view
        placed = {p["id"]: p for p in doc["views"][view]["components"]["placements"]}
        assert placed[ident]["ref"] == "eaton/tripplite-duct-1u-end@1" and placed[ident].get("rotate") == rotate
        assert placed[f"cover-{view}"]["ref"] == "eaton/tripplite-duct-1u-cover-side@1"
    placed = {p["id"]: p for p in doc["views"]["left"]["components"]["placements"]}
    walls = decor("left")
    assert abs(placed["end-left"]["at"][0] + 9.7 - walls["wall-upper"]["at"][0]) < 0.01, "the walls start where the rear part ends"


def test_the_rear_part_draws_the_flanges_the_floor_the_boss_and_the_stud():
    contract = yaml.safe_load((PARTS / "tripplite-duct-1u-end" / "v1" / "contract.yaml").read_text())
    skin = (PARTS / "tripplite-duct-1u-end" / "v1" / "skins" / "default.svg").read_text()
    assert set(contract["elements"]) == {"flange-top", "flange-bottom", "plate", "floor", "boss", "stud"}
    for ident in contract["elements"]:
        assert f'id="{ident}"' in skin, ident
    assert contract["size"] == {"w": 9.7, "h": 43.69}
    assert contract["elements"]["flange-top"]["size"] == [6.2, 1.2], "the flange runs to the plate's rear edge"
    assert 'data-fill-from="finish"' in skin


def test_the_cover_end_draws_the_return_lips_the_tongues_and_the_beaks_on_both_sides():
    skin = (PARTS / "tripplite-duct-1u-cover-side" / "v1" / "skins" / "default.svg").read_text()
    for ident in ("return-lip-top", "return-lip-bottom", "tongue-top", "tongue-bottom", "beak-top", "beak-bottom"):
        assert f'id="{ident}"' in skin, ident
    for ident in ("tongue-top", "return-lip-top"):
        d = re.search(rf'id="{ident}" d="([^"]+)"', skin).group(1)
        assert re.search(r"[CQ]", d), f"the {ident} is the maker's S curve, drawn with curve segments"
    contract = yaml.safe_load((PARTS / "tripplite-duct-1u-cover-side" / "v1" / "contract.yaml").read_text())
    assert contract["size"] == {"w": 9.8, "h": 42.0}, "the cover's outline is unchanged"


def test_the_notes_no_longer_leave_a_drawn_feature_as_a_gap():
    doc = device()
    gaps = {g["what"]: g for g in doc["gaps"]}
    assert "not drawn" not in gaps["rear-features"]["note"] and "no clip" not in gaps["cover-fitting"]["note"]
    assert "twenty" in doc["provenance"]["rear"]["note"]
    assert "It is built as the documented side" in doc["provenance"]["left"]["note"]


def test_the_front_and_rear_draw_the_ears_41_26_high_with_the_plate_strip_behind():
    """The drawing prints the ears 41.26 high and the plate 43.69; a thin plate strip shows above and below."""
    base = PARTS / "tripplite-duct-1u-base" / "v1"
    skin = (base / "skins" / "default.svg").read_text()
    assert re.search(r'id="strip"[^>]*\bx="29.8"[^>]*\by="0"[^>]*width="423"[^>]*height="43.69"', skin), "the strip, full plate height"
    assert "M3,1.215" in skin and "V39.475" in skin and "42.475" in skin, "the ears' 41.26 centred in the 43.69"
    contract = yaml.safe_load((base / "contract.yaml").read_text())
    assert "41.26" in contract["provenance"]["size"]
    rear = decor("rear")
    assert rear["plate-back"]["at"][1] == 1.215 and rear["plate-back"]["size"] == [482.6, 41.26]
    assert rear["strip-back"]["at"] == [29.8, 0] and rear["strip-back"]["size"] == [423.0, 43.69]
    text = device()["provenance"]
    for key in ("size-conflict", "ears", "mount"):
        note = " ".join(text[key]["note"].split())
        assert "43.69 high over the ears" not in note and "apart across the 43.69" not in note, key
    assert "41.26" in " ".join(text["ears"]["note"].split())


def test_the_isometric_marks_are_a_gap_that_says_what_the_vector_paths_show():
    """The drawing's paths show ten marks that match no pressing one to one, so the gap names them and places none."""
    doc = device()
    gap = {g["what"]: g for g in doc["gaps"]}["inner-studs"]
    assert gap["reason"] == "needs-drawing" and gap["scope"] == ["left", "right"]
    note = " ".join(gap["note"].split()).lower()
    for word in ("ten", "three", "seven", "one to one"):
        assert word in note, word
    for word in ("cannot be read", "inner ends"):
        assert word not in note, word
    guides = " ".join(doc["provenance"]["guides"]["note"].split())
    assert "ten in all" in guides and "one to one" in guides
    assert "inner ends" not in guides and "cannot be read" not in guides


def test_the_rear_part_says_the_plate_is_high_and_not_over_the_ears():
    """The plate is 43.69 high and the ears 41.26, so the plate is not said to stand over the ears."""
    contract = yaml.safe_load((PARTS / "tripplite-duct-1u-end" / "v1" / "contract.yaml").read_text())
    size = " ".join(contract["provenance"]["size"].split())
    assert "high" in size and "over the ears" not in size


def test_the_top_views_rear_strip_is_the_inset_rounded_tab_the_drawing_shows():
    """The drawing's top view insets the rear strip 3.5 mm from each cover end and rounds its corners."""
    for view in ("top", "bottom"):
        back = decor(view)["back"]
        assert back["at"] == [28.9, 0] and back["size"] == [424.8, 5.0] and back["rx"] == 2, view

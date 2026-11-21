"""APC NetShelter AR7710 cable containment bracket (roc-ops/Portrayal#1097, part of #1091).

The AR7710 is a cable containment bracket for the NetShelter SX, SV and VX racks. APC's data sheet prints its
envelope and weight; the installation sheet draws one bracket and the data sheet's photographs show it and its
plate. What no page dimensions is estimated in the device and held here only to what the device itself declares.
Every test reads the device file; none reads `library/dist`.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "apc" / "ar7710" / "device.yaml"


def device():
    return yaml.safe_load(DEVICE.read_text())


def decor(doc, view):
    return doc["views"][view]["panel"]["decor"]


def with_prefix(items, prefix):
    return [d for d in items if d["id"].startswith(prefix)]


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def test_the_envelope_and_weight_are_the_data_sheets():
    doc = device()
    c = doc["chassis"]
    assert doc["manufacturer"] == "APC" and doc["model"] == "AR7710"
    assert close(c["width"], 80.0) and close(c["height"], 112.0) and close(c["depth"], 45.0)
    assert close(c["weight-kg"], 0.45, 0.0005)
    assert doc["attrs"]["physical"]["color"] == "Black"


def test_it_is_a_rack_side_part_and_its_front_is_taller_than_wide():
    doc = device()
    assert doc["chassis"]["mount"] == "rack-side" and doc["chassis"]["ru"] == 3
    front = doc["views"]["front"]["size"]
    assert front["h"] > front["w"], "L152: a rack-side part is drawn as it stands"
    assert close(front["w"], 80.0) and close(front["h"], 112.0)


def test_it_has_every_side_at_the_envelope_size():
    doc = device()
    assert set(doc["views"]) == {"front", "rear", "top", "bottom", "left", "right"}
    sizes = {k: (v["size"]["w"], v["size"]["h"]) for k, v in doc["views"].items()}
    assert sizes["front"] == sizes["rear"] == (80.0, 112.0)
    assert sizes["top"] == sizes["bottom"] == (80.0, 45.0)
    assert sizes["left"] == sizes["right"] == (45.0, 112.0)


def test_the_front_shows_two_keyholes_the_joint_slot_and_the_hook():
    front = decor(device(), "front")
    assert len(with_prefix(front, "keyhole-")) == 2, "a keyhole in each of the two pieces of the long face"
    assert len(with_prefix(front, "kstem-")) == 2, "each keyhole has its stem"
    assert len(with_prefix(front, "joint-")) == 1, "the open slot between the two pieces"
    assert len(with_prefix(front, "hook-")) == 1, "the hook of the right-hand piece in that slot"


def test_the_rear_shows_the_plate_with_two_screws_and_a_small_stud():
    rear = decor(device(), "rear")
    assert len(with_prefix(rear, "screw-")) == 2
    assert len(with_prefix(rear, "core-")) == 2, "a pale centre in each screw"
    assert len(with_prefix(rear, "pin-")) == 1, "one small pale stud"


def component(ref):
    name, major = ref.split("@")
    path = ROOT / "library" / "components" / name / f"v{major}" / "contract.yaml"
    return yaml.safe_load(path.read_text())


def test_the_rear_stands_one_shank_and_one_pin_in_a_well_as_deep_as_the_shank():
    doc = device()
    placed = {p["id"]: p for p in doc["views"]["rear"]["components"]["placements"]}
    assert set(placed) == {"base", "screws"}
    assert placed["screws"]["in"] == "base", "the screws stand in the well, so the depth tests judge them inside the part"
    well, screws = component(placed["base"]["ref"]), component(placed["screws"]["ref"])
    features = {f["node"]: f for f in screws["relief"]["features"]}
    assert set(features) == {"shank", "peg"}, "the one shank the photograph shows most plainly and the small pin"
    for feature in features.values():
        assert feature["out"] > 0 and feature["confidence"] == "estimated" and feature["source"]
    assert features["shank"]["out"] > features["peg"]["out"], "the pin is the short one"
    assert well["size"]["d"] >= features["shank"]["out"], "the well is as deep as the shank's reach"
    assert well["size"]["d"] <= doc["chassis"]["depth"], "and no deeper than the part"
    assert not with_prefix(decor(doc, "rear"), "shank-"), "a shank is not flat decor"
    assert {"screw-shanks", "shank-length"} <= {g["what"] for g in doc["gaps"]}


def test_each_end_face_has_one_keyhole_and_the_open_ends_show_the_wall():
    doc = device()
    for view in ("top", "bottom"):
        assert len(with_prefix(decor(doc, view), "keyhole-")) == 1
        assert len(with_prefix(decor(doc, view), "kstem-")) == 1
    for view in ("left", "right"):
        assert len(with_prefix(decor(doc, view), "mouth")) == 1, "the open end of the bracket"
    assert len(with_prefix(decor(doc, "right"), "notch")) == 1, "the joint slot cuts the front wall at this end"
    assert not with_prefix(decor(doc, "left"), "notch"), "the other end is closed by the tab"


def centre(item):
    return (item["at"][0] + item["size"][0] / 2, item["at"][1] + item["size"][1] / 2)


def luminance(colour):
    h = colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def by_id(items):
    return {d["id"]: d for d in items}


# The plate photograph on data sheet page 4, as fractions of the plate. Here u runs along its 112 mm side as it lies.
# And v runs along its 80 mm side. The rear is drawn standing: x = 80 - v * 80 and y = 112 * (1 - u).
U_LEFT, U_RIGHT, V_SCREWS, V_STUD = 0.241, 0.743, 0.617, 0.326


def rear_xy(u, v):
    return 80.0 - v * 80.0, 112.0 * (1.0 - u)


def test_the_rear_plate_is_mirrored_across_the_80_side_as_the_photograph_lies():
    rear = by_id(decor(device(), "rear"))
    for ident, u, v in (("screw-1", U_LEFT, V_SCREWS), ("screw-2", U_RIGHT, V_SCREWS), ("pin-1", U_LEFT, V_STUD)):
        x, y = rear_xy(u, v)
        cx, cy = centre(rear[ident])
        assert abs(cx - x) <= 0.8, f"{ident} stands at x {cx}, the photograph puts it at {x}"
        assert abs(cy - y) <= 1.1, f"{ident} stands at y {cy}, the photograph puts it at {y}"
    assert centre(rear["screw-1"])[0] < centre(rear["pin-1"])[0], "the stud is on the other side of the screws from x = 0"


def test_the_stud_is_directly_above_the_left_screw_and_the_screws_are_56_mm_apart():
    rear = by_id(decor(device(), "rear"))
    assert abs(centre(rear["pin-1"])[1] - centre(rear["screw-1"])[1]) <= 0.5
    spacing = abs(centre(rear["screw-1"])[1] - centre(rear["screw-2"])[1])
    assert abs(spacing - 56.2) <= 1.5, f"the screws are {spacing} mm apart"
    assert abs(centre(rear["screw-1"])[0] - centre(rear["screw-2"])[0]) <= 0.3


def test_the_shank_and_the_pin_stand_on_the_screw_centres():
    doc = device()
    rear = by_id(decor(doc, "rear"))
    placed = {p["id"]: p for p in doc["views"]["rear"]["components"]["placements"]}
    screws = component(placed["screws"]["ref"])["elements"]
    shank, peg = centre(screws["shank"]), centre(screws["peg"])
    assert abs(shank[0] - centre(rear["screw-2"])[0]) <= 0.2 and abs(shank[1] - centre(rear["screw-2"])[1]) <= 0.2
    assert abs(peg[0] - centre(rear["screw-1"])[0]) <= 0.2 and abs(peg[1] - centre(rear["screw-1"])[1]) <= 0.2


def test_the_plate_has_a_lighter_side_fold_down_each_end():
    rear = decor(device(), "rear")
    plate = by_id(rear)["plate"]
    folds = with_prefix(rear, "fold-")
    assert len(folds) == 2, "one strip at each end of the plate"
    ends = sorted(round(centre(f)[1]) for f in folds)
    assert ends[0] < 10 and ends[1] > 102, "one at each end of the 112 mm side"
    for f in folds:
        assert f["size"][1] <= 3.0 and f["size"][0] >= 60.0, "a thin strip down the whole end"
        assert luminance(f["fill"]) > luminance(plate["fill"]), "lighter than the plate"
        assert f["confidence"] == "estimated"


def test_each_plate_screw_has_a_dark_recess_between_its_ring_and_its_pale_centre():
    rear = decor(device(), "rear")
    plate = by_id(rear)["plate"]
    recesses = by_id(with_prefix(rear, "recess-"))
    assert len(recesses) == 2
    for n in (1, 2):
        ring, recess, core = (by_id(rear)[f"{k}-{n}"] for k in ("screw", "recess", "core"))
        assert recess["size"][0] < ring["size"][0] and recess["size"][0] > core["size"][0]
        assert all(abs(a - b) <= 0.1 for a, b in zip(centre(recess), centre(ring)))
        assert all(abs(a - b) <= 0.1 for a, b in zip(centre(core), centre(ring)))
        assert luminance(recess["fill"]) < luminance(plate["fill"]), "dark against the plate"
        assert luminance(core["fill"]) > luminance(ring["fill"])
        assert recess["confidence"] == "estimated"


def test_three_keyholes_are_documented_and_the_fourth_is_the_top_mirrored():
    doc = device()
    documented = len(with_prefix(decor(doc, "front"), "keyhole-")) + len(with_prefix(decor(doc, "top"), "keyhole-"))
    assert documented == 3, "two on the long face and one in the end face the sheets draw"
    top, bottom = by_id(decor(doc, "top")), by_id(decor(doc, "bottom"))
    for ident in ("keyhole-1", "kstem-1"):
        mirrored_left_edge = 80.0 - (top[ident]["at"][0] + top[ident]["size"][0])
        assert close(bottom[ident]["at"][0], mirrored_left_edge) and close(bottom[ident]["at"][1], top[ident]["at"][1])
    assert "three" in doc["description"] and "fourth" in doc["description"]
    assert "its three faces" not in doc["description"]


def test_the_notes_say_what_the_pages_show_and_no_more():
    doc = device()
    mount = doc["provenance"]["mount"]["note"]
    assert "own two screws" in mount and "rack-frame keyholes" in mount and "screwed to the rack frame" not in mount
    gaps = {g["what"]: g for g in doc["gaps"]}
    assert "SX frame" not in gaps["cabinet-fit"]["note"] and "rack frame" in gaps["cabinet-fit"]["note"]
    keyhole = gaps["keyhole-function"]["note"]
    assert "screw head" in keyhole and "not drawn" in keyhole and "No page says what lands" not in keyhole
    shapes = gaps["perforation-shapes"]["note"]
    assert "notches" in shapes, "the corner notches of the plate folds are named as not drawn"


def test_it_has_no_connector_and_names_what_the_pages_leave_open():
    doc = device()
    assert not doc.get("ports") and "capacity" in doc["provenance"]
    gaps = {g["what"] for g in doc["gaps"]}
    assert {"set-or-single", "cabinet-fit", "cable-capacity", "plate-joint", "installed-orientation"} <= gaps

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


def test_it_has_no_connector_and_names_what_the_pages_leave_open():
    doc = device()
    assert not doc.get("ports") and "capacity" in doc["provenance"]
    gaps = {g["what"] for g in doc["gaps"]}
    assert {"set-or-single", "cabinet-fit", "cable-capacity", "plate-joint", "installed-orientation"} <= gaps

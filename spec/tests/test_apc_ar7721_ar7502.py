"""APC NetShelter cable managers AR7721 and AR7502 (roc-ops/Portrayal#1097, part of #1091).

The AR7721 is two 20U lengths for a 600 mm wide, 42U cabinet. The AR7502 is a perforated rear cable channel for a
42U cabinet. The envelope is what APC's data sheets print; what the sheets' pictures show is counted below. What no
page dimensions is estimated in the device and is held here only to what the device itself declares. Every test
reads the device files and the parts they place; none reads `library/dist`.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RU = 44.45


def device(name):
    return yaml.safe_load((LIB / "devices" / "apc" / name / "device.yaml").read_text())


def contract(name, version):
    return yaml.safe_load((LIB / "components" / "apc" / name / f"v{version}" / "contract.yaml").read_text())


def decor(doc, view):
    return doc["views"][view]["panel"]["decor"]


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def with_prefix(items, prefix):
    return [d for d in items if d["id"].startswith(prefix)]


def test_the_20u_length_version_2_is_20_crossbars_with_lips_on_a_plate():
    c = contract("nsx-vcm-20u", 2)
    assert c["version"] == "2.0.0" and close(c["size"]["w"], 107.0) and close(c["size"]["h"], 889.0, 0.5)
    els = c["elements"]
    bars = sorted(v["at"][1] for k, v in els.items() if k.startswith("b"))
    assert len(bars) == 20 and all(close(b - a, RU) for a, b in zip(bars, bars[1:])), "a crossbar to each rack unit"
    lips = [v for k, v in els.items() if k.startswith("l")]
    assert len(lips) == 20, "a lip at the end of each crossbar"
    assert all(v["size"][1] >= 30.0 for v in lips), "the photograph shows lips about 36 mm tall, nearly continuous"
    assert len([k for k in els if k.startswith("m")]) == 2, "two round marks on the plate"
    blocks = [v for k, v in els.items() if k.startswith("k")]
    assert len(blocks) == 20, "a block to each crossbar on the grey strip"
    # The strip reads 27 px at 2.41 px/mm, which is 11.2 mm.
    assert close(els["strip"]["size"][0], 11.0), "the grey strip along the plate edge is about 11 mm wide"
    assert 35.0 <= els["plate"]["size"][0] + els["strip"]["size"][0] <= 45.0, "plate and strip are about 40 per cent of the width"
    assert contract("nsx-vcm-20u", 1)["version"] == "1.0.0", "the first version stays for the AR7722"


def test_the_ar7721_is_two_20u_lengths_of_the_data_sheets_width_and_depth():
    doc = device("ar7721")
    c = doc["chassis"]
    assert doc["manufacturer"] == "APC" and doc["model"] == "AR7721"
    assert close(c["width"], 107.0) and close(c["depth"], 45.0) and close(c["height"], 2 * 20 * RU, 0.5)
    assert c["mount"] == "rack-side" and c["ru"] == 40 and close(c["weight-kg"], 2.18, 0.0005)
    placed = doc["views"]["front"]["components"]["placements"]
    assert [p["ref"] for p in placed] == ["apc/nsx-vcm-20u@2"] * 2
    length = contract("nsx-vcm-20u", 2)
    assert close(length["size"]["h"], 889.0, 0.5), "the data sheet's 889 mm is one length"
    assert [p["at"][1] for p in placed] == [0.0, pytest.approx(length["size"]["h"])]


def test_the_ar7721_has_every_side_and_a_duct_at_one_rack_unit_pitch():
    doc = device("ar7721")
    assert set(doc["views"]) == {"front", "rear", "top", "bottom", "left", "right"}
    guide = doc["views"]["front"]["guides"][0]
    assert guide["kind"] == "duct" and guide["run"] == "y" and guide["finger-pitch"] == RU
    assert close(guide["size"][1], doc["chassis"]["height"])


def test_the_ar7721_rear_has_a_crossbar_to_every_rack_unit_and_three_screws_to_a_length():
    rear = decor(device("ar7721"), "rear")
    bars = sorted(d["at"][1] for d in with_prefix(rear, "bar-"))
    assert len(bars) == 40 and len(with_prefix(rear, "lip-")) == 40
    assert all(close(b - a, RU) for a, b in zip(bars, bars[1:]))
    assert len(with_prefix(rear, "screw-")) == 6
    lips = with_prefix(rear, "lip-")
    assert all(d["size"][1] >= 30.0 for d in lips), "the lips are about 36 mm tall, as the photograph shows"
    first = next(d for d in rear if d["id"] == "screw-1-1")
    assert 125.0 <= first["at"][1] + first["size"][1] / 2 <= 140.0, "screw 1 lies about 133 mm from the plate top"


def test_the_ar7721_left_shows_the_40_crossbar_ends_and_the_right_the_plate_edge():
    doc = device("ar7721")
    assert len(with_prefix(decor(doc, "left"), "end-lip-")) == 40
    assert len(with_prefix(decor(doc, "left"), "end-")) == 80
    right = decor(doc, "right")
    for piece in (1, 2):
        assert len(with_prefix(right, f"hook-window-{piece}-")) == 8
        assert len(with_prefix(right, f"hook-slot-{piece}-")) == 4
        assert len(with_prefix(right, f"tab-{piece}-")) == 2


def test_the_ar7502_envelope_is_the_data_sheets_with_the_depth_the_table_prints():
    doc = device("ar7502")
    c = doc["chassis"]
    assert doc["manufacturer"] == "APC" and doc["model"] == "AR7502"
    assert close(c["width"], 117.0) and close(c["height"], 1930.0, 0.5) and close(c["depth"], 13.0)
    assert c["mount"] == "rack-side" and c["ru"] == 43 and close(c["weight-kg"], 2.27, 0.0005)
    assert set(doc["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


def test_the_ar7502_front_draws_what_the_installation_sheets_figure_counts():
    front = decor(device("ar7502"), "front")
    counts = {p: len(with_prefix(front, p)) for p in ("win-", "keyhole-", "kstem-", "hook-", "leg-", "rect-", "edge-",
                                                      "ledge-", "tree-", "sq-")}
    assert counts["win-"] == 4, "four large mesh windows"
    assert counts["keyhole-"] == 12 and counts["kstem-"] == 12, "six pairs of keyholes, each a bulb with a stem"
    bulbs = with_prefix(front, "keyhole-")
    # A bulb reads 42 px across at 2.48 px/mm, which is 17 mm.
    assert all(d["size"][0] >= 15.0 for d in bulbs), "the keyhole bulbs are about 17 mm across, not 12"
    assert counts["hook-"] == 18, "three hook slots under each pair, each an inverted U with a head"
    assert counts["leg-"] == 24, "the middle hook of a trio has two legs, the outer two one each"
    assert counts["rect-"] == 8, "eight rectangular slots"
    assert counts["edge-"] == 43, "one short dash to a rack unit down the right edge"
    assert counts["ledge-"] == 86, "a square and a long dash to a rack unit down the left edge"
    assert counts["tree-"] == 15, "three hanger marks of five parts"
    assert counts["sq-"] == 50, "the small square holes round the slots, windows and keyholes"


def test_the_ar7502_has_no_connector_and_states_no_capacity():
    doc = device("ar7502")
    assert not doc.get("ports") and "capacity" in doc["provenance"]
    assert any(g["what"] == "cable-capacity" for g in doc["gaps"])

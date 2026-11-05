"""The Cisco ASR 9000 grounding pad is a pair of screws one two-hole lug lands across.

The pad is placed on ten chassis. It presents the registered `stud-pair-5-8` interface at the midpoint of two 10-32 screws, on the
5/8 in. pitch, which is the lower end of the range the guides print; the contract says that the pitch is declared and not
measured, and what would settle it.
"""
import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
PAD = "cisco/a9k-ground-pad@1"
SCREW = "common/ground-screw-10-32@1"
LUG = "generic/two-hole-lug-5-8@1"
IFACE = "stud-pair-5-8"


def contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def flat(text):
    return " ".join(str(text).split())


def devices_placing_the_pad():
    return sorted(p.parent for p in (LIB / "devices" / "cisco").glob("*/device.yaml") if PAD in p.read_text())


def test_the_pad_presents_the_five_eighths_pair_and_a_lug_mates_it():
    c = contract(PAD)
    assert c["interface"] == IFACE and c["class"] == "ground" and c["behaviour"] == "mounts"
    lug = contract(LUG)
    assert lug["mates"] == IFACE
    registry = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())
    assert registry["interfaces"][IFACE]["standard"] == "two-hole-lug-5-8"


def test_the_pad_composes_two_screws_on_the_pitch_of_the_key():
    c = contract(PAD)
    parts = c["parts"]
    assert [(p["ref"], p["id"]) for p in parts] == [(SCREW, "1"), (SCREW, "2")]
    (x1, y1), (x2, y2) = parts[0]["at"], parts[1]["at"]
    assert round(x2 - x1, 4) == 15.875 and y1 == y2
    assert contract(SCREW)["interface"] == "terminal-stud"


def test_the_pad_presents_at_the_midpoint_of_the_screws_at_the_top_of_their_heads():
    c = contract(PAD)
    screw = contract(SCREW)
    sx, sy = screw["connection-points"]["mate"]["at"]
    (x1, y1), (x2, y2) = (p["at"] for p in c["parts"])
    mate = c["connection-points"]["mate"]
    assert mate["at"] == [round((x1 + x2) / 2 + sx, 4), round(y1 + sy, 4)]
    assert mate["direction"] == "front"
    (head,) = [f for f in screw["relief"]["features"] if f["node"] == "head"]
    assert mate["seat-out"] == head["cyl"]


def test_the_pad_keeps_the_box_every_chassis_cuts_for_it_and_the_screws_stay_on_the_lug():
    c = contract(PAD)
    assert c["size"] == {"w": 46.0, "h": 20.0}
    side = contract(SCREW)["size"]["w"]
    for p in c["parts"]:
        x, y = p["at"]
        assert 0 <= x and x + side <= c["size"]["w"] and 0 <= y and y + side <= c["size"]["h"]


def test_the_contract_says_the_pitch_is_declared_from_a_range_and_what_would_settle_it():
    text = flat(contract(PAD)["provenance"]["hole-pitch"])
    assert "DECLARED, NOT MEASURED" in text and "0.625- to 0.75-inch" in text
    assert "stud-pair-3-4" in text and "WHAT WOULD SETTLE IT" in text
    assert "BORROWED AND WEAKER" not in text


def test_the_pad_is_still_the_one_part_each_chassis_places():
    placing = devices_placing_the_pad()
    assert placing
    for d in placing:
        lock = json.loads((d / "device.lock.json").read_text())
        assert lock["composed-refs"][PAD].split("+")[0] == contract(PAD)["version"]


def test_no_record_excepts_the_pad_any_more():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    assert doc["cap"] == len(doc["rows"])
    assert not [r for r in doc["rows"] if r["part"] == PAD]

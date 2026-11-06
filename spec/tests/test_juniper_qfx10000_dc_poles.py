"""The DC input lugs of the Juniper QFX10000-PWR-DC supply are places a two-hole lug lands, and the supply states its two inputs.

The supply used to draw its four lug barrels as art, so it offered no place for a DC feed. Each of its four poles is now a pair of
studs on the 5/8 in. centres the hardware guides print for the lug, composed from the library's pair part, and the contract's `dc`
block states two input ports of two poles each:

  - the four poles are `juniper/mx240-dc-pole@1`, which presents `stud-pair-5-8`, the interface `generic/two-hole-lug-5-8@1` mates;
  - each input is a port of an `rtn` pole and a `batt` pole, with the voltage and current Table 24 prints and no wire size, because
    the guides print two;
  - the contract's `provenance` carries the entries its `source` names and says that the pair is a declared stand-in;
  - the supply's records row is gone.

These run against the real library and the records file. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "juniper/qfx10000-pwr-dc@1"
PAIR = "juniper/mx240-dc-pole@1"
LUG = "generic/two-hole-lug-5-8@1"
POLES = ["pole-1-rtn", "pole-1-batt", "pole-2-rtn", "pole-2-batt"]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


def test_the_supply_composes_four_pairs_and_nothing_else():
    parts = contract(SUPPLY)["parts"]
    assert [p["id"] for p in parts] == POLES
    assert {p["ref"] for p in parts} == {PAIR}


def test_the_pair_presents_the_interface_the_lug_mates():
    assert contract(PAIR)["interface"] == "stud-pair-5-8"
    assert contract(LUG)["mates"] == "stud-pair-5-8"


def test_each_pair_stands_inside_the_face_and_clear_of_the_next():
    c = contract(SUPPLY)
    w, h = contract(PAIR)["size"]["w"], contract(PAIR)["size"]["h"]
    boxes = sorted((p["at"][1], p["at"][0]) for p in c["parts"])
    for (y0, x0), (y1, x1) in zip(boxes, boxes[1:]):
        assert y0 + h <= y1, "two pairs overlap"
    for y, x in boxes:
        assert 0 <= x and x + w <= c["size"]["w"] and 0 <= y and y + h <= c["size"]["h"]


def test_each_input_is_a_port_of_two_poles_with_the_figures_the_table_prints():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input-1", "input-2"]
    for n, port in enumerate(ports, 1):
        assert port["direction"] == "input"
        assert [(q["role"], q["slot"]) for q in port["poles"]] == [("rtn", f"pole-{n}-rtn"), ("batt", f"pole-{n}-batt")]
        assert port["voltage"] == {"nominal": -48, "range": [-40, -72]}
        assert port["rating-a"] == 60
        assert "awg" not in port


def test_every_pole_is_a_pole_of_exactly_one_port():
    slots = [q["slot"] for port in contract(SUPPLY)["dc"]["ports"] for q in port["poles"]]
    assert sorted(slots) == sorted(POLES)


def test_the_provenance_has_the_entries_the_port_names_and_declares_the_stand_in():
    c = contract(SUPPLY)
    for port in c["dc"]["ports"]:
        for key in port["source"].values():
            assert key in c["provenance"], key
    assert "awg" in c["provenance"] and "NOT STATED" in c["provenance"]["awg"]
    assert "DECLARED STAND-IN" in c["provenance"]["seats"]
    assert "5/8 in" in words(c["provenance"]["seats"])


def test_the_supply_keeps_its_drawing_ids_and_attributes():
    c = contract(SUPPLY)
    assert sorted(c["elements"]) == ["handle", "led-fault", "led-inp1", "led-inp2", "led-pwr-ok"]
    assert c["attrs"]["inlet"] == "dc-terminal" and c["attrs"]["power-output-w"] == 2500


def test_the_supply_has_no_row_in_the_records_file():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY] == []

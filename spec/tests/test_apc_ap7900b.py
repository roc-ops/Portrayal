"""The APC NetShelter AP7900B switched 1U rack PDU, and the one part it needed.

It carries eight NEMA 5-15R outlets in a row on one face, with a fixed input cord leaving the left end of that face and,
at the right end, a display, a round button and two jacks; the other face is plain. What is true of the library once it
is in:

  - it is a device of the maker, with the width, height, depth and weight the data sheet gives, and six views;
  - the outlet face carries eight numbered 5-15R outlets, the input cord and every part the data sheet photograph shows;
  - the outlets are named as the unit prints them and the unit states switching;
  - every position read off a photograph is declared an estimate;
  - the new cord part says where each figure came from and is a part of the maker.

These read the contracts and the device source. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

VIEWS = ["front", "rear", "top", "bottom", "left", "right"]
ALLOWED = {"drawing", "datasheet", "photo-measured", "measured", "estimated", "borrowed", "registry"}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def dev():
    return yaml.safe_load((LIB / "devices" / "apc" / "ap7900b" / "device.yaml").read_text())


def placements(dev, view):
    comps = dev["views"][view].get("components") or {}
    return {p["id"]: p for p in (comps.get("placements") or [])}


def test_it_is_a_device_of_the_maker_the_size_the_data_sheet_gives(dev):
    assert (dev["manufacturer"], dev["model"]) == ("APC", "AP7900B")
    c = dev["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (445, 44, 108, 1)
    assert c["weight-kg"] == 2.27


def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched(dev):
    assert sorted(dev["views"]) == sorted(VIEWS)
    for name, v in dev["views"].items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{name}: neither drawn nor an `empty:` sentence"


def test_eight_5_15r_outlets_and_the_fixed_cord_stand_on_the_outlet_face(dev):
    rear = placements(dev, "rear")
    outlets = {i: p for i, p in rear.items() if i.startswith("outlet-")}
    assert sorted(outlets) == [f"outlet-{n}" for n in range(1, 9)]
    assert {p["ref"] for p in outlets.values()} == {"std/nema-5-15r@1"}
    assert rear["input"]["ref"] == "apc/pdu-cord-5-15p@1"


def test_the_right_end_of_the_outlet_face_carries_what_the_photograph_shows(dev):
    refs = {i: p["ref"] for i, p in placements(dev, "rear").items()}
    assert refs["display"] == "apc/ap78-display@1"
    assert refs["button"] == "apc/ap78-button@1"
    assert {refs["jack-1"], refs["jack-2"]} == {"std/rj45@2"}


def test_the_outlets_are_named_as_the_unit_prints_them(dev):
    rules = {r["physical"]: r for r in dev["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}"
    assert rules["outlet-{n}"]["range"] == "1-8"
    marks = sorted(dev["views"]["rear"]["silkscreen"], key=lambda s: s["at"][0])
    numerals = [m for m in marks if m.get("for", "").startswith("outlet-")]
    assert [m["text"] for m in numerals] == [str(n) for n in range(1, 9)]
    for m in numerals:
        assert m["for"] == f"outlet-{m['text']}"


def test_switching_and_input_metering_are_stated(dev):
    mgmt = dev["attrs"]["management"]
    assert mgmt["outlet-switching"] is True
    assert mgmt["metering-scope"] == "input"


def test_every_position_read_off_a_photograph_is_declared_an_estimate(dev):
    for key in ("front", "rear"):
        assert dev["provenance"][key]["confidence"] == "estimated", key
        assert "photograph" in dev["provenance"][key]["note"]


def test_the_new_cord_part_says_where_each_figure_came_from_and_which_are_estimates():
    c = contract("apc/pdu-cord-5-15p@1")
    assert "size" in c["provenance"]
    conf = c.get("size-confidence") or {}
    assert conf and set(conf.values()) <= ALLOWED
    assert c["attrs"]["plug"] == "nema-5-15p"
    assert (LIB / "components" / "apc" / "pdu-cord-5-15p" / "v1" / "skins" / "default.svg").is_file()

"""The CyberPower PDU30BHVT8R and PDU81001G rack PDUs, and the parts they needed that the library did not hold.

The PDU30BHVT8R is a 1U basic PDU with six IEC outlets and two C19 outlets on the rear, a breaker for each bank, an external
site ground and a fixed cord with a NEMA L6-30P plug. The PDU81001G is a 1U switched, metered-by-outlet PDU with eight NEMA
5-15R outlets on the front, a graphic display, two USB jacks, two Ethernet jacks, an environment jack and a serial/link jack.
What is true of the library once they are in:

  - each is a device of the maker, the size its data sheet gives, with six views;
  - each outlet is a part that presents the interface its plug mates, and the strips' outlets are numbered as printed;
  - every connector the maker's pictures show is a part, and the input cord is a part that states its plug;
  - a figure no document gives is declared an estimate in the contract that carries it;
  - the maker is registered.

These read the contracts and the device sources. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec" / "schemas"

SKUS = {
    "pdu30bhvt8r": dict(model="PDU30BHVT8R", size=(445, 44, 38)),
    "pdu81001g": dict(model="PDU81001G", size=(433, 44, 112)),
}
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]
NEW_PARTS = [
    "cyberpower/pdu-bank-led@1",
    "cyberpower/pdu-cord-l6-30p@1",
    "cyberpower/pdu-cord-5-15p@1",
    "cyberpower/pdu-lcd@1",
    "cyberpower/pdu-joystick@1",
]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(sku):
    return yaml.safe_load((LIB / "devices" / "cyberpower" / sku / "device.yaml").read_text())


def placements(sku, view):
    comps = (device(sku)["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_sku_is_a_device_of_the_maker_the_size_the_data_sheet_gives(sku):
    d = device(sku)
    assert (d["manufacturer"], d["model"]) == ("CyberPower", SKUS[sku]["model"])
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == SKUS[sku]["size"]
    assert c["ru"] == 1


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched(sku):
    views = device(sku)["views"]
    assert sorted(views) == sorted(VIEWS)
    for name, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{sku} {name}: neither drawn nor an `empty:` sentence"


def test_the_basic_pdu_has_six_c13_and_two_c19_outlets_two_breakers_and_a_ground_on_the_rear():
    rear = placements("pdu30bhvt8r", "rear")
    refs = [p["ref"] for i, p in rear.items() if i.startswith("outlet-")]
    assert sorted(refs) == ["std/c13-outlet@1"] * 6 + ["std/c19-outlet@1"] * 2
    assert sorted(i for i, p in rear.items() if p["ref"] == "common/breaker-push-reset@1") == ["breaker-1", "breaker-2"]
    assert rear["ground"]["ref"] == "common/ground-screw@1"
    assert rear["input"]["ref"] == "cyberpower/pdu-cord-l6-30p@1"


def test_the_basic_pdu_front_carries_its_two_bank_lamps_and_no_outlet():
    front = placements("pdu30bhvt8r", "front")
    assert sorted(front) == ["led-bank-1", "led-bank-2"]
    assert {p["ref"] for p in front.values()} == {"cyberpower/pdu-bank-led@1"}


def test_the_switched_pdu_has_eight_5_15r_outlets_each_with_a_lamp_on_the_front():
    front = placements("pdu81001g", "front")
    outlets = {i: p for i, p in front.items() if i.startswith("outlet-")}
    assert sorted(outlets, key=lambda i: int(i.split("-")[1])) == [f"outlet-{n}" for n in range(1, 9)]
    assert {p["ref"] for p in outlets.values()} == {"std/nema-5-15r@1"}
    lamps = {p["for"] for p in front.values() if p["ref"] == "common/led-dot@1"}
    assert lamps == set(outlets)
    assert front["input"]["ref"] == "cyberpower/pdu-cord-5-15p@1"


def test_the_switched_pdu_front_carries_every_port_the_photograph_shows():
    front = placements("pdu81001g", "front")
    refs = {i: p["ref"] for i, p in front.items()}
    assert refs["display"] == "cyberpower/pdu-lcd@1"
    assert refs["joystick"] == "cyberpower/pdu-joystick@1"
    assert {refs[i] for i in ("eth-1", "eth-2")} == {"common/rj45-eth@1"}
    assert {refs[i] for i in ("env", "serial-link")} == {"std/rj45@2"}
    assert sorted(i for i, r in refs.items() if r == "common/usb-a-bezel@1") == ["usb-1", "usb-2"]


def test_the_switched_pdu_rear_is_declared_unshown_and_not_drawn():
    rear = device("pdu81001g")["views"]["rear"]
    assert not (rear.get("components") or {}).get("placements")
    assert "empty" in rear


def test_the_switched_pdu_outlets_are_named_as_the_unit_prints_them_and_the_basic_pdu_names_none():
    rules = {r["physical"]: r for r in device("pdu81001g")["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}"
    assert rules["outlet-{n}"]["range"] == "1-8"
    assert "interfaces" not in device("pdu30bhvt8r")


@pytest.mark.parametrize("ref", NEW_PARTS)
def test_a_new_part_says_where_each_figure_came_from_and_which_are_estimates(ref):
    c = contract(ref)
    assert "size" in c["provenance"]
    conf = c.get("size-confidence") or {}
    assert conf, f"{ref}: no size-confidence"
    assert {v for v in conf.values()} <= {"drawing", "datasheet", "photo-measured", "measured", "estimated", "borrowed", "registry"}


@pytest.mark.parametrize("ref,plug", [("cyberpower/pdu-cord-l6-30p@1", "nema-l6-30p"), ("cyberpower/pdu-cord-5-15p@1", "nema-5-15p")])
def test_a_cord_part_states_the_plug_on_its_far_end(ref, plug):
    c = contract(ref)
    assert c["class"] == "inlet"
    assert c["attrs"]["plug"] == plug


def test_the_5_15r_outlet_is_no_longer_said_to_be_unplaced():
    assert "unplaced" not in contract("std/nema-5-15r@1")


def test_the_maker_is_registered():
    vendors = yaml.safe_load((SCHEMAS / "vendors.yaml").read_text())
    assert vendors["vendors"]["cyberpower"]["display"] == "CyberPower"

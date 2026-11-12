"""The CyberPower PDU15M2F12R metered PDU and PDU41021 switched PDU.

The PDU15M2F12R is a 1U metered PDU with a breaker button, a two-digit amp meter and two NEMA 5-15R outlets on the front and twelve more on
the rear, an external site ground and a fixed cord with a NEMA 5-15P plug. The PDU41021 is a 1U switched PDU with eight NEMA 5-15R outlets,
each with a lamp, and a control panel on the front; eight more outlets are on its rear, which no document shows. What is true of the library
once they are in:

  - each is a device of the maker, the size its data sheet gives, with six views, and a face no document shows says what was searched;
  - each outlet is the library's 5-15R face, and the outlets the unit prints no number for are numbered here from the left;
  - a position read off an angled photograph, or placed where no document puts it, is declared an estimate in the device that carries it;
  - the input cord states its plug, and the DCIM files the exporter wrote carry the plug and every outlet the drawing places.

These read the device sources and the DCIM files the exporter wrote. They render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SKUS = {
    "pdu15m2f12r": dict(model="PDU15M2F12R", size=(445, 44, 57), outlets=14,
                        sha="4bd61f67a7b78186bcc121f1208d6dd3bbf207d9632d5d4e62b9b754927b40ee"),
    "pdu41021": dict(model="PDU41021", size=(433, 44, 215), outlets=8,
                     sha="c924d25bb797135feccf35ee859e62b7bb37062319eb5903311d6e2111da4cf2"),
}
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]


def device(sku):
    return yaml.safe_load((LIB / "devices" / "cyberpower" / sku / "device.yaml").read_text())


def placements(sku, view):
    comps = (device(sku)["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_sku_is_a_device_of_the_maker_the_size_its_data_sheet_gives(sku):
    d = device(sku)
    assert (d["manufacturer"], d["model"]) == ("CyberPower", SKUS[sku]["model"])
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == SKUS[sku]["size"]
    assert c["ru"] == 1
    assert d["datasheet"]["sha256"] == SKUS[sku]["sha"]


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched(sku):
    views = device(sku)["views"]
    assert sorted(views) == sorted(VIEWS)
    for name, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{sku} {name}: neither drawn nor an `empty:` sentence"
        if not drawn:
            assert "Searched" in v["empty"], f"{sku} {name}: an empty face names what was searched"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_a_position_read_off_an_angled_photograph_is_declared_an_estimate(sku):
    d = device(sku)
    assert d["provenance"]["method"]["confidence"] == "estimated"
    assert "NOT orthographic" in d["provenance"]["method"]["note"]
    gaps = {g["what"] for g in d["gaps"]}
    assert "front-angled-photograph" in gaps


def test_the_metered_pdu_has_two_front_outlets_a_breaker_and_a_meter_and_twelve_rear_outlets():
    front, rear = placements("pdu15m2f12r", "front"), placements("pdu15m2f12r", "rear")
    assert sorted(i for i in front if i.startswith("outlet-")) == ["outlet-1", "outlet-2"]
    assert sorted((i for i in rear if i.startswith("outlet-")), key=lambda i: int(i.split("-")[1])) == [f"outlet-{n}" for n in range(3, 15)]
    assert {p["ref"] for i, p in {**front, **rear}.items() if i.startswith("outlet-")} == {"std/nema-5-15r@1"}
    assert front["breaker"]["ref"] == "common/breaker-push-reset@1"
    assert front["breaker"]["attrs"]["rating-a"] == 15
    assert front["meter"]["ref"] == "common/seven-segment-dual@1"


def test_the_metered_pdu_rear_carries_the_ground_and_the_fixed_cord_the_data_sheet_states():
    rear = placements("pdu15m2f12r", "rear")
    assert rear["ground"]["ref"] == "common/ground-screw@1"
    assert rear["input"]["ref"] == "cyberpower/pdu-cord-5-15p@1"
    assert rear["input"]["attrs"]["cord-length-ft"] == 15


def test_the_metered_pdu_says_its_twelve_rear_outlets_are_placed_by_estimate():
    d = device("pdu15m2f12r")
    assert d["provenance"]["rear"]["confidence"] == "estimated"
    gap = next(g for g in d["gaps"] if g["what"] == "rear-outlet-layout")
    assert gap["scope"] == ["rear"]
    assert "twelve" in gap["note"]


def test_the_metered_pdu_is_not_switched_and_meters_the_input():
    m = device("pdu15m2f12r")["attrs"]["management"]
    assert (m["metering-scope"], m["outlet-switching"]) == ("input", False)


def test_the_switched_pdu_has_eight_5_15r_outlets_each_with_a_lamp_on_the_front():
    front = placements("pdu41021", "front")
    outlets = {i: p for i, p in front.items() if i.startswith("outlet-")}
    assert sorted(outlets, key=lambda i: int(i.split("-")[1])) == [f"outlet-{n}" for n in range(1, 9)]
    assert {p["ref"] for p in outlets.values()} == {"std/nema-5-15r@1"}
    assert all(p["states"] == ["on", "off"] for p in outlets.values())
    lamps = {p["for"] for p in front.values() if p["ref"] == "common/led-dot@1" and p["for"].startswith("outlet-")}
    assert lamps == set(outlets)
    assert front["input"]["ref"] == "cyberpower/pdu-cord-5-15p@1"


def test_the_switched_pdu_front_carries_every_port_the_photograph_shows():
    front = placements("pdu41021", "front")
    refs = {i: p["ref"] for i, p in front.items()}
    assert refs["display"] == "cyberpower/pdu-lcd@1"
    assert {refs[i] for i in ("select", "enter")} == {"cyberpower/pdu-joystick@1"}
    assert refs["eth"] == "common/rj45-eth@1"
    assert {refs[i] for i in ("in-env", "out", "serial")} == {"std/rj45@2"}
    assert refs["usb"] == "common/usb-a-bezel@1"


def test_the_switched_pdu_says_its_port_labels_come_from_a_photograph_and_its_rear_is_not_shown():
    d = device("pdu41021")
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["port-labels"]["reason"] == "vendor-silent"
    assert "photograph" in gaps["port-labels"]["note"]
    assert gaps["rear"]["scope"] == ["rear"]
    assert not placements("pdu41021", "rear")
    m = d["attrs"]["management"]
    assert (m["metering-scope"], m["outlet-switching"]) == ("input", True)


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_outlets_are_numbered_as_the_interface_rule_says(sku):
    rules = {r["physical"]: r for r in device(sku)["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}"
    assert rules["outlet-{n}"]["range"] == f"1-{SKUS[sku]['outlets']}"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_exporter_writes_the_input_plug_and_every_outlet_the_drawing_places(sku):
    """The DCIM file the exporter wrote from the built library, not the source, carries the cord's plug and the outlets."""
    exported = yaml.safe_load(
        (LIB / "exports" / "netbox" / "device-types" / "CyberPower" / f"{SKUS[sku]['model']}.yaml").read_text())
    assert [p["type"] for p in exported["power-ports"]] == ["nema-5-15p"]
    assert len(exported["power-outlets"]) == SKUS[sku]["outlets"]
    assert {o["power_port"] for o in exported["power-outlets"]} == {"input"}

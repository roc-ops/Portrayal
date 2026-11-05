"""The MX960 AC supply states why no cord lands on it.

The hardware guide puts each normal-capacity supply's AC inlet in the chassis,
directly above the supply. The MX960 draws those four C20 inlets itself, in an
`inlets` group, so the supply keeps no inlet of its own (a second one would be
counted twice in the DCIM export). The port checks read a part that is only
the supply of a feed landing elsewhere from its `unmated` sentence.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SUPPLY = LIB / "components/juniper/mx960-psu-ac/v1/contract.yaml"
DEVICE = LIB / "devices/juniper/mx960/device.yaml"
RECORDS = LIB / "conformance-exceptions.yaml"


def _supply():
    return yaml.safe_load(SUPPLY.read_text())


def test_the_supply_says_its_inlet_is_on_the_chassis():
    sentence = _supply().get("unmated")
    assert isinstance(sentence, str) and len(sentence) >= 40
    assert "chassis" in sentence


def test_the_supply_still_keeps_no_inlet_and_composes_no_part():
    contract = _supply()
    assert contract["attrs"]["inlet"] == "none"
    assert "parts" not in contract


def test_the_device_still_places_four_chassis_inlets():
    device = yaml.safe_load(DEVICE.read_text())
    placements = device["views"]["rear"]["components"]["placements"]
    inlets = [p for p in placements if p["ref"] == "std/c20-inlet@1"]
    assert len(inlets) == 4
    assert {p["group"] for p in inlets} == {"inlets"}


def test_no_record_is_held_for_the_supply():
    rows = yaml.safe_load(RECORDS.read_text())["rows"]
    held = [r for r in rows if r["part"] == "juniper/mx960-psu-ac@1" and r["code"] == "C19"]
    assert held == []

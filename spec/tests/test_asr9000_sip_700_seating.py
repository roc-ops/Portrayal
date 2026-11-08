"""The ASR 9000 SIP-700 and SIP-700-8G, and the chassis line card slots that take them.

Cisco's SIP and SPA Hardware Installation Guide, "Supported Platforms", says the SIP-700 is supported on
all Cisco ASR 9000 Series Routers, and the SIP-700 data sheet's Chassis compatibility row reads "All Cisco
ASR 9000 Series chassis". The ASR 9000 Overview and Reference Guide excepts the ASR 9906 in a note, so the
9906's line card slots do not take it. The guide's installing section says a SIP slides into any
available line card slot, so every line card slot of a chassis that takes it names both parts, and no
other bay does.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
DEVICES = LIBRARY / "devices/cisco"
COMPONENTS = LIBRARY / "components/cisco"

SIP, SIP_8G = "cisco/a9k-sip-700@2", "cisco/a9k-sip-700-8g@2"
SIPS = (SIP, SIP_8G)
# every modular chassis the held rows name: the guide's "all Cisco ASR 9000 Series Routers" less the 9906
CHASSIS = ["9006", "9010", "9904", "9910", "9912", "9922"]
EVERY_MODULAR = CHASSIS + ["9906"]


def contract(ref):
    name, major = ref.split("/")[1].split("@")
    return yaml.safe_load((COMPONENTS / name / f"v{major}/contract.yaml").read_text())


def device(chassis):
    return yaml.safe_load((DEVICES / f"asr-{chassis}/device.yaml").read_text())


def bays(chassis):
    return device(chassis)["views"]["front"]["components"]["bays"]


def line_card_bays(chassis):
    """The bays that take a line card: any bay that accepts a component whose class is line-card."""
    return [b for b in bays(chassis) if any(contract(r)["class"] == "line-card" for r in b["accepts"])]


@pytest.fixture(params=CHASSIS)
def chassis(request):
    return request.param


def test_every_line_card_slot_of_each_chassis_that_takes_a_sip_names_both(chassis):
    slots = line_card_bays(chassis)
    assert slots
    for b in slots:
        for ref in SIPS:
            assert ref in b["accepts"], (chassis, b["id"], ref)


def test_no_bay_that_is_not_a_line_card_slot_names_a_sip():
    for c in EVERY_MODULAR:
        lc = {b["id"] for b in line_card_bays(c)}
        for b in bays(c):
            if b["id"] not in lc:
                assert not set(SIPS) & set(b["accepts"]), (c, b["id"])


def test_a_sip_is_a_card_every_slot_that_names_it_is_sized_for():
    size = contract(SIP)["size"]
    assert contract(SIP_8G)["size"] == size
    for c in EVERY_MODULAR:
        for b in bays(c):
            if SIP in b["accepts"]:
                # the 9006 and 9904 lay their cards flat and rotate the bay, which swaps w and h
                assert sorted(b["size"].values()) == sorted([size["w"], size["h"]]), (c, b["id"])


def test_the_two_sips_sit_in_the_same_bays_in_every_chassis():
    for c in EVERY_MODULAR:
        assert [b["id"] for b in bays(c) if SIP in b["accepts"]] == [b["id"] for b in bays(c) if SIP_8G in b["accepts"]]


def test_a_sip_is_named_once_in_a_bay(chassis):
    for b in bays(chassis):
        for ref in SIPS:
            assert b["accepts"].count(ref) <= 1, (chassis, b["id"], ref)


@pytest.mark.parametrize("chassis", [c for c in CHASSIS if c != "9010"])
def test_each_chassis_that_gained_the_sips_says_where_the_rows_come_from(chassis):
    entry = device(chassis)["provenance"]["sip-700-seating"]
    assert entry["confidence"] == "datasheet"
    note = entry["note"]
    assert "Supported Platforms" in note and "c78-573452" in note and "9906" in note


@pytest.mark.heavy
def test_each_chassis_is_locked(chassis):
    mine = [f for f in devicelock.check(LIBRARY) if f[0] == f"cisco/asr-{chassis}"]
    assert mine == []

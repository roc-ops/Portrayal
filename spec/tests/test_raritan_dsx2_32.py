"""The Raritan Dominion SX II DSX2-32: the 32-port serial console server with dual AC power.

Sources: the Dominion SX II data sheet (V1209R3) for the model table and the labelled rear photograph, the User Guide
v2.6.0 Appendix A for the dimensions, the power figure and the port pins, the Quick Setup Guide v2.6.0 for the rackmount
kit, and the maker's front photograph of a DSX2-32M-DC. No drawing is held, so every position is an estimate and the
tests hold the counts, the ids, the roles and the declarations, not a coordinate.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices/raritan/dsx2-32"
PITCH = 13.97


@pytest.fixture(scope="module")
def dev():
    return yaml.safe_load((DEVICE / "device.yaml").read_text())


def placements(d, view):
    return {p["id"]: p for p in d["views"][view]["components"].get("placements", [])}


def test_the_device_is_the_part_number_the_data_sheet_orders(dev):
    assert dev["name"] == "dsx2-32"
    assert dev["manufacturer"] == "Raritan"
    assert dev["model"] == "DSX2-32"
    assert list(dev["configurations"]["base"]["part-numbers"]) == ["DSX2-32"]


def test_the_body_is_the_guides_440_by_334_by_44_millimetres_and_it_says_the_figure_is_the_familys(dev):
    chassis = dev["chassis"]
    assert (chassis["width"], chassis["depth"], chassis["height"], chassis["ru"]) == (440, 334, 44, 1)
    family = [g for g in dev["gaps"] if g["what"] == "family-size"]
    assert family and family[0]["reason"] == "vendor-silent"


def test_the_rear_carries_one_numbered_serial_port_for_each_of_the_32_ports(dev):
    rear = placements(dev, "rear")
    serial = {i: p for i, p in rear.items() if p.get("group", "").startswith("serial-")}
    assert set(serial) == {f"serial-{n}" for n in range(1, 33)}
    assert sorted(p["rel-pos"] for p in serial.values()) == list(range(1, 33))
    for name, g in dev["groups"].items():
        if name.startswith("serial-"):
            assert g["attrs"] == {"media": "rj45-serial", "role": "console-server"}
    assert not [p for p in placements(dev, "front").values() if p.get("group", "").startswith("serial-")]


def test_the_serial_ports_are_numbered_along_the_lower_row_and_then_the_upper_row_of_each_bank(dev):
    rear = placements(dev, "rear")
    for first in (1, 17):
        lower = [rear[f"serial-{first + c}"]["at"] for c in range(8)]
        upper = [rear[f"serial-{first + 8 + c}"]["at"] for c in range(8)]
        assert [round(b[0] - a[0], 2) for a, b in zip(lower, lower[1:])] == [PITCH] * 7
        assert [p[0] for p in lower] == [p[0] for p in upper]
        assert max(p[1] for p in upper) < min(p[1] for p in lower)
    # the latch of the upper row is at the top, as the photograph shows
    assert all(rear[f"serial-{n}"].get("rotate") == 180 for n in list(range(9, 17)) + list(range(25, 33)))
    assert not any(rear[f"serial-{n}"].get("rotate") for n in list(range(1, 9)) + list(range(17, 25)))


def test_the_rear_carries_the_terminal_jack_the_admin_usb_jack_three_usb_ports_and_two_lan_jacks(dev):
    rear = placements(dev, "rear")
    console = rear["console"]
    assert console["attrs"]["role"] == "console" and console["attrs"]["media"] == "rj45-serial"
    assert rear["admin-usb"]["ref"] == "std/mini-usb@1"
    assert rear["admin-usb"]["attrs"]["role"] == "console"
    assert {rear[f"usb-rear-{n}"]["ref"] for n in (1, 2, 3)} == {"std/usb-a@1"}
    assert not [i for i in rear if i.startswith("usb-rear-") and i not in {"usb-rear-1", "usb-rear-2", "usb-rear-3"}]
    assert rear["lan-1"]["ref"] == rear["lan-2"]["ref"] == "common/rj45-eth@1"


def test_the_rear_carries_two_ac_inlets_each_under_a_switch(dev):
    rear = placements(dev, "rear")
    assert {rear["inlet-1"]["ref"], rear["inlet-2"]["ref"]} == {"std/c14-inlet@1"}
    assert rear["power-switch-1"]["for"] == "inlet-1" and rear["power-switch-2"]["for"] == "inlet-2"
    assert dev["chassis"]["power"] == "ac"
    assert dev["attrs"]["power"]["power-max-w"] == 23


def test_the_front_power_lamp_is_a_stated_gap_and_no_modem_jack_is_drawn(dev):
    gaps = {g["what"] for g in dev["gaps"]}
    assert {"power-lamp", "front-other-sku", "rack-kit"} <= gaps
    assert not [p for p in placements(dev, "rear").values() if "rj11" in p["ref"]]


def test_the_front_carries_one_usb_port_and_32_numbered_port_lamps(dev):
    front = placements(dev, "front")
    assert front["usb-front"]["ref"] == "std/usb-a@1"
    leds = {i: p for i, p in front.items() if p.get("group") == "port-leds"}
    assert sorted(p["rel-pos"] for p in leds.values()) == list(range(1, 33))


def test_every_source_is_listed_with_its_hash(dev):
    assert len(dev["references"]) == 5
    assert all(len(r["sha256"]) == 64 for r in dev["references"])

"""The Eaton Tripp Lite series B097-016, a 16-port serial console server, 1U.

Modelled from the maker's product specification page, the B097 quick start guide (93-386F rev B) and the
owner's manual for the B093, B097 and B098 console servers (rev C). The specification page carries only
small photographs of the two faces, so every position on them is estimated; the size, the ports and the
pinout are the manual's.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/eaton/b097-016/device.yaml"
EXPORTS = ROOT / "library/exports"

CISCO_STRAIGHT = ["CTS", "DSR", "RXD", "GND", "GND", "TXD", "DTR", "RTS"]


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def of(d, view, part):
    return [p for p in placements(d, view) if p["ref"].split("@")[0] == part]


def test_the_envelope_is_the_manuals(device):
    c = device["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (440, 44.45, 175.3, 1)
    assert device["views"]["front"]["size"] == {"w": 440, "h": 44.45}
    assert device["views"]["top"]["size"] == {"w": 440, "h": 175.3}
    assert device["views"]["left"]["size"] == {"w": 175.3, "h": 44.45}


def test_no_weight_is_stated_because_the_two_sources_differ(device):
    assert "weight-kg" not in device["chassis"]
    note = device["attrs"]["physical"]["weight-note"]
    assert "7.6 lb" in note and "9 lb" in note


def test_the_serial_bank_is_16_rj45_jacks_on_the_rear_in_two_rows(device):
    ports = [p for p in placements(device, "rear") if p.get("group") == "serial"]
    assert len(ports) == 16
    assert sorted(p["rel-pos"] for p in ports) == list(range(1, 17))
    assert {p["ref"].split("@")[0] for p in ports} == {"std/rj45-ganged"}
    assert len({p["at"][1] for p in ports}) == 2
    assert not [p for p in placements(device, "front") if p.get("group") == "serial"]


def test_the_serial_group_is_console_server_ports_with_the_printed_pinout(device):
    group = device["groups"]["serial"]["attrs"]
    assert group["media"] == "rj45-serial" and group["role"] == "console-server"
    pinout = device["attrs"]["features"]["serial-pinout"]
    assert "Cisco" in pinout
    for pin, signal in enumerate(CISCO_STRAIGHT, start=1):
        assert f"{pin} {signal}" in pinout


def test_the_rear_has_two_ethernet_jacks_and_two_c14_inlets(device):
    net = [p for p in placements(device, "rear") if p.get("group") == "net"]
    assert [p["rel-pos"] for p in net] == [1, 2]
    assert len(of(device, "rear", "std/c14-inlet")) == 2
    assert device["chassis"]["power"] == "ac"


def test_the_front_has_two_usb_ports_a_console_jack_and_four_lamps(device):
    usb = of(device, "front", "std/usb-a")
    assert len(usb) == 2 and all(p["skin"] == "usb2" for p in usb)
    console = [p for p in placements(device, "front") if p["id"] == "console"]
    assert len(console) == 1 and console[0]["attrs"]["role"] == "console"
    assert len(of(device, "front", "common/led-dot")) == 4


def test_every_position_is_estimated_and_the_ears_are_not_dimensioned(device):
    prov = device["provenance"]
    for key in ("front-layout", "rear-layout"):
        assert prov[key]["confidence"] == "estimated"
    assert device["chassis"]["ears"]["positions"][0]["default"] is True


def test_the_disagreements_between_the_sources_are_gaps(device):
    gaps = {g["what"] for g in device["gaps"]}
    assert {"size-sources", "weight-sources", "console-port-type", "usb-count"} <= gaps


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_exports_list_the_16_serial_lines_as_console_server_ports(device, target):
    doc = yaml.safe_load((EXPORTS / target / "device-types/Eaton/B097-016.yaml").read_text())
    ids = [p["id"] for p in placements(device, "rear") if p.get("group") == "serial"]
    assert [r["name"] for r in doc["console-server-ports"]] == ids
    assert {r["type"] for r in doc["console-server-ports"]} == {"rj-45"}
    assert doc["console-ports"] == [{"name": "Console", "type": "rj-45"}]
    assert [i["name"] for i in doc["interfaces"]] == ["NET1", "NET2"]
    assert {i["type"] for i in doc["interfaces"]} == {"1000base-t"}
    assert [p["type"] for p in doc["power-ports"]] == ["iec-60320-c14"] * 2

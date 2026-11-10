"""The Eaton Tripp Lite series B097-048, a 48-port serial console server, 1U.

Modelled from the maker's product specifications page, the B097 quick start guide (93-386F rev B), the
owner's manual for the B093, B097 and B098 console servers (rev C) and the maker's straight-on rear and
angled front photographs. No dimensioned drawing is held, so every position on the faces is read off a
photograph and is estimated; the size, the port counts, the inlet and the pinout are the documents'.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/eaton/b097-048/device.yaml"
ROCKER = ROOT / "library/components/eaton/b097-power-rocker/v1/contract.yaml"
EXPORTS = ROOT / "library/exports"

CISCO_STRAIGHT = ["CTS", "DSR", "RXD", "GND", "GND", "TXD", "DTR", "RTS"]


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def of(d, view, part):
    return [p for p in placements(d, view) if p["ref"].split("@")[0] == part]


def serial(d):
    return sorted((p for p in placements(d, "rear") if p.get("group") == "serial"),
                  key=lambda p: p["rel-pos"])


def test_the_envelope_is_the_manuals_44_by_17_by_4_5_cm(device):
    c = device["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (440, 44.45, 175.3, 1)
    for view, size in (("front", {"w": 440, "h": 44.45}), ("rear", {"w": 440, "h": 44.45}),
                       ("top", {"w": 440, "h": 175.3}), ("left", {"w": 175.3, "h": 44.45})):
        assert device["views"][view]["size"] == size


def test_the_page_and_the_manual_disagreeing_are_gaps_and_no_weight_is_stated(device):
    assert "weight-kg" not in device["chassis"]
    note = device["attrs"]["physical"]["weight-note"]
    assert "7.6 lb" in note and "9 lb" in note
    gaps = {g["what"]: g for g in device["gaps"]}
    for key in ("size-sources", "weight-sources", "usb-count"):
        assert gaps[key]["reason"] == "sources-disagree"
    size = gaps["size-sources"]["note"]
    assert "17.32 in" in size and "6.9 in" in size and "44 x 17 x 4.5 cm" in size


def test_the_rear_has_48_rj45_serial_jacks_in_two_rows_odd_numbers_on_top(device):
    ports = serial(device)
    assert [p["rel-pos"] for p in ports] == list(range(1, 49))
    assert {p["ref"].split("@")[0] for p in ports} == {"std/rj45-ganged"}
    assert len({p["at"][1] for p in ports}) == 2
    top = min(p["at"][1] for p in ports)
    assert {p["rel-pos"] % 2 for p in ports if p["at"][1] == top} == {1}
    for odd, even in zip(ports[0::2], ports[1::2]):
        assert odd["at"][0] == even["at"][0] and odd["at"][1] < even["at"][1]
    assert not [p for p in placements(device, "front") if p.get("group") == "serial"]


def test_the_jacks_stand_in_three_groups_of_eight_columns_with_one_gap_between_groups(device):
    columns = [p["at"][0] for p in serial(device)[0::2]]
    steps = [round(b - a, 2) for a, b in zip(columns, columns[1:])]
    assert len(columns) == 24
    in_group = {s for i, s in enumerate(steps) if (i + 1) % 8}
    between = {s for i, s in enumerate(steps) if not (i + 1) % 8}
    assert in_group == {13.97}
    assert len(between) == 1 and between.pop() > 13.97 + 1.0


def test_the_serial_jacks_are_numbered_on_the_panel_above_and_below_the_rows(device):
    marks = [s for s in device["views"]["rear"]["silkscreen"] if s.get("text", "").isdigit()]
    assert sorted(int(s["text"]) for s in marks) == list(range(1, 49))
    ports = serial(device)
    top = min(p["at"][1] for p in ports)
    bottom = max(p["at"][1] for p in ports)
    for s in marks:
        n = int(s["text"])
        if n % 2:
            assert s["at"][1] < top
        else:
            assert s["at"][1] > bottom


def test_the_serial_group_is_console_server_ports_with_the_printed_pinout(device):
    group = device["groups"]["serial"]["attrs"]
    assert group["media"] == "rj45-serial" and group["role"] == "console-server"
    pinout = device["attrs"]["features"]["serial-pinout"]
    assert "Cisco" in pinout
    for pin, signal in enumerate(CISCO_STRAIGHT, start=1):
        assert f"{pin} {signal}" in pinout


def test_the_rear_has_two_ethernet_jacks_two_c14_inlets_and_a_switch_for_each(device):
    net = [p for p in placements(device, "rear") if p.get("group") == "net"]
    assert [p["rel-pos"] for p in net] == [1, 2]
    inlets = of(device, "rear", "std/c14-inlet")
    assert len(inlets) == 2 and device["chassis"]["power"] == "ac"
    switches = of(device, "rear", "eaton/b097-power-rocker")
    assert sorted(p["for"] for p in switches) == sorted(p["id"] for p in inlets)
    legends = {s["text"] for s in device["views"]["rear"]["silkscreen"]}
    assert {"NET1", "NET2"} <= legends


def test_the_front_has_four_labelled_lamps_two_usb_ports_a_console_jack_and_an_erase_pinhole(device):
    leds = of(device, "front", "common/led-dot")
    assert len(leds) == 4
    usb = of(device, "front", "std/usb-a")
    assert len(usb) == 2 and all(p["skin"] == "usb2" for p in usb)
    console = [p for p in placements(device, "front") if p["id"] == "console"]
    assert len(console) == 1 and console[0]["attrs"]["role"] == "console"
    assert len(of(device, "front", "common/reset-button")) == 1
    legends = {s["text"] for s in device["views"]["front"]["silkscreen"]}
    assert {"PWR", "H/B", "SER", "NET", "USB", "CONSOLE", "ERASE"} <= legends
    ordered = [s["text"] for s in sorted(
        (s for s in device["views"]["front"]["silkscreen"] if s["text"] in ("PWR", "H/B", "SER", "NET")),
        key=lambda s: s["at"][0])]
    assert ordered == ["PWR", "H/B", "SER", "NET"]


def test_every_position_is_estimated_and_the_ears_are_not_dimensioned(device):
    prov = device["provenance"]
    for key in ("front-layout", "rear-layout", "jack-gaps"):
        assert prov[key]["confidence"] == "estimated"
    assert device["chassis"]["ears"]["positions"][0]["default"] is True


def test_the_inlet_type_is_the_specifications_page_c14(device):
    prov = device["provenance"]["inlet"]
    assert prov["confidence"] == "datasheet" and "IEC-320-C14" in prov["note"]
    assert "C14" in device["attrs"]["power"]["power-input"]


def test_the_rocker_is_a_maker_part_read_from_a_photograph():
    c = yaml.safe_load(ROCKER.read_text())
    assert c["name"] == "b097-power-rocker" and c["class"] == "button"
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "photograph" in c["provenance"]["size"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_exports_list_the_48_serial_lines_as_console_server_ports(device, target):
    doc = yaml.safe_load((EXPORTS / target / "device-types/Eaton/B097-048.yaml").read_text())
    ids = [p["id"] for p in serial(device)]
    assert [r["name"] for r in doc["console-server-ports"]] == ids
    assert len(ids) == 48
    assert {r["type"] for r in doc["console-server-ports"]} == {"rj-45"}
    assert doc["console-ports"] == [{"name": "Console", "type": "rj-45"}]
    assert [i["name"] for i in doc["interfaces"]] == ["NET1", "NET2"]
    assert {i["type"] for i in doc["interfaces"]} == {"1000base-t"}
    assert [p["type"] for p in doc["power-ports"]] == ["iec-60320-c14"] * 2

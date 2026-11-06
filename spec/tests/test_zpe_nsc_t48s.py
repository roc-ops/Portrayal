"""The ZPE Systems Nodegrid Serial Console S, 48 ports (NSC-T48S).

Modelled from the maker's data sheet (April 15, 2026) and two photographs: the dual-AC build with
two SFP cages. The data sheet calls the face with the HDMI port and the fan modules its Front and
the face with the 48 serial ports its Rear, and the device keeps those names.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/zpe/nsc-t48s/device.yaml"
COMPONENTS = ROOT / "library/components/zpe"
RAIL_PIECES = ["rail-180-395-a", "rail-180-395-b", "rail-180-395-c", "rail-180-395-d"]


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def of(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def test_the_envelope_is_the_data_sheets(device):
    c = device["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (443, 43, 312, 1)
    assert c["weight-kg"] == 4.9
    assert device["views"]["rear"]["size"] == {"w": 443, "h": 43}
    assert device["views"]["top"]["size"] == {"w": 443, "h": 312}
    assert device["views"]["left"]["size"] == {"w": 312, "h": 43}


def test_there_are_48_serial_ports_numbered_one_to_forty_eight(device):
    ports = [p for p in placements(device, "rear") if p.get("group") == "serial"]
    assert len(ports) == 48
    assert sorted(p["rel-pos"] for p in ports) == list(range(1, 49))
    assert {p["ref"] for p in ports} == {"common/rj45-ganged-lamped@1"}


def test_odd_ports_are_on_the_top_row_and_even_ports_beneath(device):
    ports = {p["rel-pos"]: p for p in placements(device, "rear") if p.get("group") == "serial"}
    for n in range(1, 49, 2):
        assert ports[n]["at"][1] < ports[n + 1]["at"][1]
        assert ports[n]["at"][0] == ports[n + 1]["at"][0]
        assert ports[n].get("rotate") == 180 and "rotate" not in ports[n + 1]


def test_the_ports_stand_in_three_blocks_of_eight_columns(device):
    xs = sorted({p["at"][0] for p in placements(device, "rear") if p.get("group") == "serial"})
    assert len(xs) == 24
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(13.97) == 21 and len([s for s in steps if s > 13.97]) == 2


def test_each_serial_port_has_a_printed_numeral(device):
    marks = {s["text"] for s in device["views"]["rear"]["silkscreen"] if s.get("for", "").startswith("port-")}
    assert marks == {str(n) for n in range(1, 49)}


def test_the_rear_has_two_sfp_cages_a_console_a_usb_3_port_and_two_ac_inlets(device):
    assert len(of(device, "rear", "std/sfp-ganged@1")) == 2
    console = [p for p in placements(device, "rear") if p["id"] == "console"]
    assert console and console[0]["attrs"]["role"] == "console"
    usb = of(device, "rear", "std/usb-a@1")
    assert len(usb) == 1 and usb[0]["attrs"]["usb"] == "3.0" and "skin" not in usb[0]
    inlets = of(device, "rear", "std/c14-inlet@1")
    assert len(inlets) == 2 and len(of(device, "rear", "zpe/nsc-power-rocker@1")) == 2


def test_the_front_has_hdmi_thirteen_usb_2_ports_two_lamps_a_reset_and_two_fans(device):
    assert len(of(device, "front", "zpe/nsc-hdmi@1")) == 1
    usb = of(device, "front", "std/usb-a@1")
    assert len(usb) == 13 and all(p["skin"] == "usb2" for p in usb)
    assert len(of(device, "front", "common/led-dot@1")) == 2
    assert len(of(device, "front", "common/reset-button@1")) == 1
    bays = device["views"]["front"]["components"]["bays"]
    assert [b["default"] for b in bays] == ["zpe/nsc-fan-module@1"] * 2


def test_the_data_sheets_14_usb_ports_are_all_drawn(device):
    n = len(of(device, "front", "std/usb-a@1")) + len(of(device, "rear", "std/usb-a@1"))
    assert n == 14


def test_the_rail_kit_is_listed_and_its_four_pieces_exist(device):
    assert {"ref": "zpe/rail-180-395@1", "supply": "optional"} in device["chassis"]["kits"]
    for name in RAIL_PIECES + ["rail-180-395"]:
        assert (COMPONENTS / name / "v1/contract.yaml").is_file()


def test_the_kit_states_the_serial_console_ranges_in_millimetres():
    kit = yaml.safe_load((COMPONENTS / "rail-180-395/v1/contract.yaml").read_text())
    depth = {c["id"]: c["depth"] for c in kit["configurations"]}
    assert depth == {"a-b": [457.2, 635.0], "a-c": [584.2, 787.4], "a-d": [787.4, 1003.3]}


def test_every_new_part_has_a_skin_and_says_what_it_estimates():
    for name in ["nsc-fan-module", "nsc-power-rocker", "nsc-hdmi"] + RAIL_PIECES:
        contract = yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())
        assert (COMPONENTS / name / "v1/skins/default.svg").is_file()
        assert "estimated" in str(contract.get("size-confidence")), name

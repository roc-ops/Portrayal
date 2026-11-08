"""The ZPE Systems Nodegrid 48-port consoles: the Serial Console R, the Serial Console Plus and the
Plus Core Edition.

Each is modelled from the maker's data sheet and the photographs it holds, and draws the faces a
document shows: the R and the Plus have a Rear photograph and no Front one, the Core Edition has
both. A face no document shows is stated as empty with its reason, never drawn.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/zpe"
NAMES = ["nsc-t48r", "nscp-t48r", "nscp-t48r-core"]


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


@pytest.fixture(scope="module", params=NAMES)
def device(request):
    return load(request.param)


@pytest.fixture(scope="module")
def r():
    return load("nsc-t48r")


@pytest.fixture(scope="module")
def plus():
    return load("nscp-t48r")


@pytest.fixture(scope="module")
def core():
    return load("nscp-t48r-core")


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def of(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def test_the_envelope_is_the_data_sheets(device):
    c = device["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (443, 43, 312, 1)
    assert device["views"]["rear"]["size"] == {"w": 443, "h": 43}
    assert device["views"]["top"]["size"] == {"w": 443, "h": 312}
    assert device["views"]["left"]["size"] == {"w": 312, "h": 43}


def test_there_are_48_serial_ports_numbered_one_to_forty_eight_on_the_rear(device):
    ports = [p for p in placements(device, "rear") if p.get("group") == "serial"]
    assert sorted(p["rel-pos"] for p in ports) == list(range(1, 49))
    assert {p["ref"] for p in ports} == {"common/rj45-ganged-lamped@1"}
    marks = {s["text"] for s in device["views"]["rear"]["silkscreen"] if s.get("for", "").startswith("port-")}
    assert marks == {str(n) for n in range(1, 49)}


def test_odd_ports_are_on_the_top_row_and_even_ports_beneath(device):
    ports = {p["rel-pos"]: p for p in placements(device, "rear") if p.get("group") == "serial"}
    for n in range(1, 49, 2):
        assert ports[n]["at"][1] < ports[n + 1]["at"][1]
        assert ports[n]["at"][0] == ports[n + 1]["at"][0]


def test_the_ports_stand_in_three_blocks_of_eight_columns(device):
    xs = sorted({p["at"][0] for p in placements(device, "rear") if p.get("group") == "serial"})
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert len(xs) == 24 and len([s for s in steps if s > 13.97]) == 2


def test_the_rear_has_two_ethernet_rj45_ports_one_above_the_other(device):
    eth = of(device, "rear", "common/rj45-ganged-eth@1")
    assert len(eth) == 2
    assert eth[0]["at"][0] == eth[1]["at"][0] and eth[0]["at"][1] != eth[1]["at"][1]


def test_the_serial_console_r_rear_has_one_ac_inlet_a_console_and_a_usb_3_port_and_no_sfp(r):
    assert len(of(r, "rear", "std/c14-inlet@1")) == 1
    assert len(of(r, "rear", "zpe/nsc-power-rocker@1")) == 1
    assert not of(r, "rear", "std/sfp-ganged@1")
    console = [p for p in placements(r, "rear") if p["id"] == "console"]
    assert console and console[0]["attrs"]["role"] == "console"
    usb = of(r, "rear", "std/usb-a@1")
    assert len(usb) == 1 and usb[0]["attrs"]["usb"] == "3.0"


@pytest.mark.parametrize("name", ["nscp-t48r", "nscp-t48r-core"])
def test_a_plus_rear_has_two_ac_inlets_two_sfp_cages_and_no_console(name):
    d = load(name)
    assert len(of(d, "rear", "std/c14-inlet@1")) == 2
    assert len(of(d, "rear", "zpe/nsc-power-rocker@1")) == 2
    assert len(of(d, "rear", "std/sfp-ganged@1")) == 2
    assert not [p for p in placements(d, "rear") if p["id"] == "console"]


def test_the_r_and_the_plus_state_their_front_as_empty_with_a_reason(r, plus):
    for d in (r, plus):
        assert d["views"]["front"].get("empty")
        assert not placements(d, "front")
        assert any(g["what"].startswith("front") and g["reason"] == "needs-photo" for g in d["gaps"])


def test_the_core_front_has_two_usb_3_ports_the_console_and_two_lamps_and_no_reset_or_hdmi(core):
    assert len(of(core, "front", "std/usb-a@1")) == 2
    assert [p for p in placements(core, "front") if p["id"] == "console"]
    assert len(of(core, "front", "common/led-dot@1")) == 2
    assert not of(core, "front", "common/reset-button@1")
    assert not of(core, "front", "zpe/nsc-hdmi@1")


def test_each_device_names_the_part_number_of_the_build_it_draws(device):
    parts = {pn for c in device["configurations"].values() for pn in c["part-numbers"]}
    assert len(parts) == 1
    assert next(iter(parts)).startswith(("NSC-T48R", "ZPE-NSCP-T48R", "NSCP-T48R"))


def test_the_builds_no_document_shows_are_listed_as_gaps(device):
    assert any(g["what"] == "other-skus" for g in device["gaps"])

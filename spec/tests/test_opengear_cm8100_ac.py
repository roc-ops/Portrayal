"""The Opengear CM8100 console managers on AC power: the 16, 32 and 48 port
models on a gigabit uplink and the same three with two 10G SFP+ cages.

What is true of the library once they are in: each model is a device of its
own, its serial block has the ports the data sheet names, numbered as printed,
the serial lines are console server ports, the front has the console jack, two
USB-A jacks and the network ports of its family, the rear has two C14 inlets
and no USB-C bank, and the envelope is the data sheet's.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "opengear"
EXPORTS = ROOT / "library" / "exports"

# name: (model, serial ports, depth mm, SFP+ cages)
SKUS = {
    "cm8116": ("CM8116", 16, 235.0, 0),
    "cm8132": ("CM8132", 32, 235.0, 0),
    "cm8148": ("CM8148", 48, 235.0, 0),
    "cm8116-10g": ("CM8116-10G", 16, 265.0, 2),
    "cm8132-10g": ("CM8132-10G", 32, 265.0, 2),
    "cm8148-10g": ("CM8148-10G", 48, 265.0, 2),
}


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(name, view):
    return (device(name)["views"][view].get("components") or {}).get("placements") or []


@pytest.mark.parametrize("name", SKUS)
def test_each_sku_is_a_device_of_its_own(name):
    model, _, depth, _ = SKUS[name]
    d = device(name)
    assert d["manufacturer"] == "Opengear" and d["model"] == model
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"], c["power"]) == (440.0, 44.0, depth, 1, "ac")


@pytest.mark.parametrize("name", SKUS)
def test_serial_block_has_the_skus_ports_numbered_as_printed(name):
    _, n, _, _ = SKUS[name]
    serial = [p for p in placements(name, "front") if p.get("group") == "serial"]
    assert [p["id"] for p in sorted(serial, key=lambda p: p["rel-pos"])] == [f"serial-{i}" for i in range(1, n + 1)]
    assert device(name)["groups"]["serial"]["attrs"] == {"media": "rj45-serial", "role": "console-server"}


@pytest.mark.parametrize("name", SKUS)
def test_front_has_the_console_two_usb_and_two_rj45_network_ports(name):
    front = placements(name, "front")
    assert len([p for p in front if p.get("group") == "console"]) == 1
    assert len([p for p in front if p["ref"] == "std/usb-a@1"]) == 2
    assert len([p for p in front if p["ref"] == "common/rj45-eth@1"]) == 2
    assert [p["id"] for p in front if p["ref"] == "common/reset-button@1"] == ["erase"]


@pytest.mark.parametrize("name", SKUS)
def test_the_10g_models_have_two_sfp_plus_cages_and_the_1g_models_none(name):
    cages = _cages(name)
    assert len(cages) == SKUS[name][3]
    if cages:
        assert device(name)["groups"]["net-sfp"]["attrs"]["speed"] == "10g"


def _cages(name):
    return [p for p in placements(name, "front") if p["ref"] == "std/sfp@1"]


@pytest.mark.parametrize("name", SKUS)
def test_rear_has_two_ac_inlets_and_no_usb_c_bank(name):
    rear = placements(name, "rear")
    assert [p["id"] for p in rear if p["ref"] == "std/c14-inlet@1"] == ["ac-inlet-1", "ac-inlet-2"]
    assert not [p for p in rear if p["ref"] == "std/usb-c@1"]


@pytest.mark.parametrize("name", SKUS)
def test_positions_read_off_a_photograph_are_declared_estimates_with_the_method(name):
    prov = device(name)["provenance"]
    for key in ("front-layout", "rear-layout"):
        assert prov[key]["confidence"] == "estimated"
        assert "Method" in prov[key]["note"]


@pytest.mark.parametrize("name", SKUS)
@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_exports_list_each_serial_line_as_a_console_server_port(name, target):
    model, n, _, _ = SKUS[name]
    doc = yaml.safe_load((EXPORTS / target / "device-types" / "Opengear" / f"{model}.yaml").read_text())
    assert [r["name"] for r in doc["console-server-ports"]] == [f"serial-{i}" for i in range(1, n + 1)]

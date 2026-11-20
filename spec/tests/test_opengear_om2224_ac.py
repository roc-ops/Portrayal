"""The Opengear OM2224-24E operations managers on dual AC power: the gigabit and
10G platforms, each with and without the cellular modem.

What is true of the library once they are in:

- Each model is a device of its own, with the data sheet envelope.
- Each has twenty-four console server ports and twenty-four switch ports, numbered as printed.
- The front has the RJ45 and micro-USB consoles, two USB-A jacks and the network ports of its platform.
- The rear has eight USB-A jacks, A to H, and two IEC C14 inlets that are real connectors.
- A cellular model also has two SIM slots and three antenna jacks. A model without the modem has none.
- Positions read off a picture are declared estimates with the method.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "opengear"
EXPORTS = ROOT / "library" / "exports"

# name: (model, SFP cages, speed of the cages, RJ45 network ports, cellular)
SKUS = {
    "om2224-24e": ("OM2224-24E", 2, "1g", 2, False),
    "om2224-24e-l": ("OM2224-24E-L", 2, "1g", 2, True),
    "om2224-24e-10g": ("OM2224-24E-10G", 2, "10g", 1, False),
    "om2224-24e-10g-l": ("OM2224-24E-10G-L", 2, "10g", 1, True),
}


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(name, view):
    return (device(name)["views"][view].get("components") or {}).get("placements") or []


@pytest.mark.parametrize("name", SKUS)
def test_each_sku_is_a_device_of_its_own_with_the_data_sheet_envelope(name):
    d = device(name)
    assert d["manufacturer"] == "Opengear" and d["model"] == SKUS[name][0]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"], c["power"]) == (440.0, 44.0, 260.0, 1, "ac")


@pytest.mark.parametrize("name", SKUS)
def test_serial_and_switch_blocks_have_twenty_four_ports_numbered_as_printed(name):
    front = placements(name, "front")
    for group, prefix in (("serial", "serial"), ("switch", "switch")):
        ports = [p for p in front if p.get("group") == group]
        assert [p["id"] for p in sorted(ports, key=lambda p: p["rel-pos"])] == [f"{prefix}-{i}" for i in range(1, 25)]
    assert device(name)["groups"]["serial"]["attrs"] == {"media": "rj45-serial", "role": "console-server"}


@pytest.mark.parametrize("name", SKUS)
def test_front_has_both_consoles_two_usb_and_the_platforms_network_ports(name):
    _, cages, speed, rj45, _ = SKUS[name]
    front = placements(name, "front")
    assert [p["id"] for p in front if p.get("group") == "console"] == ["console"]
    assert [p["id"] for p in front if p.get("group") == "console-usb"] == ["console-micro"]
    assert len([p for p in front if p["ref"] == "std/usb-a@1"]) == 2
    assert len([p for p in front if p["ref"] == "std/sfp@1"]) == cages
    assert len([p for p in front if p["ref"] == "common/rj45-eth@1"]) == rj45
    assert device(name)["groups"]["net-sfp"]["attrs"]["speed"] == speed
    assert [p["id"] for p in front if p["ref"] == "common/reset-button@1"] == ["erase"]


@pytest.mark.parametrize("name", SKUS)
def test_rear_has_eight_usb_jacks_and_two_c14_inlets_that_are_connectors(name):
    d = device(name)
    rear = placements(name, "rear")
    assert [p["id"] for p in rear if p["ref"] == "std/usb-a@1"] == [f"usb-{c}" for c in "abcdefgh"]
    assert [p["id"] for p in rear if p["ref"] == "std/c14-inlet@1"] == ["ac-inlet-1", "ac-inlet-2"]
    decor = {x["id"] for x in d["views"]["rear"]["panel"]["decor"]}
    assert not [i for i in decor if i.startswith("dc-")]
    assert "dc-connector-part" not in {g["what"] for g in d["gaps"]}


@pytest.mark.parametrize("name", SKUS)
def test_the_cellular_parts_are_on_the_cellular_models_only(name):
    cellular = SKUS[name][4]
    rear = placements(name, "rear")
    sims = [p["id"] for p in rear if p["ref"] == "opengear/sim-slot-2ff@1"]
    antennas = [p["id"] for p in rear if p["ref"] == "common/sma-jack@1"]
    assert sims == (["sim1", "sim2"] if cellular else [])
    assert antennas == (["wwan1", "wwan2", "wwan3"] if cellular else [])


@pytest.mark.parametrize("name", SKUS)
def test_six_lamps_are_placed_with_states(name):
    lamps = [p for p in placements(name, "front") if p["ref"] == "common/led-dot@1"]
    assert [p["id"] for p in lamps] == ["led-power", "led-heartbeat", "led-network", "led-ioio", "led-cellular", "led-cloud"]
    assert all("states" in p for p in lamps)


@pytest.mark.parametrize("name", SKUS)
def test_positions_read_off_a_picture_are_declared_estimates_with_the_method(name):
    prov = device(name)["provenance"]
    for key in ("front-layout", "rear-layout", "top-layout"):
        assert prov[key]["confidence"] == "estimated"
        assert "Method" in prov[key]["note"]


@pytest.mark.parametrize("name", SKUS)
def test_all_six_faces_are_present(name):
    assert set(device(name)["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


@pytest.mark.parametrize("name", SKUS)
@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_exports_list_each_serial_line_as_a_console_server_port(name, target):
    doc = yaml.safe_load((EXPORTS / target / "device-types" / "Opengear" / f"{SKUS[name][0]}.yaml").read_text())
    assert [r["name"] for r in doc["console-server-ports"]] == [f"serial-{i}" for i in range(1, 25)]


@pytest.mark.parametrize("name", SKUS)
def test_the_console_usb_group_and_jack_carry_the_librarys_micro_usb_b_media(name):
    assert device(name)["groups"]["console-usb"]["attrs"]["media"] == "micro-usb-b"
    jack = [p for p in placements(name, "front") if p["id"] == "console-micro"]
    assert [p["attrs"]["media"] for p in jack] == ["micro-usb-b"]

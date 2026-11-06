"""The Opengear CM8000 console managers: four SKUs, two front layouts and two
rear layouts, a SIM slot part and the interface it presents.

What is true of the library once they are in: each SKU has its own device, the
serial block and the cellular rear differ by SKU as the data sheet and the
photographs say, every position read off a photograph is declared an estimate
with its method, and the SIM slot is a part with a mate.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "opengear"
COMPONENTS = ROOT / "library" / "components" / "opengear"

# name: (model, serial ports, cellular, depth)
SKUS = {
    "cm8004": ("CM8004", 4, False, 177.0),
    "cm8008": ("CM8008", 8, False, 177.0),
    "cm8004-c": ("CM8004-C", 4, True, 189.0),
    "cm8008-c": ("CM8008-C", 8, True, 189.0),
}


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(name, view):
    d = device(name)
    return (d["views"][view].get("components") or {}).get("placements") or []


def refs(name, view, ref):
    return [p for p in placements(name, view) if p["ref"] == ref]


@pytest.mark.parametrize("name", SKUS)
def test_each_sku_is_a_device_of_its_own(name):
    model, _, _, depth = SKUS[name]
    d = device(name)
    assert d["manufacturer"] == "Opengear" and d["model"] == model
    assert d["name"] == name
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (220.0, 44.0, depth, 1)


@pytest.mark.parametrize("name", SKUS)
def test_all_six_faces_are_present(name):
    assert set(device(name)["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


@pytest.mark.parametrize("name", SKUS)
def test_serial_block_has_the_skus_ports_numbered_as_printed(name):
    _, n, _, _ = SKUS[name]
    serial = [p for p in placements(name, "front") if p.get("group") == "serial"]
    assert [p["id"] for p in sorted(serial, key=lambda p: p["rel-pos"])] == [f"serial-{i}" for i in range(1, n + 1)]
    assert {p["ref"] for p in serial} == {"std/rj45-ganged@2"}
    assert all(p["attrs"]["media"] == "rj45-serial" for p in serial)
    # odd numbers on the upper row, even on the lower: the printed 1 3 / 2 4
    for p in serial:
        upper = int(p["id"].split("-")[1]) % 2 == 1
        assert (p.get("rotate") == 180) == upper


@pytest.mark.parametrize("name", SKUS)
def test_each_network_port_is_a_combo_with_both_halves_placed(name):
    ids = {p["id"] for p in placements(name, "front")}
    assert {"net1-sfp", "net2-sfp", "net1-rj45", "net2-rj45"} <= ids


@pytest.mark.parametrize("name", SKUS)
def test_front_has_the_usb_console_erase_and_six_lamps(name):
    front = placements(name, "front")
    assert len([p for p in front if p["ref"] == "std/usb-a@1"]) == 2
    console = [p for p in front if p["ref"] == "std/usb-c@1"]
    assert len(console) == 1 and console[0]["attrs"]["role"] == "console"
    assert [p["id"] for p in front if p["ref"] == "common/reset-button@1"] == ["erase"]
    assert len([p for p in front if p["ref"] == "common/led-dot@1"]) == 6


@pytest.mark.parametrize("name", SKUS)
def test_rear_has_two_12vdc_jacks(name):
    jacks = refs(name, "rear", "common/dc-barrel@1")
    assert [p["id"] for p in jacks] == ["dc-in-1", "dc-in-2"]


@pytest.mark.parametrize("name", SKUS)
def test_cellular_rear_adds_four_antenna_jacks_and_two_sim_slots(name):
    _, _, cellular, _ = SKUS[name]
    sma = refs(name, "rear", "common/sma-jack@1")
    sim = refs(name, "rear", "opengear/sim-slot-4ff@1")
    assert (len(sma), len(sim)) == ((4, 2) if cellular else (0, 0))
    if cellular:
        assert [p["id"] for p in sma] == ["wwan1", "wwan2", "wwan3", "wwan4"]
        assert [p["id"] for p in sim] == ["sim1", "sim2"]


def test_the_sim_slot_presents_a_key_and_the_tray_mates_it():
    slot = yaml.safe_load((COMPONENTS / "sim-slot-4ff" / "v1" / "contract.yaml").read_text())
    tray = yaml.safe_load((COMPONENTS / "sim-tray-4ff" / "v1" / "contract.yaml").read_text())
    registry = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    assert slot["interface"] == "sim-tray-4ff" and tray["mates"] == "sim-tray-4ff"
    assert "sim-tray-4ff" in registry
    for part in (slot, tray):
        assert part["size-confidence"] == {"w": "estimated", "h": "estimated"}


@pytest.mark.parametrize("name", SKUS)
def test_positions_read_off_a_photograph_are_declared_estimates_with_the_method(name):
    prov = device(name)["provenance"]
    for key in ("front-layout", "rear-layout"):
        assert prov[key]["confidence"] == "estimated"
        assert "px/mm" in prov[key]["note"]


@pytest.mark.parametrize("name", SKUS)
def test_no_rack_kit_is_invented_where_no_document_dimensions_one(name):
    d = device(name)
    assert "ears" not in d["chassis"] and "kits" not in d["chassis"]
    assert any(g["what"] == "rack-kit" for g in d["gaps"])


def test_the_maker_is_in_the_vendor_registry():
    vendors = yaml.safe_load((ROOT / "spec" / "schemas" / "vendors.yaml").read_text())
    assert "opengear" in (vendors.get("vendors") or vendors)

"""The Opengear ACM7004-2-L and ACM7004-5-L resilience gateways.

Both are read from three documents. The ACM7000 data sheet gives size, ports and power. The Resilience Gateway
Quick Start Guide, page 2, prints the front and rear photographs of both models with callouts. The ACM700x-2
Quick Start Guide gives the kit. The faces are measured off those photographs and say so. Three connectors are
parts of their own with a registered key and a mate. They are the mini SIM slot, the four-position DC housing
and the eight-position digital I/O header.
"""
import pathlib

import pytest
import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
DEVICES = {
    "acm7004-2-l": "ACM7004-2-L",
    "acm7004-5-l": "ACM7004-5-L",
}
# key -> (presenting part, mating part)
KEYS = {
    "sim-card-2ff": ("opengear/sim-slot-2ff@1", "opengear/sim-card-2ff@1"),
    "opengear-acm-dc-block-4": ("opengear/acm7000-dc-header@1", "opengear/acm7000-dc-plug@1"),
    "opengear-acm-dio-block-8": ("opengear/acm7000-dio-header@1", "opengear/acm7000-dio-plug@1"),
}
CM = 10.0


def _load(p):
    return yaml.safe_load(pathlib.Path(p).read_text())


def _contract(ref):
    name, major = ref.split("@")
    return _load(LIB / "components" / name / f"v{major}" / "contract.yaml")


def _device(slug):
    return _load(LIB / "devices/opengear" / slug / "device.yaml")


def _placements(slug, view):
    return _device(slug)["views"][view]["components"]["placements"]


def _by_group(slug, view, group):
    return [p for p in _placements(slug, view) if p.get("group") == group]


def _refs(slug, view, ref):
    return [p for p in _placements(slug, view) if p["ref"] == ref]


@pytest.mark.parametrize("slug,model", DEVICES.items())
def test_the_device_is_the_model_the_data_sheet_lists(slug, model):
    d = _device(slug)
    assert d["manufacturer"] == "Opengear"
    assert d["model"] == model


@pytest.mark.parametrize("slug", DEVICES)
def test_the_chassis_is_the_data_sheets_centimetre_size_and_has_no_rack_units(slug):
    c = _device(slug)["chassis"]
    assert c["width"] == pytest.approx(13 * CM)
    assert c["depth"] == pytest.approx(12 * CM)
    assert c["height"] == pytest.approx(3.5 * CM)
    assert c["mount"] == "desktop"
    assert "ru" not in c


@pytest.mark.parametrize("slug", DEVICES)
def test_all_six_faces_exist_and_the_four_unseen_sides_are_plain_outlines(slug):
    device = _device(slug)
    views = device["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for name in ("top", "bottom", "left", "right"):
        assert not views[name].get("empty"), name
        assert views[name]["size"], name
    gap = next(g for g in device["gaps"] if g["what"] == "sides")
    assert gap["reason"] == "needs-photo"
    assert set(gap["scope"]) == {"top", "bottom", "left", "right"}
    assert "plain outlines from the stated size" in gap["note"]


@pytest.mark.parametrize("slug", DEVICES)
def test_the_front_carries_two_sim_slots_and_eight_lamps_drawn_off(slug):
    slots = _refs(slug, "front", "opengear/sim-slot-2ff@1")
    assert sorted(p["rel-pos"] for p in slots) == [1, 2]
    lamps = _by_group(slug, "front", "status-leds")
    assert len(lamps) == 8
    for lamp in lamps:
        assert lamp["states"]["lamp"][0] == "off", lamp["id"]


@pytest.mark.parametrize("slug", DEVICES)
def test_the_rear_carries_four_serial_four_usb_and_three_antenna_jacks(slug):
    assert len(_by_group(slug, "rear", "serial")) == 4
    assert len(_by_group(slug, "rear", "usb")) == 4
    assert len(_by_group(slug, "rear", "wwan")) == 3
    assert len(_refs(slug, "rear", "opengear/acm7000-dc-header@1")) == 1


def test_the_2_l_has_two_network_jacks_on_the_front_and_the_digital_io_header_on_the_rear():
    assert len(_by_group("acm7004-2-l", "front", "net")) == 2
    assert len(_refs("acm7004-2-l", "rear", "opengear/acm7000-dio-header@1")) == 1


def test_the_5_l_has_the_combo_uplink_on_the_front_and_a_four_port_switch_on_the_rear_and_no_dio_header():
    d = "acm7004-5-l"
    assert len(_by_group(d, "front", "uplink-sfp")) == 1
    assert len(_by_group(d, "front", "uplink-rj45")) == 1
    assert len(_by_group(d, "rear", "switch")) == 4
    assert not _refs(d, "rear", "opengear/acm7000-dio-header@1")


@pytest.mark.parametrize("key", KEYS)
def test_each_new_connector_is_registered_and_a_part_mates_it(key):
    keys = _load(SPEC / "schemas/connectors.yaml")["interfaces"]
    assert key in keys
    header, mate = KEYS[key]
    assert _contract(header)["interface"] == key
    assert _contract(mate)["mates"] == key


@pytest.mark.parametrize("key", KEYS)
def test_no_other_part_presents_or_mates_a_new_key(key):
    holders = set()
    for path in (LIB / "components").glob("*/*/v*/contract.yaml"):
        c = _load(path)
        if c.get("interface") == key or c.get("mates") == key:
            holders.add(f"{c['name']}")
    assert len(holders) == 2, holders


def test_the_mini_sim_slot_is_not_the_cm8000_nano_tray_slot():
    assert _contract("opengear/sim-slot-2ff@1")["interface"] != _contract("opengear/sim-slot-4ff@1")["interface"]


@pytest.mark.parametrize("ref", [r for pair in KEYS.values() for r in pair])
def test_the_new_parts_declare_what_no_document_gives(ref):
    c = _contract(ref)
    assert c["size-confidence"], ref
    text = " ".join(str(v) for v in c["provenance"].values())
    assert "STAND-IN" in text or "estimated" in text or "NOT STATED" in text, ref


@pytest.mark.parametrize("slug,model", DEVICES.items())
def test_the_dc_housing_is_exported_as_the_one_power_port(slug, model):
    for target in ("netbox", "nautobot"):
        export = _load(LIB / "exports" / target / "device-types/Opengear" / f"{model}.yaml")
        ports = export["power-ports"]
        assert [p["name"] for p in ports] == ["power-in"], target
        assert ports[0]["label"].startswith("DC power input"), target


@pytest.mark.parametrize("slug", DEVICES)
def test_the_faces_say_they_are_estimated_and_name_their_method(slug):
    prov = _device(slug)["provenance"]
    for name in ("front-layout", "rear-layout"):
        assert prov[name]["confidence"] == "estimated"
        assert "Method" in prov[name]["note"]

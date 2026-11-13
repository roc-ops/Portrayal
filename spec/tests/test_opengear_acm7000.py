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
        assert views[name].get("empty"), name
        assert views[name]["size"], name
    gap = next(g for g in device["gaps"] if g["what"] == "sides")
    assert gap["reason"] == "needs-photo"
    assert set(gap["scope"]) == {"top", "bottom", "left", "right"}
    assert "plain outlines from the stated size" in gap["note"]


@pytest.mark.parametrize("slug,lamp_count", [("acm7004-2-l", 8), ("acm7004-5-l", 11)])
def test_the_front_carries_two_sim_slots_and_its_lamps_drawn_off(slug, lamp_count):
    slots = _refs(slug, "front", "opengear/sim-slot-2ff@1")
    assert sorted(p["rel-pos"] for p in slots) == [1, 2]
    lamps = _by_group(slug, "front", "status-leds")
    assert len(lamps) == lamp_count
    for lamp in lamps:
        assert lamp["states"]["lamp"][0] == "off", lamp["id"]


def test_the_5_l_sfp_cage_carries_three_red_marks_drawn_off():
    marks = [p for p in _placements("acm7004-5-l", "front") if p.get("for") == "net1-sfp"]
    assert sorted(p["id"] for p in marks) == ["led-sfp-1", "led-sfp-2", "led-sfp-3"]
    assert [p["at"] for p in marks] == [[16.0, 15.5], [20.6, 15.5], [25.0, 15.5]]
    for mark in marks:
        assert mark["ref"] == "common/led-dot@1", mark["id"]
        assert mark["states"]["lamp"] == ["off", {"name": "red", "color": "#d12d32"}], mark["id"]


def test_the_2_l_has_no_sfp_cage_and_so_no_cage_marks():
    assert not _refs("acm7004-2-l", "front", "std/sfp@1")
    assert not [p for p in _placements("acm7004-2-l", "front") if str(p["id"]).startswith("led-sfp")]


def _dc_symbol_dashes(slug):
    paths = [s["path"] for s in _device(slug)["views"]["rear"]["silkscreen"] if s.get("for") == "power-in" and "path" in s]
    assert len(paths) == 1, slug
    return paths[0].count("M") - 1


@pytest.mark.parametrize("slug,dashes", [("acm7004-2-l", 4), ("acm7004-5-l", 5)])
def test_the_dc_symbol_draws_the_dashes_the_rear_photograph_shows(slug, dashes):
    assert _dc_symbol_dashes(slug) == dashes


@pytest.mark.parametrize("slug", DEVICES)
def test_part_450031_is_cited_to_the_acm700x_2_quick_start_and_not_to_the_data_sheet(slug):
    note = _device(slug)["provenance"]["power"]["note"]
    sentence = next(s for s in note.split(". ") if "450031" in s)
    assert "ACM700x-2 Quick Start Guide" in sentence
    assert "page 1" in sentence
    assert "Data sheet" not in sentence


@pytest.mark.parametrize("slug,model", DEVICES.items())
def test_net1_is_traffic_and_not_management_only_while_the_2_l_net2_stays_management(slug, model):
    device = _device(slug)
    net1 = [p for p in _placements(slug, "front") if p["id"].startswith("net1")]
    assert net1
    for p in net1:
        assert device["groups"][p["group"]]["role"] == "traffic", p["id"]
    for target in ("netbox", "nautobot"):
        export = _load(LIB / "exports" / target / "device-types/Opengear" / f"{model}.yaml")
        flags = {i["name"]: i.get("mgmt_only", False) for i in export["interfaces"]}
        for p in net1:
            assert flags[p["id"]] is False, (target, p["id"])
        if slug == "acm7004-2-l":
            assert flags["net2"] is True, target


@pytest.mark.parametrize("slug", DEVICES)
def test_the_rear_carries_four_serial_four_usb_and_three_antenna_jacks(slug):
    assert len(_by_group(slug, "rear", "serial")) == 4
    assert len(_by_group(slug, "rear", "usb")) == 4
    assert len(_by_group(slug, "rear", "wwan")) == 3
    assert len(_refs(slug, "rear", "opengear/acm7000-dc-header@1")) == 1


def test_the_2_l_has_two_network_jacks_on_the_front_and_the_digital_io_header_on_the_rear():
    assert len(_by_group("acm7004-2-l", "front", "net1")) == 1
    assert len(_by_group("acm7004-2-l", "front", "net2")) == 1
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


@pytest.mark.heavy
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

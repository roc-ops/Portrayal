"""The Digi Connect IT 4, Connect IT 16 and Connect IT 48 console servers, from Digi's product pages and photographs.

What the held sources fix, and so what these tests hold:
  the product pages   the ports, the power, the lamps, the sizes and the part numbers
  the photographs     the position of every jack, lamp and legend on the front and the rear, and the colours

No held document gives a dimension model or a drawing, so every position is read off a photograph and the
contracts say so. The four faces no photograph shows are declared empty, with the search that found nothing.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/digi"
COMP = ROOT / "library/components"

RACK = {"connect-it-16": 16, "connect-it-48": 48}
DEVICES = ["connect-it-4", "connect-it-16", "connect-it-48"]


def device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def layout(name):
    return yaml.safe_load((DEV / name / "layout.yaml").read_text())


def contract(ref):
    return yaml.safe_load((COMP / ref / "v1" / "contract.yaml").read_text())


def placements(name, view):
    return (device(name)["views"][view].get("components") or {}).get("placements") or []


def bays(name, view):
    return (device(name)["views"][view].get("components") or {}).get("bays") or []


def by_id(items):
    return {i["id"]: i for i in items}


def test_the_three_devices_are_there():
    for name in DEVICES:
        assert (DEV / name / "device.yaml").is_file(), name
        assert (DEV / name / "layout.yaml").is_file(), name
        assert device(name)["manufacturer"] == "Digi"


@pytest.mark.parametrize("name", RACK)
def test_the_rack_units_are_the_product_pages_444_by_300_by_44(name):
    c = device(name)["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (444.0, 44.0, 300.0, 1)
    views = device(name)["views"]
    assert {views[v]["size"]["w"] for v in ("front", "rear")} == {444.0}
    assert views["top"]["size"] == {"w": 444.0, "h": 300.0}
    assert views["left"]["size"] == {"w": 300.0, "h": 44.0}


def test_the_connect_it_4_is_a_desktop_box_228_by_127_by_25():
    d = device("connect-it-4")
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["mount"]) == (228.0, 25.0, 127.0, "desktop")
    assert "ru" not in c and "ears" not in c
    assert d["views"]["front"]["size"] == {"w": 228.0, "h": 25.0}
    assert d["views"]["right"]["size"] == {"w": 127.0, "h": 25.0}


@pytest.mark.parametrize("name", DEVICES)
def test_every_face_is_there_and_the_unphotographed_ones_say_where_the_search_looked(name):
    views = device(name)["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for face in ("top", "bottom", "left", "right"):
        assert len(views[face]["empty"]) > 60, face
    for face in ("front", "rear"):
        assert "empty" not in views[face], face


@pytest.mark.parametrize("name,count", RACK.items())
def test_the_serial_ports_are_two_rows_with_the_odd_numbers_below(name, count):
    ports = [p for p in placements(name, "front") if p["id"].startswith("serial-")]
    assert sorted(int(p["id"].split("-")[1]) for p in ports) == list(range(1, count + 1))
    assert {p["ref"] for p in ports} == {"common/rj45-ganged-lamped@1"}
    row = {int(p["id"].split("-")[1]): p["at"][1] for p in ports}
    assert {row[n] for n in range(1, count + 1, 2)} == {27.1}
    assert {row[n] for n in range(2, count + 1, 2)} == {11.6}
    assert {p["attrs"]["media"] for p in ports} == {"rj45-serial"}


def test_the_48_has_three_blocks_of_eight_columns():
    ports = {int(p["id"].split("-")[1]): p["at"][0]
             for p in placements("connect-it-48", "front") if p["id"].startswith("serial-")}
    lower = [ports[n] for n in range(1, 49, 2)]
    steps = [round(b - a, 2) for a, b in zip(lower, lower[1:])]
    assert steps == ([14.2] * 7 + [20.1]) * 2 + [14.2] * 7


@pytest.mark.parametrize("name", RACK)
def test_the_other_front_ports_are_parts_the_library_holds(name):
    p = by_id(placements(name, "front"))
    assert p["console"]["ref"] == "std/rj45@2" and p["console"]["attrs"]["role"] == "console"
    assert [p[i]["ref"] for i in ("usb-1", "usb-2")] == ["std/usb-a@1"] * 2
    assert [p[i]["ref"] for i in ("uplink-1", "uplink-2")] == ["std/sfp-ganged@1"] * 2
    assert [p[i]["ref"] for i in ("eth-1", "eth-2")] == ["common/rj45-eth@1"] * 2


def test_the_connect_it_4_ports_and_lamps_are_the_ones_the_photographs_print():
    front = by_id(placements("connect-it-4", "front"))
    rear = by_id(placements("connect-it-4", "rear"))
    assert sorted(i for i in front if i.startswith("led-signal-")) == [f"led-signal-{n}" for n in range(1, 6)]
    assert {"led-pwr", "led-online", "led-backup", "led-lte", "led-sim-1", "led-sim-2"} <= set(front)
    assert [rear[i]["ref"] for i in ("wan", "lan")] == ["common/rj45-eth@1"] * 2
    serial = [i for i in rear if i.startswith("serial-")]
    assert sorted(serial) == [f"serial-{n}" for n in range(1, 5)]
    assert rear["dc-in"]["ref"] == "common/dc-barrel@1"


@pytest.mark.parametrize("name", RACK)
def test_the_rear_has_two_supply_bays_that_take_the_supply_part(name):
    b = by_id(bays(name, "rear"))
    assert set(b) == {"psu-1", "psu-2"}
    for bay in b.values():
        assert bay["accepts"] == ["digi/itps-psu@1"]
        assert bay["default"] == "digi/itps-psu@1"
        assert bay["size"]["w"] == contract("digi/itps-psu")["size"]["w"]
    assert [p["ref"] for p in placements(name, "rear") if p["id"].startswith("wwan")] == ["std/sma@1"] * 2


@pytest.mark.parametrize("name", RACK)
def test_the_sd_slot_is_a_slot_that_a_card_mates(name):
    slot = by_id(placements(name, "rear"))["card-slot"]
    assert slot["ref"] == "vertiv/sd-card-slot@1"
    assert contract("vertiv/sd-card-slot")["interface"] == contract("common/sd-card")["mates"] == "sd-card"


def test_the_supply_composes_the_library_inlet_and_states_no_kit_it_cannot_tell():
    c = contract("digi/itps-psu")
    assert [p["ref"] for p in c["parts"]] == ["std/c14-inlet@1"]
    assert c["class"] == "psu"
    assert "model" not in c["attrs"]
    figures = [k for k in c["attrs"] if k.startswith("power") or "watt" in k or "airflow" in k]
    assert not figures


@pytest.mark.parametrize("name,sku", [("connect-it-4", "5402-RMG4-GLB"), ("connect-it-16", "IT16-1002"),
                                      ("connect-it-48", "IT48-1002")])
def test_each_part_number_the_page_lists_is_in_one_configuration(name, sku):
    configs = device(name)["configurations"]
    assert [pn for c in configs.values() for pn in (c.get("part-numbers") or {})] == [sku]
    assert sum(1 for c in configs.values() if c.get("default")) == 1


@pytest.mark.parametrize("name", DEVICES)
def test_the_device_is_authored_in_its_layout_and_the_export_is_its_expansion(name):
    assert layout(name)["name"] == name
    assert device(name)["version"] == layout(name)["version"]


@pytest.mark.parametrize("name", RACK)
def test_the_ears_are_the_flush_pair_the_photographs_show_and_no_kit_is_listed(name):
    ears = device(name)["chassis"]["ears"]
    assert [p["name"] for p in ears["positions"]] == ["flush"]
    assert "at" not in ears["positions"][0]
    assert "kits" not in device(name)["chassis"]


def test_the_supply_estimates_its_depth_and_says_so():
    c = contract("digi/itps-psu")
    assert "estimated" in c["provenance"]["depth"]
    assert set(c["size-confidence"].values()) == {"photo-measured"}


@pytest.mark.parametrize("name", RACK)
def test_the_unit_consumption_is_filed_as_the_maximum_because_the_page_does_not_qualify_it(name):
    power = device(name)["attrs"]["power"]
    assert power["power-max-w"] == {"connect-it-16": 30.5, "connect-it-48": 39}[name]
    assert "power-typical-w" not in power
    assert "package" not in str(device(name)["attrs"]["physical"])

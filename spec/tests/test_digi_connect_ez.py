"""The Digi Connect EZ 16 and Connect EZ 32 console servers, from Digi's product page and its dimension model.

Two devices of one chassis (444 x 44 x 255, 1U). What the held sources fix, and so what these tests hold:
  the product page      the ports, the power, the lamps and the twelve part numbers
  the dimension model   the chassis, the position of every jack on the front, the rear bays and the walls' holes
  the photographs       the legends, the lamps' colours and the rack ears

Nothing here pins a part this change does not add: the tests read the two devices and the parts they are the
reason for.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library/devices/digi"
COMP = ROOT / "library/components"

DEVICES = {"connect-ez-16": 16, "connect-ez-32": 32}

# configuration -> the part numbers the product page lists for it, with the size's prefix
SKU_SUFFIXES = {
    "single-ac": ("A100-GLB", "C100-GLB"),
    "dual-ac": ("A200-GLB", "C200-GLB"),
    "dual-dc": ("AD00", "CD00"),
}

NEW_PARTS = ["digi/serial-jack-10p", "digi/microsd-socket", "digi/ezps-ac", "digi/ez-psu-dc", "digi/ez-psu-blank",
             "digi/ez-sysfan", "digi/core-lte-modem", "digi/core-blank", "generic/rj45-10p-plug",
             "generic/microsd-card"]


def device(name):
    return yaml.safe_load((DEV / name / "device.yaml").read_text())


def contract(ref):
    return yaml.safe_load((COMP / ref / "v1" / "contract.yaml").read_text())


def placements(name, view):
    return (device(name)["views"][view].get("components") or {}).get("placements") or []


def bays(name, view):
    return (device(name)["views"][view].get("components") or {}).get("bays") or []


def by_id(items):
    return {i["id"]: i for i in items}


@pytest.mark.parametrize("name", DEVICES)
def test_the_chassis_is_the_dimension_models_body(name):
    d = device(name)
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (444.0, 44.0, 255.0, 1)
    assert d["manufacturer"] == "Digi"
    assert {v["size"]["w"] for k, v in d["views"].items() if k in ("front", "rear")} == {444.0}


@pytest.mark.parametrize("name", DEVICES)
def test_every_face_is_there(name):
    views = device(name)["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for face in ("top", "bottom", "left", "right"):
        assert "empty" not in views[face], f"{face} is drawn from the dimension model's holes"
        assert views[face]["panel"]["decor"], face


@pytest.mark.parametrize("name", DEVICES)
def test_the_ears_are_flush_and_no_kit_is_listed(name):
    ears = device(name)["chassis"]["ears"]
    assert [p["name"] for p in ears["positions"]] == ["flush"]
    assert ears["positions"][0]["default"] is True
    assert "kits" not in device(name)["chassis"]


@pytest.mark.parametrize("name,count", DEVICES.items())
def test_the_serial_ports_are_sixteen_wide_blocks_of_four(name, count):
    ports = [p for p in placements(name, "front") if p["id"].startswith("serial-")]
    assert len(ports) == count
    assert sorted(int(p["id"].split("-")[1]) for p in ports) == list(range(1, count + 1))
    assert {p["ref"] for p in ports} == {"digi/serial-jack-10p@1"}
    lower = sorted(p["at"][0] for p in ports if p["at"][1] == 23.65)
    assert len(lower) == 16
    # four jacks 16.0 apart, then a 6.0 gutter: the blocks stand 70.0 apart
    assert [round(b - a, 2) for a, b in zip(lower, lower[1:])] == [16.0, 16.0, 16.0, 22.0] * 3 + [16.0, 16.0, 16.0]


def test_the_32_has_a_second_row_turned_over():
    ports = [p for p in placements("connect-ez-32", "front") if p["id"].startswith("serial-")]
    upper = [p for p in ports if p["at"][1] < 20]
    assert len(upper) == 16
    assert {p.get("rotate") for p in upper} == {180}
    assert {p["id"] for p in upper} == {f"serial-{n}" for n in range(17, 33)}


@pytest.mark.parametrize("name", DEVICES)
def test_the_other_front_ports_are_the_reused_parts(name):
    p = by_id(placements(name, "front"))
    assert p["console"]["ref"] == "digi/serial-jack-10p@1" and p["console"]["attrs"]["role"] == "console"
    assert p["sd-slot"]["ref"] == "digi/microsd-socket@1"
    assert [p[i]["ref"] for i in ("usb-1", "usb-2")] == ["std/usb-a@1"] * 2
    assert [p[i]["ref"] for i in ("uplink-1", "uplink-2")] == ["std/sfp-ganged@1"] * 2
    assert [p[i]["ref"] for i in ("eth-1", "eth-2")] == ["common/rj45-eth@1"] * 2


@pytest.mark.parametrize("name", DEVICES)
def test_the_eight_lamps_the_page_lists_are_drawn(name):
    lamps = [i for i in by_id(placements(name, "front")) if i.startswith("led-")]
    assert sorted(lamps) == sorted(["led-fan-1", "led-fan-2", "led-sys-fan", "led-psu-1", "led-psu-2", "led-user",
                                    "led-wwan-signal", "led-wwan-service"])


@pytest.mark.parametrize("name", DEVICES)
def test_the_rear_bays_and_what_each_takes(name):
    b = by_id(bays(name, "rear"))
    assert set(b) == {"psu-1", "psu-2", "core", "sys-fan"}
    assert set(b["psu-1"]["accepts"]) == {"digi/ezps-ac@1", "digi/ez-psu-dc@1"}
    assert set(b["psu-2"]["accepts"]) == {"digi/ezps-ac@1", "digi/ez-psu-dc@1", "digi/ez-psu-blank@1"}
    assert set(b["core"]["accepts"]) == {"digi/core-lte-modem@1", "digi/core-blank@1"}
    assert b["sys-fan"]["accepts"] == ["digi/ez-sysfan@1"]
    # a bay is as wide as the part that fills it, so nothing is centred off its seat
    sizes = {"digi/ezps-ac@1": 95.0, "digi/core-lte-modem@1": 133.2, "digi/ez-sysfan@1": 54.7}
    for bay in b.values():
        occupant = bay["default"]
        if occupant in sizes:
            assert bay["size"]["w"] == sizes[occupant], bay["id"]


@pytest.mark.parametrize("name", DEVICES)
def test_each_sku_the_page_lists_is_in_one_configuration(name):
    size = name[-2:]
    configs = device(name)["configurations"]
    for config, suffixes in SKU_SUFFIXES.items():
        assert set(configs[config]["part-numbers"]) == {f"EZ{size}-{s}" for s in suffixes}, config
    assert sum(len(c.get("part-numbers") or {}) for c in configs.values()) == 6


def test_the_supplies_follow_the_build():
    for name in DEVICES:
        c = device(name)["configurations"]
        assert c["single-ac"]["bays"]["psu-2"] == "digi/ez-psu-blank@1"
        assert c["dual-ac"]["bays"] == {"psu-1": "digi/ezps-ac@1", "psu-2": "digi/ezps-ac@1", "core": "digi/core-blank@1"}
        assert c["dual-dc"]["bays"]["psu-1"] == c["dual-dc"]["bays"]["psu-2"] == "digi/ez-psu-dc@1"
        assert [c[k]["power"] for k in ("single-ac", "dual-ac", "dual-dc")] == ["ac", "ac", "dc"]


@pytest.mark.heavy
def test_one_part_number_is_one_component():
    seen = {}
    for path in (ROOT / "library/devices").glob("*/*/device.yaml"):
        for cfg in (yaml.safe_load(path.read_text()).get("configurations") or {}).values():
            for pn in (cfg.get("part-numbers") or {}):
                if pn.startswith("EZ16-") or pn.startswith("EZ32-"):
                    seen.setdefault(pn, set()).add(path.parent.name)
    assert len(seen) == 12
    assert all(len(v) == 1 for v in seen.values()), seen


@pytest.mark.parametrize("key,part,mate", [("rj45-10p", "digi/serial-jack-10p", "generic/rj45-10p-plug"),
                                           ("microsd", "digi/microsd-socket", "generic/microsd-card")])
def test_each_new_connector_has_its_key_and_its_mate(key, part, mate):
    keys = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"]
    assert key in keys
    assert contract(part)["interface"] == key
    assert contract(mate)["mates"] == key
    assert "unmated" not in keys[key]


def test_the_supply_composes_the_library_inlet_and_the_modem_the_library_jack():
    assert [p["ref"] for p in contract("digi/ezps-ac")["parts"]] == ["std/c14-inlet@1"]
    assert contract("std/c14-inlet")["interface"] == "iec-c14"
    assert [p["ref"] for p in contract("digi/core-lte-modem")["parts"]] == ["std/sma@1"] * 2
    assert contract("generic/sma-plug")["mates"] == "sma"


@pytest.mark.parametrize("ref", NEW_PARTS)
def test_every_part_this_change_adds_says_how_it_knows_its_size(ref):
    c = contract(ref)
    assert c["size-confidence"], ref
    assert set(c["size-confidence"].values()) <= {"drawing", "estimated", "borrowed", "datasheet", "photo-measured"}
    assert c["provenance"], ref


def test_the_estimates_are_declared_and_not_hidden():
    assert contract("generic/rj45-10p-plug")["size-confidence"]["w"] == "estimated"
    assert contract("generic/microsd-card")["size-confidence"] == {"w": "estimated", "h": "estimated", "d": "estimated"}
    assert "estimated" in contract("digi/serial-jack-10p")["provenance"]["cavity"]
    assert "estimated" in contract("digi/ez-psu-dc")["provenance"]["connector"]


def test_no_supply_or_fan_states_a_power_figure_the_documents_do_not():
    for ref in ("digi/ezps-ac", "digi/ez-psu-dc", "digi/ez-sysfan", "digi/core-lte-modem"):
        attrs = contract(ref)["attrs"]
        assert not [k for k in attrs if k.startswith("power")], ref


@pytest.mark.parametrize("name", DEVICES)
def test_the_package_weight_is_not_called_the_units(name):
    attrs = device(name)["attrs"]
    assert "package-weight-kg" in attrs["physical"]
    assert "weight-kg" not in attrs["physical"]

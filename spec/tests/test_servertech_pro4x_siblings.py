"""The Server Technology PRO4X Smart POPS 4T16A, Switched 4F16A and Smart 4C16A, three 0U rack PDUs.

What is true of the library once they are in it: each exists under its maker with the 36 outlets of the
maker's shared outline drawing (12 HDOT C13 and 24 HDOT Cx, numbered as printed, each through one of six
breakers), each states the metering and switching its family has, an outlet declares the on/off states only
where the family switches, and each lists the SKU its product page prints.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "servertech"

HDOT_CX = "servertech/hdot-cx-outlet"
C13 = "std/c13-outlet"

# device name: (metering-scope, outlet-switching, SKU part number)
FAMILIES = {
    "pro4x-smart-pops-4t16a": ("outlet", False, "C4T36RA-GPBD2FE1"),
    "pro4x-switched-4f16a": ("branch", True, "C4W36RA-GPBD2FE1"),
    "pro4x-smart-4c16a": ("branch", False, "C4S36RA-GPBD2FE1"),
}


def _device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text(encoding="utf-8"))


def _placements(dev):
    out = []
    for view in dev.get("views", {}).values():
        out.extend((view.get("components") or {}).get("placements") or [])
    return out


def _outlets(dev):
    return [p for p in _placements(dev) if p["ref"].split("@")[0] in (HDOT_CX, C13)]


@pytest.mark.parametrize("name", FAMILIES)
def test_the_outlets_are_twelve_c13_and_twenty_four_cx_numbered_as_printed(name):
    outlets = _outlets(_device(name))
    refs = [p["ref"].split("@")[0] for p in outlets]
    assert (refs.count(C13), refs.count(HDOT_CX)) == (12, 24)
    assert sorted(int(p["id"].rsplit("-", 1)[1]) for p in outlets) == list(range(1, 37))


@pytest.mark.parametrize("name", FAMILIES)
def test_each_breaker_feeds_six_outlets(name):
    dev = _device(name)
    breakers = {p["id"] for p in _placements(dev) if p["ref"].startswith("servertech/pro4x-breaker")}
    assert len(breakers) == 6
    per = {}
    for outlet in _outlets(dev):
        assert outlet["through"] in breakers, outlet["id"]
        per[outlet["through"]] = per.get(outlet["through"], 0) + 1
    assert sorted(per.values()) == [6] * 6


@pytest.mark.parametrize("name", FAMILIES)
def test_the_family_states_its_metering_and_switching(name):
    scope, switching, _ = FAMILIES[name]
    management = _device(name)["attrs"]["management"]
    assert management["metering-scope"] == scope
    assert management["outlet-switching"] is switching
    for outlet in _outlets(_device(name)):
        assert outlet.get("states") == (["on", "off"] if switching else None), outlet["id"]


@pytest.mark.parametrize("name", FAMILIES)
def test_the_sku_is_the_one_the_product_page_prints(name):
    dev = _device(name)
    sku = FAMILIES[name][2]
    assert list(dev["configurations"]["base"]["part-numbers"]) == [sku]
    assert dev["attrs"]["physical"]["length-mm"] == 1778.2
    assert dev["chassis"]["height"] == 1778.2


def test_the_three_part_numbers_are_distinct():
    skus = [v[2] for v in FAMILIES.values()]
    assert len(set(skus)) == 3

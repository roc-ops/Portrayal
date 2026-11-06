"""The OCP NIC 3.0 form-factor keys, their figures and the first cards that name them.

OCP NIC 3.0 Design Specification, Version 1.6.0, Table 5 (printed page 25), gives
four live card outlines: SFF, TSFF, DSFF and TDSFF. This holds the registry, the
interface keys, the R660's OCP bay and the one ConnectX-8 card to that table. All
cases read files; none builds anything.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "spec/schemas"
LIB = ROOT / "library"

# key: (width, depth, z-height, connectors)
TABLE_5 = {
    "ocp3-sff": (76.00, 115.00, 11.50, 1),
    "ocp3-tsff": (76.00, 115.00, 14.20, 1),
    "ocp3-dsff": (157.55, 115.00, 11.50, 2),
    "ocp3-tdsff": (157.55, 115.00, 14.20, 2),
}
LICENCE = "Hardware License (Permissive)"
PILOT = "library/components/nvidia/c8180p-ocp3-tsff/v1/contract.yaml"


def _yaml(path):
    return yaml.safe_load((ROOT / path).read_text())


@pytest.fixture(scope="module")
def standards():
    return _yaml("spec/schemas/standards.yaml")["standards"]


@pytest.fixture(scope="module")
def interfaces():
    return _yaml("spec/schemas/connectors.yaml")["interfaces"]


def _find(node, key, value):
    """Every mapping under `node` whose `key` is `value`."""
    if isinstance(node, dict):
        if node.get(key) == value:
            yield node
        for v in node.values():
            yield from _find(v, key, value)
    elif isinstance(node, list):
        for v in node:
            yield from _find(v, key, value)


# --- (a) the registry ----------------------------------------------------------

@pytest.mark.parametrize("key", TABLE_5)
def test_the_registry_holds_the_table_5_outline(standards, key):
    width, depth, z, connectors = TABLE_5[key]
    entry = standards[key]
    assert (entry["w"], entry["h"]) == (width, depth)
    assert entry["confidence"] == "verified"
    assert "Table 5" in entry["registry"] and "1.6.0" in entry["registry"]
    text = entry["description"] + entry["source"]
    assert f"{z:.2f}" in text, "the Z-height is in the text: the entry has no key for it"
    assert ("one 4C+" if connectors == 1 else "two 4C+") in text


@pytest.mark.parametrize("key", TABLE_5)
def test_each_entry_names_the_licence_and_the_page(standards, key):
    source = standards[key]["source"]
    assert LICENCE in source
    assert "OCP NIC 3.0 Design Specification" in source
    assert "page 25" in source


# --- (b) the deprecated outline is skipped -------------------------------------

def test_the_deprecated_large_form_factor_is_not_registered(standards, interfaces):
    assert not [k for k in standards if "lff" in k and k.startswith("ocp")]
    assert not [k for k in interfaces if "lff" in k]


# --- (c) the interface keys ----------------------------------------------------

@pytest.mark.parametrize("key", TABLE_5)
def test_the_interface_key_is_declared_and_points_at_its_entry(standards, interfaces, key):
    assert interfaces[key]["standard"] == key
    assert key in standards
    assert interfaces[key]["note"]


def test_the_tsff_note_says_it_takes_an_sff_card_and_what_is_left_open(interfaces):
    note = interfaces["ocp3-tsff"]["note"]
    assert "ocp3-sff" in note and "electromagnetic" in note


def test_the_dsff_note_says_it_is_two_sff_positions(interfaces):
    assert "two SFF" in interfaces["ocp3-dsff"]["note"]


# --- (d) the R660's slot -------------------------------------------------------

def test_the_r660_ocp_bay_is_unchanged_and_states_no_key_yet():
    """Dell calls the slot SFF, but a bay that states an interface waits for the
    readers of `accepts` to go through `manifest.offers`; that is a later change."""
    bays = list(_find(_yaml("library/devices/dell/r660/device.yaml"), "id", "ocp"))
    bays = [b for b in bays if "accepts" in b]
    assert len(bays) == 1
    bay = bays[0]
    assert "interface" not in bay
    assert bay["accepts"] == [
        "dell/ocp3-blank-16g@1", "dell/ocp3-4x1g-rj45@1", "dell/ocp3-2x10g-rj45@1",
        "dell/ocp3-4x10g-rj45@1", "dell/ocp3-2x25g-sfp28@1", "dell/ocp3-4x25g-sfp28@1",
        "dell/ocp3-2x100g-qsfp56@1"]
    assert "nvidia/c8180p-ocp3-tsff@1" not in bay["accepts"], "a TSFF card is taller than the slot"


# --- (e) the pilot card --------------------------------------------------------

def test_the_pilot_card_is_a_tsff_card_with_one_osfp_cage():
    c = _yaml(PILOT)
    assert c["kind"] == "module" and c["name"] == "c8180p-ocp3-tsff"
    assert c["attrs"]["form-factor"] == "ocp3-tsff"
    assert c["size"]["w"] == pytest.approx(71.80) and c["size"]["d"] == 115.00
    cages = [p for p in c["parts"] if p["ref"] == "std/osfp@1"]
    assert len(cages) == 1
    assert cages[0]["group"] == "osfp" and cages[0]["attrs"]["speed"] == "800g"
    assert c["groups"]["osfp"]["attrs"]["media"] == "osfp"


def test_the_pilot_card_records_the_thickness_and_the_manual_speeds():
    c = _yaml(PILOT)
    prov = c["provenance"]
    assert "14.20" in prov["thickness"] and "Table 5" in prov["thickness"]
    assert "800Gb/s" in c["description"] and "2x400GbE" in c["description"]
    assert c["attrs"]["part-numbers"] == "900-9X85E-00EX-MJ0"


def test_the_pilot_card_is_seated_in_no_held_device():
    for path in (LIB / "devices").rglob("*.yaml"):
        assert "c8180p-ocp3-tsff" not in path.read_text(), path


# --- (f) the design note -------------------------------------------------------

def test_the_design_note_names_the_keys_and_says_the_specification_is_held():
    text = (ROOT / "docs/cards-by-interface-design.md").read_text()
    for key in TABLE_5:
        assert f"`{key}`" in text
    assert "OCP NIC 3.0 Design Specification" in text
    assert "held" in text and "none held" not in text.split("## How a card seats")[0]
    assert "deprecated" in text

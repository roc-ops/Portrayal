"""CH3000 modules: every connector a module draws presents a registered interface and has a mate.

A fibre adapter is the composed SC opening, not the frame drawn round it; a test point and an RS-232 jack are
composed parts that present the key their data sheets name. Reads contracts and the registry only.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "library" / "components"
INTERFACES = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]


def contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((COMP / ns / name / f"v{major}" / "contract.yaml").read_text())


# key -> (part that presents it, part that mates it)
KEYS = {
    "g-type": ("common/g-type-male-port@1", "common/g-type-female-plug@1"),
    "g-type-female": ("common/g-type-female-port@1", "common/g-type-male-plug@1"),
    "stereo-jack": ("common/stereo-jack@1", "common/stereo-plug@1"),
}

# module -> (the element that was a bare port, the connector part now composed there)
CONNECTORS = {
    "ar3002e": ("test-point", "common/g-type-male-port@1"),
    "ar3044h": ("test-point", "common/g-type-male-port@1"),
    "ar3044l": ("test-point", "common/g-type-male-port@1"),
    "dr3450n": ("test-point", "common/g-type-male-port@1"),
    "dr3600n": ("test-point", "common/g-type-female-port@1"),
    "ht358xh": ("test-point", "std/mcx@1"),
    "cx3003c": ("rs232", "common/stereo-jack@1"),
    "cx3033n": ("rs232", "common/stereo-jack@1"),
}

# modules whose adapters are composed SC openings
ADAPTERS = (
    "bp-a5 bp-f2 bp-f4 np33f01 np34c01 np34f01d np34m05 np34s04 np35c0x np35d04 np35d08 np35f01 np35f04s np35m04 np35m08 "
    "op31m2d op33f1x op34d5x op34f1d op34m5x op34s4s op35d4x op35d8cf op35f1 op35f1d op35f4s os32m2b"
).split()


@pytest.mark.parametrize("key", sorted(KEYS))
def test_the_key_is_registered_with_a_part_that_presents_it_and_one_that_mates_it(key):
    assert key in INTERFACES
    port, plug = KEYS[key]
    assert contract(port)["interface"] == key
    assert contract(plug)["mates"] == key


@pytest.mark.parametrize("key", sorted(KEYS))
def test_a_new_key_claims_no_standard(key):
    assert "standard" not in INTERFACES[key]


@pytest.mark.parametrize("module", sorted(CONNECTORS))
def test_the_module_composes_the_connector_its_data_sheet_names(module):
    element, ref = CONNECTORS[module]
    c = contract(f"commscope/{module}@1")
    assert ref in [p["ref"] for p in c["parts"]]
    assert c["elements"][element]["class"] != "port"


@pytest.mark.parametrize("module", sorted(CONNECTORS))
def test_no_provenance_still_says_the_connector_is_only_drawn(module):
    text = " ".join(str(v) for v in contract(f"commscope/{module}@1")["provenance"].values()).lower()
    assert "no registry entry exists" not in text
    assert "drawn as an element" not in text


@pytest.mark.parametrize("module", ADAPTERS)
def test_every_port_a_module_draws_is_a_composed_connector(module):
    c = contract(f"commscope/{module}@1")
    part_ids = {p["id"] for p in c["parts"]}
    bare = [k for k, e in c["elements"].items() if e.get("class") == "port" and k not in part_ids]
    assert bare == []

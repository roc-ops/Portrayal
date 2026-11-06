"""The DC power connector of the Smartoptics DCP-2-PSU-DC-FB supply is a place a cable lands.

The supply drew its connector as art in its skin, so it offered no cable end. It now composes a connector part, a header the
DCP-series User Manual shows in one photograph and names no maker or part number for, standing in the box its skin already
reserves for the connector. The connector has its own key, which claims no maker, standard or pitch; the header and the cable
connector that mates it are declared stand-ins with estimated sizes, and each contract says so.

  - the supply states the roles the photograph's marks print and states no DC port, because the poles are the contacts of one
    pluggable connector;
  - the skin is not edited, the supply keeps its id and its boxes, and the exported power port is named by the header's id;
  - the record of the supply is gone.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild
from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "smartoptics/dcp-2-psu-dc@1"
HEADER = "smartoptics/dcp-2-dc-header@1"
PLUG = "smartoptics/dcp-2-dc-plug@1"
KEY = "smartoptics-dcp-dc-block-3"
ELEMENT = "dc-terminal"


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def registry():
    return yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_key_is_registered_and_claims_no_maker_standard_or_pitch():
    reg = registry()
    assert KEY in reg
    note = reg[KEY]["note"]
    assert "standard" not in reg[KEY], "no document names a standard"
    assert "pitch-mm" not in reg[KEY]
    assert "claims none" in note and HEADER in note and PLUG in note and SUPPLY in note


def test_the_header_is_an_inlet_and_the_plug_mates_it_at_the_same_point():
    header, plug = contract(HEADER), contract(PLUG)
    assert (header["class"], header["interface"], header["profile"]) == ("inlet", KEY, "power")
    assert (plug["class"], plug["mates"]) == ("port", KEY)
    assert header["connection-points"]["mate"]["at"] == plug["connection-points"]["mate"]["at"]
    assert header["size"] == plug["size"]
    for part in (header, plug):
        assert part["size-confidence"] == {"w": "estimated", "h": "estimated"}
        assert "relief" not in part and part["elements"] == {}
    assert "STAND-IN" in header["provenance"]["part"] and "STAND-IN" in plug["provenance"]["model"]
    assert "NOT STATED" in header["provenance"]["gender"] and "NONE STATED" in header["provenance"]["relief"]


def test_the_supply_composes_the_header_at_the_box_its_skin_reserves():
    c = contract(SUPPLY)
    ours = [p for p in c["parts"] if p["ref"] == HEADER]
    assert len(ours) == 1 and ours[0]["id"] == "dc-header"
    assert ours[0]["at"] == c["elements"][ELEMENT]["at"], "the part stands where the drawn box stands"
    header = contract(HEADER)
    assert [header["size"]["w"], header["size"]["h"]] == c["elements"][ELEMENT]["size"], "and is its size"
    svg = (path_of(SUPPLY) / "skins" / "default.svg").read_text()
    assert "dc-header" not in svg, "the skin is not edited"
    assert {"handle", "fan-aperture", ELEMENT, "latch", "lamp-status"} <= set(c["elements"])


def test_the_supply_is_a_minor_and_states_its_roles_and_no_dc_port():
    c = contract(SUPPLY)
    assert tuple(int(n) for n in c["version"].split(".")[:2]) >= (1, 5)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"connector", "roles", "no-dc-port"} <= set(prov)
    assert "DC INPUT PORT IS NOT STATED HERE" in prov["no-dc-port"]
    assert "stand-in" in prov["connector"]
    assert "`pos`" in prov["roles"] and "NOT PRINTED" in prov["roles"]


def test_the_exporter_names_the_header_as_a_plain_other_connector():
    name = HEADER.split("@")[0]
    assert dx.PART_POWER[name] == "other"
    assert name in dx.POWER_LABEL
    assert dx.power_row(name, "dc-header") == {"name": "dc-header", "type": "other", "label": dx.POWER_LABEL[name]}


@pytest.mark.heavy
def test_the_index_lists_the_header_with_its_key_and_mate_point_and_the_plug_as_a_port(index):
    assert (index[HEADER]["class"], index[HEADER]["interface"]) == ("inlet", KEY)
    assert index[HEADER]["mate"] == contract(HEADER)["connection-points"]["mate"]["at"]
    assert index[PLUG]["class"] == "port" and index[PLUG]["mate"] == index[HEADER]["mate"]


def test_the_record_of_the_supply_is_gone():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    assert (SUPPLY, "C19") not in {(r["part"], r["code"]) for r in doc["rows"]}
    assert doc["cap"] == len(doc["rows"])
    assert not re.search(r"\n\s+closed:", (LIB / "conformance-exceptions.yaml").read_text())

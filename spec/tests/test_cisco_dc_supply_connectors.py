"""The DC connector of two Cisco ASR 9000 supplies, and the HVAC/HVDC inlet of one Nexus supply, are places a cable lands.

The ASR 9901's A9K-1600W-DC and the ASR 9902 and 9903's PWR-1.6KW-DC draw their two-pole DC connector as art in their skins,
so they offered no cable end. The Cisco ASR 9000 Series Fixed-Port Routers Hardware Installation Guide shows the same
connector on both, a shrouded body with two round sockets marked "+DC" above and "-DC" below (Figures 162 and 163), and the
cable block that seats in it (Figures 67 and 68). The guide names no series or part number for it, so the key
`cisco-dc-block-2` claims none, the header and the cable connector are declared stand-ins, and the place and the size are
estimates; each contract says so. Both supplies compose one header part, standing inside the connector their skin draws.

The Nexus NXA-PHV-350W takes "the Anderson Power Saf-D-Grid connector" (Cisco N9348GC-FX3 hardware installation guide), so it
composes the library's existing Saf-D-Grid inlet and takes no new key.

  - each supply states the roles of its contacts (`pos`, `neg`) in its provenance and states no DC port;
  - no skin is edited and no supply's description is changed;
  - the records of the three supplies are gone.

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

A9K, PWR = "cisco/a9k-1600w-dc@1", "cisco/pwr-1p6kw-dc@2"
PHV = "cisco/nxa-phv-350w@1"
HEADER, PLUG = "cisco/a9k-dc-header@1", "cisco/a9k-dc-plug@1"
KEY = "cisco-dc-block-2"
SAF = "std/saf-d-grid@1"
CLOSED = [A9K, PWR, PHV]

# the window each skin draws for the connector, by the element that holds it
WINDOW = {
    A9K: r'<g id="inlet"><rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"',
    PWR: r'<g id="dc-connector"><rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"',
    PHV: r'id="inlet-surround" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"',
}


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def window(ref):
    svg = (path_of(ref) / "skins" / "default.svg").read_text()
    return tuple(map(float, re.search(WINDOW[ref], svg).groups()))


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_key_is_registered_and_claims_no_maker():
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    note = reg[KEY]["note"]
    assert "standard" not in reg[KEY], "the guide names no standard"
    assert "claims none" in note and "Fixed-Port" in note and PLUG in note and HEADER in note


def test_the_header_is_an_inlet_and_the_plug_mates_it_at_the_same_point():
    header, plug = contract(HEADER), contract(PLUG)
    assert (header["class"], header["interface"]) == ("inlet", KEY)
    assert (plug["class"], plug["mates"]) == ("port", KEY)
    assert header["connection-points"]["mate"]["at"] == plug["connection-points"]["mate"]["at"]
    assert header["size"] == plug["size"]
    for part in (header, plug):
        assert part["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "STAND-IN" in header["provenance"]["part"] and "STAND-IN" in plug["provenance"]["model"]


@pytest.mark.parametrize("ref", [A9K, PWR])
def test_the_supply_composes_the_header_inside_the_connector_its_skin_draws(ref):
    c = contract(ref)
    (part,) = c["parts"]
    assert (part["ref"], part["id"]) == (HEADER, "dc-header")
    x, y = part["at"]
    w, h = contract(HEADER)["size"]["w"], contract(HEADER)["size"]["h"]
    wx, wy, ww, wh = window(ref)
    assert wx <= x and x + w <= wx + ww and wy <= y and y + h <= wy + wh, "the part stands inside the drawn connector"


@pytest.mark.parametrize("ref", [A9K, PWR])
def test_the_supply_states_the_roles_and_no_dc_port(ref):
    c = contract(ref)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"header", "roles", "no-dc-port"} <= set(prov)
    for word in ("`pos`", "`neg`", "+DC", "-DC"):
        assert word in prov["roles"]


@pytest.mark.parametrize("ref", CLOSED)
def test_the_supply_is_a_minor_and_its_skin_keeps_what_it_drew(ref):
    c = contract(ref)
    assert c["version"].split(".")[1:] == ["1", "0"], "a supply that gains a composed part is a minor"
    svg = (path_of(ref) / "skins" / "default.svg").read_text()
    assert "dc-header" not in svg and window(ref)


def test_the_hvac_hvdc_supply_composes_the_saf_d_grid_inlet_inside_its_window():
    c = contract(PHV)
    (part,) = c["parts"]
    assert (part["ref"], part["id"]) == (SAF, "inlet")
    assert "dc" not in c and {"connector", "no-dc-port"} <= set(c["provenance"])
    x, y = part["at"]
    w, h = contract(SAF)["size"]["w"], contract(SAF)["size"]["h"]
    wx, wy, ww, wh = window(PHV)
    assert wx <= x and x + w <= wx + ww and wy <= y and y + h <= wy + wh


def test_the_saf_d_grid_inlet_has_a_mate():
    plug = contract("generic/saf-d-grid-plug@1")
    assert plug["class"] == "port" and plug["mates"] == contract(SAF)["interface"]


def test_the_exporter_names_the_header_as_a_plain_other_connector():
    assert dx.PART_POWER["cisco/a9k-dc-header"] == "other"
    assert "2-position" in dx.POWER_LABEL["cisco/a9k-dc-header"]


@pytest.mark.heavy
def test_the_index_lists_the_header_with_its_key_and_mate_point_and_the_plug_as_a_port(index):
    assert (index[HEADER]["class"], index[HEADER]["interface"]) == ("inlet", KEY)
    assert index[HEADER]["mate"] == index[PLUG]["mate"] and index[PLUG]["class"] == "port"


def test_the_records_of_the_closed_supplies_are_gone():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    assert not [ref for ref in CLOSED if (ref, "C19") in rows]
    assert doc["cap"] == len(doc["rows"])

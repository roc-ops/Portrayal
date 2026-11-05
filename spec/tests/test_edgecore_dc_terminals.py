"""The DC terminals of the Edgecore AIS800-64 supply, the ECS4120 and ECS4530 faceplates and the CSR180 and CSR200 are places a cable lands.

Each drew its terminal as art, or placed a part that presented no way to wire it. What changed:

  - the AIS800-64D and AIS800-64O 3000 W DC supply composes a header part, a six-socket DC power connector the Edgecore guide draws
    and names no maker or part number for, with a cable connector that mates it; the key claims no maker, standard or pitch, and both
    parts are declared stand-ins with estimated sizes;
  - the two-pole pluggable DC block of the ECS4120-28Fv2-I and ECS4530-54CSFP-DC-I presents its registered key, and a stand-in cable
    plug mates it;
  - the three-screw terminal blocks of the CSR180 and CSR200 state a DC input port whose poles are the screws the parts already
    compose, with the roles the guides' callouts give;
  - no skin is edited.

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
REGISTRY = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]

AIS_SUPPLY = "edgecore/ais800-64-psu-dc@1"
AIS_HEADER = "edgecore/ais800-64-dc-header@1"
AIS_PLUG = "edgecore/ais800-64-dc-plug@1"
AIS_KEY = "edgecore-ais800-dc-block-6"
PLUG2_HEADER = "common/dc-terminal-plug-2@1"
PLUG2_PLUG = "generic/screw-terminal-2-plug@1"
PLUG2_KEY = "screw-terminal-2"
# terminal, the rating its guides print, the wire size they print (None where they print two)
BLOCKS = [("common/dc-terminal-24@1", 6, None), ("common/dc-terminal-27@1", 6, [14])]
CLOSED = [("csr180", "C19"), ("csr200", "C19"), ("ecs4530-54csfp-i", "C19"),
          ("edgecore/ais800-64-psu-dc@1", "C19"), ("common/dc-terminal-plug-2@1", "C20")]


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_ais800_key_is_registered_and_claims_no_maker_standard_or_pitch():
    note = REGISTRY[AIS_KEY]["note"]
    assert "standard" not in REGISTRY[AIS_KEY] and "pitch-mm" not in REGISTRY[AIS_KEY]
    assert "claims none" in note and AIS_HEADER in note and AIS_PLUG in note and AIS_SUPPLY in note


def test_the_two_pole_key_names_its_header_and_its_mate_and_still_claims_no_pitch():
    entry = REGISTRY[PLUG2_KEY]
    assert "standard" not in entry and "pitch-mm" not in entry
    assert "claims none" in entry["note"]
    assert PLUG2_HEADER in entry["note"] and PLUG2_PLUG in entry["note"]


@pytest.mark.parametrize("header_ref,plug_ref,key", [(AIS_HEADER, AIS_PLUG, AIS_KEY)], ids=["ais800-64"])
def test_the_header_is_an_inlet_and_the_plug_mates_it_at_the_same_point(header_ref, plug_ref, key):
    header, plug = contract(header_ref), contract(plug_ref)
    assert (header["class"], header["interface"], header["profile"]) == ("inlet", key, "power")
    assert (plug["class"], plug["mates"]) == ("port", key)
    assert header["connection-points"]["mate"]["at"] == plug["connection-points"]["mate"]["at"]
    assert header["size"] == plug["size"]
    for part in (header, plug):
        assert part["size-confidence"] == {"w": "estimated", "h": "estimated"}
        assert "relief" not in part and part["elements"] == {}
    assert "STAND-IN" in header["provenance"]["part"] and "STAND-IN" in plug["provenance"]["model"]
    assert "NOT STATED" in header["provenance"]["gender"] and "NONE STATED" in header["provenance"]["relief"]


def test_the_ais800_supply_composes_the_header_at_the_box_its_skin_reserves():
    c = contract(AIS_SUPPLY)
    ours = [p for p in c["parts"] if p["ref"] == AIS_HEADER]
    assert len(ours) == 1 and ours[0]["id"] == "dc-header"
    assert ours[0]["at"] == c["elements"]["terminal-pocket"]["at"], "the part stands where the drawn box stands"
    header = contract(AIS_HEADER)
    assert [header["size"]["w"], header["size"]["h"]] == c["elements"]["terminal-pocket"]["size"], "and is its size"
    for socket in header["provenance"]["size"].split("(")[1:7]:
        x, y = (float(v) for v in socket.split(")")[0].split(", "))
        box = c["elements"]["terminal-pocket"]["at"]
        assert 0 < x < header["size"]["w"] and 0 < y < header["size"]["h"], (x, y, box)
    assert "dc-header" not in (path_of(AIS_SUPPLY) / "skins" / "default.svg").read_text(), "the skin is not edited"
    assert {"handle", "latch", "terminal", "terminal-pocket", "vent-left", "vent-right"} <= set(c["elements"])


def test_the_ais800_supply_states_its_roles_and_no_dc_port():
    c = contract(AIS_SUPPLY)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"connector", "roles", "no-dc-port"} <= set(prov)
    assert "DC INPUT PORT IS NOT STATED HERE" in prov["no-dc-port"]
    assert "stand-in" in prov["connector"]
    for word in ("`batt`", "`rtn`", "DC return", "Signal"):
        assert word in prov["roles"]
    assert "NO STAGED DOCUMENT NAMES THIS CONNECTOR" in prov["the-terminal-block-is-measured-and-unnamed"]


def test_the_two_pole_block_presents_its_key_and_the_plug_mates_it_at_the_plug_box():
    header, plug = contract(PLUG2_HEADER), contract(PLUG2_PLUG)
    assert header["interface"] == PLUG2_KEY and header["class"] == "inlet"
    assert (plug["class"], plug["mates"]) == ("port", PLUG2_KEY)
    box = header["elements"]["plug"]
    centre = [box["at"][0] + box["size"][0] / 2, box["at"][1] + box["size"][1] / 2]
    assert header["connection-points"]["mate"]["at"] == pytest.approx(centre)
    assert [plug["size"]["w"], plug["size"]["h"]] == box["size"]
    assert plug["connection-points"]["mate"]["at"] == pytest.approx([box["size"][0] / 2, box["size"][1] / 2])
    assert plug["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "STAND-IN" in plug["provenance"]["model"] and "NOT STATED" in plug["provenance"]["pitch"]
    assert "pitch-mm" not in plug["attrs"]
    assert {"roles", "interface"} <= set(header["provenance"]) and "dc" not in header
    svg = (path_of(PLUG2_HEADER) / "skins" / "default.svg").read_text()
    assert 'id="plug"' in svg and "mate" not in svg, "the skin is not edited"


@pytest.mark.parametrize("ref,rating,awg", BLOCKS, ids=["csr180", "csr200"])
def test_the_screw_block_states_one_input_port_on_its_three_screws(ref, rating, awg):
    c = contract(ref)
    (port,) = c["dc"]["ports"]
    assert (port["id"], port["direction"], port["rating-a"]) == ("input", "input", rating)
    assert "voltage" not in port, "the guides print a range and no signed nominal"
    assert port.get("awg") == awg
    assert [(p["role"], p["slot"]) for p in port["poles"]] == [("gnd", "lug-1"), ("batt", "lug-2"), ("rtn", "lug-3")]
    assert {p["id"] for p in c["parts"]} == {"lug-1", "lug-2", "lug-3"}
    for field, entry in port["source"].items():
        assert entry in c["provenance"], (field, entry)
    for word in ("ground", "72 VDC", "DC return"):
        assert word in c["provenance"]["roles"], word


def test_the_screw_blocks_keep_their_poles_and_their_skins():
    for ref, _, _ in BLOCKS:
        c = contract(ref)
        assert {"pole-1", "pole-2", "pole-3"} <= set(c["elements"])
        assert "dc-in" in c["connection-points"]
        svg = (path_of(ref) / "skins" / "default.svg").read_text()
        assert all(f'id="pole-{n}"' in svg for n in (1, 2, 3)), "the skin still draws its three poles"


def test_the_exporter_names_the_new_header_as_a_plain_other_connector():
    name = AIS_HEADER.split("@")[0]
    assert dx.PART_POWER[name] == "other"
    assert name in dx.POWER_LABEL
    assert dx.power_row(name, "dc-header") == {"name": "dc-header", "type": "other", "label": dx.POWER_LABEL[name]}


@pytest.mark.heavy
def test_the_index_lists_each_header_with_its_key_and_each_plug_as_a_port(index):
    for header, plug, key in [(AIS_HEADER, AIS_PLUG, AIS_KEY), (PLUG2_HEADER, PLUG2_PLUG, PLUG2_KEY)]:
        assert (index[header]["class"], index[header]["interface"]) == ("inlet", key)
        assert index[header]["mate"] == contract(header)["connection-points"]["mate"]["at"]
        assert index[plug]["class"] == "port" and index[plug]["mate"] == contract(plug)["connection-points"]["mate"]["at"]
    for ref, _, _ in BLOCKS:
        assert [p["id"] for p in index[ref]["dc-ports"]] == ["input"], ref


def test_the_rows_this_change_closes_are_gone():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    for row in CLOSED:
        assert row not in rows, row
    assert doc["cap"] == len(doc["rows"])
    assert not re.search(r"\n\s+closed:", (LIB / "conformance-exceptions.yaml").read_text())

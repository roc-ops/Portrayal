"""The DC connectors of the Edgecore AS5835, AMX3200 and AGR560 48 VDC supplies are places a cable lands.

Each supply drew its connector as art in its skin, so it offered no cable end. Each now composes a connector part, a header the
Edgecore guides draw and print no maker or part number for (the AGR560 data sheet names a maker and no series), standing in the
box its skin already reserves for the connector. Each connector has its own key, which claims no maker, standard or pitch; the
header and the cable connector that mates it are declared stand-ins with estimated sizes, and each contract says so.

  - the three connectors are three keys, because the cells, the keying and the colours differ; the two switches that seat the
    AS5835 supply share one part;
  - each supply states the roles of its contacts in its provenance (or says they are not stated) and states no DC port, because
    the poles are the contacts of one pluggable connector;
  - no skin is edited, every supply's id and box are kept, and the exported power port is named by the header's id;
  - the four devices that seat the supplies take a patch, and the three records are gone.

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

# supply, header, plug, key, the element whose box the header takes, (device seats), version
DCS = ("edgecore/dcs201-psu-dc@1", "edgecore/dcs201-dc-header@1", "edgecore/dcs201-dc-plug@1", "edgecore-dcs-dc-block-3", "dc-inlet",
       ["dcs201", "dcs202"], "1.2.0", 3)
AMX = ("edgecore/amx-3200-48v-psu@1", "edgecore/amx-3200-dc-header@1", "edgecore/amx-3200-dc-plug@1", "edgecore-amx-dc-block-3", "inlet",
       ["amx3200"], "1.1.0", 3)
AGR = ("edgecore/agr560-psu-dc@1", "edgecore/agr560-dc-header@1", "edgecore/agr560-dc-plug@1", "edgecore-agr-dc-block-2",
       "terminal-pocket", ["agr560"], "1.1.0", 2)
ALL = [DCS, AMX, AGR]
IDS = ["dcs201", "amx3200", "agr560"]
CLOSED = [("edgecore/agr560-psu-dc@1", "C19"), ("edgecore/amx-3200-48v-psu@1", "C19"), ("edgecore/dcs201-psu-dc@1", "C19")]


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


def test_each_key_is_registered_and_claims_no_maker_standard_or_pitch():
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    for supply, header, plug, key, *_ in ALL:
        note = reg[key]["note"]
        assert "standard" not in reg[key], "no document names a standard"
        assert "claims none" in note and header in note and plug in note and supply in note, key
        assert "pitch-mm" not in reg[key]


def test_the_three_connectors_are_three_keys_and_the_amx_is_not_the_pla03():
    keys = [c[3] for c in ALL]
    assert len(set(keys)) == 3
    assert contract(AMX[1])["interface"] != "positronic-pla03"
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    assert "positronic-pla03" in reg and "positronic-pla03" not in keys
    assert "positronic-pla03" in reg[AMX[3]]["note"], "the note says why it is not claimed"


@pytest.mark.parametrize("spec", ALL, ids=IDS)
def test_the_header_is_an_inlet_and_the_plug_mates_it_at_the_same_point(spec):
    supply, header_ref, plug_ref, key, *_ = spec
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


@pytest.mark.parametrize("spec", ALL, ids=IDS)
def test_the_supply_composes_the_header_at_the_box_its_skin_reserves(spec):
    supply, header_ref, _, _, element, _, version, _ = spec
    c = contract(supply)
    assert c["version"] == version
    ours = [p for p in c["parts"] if p["ref"] == header_ref]
    assert len(ours) == 1 and ours[0]["id"] == "dc-header"
    assert ours[0]["at"] == c["elements"][element]["at"], "the part stands where the drawn box stands"
    header = contract(header_ref)
    assert [header["size"]["w"], header["size"]["h"]] == c["elements"][element]["size"], "and is its size"
    svg = (path_of(supply) / "skins" / "default.svg").read_text()
    assert "dc-header" not in svg, "the skin is not edited"


@pytest.mark.parametrize("spec", ALL, ids=IDS)
def test_the_supply_states_its_roles_and_no_dc_port(spec):
    supply = spec[0]
    c = contract(supply)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"connector", "roles", "no-dc-port"} <= set(prov)
    assert "DC INPUT PORT IS NOT STATED HERE" in prov["no-dc-port"]
    assert "stand-in" in prov["connector"]


def test_the_roles_are_the_printed_marks_or_say_they_are_not_stated():
    dcs = contract(DCS[0])["provenance"]["roles"]
    for word in ("`gnd`", "`neg`", "`pos`", "`batt`", "`rtn`"):
        assert word in dcs
    amx = contract(AMX[0])["provenance"]["roles"]
    for word in ("`rtn`", "`gnd`", "`batt`", "No mark is printed"):
        assert word in amx
    assert "NOT STATED" in contract(AGR[0])["provenance"]["roles"]


def test_the_agr560_names_a_maker_and_claims_none():
    c = contract(AGR[1])
    assert "Amphenol" in c["provenance"]["part"] and "still unnamed" in c["provenance"]["part"]
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    assert "Amphenol" not in reg[AGR[3]]["note"].replace("Amphenol Terminal", "")
    assert "STUD" not in contract(AGR[0])["description"].upper().replace("STUDS OF", "")


def test_the_supplies_keep_their_ids_and_boxes():
    assert {"handle", "latch", "vent-field", "dc-inlet"} <= set(contract(DCS[0])["elements"])
    assert {"latch", "inlet", "status", "fan", "handle"} <= set(contract(AMX[0])["elements"])
    assert {"guard", "handle", "terminal", "terminal-pocket", "latch"} <= set(contract(AGR[0])["elements"])
    assert contract(AGR[0])["parts"][:2] == [{"ref": "common/screw-head@1", "id": "screw-1", "at": [3.4, 2.0]},
                                              {"ref": "common/screw-head@1", "id": "screw-2", "at": [37.6, 2.0]}]


def test_the_exporter_names_each_header_as_a_plain_other_connector():
    for _, header, *_ in ALL:
        name = header.split("@")[0]
        assert dx.PART_POWER[name] == "other"
        assert name in dx.POWER_LABEL
        assert dx.power_row(name, "dc-header") == {"name": "dc-header", "type": "other", "label": dx.POWER_LABEL[name]}


@pytest.mark.heavy
def test_the_index_lists_each_header_with_its_key_and_mate_point_and_each_plug_as_a_port(index):
    for supply, header, plug, key, _, _, version, _ in ALL:
        assert (index[header]["class"], index[header]["interface"]) == ("inlet", key)
        assert index[header]["mate"] == contract(header)["connection-points"]["mate"]["at"]
        assert index[plug]["class"] == "port" and index[plug]["mate"] == index[header]["mate"]
        assert index[supply]["version"] == version


def test_the_devices_that_seat_each_supply_are_the_ones_named_and_no_others():
    for supply, _, _, _, _, devices, *_ in ALL:
        seats = sorted(p.parent.name for p in (LIB / "devices" / "edgecore").glob("*/layout.yaml") if supply in p.read_text())
        assert seats == devices, supply


def test_the_records_of_the_three_supplies_are_gone():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    for row in CLOSED:
        assert row not in rows, row
    assert doc["cap"] == len(doc["rows"])
    assert not re.search(r"\n\s+closed:", (LIB / "conformance-exceptions.yaml").read_text())

"""The DC connectors of the Telco Systems XM-3352 and XM-8424H supplies are places a cable lands.

Each supply composed a green pluggable terminal as a part that presented no connector key, so neither offered a cable end. Each now
composes a header part that presents a key of its own, and a cable connector mates it:

  - the XM-3352 supply (`xm3352-psu-dc`): a green block with a flange and a screw at each end and three cells in a row, printed "-"
    over the left cell and "+" over the right one, the key `telco-dc-block-3`;
  - the XM-8424H supply (`xm8424-psu-dc`): a green block with a screw at each end, two cells and a latch tab above them, no
    pole mark legible, the key `telco-dc-block-2`.

The data sheets of the two boxes only show the connectors in photographs and name no maker or part number, so each key claims none,
the header and the cable connector are declared stand-ins with estimated sizes, and each contract says so. Each supply states the
roles its marks give in its provenance and states no DC port. The two parts that drew the green block before are replaced.

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

# supply, header, cable connector, key, the device that seats the supply, the number of cells
CASES = {
    "xm3352": ("telco-systems/xm3352-psu-dc@1", "telco-systems/xm3352-dc-header@1", "telco-systems/xm3352-dc-cable-plug@1",
               "telco-dc-block-3", "xm-3352", 3),
    "xm8424": ("telco-systems/xm8424-psu-dc@1", "telco-systems/xm8424-dc-header@1", "telco-systems/xm8424-dc-cable-plug@1",
               "telco-dc-block-2", "xm-8424h", 2),
}
RETIRED = ["telco-systems/xm3352-dc-plug", "telco-systems/xm8424-dc-plug"]


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


@pytest.mark.parametrize("case", CASES)
def test_the_key_is_registered_and_claims_no_maker_standard_or_pitch(case):
    supply, header, plug, key, device, cells = CASES[case]
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    note = reg[key]["note"]
    assert "standard" not in reg[key], "no document held names a standard"
    assert "unmated" not in reg[key], "a cable connector mates it"
    assert "claims none" in note and "no standard is held for it" in note
    for ref in (supply, header, plug):
        assert ref in note, ref
    assert "Telco Systems" in note and {3: "three", 2: "two"}[cells] in note


@pytest.mark.parametrize("case", CASES)
def test_the_header_is_an_inlet_and_the_plug_mates_it_at_the_same_point(case):
    supply, header, plug, key, device, cells = CASES[case]
    h, p = contract(header), contract(plug)
    assert (h["class"], h["interface"]) == ("inlet", key)
    assert (p["class"], p["mates"]) == ("port", key)
    assert h["connection-points"]["mate"]["at"] == p["connection-points"]["mate"]["at"]
    assert h["size"]["w"] == p["size"]["w"] and h["size"]["h"] == p["size"]["h"]
    for part in (h, p):
        assert part["size-confidence"]["w"] == part["size-confidence"]["h"] == "estimated"
    assert "STAND-IN" in h["provenance"]["part"] and "STAND-IN" in p["provenance"]["model"]
    assert len([k for k in p["connection-points"] if k.startswith("wire-")]) == cells


@pytest.mark.parametrize("case", CASES)
def test_the_supply_composes_the_header_inside_its_plate(case):
    supply, header, plug, key, device, cells = CASES[case]
    c = contract(supply)
    mine = [p for p in c["parts"] if p["ref"] == header]
    assert len(mine) == 1 and mine[0]["id"] == "dc-in"
    x, y = mine[0]["at"]
    hw, hh = contract(header)["size"]["w"], contract(header)["size"]["h"]
    assert 0 <= x and x + hw <= c["size"]["w"] and 0 <= y and y + hh <= c["size"]["h"]
    assert not [p for p in c["parts"] if "dc-plug" in p["ref"]], "the retired plug is not composed"
    assert c["version"] == "1.1.0"


@pytest.mark.parametrize("case", CASES)
def test_the_supply_states_its_roles_and_no_dc_port(case):
    supply, header, plug, key, device, cells = CASES[case]
    c = contract(supply)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"connector", "roles", "no-dc-port"} <= set(prov)
    assert "stand-in" in prov["connector"]


def test_the_xm3352_roles_follow_the_printed_marks_and_not_the_middle_cell():
    roles = contract(CASES["xm3352"][0])["provenance"]["roles"]
    for word in ("`neg`", "`pos`", "NOT MARKED"):
        assert word in roles, word


def test_the_xm8424_states_no_role_because_no_mark_is_legible():
    roles = contract(CASES["xm8424"][0])["provenance"]["roles"]
    assert "NOT STATED" in roles
    assert "`neg`" not in roles and "`pos`" not in roles and "`batt`" not in roles and "`rtn`" not in roles


def test_the_two_plugs_that_drew_the_block_are_gone_and_nothing_names_them():
    for ref in RETIRED:
        assert not (LIB / "components" / ref).exists(), ref
    for f in (LIB / "components").rglob("contract.yaml"):
        text = f.read_text()
        for ref in RETIRED:
            assert ref not in text, f"{f} still names {ref}"
    for ref in RETIRED:
        assert ref not in dx.PART_POWER


@pytest.mark.parametrize("case", CASES)
def test_the_exporter_still_types_the_connector_a_dc_terminal(case):
    assert dx.PART_POWER[CASES[case][1].split("@")[0]] == "dc-terminal"


@pytest.mark.parametrize("case", CASES)
def test_the_device_seats_the_supply_in_a_bay(case):
    supply, header, plug, key, device, cells = CASES[case]
    text = (LIB / "devices" / "telco-systems" / device / "device.yaml").read_text()
    assert re.search(r"accepts: \[[^\]]*'%s'" % re.escape(supply), text)


def test_the_records_of_the_two_supplies_are_gone_and_the_file_is_consistent():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    for case in CASES:
        assert (CASES[case][0], "C19") not in rows, case
    assert doc["cap"] == len(doc["rows"])


@pytest.mark.heavy
@pytest.mark.parametrize("case", CASES)
def test_the_index_lists_each_header_with_its_key_and_mate_point_and_each_plug_as_a_port(case, index):
    supply, header, plug, key, device, cells = CASES[case]
    assert (index[header]["class"], index[header]["interface"]) == ("inlet", key)
    assert index[header]["mate"] == contract(header)["connection-points"]["mate"]["at"]
    assert index[plug]["class"] == "port" and index[plug]["mate"] == contract(plug)["connection-points"]["mate"]["at"]

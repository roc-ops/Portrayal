"""The AC inlet of the Telco Systems XM-3352 supply and the DC feed header of the TM-7124S are places a cable lands.

Each part is drawn and composed already, and each presented no connector key, so neither supply or chassis offered a cable end:

  - the XM-3352 AC supply (`xm3352-psu-ac`) composes `xm3352-ac-inlet`, a cloverleaf appliance inlet with three round lobes in a dark
    surround. No document held names its standard, maker or part number, so its key `telco-ac-cloverleaf-3` claims none;
  - the TM-7124S chassis carries `tm-7124s-dc-feed`, a four-pole green pluggable screw-clamp header held by a screw above and below,
    legend `-48VA RETA -48VB RETB`. The registry already held the key `screw-terminal-4` for it; the part did not present it.

A cord connector (`xm3352-ac-cord-plug`) and a cable connector (`tm-7124s-dc-cable-plug`) mate them: each is a declared stand-in with an
estimated size. Neither part states a DC port, and each records the roles its marks give in its provenance.

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

pytestmark = pytest.mark.heavy

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# the connector part, its cable end, the key, the supply that composes it (none: the device places it) and the device
CASES = {
    "xm3352-ac": ("telco-systems/xm3352-ac-inlet@1", "telco-systems/xm3352-ac-cord-plug@1", "telco-ac-cloverleaf-3",
                  "telco-systems/xm3352-psu-ac@1", "xm-3352"),
    "tm7124s-dc": ("telco-systems/tm-7124s-dc-feed@1", "telco-systems/tm-7124s-dc-cable-plug@1", "screw-terminal-4",
                   None, "tm-7124s"),
}


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


def registry():
    return yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]


@pytest.mark.parametrize("case", CASES)
def test_the_key_is_registered_names_its_two_parts_and_claims_no_standard(case):
    header, plug, key, supply, device = CASES[case]
    entry = registry()[key]
    assert "standard" not in entry, "no document held names a standard"
    assert "unmated" not in entry, "a cable end mates it"
    note = entry["note"]
    for ref in (header, plug):
        assert ref in note, ref
    assert "Telco Systems" in note or "TM-7124S" in note


def test_the_ac_key_claims_no_maker_standard_or_pitch():
    note = registry()["telco-ac-cloverleaf-3"]["note"]
    assert "claims none" in note and "no standard is held for it" in note


@pytest.mark.parametrize("case", CASES)
def test_the_header_presents_the_key_and_the_plug_mates_it_at_the_same_point(case):
    header, plug, key, supply, device = CASES[case]
    h, p = contract(header), contract(plug)
    assert (h["class"], h["interface"]) == ("inlet", key)
    assert (p["class"], p["mates"]) == ("port", key)
    assert h["connection-points"]["mate"]["at"] == p["connection-points"]["mate"]["at"]
    assert h["size"]["w"] == p["size"]["w"] and h["size"]["h"] == p["size"]["h"]
    assert p["size-confidence"]["w"] == p["size-confidence"]["h"] == "estimated"
    assert "STAND-IN" in p["provenance"]["model"]


@pytest.mark.parametrize("case", CASES)
def test_only_this_plug_mates_the_key(case):
    header, plug, key, supply, device = CASES[case]
    mates = []
    for f in (LIB / "components").rglob("contract.yaml"):
        m = yaml.safe_load(f.read_text()).get("mates")
        if key in ([m] if isinstance(m, str) else (m or [])):
            mates.append(f.parent.parent.name)
    assert mates == [plug.split("/")[1].split("@")[0]]


def test_the_header_is_a_declared_stand_in_and_names_what_it_does_not_know():
    for case in CASES:
        prov = contract(CASES[case][0])["provenance"]
        assert "STAND-IN" in (prov.get("part") or prov["connector"]) and "gender" in prov, case


def test_the_ac_supply_composes_the_inlet_inside_its_plate():
    header, plug, key, supply, device = CASES["xm3352-ac"]
    c = contract(supply)
    mine = [p for p in c["parts"] if p["ref"] == header]
    assert len(mine) == 1 and mine[0]["id"] == "inlet"
    x, y = mine[0]["at"]
    hw, hh = contract(header)["size"]["w"], contract(header)["size"]["h"]
    assert 0 <= x and x + hw <= c["size"]["w"] and 0 <= y and y + hh <= c["size"]["h"]
    assert {"connector"} <= set(c["provenance"])
    assert "stand-in" in c["provenance"]["connector"]


def test_the_chassis_feed_says_its_roles_from_the_legend_and_states_no_dc_port():
    c = contract(CASES["tm7124s-dc"][0])
    assert "dc" not in c
    roles = c["provenance"]["roles"]
    for word in ("-48VA", "RETA", "-48VB", "RETB", "`batt`", "`rtn`", "NO DC PORT"):
        assert word in roles, word
    assert c["provenance"]["connector"]


def test_the_ac_supply_states_no_dc_port():
    assert "dc" not in contract(CASES["xm3352-ac"][3])


def test_the_exporter_types_both_connectors_as_before():
    assert dx.PART_POWER["telco-systems/xm3352-ac-inlet"] == "iec-60320-c6"
    assert dx.PART_POWER["telco-systems/tm-7124s-dc-feed"] == "dc-terminal"
    for case in CASES:
        assert CASES[case][1].split("@")[0] not in dx.PART_POWER, "a cable end is not a port of the device it is drawn on"


@pytest.mark.parametrize("case", CASES)
def test_the_device_places_the_part(case):
    header, plug, key, supply, device = CASES[case]
    text = (LIB / "devices" / "telco-systems" / device / "device.yaml").read_text()
    needle = supply if supply else header
    assert re.search(re.escape(needle), text), needle


def test_the_two_records_are_gone_and_the_file_is_consistent():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    assert ("telco-systems/xm3352-psu-ac@1", "C19") not in rows
    assert ("telco-systems/tm-7124s-dc-feed@1", "C20") not in rows
    assert doc["cap"] == len(doc["rows"])


@pytest.mark.parametrize("case", CASES)
def test_the_index_lists_each_header_with_its_key_and_mate_point_and_each_plug_as_a_port(case, index):
    header, plug, key, supply, device = CASES[case]
    assert (index[header]["class"], index[header]["interface"]) == ("inlet", key)
    assert index[header]["mate"] == contract(header)["connection-points"]["mate"]["at"]
    assert index[plug]["class"] == "port" and index[plug]["mate"] == contract(plug)["connection-points"]["mate"]["at"]

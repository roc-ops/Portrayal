"""The DC power connector of the Cisco NXA-PDC-930W supply is a place a cable lands.

The supply drew its inlet as a plain dark window, so it offered no cable end. It now composes a connector part, the
three-position DC power connector block of the Cisco N93108TC-FX3 hardware installation guide (a clip and three cells in a
column, printed "- DC", "+ DC" and an earth symbol), standing inside the window its skin already draws. The guide names no
maker or part number for the connector, so the key `cisco-dc-block-3` claims none, the header and the cable connector that
mates it are declared stand-ins, and the place and size are estimates; each contract says so.

  - the supply states the roles of the three contacts (`neg`, `pos`, `gnd`) in its provenance and states no DC port, because a
    port whose poles are the contacts of one pluggable connector is offered only where that part is itself the connector;
  - no skin is edited and the supply's description is unchanged;
  - the three devices that seat it take a patch, and the record for the supply is gone while the other rows of the issue stay.

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

SUPPLY = "cisco/nxa-pdc-930w@1"
HEADER, PLUG = "cisco/nxa-pdc-930w-dc-header@1", "cisco/nxa-pdc-930w-dc-plug@1"
KEY = "cisco-dc-block-3"
DEVICES = ["n9k-c93108tc-fx3", "n9k-c93180yc-fx3", "n9k-c93180yc-fx3s"]
STAY = ["cisco/a9k-1600w-dc@1", "cisco/nc57-1600w-dcfw@1", "cisco/nc5k-pdc-930w-bk@1",
        "cisco/nc5k-pdc-930w-fr@1", "cisco/nxa-pdc-1100w@1", "cisco/nxa-pdc-440w@1", "cisco/nxa-pdc-715w@1",
        "cisco/nxa-phv-350w@1", "cisco/pwr-1p6kw-dc@2"]


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


def test_the_key_is_registered_and_claims_no_maker():
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    note = reg[KEY]["note"]
    assert "standard" not in reg[KEY], "the guide names no standard"
    assert "claims none" in note and "NXA-PDC-930W" in note and PLUG in note and HEADER in note


def test_the_header_is_an_inlet_and_the_plug_mates_it_at_the_same_point():
    header, plug = contract(HEADER), contract(PLUG)
    assert (header["class"], header["interface"]) == ("inlet", KEY)
    assert (plug["class"], plug["mates"]) == ("port", KEY)
    assert header["connection-points"]["mate"]["at"] == plug["connection-points"]["mate"]["at"]
    assert header["size"] == plug["size"] == {"w": 9.0, "h": 16.0}
    for part in (header, plug):
        assert part["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "STAND-IN" in header["provenance"]["part"] and "STAND-IN" in plug["provenance"]["model"]


def test_the_supply_composes_the_header_inside_the_window_its_skin_draws():
    c = contract(SUPPLY)
    assert c["version"] == "1.1.0"
    (part,) = c["parts"]
    assert (part["ref"], part["id"]) == (HEADER, "dc-header")
    x, y = part["at"]
    w, h = contract(HEADER)["size"]["w"], contract(HEADER)["size"]["h"]
    svg = (path_of(SUPPLY) / "skins" / "default.svg").read_text()
    m = re.search(r'id="inlet-recess" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
    rx, ry, rw, rh = map(float, m.groups())
    assert rx <= x and x + w <= rx + rw and ry <= y and y + h <= ry + rh, "the part stands inside the drawn window"


def test_the_supply_states_the_roles_and_no_dc_port():
    c = contract(SUPPLY)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"connector", "roles", "no-dc-port"} <= set(prov)
    for word in ("`neg`", "`pos`", "`gnd`", "THE OTHER TWO GUIDES"):
        assert word in "".join(prov.values())


def test_the_description_and_the_skin_are_the_ones_on_main():
    c = contract(SUPPLY)
    assert c["description"].endswith("The face is drawn from its AC\nsibling and the inlet is a plain recess.") or \
        "plain recess" in c["description"]
    svg = (path_of(SUPPLY) / "skins" / "default.svg").read_text()
    assert 'id="inlet-surround"' in svg and 'id="inlet-recess"' in svg and "dc-header" not in svg


def test_the_exporter_names_the_header_as_a_plain_other_connector():
    assert dx.PART_POWER["cisco/nxa-pdc-930w-dc-header"] == "other"
    assert "3-position" in dx.POWER_LABEL["cisco/nxa-pdc-930w-dc-header"]


@pytest.mark.heavy
def test_the_index_lists_the_header_with_its_key_and_mate_point_and_the_plug_as_a_port(index):
    assert (index[HEADER]["class"], index[HEADER]["interface"], index[HEADER]["mate"]) == ("inlet", KEY, [5.3, 8.0])
    assert index[PLUG]["class"] == "port" and index[PLUG]["mate"] == [5.3, 8.0]
    assert index[SUPPLY]["version"] == "1.1.0"


def test_three_devices_seat_the_supply_and_no_others():
    seats = sorted(p.parent.name for p in (LIB / "devices" / "cisco").glob("*/layout.yaml")
                   if "cisco/nxa-pdc-930w@1" in p.read_text())
    assert seats == DEVICES


def test_the_record_of_the_supply_is_gone_and_the_others_of_the_issue_stay():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    assert (SUPPLY, "C19") not in rows
    for ref in STAY:
        assert (ref, "C19") in rows, ref
    assert doc["cap"] == len(doc["rows"])

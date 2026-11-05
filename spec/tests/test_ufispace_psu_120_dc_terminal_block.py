"""The DC input of the fixed 120 W UfiSpace supply is a place a cable lands, and says which terminal is which.

The 120 W DC fixed dual-feed supply of the S9502 family drew its three-screw terminal block as art, so a device that placed it
offered no place for a DC feed. It now composes three terminal screws, every one a seat that a ring lug lands on, and states
one DC input port whose three poles are those seats, with the roles the legend printed on the panel under the block gives,
left to right:

  - the supply composes common/terminal-screw-34@1 three times, as `pole-rtn`, `pole-batt` and `pole-gnd`;
  - that screw presents `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has one input port, `input`, with `rtn` on `pole-rtn`, `batt` on `pole-batt` and `gnd` on
    `pole-gnd`, the input current and cable size the datasheet and the guides give, no voltage, and the entries of
    `provenance` that its `source` names;
  - the terminal block's art, its element and its connection point are unchanged;
  - the S9502-16SMT places the supply twice, as its two fixed feeds, where it drew six panel posts, and the S9502-12SM
    places it as it did.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "ufispace/psu-120-dc@1"
SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"
POLES = [("rtn", "pole-rtn"), ("batt", "pole-batt"), ("gnd", "pole-gnd")]
# the centres of the clamp screws the skin draws (5.99, 15.48 and 24.96 across, 8.05 down), less the screw's own 1.7
SCREW_AT = [[4.29, 6.35], [13.78, 6.35], [23.26, 6.35]]
# the lift the supply's own relief gives the whole block (the datasheet's 14 mm of projection)
LIFT = 14.0


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(name):
    return yaml.safe_load((LIB / "devices" / "ufispace" / name / "device.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_supply_composes_three_terminal_screws_one_for_each_terminal():
    got = {q["id"]: (q["ref"], q["at"], q["lift"]) for q in contract(SUPPLY)["parts"]}
    want = {i: (SCREW, at, LIFT) for (_, i), at in zip(POLES, SCREW_AT)}
    assert got == want


def test_the_lift_is_the_block_s_own_relief():
    d = contract(SUPPLY)
    assert [f["out"] for f in d["relief"]["features"] if f["node"] == "terminal-block"] == [LIFT]


def test_the_terminal_block_is_still_drawn_and_no_id_of_the_supply_went():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ["terminal-block"]
    assert d["elements"]["terminal-block"]["class"] == "terminal"
    assert d["connection-points"]["power"] == {"at": [16.65, 8.0], "direction": "front"}
    assert d["size"] == {"w": 33.3, "h": 15.9}
    assert d["skins"] == ["default"]


def test_the_dc_port_is_one_input_with_the_legends_roles_on_the_three_screws():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES
    assert port["rating-a"] == 4.5
    assert port["awg"] == [18]
    assert "voltage" not in port


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "rating-a", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Figures 16 and 17" in d["provenance"][source["poles"]]


def test_the_build_publishes_three_seats_that_accept_the_ring_lug_and_one_dc_port(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for _, i in POLES]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES


@pytest.mark.parametrize("name", ["s9502-12sm", "s9502-16smt"])
def test_each_device_places_the_supply_twice_as_its_two_fixed_feeds(name):
    front = device(name)["views"]["front"]["components"]["placements"]
    got = [(p["id"], p["ref"]) for p in front if p["ref"] == SUPPLY]
    assert got == [("psu-0", SUPPLY), ("psu-1", SUPPLY)]


def test_the_s9502_16smt_draws_no_panel_posts_where_the_supplies_stand():
    decor = device("s9502-16smt")["views"]["front"]["panel"]["decor"]
    assert [d for d in decor if d.get("size") == [4.83, 11.0]] == []


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    closed = {(SUPPLY, "C19"), ("s9502-16smt", "C19"), ("s9502-12sm", "C20")}
    assert [(r["part"], r["code"]) for r in rows if (r["part"], r["code"]) in closed] == []

"""The DC inputs of the UfiSpace S9511-20CT are places a cable lands, and say which terminal is which.

The S9511-20CT has one fixed dual-feed DC supply and drew its two three-screw terminal blocks as panel art, so the device
offered no place for a DC feed. Each block is now a placement of one part, `ufispace/s9511-dc-input@1`, which composes three
terminal screws, every one a seat a ring lug lands on, and states one DC input port whose three poles are those seats, with
the roles the legend printed under each block gives, left to right:

  - the part composes common/terminal-screw-34@1 three times, as `pole-rtn`, `pole-batt` and `pole-gnd`;
  - that screw presents `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has one input port, `input`, with `rtn` on `pole-rtn`, `batt` on `pole-batt` and `gnd` on
    `pole-gnd`, the input current and cable size the datasheet and the guide give, no voltage, and the entries of
    `provenance` that its `source` names;
  - the device places the part twice, as `psu-0` and `psu-1`, where it drew six panel posts.

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

PART = "ufispace/s9511-dc-input@1"
SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"
POLES = [("rtn", "pole-rtn"), ("batt", "pole-batt"), ("gnd", "pole-gnd")]
LIFT = 12.0


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


def test_the_part_composes_three_terminal_screws_one_for_each_terminal():
    got = {q["id"]: (q["ref"], q["lift"]) for q in contract(PART)["parts"]}
    assert got == {i: (SCREW, LIFT) for _, i in POLES}


def test_the_lift_is_the_block_s_own_relief():
    d = contract(PART)
    assert [f["out"] for f in d["relief"]["features"] if f["node"] == "terminal-block"] == [LIFT]


def test_the_terminal_block_is_drawn_as_an_element_with_a_connection_point():
    d = contract(PART)
    assert sorted(d["elements"]) == ["terminal-block"]
    assert d["elements"]["terminal-block"]["class"] == "terminal"
    assert d["connection-points"]["power"]["direction"] == "front"
    assert d["skins"] == ["default"]


def test_the_dc_port_is_one_input_with_the_legends_roles_on_the_three_screws():
    ports = contract(PART)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES
    assert port["awg"] == [14]
    assert "voltage" not in port


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(PART)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "rating-a", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40


@pytest.mark.heavy
def test_the_build_publishes_three_seats_that_accept_the_ring_lug_and_one_dc_port(index):
    entry = index[PART]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for _, i in POLES]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES


def test_the_device_places_the_part_twice_as_its_two_fixed_feeds():
    front = device("s9511-20ct")["views"]["front"]["components"]["placements"]
    assert [(p["id"], p["ref"]) for p in front if p["ref"] == PART] == [("psu-0", PART), ("psu-1", PART)]


def test_the_device_draws_no_panel_posts_where_the_blocks_stand():
    decor = device("s9511-20ct")["views"]["front"]["panel"]["decor"]
    assert [d for d in decor if d.get("size") == [3.81, 12.0]] == []


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == "s9511-20ct"] == []

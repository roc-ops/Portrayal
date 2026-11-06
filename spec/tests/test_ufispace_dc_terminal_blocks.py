"""The DC input of three UfiSpace DC supplies is a place a cable lands, and says which terminal is which.

The PSU-401, PSU-201 and PSU-751 DC supplies drew their three-screw terminal block as art, so each offered no place for a
DC feed. Each now composes three terminal screws, every one a seat that a ring lug lands on, and states one DC input port whose
three poles are those seats, with the roles the vendor's guide prints under the three screws, left to right:

  - the supply composes common/terminal-screw-34@1 three times, as `pole-rtn`, `pole-batt` and `pole-gnd`;
  - that screw presents `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has one input port, `input`, with `rtn` on `pole-rtn`, `batt` on `pole-batt` and `gnd` on `pole-gnd`,
    the supply's input current and cable size, no voltage, and the entries of `provenance` that its `source` names;
  - the terminal block's art, its element and every other id of the supply are unchanged.

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

SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"
POLES = [("rtn", "pole-rtn"), ("batt", "pole-batt"), ("gnd", "pole-gnd")]

# supply -> where its three screws stand (the centres of the clamp screws its skin draws, less the screw's own 1.7), the input
# current its devices' datasheets give, the one cable size its guides give, and the figure that prints the legend
SUPPLIES = {
    "ufispace/psu-401-dc@1": dict(at=[[9.6, 27.5], [19.2, 27.5], [28.8, 27.5]], rating=16, awg=[14], figure="Figure 24"),
    "ufispace/psu-201-dc@1": dict(at=[[9.6, 27.5], [19.2, 27.5], [28.8, 27.5]], rating=8, awg=[14], figure="Figure 24"),
    "ufispace/psu-751-dc@1": dict(at=[[6.9, 25.4], [16.5, 25.4], [26.1, 25.4]], rating=28, awg=[10], figure="Figure 24"),
}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_the_supply_composes_three_terminal_screws_one_for_each_terminal(ref):
    got = {q["id"]: (q["ref"], q["at"], q["lift"]) for q in contract(ref)["parts"]}
    want = {i: (SCREW, at, 8.0) for (_, i), at in zip(POLES, SUPPLIES[ref]["at"])}
    assert got == want


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_the_terminal_block_is_still_drawn_and_no_id_of_the_supply_went(ref):
    d = contract(ref)
    assert sorted(d["elements"]) == ["handle", "latch", "status-led", "terminal-block"]
    assert d["elements"]["terminal-block"]["class"] == "inlet"
    assert d["connection-points"]["power"]["direction"] == "front"


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_the_dc_port_is_one_input_with_the_legends_roles_on_the_three_screws(ref):
    ports = contract(ref)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES
    assert port["rating-a"] == SUPPLIES[ref]["rating"]
    assert port["awg"] == SUPPLIES[ref]["awg"]
    assert "voltage" not in port


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from(ref):
    d = contract(ref)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "rating-a", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert SUPPLIES[ref]["figure"] in d["provenance"][source["poles"]]


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_the_build_publishes_three_seats_that_accept_the_ring_lug_and_one_dc_port(index, ref):
    entry = index[ref]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for _, i in POLES]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [(r["part"], r["code"]) for r in rows if r["part"] in SUPPLIES and r["code"] == "C19"] == []

"""The DC input of the UfiSpace PSU-132 DC supply is a place a cable lands, and says which terminal is which.

The supply used to draw its terminal block as art, so it offered no place for a DC feed. It now composes two terminal
screws, each a seat that a ring lug lands on, and states one DC input port whose two poles are those seats, with the roles
the vendor's guide prints under the two lugs:

  - ufispace/psu-132-dc@1 composes common/terminal-screw-34@1 twice, as `pole-neg` and `pole-pos`;
  - that screw presents `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has one input port, `input`, with `neg` on `pole-neg` and `pole-pos` carrying `pos`, and the
    entries of `provenance` that its `source` names;
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

SUPPLY = "ufispace/psu-132-dc@1"
SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_supply_composes_two_terminal_screws_one_for_each_pole():
    got = {q["id"]: (q["ref"], q["at"]) for q in contract(SUPPLY)["parts"]}
    assert got == {"pole-neg": (SCREW, [18.1, 20.9]), "pole-pos": (SCREW, [28.5, 20.9])}


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_terminal_block_is_still_drawn_and_no_id_of_the_supply_went():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ["handle", "latch", "status-led", "terminal-block"]
    assert d["elements"]["terminal-block"]["class"] == "inlet"


def test_the_dc_port_is_one_input_with_the_legends_signs_on_the_two_screws():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("neg", "pole-neg"), ("pos", "pole-pos")]
    assert port["rating-a"] == 40


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "rating-a"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Figure 32" in d["provenance"][source["poles"]]


def test_the_build_publishes_two_seats_that_accept_the_ring_lug_and_one_dc_port(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        ("pole-neg", "connector", "terminal-stud", [LUG]), ("pole-pos", "connector", "terminal-stud", [LUG])]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("neg", "pole-neg"), ("pos", "pole-pos")]


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY and r["code"] == "C19"] == []

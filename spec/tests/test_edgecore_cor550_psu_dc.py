"""The DC input of the Edgecore COR550 DC supply is a place a cable lands, and says which terminal is which.

The supply used to draw its two-screw terminal block as art, so it offered no place for a DC feed. It now composes two terminal
screws, each a seat that a ring lug lands on, and states one DC input port whose two poles are those seats, with the roles the
vendor's quick start guide calls out beside the two screws:

  - edgecore/cor550-psu-dc@1 composes common/terminal-screw-34@1 twice, as `pole-rtn` and `pole-batt`;
  - that screw presents `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has one input port, `input`, with `rtn` on `pole-rtn` and `batt` on `pole-batt`, the rating and the
    wire size the guide gives, no voltage and no earth pole, and the entries of `provenance` that its `source` names;
  - the terminal block's art, its element, the three hex fasteners and every other id of the supply are unchanged.

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

SUPPLY = "edgecore/cor550-psu-dc@1"
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


def test_the_supply_composes_two_terminal_screws_one_for_each_pole_and_keeps_its_hex_fasteners():
    got = {q["id"]: (q["ref"], q["at"]) for q in contract(SUPPLY)["parts"]}
    assert got["pole-rtn"] == (SCREW, [7.9, 26.3])
    assert got["pole-batt"] == (SCREW, [20.3, 26.3])
    assert sorted(i for i in got if i.startswith("hex-stud")) == ["hex-stud-1", "hex-stud-2", "hex-stud-3"]
    assert len(got) == 5


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_terminal_block_is_still_drawn_and_no_id_of_the_supply_went():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ["handle", "latch", "logo-zone", "terminal", "vent"]
    assert d["elements"]["terminal"]["class"] == "terminal"


def test_the_dc_port_is_one_input_with_the_two_callouts_on_the_two_screws_and_no_earth_pole():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("rtn", "pole-rtn"), ("batt", "pole-batt")]
    assert (port["rating-a"], port["awg"]) == (40, [10])
    assert "voltage" not in port


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "rating-a", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Connect Power" in d["provenance"][source["poles"]]


def test_the_build_publishes_two_seats_that_accept_the_ring_lug_and_one_dc_port(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        ("pole-rtn", "connector", "terminal-stud", [LUG]), ("pole-batt", "connector", "terminal-stud", [LUG])]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("rtn", "pole-rtn"), ("batt", "pole-batt")]


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY and r["code"] == "C19"] == []

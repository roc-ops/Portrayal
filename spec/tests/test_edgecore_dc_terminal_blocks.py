"""The DC input of the Edgecore CSR310 and DCS500 DC supplies is a place a cable lands, earth terminal included.

Each supply used to draw its three-screw barrier block as art, so it offered no place for a DC feed. Each now composes three
terminal screws, each a seat that a ring lug lands on, and states one DC input port whose three poles are those seats, with the
roles the vendor's quick start guide calls out beside the three screws: the ground wire (the earth terminal, a pole of the port
like the other two), the negative voltage range and the DC return:

  - edgecore/csr310-psu-dc@1 (the supply of the CSR310 and the CSR430) and edgecore/dcs500-psu-dc@1 each compose
    common/terminal-screw-34@1 three times, as `pole-gnd`, `pole-batt` and `pole-rtn`;
  - that screw presents `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has one input port, `input`, with the three roles the guide calls out, in the order the guide lists
    them, the wire size the guide gives, no voltage, no current (the documents disagree, or give a pair of currents) and the
    entries of `provenance` that its `source` names;
  - the terminal block's art, its elements and every other id of each supply are unchanged; the CSR310 supply's skin is regrouped
    (the block's drawing in one group) and not redrawn.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"

# supply -> (the screws as (id, at, role), in the order of the port's poles; the element names; the wire sizes)
SUPPLIES = {
    "edgecore/csr310-psu-dc@1": dict(
        screws=[("pole-gnd", [12.2, 25.2], "gnd"), ("pole-batt", [20.8, 25.2], "batt"), ("pole-rtn", [29.6, 25.2], "rtn")],
        lift=9.5, elements=["handle", "inlet", "latch"], awg=[14], version="1.1.0"),
    "edgecore/dcs500-psu-dc@1": dict(
        screws=[("pole-rtn", [13.1, 27.7], "rtn"), ("pole-batt", [13.1, 19.3], "batt"), ("pole-gnd", [13.1, 10.0], "gnd")],
        lift=5.0, elements=["handle", "latch", "pole-1", "pole-2", "pole-3", "terminal", "vent"], awg=[10], version="1.1.0"),
}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_composes_three_terminal_screws_one_for_each_pole_and_nothing_else(ref):
    want = SUPPLIES[ref]
    parts = contract(ref)["parts"]
    assert [(q["ref"], q["id"], q["at"], q["lift"]) for q in parts] == [
        (SCREW, i, at, want["lift"]) for i, at, _ in want["screws"]]


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_terminal_block_is_still_drawn_and_no_id_of_the_supply_went(ref):
    d = contract(ref)
    assert sorted(d["elements"]) == SUPPLIES[ref]["elements"]
    assert d["version"] == SUPPLIES[ref]["version"]
    assert d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["input"] == "dc"


def test_the_csr310_supplys_block_is_drawn_in_one_group_so_the_raised_plate_stays_under_its_drawing():
    """A supply that composes parts has its raised nodes moved to the end of its group, and the `inlet` plate was a rect beside the
    drawing on it: raised, it painted over the lips, plates and screws. In one group the plate keeps its place under them."""
    ns = "{http://www.w3.org/2000/svg}"
    root = ET.parse(LIB / "components/edgecore/csr310-psu-dc/v1/skins/default.svg").getroot()
    block = next(e for e in root if e.get("id") == "block")
    assert {e.get("id") for e in block.iter()} >= {"inlet", "block-lip-top", "block-lip-bottom", "block-mid", "poles", "screws", "slots"}
    assert "inlet" not in {e.get("id") for e in root}
    assert [e.get("id") for e in root if e.tag == f"{ns}g"] == ["warnings", "block", "pole-labels", "silkscreen"]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_dc_port_is_one_input_with_the_three_callouts_and_the_earth_is_its_third_kind_of_pole(ref):
    want = SUPPLIES[ref]
    ports = contract(ref)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [(role, i) for i, _, role in want["screws"]]
    assert sorted(q["role"] for q in port["poles"]) == ["batt", "gnd", "rtn"]
    assert port["awg"] == want["awg"]
    assert "voltage" not in port
    assert "rating-a" not in port


@pytest.mark.parametrize("ref", SUPPLIES)
def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from(ref):
    d = contract(ref)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Connect Power" in d["provenance"][source["poles"]]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_missing_current_is_said_not_left_out_silently(ref):
    text = " ".join(contract(ref)["provenance"]["rating"].split())
    assert text.startswith("NOT STATED") and "`rating-a`" in text


def test_the_csr310_supply_says_the_documents_disagree_on_the_signs_and_on_the_current():
    p = contract("edgecore/csr310-psu-dc@1")["provenance"]
    poles, rating = " ".join(p["poles"].split()), " ".join(p["rating"].split())
    assert "not read" in poles and "Input+" in poles and "Input-" in poles
    for figure in ("10 A", "15.5-9.6 A", "8.4-4.2 A"):
        assert figure in rating


def test_the_dcs500_supply_says_its_poles_sit_on_the_screws_by_an_inferred_half_turn():
    poles = " ".join(contract("edgecore/dcs500-psu-dc@1")["provenance"]["poles"].split())
    assert "half turn" in poles and "inference" in poles and "28-14 A" in " ".join(
        contract("edgecore/dcs500-psu-dc@1")["provenance"]["rating"].split())


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_build_publishes_three_seats_that_accept_the_ring_lug_and_one_dc_port(index, ref):
    want = SUPPLIES[ref]
    entry = index[ref]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _, _ in want["screws"]]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [(role, i) for i, _, role in want["screws"]]


def test_the_findings_this_change_closes_have_no_row_left_and_the_ac_supply_of_the_dcs500_keeps_its_own():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    for ref in SUPPLIES:
        assert [r for r in rows if r["part"] == ref and r["code"] == "C19"] == []
    assert len([r for r in rows if r["part"] == "edgecore/dcs500-psu-ac@1" and r["code"] == "C19"]) == 1

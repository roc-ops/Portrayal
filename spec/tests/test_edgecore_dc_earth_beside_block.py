"""The DC input of four Edgecore DC supplies is a place a cable lands, and their earth screw or stud is a place a lug lands.

Each supply used to draw its two-screw terminal block as art, so it offered no place for a DC feed. Each now composes two
terminal screws, each a seat that a ring lug lands on, and states one DC input port whose two poles are those seats, with the
roles the vendor's quick start guide calls out beside the two screws: the negative voltage range and the DC return. The earth
terminal of these four stands beside the block, not on it, so it is not a pole of the port: it is a ground part of its own, also
a seat a lug lands on, outside the port (decided 2026-11-02; the supplies whose earth screw is on the block keep it as a third pole):

  - edgecore/agr-psu-dc@1, edgecore/fsj033-610g@1, edgecore/ais800-psu-dc@2 and edgecore/csr440-psu-dc@1 each compose
    common/terminal-screw-34@1 twice, as `pole-rtn` and `pole-batt` (in the callouts' order), and one ground part;
  - the ground part is a declared stand-in, because no document held gives the thread of an earth screw or stud: the library's
    common/ground-screw@1 (a screw that claims no stud size) or common/ground-stud@1;
  - the contract's `dc` block has one input port, `input`, with the two roles the guide calls out, the wire size and the current
    where one figure is given, no voltage, and the entries of `provenance` that its `source` names;
  - the terminal block's art, its elements and every other id of each supply are unchanged.

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

# supply -> the two screws as (id, at, role) in the order of the port's poles, their lift, the ground part as (ref, id, at, lift or
# None), the element names, the port's figures (awg, rating-a or None), the contract version and the provenance entries its `source` names
SUPPLIES = {
    "edgecore/agr-psu-dc@1": dict(
        screws=[("pole-rtn", [20.6, 17.05], "rtn"), ("pole-batt", [34.0, 17.05], "batt")], lift=6.35,
        earth=("common/ground-screw@1", "earth", [45.6, 1.6], None), elements=None, awg=[8], rating=40, version="1.1.0"),
    "edgecore/fsj033-610g@1": dict(
        screws=[("pole-rtn", [19.8, 16.3], "rtn"), ("pole-batt", [29.3, 16.3], "batt")], lift=9.5,
        earth=("common/ground-screw@1", "ground-stud", [41.4, 11.2], None), elements=["handle", "latch", "terminal"],
        awg=None, rating=40, version="1.1.0"),
    "edgecore/ais800-psu-dc@2": dict(
        screws=[("pole-batt", [9.06, 23.19], "batt"), ("pole-rtn", [25.51, 23.19], "rtn")], lift=None,
        earth=("common/ground-screw@1", "earth", [4.04, 5.56], None),
        elements=["ground", "handle", "latch", "status", "terminal", "vent-field", "vent-top"], awg=[6], rating=53, version="2.1.0"),
    "edgecore/csr440-psu-dc@1": dict(
        screws=[("pole-batt", [30.5, 22.3], "batt"), ("pole-rtn", [40.0, 22.3], "rtn")], lift=9.5,
        earth=("common/ground-stud@1", "earth", [8.65, 23.95], 3.0),
        elements=["ground-stud", "handle", "latch", "terminal", "vent-field"], awg=[14], rating=None, version="1.1.0"),
}
DCS240 = "edgecore/dcs240-psu-dc@1"


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def wanted_parts(want):
    ref, ident, at, lift = want["earth"]
    parts = [dict(ref=SCREW, id=i, at=at_, **({"lift": want["lift"]} if want["lift"] else {})) for i, at_, _ in want["screws"]]
    parts.append(dict(ref=ref, id=ident, at=at, **({"lift": lift} if lift else {})))
    return parts


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_composes_two_terminal_screws_and_one_ground_part_and_nothing_else(ref):
    assert contract(ref)["parts"] == wanted_parts(SUPPLIES[ref])


def test_the_screw_and_the_ground_parts_present_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"
    for ref in {w["earth"][0] for w in SUPPLIES.values()}:
        assert contract(ref)["interface"] == "terminal-stud"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_terminal_block_is_still_drawn_and_no_id_of_the_supply_went(ref):
    d = contract(ref)
    assert d["version"] == SUPPLIES[ref]["version"]
    assert d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["input"] == "dc"
    if SUPPLIES[ref]["elements"] is not None:
        assert sorted(d["elements"]) == SUPPLIES[ref]["elements"]


def test_the_cor580_supply_keeps_the_id_of_its_ground_part_and_the_part_that_took_no_lug_is_gone():
    parts = {p["id"]: p["ref"] for p in contract("edgecore/fsj033-610g@1")["parts"]}
    assert parts["ground-stud"] == "common/ground-screw@1"
    assert "common/screw-head@1" not in parts.values()


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_dc_port_is_one_input_with_two_poles_and_the_earth_is_not_one_of_them(ref):
    want = SUPPLIES[ref]
    ports = contract(ref)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [(role, i) for i, _, role in want["screws"]]
    assert sorted(q["role"] for q in port["poles"]) == ["batt", "rtn"]
    assert want["earth"][1] not in [q["slot"] for q in port["poles"]]
    assert port.get("awg") == want["awg"]
    assert port.get("rating-a") == want["rating"]
    assert "voltage" not in port


@pytest.mark.parametrize("ref", SUPPLIES)
def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from(ref):
    d = contract(ref)
    want = {"poles": "poles"}
    if SUPPLIES[ref]["rating"] is not None:
        want["rating-a"] = "rating"
    if SUPPLIES[ref]["awg"] is not None:
        want["awg"] = "awg"
    source = d["dc"]["ports"][0]["source"]
    assert source == want
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Connect Power" in d["provenance"][source["poles"]]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_earth_is_declared_a_stand_in_and_said_to_be_outside_the_port(ref):
    text = words(contract(ref)["provenance"]["earth"])
    assert text.startswith("A DECLARED STAND-IN")
    assert "outside the DC port" in text and "decided 2026-11-02" in text and "no document held gives" in text


def test_the_csr440_supply_says_why_it_states_no_current_and_which_signs_it_does_not_read():
    p = contract("edgecore/csr440-psu-dc@1")["provenance"]
    assert words(p["rating"]).startswith("NOT STATED") and "15.5-9.6 A" in p["rating"]
    poles = words(p["poles"])
    assert "Input+" in poles and "Input-" in poles and "recorded and not read" in poles


def test_the_ais800_supply_reads_the_first_figure_only():
    poles = words(contract("edgecore/ais800-psu-dc@2")["provenance"]["poles"])
    assert "first figure" in poles and "another module and is not read" in poles


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_build_publishes_a_seat_for_each_screw_and_the_earth_and_one_dc_port_of_two_poles(index, ref):
    want = SUPPLIES[ref]
    entry = index[ref]
    seats = [i for i, _, _ in want["screws"]] + [want["earth"][1]]
    got = {c["id"]: (c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]}
    assert sorted(got) == sorted(seats)
    assert all(v == ("connector", "terminal-stud", [LUG]) for v in got.values())
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [(role, i) for i, _, role in want["screws"]]


def test_the_dcs240_supply_is_not_part_of_this_change_and_has_a_module_of_its_own():
    d = contract(DCS240)
    assert d["version"] == "1.3.0" and "dc" in d and "parts" in d
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == DCS240 and r["code"] == "C19"] == []


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    for ref in SUPPLIES:
        assert [r for r in rows if r["part"] == ref and r["code"] == "C19"] == []

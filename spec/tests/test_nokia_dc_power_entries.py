"""The DC power entries of the Nokia SR-e supply and the SR-7 PEM-3 are places a lug lands, and say which terminal is which.

Both parts drew their terminals as art in the skin, so neither offered a place for a DC feed. Each now composes its terminals as
seats, and states one DC input port whose poles are those seats:

  - nokia/sr-e-psu-dc@1 composes two terminal screws, `pole-rtn` (the left one, printed "+") and `pole-batt` (the right one,
    printed "-"), and an M4 earth screw, `earth`, beside the block, a ground seat outside the port;
  - nokia/sr-7-pem-3@1 composes two poles of two studs each, `pole-batt` (-48) and `pole-rtn` (RTN), as nokia/sr-7-dc-pole@1,
    a pair a single two-hole lug lands across, and states a current;
  - every seat presents a registered interface that a part of the library mates, and the drawings' ids and boxes are unchanged.

These run against the real library, a components index built by the indexer the build runs, the registry and the records file.
They read no library/dist and render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec" / "schemas"

SCREW = "common/terminal-screw-38@1"
EARTH = "common/ground-screw-m4@1"
STUD = "common/terminal-screw-34@1"
POLE = "nokia/sr-7-dc-pole@1"
RING_LUG = "generic/ring-lug@1"
TWO_HOLE_LUG = "generic/two-hole-lug-5-8@1"
SRE = "nokia/sr-e-psu-dc@1"
PEM = "nokia/sr-7-pem-3@1"


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def parts(ref):
    return {q["id"]: q for q in contract(ref)["parts"]}


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_interfaces_are_registered_and_the_library_mates_them():
    registry = yaml.safe_load((SCHEMAS / "connectors.yaml").read_text())["interfaces"]
    assert "terminal-stud" in registry and "stud-pair-5-8" in registry
    assert contract(RING_LUG)["mates"] == "terminal-stud"
    assert contract(TWO_HOLE_LUG)["mates"] == "stud-pair-5-8"
    for ref in (SCREW, EARTH, STUD):
        assert contract(ref)["interface"] == "terminal-stud"
    assert contract(POLE)["interface"] == "stud-pair-5-8"


def test_the_sr_e_supply_composes_a_screw_for_each_terminal_and_one_for_the_earth():
    got = {i: (q["ref"], q["at"], q.get("lift")) for i, q in parts(SRE).items() if i != "led-status"}
    assert got == {
        "pole-rtn": (SCREW, [51.9, 23.6], 6.0),
        "pole-batt": (SCREW, [65.1, 23.6], 6.0),
        "earth": (EARTH, [44.2, 6.5], None),
    }


def test_the_sr_e_port_is_one_input_and_the_earth_screw_is_not_one_of_its_poles():
    ports = contract(SRE)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("rtn", "pole-rtn"), ("batt", "pole-batt")]
    assert port["awg"] == [8]
    assert "voltage" not in port and "rating-a" not in port


def test_every_fact_the_sr_e_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SRE)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Table 65" in d["provenance"]["poles"] and "Figure 39" in d["provenance"]["poles"]


def test_the_sr_e_supply_keeps_its_drawing_and_every_id():
    d = contract(SRE)
    assert sorted(d["elements"]) == ["dc-terminal", "fan", "ground", "handle", "latch"]
    assert d["elements"]["dc-terminal"]["class"] == "terminal"
    assert sorted(d["connection-points"]) == ["mate", "power"]
    assert "led-status" in parts(SRE)


def test_the_sr_7_pole_is_a_pair_of_studs_on_the_lug_pitch_and_says_the_pitch_is_inferred():
    d = contract(POLE)
    assert d["interface"] == "stud-pair-5-8"
    studs = [(q["ref"], q["at"]) for q in d["parts"]]
    assert studs == [(STUD, [0, 0]), (STUD, [15.875, 0])]
    assert "THE PITCH IS INFERRED, NOT STATED" in d["provenance"]["pitch"]
    assert "1/4-20" in d["provenance"]["thread"]


def test_the_sr_7_pem_composes_one_pole_for_the_minus_48_studs_and_one_for_the_return():
    got = {i: (q["ref"], q["at"]) for i, q in parts(PEM).items()}
    assert got == {"pole-batt": (POLE, [46.95, 10.43]), "pole-rtn": (POLE, [46.95, 29.06])}


def test_the_sr_7_port_is_one_input_at_the_guides_current_with_no_nominal_and_no_wire_size():
    d = contract(PEM)
    ports = d["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("batt", "pole-batt"), ("rtn", "pole-rtn")]
    assert port["rating-a"] == 100
    assert "voltage" not in port and "awg" not in port
    for key in port["source"].values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40


def test_the_sr_7_pem_keeps_its_drawing_and_every_id():
    d = contract(PEM)
    assert sorted(d["elements"]) == [
        "breaker", "captive-screw-left", "captive-screw-right", "cover-screw-bottom", "cover-screw-top",
        "handle", "logo-zone", "terminal-cover", "terminal-neg", "terminal-rtn"]
    assert sorted(d["connection-points"]) == ["feed", "mate"]
    assert "mirrored-in-bay-2" in d["provenance"]


def test_the_build_publishes_the_sr_e_seats_and_one_dc_port(index):
    entry = index[SRE]
    seats = {c["id"]: (c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]}
    for i in ("pole-rtn", "pole-batt", "earth"):
        assert seats[i] == ("connector", "terminal-stud", [RING_LUG])
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("rtn", "pole-rtn"), ("batt", "pole-batt")]


def test_the_build_publishes_the_sr_7_poles_as_pairs_a_two_hole_lug_lands_across(index):
    entry = index[PEM]
    seats = {c["id"]: (c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]}
    for i in ("pole-batt", "pole-rtn"):
        assert seats[i] == ("connector", "stud-pair-5-8", [TWO_HOLE_LUG])
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"], port["rating-a"]) == ("input", "input", 100)
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("batt", "pole-batt"), ("rtn", "pole-rtn")]


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    have = {(r["part"], r["code"]) for r in rows}
    assert (SRE, "C19") not in have
    assert ("sr-7", "C19") not in have

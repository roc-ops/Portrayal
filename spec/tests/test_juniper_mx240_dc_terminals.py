"""The DC power entry of the MX240 and MX480 normal-capacity supply is a place two lugs land, and says which terminal is which.

juniper/mx240-psu-dc@1 drew its four terminal studs as art in the skin, so it offered no place for a DC feed. It now composes
two poles, `pole-rtn` (the left column, printed RTN) and `pole-batt` (the right column, printed -48V), each a
juniper/mx240-dc-pole@1: a pair of studs on the 5/8 in. pitch of the two-hole lug the guide dimensions, which one lug lands
across, and states one DC input port whose poles are those seats:

  - the pole is a registered `stud-pair-5-8` that generic/two-hole-lug-5-8@1 mates, built of two terminal screws 15.875 apart;
  - each seat stands where the midpoint of the two studs its column draws stands, and the drawing's ids and boxes are unchanged;
  - the port is one input at the guide's nominal, with the wire size and no current (the guide prints two).

These run against the real library, a components index built by the indexer the build runs, the registry and the records file.
They read no library/dist and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec" / "schemas"

SCREW = "common/terminal-screw-34@1"
POLE = "juniper/mx240-dc-pole@1"
TWO_HOLE_LUG = "generic/two-hole-lug-5-8@1"
PSU = "juniper/mx240-psu-dc@1"
DEVICES = ("mx240", "mx480")


def folder(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((folder(ref) / "contract.yaml").read_text())


def parts(ref):
    return {q["id"]: q for q in contract(ref)["parts"]}


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def drawn_studs():
    """The centres of the four studs the supply's skin draws, by id."""
    svg = (folder(PSU) / "skins" / "default.svg").read_text()
    return {m.group(1): (float(m.group(2)), float(m.group(3)))
            for m in re.finditer(r'<g id="(stud-\d)"><circle cx="([\d.]+)" cy="([\d.]+)"', svg)}


def test_the_interface_is_registered_and_the_library_mates_it():
    registry = yaml.safe_load((SCHEMAS / "connectors.yaml").read_text())["interfaces"]
    assert "stud-pair-5-8" in registry
    assert contract(TWO_HOLE_LUG)["mates"] == "stud-pair-5-8"
    assert contract(POLE)["interface"] == "stud-pair-5-8"
    assert contract(SCREW)["interface"] == "terminal-stud"


def test_the_pole_is_a_pair_of_studs_on_the_lug_pitch_and_says_what_is_the_lugs_and_what_is_not_held():
    d = contract(POLE)
    studs = [(q["ref"], q["at"], q["lift"]) for q in d["parts"]]
    assert studs == [(SCREW, [0, 0], 9.4), (SCREW, [15.875, 0], 9.4)]
    assert d["size"] == {"w": 19.275, "h": 3.4}
    assert d["connection-points"]["mate"]["at"] == [9.6375, 1.7]
    assert d["connection-points"]["mate"]["seat-out"] == pytest.approx(9.4 + 1.2)
    text = d["provenance"]
    assert "THE PITCH IS THE LUG'S, NOT THE STUDS'" in text["pitch"] and "Figure 22" in text["pitch"]
    assert "NOT CLAIMED" in text["thread"]
    assert "THE LUG IS DRAWN, NOT NAMED" in text["lug"]


def test_the_supply_composes_one_pole_for_the_return_and_one_for_the_minus_48_turned_down_the_face():
    got = {i: (q["ref"], q["at"], q.get("rotate")) for i, q in parts(PSU).items()}
    assert got == {
        "pole-rtn": (POLE, [3.3625, 51.8], 90),
        "pole-batt": (POLE, [18.3625, 51.8], 90),
    }
    assert contract(PSU)["version"] == "1.1.0"


@pytest.mark.heavy
def test_each_seat_stands_on_the_midpoint_of_the_two_studs_its_column_draws(index):
    studs = drawn_studs()
    assert sorted(studs) == ["stud-0", "stud-1", "stud-2", "stud-3"]
    middle = {"pole-rtn": ("stud-0", "stud-2"), "pole-batt": ("stud-1", "stud-3")}
    seats = {c["id"]: c for c in index[PSU]["cages"]}
    for pole, (top, bottom) in middle.items():
        want = ((studs[top][0] + studs[bottom][0]) / 2, (studs[top][1] + studs[bottom][1]) / 2)
        assert seats[pole]["mate"] == pytest.approx(want, abs=0.01), pole
        # the studs of a column stand one above the other, so the pair runs down the face
        assert studs[top][0] == studs[bottom][0] and seats[pole]["rotate"] == 90


def test_the_port_is_one_input_at_the_nominal_with_the_wire_size_and_no_current():
    d = contract(PSU)
    ports = d["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("rtn", "pole-rtn"), ("batt", "pole-batt")]
    assert port["voltage"] == {"nominal": -48, "range": [-40.5, -72]}
    assert port["awg"] == [6]
    assert "rating-a" not in port


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(PSU)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "voltage", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Table 23" in d["provenance"]["voltage"] and "Nominal: -48 VDC" in d["provenance"]["voltage"]
    assert d["provenance"]["rating"].startswith("NOT STATED")
    assert "Figure 22" in d["provenance"]["seats"] and "Figure 19" in d["provenance"]["seats"]


def test_the_supply_keeps_its_drawing_and_every_id():
    d = contract(PSU)
    assert sorted(d["elements"]) == ["breaker", "handle", "terminals"]
    assert d["elements"]["terminals"]["class"] == "terminal"
    assert [f["node"] for f in d["relief"]["features"]] == [
        "handle", "breaker", "terminals", "stud-0", "stud-1", "stud-2", "stud-3"]
    assert "connection-points" not in d
    assert drawn_studs() == {"stud-0": (13.0, 47.0), "stud-1": (28.0, 47.0),
                             "stud-2": (13.0, 60.0), "stud-3": (28.0, 60.0)}
    assert d["size"] == {"w": 101.5, "h": 79.7}


@pytest.mark.heavy
def test_the_build_publishes_the_two_poles_as_pairs_a_two_hole_lug_lands_across(index):
    entry = index[PSU]
    seats = {c["id"]: (c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]}
    for i in ("pole-rtn", "pole-batt"):
        assert seats[i] == ("connector", "stud-pair-5-8", [TWO_HOLE_LUG])
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"], port["awg"]) == ("input", "input", [6])
    assert port["voltage"]["nominal"] == -48 and port["rating-a"] is None
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("rtn", "pole-rtn"), ("batt", "pole-batt")]


def test_only_the_mx240_and_the_mx480_seat_the_supply():
    seated = sorted(p.parent.name for p in (LIB / "devices" / "juniper").glob("*/device.yaml")
                    if PSU in p.read_text())
    assert seated == sorted(DEVICES)


def test_the_finding_this_change_closes_has_no_row_left_and_the_others_keep_theirs():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    have = {(r["part"], r["code"]) for r in rows}
    assert (PSU, "C19") not in have
    # what this change leaves for later is still recorded
    for stays in (("juniper/mx304-psu-dc@1", "C19"), ("juniper/qfx10000-pwr-dc@1", "C19"),
                  ("juniper/qfx5230-jnp-2400w-dc-afi@1", "C19"), ("juniper/qfx5230-jnp-3000w-dc-afo@1", "C19"),
                  ("juniper/mx240-psu-ac@1", "C19"), ("juniper/mx960-psu-ac@1", "C19")):
        assert stays in have, stays

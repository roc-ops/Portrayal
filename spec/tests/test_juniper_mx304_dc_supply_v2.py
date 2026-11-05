"""The Juniper MX304 DC supply is redrawn from its guide as version 2, and its input is a place two lugs land.

The supply's drawn face did not match the guide's figures. Version 1 drew two studs 11 mm apart on a flat black plate; the guide's
figures show a raised terminal block with four studs under four nuts, -48V/-60V at the left and RTN to its right, and the guide's
cable lug (LCD6-14A-L) has two holes 0.63 in. apart, so each of the two terminals takes one two-hole lug across a pair of studs. A
redraw that moves the drawn boxes is a new major, so the supply is `juniper/mx304-psu-dc@2` and the @1 stays as it was,
`superseded-by` the @2. The @2:

  - composes `juniper/mx240-dc-pole@1` twice, as `pole-batt` (the -48V/-60V terminal, the left pair of studs) and `pole-rtn` (the
    RTN terminal, the right pair), each a pair of studs on 5/8 in. centres that one two-hole lug lands across, turned a quarter
    so the pair runs down the face, at the midpoint of the two studs its skin draws in that column;
  - states one DC input port, `input`, of those two poles in that order, the wire size the guide gives and the current the
    guide's electrical table gives for the supply, and no voltage, because the guide prints two nominals;
  - is seated by the MX304's DC configuration, whose supply bays accept both majors, so a saved rack that seated the @1 still opens.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

NAME = "juniper/mx304-psu-dc"
SUPPLY = f"{NAME}@2"
OLD = f"{NAME}@1"
POLE = "juniper/mx240-dc-pole@1"
SCREW = "common/terminal-screw-34@1"
LUG = "generic/two-hole-lug-5-8@1"
RING = "generic/ring-lug@1"
# the poles as (id, role, [two stud centres across, down]) on the 66.0 x 40.1 face, left to right as the figures print them
POLES = [("pole-batt", "batt", [[41.0, 14.56], [41.0, 30.44]]), ("pole-rtn", "rtn", [[56.7, 14.56], [56.7, 30.44]])]
PITCH = 15.875
DEVICE = "mx304"
V1_SKIN_SHA256 = "f5e8e2720b5dd020cd280f44c66ff6c8ff911401089555d62b95247025e3d2b5"


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


def test_the_supply_is_a_new_major_and_the_old_one_is_kept_and_points_to_it():
    v1, v2 = contract(OLD), contract(SUPPLY)
    assert v2["version"] == "2.0.0" and v2["name"] == "mx304-psu-dc"
    assert v1["version"] == "1.0.2" and v1["superseded-by"] == SUPPLY
    assert "dc" not in v1 and "parts" not in v1 and sorted(v1["elements"]) == ["handle", "terminals"]


def test_the_old_skin_is_kept_byte_for_byte():
    skin = (LIB / "components" / NAME / "v1/skins/default.svg").read_bytes()
    assert hashlib.sha256(skin).hexdigest() == V1_SKIN_SHA256


def test_the_supply_composes_two_poles_and_nothing_else():
    parts = contract(SUPPLY)["parts"]
    assert [(p["ref"], p["id"], p["rotate"]) for p in parts] == [(POLE, i, 90) for i, _, _ in POLES]


def test_the_pole_part_presents_the_pair_key_and_the_two_hole_lug_mates_it():
    pole = contract(POLE)
    assert pole["interface"] == "stud-pair-5-8"
    assert [(p["ref"], p["at"][0]) for p in pole["parts"]] == [(SCREW, 0), (SCREW, PITCH)]
    assert contract(LUG)["mates"] == "stud-pair-5-8"
    assert contract(SCREW)["interface"] == "terminal-stud" and contract(RING)["mates"] == "terminal-stud"


@pytest.mark.parametrize("which", [0, 1])
def test_each_pole_stands_at_the_midpoint_of_the_two_studs_the_skin_draws_in_its_column(which):
    ident, _, studs = POLES[which]
    skin = (LIB / "components" / NAME / "v2/skins/default.svg").read_text()
    drawn = [[float(x), float(y)] for x, y in re.findall(r'<g id="stud-\d"><circle cx="([\d.]+)" cy="([\d.]+)" r="3\.2"', skin)]
    assert drawn == [c for _, _, pair in POLES for c in pair]
    assert abs(studs[1][1] - studs[0][1] - PITCH) < 0.01
    pole = contract(POLE)
    centre = [studs[0][0], (studs[0][1] + studs[1][1]) / 2]
    part = next(p for p in contract(SUPPLY)["parts"] if p["id"] == ident)
    mate = pole["connection-points"]["mate"]["at"]
    # a quarter turn about the pole's own centre: the pair's midpoint stays where the part's own midpoint is
    half = [pole["size"]["w"] / 2, pole["size"]["h"] / 2]
    assert [round(part["at"][0] + half[0], 2), round(part["at"][1] + half[1], 2)] == [round(centre[0], 2), round(centre[1], 2)]
    assert mate[0] == pytest.approx(half[0], abs=0.01)


def test_the_face_is_drawn_the_way_the_guide_shows_it():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ["handle", "terminals"]
    skin = (LIB / "components" / NAME / "v2/skins/default.svg").read_text()
    ids = re.findall(r'id="([^"]+)"', skin)
    for want in ("face", "rotor", "handle", "led-status", "terminals", "stud-0", "stud-1", "stud-2", "stud-3", "silkscreen"):
        assert want in ids, want
    # the handle is at the left and the block, with its labels, at the right
    assert d["elements"]["handle"]["at"][0] < 5 and d["elements"]["terminals"]["at"][0] > 30
    texts = re.findall(r"<text[^>]*>([^<]+)</text>", skin)
    assert texts == ["-48V/-60V", "RTN"]


def test_the_dc_port_is_one_input_of_two_poles_left_to_right_as_the_supply_prints_them():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    assert ports[0]["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in ports[0]["poles"]] == [(r, i) for i, r, _ in POLES]


def test_the_port_states_the_wire_size_and_the_current_and_no_voltage():
    port = contract(SUPPLY)["dc"]["ports"][0]
    assert port["awg"] == [6] and port["rating-a"] == 50
    assert "voltage" not in port and "side" not in port
    assert port["source"] == {"poles": "poles", "awg": "awg", "rating-a": "rating"}


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    for key in ("poles", "awg", "seats", "face", "lug", "voltage", "rating"):
        assert len(words(d["provenance"][key])) >= 40, key
    poles = words(d["provenance"]["poles"])
    assert "-48V/-60V (negative) and RTN (positive)" in poles and "four terminals" in poles
    assert "Figure 35" in words(d["provenance"]["lug"]) and ".63 in." in words(d["provenance"]["lug"])
    assert "6 AWG" in words(d["provenance"]["awg"])


def test_the_missing_voltage_is_said_not_left_out_silently():
    text = words(contract(SUPPLY)["provenance"]["voltage"])
    assert text.startswith("NOT STATED") and "the port states none" in text


def test_the_pole_stand_in_is_declared_in_the_seats_entry():
    text = words(contract(SUPPLY)["provenance"]["seats"])
    assert text.startswith("A DECLARED STAND-IN") and "THE LUG'S PITCH IS PRINTED AND THE STUDS' IS NOT" in text


@pytest.mark.heavy
def test_the_build_publishes_two_pole_slots_that_accept_the_lug_and_one_dc_port(index):
    entry = index[SUPPLY]
    assert [(p["id"], p["direction"]) for p in entry["dc-ports"]] == [("input", "input")]
    assert [(q["role"], q["slot"]) for q in entry["dc-ports"][0]["poles"]] == [(r, i) for i, r, _ in POLES]
    assert entry["dc-ports"][0]["awg"] == [6] and entry["dc-ports"][0]["rating-a"] == 50


def test_the_device_accepts_both_majors_and_seats_the_new_one_in_its_dc_configuration():
    d = yaml.safe_load((LIB / "devices/juniper" / DEVICE / "device.yaml").read_text())
    bays = [b for v in d["views"].values() for b in v.get("components", {}).get("bays", [])]
    supply_bays = [b for b in bays if OLD in b.get("accepts", [])]
    assert [b["id"] for b in supply_bays] == ["psu-0", "psu-1"] and all(SUPPLY in b["accepts"] for b in supply_bays)
    assert {r for b in supply_bays for r in b["accepts"] if r.startswith(NAME)} == {OLD, SUPPLY}
    assert d["configurations"]["dc"]["bays"] == {"psu-0": SUPPLY, "psu-1": SUPPLY}
    assert not [c for k, c in d["configurations"].items() if k != "dc" and SUPPLY in (c.get("bays") or {}).values()]


def test_the_device_took_one_minor_and_its_lock_holds_one_port_for_each_supply_bay():
    folder = LIB / "devices/juniper" / DEVICE
    lock = json.loads((folder / "device.lock.json").read_text())
    assert lock["composed-refs"][SUPPLY].startswith("2.0.0+") and lock["composed-refs"][POLE].startswith("1.0.0+")
    assert sorted(lock["dc-ports"]) == ["psu-0/module/input", "psu-1/module/input"]
    for path, refs in lock["dc-ports"].items():
        assert list(refs) == [SUPPLY] and refs[SUPPLY]["voltage"] is None and refs[SUPPLY]["rating-a"] == 50


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] in (OLD, SUPPLY) and r["code"] == "C19"] == []

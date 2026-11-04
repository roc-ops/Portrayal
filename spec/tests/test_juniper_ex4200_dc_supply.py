"""The Juniper EX-PWR-190-DC supply of the EX4200 offers a power end: its four terminals are seats a ring lug lands on, and it
states one DC port per feed.

The supply drew its terminal block as art inside its skin, so it offered no place for a DC feed. It now composes the four screws
of that block as parts, in the order the face prints them from the top (A+, B+, A-, B-), and states the two feeds its hardware
guide describes: `feed-a` on A+ and A- and `feed-b` on B+ and B-, the poles `pos` and `neg` the supply prints, the sides a and b
it prints. The jumpers fitted at the factory, from A+ to B+ and from A- to B-, are not modelled.

The three EX4200 switches that seat it take a minor each, and the record of the issue that the change closes is gone. These run
against the real library, a components index built by the indexer the build runs, and the records file. Only one of them reads
the index, and none reads library/dist or renders.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"
SUPPLY = "juniper/ex4200-pwr-190-dc@1"

# the seats as (id, at): the centre of each terminal the skin already draws, less half the screw's width
SEATS = [("pole-a-pos", [78.3, 6.3]), ("pole-b-pos", [78.3, 15.3]), ("pole-a-neg", [78.3, 24.3]), ("pole-b-neg", [78.3, 33.3])]
PORTS = [("feed-a", "a", [("pos", "pole-a-pos"), ("neg", "pole-a-neg")]), ("feed-b", "b", [("pos", "pole-b-pos"), ("neg", "pole-b-neg")])]
ELEMENTS = ["handle", "latch", "led-a", "led-b"]
# the devices that seat it and the version each takes (a minor)
DEVICES = {"ex4200-24f": "0.3.0", "ex4200-24t": "0.3.0", "ex4200-48t": "0.3.0"}


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_supply_composes_the_four_screws_of_its_block_and_nothing_else():
    assert contract(SUPPLY)["parts"] == [dict(ref=SCREW, id=i, at=at) for i, at in SEATS]


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_seats_stand_at_the_centres_of_the_terminals_the_skin_already_draws():
    skin = (path_of(SUPPLY) / "skins/default.svg").read_text()
    group = re.search(r'<g id="terminals">(.*?)</g>\s*<g stroke', skin, re.S).group(1)
    centres = [[float(x), float(y)] for x, y in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="2\.5"/>', group)]
    half = contract(SCREW)["size"]["w"] / 2
    assert len(centres) == len(SEATS) == 4
    for (ident, at), centre in zip(SEATS, centres):
        assert [round(at[0] + half, 2), round(at[1] + half, 2)] == centre, ident


def test_the_skin_still_prints_the_four_marks_in_the_order_the_seats_are_composed():
    skin = (path_of(SUPPLY) / "skins/default.svg").read_text()
    assert re.findall(r'font-size="1\.6" text-anchor="middle">([AB][+-])</text>', skin) == ["A+", "B+", "A-", "B-"]


def test_the_elements_the_version_and_the_description_are_what_the_change_leaves():
    d = contract(SUPPLY)
    assert d["version"] == "1.1.0"
    assert sorted(d["elements"]) == ELEMENTS
    assert d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["input-current"] == "7 A maximum"
    assert d["description"].startswith("Juniper EX-PWR-190-DC, the 190 W DC power supply of the EX4200-24T-DC")
    assert "shipped with a jumper from A+ to B+" in words(d["description"])


def test_the_supply_states_one_port_per_feed_with_the_roles_and_the_sides_it_prints():
    got = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in got] == [i for i, _, _ in PORTS]
    for port, (_, side, poles) in zip(got, PORTS):
        assert port["direction"] == "input" and port["side"] == side
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles
    slots = [q["slot"] for p in got for q in p["poles"]]
    assert len(slots) == len(set(slots)) == 4


def test_each_port_states_only_the_figures_a_held_table_prints():
    for port in contract(SUPPLY)["dc"]["ports"]:
        assert port["rating-a"] == 7
        assert port["awg"] == [12, 14]
        assert "voltage" not in port, "the guide's table prints a range and no nominal"


def test_the_jumpers_the_supply_ships_with_are_not_modelled():
    d = contract(SUPPLY)
    assert not [p for p in d["parts"] if "jump" in p["id"]]
    text = words(d["provenance"]["poles"])
    assert "jumper from A+ to B+" in text and "not modelled" in text


def test_every_fact_the_ports_state_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    want = {"poles": "poles", "rating-a": "rating", "awg": "awg", "side": "side"}
    for port in d["dc"]["ports"]:
        assert port["source"] == want
    for key in ("seats", "poles", "side", "voltage", "rating", "awg"):
        assert len(words(d["provenance"][key])) >= 40, key
    assert words(d["provenance"]["voltage"]).startswith("NOT STATED")
    assert not words(d["provenance"]["rating"]).startswith("NOT STATED")
    assert "not seats" not in words(d["provenance"]["terminals"]), "the terminals are seats now"


def test_the_roles_are_the_marks_the_supply_prints():
    text = words(contract(SUPPLY)["provenance"]["poles"])
    for mark in ("A+", "B+", "A-", "B-"):
        assert mark in text
    assert "so the roles are not `rtn` and `batt`" in text


@pytest.mark.heavy
def test_the_build_publishes_the_seats_that_accept_the_ring_lug_and_the_two_ports(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _ in SEATS]
    assert [(p["id"], p["direction"]) for p in entry["dc-ports"]] == [(i, "input") for i, _, _ in PORTS]
    for port, (_, _, poles) in zip(entry["dc-ports"], PORTS):
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles


@pytest.mark.parametrize("device", DEVICES)
def test_each_device_that_seats_the_supply_takes_one_minor(device):
    folder = LIB / "devices/juniper" / device
    lock = json.loads((folder / "device.lock.json").read_text())
    for fn in ("layout.yaml", "device.yaml"):
        assert re.search(rf"^version: {re.escape(DEVICES[device])}$", (folder / fn).read_text(), re.M), fn
    assert lock["version"] == DEVICES[device]
    assert lock["composed-refs"][SUPPLY].startswith("1.1.0+")
    assert lock["composed-refs"][SCREW].startswith("1.0.1+")
    assert sorted(lock["dc-ports"]) == ["psu-0/module/feed-a", "psu-0/module/feed-b"]


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY] == []

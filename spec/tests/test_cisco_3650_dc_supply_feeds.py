"""The two DC feeds of the Cisco Catalyst 3650 640 W DC supply are places a cable lands, one port per feed.

The supply used to draw its five-screw terminal block as art inside a cover element, so it offered no place for a DC feed. The
block carries two feeds, A and B, with the grounding terminal between them (positive, negative, ground, negative, positive, as
the vendor's hardware installation guide draws and labels it). It now composes the five screws as parts, each a seat a ring lug
lands on, and states one DC input port per feed, two poles each (decided 2026-11-03):

  - cisco/pwr-c2-640wdc@1 composes common/terminal-screw-34@1 four times, as `pole-a-pos`, `pole-a-neg`, `pole-b-neg` and
    `pole-b-pos`, and common/ground-screw@1 once, as `earth`, at the centres of the five screws its skin already draws;
  - both screw parts present `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has two input ports, `feed-a` (A+ and A-) and `feed-b` (B- and B+), with the roles the guide
    prints, side a and side b, the one wire size the guide gives and no voltage (the guide prints two nominals) and no current
    (it prints a pair), each fact naming the `provenance` entry that says it;
  - the earth screw is common to both feeds and is a ground seat outside both ports, not a pole of either;
  - the supply's elements, its other ids and its description are unchanged.

The Nexus 9500 DC supply (four posts, two inputs) is not part of this change: it keeps its contract and its record. These run
against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "cisco/pwr-c2-640wdc@1"
SCREW = "common/terminal-screw-34@1"
EARTH = "common/ground-screw@1"
LUG = "generic/ring-lug@1"
# the seats as (id, part, at), left to right as the guide's figures draw the block
SEATS = [("pole-a-pos", SCREW, [5.3, 21.3]), ("pole-a-neg", SCREW, [13.3, 21.3]), ("earth", EARTH, [20.2, 20.2]),
         ("pole-b-neg", SCREW, [29.3, 21.3]), ("pole-b-pos", SCREW, [37.3, 21.3])]
# the ports as (id, side, [(role, slot)]), the poles of each in the order the figures print them from the left
PORTS = [("feed-a", "a", [("pos", "pole-a-pos"), ("neg", "pole-a-neg")]),
         ("feed-b", "b", [("neg", "pole-b-neg"), ("pos", "pole-b-pos")])]
ELEMENTS = ["dc-ok", "handle", "latch", "ps-ok", "terminals"]
DEVICE = "ws-c3650-48pd"
NOT_TAKEN = "cisco/n9k-pdc-3000w-b@1"


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


def test_the_supply_composes_four_terminal_screws_and_one_ground_screw_and_nothing_else():
    assert contract(SUPPLY)["parts"] == [dict(ref=ref, id=i, at=at) for i, ref, at in SEATS]


def test_both_screw_parts_present_terminal_stud_and_the_ring_lug_mates_them():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(EARTH)["interface"] == "terminal-stud" and contract(EARTH)["class"] == "ground"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_seats_stand_at_the_centres_of_the_five_screws_the_skin_already_draws():
    skin = (LIB / "components/cisco/pwr-c2-640wdc/v1/skins/default.svg").read_text()
    block = re.search(r'<g id="terminals">(.*?)</g>\s*<g id="handle">', skin, re.S).group(1)
    centres = [[float(x), float(y)] for x, y in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="2\.8"/>', block)]
    assert len(centres) == 5
    for (ident, ref, at), centre in zip(SEATS, centres):
        half = contract(ref)["size"]["w"] / 2
        assert [round(at[0] + half, 2), round(at[1] + half, 2)] == centre, ident


def test_the_elements_and_the_description_are_unchanged_and_no_id_of_the_supply_went():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ELEMENTS
    assert d["version"] == "1.1.0"
    assert d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["input"] == "dc"
    assert d["attrs"]["input-voltage"] == "-36 to -72 VDC, dual input feeds A and B"
    assert d["description"].startswith("The 640 W DC-input power supply of the Cisco Catalyst 3650 and 2960-X/XR families")


def test_the_block_gives_one_dc_input_port_per_feed_with_two_poles_each():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == [i for i, _, _ in PORTS]
    for port, (_, _, poles) in zip(ports, PORTS):
        assert port["direction"] == "input"
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles


def test_the_earth_screw_is_a_ground_seat_outside_both_ports():
    d = contract(SUPPLY)
    slots = [q["slot"] for p in d["dc"]["ports"] for q in p["poles"]]
    assert "earth" not in slots and len(slots) == len(set(slots)) == 4
    assert [q["ref"] for q in d["parts"] if q["id"] == "earth"] == [EARTH]


def test_each_port_states_its_side_and_the_one_wire_size_and_no_voltage_and_no_current():
    for port, (_, side, _) in zip(contract(SUPPLY)["dc"]["ports"], PORTS):
        assert port["side"] == side
        assert port["awg"] == [12]
        assert "voltage" not in port and "rating-a" not in port


def test_every_fact_the_ports_state_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    for port in d["dc"]["ports"]:
        assert port["source"] == {"poles": "poles", "awg": "awg", "side": "side"}
    for key in ("poles", "awg", "side", "seats", "earth"):
        assert len(words(d["provenance"][key])) >= 40
    poles = words(d["provenance"]["poles"])
    assert "Figure 4-6" in poles and "Figures 4-14 and 4-15" in poles and "Grounding terminal" in poles
    assert "dual input feeds (A and B)" in words(d["provenance"]["side"])
    assert "12-AWG DC power input wires" in words(d["provenance"]["awg"])
    assert words(d["provenance"]["earth"]).startswith("A DECLARED STAND-IN") and "outside both DC ports" in words(d["provenance"]["earth"])


@pytest.mark.parametrize("key", ["voltage", "rating"])
def test_the_missing_voltage_and_current_are_said_not_left_out_silently(key):
    text = words(contract(SUPPLY)["provenance"][key])
    assert text.startswith("NOT STATED") and "the ports state none" in text
    if key == "voltage":
        assert "-48 VDC (nominal)" in text and "-60 VDC (nominal)" in text


def test_the_build_publishes_five_seats_that_accept_the_ring_lug_and_two_dc_ports(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _, _ in SEATS]
    assert [(p["id"], p["direction"], p["side"]) for p in entry["dc-ports"]] == [(i, "input", s) for i, s, _ in PORTS]
    for port, (_, _, poles) in zip(entry["dc-ports"], PORTS):
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles


def test_the_device_that_seats_the_supply_takes_one_minor():
    folder = LIB / "devices/cisco" / DEVICE
    lock = json.loads((folder / "device.lock.json").read_text())
    for fn in ("layout.yaml", "device.yaml"):
        assert re.search(r"^version: 1\.2\.0$", (folder / fn).read_text(), re.M), fn
    assert lock["version"] == "1.2.0"
    assert lock["composed-refs"][SUPPLY].startswith("1.1.0+")
    assert lock["composed-refs"][SCREW].startswith("1.0.1+")
    assert lock["composed-refs"][EARTH].startswith("1.0.0+")


def test_the_lock_holds_two_ports_for_each_supply_of_the_two_dc_configurations():
    lock = json.loads((LIB / "devices/cisco" / DEVICE / "device.lock.json").read_text())
    ports = {path: refs[SUPPLY] for path, refs in lock["dc-ports"].items()}
    assert sorted(ports) == ["psu-1/module/feed-a", "psu-1/module/feed-b", "psu-2/module/feed-a", "psu-2/module/feed-b"]
    for path, fact in ports.items():
        assert fact["configs"] == (["dc", "dc-dual"] if path.startswith("psu-1/") else ["dc-dual"])
        assert fact["side"] == path[-1] and fact["voltage"] is None and fact["rating-a"] is None


def test_the_nexus_9500_dc_supply_is_not_part_of_this_change_and_keeps_its_row():
    d = contract(NOT_TAKEN)
    assert d["version"] == "1.0.0" and "dc" not in d and "parts" not in d
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert len([r for r in rows if r["part"] == NOT_TAKEN and r["code"] == "C19"]) == 1


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY and r["code"] == "C19"] == []

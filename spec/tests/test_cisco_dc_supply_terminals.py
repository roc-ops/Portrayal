"""The DC input of the Cisco Catalyst 9300 715 W DC supply is a place a cable lands, earth terminal included.

The supply used to draw its three-screw terminal block as elements, so it offered no place for a DC feed. It now composes three
terminal screws, each a seat that a ring lug lands on, and states one DC input port whose three poles are those seats, with the
roles the vendor's hardware installation guide gives them: the positive polarity terminal, the negative polarity terminal and the
grounding terminal, which is one of the block's three screws and so a pole of the port like the other two (decided 2026-11-02):

  - cisco/pwr-c1-715wdc@1 composes common/terminal-screw-34@1 three times, as `pole-pos`, `pole-neg` and `pole-gnd`, at the centres
    of the three terminal elements it already draws;
  - that screw presents `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has one input port, `input`, with the three roles the guide calls out, in the order the guide lists
    them, the voltage the guide's power table gives (a nominal and a range, negative), no current (the guide prints a pair), no
    wire size (the guide gives two) and the entries of `provenance` that its `source` names;
  - the terminal elements, every other id of the supply and its description are unchanged.

The Nexus 9500 DC supply (four posts, two inputs) is not part of this change: it keeps its contract and its record. The Catalyst
3650 supply (five screws, two feeds) has a test module of its own. These run against the real library, a components index built by
the indexer the build runs, and the records file. They read no library/dist and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "cisco/pwr-c1-715wdc@1"
SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"
# the screws as (id, at, role), in the order of the port's poles (the guide's callouts 6, 7 and 8)
SCREWS = [("pole-pos", [23.3, 22.3], "pos"), ("pole-neg", [35.3, 22.3], "neg"), ("pole-gnd", [47.3, 22.3], "gnd")]
ELEMENTS = ["dc-ok", "handle", "latch", "ps-ok", "terminal-cover", "terminal-ground", "terminal-negative", "terminal-positive"]
DEVICES = ["c9300-24p", "c9300-24u", "c9300-48p", "c9300-48t", "c9300-48u"]
NOT_TAKEN = ["cisco/n9k-pdc-3000w-b@1"]


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


def test_the_supply_composes_three_terminal_screws_one_for_each_pole_and_nothing_else():
    assert contract(SUPPLY)["parts"] == [dict(ref=SCREW, id=i, at=at) for i, at, _ in SCREWS]


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_seats_stand_at_the_centres_of_the_terminal_elements_the_supply_already_draws():
    d = contract(SUPPLY)
    boxes = {"pole-pos": "terminal-positive", "pole-neg": "terminal-negative", "pole-gnd": "terminal-ground"}
    for ident, at, _ in SCREWS:
        el = d["elements"][boxes[ident]]
        centre = [el["at"][0] + el["size"][0] / 2, el["at"][1] + el["size"][1] / 2]
        assert [round(at[0] + 1.7, 2), round(at[1] + 1.7, 2)] == centre


def test_the_terminal_elements_are_still_drawn_and_no_id_of_the_supply_went():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ELEMENTS
    assert d["version"] == "1.1.0"
    assert d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["input"] == "dc"
    assert d["attrs"]["input-voltage"] == "-36 VDC minimum, -48 VDC nominal, -72 VDC maximum"
    assert d["description"].startswith("The 715 W DC power supply of the Cisco Catalyst 9300 family, PWR-C1-715WDC.")


def test_the_dc_port_is_one_input_with_the_guides_three_terminals_the_earth_among_them():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [(role, i) for i, _, role in SCREWS]
    assert sorted(q["role"] for q in port["poles"]) == ["gnd", "neg", "pos"]


def test_the_port_states_the_voltage_the_guides_table_gives_and_no_current_and_no_wire_size():
    port = contract(SUPPLY)["dc"]["ports"][0]
    assert port["voltage"] == {"nominal": -48, "range": [-36, -72]}
    assert "rating-a" not in port and "awg" not in port


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    source = d["dc"]["ports"][0]["source"]
    assert source == {"poles": "poles", "voltage": "voltage"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    poles = words(d["provenance"]["poles"])
    assert "Figure 49" in poles and "Figure 57" in poles and "Grounding terminal" in poles
    assert "Table 47" in words(d["provenance"]["voltage"]) and "-48 VDC (nominal)" in words(d["provenance"]["voltage"])


@pytest.mark.parametrize("key", ["rating", "awg"])
def test_the_missing_current_and_wire_size_are_said_not_left_out_silently(key):
    text = words(contract(SUPPLY)["provenance"][key])
    assert text.startswith("NOT STATED") and "the port states none" in text
    assert ("`rating-a`" in text) == (key == "rating")


def test_the_one_sentence_of_the_terminals_entry_that_the_seats_made_false_is_reworded():
    text = words(contract(SUPPLY)["provenance"]["terminals"])
    assert "not as seated parts" not in text and "a seat part stands on each" in text


def test_the_build_publishes_three_seats_that_accept_the_ring_lug_and_one_dc_port(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _, _ in SCREWS]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [(role, i) for i, _, role in SCREWS]


@pytest.mark.parametrize("name", DEVICES)
def test_each_of_the_five_devices_that_seat_the_supply_takes_one_minor(name):
    folder = LIB / "devices/cisco" / name
    lock = json.loads((folder / "device.lock.json").read_text())
    for fn in ("layout.yaml", "device.yaml"):
        assert re.search(r"^version: 1\.2\.0$", (folder / fn).read_text(), re.M), (name, fn)
    assert lock["version"] == "1.2.0"
    assert lock["composed-refs"]["cisco/pwr-c1-715wdc@1"].startswith("1.1.0+")
    assert lock["composed-refs"]["common/terminal-screw-34@1"].startswith("1.0.1+")


@pytest.mark.parametrize("ref", NOT_TAKEN)
def test_the_two_cisco_dc_supplies_with_two_feeds_are_not_part_of_this_change_and_keep_their_rows(ref):
    d = contract(ref)
    assert d["version"] == "1.0.0" and "dc" not in d and "parts" not in d
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert len([r for r in rows if r["part"] == ref and r["code"] == "C19"]) == 1


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY and r["code"] == "C19"] == []

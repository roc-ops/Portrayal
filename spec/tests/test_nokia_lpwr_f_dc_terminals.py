"""The Lightspan MF-8 power module offers a DC feed whose two terminals a two-hole lug lands on.

The LPWR-F module drew its connector block as art in its skin, so a shelf that seats it offered no place a DC feed lands. It now
composes each of its two terminals as a pair of studs a single two-hole lug lands across, and states one DC input port:

  - nokia/lpwr-f-dc-pole@1 is a pair of studs on the 5/8 in. pitch the installation manual's 16 mm (0.63 in.) lug spacing
    reads as, and generic/two-hole-lug-5-8@1 mates it;
  - nokia/lpwr-f@1 composes two of them, `pole-batt` at the left and `pole-rtn` at the right, turned to the slant the unit's
    drawings give, and its port `input` carries the roles the terminals are named for, with no nominal voltage, no current and no
    wire size, because the guides print none for both builds of the module;
  - the build publishes the two pairs as seats and the port as the module's one DC port.

These run against the real library, a components index built by the indexer the build runs and the registry.
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

STUD = "common/terminal-screw-34@1"
POLE = "nokia/lpwr-f-dc-pole@1"
MODULE = "nokia/lpwr-f@1"
LUG = "generic/two-hole-lug-5-8@1"
POLES = [("batt", "pole-batt"), ("rtn", "pole-rtn")]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_pole_is_a_pair_of_studs_on_the_lug_pitch_and_says_how_the_pitch_is_read():
    registry = yaml.safe_load((SCHEMAS / "connectors.yaml").read_text())["interfaces"]
    assert "stud-pair-5-8" in registry
    assert contract(LUG)["mates"] == "stud-pair-5-8"
    d = contract(POLE)
    assert d["interface"] == "stud-pair-5-8"
    assert [(q["ref"], q["at"]) for q in d["parts"]] == [(STUD, [0, 0]), (STUD, [15.875, 0])]
    assert d["provenance"]["thread"].startswith("NOT CLAIMED")
    assert "16 mm" in d["provenance"]["pitch"]


def test_the_module_composes_one_pole_for_each_terminal_turned_to_the_same_slant():
    parts = contract(MODULE)["parts"]
    poles = [q for q in parts if q["ref"] == POLE]
    assert [q["id"] for q in poles] == [slot for _, slot in POLES]
    assert len({q["rotate"] for q in poles}) == 1 and 0 < poles[0]["rotate"] < 45
    assert poles[0]["at"][0] < poles[1]["at"][0]


def test_the_port_is_one_feed_of_the_terminals_two_roles_and_states_no_figure_the_guides_do_not_print():
    d = contract(MODULE)
    ports = d["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES
    assert not {"voltage", "rating-a", "awg"} & set(port)
    for key in port["source"].values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    for key in ("port-voltage", "port-rating", "port-awg"):
        assert d["provenance"][key].startswith("NOT STATED")


def test_the_module_keeps_its_drawing_and_every_id():
    d = contract(MODULE)
    assert sorted(d["elements"]) == ["breaker", "connector-block", "esd-mark", "handle", "screw-left", "screw-right"]
    assert d["elements"]["connector-block"]["class"] == "terminal"
    assert sorted(d["connection-points"]) == ["mate", "power"]
    assert [p["id"] for p in d["parts"] if p["ref"] != POLE] == ["led-pwr"]


@pytest.mark.heavy
def test_the_build_publishes_two_pairs_a_two_hole_lug_lands_across_and_one_dc_port(index):
    entry = index[MODULE]
    seats = {c["id"]: (c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]}
    for _, slot in POLES:
        assert seats[slot] == ("connector", "stud-pair-5-8", [LUG])
    assert [(p["id"], p["direction"], [(q["role"], q["slot"]) for q in p["poles"]]) for p in entry["dc-ports"]] == [
        ("input", "input", POLES)]

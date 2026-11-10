"""The 7360 ISAM FX-16 shelf offers two DC feeds a lug lands on, and draws no terminal as panel art.

The shelf drew its four -48 V terminals TB1-1 to TB1-4 as sixteen loose nut and post shapes in its front panel, so it offered no
place for a DC feed. It now places one terminal block, which composes each terminal as a pair of studs a single two-hole lug lands
across, and states two DC input ports:

  - nokia/fx-16-dc-pole@1 is a pair of studs on the 5/8 in. pitch of the lug the installation manual names, and
    generic/two-hole-lug-5-8@1 mates it;
  - nokia/fx-16-dc-terminal-block@1 composes four of them, turned to the angle the shelf's elevation draws, and its ports `feed-a`
    and `feed-b` carry the roles the legends print and the nominal voltage, branch current and wire size the data sheet prints;
  - nokia/nfxs-d-ba places that block and no longer draws the sixteen decor shapes.

These run against the real library, a components index built by the indexer the build runs, the registry and the lint baseline.
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
POLE = "nokia/fx-16-dc-pole@1"
BLOCK = "nokia/fx-16-dc-terminal-block@1"
LUG = "generic/two-hole-lug-5-8@1"
POLES = ["tb1-1", "tb1-2", "tb1-3", "tb1-4"]
FEEDS = [("feed-a", [("batt", "tb1-1"), ("rtn", "tb1-2")]),
         ("feed-b", [("rtn", "tb1-3"), ("batt", "tb1-4")])]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device():
    return yaml.safe_load((LIB / "devices" / "nokia" / "nfxs-d-ba" / "device.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_pole_is_a_pair_of_studs_on_the_lug_pitch():
    registry = yaml.safe_load((SCHEMAS / "connectors.yaml").read_text())["interfaces"]
    assert "stud-pair-5-8" in registry
    assert contract(LUG)["mates"] == "stud-pair-5-8"
    d = contract(POLE)
    assert d["interface"] == "stud-pair-5-8"
    assert [(q["ref"], q["at"]) for q in d["parts"]] == [(STUD, [0, 0]), (STUD, [15.875, 0])]
    assert d["provenance"]["thread"].startswith("NOT CLAIMED")


def test_the_block_composes_one_pole_for_each_terminal_turned_to_the_drawn_angle():
    d = contract(BLOCK)
    got = [(q["id"], q["ref"], q.get("rotate")) for q in d["parts"]]
    assert got == [(p, POLE, -30.2) for p in POLES]
    assert d["class"] == "inlet"


def test_each_feed_is_a_port_of_the_legends_roles_and_states_the_figures_the_data_sheet_prints():
    d = contract(BLOCK)
    ports = d["dc"]["ports"]
    assert [p["id"] for p in ports] == [f for f, _ in FEEDS]
    for port, (_, poles) in zip(ports, FEEDS):
        assert port["direction"] == "input"
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles
        assert port["voltage"] == {"nominal": -48}
        assert port["rating-a"] == 70
        assert port["awg"] == [2]
        for key in port["source"].values():
            assert key in d["provenance"] and len(d["provenance"][key]) >= 40


def test_the_build_publishes_four_pairs_a_two_hole_lug_lands_across_and_two_dc_ports(index):
    entry = index[BLOCK]
    seats = {c["id"]: (c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]}
    for slot in POLES:
        assert seats[slot] == ("connector", "stud-pair-5-8", [LUG])
    assert [(p["id"], p["direction"], [(q["role"], q["slot"]) for q in p["poles"]]) for p in entry["dc-ports"]] == [
        (f, "input", poles) for f, poles in FEEDS]


def test_the_shelf_places_the_block_and_draws_no_terminal_as_decor():
    d = device()
    placed = [p for p in d["views"]["front"]["components"]["placements"] if p["ref"] == BLOCK]
    assert len(placed) == 1
    decor = d["views"]["front"]["panel"]["decor"]
    assert not [x for x in decor if x.get("kind") in ("terminal-post", "terminal-nut")]


def test_the_lint_baseline_holds_no_decor_warning_for_the_shelf():
    base = json.loads((LIB / "lint-baseline.json").read_text())
    assert "L197" not in base.get("devices/nokia/nfxs-d-ba/device.yaml", {})

"""The PSU-151 DC supply's terminal block is drawn as the vendor's figure shows it, offers three seats, and states its DC input.

The PSU-151 DC supply of the UfiSpace S6301-56ST drew a terminal block 24.6 mm wide with its three clamp screws 7.5 mm apart, the
third against the block's edge. The vendor's guide dimensions 8.2 mm across ONE terminal's cell, so three screws cannot stand closer
than that, and its figure shows a block about 31 mm wide with the screws about 9.6 mm apart and the handle against its right edge.
The redrawn supply moves two drawn boxes, so it is version 2 of the part (`v2/`), and version 1 keeps its drawing. Version 2
composes its three terminal screws as parts, each a seat a ring lug lands on, and states one DC input port whose poles are those
seats, with the roles the vendor's guide prints under the three screws, left to right:

  - the skin draws three clamp rings at least 8.2 mm apart inside a block at least three terminals wide, the handle clear of the
    block, and the `terminal-block` and `handle` elements are those boxes;
  - the supply composes common/terminal-screw-34@1 three times, as `pole-rtn`, `pole-batt` and `pole-gnd`, each standing on the
    centre of a ring the skin draws;
  - that screw presents `terminal-stud`, and generic/ring-lug@1 mates it;
  - the contract's `dc` block has one input port, `input`, with `rtn` on `pole-rtn`, `batt` on `pole-batt` and `gnd` on `pole-gnd`,
    the supply's input current and cable size, no voltage, and the entries of `provenance` that its `source` names;
  - the cable registry holds a DC feed of two conductors of the port's gauge, its figures declared estimates, so a feed to the port
    can be typed without a cable-size warning;
  - every id of the supply is kept, version 1 is drawn as it was and names version 2 as its successor, and the S6301-56ST's DC
    builds seat version 2 while its supply bays still accept version 1.

These run against the real library, a components index built by the indexer the build runs, the cable registry and the records
file. They read no library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

REF = "ufispace/psu-151-dc@2"
OLD = "ufispace/psu-151-dc@1"
AC = "ufispace/psu-151-ac@1"
DEVICE = LIB / "devices/ufispace/s6301-56st/device.yaml"
SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"
POLES = [("rtn", "pole-rtn"), ("batt", "pole-batt"), ("gnd", "pole-gnd")]
SVG = "{http://www.w3.org/2000/svg}"
TERMINAL_CELL_MM = 8.2          # the guide's Figure 25: the width across one terminal's cell
SCREW_HALF = 1.7                # half of common/terminal-screw-34's own 3.4 head
RATING_A = 6
AWG = 18


def contract(major=2):
    return yaml.safe_load((LIB / f"components/ufispace/psu-151-dc/v{major}/contract.yaml").read_text())


def block_art(major=2):
    """The plate and the clamp rings of the skin's `terminal-block` group, and the handle's rectangle."""
    root = ET.parse(LIB / f"components/ufispace/psu-151-dc/v{major}/skins/default.svg").getroot()
    group = next(e for e in root.iter(f"{SVG}g") if e.get("id") == "terminal-block")
    plate = group.find(f"{SVG}rect")
    rings = [(float(c.get("cx")), float(c.get("cy")), float(c.get("r"))) for c in group.findall(f"{SVG}circle")]
    handle = next(e for e in root.iter(f"{SVG}rect") if e.get("id") == "handle")
    box = lambda e: [float(e.get(k)) for k in ("x", "y", "width", "height")]
    return box(plate), rings, box(handle)


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    d = yaml.safe_load((LIB / "components/common/terminal-screw-34/v1/contract.yaml").read_text())
    lug = yaml.safe_load((LIB / "components/generic/ring-lug/v1/contract.yaml").read_text())
    assert d["interface"] == "terminal-stud"
    assert lug["mates"] == "terminal-stud"


def test_the_skin_draws_three_rings_a_terminal_apart_inside_a_block_clear_of_the_handle():
    plate, rings, handle = block_art()
    assert len(rings) == 3
    xs = [x for x, _, _ in rings]
    assert len({y for _, y, _ in rings}) == 1, "the three rings stand on one line"
    # the guide dimensions one terminal at 8.2 mm: no two screws stand closer than that
    assert all(b - a >= TERMINAL_CELL_MM for a, b in zip(xs, xs[1:])), xs
    assert plate[2] >= 3 * TERMINAL_CELL_MM, "the block is at least three terminals wide"
    for x, y, r in rings:
        assert plate[0] <= x - r and x + r <= plate[0] + plate[2] and plate[1] <= y - r and y + r <= plate[1] + plate[3], (x, y)
    assert plate[0] + plate[2] <= handle[0], "the handle stands clear of the block"


def test_the_elements_are_the_boxes_the_skin_draws_and_no_id_of_the_supply_went():
    d = contract()
    plate, _, handle = block_art()
    assert sorted(d["elements"]) == sorted(contract(1)["elements"]) == ["handle", "latch", "status-led", "terminal-block"]
    assert d["elements"]["terminal-block"]["class"] == "inlet"
    assert d["elements"]["handle"]["class"] == "handle"
    for name, drawn in (("terminal-block", plate), ("handle", handle)):
        got = d["elements"][name]
        assert got["at"] + got["size"] == pytest.approx(drawn), name
    assert d["connection-points"]["power"]["direction"] == "front"


def test_the_redraw_is_version_2_and_version_1_is_drawn_as_it_was():
    """A redraw that moves a drawn box is a new major. Version 1 keeps its boxes, its skin's rings and its description, carries no
    seat and no port, and names version 2 as its successor, so a manifest that pins it still gets the drawing it pinned."""
    new, old = contract(2), contract(1)
    assert new["version"].split(".")[0] == "2" and old["version"].split(".")[0] == "1"
    assert new["description"] == old["description"], "the exported module type quotes the description"
    assert old["superseded-by"] == REF and "superseded-by" not in new
    assert old["elements"]["terminal-block"]["at"] + old["elements"]["terminal-block"]["size"] == pytest.approx([3.0, 16.5, 24.6, 19.2])
    assert old["elements"]["handle"]["at"] + old["elements"]["handle"]["size"] == pytest.approx([28.0, 2.0, 4.6, 36.5])
    assert "parts" not in old and "dc" not in old
    _, rings, _ = block_art(1)
    assert [x for x, _, _ in rings] == pytest.approx([9.5, 17.0, 24.5])


def test_the_device_seats_version_2_in_its_dc_builds_and_still_accepts_version_1():
    d = yaml.safe_load(DEVICE.read_text())
    bays = {b["id"]: b for b in d["views"]["rear"]["components"]["bays"] if b["id"] in ("psu-0", "psu-1")}
    assert sorted(bays) == ["psu-0", "psu-1"]
    for b in bays.values():
        assert b["accepts"] == [OLD, REF, AC], b["id"]
    configs = d["configurations"]
    for name in ("dc", "dc-b2f"):
        assert configs[name]["bays"] == {"psu-0": REF, "psu-1": REF}, name
    for name in ("ac", "ac-b2f"):
        assert configs[name]["bays"] == {"psu-0": AC, "psu-1": AC}, name


def test_the_supply_composes_three_terminal_screws_each_on_the_centre_of_a_ring():
    got = {q["id"]: (q["ref"], q["at"], q["lift"]) for q in contract()["parts"]}
    _, rings, _ = block_art()
    want = {i: (SCREW, [x - SCREW_HALF, y - SCREW_HALF], 8.0) for (_, i), (x, y, _) in zip(POLES, sorted(rings))}
    assert sorted(got) == sorted(want)
    for i in want:
        assert got[i][0] == want[i][0] and got[i][2] == want[i][2]
        assert got[i][1] == pytest.approx(want[i][1]), i


def test_the_dc_port_is_one_input_with_the_legends_roles_on_the_three_screws():
    ports = contract()["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES
    assert port["rating-a"] == RATING_A
    assert port["awg"] == [AWG]
    assert "voltage" not in port


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract()
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "rating-a", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Figure 26" in d["provenance"][source["poles"]]
    assert d["provenance"]["block"].startswith("estimated")


def test_the_build_publishes_three_seats_that_accept_the_ring_lug_and_one_dc_port(index):
    entry = index[REF]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for _, i in POLES]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES
    assert not index[OLD].get("cages") and not index[OLD].get("dc-ports")


def test_the_registry_holds_a_two_conductor_dc_feed_of_the_ports_gauge_and_says_it_is_an_estimate():
    types = yaml.safe_load((ROOT / "spec/schemas/cable-types.yaml").read_text())["types"]
    feeds = {tid: t for tid, t in types.items() if t.get("dc") and [c["awg"] for c in t["conductors"]] == [AWG, AWG]}
    assert list(feeds) == ["dc-feed-2x18awg"]
    t = feeds["dc-feed-2x18awg"]
    assert t["label"] == "DC power feed, 2 x 18 AWG" and t["media"] == "power" and t["family"] == "power"
    assert t["ampacity-a"] >= RATING_A, "a feed that cannot carry the supply's input would warn on every cable"
    # no source held gives this gauge's diameter or ampacity: each figure is Portrayal's own, and the type says so
    assert t["od_sources"] == ["portrayal-estimate"] and t["ampacity-sources"] == ["portrayal-estimate"]
    assert t["unverified"] is True and t["min_bend_radius"]["installed"]["unverified"] is True
    assert "estimate" in t["note"]


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [(r["part"], r["code"]) for r in rows if r["part"] in (OLD, REF) and r["code"] == "C19"] == []

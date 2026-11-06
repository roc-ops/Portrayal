"""The UfiSpace PSU-302 and PSU-132 CRPS DC supplies draw the terminal block the vendor's guides show, offer two poles and state their DC input.

Both supplies take a two-hole lug on each of two poles (the PSU-302 guides' Figures 23 and 26, the S9601-104BC guide's lug drawing and
Figure 24). The lug each guide dimensions has two holes .63 +/- .02 in. apart, which holds 5/8 in. The first drawing of each supply
put its screws 7.2 mm apart (PSU-132 CRPS) or one to a pole (PSU-302), neither of which a two-hole lug can land on. Each is redrawn
as version 2 of its part (`v2/`), which composes its two poles as parts that present a registered stud pair a two-hole lug lands
across, and states one DC input port whose poles are those two parts:

  - the skin's four screw rings stand where the poles' studs do (5/8 in. apart along each pole);
  - the supply composes juniper/mx240-dc-pole@1 twice: `pole-1` and `pole-2` on the PSU-302 (the guides print no conductor name,
    so both roles are `unstated`), `pole-rtn` and `pole-batt` on the PSU-132 CRPS (the S9601-104BC guide's Figure 6 letters them);
  - the port states the input current every datasheet of its devices prints, and the cable size only where every guide prints one;
  - every id of the supply is kept, version 1 keeps its drawing and names version 2 as its successor, and every device that seats the
    supply in a DC build seats version 2 while its supply bays still accept version 1.

These run against the real library, a components index built by the indexer the build runs and the records file. They read no
library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"
KEY = "stud-pair-5-8"
LUG = "generic/two-hole-lug-5-8@1"
PITCH = 15.875
POLE_MIDDLE = (9.6375, 1.7)    # the pole part's own `mate` point: the middle of its two screws

SUPPLIES = {
    "psu-302-dc": {
        "roles": [("unstated", "pole-1"), ("unstated", "pole-2")],
        "rating": 80, "awg": [4], "gap": True, "turn": 90,
        "devices": ["s9321-64e", "s9321-64eo", "s9610-36d", "s9611-36d", "s9710-76d", "s9720-56ed", "s9725-64e"],
    },
    "psu-132-crps-dc": {
        "roles": [("rtn", "pole-rtn"), ("batt", "pole-batt")],
        "rating": 37, "awg": None, "gap": False, "turn": 0,
        "devices": ["s9601-104bc"],
    },
}
EVERY = pytest.mark.parametrize("name", sorted(SUPPLIES))


def contract(name, major=2):
    return yaml.safe_load((LIB / f"components/ufispace/{name}/v{major}/contract.yaml").read_text())


def skin(name, major=2):
    return ET.parse(LIB / f"components/ufispace/{name}/v{major}/skins/default.svg").getroot()


def rings(name):
    """The centres of the circles of the skin's block group that are not the status lamp, as (x, y)."""
    root = skin(name)
    return sorted((round(float(c.get("cx")), 4), round(float(c.get("cy")), 4)) for c in root.iter(f"{SVG}circle")
                  if c.get("id") != "status-led" and c.get("r") is not None and float(c.get("r")) < 2.5
                  and c.get("cx") and c.get("cy") and not _in_fan_frame(root, c))


def _in_fan_frame(root, circle):
    for g in root.iter(f"{SVG}g"):
        if g.get("id") in ("fan-frame", "rotor-grille", "rotor-bulge") and circle in list(g.iter(f"{SVG}circle")):
            return True
    return False


def studs(part):
    """Where a composed pole's two studs stand on the supply's face, from its `at` and `rotate`."""
    cx, cy = part["at"][0] + POLE_MIDDLE[0], part["at"][1] + POLE_MIDDLE[1]
    half = PITCH / 2
    return [(round(cx - half, 4), round(cy, 4)), (round(cx + half, 4), round(cy, 4))] if not part.get("rotate") else \
           [(round(cx, 4), round(cy - half, 4)), (round(cx, 4), round(cy + half, 4))]


def device_sources(name):
    return {d: yaml.safe_load((LIB / f"devices/ufispace/{d}/device.yaml").read_text()) for d in SUPPLIES[name]["devices"]}


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@EVERY
def test_the_skin_draws_a_screw_ring_where_each_poles_studs_stand(name):
    d = contract(name)
    expect = sorted(s for q in d["parts"] for s in studs(q))
    assert len(expect) == 4
    got = rings(name)
    for want in expect:
        assert want in got, (name, want, got)


@EVERY
def test_the_two_poles_of_one_supply_stand_on_two_lines_and_each_pair_is_a_lug_apart(name):
    d = contract(name)
    first, second = (studs(q) for q in d["parts"])
    for pair in (first, second):
        assert abs(pair[1][0] - pair[0][0] + pair[1][1] - pair[0][1]) == pytest.approx(PITCH, abs=0.001)
    assert first != second


@EVERY
def test_the_supply_composes_two_poles_that_present_the_stud_pair(name):
    d = contract(name)
    assert [q["id"] for q in d["parts"]] == [slot for _, slot in SUPPLIES[name]["roles"]]
    assert {q["ref"] for q in d["parts"]} == {"juniper/mx240-dc-pole@1"}
    assert all(q.get("rotate", 0) == SUPPLIES[name]["turn"] for q in d["parts"])


@EVERY
def test_the_dc_port_is_one_input_with_the_roles_the_documents_print(name):
    port = contract(name)["dc"]["ports"]
    assert [p["id"] for p in port] == ["input"]
    p = port[0]
    assert p["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in p["poles"]] == SUPPLIES[name]["roles"]
    assert p["rating-a"] == SUPPLIES[name]["rating"]
    if SUPPLIES[name]["awg"] is None:
        assert "awg" not in p
    else:
        assert p["awg"] == SUPPLIES[name]["awg"]
    assert "voltage" not in p


@EVERY
def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from(name):
    d = contract(name)
    source = d["dc"]["ports"][0]["source"]
    expect = {"poles", "rating-a"} | ({"awg"} if SUPPLIES[name]["awg"] else set())
    assert set(source) == expect
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert d["provenance"]["block"].startswith("estimated")


@EVERY
def test_the_redraw_is_version_2_and_version_1_keeps_its_drawing_and_names_it(name):
    new, old = contract(name), contract(name, 1)
    assert new["version"].split(".")[0] == "2" and old["version"].split(".")[0] == "1"
    assert new["description"] == old["description"], "the exported module type quotes the description"
    assert old["superseded-by"] == f"ufispace/{name}@2" and "superseded-by" not in new
    assert "parts" not in old and "dc" not in old
    assert set(old["elements"]) <= set(new["elements"]), "no id of the supply went"


@pytest.mark.heavy
@EVERY
def test_the_two_hole_lug_mates_the_published_poles(name, index):
    entry = index[f"ufispace/{name}@2"]
    seats = {c["id"]: c for c in entry["cages"] if c["id"] in {s for _, s in SUPPLIES[name]["roles"]}}
    assert sorted(seats) == sorted(s for _, s in SUPPLIES[name]["roles"])
    for c in seats.values():
        assert (c["kind"], c["interface"], c["accepts"]) == ("connector", KEY, [LUG])
    assert [p["id"] for p in entry["dc-ports"]] == ["input"]
    assert not index[f"ufispace/{name}@1"].get("dc-ports")


@EVERY
def test_every_device_seats_version_2_in_its_dc_builds_and_still_accepts_version_1(name):
    old, new = f"ufispace/{name}@1", f"ufispace/{name}@2"
    for dev, d in device_sources(name).items():
        bays = [b for b in d["views"]["rear"]["components"]["bays"] if old in b.get("accepts", [])]
        assert len(bays) == 2, dev
        for b in bays:
            assert new in b["accepts"], (dev, b["id"])
        dc = [c for c in d["configurations"].values() if c.get("power") == "dc"]
        assert dc, dev
        for c in dc:
            assert (c.get("bays") or {}) == {"psu-0": new, "psu-1": new}, dev


@EVERY
def test_a_supply_whose_poles_are_unstated_is_declared_in_a_gap_on_every_device_that_seats_it(name):
    new = f"ufispace/{name}@2"
    for dev, d in device_sources(name).items():
        gaps = [g for g in d.get("gaps", []) if g["what"] == "dc-polarity"]
        if SUPPLIES[name]["gap"]:
            assert len(gaps) == 1 and new in gaps[0]["scope"], dev
            assert gaps[0]["reason"] == "needs-drawing" and len(gaps[0]["wanted"]) >= 40, dev
        else:
            assert gaps == [], dev


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    refs = {f"ufispace/{n}@{m}" for n in SUPPLIES for m in (1, 2)}
    assert [(r["part"], r["code"]) for r in rows if r["part"] in refs and r["code"] == "C19"] == []

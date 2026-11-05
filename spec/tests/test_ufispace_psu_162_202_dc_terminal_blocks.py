"""The UfiSpace PSU-162 and PSU-202 DC supplies draw the terminal block the vendor's guides show, offer two poles and state their DC input.

Both supplies fit a screw-type terminal block under a plastic cover: two poles stacked one above the other, each pole two
screws side by side, a two-hole lug on each pole (the guides' Figures 25 and 26 for the S9600-30DX and the S9600-56DX, and the
lug of Figure 22, whose hole centres are printed as a range, .65/.61 in., that holds 5/8 in.). The black cable of the negative
voltage range lands on the upper pole and the red RTN cable on the lower. The first drawing of each supply put one screw in
each row, and the PSU-162's put the legend "+" over "-" the wrong way round. Each is redrawn as version 2 of its part
(`v2/`), which composes the two poles as parts that present a registered stud pair a two-hole lug lands on, and states one DC
input port whose poles are those two parts, with the roles the vendor's guides print on the cables:

  - the skin draws four screws, two to a pole, the two poles one above the other on one vertical line, inside a block that holds
    a pair 5/8 in. apart, and the `terminal-block` (PSU-202) or `dc-input` (PSU-162) element is that block's box;
  - the supply composes juniper/mx240-dc-pole@1 twice, as `pole-batt` (upper) and `pole-rtn` (lower), each standing on the middle
    of the two screws the skin draws in its row;
  - that pole presents `stud-pair-5-8`, and generic/two-hole-lug-5-8@1 mates it;
  - the `dc` block has one input port, `input`, with `batt` on `pole-batt` and `rtn` on `pole-rtn`, the cable size every guide of
    the supply prints, the input current every datasheet of its devices prints, no voltage, and the entries of `provenance` that
    its `source` names;
  - every id of the supply is kept, version 1 keeps its drawing and names version 2 as its successor, and every device that
    seats the supply in a DC build seats version 2 while its supply bays still accept version 1.

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
POLE = "juniper/mx240-dc-pole@1"
LUG = "generic/two-hole-lug-5-8@1"
KEY = "stud-pair-5-8"
PITCH = 15.875              # 5/8 in., inside the .65/.61 in. range the lug's Figure 22 prints
POLE_MIDDLE = (9.6375, 1.7)  # the pole's `mate` point: the middle of its two screws

SUPPLIES = {
    "psu-162-dc": {"block": "dc-input", "rating": 50,
                   "devices": ["s9600-30dx", "s9600-32x", "s9600-64x"]},
    "psu-202-dc": {"block": "terminal-block", "rating": 60,
                   "devices": ["s9600-56dx", "s9610-46dx", "s9610-48dx", "s9700-23d", "s9700-53dx", "s9705-48d"]},
}
ROLES = [("batt", "pole-batt"), ("rtn", "pole-rtn")]     # upper pole first, as the guides' Figure 25 stands
EVERY = pytest.mark.parametrize("name", sorted(SUPPLIES))


def contract(name, major=2):
    return yaml.safe_load((LIB / f"components/ufispace/{name}/v{major}/contract.yaml").read_text())


def rect(e):
    return [float(e.get(k)) for k in ("x", "y", "width", "height")]


def art(name):
    """The plate of the skin's block group, and the screw circles in it."""
    root = ET.parse(LIB / f"components/ufispace/{name}/v2/skins/default.svg").getroot()
    group = next(e for e in root.iter(f"{SVG}g") if e.get("id") == SUPPLIES[name]["block"])
    plate = rect(group.find(f"{SVG}rect"))
    circles = [(float(c.get("cx")), float(c.get("cy")), float(c.get("r"))) for c in group.iter(f"{SVG}circle")]
    return plate, circles


def rows(name):
    """The four screws as two rows, upper first, each row left to right."""
    _, circles = art(name)
    ys = sorted({y for _, y, _ in circles})
    return [sorted((x, y) for x, yy, _ in circles if yy == y) for y in ys]


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def device_sources(name):
    return {d: yaml.safe_load((LIB / f"devices/ufispace/{d}/device.yaml").read_text()) for d in SUPPLIES[name]["devices"]}


def test_the_pole_presents_the_stud_pair_and_the_two_hole_lug_mates_it():
    pole = yaml.safe_load((LIB / "components/juniper/mx240-dc-pole/v1/contract.yaml").read_text())
    lug = yaml.safe_load((LIB / "components/generic/two-hole-lug-5-8/v1/contract.yaml").read_text())
    assert pole["interface"] == KEY and lug["mates"] == KEY
    assert [q["at"][0] for q in pole["parts"]] == [0, PITCH]
    assert pole["size"]["w"] == pytest.approx(PITCH + 3.4)


@EVERY
def test_the_skin_draws_two_rows_of_two_screws_a_pair_apart_inside_the_block(name):
    plate, _ = art(name)
    upper, lower = rows(name)
    assert len(upper) == len(lower) == 2
    assert [x for x, _ in upper] == pytest.approx([x for x, _ in lower]), "the two poles stand on one vertical line"
    for row in (upper, lower):
        assert row[1][0] - row[0][0] == pytest.approx(PITCH, abs=0.01)
    assert lower[0][1] > upper[0][1]
    r = art(name)[1][0][2]
    for x, y in upper + lower:
        assert plate[0] <= x - r and x + r <= plate[0] + plate[2] and plate[1] <= y - r and y + r <= plate[1] + plate[3], (x, y)


@EVERY
def test_the_element_is_the_box_the_skin_draws_and_no_id_of_the_supply_went(name):
    d, old = contract(name), contract(name, 1)
    box = SUPPLIES[name]["block"]
    plate, _ = art(name)
    assert sorted(d["elements"]) == sorted(old["elements"])
    assert d["elements"][box]["class"] == "inlet"
    assert d["elements"][box]["at"] + d["elements"][box]["size"] == pytest.approx(plate)


@EVERY
def test_the_redraw_is_version_2_and_version_1_keeps_its_drawing_and_names_it(name):
    new, old = contract(name), contract(name, 1)
    assert new["version"].split(".")[0] == "2" and old["version"].split(".")[0] == "1"
    assert new["description"] == old["description"], "the exported module type quotes the description"
    assert old["superseded-by"] == f"ufispace/{name}@2" and "superseded-by" not in new
    assert "parts" not in old and "dc" not in old


@EVERY
def test_the_supply_composes_two_poles_each_on_the_middle_of_a_row_of_screws(name):
    got = {q["id"]: (q["ref"], q["at"]) for q in contract(name)["parts"]}
    assert sorted(got) == sorted(i for _, i in ROLES)
    for (_, pole_id), row in zip(ROLES, rows(name)):
        ref, at = got[pole_id]
        assert ref == POLE
        middle = ((row[0][0] + row[1][0]) / 2, row[0][1])
        assert (at[0] + POLE_MIDDLE[0], at[1] + POLE_MIDDLE[1]) == pytest.approx(middle, abs=0.01), pole_id


@EVERY
def test_the_dc_port_is_one_input_with_the_cables_roles_on_the_two_poles(name):
    ports = contract(name)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == ROLES
    assert port["rating-a"] == SUPPLIES[name]["rating"]
    assert port["awg"] == [6]
    assert "voltage" not in port


@EVERY
def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from(name):
    d = contract(name)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "rating-a", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Figure 25" in d["provenance"][source["poles"]]
    assert d["provenance"]["block"].startswith("estimated")


@pytest.mark.heavy
@EVERY
def test_the_build_publishes_two_poles_that_accept_the_two_hole_lug_and_one_dc_port(name, index):
    entry = index[f"ufispace/{name}@2"]
    seats = {c["id"]: c for c in entry["cages"] if c["id"] in dict((i, 0) for _, i in ROLES)}
    assert sorted(seats) == sorted(i for _, i in ROLES)
    for c in seats.values():
        assert (c["kind"], c["interface"], c["accepts"]) == ("connector", KEY, [LUG])
    assert [p["id"] for p in entry["dc-ports"]] == ["input"]
    assert [(q["role"], q["slot"]) for q in entry["dc-ports"][0]["poles"]] == ROLES
    old = index[f"ufispace/{name}@1"]
    assert not old.get("dc-ports")


@EVERY
def test_every_device_seats_version_2_in_its_dc_build_and_still_accepts_version_1(name):
    old, new = f"ufispace/{name}@1", f"ufispace/{name}@2"
    for dev, d in device_sources(name).items():
        bays = [b for b in d["views"]["rear"]["components"]["bays"] if old in b.get("accepts", [])]
        assert len(bays) == 2, dev
        for b in bays:
            assert new in b["accepts"], (dev, b["id"])
        seated = [c for c in d["configurations"].values() if old in (c.get("bays") or {}).values() or new in (c.get("bays") or {}).values()]
        assert seated, dev
        for c in seated:
            assert set(c["bays"].values()) == {new}, dev


@EVERY
def test_every_device_says_the_height_of_the_pair_is_an_estimate_and_what_would_replace_it(name):
    new = f"ufispace/{name}@2"
    for dev, d in device_sources(name).items():
        gaps = [g for g in d["gaps"] if g["what"] == "dc-terminal-height"]
        assert len(gaps) == 1 and new in gaps[0]["scope"], dev
        assert gaps[0]["reason"] == "needs-drawing" and len(gaps[0]["wanted"]) >= 40, dev


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    refs = {f"ufispace/{n}@{m}" for n in SUPPLIES for m in (1, 2)}
    assert [(r["part"], r["code"]) for r in rows if r["part"] in refs and r["code"] == "C19"] == []

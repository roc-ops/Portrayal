"""The UfiSpace PSU-162 and PSU-202 DC supplies draw the terminal block the vendor's guides show, offer two poles and state their DC input.

Both supplies fit a screw-type terminal block under a plastic cover: two poles stacked one above the other, each pole two
screws one behind the other along the block, a two-hole lug on each pole (the guides' Figures 25 and 26 for the S9600-30DX and the S9600-56DX, and the
lug of Figure 22, whose hole centres are printed as a range, .65/.61 in., that holds 5/8 in.). The black cable of the negative
voltage range lands on the upper pole and the red RTN cable on the lower. The first drawing of each supply put one screw in
each row, and the PSU-162's put the legend "+" over "-" the wrong way round. Each is redrawn as version 2 of its part
(`v2/`), which composes the two poles as parts that present a registered stud pair a two-hole lug lands on, and states one DC
input port whose poles are those two parts, with the roles the vendor's guides print on the cables:

  - the skin draws the block as seen straight at the rear face: the plates the screws enter stand square to it, so they show
    edge-on, the two poles one above the other on one vertical line, no screw head facing the viewer, and the `terminal-block`
    (PSU-202) or `dc-input` (PSU-162) element is that block's box;
  - the supply composes juniper/mx240-dc-pole@1 twice, as `pole-batt` (upper) and `pole-rtn` (lower), each standing on its
    plate, a relief facet 89 degrees off the face looking left, which is how the format states a surface square to the face;
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
import math
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
POLE_WIDTH = PITCH + 3.4     # the pair's own width, which a facet square to the face foreshortens
PLATES = [("batt", "plate-batt"), ("rtn", "plate-rtn")]   # the pale plates the poles stand on, upper first

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


def skin_root(name):
    return ET.parse(LIB / f"components/ufispace/{name}/v2/skins/default.svg").getroot()


def art(name):
    """The box of the skin's block group, and the two pale plates in it (upper first), each as x, y, w, h."""
    root = skin_root(name)
    group = next(e for e in root.iter(f"{SVG}g") if e.get("id") == SUPPLIES[name]["block"])
    plate = rect(group.find(f"{SVG}rect"))
    plates = [rect(next(e for e in group.iter(f"{SVG}rect") if e.get("id") == pid)) for _, pid in PLATES]
    return plate, plates


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
def test_the_skin_draws_the_block_as_seen_straight_on_with_the_plates_edge_on(name):
    """Figure 25: the plates and screws stand square to the rear face, so no screw head faces the viewer."""
    block, plates = art(name)
    upper, lower = plates
    assert upper[0] == pytest.approx(lower[0]), "the two poles stand on one vertical line"
    assert lower[1] > upper[1]
    for p in plates:
        assert p[2] < 0.5, "a plate seen edge-on is a line"
        assert block[0] <= p[0] and p[0] + p[2] <= block[0] + block[2]
        assert block[1] <= p[1] and p[1] + p[3] <= block[1] + block[3]
    assert not list(skin_root(name).iter(f"{SVG}circle")) or all(
        c.get("id") == "status-led" for c in skin_root(name).iter(f"{SVG}circle")), "no screw drawn face-on"


@EVERY
def test_the_element_is_the_box_the_skin_draws_and_no_id_of_the_supply_went(name):
    d, old = contract(name), contract(name, 1)
    box = SUPPLIES[name]["block"]
    plate, _ = art(name)
    assert set(old["elements"]) <= set(d["elements"]) and set(d["elements"]) - set(old["elements"]) == {p for _, p in PLATES}
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
def test_the_supply_composes_two_poles_each_standing_on_its_plate_square_to_the_face(name):
    d = contract(name)
    got = {q["id"]: q for q in d["parts"]}
    facets = {f["node"]: f for f in d["relief"]["features"] if "facet" in f}
    assert sorted(got) == sorted(i for _, i in ROLES)
    _, plates = art(name)
    for (_, pole_id), (_, plate_id), box in zip(ROLES, PLATES, plates):
        q = got[pole_id]
        assert q["ref"] == POLE and q["on"] == plate_id
        assert facets[plate_id]["facet"] == {"deg": 89, "facing": "left"}
        assert facets[plate_id]["confidence"] == "estimated"
        x, y = q["at"]
        assert box[0] - 0.5 <= x and x + POLE_WIDTH * math.cos(math.radians(89)) <= box[0] + box[2] + 0.5, pole_id
        assert y + POLE_MIDDLE[1] == pytest.approx(box[1] + box[3] / 2, abs=0.01), "the pair is level with its plate"


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

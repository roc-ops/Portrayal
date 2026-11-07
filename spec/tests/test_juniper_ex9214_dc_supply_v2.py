"""The EX9214 high-capacity DC supply is redrawn from its guide as version 2, and its two inputs are places a cable lands.

The supply's drawn face did not match the guide's figures: the power switch, the door over the input mode switch and the four lamps
are at the top as the supply stands in the chassis, a vertical handle is below them, and a terminal strip printed `INP0` and `INP1`
over four legends (-48V, RTN, RTN, -48V) sits about three fifths of the way down, above a lower cover; version 1 drew the
switch at the top middle, the lamps at the upper left, a plain strip three quarters of the way down and no terminal at all. A redraw
that moves a drawn box is a new major, so the supply is `juniper/ex9214-pwr-mx960-4100-dc@2` and the @1 stays as it was,
`superseded-by` the @2. The @2 composes four poles of the library's two-stud 5/8 in. part, one for each legend, and states one DC input
port per input, two poles each:

  - the poles are `pole-0-batt`, `pole-0-rtn`, `pole-1-rtn` and `pole-1-batt`, left to right as the strip prints them;
  - the contract's `dc` block has two input ports, `input-0` (the first two poles) and `input-1` (the last two), with the roles the
    legends give (`batt` for -48V, `rtn` for RTN), the nominal and range the guide prints and no current and no wire size, because
    the guide's two figures per feed and the other guide's wire size are not one figure;
  - the EX9214 accepts the @2 beside the @1 in each supply bay and seats the @2 in its DC configurations.

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

NAME = "juniper/ex9214-pwr-mx960-4100-dc"
SUPPLY = f"{NAME}@2"
OLD = f"{NAME}@1"
POLE = "juniper/mx240-dc-pole@1"
SCREW = "common/terminal-screw-34@1"
PAIR_LUG = "generic/two-hole-lug-5-8@1"
# the legends' centres across the 101.6 x 368.3 face, left to right, and the centre down of every pair of studs
LEGEND_X = [12.3, 37.1, 63.0, 88.4]
POLE_Y = 265.0
# the pole part is 19.275 x 3.4 with its pair midpoint at (9.6375, 1.7); it is turned a quarter about that midpoint
POLE_HALF = (9.6375, 1.7)
POLES = [("pole-0-batt", LEGEND_X[0]), ("pole-0-rtn", LEGEND_X[1]), ("pole-1-rtn", LEGEND_X[2]), ("pole-1-batt", LEGEND_X[3])]
PORTS = [("input-0", [("batt", "pole-0-batt"), ("rtn", "pole-0-rtn")]),
         ("input-1", [("rtn", "pole-1-rtn"), ("batt", "pole-1-batt")])]
KEPT_ELEMENTS = ["handle", "led-dc-ok", "led-inp0-ok", "led-inp1-ok", "led-ps-fail", "switch"]
DC_CONFIGURATIONS = ["red3b-dc", "red3c-dc", "redund3-dc", "redund3a-dc"]
V1_SKIN_SHA256 = "e8275c139c56fa2544bdb155880c894b8c31efa15cb6267322eb9a09da5a85bd"


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
    assert v2["version"] == "2.0.0" and v2["name"] == "ex9214-pwr-mx960-4100-dc"
    assert v1["version"] == "1.0.1" and v1["superseded-by"] == SUPPLY
    assert "dc" not in v1 and "parts" not in v1 and sorted(v1["elements"]) == sorted(
        ["led-inp0-ok", "led-inp1-ok", "led-dc-ok", "led-ps-fail", "switch", "handle"])


def test_the_old_skin_is_kept_byte_for_byte():
    skin = (LIB / "components" / NAME / "v1/skins/default.svg").read_bytes()
    assert hashlib.sha256(skin).hexdigest() == V1_SKIN_SHA256


def test_the_supply_keeps_its_part_number_size_and_ids():
    v1, v2 = contract(OLD), contract(SUPPLY)
    assert v2["part-numbers"] == v1["part-numbers"]
    assert v2["size"] == v1["size"] and v2["class"] == "psu"
    assert sorted(v2["elements"]) == KEPT_ELEMENTS


def test_the_supply_composes_four_poles_and_nothing_else():
    want = [dict(ref=POLE, id=i, at=[round(x - POLE_HALF[0], 4), round(POLE_Y - POLE_HALF[1], 4)], rotate=90) for i, x in POLES]
    assert contract(SUPPLY)["parts"] == want


def test_the_pole_part_presents_the_pair_key_and_the_two_hole_lug_mates_it():
    assert contract(POLE)["interface"] == "stud-pair-5-8"
    assert contract(PAIR_LUG)["mates"] == "stud-pair-5-8"
    assert [p["id"] for p in contract(POLE)["parts"]] == ["1", "2"]
    assert contract(POLE)["parts"][1]["at"][0] == 15.875


def test_the_face_is_drawn_the_way_the_guide_shows_it():
    d = contract(SUPPLY)
    skin = (LIB / "components" / NAME / "v2/skins/default.svg").read_text()
    ids = re.findall(r'id="([^"]+)"', skin)
    for want in ("face", "switch", "door", "lamps", "handle", "strip", "silkscreen", "cover"):
        assert want in ids, want
    h = d["size"]["h"]
    lamp_y = [d["elements"][e]["at"][1] / h for e in ("led-inp0-ok", "led-inp1-ok", "led-dc-ok", "led-ps-fail")]
    assert lamp_y == sorted(lamp_y) and lamp_y[-1] < 0.2
    assert 0.55 < POLE_Y / h < 0.75
    assert d["elements"]["handle"]["at"][1] / h < 0.3
    strip = re.search(r'<rect id="strip" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', skin)
    assert 0.55 < float(strip.group(2)) / h < 0.65
    legends = re.findall(r'<text class="legend" x="([\d.]+)"[^>]*>([^<]+)</text>', skin)
    assert [t for _, t in legends] == ["-48V", "RTN", "RTN", "-48V"]
    assert [float(x) for x, _ in legends] == LEGEND_X


def test_the_dc_ports_are_two_inputs_with_two_poles_each():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == [i for i, _ in PORTS]
    for port, (_, poles) in zip(ports, PORTS):
        assert port["direction"] == "input"
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles
    assert len({q["slot"] for p in ports for q in p["poles"]}) == 4


def test_each_port_states_the_nominal_and_range_and_no_current_and_no_wire_size_and_no_side():
    for port in contract(SUPPLY)["dc"]["ports"]:
        assert port["voltage"] == {"nominal": -48, "range": [-40, -72]}
        assert "rating-a" not in port and "awg" not in port and "side" not in port
        assert port["source"] == {"poles": "poles", "voltage": "voltage"}


@pytest.mark.parametrize("key", ["rating", "awg"])
def test_the_missing_current_and_wire_size_are_said_not_left_out_silently(key):
    text = words(contract(SUPPLY)["provenance"][key])
    assert text.startswith("NOT STATED") and "the ports state none" in text


def test_every_fact_the_ports_state_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    for key in ("poles", "voltage", "rating", "awg", "seats", "skin", "lug"):
        assert len(words(d["provenance"][key])) >= 40, key
    assert "RTN" in words(d["provenance"]["poles"]) and "-48V" in words(d["provenance"]["poles"])
    assert words(d["provenance"]["seats"]).startswith("ESTIMATED")
    assert "Figure 46" in words(d["provenance"]["lug"])


def test_the_build_publishes_the_pole_seats_and_two_dc_ports(index):
    entry = index[SUPPLY]
    assert [(p["id"], p["direction"]) for p in entry["dc-ports"]] == [(i, "input") for i, _ in PORTS]
    for port, (_, poles) in zip(entry["dc-ports"], PORTS):
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles
    published = {c["id"] for c in entry["cages"]}
    for ident, _ in POLES:
        assert ident in published or any(c.startswith(f"{ident}/") for c in published), ident


def test_the_chassis_accepts_both_majors_and_seats_the_new_one_in_its_dc_configurations():
    d = yaml.safe_load((LIB / "devices/juniper/ex9214/device.yaml").read_text())
    bays = [b for v in d["views"].values() for b in v.get("components", {}).get("bays", [])]
    supply_bays = [b for b in bays if OLD in b.get("accepts", [])]
    assert len(supply_bays) == 4 and all(SUPPLY in b["accepts"] for b in supply_bays)
    for name in DC_CONFIGURATIONS:
        seated = d["configurations"][name]["bays"]
        assert {v for k, v in seated.items() if k.startswith("pem")} == {SUPPLY}, name


def test_the_chassis_took_one_minor_and_its_lock_holds_the_two_ports_of_each_supply():
    folder = LIB / "devices/juniper/ex9214"
    lock = json.loads((folder / "device.lock.json").read_text())
    assert re.search(r"^version: 0\.3\.0$", (folder / "device.yaml").read_text(), re.M)
    assert lock["version"] == "0.3.0"
    assert lock["composed-refs"][SUPPLY].startswith("2.0.0+")
    assert lock["composed-refs"][POLE].startswith("1.0.0+")
    ports = {path.rsplit("/", 1)[1] for path, refs in lock["dc-ports"].items() if SUPPLY in refs}
    assert ports == {"input-0", "input-1"}


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] in (OLD, SUPPLY) and r["code"] == "C19"] == []

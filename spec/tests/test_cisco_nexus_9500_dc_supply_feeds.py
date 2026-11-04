"""The Cisco Nexus 9500 3 kW DC supply is redrawn from its guide as version 2, and its two inputs are places a cable lands.

The supply's drawn face did not match the guide's figures: the lamps and the switch are at the top as the supply stands in the
chassis, a hexagon vent grille runs down the face, the release lever runs along the right edge, and the terminal box is down the
lower left with four posts in a column under a three-screw safety cover, printed -1+ and +2- (inputs 1 and 2). A redraw that moves
a drawn box is a new major, so the supply is `cisco/n9k-pdc-3000w-b@2` and the @1 stays as it was, `superseded-by` the @2. The @2 composes the four posts as seats a ring lug lands on, and states one DC input port per input, two poles each:

  - cisco/n9k-pdc-3000w-b@2 composes common/terminal-screw-34@1 four times, as `pole-1-neg`, `pole-1-pos`, `pole-2-pos` and
    `pole-2-neg`, at the centres of the four posts its skin draws, in the order the guide gives them from the top (negative,
    positive, positive, negative); the posts are a declared stand-in on that existing part, which claims no post size;
  - the contract's `dc` block has two input ports, `input-1` (the first two posts) and `input-2` (the last two), with the roles
    the guide's words give (`neg` and `pos`), the one wire size the guide recommends and no voltage and no current;
  - the supply has no earth terminal of its own, so no ground seat is composed;
  - the Nexus 9504, 9508 and 9516 accept the @2 beside the @1 and seat the @2 in their DC configuration, each taking one minor.

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

NAME = "cisco/n9k-pdc-3000w-b"
SUPPLY = f"{NAME}@2"
OLD = f"{NAME}@1"
SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"
# the posts as (id, centre across, centre down) on the 44.45 x 133.35 face, from the top as the supply stands in the chassis
POSTS = [("pole-1-neg", 7.6, 43.6), ("pole-1-pos", 7.6, 62.2), ("pole-2-pos", 7.6, 80.8), ("pole-2-neg", 7.6, 99.4)]
# the ports as (id, [(role, slot)]), the poles of each in the order the guide gives them from the top
PORTS = [("input-1", [("neg", "pole-1-neg"), ("pos", "pole-1-pos")]),
         ("input-2", [("pos", "pole-2-pos"), ("neg", "pole-2-neg")])]
KEPT_ELEMENTS = ["fail", "ok"]
# the three chassis and the version each had before this change; each takes one minor
CHASSIS = {"n9k-c9504": "2.3.0", "n9k-c9508": "1.3.0", "n9k-c9516": "2.3.0"}
V1_SKIN_SHA256 = "7599f10779cddd62d91f42930b4017438e84c7c8ccbdc34f89946d29b7d482cd"


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
    assert v2["version"] == "2.0.0" and v2["name"] == "n9k-pdc-3000w-b"
    assert v1["superseded-by"] == SUPPLY
    assert "dc" not in v1 and "parts" not in v1 and sorted(v1["elements"]) == KEPT_ELEMENTS


def test_the_old_skin_is_kept_byte_for_byte():
    skin = (LIB / "components" / NAME / "v1/skins/default.svg").read_bytes()
    assert hashlib.sha256(skin).hexdigest() == V1_SKIN_SHA256


def test_the_supply_composes_four_terminal_screws_and_nothing_else():
    assert contract(SUPPLY)["parts"] == [dict(ref=SCREW, id=i, at=[round(x - 1.7, 2), round(y - 1.7, 2)]) for i, x, y in POSTS]


def test_the_screw_part_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_seats_stand_at_the_centres_of_the_four_posts_the_skin_draws():
    skin = (LIB / "components" / NAME / "v2/skins/default.svg").read_text()
    block = re.search(r'<g id="posts"[^>]*>(.*?)</g>', skin, re.S).group(1)
    centres = [[float(x), float(y)] for x, y in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="3(?:\.0)?"', block)]
    assert centres == [[x, y] for _, x, y in POSTS]
    for part, centre in zip(contract(SUPPLY)["parts"], centres):
        assert [round(part["at"][0] + 1.7, 2), round(part["at"][1] + 1.7, 2)] == centre


def test_the_lamps_keep_their_ids_and_the_face_is_drawn_the_way_the_guide_shows_it():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == KEPT_ELEMENTS
    skin = (LIB / "components" / NAME / "v2/skins/default.svg").read_text()
    ids = re.findall(r'id="([^"]+)"', skin)
    for want in ("plate", "vent", "handle", "ok", "fail", "switch", "terminal-box", "posts"):
        assert want in ids, want
    # the lamps are at the top, FAIL above OK, beside the switch; the box is down the left
    ok = d["elements"]["ok"]["at"][1]
    fail = d["elements"]["fail"]["at"][1]
    assert fail < ok < 20
    box = re.search(r'<g id="terminal-box">\s*<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', skin)
    assert box and float(box.group(1)) < 5 and float(box.group(2)) > 20 and float(box.group(4)) > 70


def test_the_dc_ports_are_two_inputs_with_two_poles_each():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == [i for i, _ in PORTS]
    for port, (_, poles) in zip(ports, PORTS):
        assert port["direction"] == "input"
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles
    assert len({q["slot"] for p in ports for q in p["poles"]}) == 4


def test_each_port_states_the_one_wire_size_and_no_voltage_no_current_and_no_side():
    for port in contract(SUPPLY)["dc"]["ports"]:
        assert port["awg"] == [6]
        assert "voltage" not in port and "rating-a" not in port and "side" not in port
        assert port["source"] == {"poles": "poles", "awg": "awg"}


def test_the_supply_has_no_earth_seat():
    d = contract(SUPPLY)
    assert [p for p in d["parts"] if p["ref"].startswith("common/ground")] == []
    assert "earth" in d["provenance"] and words(d["provenance"]["earth"]).startswith("NONE")


def test_every_fact_the_ports_state_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    for key in ("poles", "awg", "seats", "skin", "earth", "voltage", "rating"):
        assert len(words(d["provenance"][key])) >= 40, key
    poles = words(d["provenance"]["poles"])
    assert "four slots for four power terminals" in poles and "negative [-], positive [+], positive [+]" in poles
    assert "6-AWG cables recommended" in words(d["provenance"]["awg"])


@pytest.mark.parametrize("key", ["voltage", "rating"])
def test_the_missing_voltage_and_current_are_said_not_left_out_silently(key):
    text = words(contract(SUPPLY)["provenance"][key])
    assert text.startswith("NOT STATED") and "the ports state none" in text


def test_the_stand_in_posts_are_declared_in_the_seats_entry():
    text = words(contract(SUPPLY)["provenance"]["seats"])
    assert text.startswith("A DECLARED STAND-IN") and "two nuts" in text


def test_the_build_publishes_four_seats_that_accept_the_ring_lug_and_two_dc_ports(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _, _ in POSTS]
    assert [(p["id"], p["direction"]) for p in entry["dc-ports"]] == [(i, "input") for i, _ in PORTS]
    for port, (_, poles) in zip(entry["dc-ports"], PORTS):
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles


@pytest.mark.parametrize("name", sorted(CHASSIS))
def test_each_chassis_accepts_both_majors_and_seats_the_new_one_in_its_dc_configuration(name):
    d = yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())
    bays = [b for v in d["views"].values() for b in v.get("components", {}).get("bays", [])]
    supply_bays = [b for b in bays if OLD in b.get("accepts", [])]
    assert supply_bays and all(SUPPLY in b["accepts"] for b in supply_bays)
    seated = d["configurations"]["psu-dc"]["bays"]
    assert seated and set(seated.values()) == {SUPPLY}


@pytest.mark.parametrize("name", sorted(CHASSIS))
def test_each_chassis_took_one_minor_and_its_lock_holds_the_two_ports_of_each_supply(name):
    folder = LIB / "devices/cisco" / name
    lock = json.loads((folder / "device.lock.json").read_text())
    assert re.search(rf"^version: {re.escape(CHASSIS[name])}$", (folder / "device.yaml").read_text(), re.M)
    assert lock["version"] == CHASSIS[name]
    assert lock["composed-refs"][SUPPLY].startswith("2.0.0+")
    assert lock["composed-refs"][SCREW].startswith("1.0.1+")
    ports = {path.rsplit("/", 1)[1] for path, refs in lock["dc-ports"].items() if SUPPLY in refs}
    assert ports == {"input-1", "input-2"}


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] in (OLD, SUPPLY) and r["code"] == "C19"] == []

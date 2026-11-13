"""The Edgecore DCS240 and DCS511 DC supply is drawn from its photograph, as a new major, and its DC input is a place a cable lands.

The supply used to borrow the AC supply's face, with a three-slot green block that no document shows. Its face is now drawn from the
photograph in the vendor's quick start guides (a black two-screw block with "-" and "+" under the screws, a black bail at the left, a
perforated grille, a cross-head earth screw at the upper right and a red latch at the right), every position an estimate. Drawing it
moved three of the face's four boxes, and a moved box is a major of the part (decided 2026-11-03), so the redraw is
edgecore/dcs240-psu-dc@2 and @1 keeps the face it had:

  - edgecore/dcs240-psu-dc@2 composes common/terminal-screw-34@1 twice, as `pole-batt` and `pole-rtn`, and common/ground-screw@1 once,
    as `earth`; the ground part is a declared stand-in, because no document held gives the thread of the earth screw;
  - its `dc` block has one input port, `input`, with the two roles the guide calls out, the wire size and the current the guide
    gives, no voltage, and the entries of `provenance` that its `source` names; the earth screw stands beside the block, not on it,
    so it is a ground part of its own, outside the port (decided 2026-11-02);
  - its four element ids stay, and so does the latch's box; the skin draws all four inside its 54.4 by 40.0 face; its description
    says what the face carries and no longer says it is the AC variant's;
  - edgecore/dcs240-psu-dc@1 is main's part, unchanged but for its patch version and `superseded-by` the new major;
  - the DCS240 and DCS511 seat @2 in their two DC configurations, and their supply bays accept both majors.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "edgecore/dcs240-psu-dc@2"
OLD = "edgecore/dcs240-psu-dc@1"
SCREW = "common/terminal-screw-34@1"
EARTH = "common/ground-screw@1"
LUG = "generic/ring-lug@1"
DEVICES = {"edgecore/dcs240": "1.2.1", "edgecore/dcs511": "2.1.1"}
DESCRIPTION = ("The -48 VDC power supply of the Edgecore DCS240 (AS9726-32DB) - a 54.4 x 40 CRPS face with a two-screw DC terminal "
               "block and an earth screw beside it. Rated 1600 W.")
OLD_DESCRIPTION = ("The -48 VDC power supply of the Edgecore DCS240 (AS9726-32DB) - the same 54.4 x 40 CRPS face as the AC variant "
                   "with a DC terminal in place of the C14 inlet. Rated 1600 W.")
# main's skin of @1, byte for byte
OLD_SKIN_SHA = "f87e8c4efce4dc6ed4bf5b85edf8880205c45d99d2cdd3db0b38715f462115bd"


def words(text):
    return " ".join(str(text).split())


def other(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def contract():
    return other(SUPPLY)


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_supply_composes_two_terminal_screws_and_one_ground_part_and_nothing_else():
    assert contract()["parts"] == [
        dict(ref=SCREW, id="pole-batt", at=[16.16, 25.33]),
        dict(ref=SCREW, id="pole-rtn", at=[30.72, 25.33]),
        dict(ref=EARTH, id="earth", at=[41.85, 5.33]),
    ]


def test_the_screw_and_the_ground_part_present_terminal_stud_and_the_ring_lug_mates_it():
    assert other(SCREW)["interface"] == "terminal-stud"
    assert other(EARTH)["interface"] == "terminal-stud"
    assert other(LUG)["mates"] == "terminal-stud"


def test_the_supply_is_a_new_major_that_keeps_its_four_ids_its_latch_and_its_size():
    d = contract()
    assert d["version"] == "2.0.0" and "superseded-by" not in d
    assert sorted(d["elements"]) == ["dc-inlet", "handle", "latch", "vent-field"]
    assert d["elements"]["latch"] == {"at": [45.40, 19.40], "size": [9.00, 20.60], "class": "latch"}
    assert d["attrs"] == other(OLD)["attrs"] and d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["input"] == "dc"
    assert d["size"] == {"w": 54.4, "h": 40.0}
    assert "A NEW MAJOR, decided 2026-11-03" in words(d["provenance"]["major"])


def test_the_description_says_what_the_face_carries_and_not_that_it_is_the_ac_variants():
    d = contract()
    assert words(d["description"]) == DESCRIPTION
    assert "AC variant" not in d["description"]


def test_the_old_major_is_mains_part_retired_in_favour_of_the_new_one():
    d = other(OLD)
    assert d["version"] == "1.2.1" and d["superseded-by"] == SUPPLY
    assert "parts" not in d and "dc" not in d and "unplaced" not in d
    assert words(d["description"]) == OLD_DESCRIPTION
    assert d["elements"] == {
        "handle": {"at": [17.70, 2.00], "size": [6.00, 37.70], "class": "handle"},
        "latch": {"at": [45.40, 19.40], "size": [9.00, 20.60], "class": "latch"},
        "vent-field": {"at": [4.20, 3.60], "size": [19.40, 32.40], "class": "vent"},
        "dc-inlet": {"at": [30.0, 12.0], "size": [20.0, 16.0], "class": "inlet"},
    }
    skin = LIB / "components/edgecore/dcs240-psu-dc/v1/skins/default.svg"
    assert hashlib.sha256(skin.read_bytes()).hexdigest() == OLD_SKIN_SHA


def test_the_skin_draws_the_four_ids_and_the_two_screw_heads_and_the_earth_screw_inside_its_face():
    svg = ET.parse(LIB / "components/edgecore/dcs240-psu-dc/v2/skins/default.svg").getroot()
    ids = {e.get("id") for e in svg.iter() if e.get("id")}
    assert {"handle", "latch", "vent-field", "dc-inlet", "body"} <= ids
    assert svg.get("viewBox") == "0 0 54.4 40"
    pts = {"pole-batt": (16.16, 25.33), "pole-rtn": (30.72, 25.33), "earth": (41.85, 5.33)}
    for ident, (x, y) in pts.items():
        size = 5.6 if ident == "earth" else 3.4
        assert 0 <= x and 0 <= y and x + size <= 54.4 and y + size <= 40.0, ident


def test_every_element_box_lies_inside_the_face():
    for name, e in contract()["elements"].items():
        (x, y), (w, h) = e["at"], e["size"]
        assert x >= 0 and y >= 0 and x + w <= 54.4 + 1e-9 and y + h <= 40.0 + 1e-9, name


def test_the_dc_port_is_one_input_with_two_poles_in_the_callouts_order_and_the_earth_is_not_one_of_them():
    ports = contract()["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("batt", "pole-batt"), ("rtn", "pole-rtn")]
    assert "earth" not in [q["slot"] for q in port["poles"]]
    assert port["awg"] == [8] and port["rating-a"] == 40
    assert "voltage" not in port


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract()
    source = d["dc"]["ports"][0]["source"]
    assert source == {"poles": "poles", "rating-a": "rating", "awg": "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    assert "Connect Power" in d["provenance"][source["poles"]]


def test_the_earth_is_declared_a_stand_in_and_said_to_be_outside_the_port():
    text = words(contract()["provenance"]["earth"])
    assert text.startswith("A DECLARED STAND-IN")
    assert "outside the DC port" in text and "decided 2026-11-02" in text and "no document held gives" in text


def test_the_face_is_said_to_be_read_off_the_photograph_and_estimated_and_the_bail_and_latch_are_said_not_to_be_read_at_its_size():
    p = contract()["provenance"]
    face = words(p["face"])
    assert face.startswith("estimated") and "12.43 px/mm" in face
    assert "THE BAIL AND THE LATCH ARE NOT READ AT THE PHOTOGRAPH'S SIZE" in face
    assert "No depth is claimed" in words(p["seats"])
    assert "6/8AWG" in words(p["awg"]) and "recorded here and not stated" in words(p["awg"])


def test_the_build_publishes_a_seat_for_each_screw_and_the_earth_and_one_dc_port_of_two_poles(index):
    entry = index[SUPPLY]
    got = {c["id"]: (c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]}
    assert sorted(got) == ["earth", "pole-batt", "pole-rtn"]
    assert all(v == ("connector", "terminal-stud", [LUG]) for v in got.values())
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [("batt", "pole-batt"), ("rtn", "pole-rtn")]


def test_the_index_says_the_old_major_is_retired_and_it_publishes_no_port(index):
    old = index[OLD]
    assert old["superseded-by"] == SUPPLY
    assert not old.get("cages") and not old.get("dc-ports")


@pytest.mark.parametrize("slug", DEVICES)
def test_each_device_takes_one_minor_and_its_gap_names_the_new_major_and_no_longer_says_the_face_is_borrowed(slug):
    for name in ("layout.yaml", "device.yaml"):
        doc = yaml.safe_load((LIB / "devices" / slug / name).read_text())
        assert doc["version"] == DEVICES[slug]
        gap = next(g for g in doc["gaps"] if g["what"] == "dc-supply-face")
        text = words(gap["wanted"])
        assert "borrows" not in text and "photograph of the supply" in text and "every position on it is an estimate" in text
        assert SUPPLY in text and OLD not in text


@pytest.mark.parametrize("slug", DEVICES)
def test_each_device_seats_the_new_major_in_its_dc_configurations_and_its_supply_bays_accept_both(slug):
    doc = yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())
    bays = {b["id"]: b for b in doc["views"]["rear"]["components"]["bays"] if b["id"] in ("psu-1", "psu-2")}
    assert sorted(bays) == ["psu-1", "psu-2"]
    for bay in bays.values():
        assert bay["accepts"] == ["edgecore/dcs240-psu-ac@1", OLD, SUPPLY]
        assert bay["default"] == "edgecore/dcs240-psu-ac@1"
    configs = doc["configurations"]
    for name in ("dc-f2b", "dc-b2f"):
        assert configs[name]["bays"] == {"psu-1": SUPPLY, "psu-2": SUPPLY}, name
    assert not [n for n, c in configs.items() if OLD in ((c or {}).get("bays") or {}).values()]


def test_the_finding_this_change_closes_has_no_row_left():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    assert [r for r in doc["rows"] if r["part"] in (SUPPLY, OLD) and r["code"] == "C19"] == []
    assert doc["cap"] == len(doc["rows"])

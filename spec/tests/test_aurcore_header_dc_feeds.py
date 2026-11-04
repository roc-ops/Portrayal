"""The AurCore AIS switches' five-position power header states its two DC feeds, one port each.

The header common/terminal-header-508-5f@2 is wired `+ - earth + -` and the housing prints `1` and `2` at its ends (AurCore AIS4001P
vendor video; the ten AIS data sheets name two "Phoenix Terminal" plugs, nine of them a "dual power input"). It is placed once on
each of ten switches, on their top panel. It already presents `terminal-508-5` and a plug mates it, but it stated no DC port, so a switch that
places it offered no power end. So:

  - the part gains four connection points, one on each contact its skin draws but the earth's, and two DC ports of two poles:
    `feed-a` on the pair before the earth contact and `feed-b` on the pair after it, the roles the housing prints (`+` is `pos`,
    `-` is `neg`);
  - the earth contact is in neither port and is not a connection point;
  - no port states a voltage, a current, a wire size or a side: the printed range differs by model and no document gives the rest;
  - the ten switches take the minor the lock asks and place the part where they did; no skin is redrawn;
  - the ten rows of the issue that asked for it go and the other rows of that issue stay.

These run against the real library, a components index built by the indexer the build runs, the device locks and the records file.
They read no library/dist and render nothing.
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
HEADER = "common/terminal-header-508-5f@2"
HEADER_DIR = LIB / "components" / "common" / "terminal-header-508-5f" / "v2"
PLUG = "generic/terminal-508-5-plug@1"
SMALL = ("aurcore/ais2001", "aurcore/ais2001p", "aurcore/ais2002", "aurcore/ais2002p")
LARGE = ("aurcore/ais2003", "aurcore/ais2003p", "aurcore/ais2004", "aurcore/ais2004p", "aurcore/ais4001", "aurcore/ais4001p")
DEVICES = {**{slug: [10.92, 55.3] for slug in SMALL}, **{slug: [9.32, 37.3] for slug in LARGE}}
STAYS = ["smartoptics/dcp-2-psu-dc@1", "ds6000"]


def contract():
    return yaml.safe_load((HEADER_DIR / "contract.yaml").read_text())


def device(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


def placements(slug):
    out = []
    for name, view in (device(slug).get("views") or {}).items():
        for p in ((view.get("components") or {}).get("placements") or []):
            if p.get("ref") == HEADER:
                out.append((name, p))
    return out


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_header_is_a_minor_and_keeps_its_key_class_and_mate():
    d = contract()
    assert (d["version"], d["class"], d["interface"]) == ("2.1.0", "inlet", "terminal-508-5")
    assert d["size"] == {"w": 35.56, "h": 8.6, "d": 12.0}
    assert d["connection-points"]["mate"] == {"at": [17.78, 4.3], "direction": "front", "on": "body"}
    plug = yaml.safe_load((LIB / "components/generic/terminal-508-5-plug/v1/contract.yaml").read_text())
    assert (plug["class"], plug["mates"]) == ("port", "terminal-508-5")


def test_the_four_connection_points_stand_on_the_contacts_the_skin_draws_and_the_earth_contact_has_none():
    d = contract()
    root = ET.parse(HEADER_DIR / "skins" / "default.svg").getroot()
    rects = {e.get("id"): e for e in root.iter() if e.get("id")}
    points = d["connection-points"]
    assert sorted(points) == ["mate", "pin-1", "pin-2", "pin-4", "pin-5"]
    for n in (1, 2, 4, 5):
        r = rects[f"pin-{n}"]
        centre = [round(float(r.get("x")) + float(r.get("width")) / 2, 2), round(float(r.get("y")) + float(r.get("height")) / 2, 2)]
        assert points[f"pin-{n}"]["at"] == centre, n
        assert points[f"pin-{n}"]["direction"] == "front"
    assert points["pin-2"]["at"][0] - points["pin-1"]["at"][0] == pytest.approx(5.08)
    assert points["pin-5"]["at"][0] - points["pin-4"]["at"][0] == pytest.approx(5.08)


def test_the_part_states_one_port_per_feed_of_two_poles_and_nothing_else():
    ports = contract()["dc"]["ports"]
    assert [p["id"] for p in ports] == ["feed-a", "feed-b"]
    assert [[(q["role"], q["slot"]) for q in p["poles"]] for p in ports] == [
        [("pos", "pin-1"), ("neg", "pin-2")],
        [("pos", "pin-4"), ("neg", "pin-5")],
    ]
    for p in ports:
        assert p["direction"] == "input"
        assert p["source"] == {"poles": "poles"}
        for absent in ("voltage", "rating-a", "awg", "side", "voltage-range"):
            assert absent not in p, absent


def test_the_earth_contact_is_in_no_port():
    d = contract()
    used = {q["slot"] for p in d["dc"]["ports"] for q in p["poles"]}
    assert "pin-3" not in used and used == {"pin-1", "pin-2", "pin-4", "pin-5"}
    assert not any(q["role"] == "gnd" for p in d["dc"]["ports"] for q in p["poles"])


def test_the_provenance_says_what_is_estimated_and_what_is_not_stated():
    prov = contract()["provenance"]
    for key in ("contacts", "poles", "voltage", "rating", "awg", "side"):
        assert key in prov, key
    assert prov["contacts"].startswith("ESTIMATED")
    for key in ("voltage", "rating", "awg", "side"):
        assert prov[key].startswith("NOT STATED"), key
    for words in ("Data Sheets 1.0", "1 + - (earth) + - 2", "no seat for a ground lug"):
        assert words in prov["poles"], words


def test_the_skin_is_not_redrawn():
    root = ET.parse(HEADER_DIR / "skins" / "default.svg").getroot()
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert ids == ["body"] + [f"{k}-{n}" for n in range(1, 6) for k in ("cell", "pin")] + ["insert-1", "insert-2"]


def test_only_the_ten_aurcore_switches_place_the_header():
    found = sorted(
        str(p.relative_to(LIB / "devices").parent)
        for p in (LIB / "devices").glob("*/*/device.yaml")
        if re.search(r"common/terminal-header-508-5f@2\b", p.read_text())
    )
    assert found == sorted(DEVICES)
    for other in (LIB / "components").glob("*/*/v*/contract.yaml"):
        if other.parent != HEADER_DIR:
            assert "terminal-header-508-5f" not in "".join(str(p) for p in yaml.safe_load(other.read_text()).get("parts") or []), other


@pytest.mark.parametrize("slug", sorted(DEVICES))
def test_each_switch_places_the_header_once_on_its_top_panel_where_it_did(slug):
    got = placements(slug)
    assert len(got) == 1
    view, p = got[0]
    assert view == "top"
    assert (p["id"], p["at"], p["rotate"], p["group"]) == ("power", DEVICES[slug], 90, "power-input")
    assert "dc" not in p and "attrs" not in p


@pytest.mark.parametrize("slug", sorted(DEVICES))
def test_each_switch_takes_one_minor_and_its_lock_records_the_new_part(slug):
    doc = device(slug)
    assert doc["version"] == "2.1.0"
    lock = json.loads((LIB / "devices" / slug / "device.lock.json").read_text())
    assert lock["version"] == "2.1.0"
    assert lock["composed-refs"][HEADER].startswith("2.1.0+")


@pytest.mark.heavy
def test_the_index_carries_the_header_as_one_part_with_its_two_ports(index):
    ports = index[HEADER]["dc-ports"]
    assert [(p["id"], p["path"], p["direction"]) for p in ports] == [("feed-a", "feed-a", "input"), ("feed-b", "feed-b", "input")]
    assert [[(q["role"], q["slot"]) for q in p["poles"]] for p in ports] == [
        [("pos", "pin-1"), ("neg", "pin-2")],
        [("pos", "pin-4"), ("neg", "pin-5")],
    ]
    for p in ports:
        assert (p["voltage"], p["rating-a"], p["awg"], p["side"]) == (None, None, None, None)


def test_the_ten_rows_go_and_the_other_rows_of_the_issue_stay():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = doc["rows"]
    assert doc["cap"] == len(rows)
    assert [r for r in rows if r["part"] in {s.split("/")[1] for s in DEVICES}] == []
    for part in STAYS:
        assert len([r for r in rows if r["part"] == part and r["code"] == "C19"]) == 1, part

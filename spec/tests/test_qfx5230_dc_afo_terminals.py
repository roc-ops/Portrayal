"""The DC input of the JNP-3000W-DC-AFO supply is a place a cable lands, and says which terminal is which.

The supply drew its terminal block as a ridged cover and offered no place for a DC feed. It now composes one stud pair for
each polarity, every pair a seat that one two-hole lug lands across, and states one DC input port whose poles are those seats:

  - the supply composes juniper/mx240-dc-pole@1 twice, as `pole-rtn` and `pole-batt`, inside the footprint of the cover;
  - that pole presents `stud-pair-5-8` and generic/two-hole-lug-5-8@1 mates it;
  - the contract's `dc` block has one input port, `input`, with `rtn` on `pole-rtn` and `batt` on `pole-batt`, no voltage and no
    rating, and the entries of `provenance` that its `source` names;
  - the stud positions say they are estimated, and the contract says no held figure gives their position, which pair is which or any printed mark;
  - the cover's art, its elements and every other id of the supply are unchanged.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "juniper/qfx5230-jnp-3000w-dc-afo@1"
POLE = "juniper/mx240-dc-pole@1"
LUG = "generic/two-hole-lug-5-8@1"
POLES = [("rtn", "pole-rtn"), ("batt", "pole-batt")]
# the cover's footprint in the skin: x 42.2 to 66.6, y 3.7 to 36.1
COVER = (42.2, 3.7, 66.6, 36.1)


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_pole_presents_the_registered_pair_key_and_the_lug_mates_it():
    assert contract(POLE)["interface"] == "stud-pair-5-8"
    assert contract(LUG)["mates"] == "stud-pair-5-8"


def test_the_supply_composes_one_stud_pair_for_each_polarity_inside_the_cover():
    parts = contract(SUPPLY)["parts"]
    assert [(q["id"], q["ref"]) for q in parts] == [(i, POLE) for _, i in POLES]
    width, height = contract(POLE)["size"]["w"], contract(POLE)["size"]["h"]
    for q in parts:
        x, y = q["at"]
        assert COVER[0] <= x and x + width <= COVER[2] and COVER[1] <= y and y + height <= COVER[3]
    assert parts[0]["at"][1] < parts[1]["at"][1]


def test_the_cover_is_still_drawn_and_no_id_of_the_supply_went():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ["latch", "led-pwr", "release-latch"]
    assert d["size"] == {"w": 74.8, "h": 40.2}
    assert 'id="terminal-cover"' in (LIB / "components/juniper/qfx5230-jnp-3000w-dc-afo/v1/skins/default.svg").read_text()


def test_the_dc_port_is_one_input_with_the_text_roles_and_states_no_voltage_or_rating():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES
    assert "voltage" not in port and "rating-a" not in port and "awg" not in port


def test_the_contract_says_the_studs_are_a_stand_in_and_what_the_figure_does_and_does_not_show():
    d = contract(SUPPLY)
    seats = d["provenance"]["seats"]
    for word in ("STAND-IN", "estimated", "15.86", "printed page 49"):
        assert word in seats
    assert "Figure 39 of the QFX5230 guide shows threaded studs" in seats
    assert "no held figure gives the studs' position on the face" in seats
    poles = d["provenance"]["poles"]
    assert "-48V/-60V" in poles and "RTN" in poles and "NO FIGURE PRINTS A MARK" in poles


def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from():
    d = contract(SUPPLY)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles"}
    assert len(d["provenance"][source["poles"]]) >= 40


@pytest.mark.heavy
def test_the_build_publishes_two_seats_that_accept_the_two_hole_lug_and_one_dc_port(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "stud-pair-5-8", [LUG]) for _, i in POLES]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [(r["part"], r["code"]) for r in rows if r["part"] == SUPPLY and r["code"] == "C19"] == []

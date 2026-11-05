"""The DC terminal block of the Juniper EX2200-24T-DC and the EX2300-24T-DC is a place two DC feeds land.

Both devices drew the block of four terminals as art in the DC rear view, so they offered no place for a DC feed. Each
now places a part of its own that composes the four terminal screws and states two DC input ports, one per feed, two
poles each, and the EX2300's `dc` configuration states the power it runs on:

  - juniper/ex2200-dc-terminal@1 (36.0 x 18.4 mm, estimated) has the terminals B-, A-, B+, A+ from left to right and the
    ports `input-a` (A+, A-) and `input-b` (B+, B-);
  - juniper/ex2300-dc-terminal@1 (52.6 x 17.5 mm, photo-measured) has INPUT 1+, INPUT 1-, INPUT 2+, INPUT 2- from left to
    right and the ports `input-1` and `input-2`;
  - the two blocks differ in size and pitch, so they are two parts, each named for its device because the maker gives no
    part number for either;
  - each screw is common/terminal-screw-34@1 and presents `terminal-stud`, which generic/ring-lug@1 mates; neither block has
    an earth terminal, so no port has a third pole;
  - the roles are the ones the guides tie to the labels (+RTN and -48 V), no port states a voltage, the one wire size the
    guides give is stated, and the EX2200 states the one current its guide gives while the EX2300, whose documents
    disagree on it, states none;
  - the art each device drew in its place is gone from the DC rear view and the placed part stands where the art stood.

These run against the real library and a components index built by the indexer the build runs. They read no library/dist
and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"

# per device: the part, where it stands on the DC rear view, the art it replaced, the seats left to right, the ports
CASES = {
    "ex2200-24t": dict(
        part="juniper/ex2200-dc-terminal@1", size=[36.0, 18.4], at=[401.2, 11.9], dc_config="dc",
        art=["dc-terminal-strip", "dc-pole-1", "dc-pole-2", "dc-pole-3", "dc-pole-4",
             "dc-pole-1-screw", "dc-pole-2-screw", "dc-pole-3-screw", "dc-pole-4-screw"],
        seats=[("pole-b-neg", [4.3, 5.7]), ("pole-a-neg", [12.3, 5.7]), ("pole-b-pos", [20.3, 5.7]), ("pole-a-pos", [28.3, 5.7])],
        ports=[("input-a", "a", 3.5, [("rtn", "pole-a-pos"), ("batt", "pole-a-neg")]),
               ("input-b", "b", 3.5, [("rtn", "pole-b-pos"), ("batt", "pole-b-neg")])]),
    "ex2300-24t": dict(
        part="juniper/ex2300-dc-terminal@1", size=[52.6, 17.5], at=[377.3, 9.5], dc_config="dc",
        art=["dc-terminal-strip", "dc-mount-1", "dc-mount-1-head", "dc-mount-2", "dc-mount-2-head", "dc-pole-1", "dc-pole-2",
             "dc-pole-3", "dc-pole-4", "dc-pole-1-screw", "dc-pole-2-screw", "dc-pole-3-screw", "dc-pole-4-screw"],
        seats=[("pole-1-pos", [13.3, 7.05]), ("pole-1-neg", [21.6, 7.05]), ("pole-2-pos", [29.7, 7.05]), ("pole-2-neg", [37.9, 7.05])],
        ports=[("input-1", None, None, [("rtn", "pole-1-pos"), ("batt", "pole-1-neg")]),
               ("input-2", None, None, [("rtn", "pole-2-pos"), ("batt", "pole-2-neg")])]),
}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("name", CASES)
def test_the_part_composes_four_terminal_screws_at_the_centres_of_the_screws_its_skin_draws(name):
    case = CASES[name]
    d = contract(case["part"])
    assert d["parts"] == [dict(ref=SCREW, id=i, at=at) for i, at in case["seats"]]
    assert d["size"] == dict(w=case["size"][0], h=case["size"][1])
    skin = (LIB / "components" / case["part"].split("@")[0] / "v1/skins/default.svg").read_text()
    block = re.search(r'<g id="screws"[^>]*>(.*?)</g>', skin, re.S).group(1)
    centres = [[float(x), float(y)] for x, y in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="2\.2"/>', block)]
    assert len(centres) == 4
    for (ident, at), centre in zip(case["seats"], centres):
        assert [round(at[0] + 1.7, 2), round(at[1] + 1.7, 2)] == centre, ident


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


@pytest.mark.parametrize("name", CASES)
def test_each_block_states_two_input_ports_of_two_poles_and_no_earth_pole(name):
    case = CASES[name]
    ports = contract(case["part"])["dc"]["ports"]
    assert [p["id"] for p in ports] == [i for i, _, _, _ in case["ports"]]
    slots = []
    for port, (_, side, rating, poles) in zip(ports, case["ports"]):
        assert port["direction"] == "input"
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles
        assert port["awg"] == [14] and "voltage" not in port
        assert port.get("side") == side and port.get("rating-a") == rating
        slots += [q["slot"] for q in port["poles"]]
    assert sorted(slots) == sorted(i for i, _ in case["seats"])
    assert all(q["role"] in ("rtn", "batt") for p in ports for q in p["poles"])


@pytest.mark.parametrize("name", CASES)
def test_every_fact_a_port_states_names_a_provenance_entry_that_says_where_it_came_from(name):
    d = contract(CASES[name]["part"])
    for port in d["dc"]["ports"]:
        for fact, key in port["source"].items():
            assert fact in port or fact == "poles"
            assert len(words(d["provenance"][key])) >= 40, key
    for key in ("size", "poles", "pitch", "seats", "voltage", "rating", "awg"):
        assert len(words(d["provenance"][key])) >= 40, key
    for key in ("voltage",):
        assert words(d["provenance"][key]).startswith("NOT STATED")


def test_the_ex2200_block_says_its_size_and_pitch_are_estimated_with_no_scale():
    p = contract("juniper/ex2200-dc-terminal@1")["provenance"]
    assert words(p["size"]).startswith("ESTIMATED, NO SCALE") and words(p["pitch"]).startswith("ESTIMATED, NO SCALE")
    assert contract("juniper/ex2200-dc-terminal@1")["size-confidence"] == dict(w="estimated", h="estimated")


def test_the_ex2300_block_is_photo_measured_and_states_no_current_because_its_documents_disagree():
    d = contract("juniper/ex2300-dc-terminal@1")
    assert d["size-confidence"] == dict(w="photo-measured", h="photo-measured")
    assert words(d["provenance"]["rating"]).startswith("NOT STATED")
    assert all("rating-a" not in p and "side" not in p for p in d["dc"]["ports"])
    assert "3.7A" in words(d["provenance"]["rating"]) and "2.8" in words(d["provenance"]["rating"])


@pytest.mark.parametrize("name", CASES)
def test_the_dc_rear_view_places_the_part_where_the_art_stood_and_the_art_is_gone(name):
    case = CASES[name]
    d = device(name)
    view = d["views"]["rear-dc"]
    placed = [p for p in view["components"]["placements"] if p["ref"] == case["part"]]
    assert [(p["id"], p["at"]) for p in placed] == [("dc-terminal", case["at"])]
    ids = [x["id"] for x in view["panel"]["decor"]]
    assert "dc-terminal" not in ids
    for gone in case["art"]:
        assert gone not in ids, gone
    assert not [x for x in view["panel"]["decor"] if x.get("kind", "").startswith("dc-terminal")]


@pytest.mark.parametrize("name", CASES)
def test_the_ac_rear_is_unchanged_and_still_places_the_c14_inlet(name):
    d = device(name)
    assert [p["id"] for p in d["views"]["rear"]["components"]["placements"] if p["ref"] == "std/c14-inlet@1"] == ["ac-inlet"]
    assert not [p for p in d["views"]["rear"]["components"]["placements"] if "dc-terminal" in p["ref"]]


def test_the_ex2300_dc_configuration_states_the_power_it_runs_on_and_the_others_do_not():
    cfg = device("ex2300-24t")["configurations"]
    assert cfg["dc"]["power"] == "dc"
    for other in ("ac", "taa", "vc"):
        assert "power" not in cfg[other]
    assert device("ex2300-24t")["chassis"]["power"] == "ac"


def test_the_ex2200_dc_configuration_still_states_dc():
    assert device("ex2200-24t")["configurations"]["dc"]["power"] == "dc"


@pytest.mark.heavy
@pytest.mark.parametrize("name", CASES)
def test_the_build_publishes_four_seats_that_accept_the_ring_lug_and_two_dc_ports(name, index):
    case = CASES[name]
    entry = index[case["part"]]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _ in case["seats"]]
    assert [p["id"] for p in entry["dc-ports"]] == [i for i, _, _, _ in case["ports"]]
    for port, (_, _, _, poles) in zip(entry["dc-ports"], case["ports"]):
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles

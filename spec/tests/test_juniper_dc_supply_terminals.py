"""The terminals of three Juniper DC supplies are places a ring lug lands, and each supply states one DC input port.

The QFX5130 DC supplies (JPSU-1600W-1UDCAFI and -1UDCAFO, shared by the QFX5130-32CD, the QFX5130-48C and the QFX5220-32CD) and
the MX104 DC supply used to draw their two screw terminals as art, so they offered no place for a DC feed. Each now composes its
two terminal screws as parts, each a seat a ring lug lands on, and states one DC input port of two poles, the roles the vendor's
hardware guide gives them and no voltage:

  - juniper/qfx5130-jpsu-1600-dc-afi@1 and -afo@1 compose common/terminal-screw-34@1 as `pole-rtn` (the V+ "(return)" terminal at
    the left) and `pole-batt` (the V- "(input)" terminal beside it), at the centres of the two screws their skin draws; the port
    states the wire size the guide gives, 10 and 12 AWG, and no current (the chassis differ: 35 A and 40 A);
  - juniper/mx104-psu-dc@1 composes it as `pole-batt` (V-, the input terminal at the left) and `pole-rtn` (V+, the return terminal
    at the right), at the centres of the two studs its skin draws and lifted as those studs are; the port states no wire size (the
    guide gives a minimum, not a size) and no current (the guide gives three, one for each nominal voltage);
  - both screw parts present `terminal-stud`, and generic/ring-lug@1 mates it;
  - the supplies' elements, ids and descriptions are unchanged, and no skin is edited.

The other Juniper DC supplies are not part of this change: each keeps its contract and its record. These run against the real
library, a components index built by the indexer the build runs, and the records file. They read no library/dist and render nothing.
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
QFX = ["juniper/qfx5130-jpsu-1600-dc-afi@1", "juniper/qfx5130-jpsu-1600-dc-afo@1"]
MX = "juniper/mx104-psu-dc@1"
SUPPLIES = QFX + [MX]
# the seats as (id, at), left to right as the figures draw the block
QFX_SEATS = [("pole-rtn", [7.9, 24.3]), ("pole-batt", [22.4, 24.3])]
MX_SEATS = [("pole-batt", [18.3, 28.3]), ("pole-rtn", [36.3, 28.3])]
# the port's poles as (role, slot), in the order the figures print them from the left
QFX_POLES = [("rtn", "pole-rtn"), ("batt", "pole-batt")]
MX_POLES = [("batt", "pole-batt"), ("rtn", "pole-rtn")]
VERSIONS = {QFX[0]: "1.1.0", QFX[1]: "1.1.0", MX: "1.2.0"}
# the devices that seat them: slug -> (version on the change, the supplies it seats)
DEVICES = {"qfx5130-32cd": "0.2.0", "qfx5130-48c": "0.2.0", "qfx5220-32cd": "0.2.0", "mx104": "5.1.0"}
NOT_TAKEN = [
    "juniper/qfx5100-jpsu-650w-dc-afi@1", "juniper/qfx5100-jpsu-650w-dc-afo@1",
    "juniper/qfx5200-jpsu-850w-dc-afi@1", "juniper/qfx5200-jpsu-850w-dc-afo@1",
    "juniper/qfx5210-jpsu-1100w-dc-afi@1", "juniper/qfx5210-jpsu-1100w-dc-afo@1",
    "juniper/mx204-psu-dc@1", "juniper/mx304-psu-dc@1",
    "juniper/qfx10002-jpsu-1600w-dc-afo@1", "juniper/qfx10000-pwr-dc@1", "juniper/mx2000-psm-dc-v@1",
]


def folder(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((folder(ref) / "contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


def seats_of(ref):
    return QFX_SEATS if ref in QFX else MX_SEATS


def poles_of(ref):
    return QFX_POLES if ref in QFX else MX_POLES


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("ref", SUPPLIES)
def test_each_supply_composes_two_terminal_screws_and_nothing_else(ref):
    parts = contract(ref)["parts"]
    assert [(p["ref"], p["id"], p["at"]) for p in parts] == [(SCREW, i, at) for i, at in seats_of(ref)]


def test_the_screw_part_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


@pytest.mark.parametrize("ref", QFX)
def test_the_qfx5130_seats_stand_at_the_centres_of_the_two_screws_the_skin_draws(ref):
    skin = (folder(ref) / "skins/default.svg").read_text()
    centres = [[float(x), float(y)] for x, y in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="4\.4" fill="#9a9ea6"', skin)]
    assert len(centres) == 2
    half = contract(SCREW)["size"]["w"] / 2
    for (ident, at), centre in zip(QFX_SEATS, centres):
        assert [round(at[0] + half, 2), round(at[1] + half, 2)] == centre, ident
    assert all("lift" not in p for p in contract(ref)["parts"])


def test_the_mx104_seats_stand_at_the_centres_of_the_two_studs_and_are_lifted_as_the_studs_are():
    skin = (folder(MX) / "skins/default.svg").read_text()
    centres = [[float(x), float(y)] for x, y in re.findall(r'<g id="stud-\d"><circle cx="([\d.]+)" cy="([\d.]+)" r="4\.6"', skin)]
    assert len(centres) == 2
    half = contract(SCREW)["size"]["w"] / 2
    d = contract(MX)
    for (ident, at), centre in zip(MX_SEATS, centres):
        assert [round(at[0] + half, 2), round(at[1] + half, 2)] == centre, ident
    studs = [f["lift"] for f in d["relief"]["features"] if f["node"] in ("stud-0", "stud-1")]
    assert studs == [2.4, 2.4] and [p["lift"] for p in d["parts"]] == studs


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_elements_the_description_and_the_skin_stand_as_they_were(ref):
    d = contract(ref)
    assert d["version"] == VERSIONS[ref]
    assert d["attrs"]["inlet"] == "dc-terminal"
    assert d["description"].startswith("JPSU-1600W-1UDC" if ref in QFX else "Juniper MX104 DC power supply")
    elements = ["led-fault", "led-input", "led-output", "latch", "release-latch", "terminal-neg", "terminal-pos"] if ref in QFX else ["terminals"]
    assert sorted(d["elements"]) == sorted(elements)
    assert "skins" not in d


@pytest.mark.parametrize("ref", SUPPLIES)
def test_each_supply_gives_one_dc_input_port_of_two_poles_and_no_earth_pole(ref):
    ports = contract(ref)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    assert ports[0]["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in ports[0]["poles"]] == poles_of(ref)
    assert not [p for p in contract(ref)["parts"] if p["ref"] != SCREW]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_port_states_no_voltage_and_no_current(ref):
    port = contract(ref)["dc"]["ports"][0]
    assert "voltage" not in port and "rating-a" not in port and "side" not in port


@pytest.mark.parametrize("ref", QFX)
def test_the_qfx5130_port_states_the_wire_sizes_the_guide_gives(ref):
    assert contract(ref)["dc"]["ports"][0]["awg"] == [10, 12]


def test_the_mx104_port_states_no_wire_size_because_the_guide_gives_a_minimum():
    assert "awg" not in contract(MX)["dc"]["ports"][0]
    assert words(contract(MX)["provenance"]["awg"]).startswith("NOT STATED AS A SIZE")


@pytest.mark.parametrize("ref", SUPPLIES)
def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from(ref):
    d = contract(ref)
    source = d["dc"]["ports"][0]["source"]
    assert source == ({"poles": "poles", "awg": "awg"} if ref in QFX else {"poles": "poles"})
    for key in ("poles", "seats", "voltage", "rating", "awg"):
        assert len(words(d["provenance"][key])) >= 40, key
    poles = words(d["provenance"]["poles"])
    if ref in QFX:
        assert "Figure 105" in poles and "V+ (return)" in poles and "V- (input)" in poles and "PDF page" in poles
    else:
        assert "return (+)" in poles and "input (-)" in poles and "Figure 24" in poles and "V- above the left screw" in poles


@pytest.mark.parametrize("ref", SUPPLIES)
@pytest.mark.parametrize("key", ["voltage", "rating"])
def test_the_missing_voltage_and_current_are_said_not_left_out_silently(ref, key):
    text = words(contract(ref)["provenance"][key])
    assert text.startswith("NOT STATED") and "the port states none" in text.lower()


@pytest.mark.heavy
@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_build_publishes_two_seats_that_accept_the_ring_lug_and_one_dc_port(index, ref):
    entry = index[ref]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _ in seats_of(ref)]
    assert [(p["id"], p["direction"]) for p in entry["dc-ports"]] == [("input", "input")]
    assert [(q["role"], q["slot"]) for q in entry["dc-ports"][0]["poles"]] == poles_of(ref)


@pytest.mark.parametrize("slug", DEVICES)
def test_each_device_that_seats_a_supply_takes_one_minor(slug):
    folder_ = LIB / "devices/juniper" / slug
    lock = json.loads((folder_ / "device.lock.json").read_text())
    for fn in ("layout.yaml", "device.yaml"):
        if (folder_ / fn).exists():
            assert re.search(rf"^version: {re.escape(DEVICES[slug])}$", (folder_ / fn).read_text(), re.M), fn
    assert lock["version"] == DEVICES[slug]
    refs = lock["composed-refs"]
    assert refs[SCREW].startswith("1.0.1+")
    assert [r for r in refs if r in SUPPLIES] == [r for r in SUPPLIES if r in refs] and any(r in refs for r in SUPPLIES)


@pytest.mark.parametrize("slug", DEVICES)
def test_the_lock_holds_one_input_port_for_each_supply_bay_a_dc_configuration_seats(slug):
    lock = json.loads((LIB / "devices/juniper" / slug / "device.lock.json").read_text())
    ports = lock["dc-ports"]
    assert ports and all(path.endswith("/module/input") for path in ports)
    for path, refs in ports.items():
        for ref, fact in refs.items():
            assert ref in SUPPLIES and fact["voltage"] is None and fact["rating-a"] is None


@pytest.mark.parametrize("ref", NOT_TAKEN)
def test_the_supplies_this_change_leaves_for_later_keep_their_contract_and_their_record(ref):
    d = contract(ref)
    assert "dc" not in d and "parts" not in d
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert len([r for r in rows if r["part"] == ref and r["code"] == "C19"]) == 1


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_findings_this_change_closes_have_no_row_left(ref):
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == ref and r["code"] == "C19"] == []

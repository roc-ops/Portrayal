"""The Arista 7010TX-48-DC input is a place a cable lands: its terminal block states one DC input port.

The switch's DC rear places two `arista/7010tx-dc-terminal@1` blocks, one for each of its two internal power supplies, each
composing two terminal screws. The part stated no DC port, so the kit offered neither block as a power end and the conformance
scan reported the DC configurations as powered with no power end. The part now states one input port, `input`, on its two
screws, with the roles the vendor's quick start guide prints beside them: `batt` on the upper screw (printed -48V) and `rtn` on
the lower (printed RTN). The port states no voltage (the guide prints the range -40 to -72), no current (Table 3 does not say
whether 2.5 A is per switch or per supply), no wire size (Table 4 prints the range 14 to 18) and no side (no document says which
supply is feed A); each omission is said in the part's `provenance`. The switch that places it takes one minor, and the
conformance row that reported it is gone. These run against the real library, a components index built by the indexer the build
runs, and the records file. They read no library/dist and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

PART = "arista/7010tx-dc-terminal@1"
SCREW = "common/terminal-screw-34@1"
DEVICE = LIB / "devices/arista/7010tx-48"
LAYOUT_VERSION = "0.2.0"


def contract():
    return yaml.safe_load((LIB / "components/arista/7010tx-dc-terminal/v1/contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_part_is_one_minor_up_and_keeps_its_screws_elements_and_connection_point():
    d = contract()
    assert d["version"] == "1.1.0"
    assert d["parts"] == [dict(ref=SCREW, id="lug-1", at=[18.0, 6.6]), dict(ref=SCREW, id="lug-2", at=[18.0, 15.9])]
    assert sorted(d["elements"]) == ["pole-1", "pole-2"]
    assert d["connection-points"] == {"dc-in": {"at": [21.2, 13.7], "direction": "front"}}


def test_the_part_states_one_input_port_with_batt_on_the_upper_screw_and_rtn_on_the_lower():
    ports = contract()["dc"]["ports"]
    assert len(ports) == 1
    port = ports[0]
    assert (port["id"], port["direction"]) == ("input", "input")
    assert [(p["role"], p["slot"]) for p in port["poles"]] == [("batt", "lug-1"), ("rtn", "lug-2")]
    parts = {p["id"]: p for p in contract()["parts"]}
    assert parts["lug-1"]["at"][1] < parts["lug-2"]["at"][1]


def test_the_port_states_no_voltage_no_current_no_wire_size_and_no_side():
    port = contract()["dc"]["ports"][0]
    for key in ("voltage", "rating-a", "awg", "side"):
        assert key not in port, key
    assert port["source"] == {"poles": "poles"}


@pytest.mark.parametrize("key", ["voltage", "rating", "awg", "side"])
def test_each_omission_is_said_in_the_provenance_and_not_left_out_silently(key):
    text = words(contract()["provenance"][key])
    assert text.startswith("NOT STATED") and "the port states no" in text


def test_the_poles_provenance_names_the_guides_labels():
    text = words(contract()["provenance"]["poles"])
    assert "-48V (upper)" in text and "RTN (lower)" in text and "Figure D-4" in text


@pytest.mark.heavy
def test_the_build_publishes_one_input_port_of_two_poles(index):
    entry = index[PART]
    assert [(p["id"], p["direction"]) for p in entry["dc-ports"]] == [("input", "input")]
    assert [(q["role"], q["slot"]) for q in entry["dc-ports"][0]["poles"]] == [("batt", "lug-1"), ("rtn", "lug-2")]


def test_the_switch_takes_one_minor_and_its_lock_holds_one_port_for_each_supply_of_the_two_dc_configurations():
    for fn in ("layout.yaml", "device.yaml"):
        assert re.search(rf"^version: {re.escape(LAYOUT_VERSION)}$", (DEVICE / fn).read_text(), re.M), fn
    lock = json.loads((DEVICE / "device.lock.json").read_text())
    assert lock["version"] == LAYOUT_VERSION
    assert lock["composed-refs"][PART].startswith("1.1.0+")
    ports = {path: refs[PART] for path, refs in lock["dc-ports"].items()}
    assert sorted(ports) == ["dc-ps1/input", "dc-ps2/input"]
    for path, fact in ports.items():
        slot = path.split("/")[0]
        assert fact["configs"] == ["dc-f", "dc-r"]
        assert [(p["role"], p["slot"]) for p in fact["poles"]] == [("batt", f"{slot}/lug-1"), ("rtn", f"{slot}/lug-2")]
        assert fact["voltage"] is None and fact["rating-a"] is None and fact["awg"] is None and fact["side"] is None


def test_the_finding_this_change_closes_has_no_row_left_and_the_cap_is_the_row_count():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    assert [r for r in doc["rows"] if r["part"] == "7010tx-48" and r["code"] == "C19"] == []
    assert doc["cap"] == len(doc["rows"])

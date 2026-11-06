"""The valve of the liquid-cooling coupler is not a port, so the coolant valves of two switches are not reported as ports.

The valve of `common/liquid-qd-coupler@1` is the face of a quick-disconnect coupler that joins a tray's coolant loop to the
rack manifold. It carries liquid and takes no cable, cord, lug or plug. The port-usable check reads element class `port`
and cannot excuse an element of a placed part by that part's sentence, so the element is named for what it is as well
(spec/tools/dev/part_conformance.mjs).
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "library" / "components" / "common" / "liquid-qd-coupler" / "v1" / "contract.yaml"
RECORDS = ROOT / "library" / "conformance-exceptions.yaml"


def contract():
    return yaml.safe_load(CONTRACT.read_text())


def words(text):
    return " ".join(str(text).split())


def test_the_coupler_valve_is_not_a_port():
    assert contract()["elements"]["valve"]["class"] == "mechanical"


def test_the_coupler_says_why_nothing_plugs_into_it():
    sentence = words(contract()["unmated"])
    for phrase in ("coolant loop", "carries liquid", "no cable, cord or lug lands on it"):
        assert phrase in sentence, f"the sentence does not say {phrase!r}: {sentence}"


def test_the_coupler_says_why_the_valve_is_mechanical():
    note = words(contract()["provenance"]["valve-class"])
    for phrase in ("cold-plate loop", "takes no cable, cord, lug or plug", "class `mechanical` and not `port`"):
        assert phrase in note, f"the note does not say {phrase!r}: {note}"


def test_the_valve_keeps_its_place_size_and_relief():
    doc = contract()
    assert doc["elements"]["valve"]["at"] == [16.0, 16.0] and doc["elements"]["valve"]["size"] == [6.4, 6.4]
    assert [f for f in doc["relief"]["features"] if f.get("node") == "fitting" and f.get("out") == 8.0]


def test_the_records_file_holds_no_port_row_for_the_two_coolant_devices():
    rows = yaml.safe_load(RECORDS.read_text())["rows"]
    left = [r for r in rows if r["code"] == "C22" and r["part"] in ("ds6001", "qfx5250-64oe-l")]
    assert not left, "the coolant valves are no longer reported as ports"

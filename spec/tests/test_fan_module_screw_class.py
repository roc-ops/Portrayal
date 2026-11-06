"""The captive screw of the generic fan module is a latch, so the MX150's fixed fans offer no place for a lug.

The screw on the mounting tab of `common/fan-module@1` holds the module; it is not a place a cord or lug lands.
The port-usable check reads element classes `inlet`, `terminal`, `ground` and `screw` and cannot excuse an element
of a placed part by that part's sentence, so the element is named for what it is (spec/tools/dev/part_conformance.mjs).
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "library" / "components" / "common" / "fan-module" / "v1" / "contract.yaml"
RECORDS = ROOT / "library" / "conformance-exceptions.yaml"


def contract():
    return yaml.safe_load(CONTRACT.read_text())


def test_the_fan_module_screw_is_a_latch():
    assert contract()["elements"]["screw"]["class"] == "latch"


def test_the_fan_module_says_why_the_screw_is_a_latch():
    note = " ".join(str(contract()["provenance"]["screw-class"]).split())
    for words in ("mounting tab", "class `latch`", "maiaedge/pbc-2000-fan-plate@2", "not a place a cord or lug lands"):
        assert words in note, f"the note does not say {words!r}: {note}"


def test_the_screw_keeps_its_place_size_and_relief():
    doc = contract()
    assert doc["elements"]["screw"]["at"] == [0.3, 17.8] and doc["elements"]["screw"]["size"] == [3.4, 3.4]
    assert [f for f in doc["relief"]["features"] if f.get("node") == "screw" and f.get("cyl") == 5 and f.get("knurl")]


def test_the_records_file_holds_no_row_for_the_mx150():
    rows = yaml.safe_load(RECORDS.read_text())["rows"]
    assert not [r for r in rows if r["part"] == "mx150"], "the fan screws are no longer reported"

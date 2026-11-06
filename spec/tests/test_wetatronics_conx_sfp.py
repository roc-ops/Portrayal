"""Wetatronics ConX-SFP: a console server in an SFP housing, registered as a
maker's pluggable wrapped on generic/sfp-rj45, its jack stated as a console.

What is true of the library once it is there: the wrapper is a module of the
copper SFP's shape, every size is the generic's and says so, the console role
is stated where the kit reads it, no draw is invented, and every fact no
document holds is written down as not stated.
"""
import json
import pathlib

import jsonschema
import pytest
import yaml

from portrayal import dcim_export

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/wetatronics/conx-sfp/v1/contract.yaml"
G = LIB / "components/generic/sfp-rj45/v1/contract.yaml"


@pytest.fixture(scope="module")
def conx():
    assert P.is_file(), "wetatronics/conx-sfp has no contract"
    return yaml.safe_load(P.read_text())


@pytest.fixture(scope="module")
def generic():
    return yaml.safe_load(G.read_text())


def test_it_validates_as_a_module_of_the_copper_sfp_shape(conx, generic):
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    jsonschema.validate(conx, schema)
    assert conx["kind"] == "module" and conx["class"] == "transceiver"
    assert conx["mates"] == generic["mates"] == "sfp"
    assert [p["ref"] for p in conx["parts"]] == ["generic/sfp-rj45@1"]
    assert conx["connection-points"]["mate"] == generic["connection-points"]["mate"]


def test_every_size_is_the_generics_and_is_declared_borrowed(conx, generic):
    assert conx["size"] == generic["size"]
    assert set(conx["size-confidence"].values()) == {"borrowed"}
    for key in ("size", "head"):
        assert conx["provenance"][key].lstrip().startswith("borrowed"), key
    assert "head" not in conx, "the head outside the cage is the generic's, not restated"


def test_the_jack_is_a_serial_console_and_not_an_ethernet_port(conx):
    a = conx["attrs"]
    assert a["role"] == "console" and a["media"] == "rj45-serial"
    assert a["model"] == "ConX-SFP"
    assert "RS-232" in conx["description"] and "1000BASE-LX" in conx["description"]
    assert "face" not in a, "the face is the generic's, composed through parts"


def test_no_draw_is_invented_and_the_gaps_are_written_down(conx):
    a = conx["attrs"]
    assert not [k for k in a if k.startswith("power-draw")]
    assert a["power-absent"] == "not-published"
    for key in ("power", "latch", "leds", "model", "role", "media"):
        assert conx["provenance"][key].strip(), key
    for key in ("power", "latch", "leds"):
        text = conx["provenance"][key]
        assert "NOT STATED" in text.upper() or "not-published" in text, key


def test_the_maker_is_registered_and_the_module_type_is_exported_under_its_name(conx):
    vendors = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    assert vendors["wetatronics"]["display"] == "Wetatronics"
    doc = dcim_export.build_module(conx, vendors["wetatronics"]["display"])
    assert (doc["manufacturer"], doc["model"]) == ("Wetatronics", "ConX-SFP")
    assert doc["description"].startswith("Wetatronics ConX-SFP")

"""The QFX5210 DC supplies carry a three-position DC power header, and a cable plug seats in it.

The QFX5210 Switch Hardware Guide draws the supply's power connector in its flat faceplate figures (Figures 19 and 32) and calls
it the "Terminal block": a keyed shroud with three round cells in a column numbered 1, 2 and 3 from the top, and no pole printed
at any cell. It names no maker, series, pitch or dimension, and its text says in different places that the DC cables are
provided, that they are unlatched, and that a lug is attached to them. So:

  - the registry gains the interface `juniper-qfx5210-dc-header-3`, a vendor connector that claims no standard;
  - juniper/qfx5210-dc-header@1 presents it, drawn at the block the supplies' face already shows (its size is an estimate);
  - juniper/qfx5210-dc-plug@1, a stand-in for the cable connector no figure draws, mates it, its wires plain grey;
  - both supplies (airflow in and airflow out, one connector) compose the header, keep every other figure, and state no DC port
    (no cell has a printed role);
  - the device that seats them takes the patch the lock asks.

These run against the real library, a components index built by the indexer the build runs, the device locks and the records file.
They read no library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
KEY = "juniper-qfx5210-dc-header-3"
HEADER = "juniper/qfx5210-dc-header@1"
PLUG = "juniper/qfx5210-dc-plug@1"
SUPPLIES = ["juniper/qfx5210-jpsu-1100w-dc-afi@1", "juniper/qfx5210-jpsu-1100w-dc-afo@1"]
DEVICES = ["juniper/qfx5210-64c"]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def skin(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return ET.parse(LIB / "components" / ns / part / f"v{major}" / "skins" / "default.svg").getroot()


def ids(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_registry_names_the_connector_and_both_its_halves():
    entry = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"][KEY]
    assert "standard" not in entry and "unmated" not in entry
    for words in (HEADER, PLUG, "Figures 19 and 32", "no standard is held"):
        assert words in entry["note"], words


def test_the_header_presents_the_key_and_says_its_size_is_an_estimate():
    d = contract(HEADER)
    assert (d["kind"], d["class"], d["interface"], d["version"]) == ("component", "inlet", KEY, "1.0.0")
    assert d["size"] == {"w": 10.9, "h": 29.9} and d["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "model" not in d["attrs"] and "part-numbers" not in d
    assert d["attrs"]["positions"] == 3
    assert "NO MAKER" in d["provenance"]["part"]
    assert "NO POLE IS ASSIGNED" in d["provenance"]["marks"]
    assert d["connection-points"]["mate"]["direction"] == "front"
    assert {"body", "cell-1", "cell-2", "cell-3", "silkscreen"} <= set(ids(skin(HEADER)))
    assert [t.text for t in ids(skin(HEADER))["silkscreen"]] == ["1", "2", "3"]


def test_the_plug_is_a_declared_stand_in_and_mates_the_key():
    d = contract(PLUG)
    assert (d["class"], d["mates"], d["version"]) == ("port", KEY, "1.1.0")
    assert d["size"] == contract(HEADER)["size"]
    assert "STAND-IN" in d["provenance"]["model"]
    points = d["connection-points"]
    assert points["mate"]["at"] == contract(HEADER)["connection-points"]["mate"]["at"]
    assert sorted(k for k in points if k.startswith("wire-")) == ["wire-1", "wire-2", "wire-3"]
    assert "fields" not in d


@pytest.mark.parametrize("ref", SUPPLIES)
def test_each_supply_composes_the_header_and_keeps_its_figures(ref):
    d = contract(ref)
    assert d["version"] == "1.1.0"
    assert d["parts"] == [{"ref": HEADER, "id": "dc-header", "at": [6.8, 4.4]}]
    assert "dc" not in d
    assert d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["power-output-w"] == 1100
    assert d["elements"]["terminals"] == {"at": [6.8, 4.4], "size": [10.9, 29.9], "class": "terminal"}
    assert d["size"] == {"w": 52.0, "h": 41.8}
    for key in ("connector", "roles", "no-dc-port"):
        assert key in d["provenance"], key
    text = d["provenance"]["connector"] + d["provenance"]["roles"] + d["provenance"]["no-dc-port"]
    for word in ("Figure 19", "NO POLE IS PRINTED", "NOT STATED HERE, ON PURPOSE"):
        assert word in text, word


@pytest.mark.heavy
@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_index_publishes_the_header_as_a_slot_the_plug_seats_in(index, ref):
    cages = index[ref]["cages"]
    assert [(c["interface"], c["kind"], c["accepts"]) for c in cages] == [(KEY, "connector", [PLUG])]


@pytest.mark.parametrize("slug", DEVICES)
def test_each_device_records_the_new_part_in_its_lock(slug):
    lock = json.loads((LIB / "devices" / slug / "device.lock.json").read_text())
    assert HEADER in lock["composed-refs"]
    doc = yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())
    assert lock["version"] == doc["version"]


def test_the_two_supplies_records_go():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    assert doc["cap"] == len(doc["rows"])
    assert [r for r in doc["rows"] if r["part"] in set(SUPPLIES) | {HEADER, PLUG}] == []

"""The QFX5200-48Y DC supplies carry a three-position DC power header, and a cable plug seats in it.

The QFX5200 Hardware Guide draws the supply's power connector in its flat faceplate figure (Figure 42) and shows the cable's
connector going into it (Figure 85): three round cells in a column numbered 3, 2 and 1 from the top, and wires labelled
"Red: RTN", "Black: -36 -72V" and "Green: Grounding". It names no maker, series, pitch or dimension. So:

  - the registry gains the interface `juniper-dc-header-3`, a vendor connector that claims no standard;
  - juniper/qfx5200-48y-dc-header@1 presents it, drawn at the block the supplies' face already shows (its size is an estimate);
  - juniper/qfx5200-48y-dc-plug@1, the cable connector of Figure 85, mates it, wired top to bottom as the figure labels the wires;
  - both supplies (airflow in and airflow out, one connector) compose the header, keep every other figure, and state no DC port
    (a port on a composed connector cannot be published at the connector yet);
  - the two devices that seat them take the patch the lock asks.

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
KEY = "juniper-dc-header-3"
HEADER = "juniper/qfx5200-48y-dc-header@1"
PLUG = "juniper/qfx5200-48y-dc-plug@1"
SUPPLIES = ["juniper/qfx5200-48y-dpsu-ai@1", "juniper/qfx5200-48y-dpsu-ao@1"]
DEVICES = ["juniper/qfx5120-32c", "juniper/qfx5200-48y"]


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
    for words in (HEADER, PLUG, "Figure 42", "no standard is held"):
        assert words in entry["note"], words


def test_the_header_presents_the_key_and_says_its_size_is_an_estimate():
    d = contract(HEADER)
    assert (d["kind"], d["class"], d["interface"], d["version"]) == ("component", "inlet", KEY, "1.0.0")
    assert d["size"] == {"w": 10.9, "h": 28.4} and d["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "model" not in d["attrs"] and "part-numbers" not in d
    assert d["attrs"]["positions"] == 3
    assert "NO MAKER" in d["provenance"]["part"]
    assert d["connection-points"]["mate"]["direction"] == "front"
    assert {"body", "cell-3", "cell-2", "cell-1", "silkscreen"} <= set(ids(skin(HEADER)))
    assert [t.text for t in ids(skin(HEADER))["silkscreen"]] == ["3", "2", "1"]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_skin_no_longer_draws_what_the_part_draws(ref):
    nodes = ids(skin(ref))
    assert "silkscreen" not in nodes
    assert (nodes["connector"].get("fill"), len(list(nodes["connector"]))) == ("none", 0)


def test_the_plug_is_the_guides_cable_connector_and_mates_the_key():
    d = contract(PLUG)
    assert (d["class"], d["mates"], d["version"]) == ("port", KEY, "1.1.0")
    assert d["size"] == {"w": 10.9, "h": 28.4}
    points = d["connection-points"]
    assert points["mate"]["at"] == contract(HEADER)["connection-points"]["mate"]["at"]
    assert sorted(k for k in points if k.startswith("wire-")) == ["wire-1", "wire-2", "wire-3"]
    # top to bottom as the supply numbers the cells: pin 3 red (RTN), pin 2 black, pin 1 green (grounding)
    assert [d["fields"][f"wire-{n}-color"]["default"] for n in (1, 2, 3)] == ["#d32f2f", "#1c1c1c", "#5a9e3c"]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_each_supply_composes_the_header_and_keeps_its_figures(ref):
    d = contract(ref)
    assert d["version"] == "1.1.0"
    assert d["parts"] == [{"ref": HEADER, "id": "dc-header", "at": [37.6, 8.5]}]
    assert "dc" not in d
    assert d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["power-output-w"] == 650
    assert d["elements"]["connector"] == {"at": [37.6, 8.5], "size": [10.9, 28.4], "class": "terminal"}
    assert d["size"] == {"w": 54.4, "h": 39.7}
    for key in ("connector", "roles", "no-dc-port"):
        assert key in d["provenance"], key
    text = d["provenance"]["connector"] + d["provenance"]["roles"] + d["provenance"]["no-dc-port"]
    for word in ("Figure 42", "Red: RTN", "NOT STATED HERE, ON PURPOSE"):
        assert word in text, word


def test_the_two_supplies_differ_only_in_the_latch_colour():
    a, b = (ids(skin(r)) for r in SUPPLIES)
    assert set(a) == set(b)
    assert ET.tostring(a["connector"]) == ET.tostring(b["connector"])


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


def test_the_two_supplies_records_go_and_the_cap_follows():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = doc["rows"]
    assert doc["cap"] == len(rows)
    assert [r for r in rows if r["part"] in set(SUPPLIES) | {HEADER, PLUG}] == []

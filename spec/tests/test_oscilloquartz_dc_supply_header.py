"""The OSA 5420 and OSA 5421 -48 VDC supplies carry a three-position latching header, and a cable plug seats in it.

The Installation and Commissioning Manual (R9.5.1) draws the supply's power connector in Figures 13 and 15 and tabulates its pins
(Table 8): a keyed three-position header with a release tab above it, printed "- Gnd +", pin 3 the -48 VDC battery, pin 2 ground and pin 1
the return for the battery source, and a cable whose plug carries the release tab. It names no maker, series, pitch or dimension. So:

  - the registry gains the interface `latch-header-3`, a vendor connector that claims no standard;
  - oscilloquartz/osa542x-dc-header@1 presents it, drawn at the header the 40 W supply's face already shows (its size is an estimate);
  - oscilloquartz/osa542x-dc-plug@1, the cable connector of Figure 15, mates it, wired top to bottom as the figure wires it;
  - both supplies (40 W and 90 W, one face) compose the header, keep every other figure, and state no DC port (a port on a composed
    connector cannot be published at the connector yet);
  - the four devices that seat them take the patch the lock asks.

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
KEY = "latch-header-3"
HEADER = "oscilloquartz/osa542x-dc-header@1"
PLUG = "oscilloquartz/osa542x-dc-plug@1"
SUPPLIES = {"oscilloquartz/osa542x-psu-dc-40w@1": 40, "oscilloquartz/osa542x-psu-dc-90w@1": 90}
DEVICES = {
    "oscilloquartz/osa-5420-quartz": ("0.1.3", "0.1.5", "oscilloquartz/osa542x-psu-dc-40w@1"),
    "oscilloquartz/osa-5420-quartz-hq-plus": ("0.1.3", "0.1.5", "oscilloquartz/osa542x-psu-dc-40w@1"),
    "oscilloquartz/osa-5421-quartz-hq-plus-plus": ("0.1.3", "0.1.5", "oscilloquartz/osa542x-psu-dc-90w@1"),
    "oscilloquartz/osa-5421-rubidium": ("0.1.3", "0.1.5", "oscilloquartz/osa542x-psu-dc-90w@1"),
}


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


def device(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_registry_names_the_connector_and_both_its_halves():
    entry = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"][KEY]
    assert "standard" not in entry and "unmated" not in entry
    for words in (HEADER, PLUG, "Figures 13 and 15", "no standard is held"):
        assert words in entry["note"], words


def test_the_header_presents_the_key_and_says_its_size_is_an_estimate():
    d = contract(HEADER)
    assert (d["kind"], d["class"], d["interface"], d["version"]) == ("component", "inlet", KEY, "1.0.0")
    assert d["size"] == {"w": 13.7, "h": 10.3} and d["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "model" not in d["attrs"] and "part-numbers" not in d
    assert d["attrs"]["positions"] == 3
    assert "NO MAKER" in d["provenance"]["part"]
    assert d["connection-points"]["mate"]["direction"] == "front"
    nodes = ids(skin(HEADER))
    assert {"key", "body"} <= set(nodes)


def test_the_plug_is_the_manuals_cable_connector_and_mates_the_key():
    d = contract(PLUG)
    assert (d["class"], d["mates"], d["version"]) == ("port", KEY, "1.1.0")
    assert d["size"] == {"w": 13.7, "h": 10.3}
    points = d["connection-points"]
    assert points["mate"]["at"] == contract(HEADER)["connection-points"]["mate"]["at"]
    assert sorted(k for k in points if k.startswith("wire-")) == ["wire-1", "wire-2", "wire-3"]
    # left to right as the supply prints it: "-" (pin 3, the battery), Gnd (pin 2), "+" (pin 1, the return)
    assert [d["fields"][f"wire-{n}-color"]["default"] for n in (1, 2, 3)] == ["#c8262c", "#5a9e3c", "#1c1c1c"]


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_each_supply_composes_the_header_and_keeps_its_figures(ref):
    d = contract(ref)
    assert d["version"] == "1.1.0"
    assert d["parts"] == [{"ref": HEADER, "id": "dc-header", "at": [39.9, 17.75]}]
    assert "dc" not in d
    assert d["attrs"]["input"] == "dc" and d["attrs"]["inlet"] == "dc-terminal"
    assert d["attrs"]["power-output-w"] == SUPPLIES[ref]
    assert d["attrs"]["input-voltage"] == "-48 to -60 VDC (tolerates -36 to -72 VDC)"
    assert d["elements"]["inlet"] == {"at": [39.9, 17.75], "size": [13.7, 10.3], "class": "inlet"}
    assert d["connection-points"]["power"] == {"at": [46.75, 25.3], "direction": "rear"}
    assert d["size"] == {"w": 81.0, "h": 36.0}
    for key in ("connector", "roles", "no-dc-port"):
        assert key in d["provenance"], key
    for word in ("Table 8", "Figure 15", "NOT STATED HERE, ON PURPOSE"):
        assert word in d["provenance"]["connector"] + d["provenance"]["roles"] + d["provenance"]["no-dc-port"], word


def test_the_two_supplies_carry_one_face():
    a, b = (skin(r) for r in sorted(SUPPLIES))
    assert ET.tostring(a) == ET.tostring(b)


@pytest.mark.heavy
@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_the_index_publishes_the_header_as_a_slot_the_plug_seats_in(index, ref):
    cages = index[ref]["cages"]
    assert [(c["interface"], c["kind"], c["accepts"]) for c in cages] == [(KEY, "connector", [PLUG])]


@pytest.mark.parametrize("slug", sorted(DEVICES))
def test_each_device_takes_one_minor_and_its_lock_records_the_new_part(slug):
    before, after, supply = DEVICES[slug]
    doc = device(slug)
    assert doc["version"] == after
    lock = json.loads((LIB / "devices" / slug / "device.lock.json").read_text())
    assert lock["version"] == after
    assert HEADER in lock["composed-refs"] and supply in lock["composed-refs"]


def test_the_two_supplies_records_are_gone():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = doc["rows"]
    assert doc["cap"] == len(rows)
    assert [r for r in rows if r["part"] in set(SUPPLIES) | {HEADER, PLUG}] == []

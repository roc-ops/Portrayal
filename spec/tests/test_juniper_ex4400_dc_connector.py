"""The EX4400 front-to-back 550 W DC supply carries its power connector as a part, and the cable plug of the QFX10002 seats in it.

The EX4400 Switch Hardware Guide says its DC supplies "require a D-Sub 3W3-type connector" whose three pins carry the
-48 VDC input, the return and the ground, and supplies the cable CBL-JNP-PWR-DSUB, the cable the QFX10002 Switch Hardware
Guide names in the same words. Figure 10 draws the connector on the supply (a shell with three contacts, the middle one
larger, between two standoffs). The guide names no maker or part number for the connector and prints no mark beside a
contact. So:

  - the registered key `dc-connector-3w3` covers this connector too, and its note says so;
  - a header part presents it, drawn at the box the supply's face already showed (its size is an estimate);
  - the cable plug that already mates the key mates it, and no new plug is drawn;
  - the supply composes the header, keeps every other figure and states no DC port yet;
  - each device that seats the supply takes the minor the version check asks.

These run against the real library, a components index built by the indexer the build runs, the devices' recorded component
versions and the records file. They read no library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

KEY = "dc-connector-3w3"
HEADER = "juniper/ex4400-dc-header@1"
PLUG = "juniper/qfx10002-dc-plug@1"
SUPPLY = "juniper/jpsu-550-c-dc-afo@1"
DEVICES = ["juniper/ex4400-24t", "juniper/ex4400-24x", "juniper/ex4400-48f", "juniper/ex4400-48t"]


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


def test_the_registry_note_names_both_guides_and_both_headers_and_claims_no_standard():
    entry = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"][KEY]
    assert "standard" not in entry and "unmated" not in entry
    for words in ("QFX10002 Switch Hardware Guide", "EX4400 Switch Hardware Guide", "CBL-JNP-PWR-DSUB",
                  "juniper/qfx10002-dc-header@1", HEADER, PLUG, "no standard is held"):
        assert words in entry["note"], words


def test_the_header_presents_the_key_and_says_what_is_an_estimate():
    d = contract(HEADER)
    assert (d["kind"], d["class"], d["interface"], d["version"]) == ("component", "inlet", KEY, "1.0.0")
    assert "model" not in d["attrs"] and "part-numbers" not in d
    assert d["attrs"]["positions"] == 3
    assert "NO MAKER" in d["provenance"]["part"]
    assert set(d["size-confidence"].values()) == {"estimated"}
    for field in ("gender", "pins", "key", "mate", "colour", "relief", "marks"):
        assert field in d["provenance"], field
    assert "NOT STATED" in d["provenance"]["pins"]
    assert d["connection-points"]["mate"]["direction"] == "front"


def test_the_header_has_three_contacts_between_two_standoffs():
    nodes = ids(skin(HEADER))
    assert {"shell", "contact-top", "contact-middle", "contact-bottom", "standoff-top", "standoff-bottom"} <= set(nodes)


def test_the_supply_skin_and_contract_no_longer_draw_what_the_part_draws():
    assert "dc-input" not in ids(skin(SUPPLY))
    assert "dc-input" not in contract(SUPPLY)["elements"]


def test_the_supply_composes_the_header_and_states_no_dc_port():
    d = contract(SUPPLY)
    assert d["version"] == "1.1.0"
    assert d["parts"] == [{"ref": HEADER, "id": "dc-header", "at": [58.9, 2.2]}]
    assert "dc" not in d
    for key in ("connector", "roles", "no-dc-port"):
        assert key in d["provenance"], key
    assert "NOT STATED HERE, ON PURPOSE" in d["provenance"]["no-dc-port"]


def test_the_plug_that_mates_the_key_is_the_one_the_guides_cable_ends_in():
    d = contract(PLUG)
    assert (d["class"], d["mates"]) == ("port", KEY)


@pytest.mark.heavy
def test_the_index_publishes_the_header_as_a_slot_the_plug_seats_in(index):
    cages = index[SUPPLY]["cages"]
    assert [(c["interface"], c["kind"], c["accepts"]) for c in cages] == [(KEY, "connector", [PLUG])]


@pytest.mark.parametrize("slug", DEVICES)
def test_each_device_records_the_new_part_in_its_lock(slug):
    lock = json.loads((LIB / "devices" / slug / "device.lock.json").read_text())
    assert HEADER in lock["composed-refs"], slug
    layout = yaml.safe_load((LIB / "devices" / slug / "layout.yaml").read_text())
    assert lock["version"] == layout["version"], slug


def test_the_supplys_record_goes_and_the_cap_follows():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = doc["rows"]
    assert doc["cap"] == len(rows)
    assert [r for r in rows if r["part"] == SUPPLY] == []

"""The EX4400 back-to-front 550 W DC supply carries its power connector as a part, as the front-to-back supply does.

The EX4400 Switch Hardware Guide gives the two 550 W DC supplies one set of figures and says its DC supplies "require a
D-Sub 3W3-type connector". It draws only the front-to-back unit (Figure 84, and Figure 10 on the switch), so the
back-to-front unit's face is that unit's with another handle colour, and its connector is the same one. So:

  - the supply composes the header part that already presents the registered key `dc-connector-3w3`, at the place the
    supply's own art drew it, and the cable plug that mates the key mates it;
  - the connector is no longer drawn in the supply's own art, and the supply keeps every other figure;
  - the supply states no DC port, for the reason the front-to-back supply gives;
  - each device that seats the supply takes the version the check asks, and the supply's record of the conformance
    records goes with the cap.

These run against the real library, a components index built by the indexer the build runs, the devices' recorded
component versions and the records file. They read no library/dist and render nothing.
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
SUPPLY = "juniper/jpsu-550-c-dc-afi@1"
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


def test_the_supply_skin_and_contract_no_longer_draw_what_the_part_draws():
    assert "dc-input" not in ids(skin(SUPPLY))
    assert "dc-input" not in contract(SUPPLY)["elements"]


def test_the_supply_keeps_its_handle_lamp_and_lever():
    nodes = ids(skin(SUPPLY))
    assert {"face", "fan", "screws", "handle", "silkscreen", "led", "latch"} <= set(nodes)
    assert {"led", "handle", "latch"} <= set(contract(SUPPLY)["elements"])


def test_the_supply_composes_the_same_header_at_the_same_place_as_the_front_to_back_supply():
    d = contract(SUPPLY)
    assert d["parts"] == [{"ref": HEADER, "id": "dc-header", "at": [58.9, 2.2]}]
    assert d["parts"] == contract("juniper/jpsu-550-c-dc-afo@1")["parts"]
    assert d["connection-points"]["power"]["direction"] == "rear"


def test_the_supply_states_no_dc_port_and_says_why():
    d = contract(SUPPLY)
    assert "dc" not in d
    for key in ("connector", "roles", "no-dc-port"):
        assert key in d["provenance"], key
    assert "NOT STATED HERE, ON PURPOSE" in d["provenance"]["no-dc-port"]
    assert "library has no D-sub 3W3 power part" not in d["provenance"]["input"]


def test_the_supply_says_the_connector_is_borrowed_from_the_unit_the_guide_draws():
    d = contract(SUPPLY)
    assert "jpsu-550-c-dc-afo@1" in d["provenance"]["connector"]
    assert "No figure" in d["provenance"]["sources"]


def test_the_plug_that_mates_the_key_is_the_one_the_guides_cable_ends_in():
    d = contract(PLUG)
    assert (d["class"], d["mates"]) == ("port", KEY)


@pytest.mark.heavy
def test_the_index_publishes_the_header_as_a_slot_the_plug_seats_in(index):
    cages = index[SUPPLY]["cages"]
    assert [(c["interface"], c["kind"], c["accepts"]) for c in cages] == [(KEY, "connector", [PLUG])]


@pytest.mark.parametrize("slug", DEVICES)
def test_each_device_records_the_new_supply_version_in_its_lock(slug):
    lock = json.loads((LIB / "devices" / slug / "device.lock.json").read_text())
    assert HEADER in lock["composed-refs"], slug
    assert lock["composed-refs"][SUPPLY].startswith(contract(SUPPLY)["version"] + "+"), slug
    layout = yaml.safe_load((LIB / "devices" / slug / "layout.yaml").read_text())
    assert lock["version"] == layout["version"], slug


def test_the_supplys_record_goes_and_the_cap_follows():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = doc["rows"]
    assert doc["cap"] == len(rows)
    assert [r for r in rows if r["part"] == SUPPLY] == []

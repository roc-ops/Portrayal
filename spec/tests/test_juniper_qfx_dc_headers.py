"""The QFX5241 DC supply and the QFX10002 1600 W DC supply carry their power connector as a part, and a cable plug seats in it.

The QFX5241-64OD and QFX5241-64QD Hardware Guide draws the DC supply's power connector (Figure 22, Figure 25) and the cord
going into it (Figure 35): six round cells in two rows of three behind a keyed outline. The cord's connector is a "six-pin
female" 2x3 connector with pins P1, P2, S1, S2, P3 and P4. The QFX10002 Switch Hardware Guide draws the DC supply's connector
(Figure 31) as a vertical D-sub with three contacts between two standoffs and says the supplies "require a D-Sub 3W3-type
connector". Neither guide names a maker or a part number for the connector, and neither says which contact is which pin. So:

  - the registry gains `juniper-dc-header-6` and `dc-connector-3w3`, vendor connectors that claim no standard;
  - a header part presents each key, drawn at the box the supply's face already showed (sizes are estimates);
  - a plug part, the cord's connector, mates each key and draws no wire at a contact (no document places a wire);
  - each supply composes its header, keeps every other figure and states no DC port yet;
  - each device that seats one of them takes the patch or minor the version check asks.

These run against the real library, a components index built by the indexer the build runs, the devices' recorded component versions and the records
file. They read no library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# (registry key, header, plug, supply, supply skin box of the header, devices that seat the supply)
SIX = ("juniper-dc-header-6", "juniper/qfx524x-dc-header@1", "juniper/qfx524x-dc-plug@1",
       "juniper/qfx524x-2ru-pwr-do@1", [23.0, 5.6], ["juniper/qfx5241-64od", "juniper/qfx5241-64qd"])
D3W3 = ("dc-connector-3w3", "juniper/qfx10002-dc-header@1", "juniper/qfx10002-dc-plug@1",
        "juniper/qfx10002-jpsu-1600w-dc-afo@1", [48.5, 2.2],
        ["juniper/qfx10002-36q", "juniper/qfx10002-60c", "juniper/qfx10002-72q", "juniper/qfx5220-128c"])
FAMILIES = [SIX, D3W3]
IDS = ["six-pin", "d-sub-3w3"]


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


@pytest.mark.parametrize("fam", FAMILIES, ids=IDS)
def test_the_registry_names_the_connector_and_both_its_halves(fam):
    key, header, plug = fam[:3]
    entry = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"][key]
    assert "standard" not in entry and "unmated" not in entry
    for words in (header, plug, "no standard is held"):
        assert words in entry["note"], words


@pytest.mark.parametrize("fam", FAMILIES, ids=IDS)
def test_the_header_presents_the_key_and_says_what_is_an_estimate(fam):
    key, header = fam[:2]
    d = contract(header)
    assert (d["kind"], d["class"], d["interface"], d["version"]) == ("component", "inlet", key, "1.0.0")
    assert "model" not in d["attrs"] and "part-numbers" not in d
    assert "NO MAKER" in d["provenance"]["part"]
    assert set(d["size-confidence"].values()) == {"estimated"}
    for field in ("gender", "pins", "key", "mate", "colour", "relief"):
        assert field in d["provenance"], field
    assert d["connection-points"]["mate"]["direction"] == "front"


def test_the_six_pin_header_has_six_cells_in_two_rows_and_places_no_pin():
    d = contract(SIX[1])
    assert d["attrs"]["positions"] == 6
    nodes = ids(skin(SIX[1]))
    assert {"body", "cell-t1", "cell-t2", "cell-t3", "cell-b1", "cell-b2", "cell-b3"} <= set(nodes)
    # the guide gives pin names (Table 18) and no figure that puts a name at a cell
    assert "NOT STATED" in d["provenance"]["pins"]


def test_the_3w3_header_has_three_contacts_between_two_standoffs_and_places_no_pin():
    d = contract(D3W3[1])
    assert d["attrs"]["positions"] == 3
    nodes = ids(skin(D3W3[1]))
    assert {"shell", "contact-top", "contact-middle", "contact-bottom", "standoff-top", "standoff-bottom"} <= set(nodes)
    assert "NOT STATED" in d["provenance"]["pins"]


@pytest.mark.parametrize("fam", FAMILIES, ids=IDS)
def test_the_supply_skin_no_longer_draws_what_the_part_draws(fam):
    assert "connector" not in ids(skin(fam[3]))


@pytest.mark.parametrize("fam", FAMILIES, ids=IDS)
def test_the_plug_is_the_cords_connector_and_mates_the_key(fam):
    key, header, plug = fam[:3]
    d = contract(plug)
    assert (d["class"], d["mates"], d["version"]) == ("port", key, "1.0.0")
    assert d["size"] == contract(header)["size"]
    assert d["connection-points"]["mate"] == contract(header)["connection-points"]["mate"]
    assert "STAND-IN" in d["provenance"]["model"]
    assert "NOT STATED" in d["provenance"]["wiring"] or "NOT PLACED" in d["provenance"]["wiring"]


@pytest.mark.parametrize("fam", FAMILIES, ids=IDS)
def test_each_supply_composes_the_header_and_states_no_dc_port(fam):
    header, supply, at = fam[1], fam[3], fam[4]
    d = contract(supply)
    assert d["version"] == "1.1.0"
    assert d["parts"] == [{"ref": header, "id": "dc-header", "at": at}]
    assert "dc" not in d
    for key in ("connector", "roles", "no-dc-port"):
        assert key in d["provenance"], key
    assert "NOT STATED HERE, ON PURPOSE" in d["provenance"]["no-dc-port"]


@pytest.mark.heavy
@pytest.mark.parametrize("fam", FAMILIES, ids=IDS)
def test_the_index_publishes_the_header_as_a_slot_the_plug_seats_in(index, fam):
    key, _, plug, supply = fam[:4]
    cages = index[supply]["cages"]
    assert [(c["interface"], c["kind"], c["accepts"]) for c in cages] == [(key, "connector", [plug])]


@pytest.mark.parametrize("fam", FAMILIES, ids=IDS)
def test_each_device_records_the_new_part_in_its_lock(fam):
    header, devices = fam[1], fam[5]
    for slug in devices:
        lock = json.loads((LIB / "devices" / slug / "device.lock.json").read_text())
        assert header in lock["composed-refs"], slug
        doc = yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())
        assert lock["version"] == doc["version"], slug


def test_the_two_supplies_records_go_and_the_cap_follows():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = doc["rows"]
    assert doc["cap"] == len(rows)
    gone = {SIX[3], D3W3[3]} | {f[i] for f in FAMILIES for i in (1, 2)}
    assert [r for r in rows if r["part"] in gone] == []

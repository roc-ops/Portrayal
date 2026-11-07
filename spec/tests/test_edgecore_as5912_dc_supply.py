"""The 48 VDC supply of the Edgecore AS5912-54X (AGR100) is a part of its own, and its Positronic connector is a place a cable plugs in.

The switch's two DC builds seated common/psu-dc-650@2, a generic supply drawn with a terminal cover and two lugs. The AS5912-54X |
5916-54XM quick start guide shows instead a blue Positronic connector on the supply and names the plug on the cable PLA03F7000/AA. The
guide rates this chassis's supply "36-75 VDC, 12 A maximum", where the DCS204's supplies carry "-36 - -72 VDC (16A/650 W max.)" and a
maker part number, and no held document gives the AS5912-54X's supply a part number. So:

  - edgecore/as5912-54x-psu-dc@1 is a supply of its own, named for the chassis, with no model and no part number;
  - it composes common/pla03-receptacle@1 as `inlet`, so the cable's plug (generic/pla03-plug@1) has a place to seat, and it
    states no DC port (a port on a composed connector cannot be published at the connector yet);
  - the two DC builds seat it and the bays still accept the generic supply, because a bay that stops accepting a part is a major;
  - the AS7326-56X still seats the generic supply, so that part is not edited.

These run against the real library, a components index built by the indexer the build runs, the device lock and the exporter's own
functions. They read no library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild
from portrayal import dcim_export

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SUPPLY = "edgecore/as5912-54x-psu-dc@1"
RECEPTACLE = "common/pla03-receptacle@1"
GENERIC = "common/psu-dc-650@2"
DEVICE = "edgecore/as5912-54x"
OTHER_DEVICE = "edgecore/as7326-56x"
DCS204_SUPPLIES = ["edgecore/psu-48v-650-f@1", "edgecore/psu-48v-650-b@1"]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def skin(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return ET.parse(LIB / "components" / ns / part / f"v{major}" / "skins" / "default.svg").getroot()


def device(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_supply_states_no_part_number_and_no_input_range_the_guide_does_not_settle():
    d = contract(SUPPLY)
    assert (d["kind"], d["class"], d["version"]) == ("module", "psu", "1.0.0")
    assert "part-numbers" not in d and "model" not in d["attrs"]
    assert d["attrs"]["power-output-w"] == 650 and d["attrs"]["input"] == "dc"
    assert "input-note" not in d["attrs"] and "airflow" not in d["attrs"]
    assert "NO MAKER PART NUMBER IS HELD" in d["provenance"]["naming"]
    assert "THE GUIDE PRINTS TWO RANGES" in d["provenance"]["input"]


def test_the_device_seats_neither_of_the_dcs204_supplies():
    seated = {r for c in device(DEVICE)["configurations"].values() for r in (c.get("bays") or {}).values()}
    accepted = {r for b in device(DEVICE)["views"]["rear"]["components"]["bays"] for r in b.get("accepts", [])}
    assert not (seated | accepted) & set(DCS204_SUPPLIES)


def test_the_supply_composes_the_connector_and_says_why_it_states_no_dc_port():
    d = contract(SUPPLY)
    assert d["parts"] == [{"ref": RECEPTACLE, "id": "inlet", "at": [32.8, 10.3]}]
    assert d["elements"]["dc-inlet"] == {"at": [32.8, 10.3], "size": [10.36, 28.6], "class": "inlet"}
    assert "dc" not in d and "inlet" not in d["attrs"]
    assert "NOT STATED HERE, ON PURPOSE" in d["provenance"]["no-dc-port"]
    for words in ("RTN", "-36 - -72 VDC (black wire)", "DC Return (red wire)", "Ground (yellow-green wire)", "NOT SETTLED"):
        assert words in d["provenance"]["roles"]


def test_the_skin_draws_what_the_figure_prints_and_the_latch_is_a_field():
    root = skin(SUPPLY)
    by_id = {e.get("id"): e for e in root.iter() if e.get("id")}
    assert [t.text for t in root.iter("{http://www.w3.org/2000/svg}text")] == ["RTN"]
    assert {"legend-earth", "dc-inlet", "latch-body", "handle-bar"} <= set(by_id)
    latch = by_id["latch-body"]
    assert (latch.get("data-fill-from"), latch.get("data-stroke-from")) == ("latch-finish", "latch-edge")
    assert set(contract(SUPPLY)["fields"]) == {"latch-finish", "latch-edge"}


def test_the_index_publishes_the_connector_as_a_slot_the_plug_seats_in(index):
    cages = index[SUPPLY]["cages"]
    assert [(c["id"], c["interface"], c["kind"], c["accepts"]) for c in cages] == [
        ("inlet", "positronic-pla03", "connector", ["generic/pla03-plug@1"])]


def test_the_supply_exports_one_power_port_named_for_its_connector():
    load = lambda r: contract(r.split(":")[0]) if r else None  # noqa: E731
    out = dcim_export.build_module(contract(SUPPLY), "Edgecore", load_ref=load)
    assert out["power-ports"] == [{"name": "inlet", "type": "other", "label": "Positronic PCS PLA03 (3-position)"}]


def test_the_device_seats_the_supply_in_both_dc_builds_and_still_accepts_the_generic_one():
    doc = device(DEVICE)
    for name in ("dc-f2b", "dc-b2f"):
        assert doc["configurations"][name]["bays"] == {"psu-1": SUPPLY, "psu-2": SUPPLY}
    assert doc["configurations"]["dc-b2f"]["component-attrs"]["as5912-54x-psu-dc"] == {
        "latch-finish": "#3d7bd6", "latch-edge": "#234b8c", "airflow": "back-to-front"}
    assert "psu-dc-650" not in (doc["configurations"]["dc-b2f"].get("component-attrs") or {})
    assert doc["configurations"]["ac-f2b"]["bays"] == {"psu-1": "common/psu-ac-650@3", "psu-2": "common/psu-ac-650@3"}
    for b in (b for b in doc["views"]["rear"]["components"]["bays"] if b["id"].startswith("psu-")):
        assert b["accepts"] == ["common/psu-ac-650@3", GENERIC, SUPPLY]


def test_the_lock_records_the_bays_and_the_composed_parts():
    lock = json.loads((LIB / "devices" / DEVICE / "device.lock.json").read_text())
    for bay in ("rear/bays/psu-1", "rear/bays/psu-2"):
        assert set(lock["bay-accepts"][bay]) == {"common/psu-ac-650@3", GENERIC, SUPPLY}
    assert {RECEPTACLE, SUPPLY} <= set(lock["composed-refs"])


def test_the_other_device_that_seats_the_generic_supply_still_does():
    seated = {ref for c in device(OTHER_DEVICE)["configurations"].values() for ref in (c.get("bays") or {}).values()}
    assert GENERIC in seated and SUPPLY not in seated


def test_the_new_supply_needs_no_record():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY] == []

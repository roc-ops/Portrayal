"""The DC supplies of the Edgecore DCS204 (AS7726-32X) are parts of their own, and their Positronic connector is a place a cable plugs in.

The switch's two DC builds seated common/psu-dc-650@2, a generic supply drawn with a terminal cover and two lugs marked "-" and "+". The
DCS204 quick start guide shows instead a blue Positronic connector on the supply and names the plug on the cable PLA03F7000/AA, which
Positronic's catalog reads as a one-row, three-position, female cable connector. The data sheet lists the two supplies as FRUs. So:

  - the registry gains the interface `positronic-pla03`, the male PLA03 on the panel;
  - common/pla03-receptacle@1 presents it, drawn to the catalog's face (its own part number is not known and is not stated);
  - generic/pla03-plug@1, the female cable connector PLA03F7000/AA, mates it, wired DC return, the feed and ground, top to bottom;
  - edgecore/psu-48v-650-f@1 and edgecore/psu-48v-650-b@1 are the two FRUs, one maker part number each; each composes the connector,
    states no DC port (a port on a composed connector cannot be published at the connector yet) and exports a power port typed `other`;
  - the AS7726-32X seats the F supply in `dc-f2b` and the B supply in `dc-b2f`; its bays still accept common/psu-dc-650@2;
  - the AS7326-56X and the AS5912-54X are not touched (no held document gives their DC supply's part number), so the generic supply
    keeps its record.

These run against the real library, a components index built by the indexer the build runs, the device lock, the records file and the
exporter's own functions. They read no library/dist and render nothing.
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
KEY = "positronic-pla03"
RECEPTACLE = "common/pla03-receptacle@1"
PLUG = "generic/pla03-plug@1"
GENERIC = "common/psu-dc-650@2"
SUPPLIES = {
    "edgecore/psu-48v-650-f@1": ("PSU-48V-650-F", "F0TZZ7632004A", "front-to-back", "#c22f2f"),
    "edgecore/psu-48v-650-b@1": ("PSU-48V-650-B", "F0TZZ7632003A", "back-to-front", "#3d7bd6"),
}
DEVICE = "edgecore/as7726-32x"
SEATS = {"dc-f2b": "edgecore/psu-48v-650-f@1", "dc-b2f": "edgecore/psu-48v-650-b@1"}
CONTROLS = ["edgecore/as5912-54x", "edgecore/as7326-56x"]


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
    for words in ("MALE on the panel", "PLA03F7000/AA", "common/pla03-receptacle@1", "generic/pla03-plug@1", "5.00 mm"):
        assert words in entry["note"], words


def test_the_receptacle_presents_the_key_at_the_catalogs_face_and_states_no_part_number():
    d = contract(RECEPTACLE)
    assert (d["kind"], d["class"], d["interface"]) == ("component", "inlet", KEY)
    assert d["size"] == {"w": 10.36, "h": 28.60} and d["size-confidence"] == {"w": "drawing", "h": "drawing"}
    assert d["connection-points"]["mate"] == {"at": [5.18, 14.30], "direction": "front"}
    assert "model" not in d["attrs"] and "part-numbers" not in d
    assert "DECLARED STAND-IN" in d["provenance"]["part"]
    pins = [ids(skin(RECEPTACLE))[f"pin-{n}"] for n in (1, 2, 3)]
    assert [float(p.get("cy")) for p in pins] == [9.30, 14.30, 19.30] and {p.get("cx") for p in pins} == {"5.18"}


def test_the_plug_is_the_guides_cable_connector_and_mates_the_key():
    d = contract(PLUG)
    assert (d["class"], d["mates"]) == ("port", KEY)
    assert d["attrs"]["connector"] == "PLA03F7000/AA"
    assert d["size"] == {"w": 10.36, "h": 22.25}
    points = d["connection-points"]
    assert points["mate"]["at"] == [5.18, 11.125]
    assert [points[f"wire-{n}"]["at"][1] for n in (1, 2, 3)] == [6.125, 11.125, 16.125]
    assert [d["fields"][f"wire-{n}-color"]["default"] for n in (1, 2, 3)] == ["#af3728", "#1c1c1c", "#5a9e3c"]


@pytest.mark.heavy
@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_each_supply_carries_its_one_part_number_and_no_other_part_carries_it(ref):
    model, part, airflow, latch = SUPPLIES[ref]
    d = contract(ref)
    assert d["part-numbers"] == {model: {"part": part}}
    assert d["attrs"]["airflow"] == airflow and d["attrs"]["power-output-w"] == 650
    assert d["fields"]["latch-finish"]["default"] == latch
    holders = []
    for p in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        other = yaml.safe_load(p.read_text()) or {}
        pns = other.get("part-numbers") or {}
        if model in pns or part in {str((v or {}).get("part")) for v in pns.values()} or (other.get("attrs") or {}).get("model") == model:
            holders.append(p.parent.parent.name)
    assert holders == [ref.split("/")[1].split("@")[0]]


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_each_supply_composes_the_connector_and_says_why_it_states_no_dc_port(ref):
    d = contract(ref)
    assert d["parts"] == [{"ref": RECEPTACLE, "id": "inlet", "at": [32.8, 10.3]}]
    assert "dc" not in d and "inlet" not in d["attrs"]
    assert "NOT STATED HERE, ON PURPOSE" in d["provenance"]["no-dc-port"]
    for role in ("RTN", "-36~-72V", "earth symbol"):
        assert role in d["provenance"]["roles"]
    texts = [t.text for t in skin(ref).iter("{http://www.w3.org/2000/svg}text")]
    assert texts == ["RTN", "-36~-72V"]
    latch = ids(skin(ref))["latch-body"]
    assert (latch.get("data-fill-from"), latch.get("data-stroke-from")) == ("latch-finish", "latch-edge")


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_the_index_publishes_the_connector_as_a_slot_the_plug_seats_in(index, ref):
    cages = index[ref]["cages"]
    assert [(c["id"], c["interface"], c["kind"], c["accepts"]) for c in cages] == [("inlet", KEY, "connector", [PLUG])]


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_each_supply_exports_one_power_port_named_for_its_connector(ref):
    load = lambda r: contract(r.split(":")[0]) if r else None  # noqa: E731
    model = SUPPLIES[ref][0]
    out = dcim_export.build_module(contract(ref), "Edgecore", load_ref=load, model=model)
    assert out["part_number"] == SUPPLIES[ref][1]
    assert out["power-ports"] == [{"name": "inlet", "type": "other", "label": "Positronic PCS PLA03 (3-position)"}]


def test_the_device_seats_one_supply_per_airflow_and_still_accepts_the_generic_one():
    doc = device(DEVICE)
    assert doc["version"] == "3.0.0"
    for name, ref in SEATS.items():
        cfg = doc["configurations"][name]
        assert cfg["bays"] == {"psu-1": ref, "psu-2": ref}
        assert "psu-dc-650" not in (cfg.get("component-attrs") or {})
    bays = {b["id"]: b for b in doc["views"]["rear"]["components"]["bays"] if b["id"].startswith("psu-")}
    for b in bays.values():
        assert b["accepts"] == ["common/psu-ac-650@3", GENERIC, *sorted(SUPPLIES, reverse=True)]


def test_the_lock_records_the_bays_and_the_composed_parts():
    lock = json.loads((LIB / "devices" / DEVICE / "device.lock.json").read_text())
    assert lock["version"] == "3.0.0"
    for bay in ("rear/bays/psu-1", "rear/bays/psu-2"):
        assert set(lock["bay-accepts"][bay]) == {"common/psu-ac-650@3", GENERIC, *SUPPLIES}
    assert {RECEPTACLE, *SUPPLIES} <= set(lock["composed-refs"])


@pytest.mark.parametrize("slug", CONTROLS)
def test_the_other_devices_that_seat_the_generic_supply_still_do(slug):
    seated = {ref for c in device(slug)["configurations"].values() for ref in (c.get("bays") or {}).values()}
    assert GENERIC in seated and not seated & set(SUPPLIES)


def test_the_new_parts_and_supplies_need_no_record():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] in {RECEPTACLE, PLUG, *SUPPLIES}] == []

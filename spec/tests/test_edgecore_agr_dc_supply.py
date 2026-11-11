"""The DC supply of the Edgecore AGR110 and AGR130 is a part of its own, and its terminal block is a place a cable lands, earth terminal included.

Both switches seated common/psu-dc-650@2 in their DC configuration, a generic supply drawn with two terminals marked "-" and "+" that the
Edgecore quick start guides for these switches do not show. Their figure is a barrier block of three screws one above the other, DC return
on the top one, the -36 to -72 VDC feed on the middle one and an earth symbol printed beside the bottom one. So:

  - edgecore/agr110-psu-dc@1 is that supply. No maker part number is held for it, so it is named for the two chassis and states no model;
  - it composes common/terminal-screw-34@1 three times, as `pole-rtn`, `pole-batt` and `pole-gnd`, each a seat a ring lug lands on, and its
    `dc` block has one input port whose three poles are those seats, the earth screw the third (`gnd`), the wire size the guides give, no
    voltage and no current;
  - the AGR110 and the AGR130 seat it in the `dc` configuration. Their rear bays still accept common/psu-dc-650@2 beside it, because a bay
    that stops accepting a part is a major bump for the device;
  - common/psu-dc-650@2 is not edited; the AS7726-32X, the AS5912-54X and the AS7326-56X each seat a supply of their own now.

These run against the real library, a components index built by the indexer the build runs, the device locks and the records file. They read
no library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "edgecore/agr110-psu-dc@1"
GENERIC = "common/psu-dc-650@2"
AC = "common/psu-ac-650@3"
SCREW = "common/terminal-screw-34@1"
LUG = "generic/ring-lug@1"
SCREWS = [("pole-rtn", [32.6, 8.7], "rtn"), ("pole-batt", [32.6, 18.0], "batt"), ("pole-gnd", [32.6, 27.0], "gnd")]
DEVICES = {"edgecore/agr110": "8.3.0", "edgecore/agr130": "0.2.0"}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(slug, source="device.yaml"):
    return yaml.safe_load((LIB / "devices" / slug / source).read_text())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_supply_is_named_for_its_chassis_and_states_no_maker_part_number_and_no_power_it_does_not_have():
    d = contract(SUPPLY)
    assert d["name"] == "agr110-psu-dc" and d["version"] == "1.0.0" and d["class"] == "psu"
    assert "model" not in d["attrs"] and "part-numbers" not in d
    assert "power-output-w" not in d["attrs"] and "voltage" not in d["attrs"]
    assert d["attrs"]["power-absent"] == "not-published"
    assert d["attrs"]["inlet"] == "dc-terminal" and d["attrs"]["input"] == "dc"
    assert " ".join(d["provenance"]["naming"].split()).startswith("NO MAKER PART NUMBER IS HELD")
    assert " ".join(d["provenance"]["power"].split()).startswith("NOT PUBLISHED")


def test_the_supply_composes_three_terminal_screws_one_for_each_pole_and_nothing_else():
    parts = contract(SUPPLY)["parts"]
    assert [(q["ref"], q["id"], q["at"]) for q in parts] == [(SCREW, i, at) for i, at, _ in SCREWS]
    assert all("lift" not in q for q in parts)


def test_the_screw_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


def test_the_block_keeps_the_element_and_the_connection_point_the_generic_supply_states():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ["dc-inlet", "handle", "latch"]
    assert d["elements"]["dc-inlet"]["class"] == "inlet"
    assert d["connection-points"] == {"power": {"at": [34.5, 20.0], "direction": "rear"}}
    old = contract(GENERIC)
    assert sorted(old["elements"]) == ["dc-inlet", "handle", "latch"] and sorted(old["connection-points"]) == ["power"]


def test_the_skin_draws_three_poles_and_an_earth_symbol_and_wires_the_latch_colour_to_its_fields():
    ns = "{http://www.w3.org/2000/svg}"
    root = ET.parse(LIB / "components/edgecore/agr110-psu-dc/v1/skins/default.svg").getroot()
    top = {e.get("id"): e for e in root if e.tag == f"{ns}g"}
    assert {"latch", "handle", "dc-inlet", "earth-symbol"} <= set(top)
    assert [e.get("id") for e in top["dc-inlet"] if e.tag == f"{ns}g"] == ["pole-1", "pole-2", "pole-3"]
    wired = {e.get("data-fill-from") for e in root.iter() if e.get("data-fill-from")} | {
        e.get("data-stroke-from") for e in root.iter() if e.get("data-stroke-from")}
    assert wired == set(contract(SUPPLY)["fields"]) == {"latch-finish", "latch-edge"}


def test_the_dc_port_is_one_input_with_return_feed_and_earth_in_the_order_of_the_figure():
    ports = contract(SUPPLY)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [(role, i) for i, _, role in SCREWS]
    assert port["awg"] == [10]
    assert "voltage" not in port and "rating-a" not in port


def test_every_fact_the_port_states_names_a_provenance_entry_and_the_missing_current_is_said():
    d = contract(SUPPLY)
    source = d["dc"]["ports"][0]["source"]
    assert set(source) == {"poles", "awg"}
    for key in source.values():
        assert key in d["provenance"] and len(d["provenance"][key]) >= 40
    poles = " ".join(d["provenance"]["poles"].split())
    assert "Connect Power" in poles and "earth" in poles and "third pole" in poles
    assert " ".join(d["provenance"]["rating"].split()).startswith("NOT STATED")
    assert "AWG #14" in " ".join(d["provenance"]["awg"].split())


@pytest.mark.parametrize("slug", DEVICES)
def test_the_device_seats_the_supply_in_its_dc_configuration_and_still_accepts_the_generic_one(slug):
    for source in ("device.yaml", "layout.yaml"):
        doc = device(slug, source)
        assert str(doc["version"]) == DEVICES[slug]
        bays = {b["id"]: b for b in doc["views"]["rear"]["components"]["bays"] if b["id"].startswith("psu-")}
        assert sorted(bays) == ["psu-0", "psu-1"]
        for b in bays.values():
            assert b["accepts"] == [AC, GENERIC, SUPPLY] and b["default"] == AC
        assert doc["configurations"]["dc"]["bays"] == {"psu-0": SUPPLY, "psu-1": SUPPLY}
        assert doc["configurations"]["ac"]["bays"] == {"psu-0": AC, "psu-1": AC}


@pytest.mark.parametrize("slug", DEVICES)
def test_the_lock_records_the_port_of_each_supply_bay_with_its_three_poles(slug):
    lock = json.loads((LIB / "devices" / slug / "device.lock.json").read_text())
    assert lock["version"] == DEVICES[slug]
    assert sorted(lock["dc-ports"]) == ["psu-0/module/input", "psu-1/module/input"]
    for path, by_part in lock["dc-ports"].items():
        bay = path.split("/")[0]
        assert list(by_part) == [SUPPLY]
        port = by_part[SUPPLY]
        assert [(p["role"], p["slot"]) for p in port["poles"]] == [(role, f"{bay}/module/{i}") for i, _, role in SCREWS]
        assert (port["awg"], port["rating-a"], port["voltage"], port["configs"]) == ([10], None, None, ["dc"])
    assert SUPPLY in lock["bay-accepts"]["rear/bays/psu-0"] and GENERIC in lock["bay-accepts"]["rear/bays/psu-0"]


def test_the_new_supply_needs_no_record():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY] == []


def test_the_build_publishes_three_seats_that_accept_the_ring_lug_and_one_dc_port(index):
    entry = index[SUPPLY]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _, _ in SCREWS]
    assert len(entry["dc-ports"]) == 1
    port = entry["dc-ports"][0]
    assert (port["id"], port["direction"], port["awg"]) == ("input", "input", [10])
    assert [(q["role"], q["slot"]) for q in port["poles"]] == [(role, i) for i, _, role in SCREWS]
    assert "dc-ports" not in index[GENERIC]

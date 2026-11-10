"""The MX240 normal-capacity AC supply draws the C20 inlet its guide names, so a cord has a place to land.

juniper/mx240-psu-ac@1 drew a handle, an input switch and a vent field, and no inlet, so it offered no cable end. The guide
says each supply has "a single AC appliance inlet" of type C20 (right angle), which a C19 cord end mates. The current major,
@2, composes std/c20-inlet@1 as `inlet`, as the MX304 supply does:

  - the supply composes the registered C20 inlet under the id `inlet`, and the library holds the mate (a C19 plug);
  - the inlet stands clear of every drawn box and lamp, declared an estimate (where the face puts it is test_juniper_mx240_psu_ac_face);
  - the exported module type gains one power port, `{module}/inlet`, and no exported port name changes;
  - the supply says where its face and its colours come from, and that no photograph of the AC variant is held.

These run against the real library, the registry, a components index built by the indexer the build runs and the exports
that are committed. They render nothing and read no library/dist.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec" / "schemas"

PSU = "juniper/mx240-psu-ac@2"
INLET = "std/c20-inlet@1"
PLUG = "generic/c19-plug@1"
MODULE_TYPE = "MX240 AC PSU (normal capacity).yaml"


def folder(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((folder(ref) / "contract.yaml").read_text())


def boxes(doc):
    return {k: (*v["at"], *v["size"]) for k, v in doc["elements"].items()}


def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_interface_is_registered_and_the_library_mates_it():
    registry = yaml.safe_load((SCHEMAS / "connectors.yaml").read_text())["interfaces"]
    assert "iec-c20" in registry
    assert contract(INLET)["interface"] == "iec-c20"
    assert contract(PLUG)["mates"] == "iec-c20"


def test_the_supply_composes_the_registered_c20_inlet_as_inlet_and_is_the_second_major():
    d = contract(PSU)
    assert [(q["ref"], q["id"]) for q in d["parts"]] == [(INLET, "inlet")]
    assert d["version"] == "2.0.0"


def test_the_inlet_stands_clear_of_every_drawn_box_and_the_lamps_on_the_face():
    d = contract(PSU)
    inlet = contract(INLET)["size"]
    x, y = d["parts"][0]["at"]
    box = (x, y, inlet["w"], inlet["h"])
    assert 0 <= x and x + inlet["w"] <= d["size"]["w"] and 0 <= y and y + inlet["h"] <= d["size"]["h"]
    for name, other in boxes(d).items():
        assert not overlap(box, other), name
    svg = (folder(PSU) / "skins" / "default.svg").read_text()
    lamps = [(float(a), float(b), float(r)) for a, b, r in
             re.findall(r'<circle id="led-[a-z-]+" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"', svg)]
    assert len(lamps) == 3
    for cx, cy, r in lamps:
        assert not overlap(box, (cx - r, cy - r, 2 * r, 2 * r)), (cx, cy)


def test_the_bay_size_does_not_change():
    assert contract(PSU)["size"] == {"w": 101.5, "h": 79.7}


def test_the_face_and_the_colours_are_declared_estimates_and_no_photograph_of_the_ac_variant_is_held():
    text = contract(PSU)["provenance"]
    entry = text["inlet"]
    assert "Figure 14" in entry and "ESTIMATE" in entry and len(entry) >= 80
    assert text["colours"].startswith("ESTIMATED") and "No photograph of the AC variant is held" in text["colours"]


def test_the_module_type_gains_the_one_power_port_in_both_dcim_formats():
    for fmt in ("netbox", "nautobot"):
        path = LIB / "exports" / fmt / "module-types" / "Juniper" / MODULE_TYPE
        doc = yaml.safe_load(path.read_text())
        assert doc["power-ports"] == [{"name": "{module}/inlet", "type": "iec-60320-c20"}], fmt


@pytest.mark.heavy
def test_the_build_publishes_the_inlet_as_a_seat_a_c19_cord_end_lands_on(index):
    cages = {c["id"]: c for c in index[PSU]["cages"]}
    assert "inlet" in cages
    assert cages["inlet"]["interface"] == "iec-c20"
    assert PLUG in cages["inlet"]["accepts"]


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert (PSU, "C19") not in {(r["part"], r["code"]) for r in rows}

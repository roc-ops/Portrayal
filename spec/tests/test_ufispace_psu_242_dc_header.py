"""The DC input connector of the UfiSpace PSU-242-DEERN supply is a place a cable lands.

The supply drew its input as a block in its skin, so it offered no cable end. It now composes a connector part, the
six-position DC input connector of the UfiSpace S9311-64D hardware installation guide (two rows of three cells, printed
"V+" over "V-"), standing over the block its skin already draws. The figure prints "INPUT CONNECTOR PN:3072980925" and no
document joins that number to a maker's part, so the key `ufispace-dc-block-6` claims no maker, standard or pitch, the header
and the cable connector that mates it are declared stand-ins, and the size is an estimate; each contract says so.

  - the supply states the roles of the two rows in its provenance (`pos` over `neg`) and states no DC port, because a port
    whose poles are the contacts of one pluggable connector is offered only where that part is itself the connector;
  - no skin is edited, the supply's description is unchanged, and the header draws what the skin draws, shape for shape;
  - the exported power port of the supply's module type is named for the header, not `Inlet`;
  - the record for the supply is gone.

These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild
from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SUPPLY = "ufispace/psu-242-dc@1"
HEADER, PLUG = "ufispace/psu-242-dc-header@1", "ufispace/psu-242-dc-plug@1"
KEY = "ufispace-dc-block-6"
RECT = re.compile(r'<rect\b[^>]*?\bx="([\d.]+)"[^>]*?\by="([\d.]+)"[^>]*?\bwidth="([\d.]+)"[^>]*?\bheight="([\d.]+)"')


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def rects(svg):
    return [tuple(round(float(v), 3) for v in m.groups()) for m in RECT.finditer(svg)]


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_key_is_registered_and_claims_no_maker():
    reg = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]
    note = reg[KEY]["note"]
    assert "standard" not in reg[KEY], "no document names a standard"
    assert "claims none" in note and "PSU-242-DEERN" in note and PLUG in note and HEADER in note
    assert "3072980925" in note and "joins the printed number" in note


def test_the_header_is_an_inlet_and_the_plug_mates_it_at_the_same_point():
    header, plug = contract(HEADER), contract(PLUG)
    assert (header["class"], header["interface"]) == ("inlet", KEY)
    assert (plug["class"], plug["mates"]) == ("port", KEY)
    assert header["connection-points"]["mate"]["at"] == plug["connection-points"]["mate"]["at"]
    assert header["size"] == plug["size"]
    for part in (header, plug):
        assert part["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "STAND-IN" in header["provenance"]["part"] and "STAND-IN" in plug["provenance"]["model"]
    assert "NO MAKER" in header["provenance"]["part"] and "3072980925" in header["provenance"]["part"]


def test_the_plug_has_one_wire_for_each_of_the_six_cells():
    plug = contract(PLUG)
    wires = {k: v for k, v in plug["connection-points"].items() if k.startswith("wire-")}
    assert len(wires) == 6
    rows = sorted({v["at"][1] for v in wires.values()})
    assert len(rows) == 2 and all(sum(1 for v in wires.values() if v["at"][1] == y) == 3 for y in rows)
    svg = (path_of(PLUG) / "skins" / "default.svg").read_text()
    assert len(re.findall(r'<circle id="wire-\d"', svg)) == 6


def test_the_supply_composes_the_header_at_the_box_of_the_block_its_skin_draws():
    c = contract(SUPPLY)
    (part,) = c["parts"]
    assert (part["ref"], part["id"]) == (HEADER, "dc-header")
    block = c["elements"]["dc-input"]
    assert part["at"] == block["at"], "the part stands where the block stands, so no drawn box moves"
    assert [contract(HEADER)["size"]["w"], contract(HEADER)["size"]["h"]] == block["size"]


def test_the_header_draws_the_block_the_skin_draws_shape_for_shape():
    (part,) = contract(SUPPLY)["parts"]
    ox, oy = part["at"]
    skin = rects((path_of(SUPPLY) / "skins" / "default.svg").read_text())
    drawn = rects((path_of(HEADER) / "skins" / "default.svg").read_text())
    assert len(drawn) == 8, "the body, six cells and the bar"
    for x, y, w, h in drawn:
        assert (round(x + ox, 3), round(y + oy, 3), w, h) in skin


def test_the_supply_states_the_roles_the_printed_marks_give_and_no_dc_port():
    c = contract(SUPPLY)
    assert "dc" not in c
    prov = c["provenance"]
    assert {"connector", "roles", "no-dc-port", "pe-lug"} <= set(prov)
    roles = prov["roles"]
    for word in ("`pos`", "`neg`", '"V+"', '"V-"', "DC+(+48V)", "DC-(0)", "no voltage is carried"):
        assert word in roles
    text = prov["connector"]
    assert "not a maker's identity" in text and "3072980925" in text and "2204535-3" in text
    assert "claims no maker" in text
    assert "PE LUG" in prov["pe-lug"] and "11.0 mm" in prov["pe-lug"]


def test_the_skin_and_the_description_are_the_ones_the_block_was_drawn_with():
    c = contract(SUPPLY)
    assert c["description"].rstrip().endswith("front-to-back (exhaust) airflow")
    assert "two-row DC input connector and its lug screws" in c["description"]
    svg = (path_of(SUPPLY) / "skins" / "default.svg").read_text()
    assert 'id="dc-input"' in svg and 'id="lug-holes"' in svg and "dc-header" not in svg


def test_the_exporter_names_the_header_as_a_plain_other_connector():
    assert dx.PART_POWER["ufispace/psu-242-dc-header"] == "other"
    assert "6-position" in dx.POWER_LABEL["ufispace/psu-242-dc-header"]


def test_the_exported_power_port_of_the_supply_is_named_for_the_header():
    for fmt in ("netbox", "nautobot"):
        doc = yaml.safe_load((LIB / "exports" / fmt / "module-types" / "UfiSpace" / "PSU-242-DEERN.yaml").read_text())
        (port,) = doc["power-ports"]
        assert port["name"] == "{module}/dc-header" and port["type"] == "other" and "6-position" in port["label"]


@pytest.mark.heavy
def test_the_index_lists_the_header_with_its_key_and_mate_point_and_the_plug_as_a_port(index):
    assert (index[HEADER]["class"], index[HEADER]["interface"], index[HEADER]["mate"]) == ("inlet", KEY, [11.0, 11.3])
    assert index[PLUG]["class"] == "port" and index[PLUG]["mate"] == [11.0, 11.3]
    assert index[SUPPLY]["version"] == "1.2.0"


def test_the_record_of_the_supply_is_gone():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    assert (SUPPLY, "C19") not in {(r["part"], r["code"]) for r in doc["rows"]}
    assert doc["cap"] == len(doc["rows"])

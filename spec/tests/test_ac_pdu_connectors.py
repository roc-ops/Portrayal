"""The PDU side of the AC connectors (#933).

Outlet faces (std/c19-outlet@1, std/nema-5-20r@1), the jumper ends that go into
a PDU's outlets (generic/c14-plug@1, generic/c20-plug@1) and the faces of the
plugs at the end of a PDU's input cord. Read from the real library.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "library/components"
SVG = "{http://www.w3.org/2000/svg}"

OUTLETS = {"std/c19-outlet": "iec-60320-c19", "std/nema-5-20r": "nema-5-20r"}
INPUT_PLUGS = {"generic/nema-l6-20p-plug": "nema-l6-20p",
               "generic/nema-l5-20p-plug": "nema-l5-20p",
               "generic/nema-5-20p-plug": "nema-5-20p",
               "generic/cs8365c-plug": "cs8365c"}
CORD_ENDS = ["generic/c14-plug", "generic/c20-plug"]


def contract(ref):
    return yaml.safe_load((COMP / ref / "v1/contract.yaml").read_text())


def std():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def test_each_outlet_exports_as_its_upstream_type():
    for ref, typ in OUTLETS.items():
        assert dx.PART_OUTLET[ref] == typ
        assert typ in dx.OUTLET_TYPES


def test_each_input_plug_exports_as_its_upstream_power_port_type():
    for ref, typ in INPUT_PLUGS.items():
        assert dx.PART_POWER[ref] == typ


def test_a_jumper_end_is_not_a_device_port():
    """As generic/c13-plug and generic/c19-plug have no row: a cord end is the
    far end of a jumper, not a port of the device it is drawn on."""
    for ref in CORD_ENDS + ["generic/c13-plug", "generic/c19-plug"]:
        assert ref not in dx.PART_POWER and ref not in dx.PART_OUTLET


@pytest.mark.parametrize("ref", sorted(OUTLETS) + sorted(INPUT_PLUGS) + CORD_ENDS)
def test_size_is_the_registry_entry(ref):
    c = contract(ref)
    entry = std()[c["conforms"]]
    assert (c["size"]["w"], c["size"]["h"]) == (entry["w"], entry["h"])


def test_the_c19_well_is_walled_along_its_outline():
    """relief.cavity names an evenodd <path>, the R5 outline with the nose cut
    out, so relief.js builds outlineWalls along it - std/c13-outlet@1's
    pattern - rather than a box; a rect node would keep the box."""
    c = contract("std/c19-outlet")
    root = ET.parse(COMP / "std/c19-outlet/v1/skins/default.svg").getroot()
    el = next(e for e in root.iter() if e.get("id") == c["relief"]["cavity"])
    assert el.tag == f"{SVG}path" and el.get("fill-rule") == "evenodd"
    assert el.get("d").count("M ") == 2 and " A " in el.get("d")
    # the well is as deep as the C19 nose that stands in it (Volex VAC19)
    assert c["size"]["d"] == 20


def test_a_flat_receptacle_face_has_no_pit():
    """size.d on a fixed part is built as a pit behind its whole box; the
    5-20R's holes are pockets instead."""
    c = contract("std/nema-5-20r")
    assert "d" not in c["size"]
    assert {f["node"] for f in c["relief"]["features"] if f.get("pocket")} == \
        {"hole-earth", "slot-line", "slot-neutral"}


def test_the_c20_plug_stands_its_length_less_the_well_in_front_of_the_outlet():
    plug = contract("generic/c20-plug")
    assert plug["mates"] == contract("std/c19-outlet")["interface"] == "iec-c19"
    feats = {f["node"]: f for f in plug["relief"]["features"]}
    boot = feats["relief-boot"]
    overall = std()["c20-plug"]["depth"]
    well = contract("std/c19-outlet")["size"]["d"]
    assert boot["lift"] + boot["cyl"] == pytest.approx(overall - well)
    assert feats["stub"]["lift"] == pytest.approx(overall - well)


def test_the_c14_plug_stands_its_length_less_the_c13_well():
    """The C13 outlet's well is 18 (the C13 nose's 18 MIN); pinned here so the
    plug follows if that part's depth moves."""
    plug = contract("generic/c14-plug")
    outlet = contract("std/c13-outlet")
    assert plug["mates"] == outlet["interface"] == "iec-c13"
    assert outlet["size"]["d"] == 18
    feats = {f["node"]: f for f in contract("generic/c14-plug")["relief"]["features"]}
    boot = feats["relief-boot"]
    assert boot["lift"] + boot["cyl"] == pytest.approx(std()["c14-plug"]["depth"] - 18)
    assert feats["stub"]["lift"] == pytest.approx(std()["c14-plug"]["depth"] - 18)

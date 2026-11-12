"""The NEMA 6-15P and 6-20P plug faces: the plug at the end of a 250 V cord.

Read from the real library. Each is a face with no mate, as generic/nema-5-20p-plug@1
is, and exports as the power-port type a fixed cord ending in it gives a device.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "library/components"
SVG = "{http://www.w3.org/2000/svg}"

PLUGS = {"generic/nema-6-15p-plug": ("nema-6-15p", 15), "generic/nema-6-20p-plug": ("nema-6-20p", 20)}


def contract(ref):
    return yaml.safe_load((COMP / ref / "v1/contract.yaml").read_text())


def skin(ref):
    return ET.parse(COMP / ref / "v1/skins/default.svg").getroot()


def std():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


@pytest.mark.parametrize("ref", sorted(PLUGS))
def test_the_plug_face_states_what_it_is(ref):
    typ, amps = PLUGS[ref]
    c = contract(ref)
    assert c["class"] == "inlet" and c["profile"] == "power" and "mates" not in c
    assert c["conforms"] == ref.split("/")[1]
    assert c["attrs"] == {"plug": typ, "rating-a": amps, "rating-v": 250}
    assert "d" not in c["size"], "a generic plug face has no depth"


@pytest.mark.parametrize("ref", sorted(PLUGS))
def test_size_is_the_registry_entry(ref):
    c = contract(ref)
    entry = std()[c["conforms"]]
    assert (c["size"]["w"], c["size"]["h"]) == (entry["w"], entry["h"])


@pytest.mark.parametrize("ref", sorted(PLUGS))
def test_exports_as_an_other_power_port_labelled_with_the_plug(ref):
    """No target's power-port slug for the plug has been read from a source file, so it is `other`."""
    assert dx.PART_POWER[ref] == "other"
    assert dx.POWER_LABEL[ref] == "NEMA " + PLUGS[ref][0][len("nema-"):].upper() + " plug"


@pytest.mark.parametrize("ref", sorted(PLUGS))
def test_every_relief_node_is_drawn_in_the_skin(ref):
    ids = {e.get("id") for e in skin(ref).iter()}
    for f in contract(ref)["relief"]["features"]:
        assert f["node"] in ids


def test_the_6_20_key_turns_one_blade_a_quarter():
    """6-15P: both blades lie the same way. 6-20P: one is turned, as on the 5-20P."""
    def blades(ref):
        out = {}
        for e in skin(ref).iter():
            if (e.get("id") or "").startswith("blade-"):
                out[e.get("id")] = (float(e.get("width")), float(e.get("height")))
        return out

    flat = blades("generic/nema-6-15p-plug")
    keyed = blades("generic/nema-6-20p-plug")
    assert len(flat) == len(keyed) == 2
    assert len({w > h for w, h in flat.values()}) == 1
    assert len({w > h for w, h in keyed.values()}) == 2

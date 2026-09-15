"""The FS archetypes - one real part per shape the catalogue contains.

Every figure here is either measured off FS's own dimensioned drawing (the
enclosure) or off a face-on render validated by panel_measure (the cassettes),
except the splice cassette, which no image in the corpus shows at all. Where a
number is estimated the contract says so; these tests check the claims, not the
prose.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))


def device(rel):
    p = LIB / "devices" / rel / "device.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def contract(rel):
    p = LIB / "components" / rel / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_the_enclosure_carries_its_dimensioned_figures():
    """Read off page 7 of FS's own datasheet: front and top views, dimensioned.

    448.0 body in a 482.6 rack, 44.0 high, 432.8 deep. This is the only part in
    this plan whose size needs no estimating at all.

    A DEVICE DECLARES `chassis`, not `size` - `size` is a per-view key. See
    library/devices/smartoptics/dcp-2/device.yaml for the shape.
    """
    d = device("fs/fhd-1ufce")
    assert d is not None, "fs/fhd-1ufce not built"
    assert d["manufacturer"] == "FS.com"
    ch = d["chassis"]
    assert (ch["width"], ch["height"], ch["depth"]) == (448.0, 44.0, 432.8)
    assert ch["ru"] == 1


def test_the_enclosure_holds_four_modules():
    """Four slots at the 108.97 module width need 435.88, inside the 448.0 body."""
    d = device("fs/fhd-1ufce")
    bays = d["views"]["front"]["components"]["bays"]
    assert len(bays) == 4, f"expected 4 cassette slots, found {len(bays)}"
    assert 4 * 108.97 <= 448.0


def test_the_enclosure_accepts_every_fs_cassette_in_the_library():
    """THIS IS WHAT KEEPS THE `accepts` LIST HONEST.

    Four later tasks each add a cassette, and an `accepts` list written once is
    an omission that passes quietly - the enclosure would ship accepting one of
    the five modules that seat in it. Every FHD cassette seats in every FHD
    enclosure; that is what the format is for, so the assertion is total rather
    than a list someone maintains by hand.
    """
    d = device("fs/fhd-1ufce")
    accepted = set()
    for bay in d["views"]["front"]["components"]["bays"]:
        accepted |= set(bay.get("accepts") or [])
    modelled = set()
    for c in (LIB / "components" / "fs").glob("*/v*/contract.yaml"):
        doc = yaml.safe_load(c.read_text()) or {}
        if doc.get("kind") != "module":
            continue                       # a rear face is not a seatable part
        modelled.add(f"fs/{doc['name']}@{c.parent.name[1:]}")
    missing = sorted(modelled - accepted)
    assert not missing, f"cassettes the enclosure does not accept: {missing}"


SPLICE = "fs/fhd-splice-12-lc/v1"


def test_the_splice_cassette_states_that_nothing_measured_it():
    """Eleven splice cassettes in the catalogue and not one photograph.

    The whole contract is derived from family constants. If a later intake
    fetches imagery and someone measures it, this assertion is what tells them
    the prose needs rewriting too.
    """
    c = contract(SPLICE)
    assert c is not None, "fs/fhd-splice-12-lc@1 not built"
    conf = set(c["size-confidence"].values())
    assert conf <= {"estimated", "borrowed"}, \
        f"claims a measurement the corpus cannot support: {c['size-confidence']}"
    note = (c.get("provenance") or {}).get("size", "")
    assert "no image" in note.lower() or "not photographed" in note.lower(), \
        "provenance must say plainly that no imagery of this part exists"


def test_the_splice_cassettes_polish_is_sourced_not_assumed():
    """Unlike SKU 57016, this row names it: 'Fiber Splice Cassette, LC UPC'."""
    c = contract(SPLICE)
    assert c["optical"]["polish"] == "upc"
    note = (c.get("provenance") or {}).get("optical", "")
    assert "382907" in note, "cite the catalogue row that names the polish"


def test_the_splice_cassette_has_a_splice_rear():
    c = contract(SPLICE)
    assert c["optical"]["rear-kind"] == "splice"
    assert (c.get("faces") or {}).get("rear"), "a rear-kind needs a rear face (L87)"
    assert len(c["optical"]["paths"]) == 12

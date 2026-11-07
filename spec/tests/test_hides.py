"""A cover says what it hides (#642).

A cover is a removable part that hides others - a bezel over drives, a filter
cover over PSUs. A placement writes `hides: [...]`; the compiler writes
`data-hides="<id> <id> ..."` on the cover's group, and one attribute says both
"this is a cover" and what it covers. `data-for` keeps its meanings, since
screws, ground studs and ESD jacks carry it too. L196 checks every id.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

from portrayal import lint
import pytest

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
ROOTS = [str(LIB)]
COVER = "casa/c40g-psu-cover@1"          # 349.2 x 38.2
RING = "fs/cmh-5dr1u-n-ring@1"           # 12.7 x 44


def _built(pattern):
    found = sorted((LIB / "dist").glob(pattern))
    assert found, f"library/dist has no {pattern}: these read the build, so run ./build.sh first"
    return found


def _group(svg, gid):
    return next((g for g in ET.parse(svg).iter() if g.get("id") == gid), None)


def _paths(svg):
    return {n.get("data-path") for n in ET.parse(svg).iter() if n.get("data-path")}


# --- the compiler ------------------------------------------------------------

def test_the_c40g_cover_names_its_four_psus():
    svg = _built("c40g.docsis-classic.front.svg")[0]
    cover = _group(svg, "psu-cover")
    assert cover is not None
    assert cover.get("data-hides").split() == ["psu-1", "psu-2", "psu-3", "psu-4"]
    assert cover.get("data-for").split() == ["psu-1", "psu-2", "psu-3", "psu-4"], \
        "`for` keeps its meaning beside `hides`"
    assert set(cover.get("data-hides").split()) <= _paths(svg), \
        "a consumer finds each hidden part in the same drawing"


def test_the_r660_bezel_names_its_drives():
    faces = _built("r660.*.front*.svg")
    hid = {}
    for svg in faces:
        bezel = _group(svg, "bezel")
        if bezel is not None and bezel.get("data-hides"):
            hid[svg.name] = bezel.get("data-hides").split()
            assert set(hid[svg.name]) <= _paths(svg), svg.name
            assert not {"vga", "mark-vga", "centre-vent"} & set(hid[svg.name]), \
                "the bezel is said to hide drives"
    assert hid, "no R660 front face carries a bezel with data-hides"
    assert any(len(v) == 10 and v[0] == "drive-0" for v in hid.values())
    assert any(len(v) == 16 and v[0] == "e3s-0" for v in hid.values())


@pytest.mark.heavy
def test_nothing_else_in_the_library_carries_data_hides():
    carriers = set()
    for svg in _built("*.svg"):
        for n in ET.parse(svg).iter():
            if n.get("data-hides") is not None:
                carriers.add((svg.name.split(".")[0], n.get("id")))
    # the R660xs seats the R660's security bezel
    # the R6615's bezel is the R660's part over its own fronts
    # the R6625's security bezel hides its drives the way the R660's does
    # the R760's security bezel (dell/bezel-2u-16g@1) names its drives as the R660's does
    # ("r960", "bezel"): the PowerEdge R960's honeycomb security bezel, over its drives
    # the Entra EN8100 and EN8400's power entry covers hide the port entry modules beneath them (guide p35)
    assert carriers == {("c40g", "psu-cover"), ("r660", "bezel"), ("r660xs", "bezel"),
                        ("r6615", "bezel"), ("r6625", "bezel"), ("r760", "bezel"),
                        ("r960", "bezel"), ("en8100", "pec-1"), ("en8100", "pec-2"),
                        ("en8400", "pec-1"), ("en8400", "pec-2")}, carriers


# --- L196 --------------------------------------------------------------------

def _codes(views):
    with lint.collecting() as found:
        lint.lint_device_hides("device.yaml", {"views": views}, ROOTS)
    return [m for m in found.errors + found.warnings if "[L196]" in m]


def _front(cover_hides, bays=None, placements=(), cover_at=(0.0, 0.0), **view):
    return {"front": {"components": {
        "bays": bays if bays is not None else [
            {"id": "psu-1", "at": [10.0, 5.0], "size": {"w": 80.0, "h": 30.0}}],
        "placements": [{"ref": COVER, "id": "cover", "at": list(cover_at),
                        "hides": cover_hides}, *placements]}, **view}}


def test_L196_a_bay_the_cover_overlaps_is_quiet():
    assert not _codes(_front(["psu-1"]))


def test_L196_a_placement_the_cover_overlaps_is_quiet():
    ring = {"ref": RING, "id": "ring", "at": [20.0, 0.0]}
    assert not _codes(_front(["ring"], placements=[ring]))


def test_L196_an_id_that_names_nothing_is_an_error():
    found = _codes(_front(["psu-9"]))
    assert found and "not a placement or a bay on this face" in found[0]


def test_L196_an_id_on_another_face_is_an_error():
    views = _front(["psu-1"], bays=[])
    views["rear"] = {"components": {"bays": [
        {"id": "psu-1", "at": [10.0, 5.0], "size": {"w": 80.0, "h": 30.0}}]}}
    found = _codes(views)
    assert found and "on rear, not on this face" in found[0]


def test_L196_an_id_the_cover_does_not_overlap_is_an_error():
    bays = [{"id": "psu-1", "at": [10.0, 100.0], "size": {"w": 80.0, "h": 30.0}}]
    found = _codes(_front(["psu-1"], bays=bays))
    assert found and "does not overlap" in found[0]


def test_L196_a_cover_cannot_hide_itself():
    found = _codes(_front(["cover"]))
    assert found and "itself" in found[0]

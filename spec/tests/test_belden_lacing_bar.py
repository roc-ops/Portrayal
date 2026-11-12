"""Belden 9512-1903, the rack-mount lacing bar (roc-ops/Portrayal#1103, part of #1091).

The one source is Belden's technical data sheet (revision 0.41, 05-31-2024): 1U, 0.5 in high, 19 in wide,
0.5 in deep, 0.5 lb, steel, black powder-coated. It holds no drawing of the bar, so the bar is modelled as
its overall size and nothing inside it: no tie point, no hole and no cut-out is drawn, and each is a named
gap. What is true of the library is held here: the size is the data sheet's, no figure the sheet does not
give is drawn, and the gaps that say so are present.

The size and gap tests read only the device file; the catalogue test reads the build (`library/dist`) and
skips without it, like the other sweeps over compiled drawings.
"""
import json
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
MM = 25.4
LB = 0.45359237
NAME = "9512-1903"

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")


def device():
    return yaml.safe_load((LIB / "devices" / "belden" / NAME / "device.yaml").read_text())


def close(a, b, tol=0.01):
    return abs(a - b) <= tol


def test_the_envelope_is_the_data_sheets_and_the_bar_bolts_to_the_rail_face():
    doc = device()
    c = doc["chassis"]
    assert doc["manufacturer"] == "Belden" and doc["model"] == NAME
    assert c["width"] == 482.6, "19 in, the bar's own length"
    assert close(c["height"], 0.5 * MM) and close(c["depth"], 0.5 * MM)
    assert c["ru"] == 1 and c["mount"] == "rack-face"
    assert close(c["weight-kg"], 0.5 * LB, 0.001) and c["weight-kg"] == doc["attrs"]["physical"]["weight-kg"]
    assert doc["attrs"]["physical"]["material"] == "Steel"
    assert doc["attrs"]["physical"]["finish"] == "Black Powdercoat Finish"
    assert doc["datasheet"]["url"] == "https://catalog.belden.com/techdata/EN/9512-1903_techdata.pdf"
    assert len(doc["datasheet"]["sha256"]) == 64


@pytest.mark.parametrize("view", ["front", "rear", "top", "bottom", "left", "right"])
def test_each_side_is_drawn_as_the_overall_size_and_nothing_the_data_sheet_does_not_give(view):
    doc = device()
    v = doc["views"][view]
    w, h = v["size"]["w"], v["size"]["h"]
    assert (w, h) in ((482.6, 12.7), (12.7, 12.7))
    assert not v.get("components") and "guides" not in v, "no part and no tie point: no document places one"
    for d in v["panel"]["decor"]:
        assert d["kind"] == "base", "only the bar's outline: no hole, no slot and no cut-out is dimensioned"
        assert d["size"] == [w, h] and d["at"] == [0, 0]


def test_the_figures_the_data_sheet_does_not_give_are_named_gaps_with_the_document_each_needs():
    gaps = {g["what"]: g for g in device()["gaps"]}
    assert {"tie-points", "end-holes", "cross-section", "height-in-unit", "mounting-screws"} <= set(gaps)
    for g in gaps.values():
        assert g["reason"] == "vendor-silent" and g["wanted"]


@pytest.mark.heavy
@needs_dist
def test_the_build_carries_the_envelope_to_the_rack_catalogue():
    r = json.loads((DIST / "rack.json").read_text())["devices"][NAME]
    assert (r["ru"], r["w"], r["mount"]) == (1, 482.6, "rack-face")
    assert close(r["d"], 12.7) and close(r["h"], 12.7)
    assert not r.get("guides"), "no tie point is placed"

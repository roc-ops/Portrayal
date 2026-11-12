"""Middle Atlantic LBP-1A, the 19 in L-shaped lacing bar (roc-ops/Portrayal#1102).

The one source for the part is the maker's generated cut sheet for LBP-1A and its SKU page: 19 in wide, 0.5 in
deep, 0.5 in high, two mounting points, no offset, L-shaped, sold in packs of 10. Neither gives a drawing of the
bar or a weight for one, so the bar is modelled as its overall size and nothing inside it: no slot, no end hole
and no section is drawn, and each is a named gap. What is true of the library is held here: the size is the
maker's, no figure the cut sheet does not give is drawn or recorded, and the gaps that say so are present.

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
NAME = "lbp-1a"

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")


def device():
    return yaml.safe_load((LIB / "devices" / "middle-atlantic" / NAME / "device.yaml").read_text())


def close(a, b, tol=0.01):
    return abs(a - b) <= tol


def test_middle_atlantic_is_a_hardware_vendor_with_its_source_named():
    vendors = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    v = vendors["middle-atlantic"]
    assert v["role"] == "hardware" and v["display"] == "Middle Atlantic"
    assert "cut sheet" in v["source"] and "LBP-1A" in v["source"]


def test_the_envelope_is_the_cut_sheets_and_the_bar_bolts_to_the_rail_face():
    doc = device()
    c = doc["chassis"]
    assert doc["manufacturer"] == "Middle Atlantic" and doc["model"] == "LBP-1A"
    assert c["width"] == 482.6, "19 in, the bar's own length"
    assert close(c["height"], 0.5 * MM) and close(c["depth"], 0.5 * MM)
    assert c["ru"] == 1 and c["mount"] == "rack-face" and c["shell"] == "sheet"
    phys = doc["attrs"]["physical"]
    assert phys["material"] == "Steel" and phys["finish"] == "Black Powder Coat" and phys["color"] == "Black"
    assert doc["datasheet"]["url"].endswith("/lbp_horizontal_lacer_bar/LBP-1A")
    assert len(doc["datasheet"]["sha256"]) == 64


def test_no_weight_is_recorded_because_no_document_gives_one_for_this_bar():
    doc = device()
    assert "weight-kg" not in doc["chassis"] and "weight-kg" not in doc["attrs"]["physical"]
    assert "weight" in {g["what"] for g in doc["gaps"]}


@pytest.mark.parametrize("view", ["front", "rear", "top", "bottom", "left", "right"])
def test_each_side_is_drawn_as_the_overall_size_and_nothing_the_cut_sheet_does_not_give(view):
    doc = device()
    v = doc["views"][view]
    w, h = v["size"]["w"], v["size"]["h"]
    assert (w, h) in ((482.6, 12.7), (12.7, 12.7))
    assert not v.get("components") and "guides" not in v, "no part and no tie point: no document places one"
    for d in v["panel"]["decor"]:
        assert d["kind"] == "base", "only the bar's outline: no slot, no hole and no cut-out is dimensioned"
        assert d["size"] == [w, h] and d["at"] == [0, 0]


def test_the_figures_the_cut_sheet_does_not_give_are_named_gaps_with_the_document_each_needs():
    gaps = {g["what"]: g for g in device()["gaps"]}
    assert {"tie-points", "end-holes", "cross-section", "height-in-unit", "weight", "mounting-hardware"} <= set(gaps)
    for g in gaps.values():
        assert g["reason"] == "vendor-silent" and g["wanted"]


@pytest.mark.heavy
@needs_dist
def test_the_build_carries_the_envelope_to_the_rack_catalogue():
    r = json.loads((DIST / "rack.json").read_text())["devices"][NAME]
    assert (r["ru"], r["w"], r["mount"]) == (1, 482.6, "rack-face")
    assert close(r["d"], 12.7) and close(r["h"], 12.7)
    assert not r.get("guides"), "no tie point is placed"

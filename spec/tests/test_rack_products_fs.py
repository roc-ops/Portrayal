"""The FS four-post open frames, FS-OR4P-45U and FS-OR4P-XXU.

Every figure is read from FS's own documents: the FS-OR4P-45U datasheet and its
technical drawing, the GF4-Series quick start guide (its mounting depth table),
and the FS-OR4P-XXU datasheet. A figure no document prints is a stand-in, and a
stand-in says so three ways: its provenance confidence is `estimated`, a `gaps`
entry asks for the document that would close it, and the note says what it
stands in for. The two heights of one listing are not modelled twice.
"""
import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

from portrayal import devicelock, lint, libwalk
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/rack-product.schema.json").read_text())

# what the datasheets print (inches converted once at 25.4 mm)
DEPTH = {"min": 558.8, "max": 1016, "step": 25.4}
WANT = {
    "fs/fs-or4p-45u": {
        "form": "4-post-frame", "ru": 45, "width": 19,
        "numbering": {"direction": "bottom-up", "start": 1},
        "holes": {"style": "square"},
        "hole-centres": 465, "opening": 450,
        "rails": [{"id": "front"}, {"id": "rear", "depth": DEPTH}],
        "outer": {"w": 600, "h": 2104.8, "d": 1049},
        "load": {"static-kg": 907.18},
        "model": "FS-OR4P-45U",
    },
    "fs/fs-or4p-xxu": {
        "form": "4-post-frame", "ru": 42, "width": 19,
        "numbering": {"direction": "bottom-up", "start": 1},
        "holes": {"style": "square"},
        "rails": [{"id": "front"}, {"id": "rear", "depth": DEPTH}],
        "load": {"static-kg": 907.18},
        "model": "FS-OR4P-XXU",
    },
}
# figures no document prints for the product, declared rather than read
STAND_INS = {
    "fs/fs-or4p-45u": ["numbering"],
    "fs/fs-or4p-xxu": ["numbering", "ru", "rails"],
}
# every figure either product states, for its provenance entries
STATED = {
    "fs/fs-or4p-45u": ["ru", "form", "width", "holes", "hole-centres", "opening",
                       "rails", "outer", "load"],
    "fs/fs-or4p-xxu": ["form", "width", "holes", "load"],
}


def rack(key):
    return load_yaml(LIB / "racks" / key / "rack.yaml")


def test_both_products_are_in_the_library_under_the_maker():
    keys = [libwalk.rack_key(f) for f in libwalk.iter_racks([LIB])]
    assert set(WANT) <= set(keys)


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_matches_its_schema(key):
    assert list(Draft202012Validator(SCHEMA).iter_errors(rack(key))) == []


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_printed_figure_is_the_sheets(key):
    doc = rack(key)
    for k, v in WANT[key].items():
        assert doc[k] == v, (key, k)
    assert doc["kind"] == "rack" and doc["manufacturer"] == "FS.com"
    assert doc["name"] == key.split("/")[1]


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_rail_depth_is_a_range_the_kit_can_step_through(key):
    rear = [r for r in rack(key)["rails"] if r["id"] == "rear"][0]["depth"]
    assert "fixed" not in rear
    assert 0 < rear["min"] < rear["max"] and rear["step"] > 0
    whole = (rear["max"] - rear["min"]) / rear["step"]
    assert abs(whole - round(whole)) < 1e-6, "max is reached from min by whole steps"
    assert "factory" not in rear, "no sheet names a default setting for the depth"


@pytest.mark.parametrize("key", sorted(WANT))
def test_no_figure_a_sheet_does_not_print_is_written(key):
    doc = rack(key)
    assert "rolling-kg" not in doc["load"]
    assert "weight-kg" not in doc
    assert "max-device-depth" not in doc
    assert "size" not in doc["holes"] and "fixing" not in doc["holes"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_a_stand_in_is_declared_three_ways(key):
    doc = rack(key)
    gaps = {g["what"]: g for g in doc.get("gaps") or []}
    for fig in STAND_INS[key]:
        prov = doc["provenance"][fig]
        assert prov["confidence"] == "estimated", (key, fig)
        assert "stand" in prov["note"].lower(), (key, fig)
        assert fig in gaps, (key, fig)
        assert gaps[fig]["reason"] in {"vendor-silent", "needs-drawing"}, (key, fig)


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_other_figure_has_a_sourced_provenance_entry(key):
    doc = rack(key)
    for fig in STATED[key]:
        prov = doc["provenance"].get(fig)
        assert prov and prov["note"].strip(), (key, fig)
        if fig not in STAND_INS[key]:
            assert prov["confidence"] in {"datasheet", "drawing"}, (key, fig)
    stated = set(doc["provenance"]) - set(STATED[key]) - set(STAND_INS[key])
    assert not stated, f"provenance for a figure the rack does not state: {stated}"


def test_the_xxu_does_not_claim_a_height_or_a_box():
    doc = rack("fs/fs-or4p-xxu")
    assert "outer" not in doc
    assert doc["provenance"]["ru"]["confidence"] == "estimated"
    gaps = {g["what"]: g for g in doc["gaps"]}
    assert gaps["ru"]["reason"] == "vendor-silent"
    assert "42U/45U" in gaps["ru"]["note"]
    assert "hole-centres" not in doc and "opening" not in doc


def test_the_45u_records_where_its_sheet_and_its_drawing_disagree():
    doc = rack("fs/fs-or4p-45u")
    gaps = {g["what"]: g for g in doc["gaps"]}
    assert gaps["outer"]["reason"] == "sources-disagree"
    for figure in ("1016", "1049", "591.8"):
        assert figure in gaps["outer"]["note"]
    assert doc["outer"]["d"] == 1049 != doc["rails"][1]["depth"]["max"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_sources_are_registered_and_public(key):
    doc = rack(key)
    assert "datasheet" in doc["datasheet"]["title"].lower()
    assert doc["datasheet"]["url"].startswith("https://resource.fs.com/")
    for r in doc.get("references", []) + [doc["datasheet"]]:
        assert r.get("url", "https://").startswith("https://"), r
    for r in doc.get("references", []):
        assert len(r["sha256"]) == 64, "a copy the project holds carries its hash"


def test_the_45u_cites_the_depth_table_it_reads_the_range_from():
    refs = rack("fs/fs-or4p-45u")["references"]
    assert any("Quick Start Guide" in r["title"] for r in refs)


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_says_nothing_private(key):
    text = (LIB / "racks" / key / "rack.yaml").read_text().lower()
    for word in ("okf", "/volumes", "/home/", "/mnt/", "fs-hw"):
        assert word not in text, word


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_is_pinned_and_passes_its_rule(key):
    assert (LIB / "racks" / key / "rack.lock.json").exists()
    got = []
    real = lint.err
    lint.err = lambda p, rule, msg: got.append((rule, msg))
    try:
        lint.lint_rack(LIB / "racks" / key / "rack.yaml", rack(key), [str(LIB)])
    finally:
        lint.err = real
    assert got == []
    assert devicelock.check_racks(LIB) == []


def test_fs_is_a_registered_maker():
    vendors = load_yaml(ROOT / "spec/schemas/vendors.yaml")["vendors"]
    assert vendors["fs"]["display"]

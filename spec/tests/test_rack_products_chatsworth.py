"""Chatsworth's two-post frames: the Standard Rack 55053-X03 and the SeismicFrame 13853-X03.

Every figure is read from the maker's two data sheets (the Standard Rack
product data sheet, Rev.11 03/24, and the SeismicFrame data sheet, Rev11
10/26). A figure no sheet prints is a stand-in, and a stand-in says so three
ways: its provenance confidence is `estimated`, a `gaps` entry asks for the
document that would close it, and the note names what it stands in for. The
SeismicFrame's seismic rating is a rating under a standard, not a static
load, so it is kept out of `load`.
"""
import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

from portrayal import devicelock, dcim_export, lint, libwalk, racks_index
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/rack-product.schema.json").read_text())

# what each data sheet prints
WANT = {
    "chatsworth/55053-x03": {
        "model": "55053-X03", "form": "2-post-frame", "ru": 45, "width": 19,
        "holes": {"style": "tapped", "thread": "12-24"},
        "hole-centres": 465.3, "opening": 451.9,
        "rails": [{"id": "front"}],
        "max-device-depth": 508,
        "outer": {"w": 516.1, "h": 2133.6, "d": 381.0},
        "load": {"static-kg": 453.6},
    },
    "chatsworth/13853-x03": {
        "model": "13853-X03", "form": "2-post-frame", "ru": 44, "width": 19,
        "holes": {"style": "tapped", "thread": "12-24"},
        "opening": 450.85,
        "rails": [{"id": "front"}],
        "outer": {"w": 610, "h": 2133.6, "d": 380},
    },
}
# the figures neither sheet prints, written as stand-ins
STAND_INS = {
    "chatsworth/55053-x03": ["numbering"],
    "chatsworth/13853-x03": ["numbering", "hole-centres"],
}
# what a product states and cites to a sheet (stand-ins aside)
SOURCED = {
    "chatsworth/55053-x03": ["ru", "form", "width", "holes", "hole-centres", "opening", "rails",
                             "max-device-depth", "outer", "load"],
    "chatsworth/13853-x03": ["ru", "form", "width", "holes", "opening", "rails", "outer"],
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
    assert doc["kind"] == "rack" and doc["manufacturer"] == "Chatsworth Products"
    assert doc["name"] == key.split("/")[1]
    assert doc["maturity"] == "modelled"
    assert list(doc["part-numbers"]) == [doc["model"]]


@pytest.mark.parametrize("key", sorted(WANT))
def test_a_stand_in_is_declared_three_ways(key):
    doc = rack(key)
    assert doc["numbering"] == {"direction": "bottom-up", "start": 1}
    if "hole-centres" in STAND_INS[key]:
        assert doc["hole-centres"] == 465.1
    gaps = {g["what"]: g for g in doc.get("gaps") or []}
    for fig in STAND_INS[key]:
        prov = doc["provenance"][fig]
        assert prov["confidence"] == "estimated", (key, fig)
        assert "stand-in" in prov["note"].lower(), (key, fig)
        assert fig in gaps, (key, fig)
        assert gaps[fig]["reason"] in {"vendor-silent", "needs-drawing"}, (key, fig)


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_other_figure_has_a_sourced_provenance_entry(key):
    doc = rack(key)
    for fig in SOURCED[key]:
        prov = doc["provenance"].get(fig)
        assert prov and prov["note"].strip(), (key, fig)
        assert prov["confidence"] in {"datasheet", "drawing"}, (key, fig)
    stated = set(doc["provenance"]) - set(SOURCED[key]) - set(STAND_INS[key])
    assert not stated, f"provenance for a figure the rack does not state: {stated}"
    estimated = {k for k, v in doc["provenance"].items() if v["confidence"] == "estimated"}
    assert estimated == set(STAND_INS[key])


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_sources_are_public(key):
    doc = rack(key)
    assert "data sheet" in doc["datasheet"]["title"].lower()
    assert doc["references"]
    for r in doc["references"] + [doc["datasheet"]]:
        assert r.get("url", "https://").startswith("https://"), r
        assert "sha256" not in r, "a hash is for a copy the project holds"


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_says_nothing_private(key):
    text = (LIB / "racks" / key / "rack.yaml").read_text().lower()
    for word in ("okf", "/volumes", "/home/", "/data/", "customer", "agent", "sha256"):
        assert word not in text, word


def test_the_seismic_frame_keeps_its_rating_out_of_the_figures():
    doc = rack("chatsworth/13853-x03")
    assert not {"load", "weight-kg", "max-device-depth"} & set(doc)
    gaps = {g["what"]: g for g in doc["gaps"]}
    assert gaps["load"]["reason"] == "vendor-silent"
    assert "seismic" in gaps["load"]["note"].lower()
    assert "seismic" in doc["description"].lower() and "zone 4" in doc["description"].lower()


def test_the_seismic_frame_names_the_channel_depth_the_sheet_misprints():
    gaps = {g["what"]: g for g in rack("chatsworth/13853-x03")["gaps"]}
    assert gaps["channel-depth"]["reason"] == "sources-disagree"
    note = gaps["channel-depth"]["note"]
    assert "244" in note and "294" in note


def test_the_standard_rack_names_the_load_and_what_it_leaves_open():
    doc = rack("chatsworth/55053-x03")
    assert "weight-kg" not in doc
    gaps = {g["what"]: g for g in doc["gaps"]}
    assert "453.1" in gaps["load"]["note"] and gaps["load"]["reason"] == "sources-disagree"
    assert gaps["load-kind"]["reason"] == "vendor-silent"
    assert gaps["rail-length"]["reason"] == "sources-disagree"
    assert gaps["weight-kg"]["reason"] == "vendor-silent"
    assert "17-3/4" in doc["provenance"]["opening"]["note"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_a_two_post_frame_has_no_rear_rail(key):
    assert [r["id"] for r in rack(key)["rails"]] == ["front"]


def test_no_twenty_three_inch_product_is_written():
    for key in (libwalk.rack_key(f) for f in libwalk.iter_racks([LIB])):
        if key.startswith("chatsworth/"):
            assert rack(key)["width"] == 19, key


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_is_locked_and_passes_its_rule(key):
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


# ---- the DCIM export -----------------------------------------------------------

@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("chatsworth-rack-export")
    racks_index.build([LIB], tmp / "dist", ROOT / "spec/schemas")
    dcim_export.export_racks(tmp / "dist", tmp / "exports")
    return tmp / "exports"


def doc_at(root, target, model):
    return yaml.safe_load((root / target / "rack-types" / "Chatsworth Products" / f"{model}.yaml").read_text())


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_netbox_rack_type_carries_the_form_the_height_and_the_box(exported, key):
    want = WANT[key]
    doc = doc_at(exported, "netbox", want["model"])
    assert doc["form_factor"] == "2-post-frame" and doc["u_height"] == want["ru"]
    assert doc["width"] == 19 and "mounting_depth" not in doc and "weight" not in doc
    out = want["outer"]
    assert (doc["outer_width"], doc["outer_height"], doc["outer_depth"], doc["outer_unit"]) == \
        (out["w"], out["h"], out["d"], "mm")
    assert "tapped" in doc["comments"] and "12-24" in doc["comments"]


def test_only_the_standard_rack_exports_a_static_load(exported):
    nb = doc_at(exported, "netbox", "55053-X03")
    assert (nb["max_weight"], nb["weight_unit"]) == (453.6, "kg")
    assert "max_weight" not in doc_at(exported, "netbox", "13853-X03")


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_nautobot_rack_names_the_form_and_the_box(exported, key):
    want = WANT[key]
    doc = doc_at(exported, "nautobot", want["model"])
    assert doc["type"] == "2-post-frame" and doc["u_height"] == want["ru"]
    assert doc["outer_width"] == want["outer"]["w"] and doc["outer_depth"] == want["outer"]["d"]
    assert f"outer height {want['outer']['h']:g} mm" in doc["comments"]


def test_the_committed_export_holds_both_products():
    for want in WANT.values():
        for target in ("netbox", "nautobot"):
            f = LIB / "exports" / target / "rack-types" / "Chatsworth Products" / f"{want['model']}.yaml"
            assert f.exists(), f

"""The StarTech.com 12U and 42U open four-post frames as rack products (#1118, #1109).

Every figure is read from StarTech.com's own public pages: the 4POSTRACK12A data
sheet and a dated print of the 4POSTRACK42 product page. Where a page prints
a figure in two units the finer print is written and the other is checked to lie
inside its rounding. A figure no page prints is a stand-in, and a stand-in says
so three ways: its provenance confidence is `estimated`, a `gaps` entry asks for
the document that would close it, and the note names what it stands in for.
Neither page prints a rail step, a hole size or a drawing, so the rear rail's
depth is a range with no `step` and nothing here is drawn from a picture.
"""
import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator
from pytest import approx

from portrayal import dcim_export, devicelock, lint, libwalk, racks_index
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/rack-product.schema.json").read_text())

# What each page prints, in mm and kg, with the half-step of the print it was written from.
WANT = {
    "startech/4postrack12a": {
        "model": "4POSTRACK12A", "ru": 12,
        "rear-depth": {"min": (97, 0.5), "max": (913, 0.5)},
        "outer": {"w": (534, 0.5), "h": (657, 0.5), "d": (913, 0.5)},
        "weight-kg": (15.60, 0.05), "static-kg": (270.07, 0.5), "rolling-kg": None,
    },
    "startech/4postrack42": {
        "model": "4POSTRACK42", "ru": 42,
        "rear-depth": {"min": (558.8, 0.1), "max": (1016.0, 0.1)},
        "outer": {"w": (600, 0.5), "h": (2040, 15), "d": (1130, 15)},
        "weight-kg": (38.51, 0.05), "static-kg": (600.10, 0.5), "rolling-kg": (360.06, 0.5),
    },
}
# EIA-310 figures and the direction no page gives: declared, not read
STAND_INS = ["numbering", "hole-centres", "opening"]
# what each page is
SOURCES = {
    "startech/4postrack12a": "https://media.startech.com/cms/pdfs/4postrack12a_datasheet.pdf",
    "startech/4postrack42": "https://www.startech.com/en-us/server-management/4postrack42",
}


def rack(key):
    return load_yaml(LIB / "racks" / key / "rack.yaml")


def rear(key):
    return next(r for r in rack(key)["rails"] if r["id"] == "rear")


def gaps(key):
    return {g["what"]: g for g in rack(key).get("gaps") or []}


def test_both_products_are_in_the_library_under_the_maker():
    keys = {libwalk.rack_key(f) for f in libwalk.iter_racks([LIB])}
    assert set(WANT) <= keys


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_matches_its_schema(key):
    assert list(Draft202012Validator(SCHEMA).iter_errors(rack(key))) == []


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_is_an_open_four_post_frame_with_square_holes(key):
    doc = rack(key)
    assert doc["kind"] == "rack" and doc["manufacturer"] == "StarTech.com"
    assert doc["name"] == key.split("/")[1] and doc["model"] == WANT[key]["model"]
    assert doc["form"] == "4-post-frame" and doc["ru"] == WANT[key]["ru"] and doc["width"] == 19
    assert doc["maturity"] == "modelled"
    assert doc["holes"] == {"style": "square", "fixing": "cage nut"}
    assert [r["id"] for r in doc["rails"]] == ["front", "rear"]
    assert doc["part-numbers"] and WANT[key]["model"] in doc["part-numbers"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_printed_figure_is_the_pages_within_its_print(key):
    doc, want = rack(key), WANT[key]
    for k, (v, tol) in want["outer"].items():
        assert doc["outer"][k] == approx(v, abs=tol), (key, "outer", k)
    assert set(doc["outer"]) == {"w", "h", "d"}
    assert doc["weight-kg"] == approx(want["weight-kg"][0], abs=want["weight-kg"][1])
    assert doc["load"]["static-kg"] == approx(want["static-kg"][0], abs=want["static-kg"][1])
    for k, (v, tol) in want["rear-depth"].items():
        assert rear(key)["depth"][k] == approx(v, abs=tol), (key, "depth", k)


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_rear_rail_is_a_range_with_no_step(key):
    depth = rear(key)["depth"]
    assert set(depth) == {"min", "max"}
    assert 0 < depth["min"] < depth["max"]
    assert "depth" not in next(r for r in rack(key)["rails"] if r["id"] == "front")
    assert "rail-depth-step" in gaps(key)
    assert gaps(key)["rail-depth-step"]["reason"] == "vendor-silent"


def test_the_42u_states_a_rolling_load_and_the_12u_does_not():
    want = WANT["startech/4postrack42"]["rolling-kg"]
    assert rack("startech/4postrack42")["load"]["rolling-kg"] == approx(want[0], abs=want[1])
    assert set(rack("startech/4postrack12a")["load"]) == {"static-kg"}
    assert "rolling-kg" in rack("startech/4postrack42")["load"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_no_usable_depth_and_no_hole_size_is_written(key):
    doc = rack(key)
    assert "max-device-depth" not in doc and "size" not in doc["holes"]
    assert gaps(key)["max-device-depth"]["reason"] == "vendor-silent"
    assert gaps(key)["hole-size"]["reason"] == "vendor-silent"


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_stand_ins_are_eia_310_and_the_default_direction(key):
    doc = rack(key)
    assert doc["numbering"] == {"direction": "bottom-up", "start": 1}
    assert doc["hole-centres"] == 465.1 and doc["opening"] == 450.85


@pytest.mark.parametrize("key", sorted(WANT))
def test_a_stand_in_is_declared_three_ways(key):
    doc, g = rack(key), gaps(key)
    for fig in STAND_INS:
        prov = doc["provenance"][fig]
        assert prov["confidence"] == "estimated", (key, fig)
        assert "stand-in" in prov["note"].lower(), (key, fig)
        assert fig in g, (key, fig)
        assert g[fig]["reason"] in {"vendor-silent", "needs-drawing"}, (key, fig)


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_other_stated_figure_has_a_sourced_provenance_entry(key):
    doc = rack(key)
    figures = ["ru", "form", "holes", "rails", "outer", "weight-kg", "load"]
    # the 12U sheet prints no rail width; the 42U page's listing line prints 19in
    if key != "startech/4postrack12a":
        figures.append("width")
    for fig in figures:
        prov = doc["provenance"].get(fig)
        assert prov and prov["note"].strip(), (key, fig)
        assert prov["confidence"] == "datasheet", (key, fig)
    stated = set(doc["provenance"]) - set(figures) - set(STAND_INS) - {"width"}
    assert not stated, f"provenance for a figure the rack does not state: {stated}"


def test_the_12u_width_is_a_stand_in_because_the_sheet_prints_none():
    doc = rack("startech/4postrack12a")
    assert doc["width"] == 19
    assert doc["provenance"]["width"]["confidence"] == "estimated"
    assert "stand-in" in doc["provenance"]["width"]["note"].lower()
    assert gaps("startech/4postrack12a")["width"]["reason"] == "vendor-silent"


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_sources_are_public_and_name_the_makers_own_pages(key):
    doc = rack(key)
    assert doc["datasheet"]["url"] == SOURCES[key]
    assert doc["datasheet"]["title"].strip()
    for r in doc.get("references", []) + [doc["datasheet"]]:
        assert r.get("url", "https://").startswith("https://"), r
        assert "sha256" not in r, "a hash is for a copy the project holds"
    text = (LIB / "racks" / key / "rack.yaml").read_text()
    for private in ("okf", "/volumes", "/home/", "/data/"):
        assert private not in text.lower(), private


def test_the_42u_source_is_a_dated_web_page_and_not_a_data_sheet():
    doc = rack("startech/4postrack42")
    assert "2026-11-05" in doc["datasheet"]["title"]
    assert "data sheet" not in doc["datasheet"]["title"].lower()


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_casters_are_in_the_description_and_a_gap_asks_for_a_base(key):
    doc = rack(key)
    assert "caster" in doc["description"].lower() and "black" in doc["description"].lower()
    assert "base" in gaps(key)["casters"]["note"].lower()
    assert "base" in gaps(key)["casters"]["wanted"].lower()
    assert "base" not in doc and "casters" not in doc


def test_the_42u_names_its_feet_and_floor_anchoring_base_plate():
    text = (rack("startech/4postrack42")["description"] + json.dumps(gaps("startech/4postrack42"))).lower()
    assert "leveling feet" in text and "floor-anchoring" in text


def test_the_12u_says_its_two_equal_lengths_and_the_axes_it_read():
    g = gaps("startech/4postrack12a")
    assert g["outer-depth"]["reason"] == "sources-disagree"
    assert "35.9 in" in g["outer-depth"]["note"] and "913" in g["outer-depth"]["note"]
    assert g["outer-height"]["reason"] == "sources-disagree"
    assert "661" in g["outer-height"]["note"] and "657" in g["outer-height"]["note"]
    note = rack("startech/4postrack12a")["provenance"]["outer"]["note"]
    assert "front to back" in note and "586" in note


def test_the_42u_names_its_readings_of_feet_and_of_the_title():
    doc = rack("startech/4postrack42")
    assert "outer" in gaps("startech/4postrack42") or "outer-size" in gaps("startech/4postrack42")
    outer = doc["provenance"]["outer"]["note"]
    assert "15 mm" in outer and "1980" in outer
    rails = doc["provenance"]["rails"]["note"]
    assert "40 in" in rails and "3.3 ft" in rails


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_is_versioned_and_passes_its_rule(key):
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


def test_startech_is_a_registered_maker():
    vendors = load_yaml(ROOT / "spec/schemas/vendors.yaml")["vendors"]
    assert vendors["startech"]["role"] == "hardware" and vendors["startech"]["display"] == "StarTech.com"


# ---- the DCIM export -----------------------------------------------------------

@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rack-export")
    racks_index.build([LIB], tmp / "dist", ROOT / "spec/schemas")
    dcim_export.export_racks(tmp / "dist", tmp / "exports")
    return tmp / "exports"


def doc_at(root, target, model):
    return yaml.safe_load((root / target / "rack-types" / "StarTech.com" / f"{model}.yaml").read_text())


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_netbox_rack_type_carries_the_form_the_box_and_the_static_load(exported, key):
    want = WANT[key]
    nb = doc_at(exported, "netbox", want["model"])
    assert nb["manufacturer"] == "StarTech.com" and nb["form_factor"] == "4-post-frame"
    assert nb["u_height"] == want["ru"] and nb["width"] == 19
    assert nb["outer_width"] == approx(want["outer"]["w"][0], abs=want["outer"]["w"][1])
    assert nb["outer_height"] == approx(want["outer"]["h"][0], abs=want["outer"]["h"][1])
    assert nb["outer_depth"] == approx(want["outer"]["d"][0], abs=want["outer"]["d"][1])
    assert nb["outer_unit"] == "mm" and nb["weight_unit"] == "kg"
    assert nb["weight"] == approx(want["weight-kg"][0], abs=want["weight-kg"][1])
    assert nb["max_weight"] == approx(want["static-kg"][0], abs=want["static-kg"][1])
    assert "holes: square" in nb["comments"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_nautobot_rack_names_the_form_and_the_loads(exported, key):
    want = WANT[key]
    nt = doc_at(exported, "nautobot", want["model"])
    assert nt["type"] == "4-post-frame" and nt["u_height"] == want["ru"]
    assert "static load" in nt["comments"]
    assert ("rolling load" in nt["comments"]) == (want["rolling-kg"] is not None)


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_committed_export_holds_the_product(key):
    model = WANT[key]["model"]
    for target in ("netbox", "nautobot"):
        assert (LIB / "exports" / target / "rack-types" / "StarTech.com" / f"{model}.yaml").exists()

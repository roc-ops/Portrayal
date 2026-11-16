"""The Eaton (Tripp Lite) SRW12US swinging 12U wall cabinet as a rack product.

Every figure is read from the maker's own public pages: the SRW12US
specification sheet, the SRW12US and SRW12USG submittal drawing and the owner's
manual for swinging wall-mounted SmartRack enclosures. Where the drawing prints
a figure in two units the metric print is written and the other is checked to
lie inside its rounding. A figure no page prints is a stand-in, and a stand-in
says so three ways: its provenance confidence is `estimated`, a `gaps` entry
asks for the document that would close it, and the note names what it stands
in for. A wall cabinet states its front rail alone, so the cabinet's four
rails, its door, its swing, its wall fixing and its caster base are in the
description and in `gaps`.
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
KEY = "eaton/srw12us"
MODEL = "SRW12US"

# What the drawing's table prints, in mm and kg, with the half-step of the print it was written from.
WANT = {
    "outer": {"w": (623.07, 0.005), "h": (637, 0.5), "d": (548, 0.5)},   # 25.08 x 24.53 x 21.57 in
    "weight-kg": (27.21, 0.005),                                          # 60 lb. (27.21 kg)
    "static-kg": (90.7, 0.05),                                            # 200 lb. (90.7 kg)
    "usable-depth": (520.7, 0.05),                                        # up to 20.5 in. (520.7 mm)
}
# the sheet's own prints of the same figures, in inches: the disagreement is declared, not hidden
SHEET_IN = {"h": 24.625, "w": 23.5, "d": 21.625}
# EIA-310 figures and the direction no page gives: declared, not read
STAND_INS = ["numbering", "hole-centres", "opening"]


def rack():
    return load_yaml(LIB / "racks" / KEY / "rack.yaml")


def gaps():
    return {g["what"]: g for g in rack().get("gaps") or []}


def test_the_product_is_in_the_library_under_the_maker():
    assert KEY in {libwalk.rack_key(f) for f in libwalk.iter_racks([LIB])}


def test_the_product_matches_its_schema():
    assert list(Draft202012Validator(SCHEMA).iter_errors(rack())) == []


def test_the_product_is_a_12u_wall_cabinet_with_square_holes_for_cage_nuts():
    doc = rack()
    assert doc["kind"] == "rack" and doc["manufacturer"] == "Eaton"
    assert doc["name"] == "srw12us" and doc["model"] == MODEL
    assert doc["form"] == "wall-cabinet" and doc["ru"] == 12 and doc["width"] == 19
    assert doc["maturity"] == "modelled"
    assert doc["holes"]["style"] == "square" and "cage nut" in doc["holes"]["fixing"]
    assert MODEL in doc["part-numbers"]


def test_a_wall_cabinet_lists_the_front_rail_alone():
    doc = rack()
    assert [r["id"] for r in doc["rails"]] == ["front"]


def test_every_printed_figure_is_the_drawings_within_its_print():
    doc = rack()
    for k, (v, tol) in WANT["outer"].items():
        assert doc["outer"][k] == approx(v, abs=tol), ("outer", k)
    assert doc["weight-kg"] == approx(WANT["weight-kg"][0], abs=WANT["weight-kg"][1])
    assert doc["load"]["static-kg"] == approx(WANT["static-kg"][0], abs=WANT["static-kg"][1])
    assert doc["max-device-depth"] == approx(WANT["usable-depth"][0], abs=WANT["usable-depth"][1])


def test_the_usable_depth_is_inside_the_outer_depth():
    doc = rack()
    assert doc["max-device-depth"] < doc["outer"]["d"]


def test_the_stand_ins_are_eia_310_and_the_default_direction():
    doc = rack()
    assert doc["numbering"] == {"direction": "bottom-up", "start": 1}
    assert doc["hole-centres"] == 465.1 and doc["opening"] == 450.85


def test_a_stand_in_is_declared_three_ways():
    doc, g = rack(), gaps()
    for fig in STAND_INS:
        prov = doc["provenance"][fig]
        assert prov["confidence"] == "estimated", fig
        assert "stand-in" in prov["note"].lower(), fig
        assert fig in g, fig


def test_every_other_stated_figure_has_a_sourced_provenance_entry():
    doc = rack()
    figures = ["ru", "form", "width", "holes", "rails", "max-device-depth", "outer",
               "weight-kg", "load"]
    for fig in figures:
        prov = doc["provenance"].get(fig)
        assert prov and prov["note"].strip(), fig
        assert prov["confidence"] in {"datasheet", "drawing"}, fig


def test_the_sheet_and_the_drawing_disagree_on_the_box_and_the_product_says_so():
    """The sheet's inches are not the drawing's table; the gap names both, the drawing is written."""
    doc, g = rack(), gaps()["outer-size"]
    for token in ("24.625", "23.5", "21.625", "25.08", "24.53", "21.57"):
        assert token in g["note"], token
    out = doc["outer"]
    assert out["d"] == approx(SHEET_IN["d"] * 25.4, abs=2), "the depth agrees within 2 mm"


def test_the_drawings_448_for_a_depth_of_21_57_inches_is_noted_and_not_written():
    note = gaps()["outer-size"]["note"]
    assert "448" in note and "21.57" in note


def test_the_four_rails_are_in_the_description_and_the_rail_choice_is_a_gap():
    doc, g = rack(), gaps()
    text = doc["description"].lower()
    assert "four" in text and "rail" in text and "6 mm" in text
    assert "rear-rail" in g
    for token in ("10.42", "3 in"):
        assert token in g["rear-rail"]["note"], token


def test_the_wall_fixing_is_the_keyhole_spacing_and_not_a_fan_spacing():
    doc, g = rack(), gaps()
    text = doc["description"].lower()
    assert "keyhole" in text and "16 in" in text
    note = g["wall-fixing"]["note"]
    for token in ("406.40", "542.60", "28.58", "492.13"):
        assert token in note, token
    assert "key" in g["wall-fixing"]["wanted"].lower()


def test_the_door_the_swing_and_the_cable_entries_are_in_the_description_and_gaps():
    doc, g = rack(), gaps()
    text = doc["description"].lower()
    for word in ("door", "side panel", "hinge", "swing", "fan"):
        assert word in text, word
    assert "enclosure" in g and "swing" in g
    assert "225" in g["swing"]["note"] and "90" in g["swing"]["note"]
    for token in ("9.812", "2.35", "10.63", "2.56"):
        assert token in g["cable-entry"]["note"], token


def test_the_caster_kit_is_a_gap_because_its_documents_are_not_held():
    g = gaps()["casters"]
    assert "SRCASTER" in g["note"]
    assert "SRCASTER" in rack()["description"]


def test_the_hole_size_and_the_tapped_face_are_named_in_gaps():
    assert {"hole-size", "hole-style"} <= set(gaps())


def test_the_sources_are_public_and_name_the_makers_own_pages():
    doc = rack()
    assert doc["datasheet"]["url"] == "https://www.eaton.com/us/en-us/skuPage.SRW12US.pdf"
    assert doc["datasheet"]["title"].strip()
    refs = doc.get("references", [])
    for r in refs + [doc["datasheet"]]:
        assert r.get("url", "https://").startswith("https://"), r
    for r in refs:
        assert len(r.get("sha256", "")) == 64, r
    text = (LIB / "racks" / KEY / "rack.yaml").read_text()
    for private in ("okf", "/volumes", "/home/", "/data/"):
        assert private not in text.lower(), private


def test_the_product_is_versioned_and_passes_its_rule():
    assert (LIB / "racks" / KEY / "rack.lock.json").exists()
    got = []
    real = lint.err
    lint.err = lambda p, rule, msg: got.append((rule, msg))
    try:
        lint.lint_rack(LIB / "racks" / KEY / "rack.yaml", rack(), [str(LIB)])
    finally:
        lint.err = real
    assert got == []
    assert devicelock.check_racks(LIB) == []


# ---- the DCIM export -----------------------------------------------------------

@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rack-export")
    racks_index.build([LIB], tmp / "dist", ROOT / "spec/schemas")
    dcim_export.export_racks(tmp / "dist", tmp / "exports")
    return tmp / "exports"


def doc_at(root, target):
    return yaml.safe_load((root / target / "rack-types" / "Eaton" / f"{MODEL}.yaml").read_text())


def test_the_netbox_rack_type_names_the_wall_form_the_box_and_the_load(exported):
    nb = doc_at(exported, "netbox")
    assert nb["manufacturer"] == "Eaton" and nb["form_factor"] == "wall-cabinet"
    assert nb["u_height"] == 12 and nb["width"] == 19
    for k, name in (("w", "outer_width"), ("h", "outer_height"), ("d", "outer_depth")):
        assert nb[name] == approx(WANT["outer"][k][0], abs=WANT["outer"][k][1])
    assert nb["outer_unit"] == "mm" and nb["weight_unit"] == "kg"
    assert nb["weight"] == approx(WANT["weight-kg"][0], abs=WANT["weight-kg"][1])
    assert nb["max_weight"] == approx(WANT["static-kg"][0], abs=WANT["static-kg"][1])
    assert "holes: square" in nb["comments"]


def test_the_nautobot_rack_names_the_wall_form(exported):
    nt = doc_at(exported, "nautobot")
    assert nt["type"] == "wall-cabinet" and nt["u_height"] == 12
    assert "static load" in nt["comments"]


def test_the_committed_export_holds_the_product():
    for target in ("netbox", "nautobot"):
        assert (LIB / "exports" / target / "rack-types" / "Eaton" / f"{MODEL}.yaml").exists()

"""The StarTech.com 12U hinged open wall frame as a rack product.

Every figure is read from StarTech.com's own RK1219WALLOH specification sheet and
its quick-start guide for the 6U, 8U and 12U models. Where the sheet prints a
figure in two units the finer print is written and the other is checked to lie
inside its rounding. A figure no page prints is a stand-in, and a stand-in says
so three ways: its provenance confidence is `estimated`, a `gaps` entry asks for
the document that would close it, and the note names what it stands in for.
The rack product has no key for a wall fixing, a hinge or a swing, so those are in
the description and in `gaps`, and nothing here is drawn from a picture.
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
KEY = "startech/rk1219walloh"
MODEL = "RK1219WALLOH"

# What the sheet prints, in mm and kg, with the half-step of the print it was written from.
WANT = {
    "usable-depth": (502, 0.5),            # Maximum Mounting Depth 19.8 in [50.2 cm]
    "outer": {"w": (555, 0.5), "h": (647, 0.5), "d": (602, 0.5)},
    "weight-kg": (22.73, 0.05),             # 50.1 lb [22.7 kg]
    "static-kg": (63.37, 0.05),             # 139.7 lb [63.4 kg]
}
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


def test_the_product_is_a_12u_wall_frame_with_square_holes_for_cage_nuts():
    doc = rack()
    assert doc["kind"] == "rack" and doc["manufacturer"] == "StarTech.com"
    assert doc["name"] == "rk1219walloh" and doc["model"] == MODEL
    assert doc["form"] == "wall-frame" and doc["ru"] == 12 and doc["width"] == 19
    assert doc["maturity"] == "modelled"
    assert doc["holes"]["style"] == "square" and "cage nut" in doc["holes"]["fixing"]
    assert "size" not in doc["holes"]
    assert MODEL in doc["part-numbers"]


def test_a_wall_frame_lists_the_front_rail_alone():
    doc = rack()
    assert [r["id"] for r in doc["rails"]] == ["front"]
    assert "depth" not in doc["rails"][0]


def test_every_printed_figure_is_the_sheets_within_its_print():
    doc = rack()
    for k, (v, tol) in WANT["outer"].items():
        assert doc["outer"][k] == approx(v, abs=tol), ("outer", k)
    assert set(doc["outer"]) == {"w", "h", "d"}
    assert doc["weight-kg"] == approx(WANT["weight-kg"][0], abs=WANT["weight-kg"][1])
    assert doc["load"] == {"static-kg": approx(WANT["static-kg"][0], abs=WANT["static-kg"][1])}
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
        assert g[fig]["reason"] in {"vendor-silent", "needs-drawing"}, fig


def test_every_other_stated_figure_has_a_sourced_provenance_entry():
    doc = rack()
    figures = ["ru", "form", "width", "holes", "rails", "max-device-depth", "outer",
               "weight-kg", "load"]
    for fig in figures:
        prov = doc["provenance"].get(fig)
        assert prov and prov["note"].strip(), fig
        assert prov["confidence"] in {"datasheet", "estimated"}, fig
    # the axes of the outer box are a reading, and it is declared as one
    assert doc["provenance"]["outer"]["confidence"] == "datasheet"
    stated = set(doc["provenance"]) - set(figures) - set(STAND_INS)
    assert not stated, f"provenance for a figure the rack does not state: {stated}"


def test_the_axes_of_the_outer_box_are_a_reading_the_product_declares():
    note = rack()["provenance"]["outer"]["note"]
    assert "Product Length" in note and "front to back" in note
    g = gaps()["outer-axes"]
    assert g["reason"] == "needs-drawing" and "Length" in g["note"]


def test_the_wall_fixing_and_the_swing_are_in_the_description_and_a_gap():
    doc, g = rack(), gaps()
    text = doc["description"].lower()
    assert "16 in" in text and "4 anchor" in text.replace("four", "4")
    assert "swing" in text and "hinge" in text and "latch" in text
    assert "wall-fixing" in g and "key" in g["wall-fixing"]["note"].lower()
    assert g["hinge"]["reason"] in {"vendor-silent", "needs-drawing"}
    for key in ("base", "hinge", "wall", "anchors", "swing"):
        assert key not in doc


def test_the_four_posts_are_in_the_description_and_the_rail_choice_is_a_gap():
    doc, g = rack(), gaps()
    text = doc["description"].lower()
    assert "front vertical rails" in text and "rear vertical rails" in text
    assert "rear-rail" in g and "rail" in g["rear-rail"]["note"].lower()


def test_no_hole_size_and_no_rail_step_is_written():
    assert gaps()["hole-size"]["reason"] == "vendor-silent"


def test_the_sources_are_public_and_name_the_makers_own_pages():
    doc = rack()
    assert doc["datasheet"]["url"] == "https://media.startech.com/cms/pdfs/rk1219walloh_datasheet.pdf"
    assert doc["datasheet"]["title"].strip()
    for r in doc.get("references", []) + [doc["datasheet"]]:
        assert r.get("url", "https://").startswith("https://"), r
        assert "sha256" not in r, "a hash is for a copy the project holds"
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
    return yaml.safe_load((root / target / "rack-types" / "StarTech.com" / f"{MODEL}.yaml").read_text())


def test_the_netbox_rack_type_names_the_wall_form_the_box_and_the_load(exported):
    nb = doc_at(exported, "netbox")
    assert nb["manufacturer"] == "StarTech.com" and nb["form_factor"] == "wall-frame"
    assert nb["u_height"] == 12 and nb["width"] == 19
    for k, name in (("w", "outer_width"), ("h", "outer_height"), ("d", "outer_depth")):
        assert nb[name] == approx(WANT["outer"][k][0], abs=WANT["outer"][k][1])
    assert nb["outer_unit"] == "mm" and nb["weight_unit"] == "kg"
    assert nb["weight"] == approx(WANT["weight-kg"][0], abs=WANT["weight-kg"][1])
    assert nb["max_weight"] == approx(WANT["static-kg"][0], abs=WANT["static-kg"][1])
    assert "holes: square" in nb["comments"]


def test_the_nautobot_rack_names_the_wall_form(exported):
    nt = doc_at(exported, "nautobot")
    assert nt["type"] == "wall-frame" and nt["u_height"] == 12
    assert "static load" in nt["comments"]


def test_the_committed_export_holds_the_product():
    for target in ("netbox", "nautobot"):
        assert (LIB / "exports" / target / "rack-types" / "StarTech.com" / f"{MODEL}.yaml").exists()

"""The FS-DR-8U desktop open frame as a rack product (#1117).

Every figure is read from FS's own FS-DR-8U data sheet (pages 1 to 3). Where the
sheet prints a figure in two units the finer print is written and the other is
checked to lie inside its rounding. A figure the sheet does not print is a
stand-in, and a stand-in says so three ways: its provenance confidence is
`estimated`, a `gaps` entry asks for the document that would close it, and the
note names what it stands in for. The rack product has no key for a lean-back
angle or for a base, so both are said in the description and in a `gaps` entry
and are not written as keys.
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

# What the sheet prints, in mm and kg, with the half-step of the print it was written from.
WANT = {
    "fs/fs-dr-8u": {
        "model": "FS-DR-8U", "maker": "FS.com", "ru": 8,
        "outer": {"w": (503, 0.5), "h": (409, 0.5), "d": (296, 0.5)},
        "weight-kg": (1.75, 0.005), "static-kg": (50, 0.01),
        "hole-centres": 465, "opening": 451,
    },
}
SOURCES = {
    "fs/fs-dr-8u": "https://resource.fs.com/mall/resource/fs-dr-8u-desktop-rack-datasheet.pdf",
}
# what neither the sheet nor the rack product has a key for: said, never written as a key
UNKEYED = ["tilt", "base"]


def rack(key):
    return load_yaml(LIB / "racks" / key / "rack.yaml")


def gaps(key):
    return {g["what"]: g for g in rack(key).get("gaps") or []}


def test_the_product_is_in_the_library_under_its_maker():
    keys = {libwalk.rack_key(f) for f in libwalk.iter_racks([LIB])}
    assert set(WANT) <= keys


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_matches_its_schema(key):
    assert list(Draft202012Validator(SCHEMA).iter_errors(rack(key))) == []


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_is_a_two_post_desktop_frame_with_square_holes(key):
    doc, want = rack(key), WANT[key]
    assert doc["kind"] == "rack" and doc["manufacturer"] == want["maker"]
    assert doc["name"] == key.split("/")[1] and doc["model"] == want["model"]
    assert doc["form"] == "desktop-frame" and doc["ru"] == want["ru"] and doc["width"] == 19
    assert doc["maturity"] == "modelled"
    assert doc["holes"]["style"] == "square" and "thread" not in doc["holes"]
    assert [r["id"] for r in doc["rails"]] == ["front"]
    assert want["model"] in doc["part-numbers"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_printed_figure_is_the_sheets_within_its_print(key):
    doc, want = rack(key), WANT[key]
    assert set(doc["outer"]) == {"w", "h", "d"}
    for k, (v, tol) in want["outer"].items():
        assert doc["outer"][k] == approx(v, abs=tol), (key, "outer", k)
    assert doc["load"]["static-kg"] == approx(want["static-kg"][0], abs=want["static-kg"][1])
    assert set(doc["load"]) == {"static-kg"}
    assert doc["weight-kg"] == approx(want["weight-kg"][0], abs=want["weight-kg"][1])


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_hole_lines_are_the_drawings_and_not_stand_ins(key):
    doc, want = rack(key), WANT[key]
    assert doc["hole-centres"] == want["hole-centres"] and doc["opening"] == want["opening"]
    for fig in ("hole-centres", "opening"):
        assert doc["provenance"][fig]["confidence"] == "drawing"
        assert fig not in gaps(key)


@pytest.mark.parametrize("key", sorted(WANT))
def test_numbering_is_the_default_first_label_declared_as_a_stand_in(key):
    doc = rack(key)
    assert doc["numbering"] == {"direction": "bottom-up", "start": 1}
    assert doc["provenance"]["numbering"]["confidence"] == "estimated"
    assert "stand-in" in doc["provenance"]["numbering"]["note"].lower()
    assert gaps(key)["numbering"]["reason"] == "vendor-silent"


@pytest.mark.parametrize("key", sorted(WANT))
def test_no_usable_depth_and_no_hole_size_is_written(key):
    doc = rack(key)
    assert "max-device-depth" not in doc and "size" not in doc["holes"]
    assert "fixing" not in doc["holes"]
    assert gaps(key)["max-device-depth"]["reason"] == "vendor-silent"
    assert gaps(key)["hole-size"]["reason"] == "vendor-silent"


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_lean_back_and_the_base_are_said_and_no_key_is_invented(key):
    doc, g = rack(key), gaps(key)
    for k in UNKEYED:
        assert k not in doc, k
        assert k in g, k
        assert "key" in g[k]["wanted"].lower(), k
    assert "lean back" in doc["description"].lower()


def test_the_sheet_prints_the_angle_and_the_base():
    g = gaps("fs/fs-dr-8u")
    assert "81" in g["tilt"]["note"] and "73.7" in g["base"]["note"]
    assert "296" in g["base"]["note"] and "445.5" in g["base"]["note"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_other_stated_figure_has_a_sourced_provenance_entry(key):
    doc = rack(key)
    figures = ["ru", "form", "width", "holes", "outer", "weight-kg", "load"]
    for fig in figures:
        prov = doc["provenance"].get(fig)
        assert prov and prov["note"].strip(), (key, fig)
        assert prov["confidence"] in {"datasheet", "drawing"}, (key, fig)
    stated = set(doc["provenance"]) - set(figures) - {"numbering", "hole-centres", "opening"}
    assert not stated, f"provenance for a figure the rack does not state: {stated}"


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_sources_are_public_and_name_the_makers_own_document(key):
    doc = rack(key)
    assert doc["datasheet"]["url"] == SOURCES[key]
    assert doc["datasheet"]["title"].strip()
    for r in doc.get("references", []) + [doc["datasheet"]]:
        assert r.get("url", "https://").startswith("https://"), r
        assert "sha256" not in r, "a hash is for a copy the project holds"
    text = (LIB / "racks" / key / "rack.yaml").read_text()
    for private in ("okf", "/volumes", "/home/", "/data/", "intake"):
        assert private not in text.lower(), private


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


# ---- the DCIM export -----------------------------------------------------------

@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rack-export")
    racks_index.build([LIB], tmp / "dist", ROOT / "spec/schemas")
    dcim_export.export_racks(tmp / "dist", tmp / "exports")
    return tmp / "exports"


def doc_at(root, target, key):
    want = WANT[key]
    d = root / target / "rack-types" / dcim_export.manufacturer_dir(want["maker"])
    return yaml.safe_load((d / f"{want['model']}.yaml").read_text())


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_netbox_rack_type_is_a_two_post_frame_said_to_be_a_desktop_rack(exported, key):
    want = WANT[key]
    nb = doc_at(exported, "netbox", key)
    assert nb["form_factor"] == "2-post-frame" and nb["manufacturer"] == want["maker"]
    assert nb["u_height"] == want["ru"] and nb["width"] == 19
    assert nb["outer_width"] == approx(want["outer"]["w"][0], abs=want["outer"]["w"][1])
    assert nb["outer_height"] == approx(want["outer"]["h"][0], abs=want["outer"]["h"][1])
    assert nb["outer_depth"] == approx(want["outer"]["d"][0], abs=want["outer"]["d"][1])
    assert nb["max_weight"] == approx(want["static-kg"][0], abs=want["static-kg"][1])
    assert nb["weight"] == approx(want["weight-kg"][0], abs=want["weight-kg"][1])
    assert "A desktop rack" in nb["comments"] and "holes: square" in nb["comments"]
    assert "hole-centres 465 mm" in nb["comments"] and "stand-in" not in nb["comments"]
    assert "mounting_depth" not in nb


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_nautobot_rack_is_a_two_post_frame_with_its_static_load(exported, key):
    nt = doc_at(exported, "nautobot", key)
    assert nt["type"] == "2-post-frame" and nt["u_height"] == WANT[key]["ru"]
    assert "static load" in nt["comments"] and "A desktop rack" in nt["comments"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_committed_export_holds_the_product(key):
    want = WANT[key]
    for target in ("netbox", "nautobot"):
        d = LIB / "exports" / target / "rack-types" / dcim_export.manufacturer_dir(want["maker"])
        assert (d / f"{want['model']}.yaml").exists()

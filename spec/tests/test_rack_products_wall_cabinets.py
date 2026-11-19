"""The Eaton SRW12U and the two Ubiquiti 450 mm 12U wall cabinets as rack products (#1119).

Every figure is read from the maker's own public pages: the SRW12U data sheet
and product drawing, and the UniFi techspecs page of each Ubiquiti cabinet.
Where a page prints a figure in two units the metric print is written and the
other is checked to lie inside its rounding. A figure no page prints is a
stand-in, and a stand-in says so three ways: its provenance confidence is
`estimated`, a `gaps` entry asks for the document that would close it, and the
note names what it stands in for. A wall cabinet states its front rail alone.
Nothing here is drawn from a picture.
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
    "eaton/srw12u": {
        "maker": "Eaton", "model": "SRW12U", "outer": {"w": (600, 0.5), "h": (637, 0.5), "d": (450, 0.5)},
        "weight-kg": (22.0, 0.05), "static-kg": (90.7, 0.05), "usable": (419, 0.5), "opening": 450.85,
    },
    "ubiquiti/uacc-rack-12u-wall-450-g": {
        "maker": "Ubiquiti", "model": "UACC-Rack-12U-Wall-450-G",
        "outer": {"w": (550, 0.5), "h": (635, 0.5), "d": (450, 0.5)},
        "weight-kg": (19.0, 0.05), "static-kg": (50, 0.5), "usable": (325, 0.5), "opening": None,
    },
    "ubiquiti/uacc-rack-12u-wall-450-p": {
        "maker": "Ubiquiti", "model": "UACC-Rack-12U-Wall-450-P",
        "outer": {"w": (550, 0.5), "h": (635, 0.5), "d": (450, 0.5)},
        "weight-kg": (17.8, 0.05), "static-kg": (50, 0.5), "usable": (325, 0.5), "opening": None,
    },
}
SOURCES = {
    "eaton/srw12u": "https://assets.tripplite.com/product-pdfs/en/srw12u.pdf",
    "ubiquiti/uacc-rack-12u-wall-450-g": "https://techspecs.ui.com/unifi/accessories/uacc-rack-12u-wall-450-g",
    "ubiquiti/uacc-rack-12u-wall-450-p": "https://techspecs.ui.com/unifi/accessories/uacc-rack-12u-wall-450-p",
}


def rack(key):
    return load_yaml(LIB / "racks" / key / "rack.yaml")


def gaps(key):
    return {g["what"]: g for g in rack(key).get("gaps") or []}


def test_the_products_are_in_the_library_under_the_maker():
    keys = {libwalk.rack_key(f) for f in libwalk.iter_racks([LIB])}
    assert set(WANT) <= keys


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_matches_its_schema(key):
    assert list(Draft202012Validator(SCHEMA).iter_errors(rack(key))) == []


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_product_is_a_12u_wall_cabinet_with_a_front_rail_alone(key):
    doc = rack(key)
    assert doc["kind"] == "rack" and doc["manufacturer"] == WANT[key]["maker"]
    assert doc["name"] == key.split("/")[1] and doc["model"] == WANT[key]["model"]
    assert doc["form"] == "wall-cabinet" and doc["ru"] == 12 and doc["width"] == 19
    assert doc["maturity"] == "modelled"
    assert doc["holes"]["style"] == "square"
    assert doc["rails"] == [{"id": "front"}]
    assert WANT[key]["model"] in doc["part-numbers"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_printed_figure_is_the_pages_within_its_print(key):
    doc, want = rack(key), WANT[key]
    for k, (v, tol) in want["outer"].items():
        assert doc["outer"][k] == approx(v, abs=tol), (key, "outer", k)
    assert set(doc["outer"]) == {"w", "h", "d"}
    assert doc["weight-kg"] == approx(want["weight-kg"][0], abs=want["weight-kg"][1])
    assert doc["load"] == {"static-kg": approx(want["static-kg"][0], abs=want["static-kg"][1])}
    assert doc["max-device-depth"] == approx(want["usable"][0], abs=want["usable"][1])


def test_the_two_ubiquiti_cabinets_differ_in_the_weight_and_the_door_alone():
    g, p = rack("ubiquiti/uacc-rack-12u-wall-450-g"), rack("ubiquiti/uacc-rack-12u-wall-450-p")
    assert g["weight-kg"] > p["weight-kg"]
    assert "tempered glass front door" in g["description"] and "perforated front door" in p["description"]
    keep = ("form", "ru", "width", "holes", "hole-centres", "opening", "rails", "max-device-depth", "outer", "load")
    assert {k: g[k] for k in keep} == {k: p[k] for k in keep}


@pytest.mark.parametrize("key", sorted(WANT))
def test_a_stand_in_is_declared_three_ways(key):
    doc, g = rack(key), gaps(key)
    estimated = [k for k, v in doc["provenance"].items() if v["confidence"] == "estimated"]
    assert {"numbering", "hole-centres"} <= set(estimated)
    for fig in estimated:
        assert "stand-in" in doc["provenance"][fig]["note"].lower(), (key, fig)
        assert fig in g and g[fig]["reason"] in {"vendor-silent", "needs-drawing"}, (key, fig)
    # the clear opening is read from the SRW12U's drawing and is a stand-in on the Ubiquiti pages
    assert (doc["provenance"]["opening"]["confidence"] == "drawing") == (WANT[key]["opening"] is not None)
    if WANT[key]["opening"]:
        assert doc["opening"] == WANT[key]["opening"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_every_other_stated_figure_has_a_sourced_provenance_entry(key):
    doc = rack(key)
    for fig in ("ru", "form", "holes", "rails", "max-device-depth", "outer", "weight-kg", "load"):
        prov = doc["provenance"].get(fig)
        assert prov and prov["note"].strip() and prov["confidence"] in {"datasheet", "drawing"}, (key, fig)
    stated = {k for k in doc["provenance"] if k not in doc}
    assert not stated, f"provenance for a figure the rack does not state: {stated}"


@pytest.mark.parametrize("key", sorted(WANT))
def test_what_the_rack_product_cannot_say_is_in_the_description_and_a_gap(key):
    doc, g = rack(key), gaps(key)
    assert "enclosure" in g and "enclosure key" in g["enclosure"]["wanted"]
    assert "rail-depth" in g and g["rail-depth"]["reason"] == "vendor-silent"
    for absent in ("enclosure", "base", "tilt"):
        assert absent not in doc, absent
    assert "door" in doc["description"].lower() and "fan" in doc["description"].lower()


def test_the_srw12u_names_its_sources_disagreeing_and_its_casters_and_wall_plate():
    g = gaps("eaton/srw12u")
    assert g["outer-size"]["reason"] == "sources-disagree"
    assert "17.500" in g["outer-size"]["note"] and "450" in g["outer-size"]["note"]
    assert "base" in g["casters"]["wanted"].lower() and "SRCASTER" in rack("eaton/srw12u")["description"]
    assert "406" in g["wall-fixing"]["note"]
    assert g["hole-style"]["reason"] == "needs-photo"
    assert "12-24" in rack("eaton/srw12u")["provenance"]["holes"]["note"]


def test_the_ubiquiti_mounting_depth_is_in_the_notes_and_not_a_rear_rail():
    for key in ("ubiquiti/uacc-rack-12u-wall-450-g", "ubiquiti/uacc-rack-12u-wall-450-p"):
        text = rack(key)["description"] + gaps(key)["rail-depth"]["note"]
        assert "283" in text and "305" in text and "22 mm" in text
        assert "depth" not in rack(key)["rails"][0]
        assert "325 mm" in rack(key)["provenance"]["max-device-depth"]["note"]


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_sources_are_public_and_name_the_makers_own_pages(key):
    doc = rack(key)
    assert doc["datasheet"]["url"] == SOURCES[key]
    assert doc["datasheet"]["title"].strip()
    for r in doc.get("references", []) + [doc["datasheet"]]:
        assert r.get("url", "https://").startswith("https://"), r
    text = (LIB / "racks" / key / "rack.yaml").read_text()
    for private in ("okf", "/volumes", "/home/", "/data/"):
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


def test_the_makers_are_registered():
    vendors = load_yaml(ROOT / "spec/schemas/vendors.yaml")["vendors"]
    assert vendors["eaton"]["role"] == "hardware" and vendors["ubiquiti"]["role"] == "hardware"


# ---- the DCIM export -----------------------------------------------------------

@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rack-export")
    racks_index.build([LIB], tmp / "dist", ROOT / "spec/schemas")
    dcim_export.export_racks(tmp / "dist", tmp / "exports")
    return tmp / "exports"


def doc_at(root, target, key):
    maker = {"Eaton": "Eaton", "Ubiquiti": "Ubiquiti"}[WANT[key]["maker"]]
    return yaml.safe_load((root / target / "rack-types" / maker / f"{WANT[key]['model']}.yaml").read_text())


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_netbox_rack_type_carries_the_form_the_box_and_the_static_load(exported, key):
    want = WANT[key]
    nb = doc_at(exported, "netbox", key)
    assert nb["manufacturer"] == want["maker"] and nb["form_factor"] == "wall-cabinet"
    assert nb["u_height"] == 12 and nb["width"] == 19
    assert nb["outer_width"] == approx(want["outer"]["w"][0], abs=0.5)
    assert nb["outer_height"] == approx(want["outer"]["h"][0], abs=0.5)
    assert nb["outer_depth"] == approx(want["outer"]["d"][0], abs=0.5)
    assert nb["weight"] == approx(want["weight-kg"][0], abs=want["weight-kg"][1])
    assert nb["max_weight"] == approx(want["static-kg"][0], abs=want["static-kg"][1])


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_nautobot_rack_names_the_form(exported, key):
    nt = doc_at(exported, "nautobot", key)
    assert nt["type"] == "wall-cabinet" and nt["u_height"] == 12


@pytest.mark.parametrize("key", sorted(WANT))
def test_the_committed_export_holds_the_product(key):
    for target in ("netbox", "nautobot"):
        path = LIB / "exports" / target / "rack-types" / WANT[key]["maker"] / f"{WANT[key]['model']}.yaml"
        assert path.exists(), path

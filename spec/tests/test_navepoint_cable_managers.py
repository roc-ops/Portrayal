"""NavePoint's cable managers (roc-ops/Portrayal#1099): three plastic raceways, a brush panel and three
vertical managers.

Every size below is what NavePoint's product pages state, in inches as printed and converted here, so a model
that drifts from its page fails by name. The pages carry no drawing: the plate and cover thickness, the walls
and the brush slot are estimates, which the devices say in their provenance and their gaps.

The checks on the compiled drawings and the catalogue read the build (`library/dist`) and skip without it.
"""
import json
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
MM = 25.4

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# sku -> (rack units, height in, depth in, channel depth in), each from the part's own page
RACEWAYS = {
    "00404167": (1, 1.75, 2.36, 1.85),
    "00404169": (1, 1.75, 4.41, 4.1),
    "00404170": (2, 3.5, 4.41, 4.1),
}
# sku -> (rack units, length in), the length being 1.75 in a rack unit and the page's own record
VERTICALS = {"00407295": (24, 42.0), "00407296": (40, 70.0), "00407297": (44, 77.0)}
BRUSH = "00401654"
ALL = list(RACEWAYS) + [BRUSH] + list(VERTICALS)
FACE_W = 482.6                         # 19 in, ears included: a rack-face part is its ears and what hangs off them
SECTION = 3.72                         # in: the page's width and depth of a vertical manager


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "navepoint" / name / "device.yaml").read_text())


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


# --- the maker ----------------------------------------------------------------------------------

def test_navepoint_is_a_hardware_vendor_that_names_its_source():
    vendors = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    v = vendors["navepoint"]
    assert v["role"] == "hardware" and v["display"] == "NavePoint"
    assert "product pages" in v["source"] and "Infinite Electronics" in v["source"]


def test_exactly_these_seven_parts_are_modelled():
    names = sorted(p.name for p in (LIB / "devices" / "navepoint").iterdir() if p.is_dir())
    assert names == sorted(ALL)


# --- each device's envelope against its page ------------------------------------------------------

@pytest.mark.parametrize("name", RACEWAYS)
def test_a_raceway_is_the_pages_size_and_bolts_to_the_rail_face(name):
    ru, h_in, d_in, ch_in = RACEWAYS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "NavePoint" and doc["model"] == name
    assert c["width"] == FACE_W and close(c["height"], h_in * MM, 0.01) and close(c["depth"], d_in * MM, 0.01)
    assert c["ru"] == ru and c["mount"] == "rack-face" and c["shell"] == "sheet"
    assert doc["views"]["front"]["size"] == {"w": c["width"], "h": c["height"]}


@pytest.mark.parametrize("name", RACEWAYS)
def test_a_raceways_channel_is_the_pages_depth_and_the_cover_closes_it(name):
    """The well the walls stand in, less the cover, is the overall depth: the cover's face is the page's depth."""
    ru, h_in, d_in, ch_in = RACEWAYS[name]
    doc = device_yaml(name)
    place = {p["id"]: p for p in doc["views"]["front"]["components"]["placements"]}
    cover = yaml.safe_load((LIB / "components/navepoint" / f"{name}-cover/v1/contract.yaml").read_text())
    base = yaml.safe_load((LIB / "components/navepoint" / f"{name}-base/v1/contract.yaml").read_text())
    thick = cover["relief"]["features"][0]["out"]
    assert close(place["cover"]["lift"] + thick, doc["chassis"]["depth"] - doc["chassis"]["thickness"], 0.011)
    assert close(base["size"]["d"] + doc["chassis"]["thickness"], d_in * MM, 0.011)
    assert close(d_in * MM - thick - doc["chassis"]["thickness"], ch_in * MM, 0.02), "the channel is the page's depth"
    assert cover["lid"] is True and cover["behaviour"] == "mounts"
    assert "cover-off" in doc["configurations"]
    (duct,) = doc["views"]["front"]["guides"]
    assert duct["kind"] == "duct" and duct["run"] == "x" and duct["confidence"] == "estimated"
    assert "finger-pitch" not in duct, "the page names no fingers"


def test_the_brush_panel_is_the_pages_size_and_its_slot_is_a_declared_pass_through():
    doc = device_yaml(BRUSH)
    c = doc["chassis"]
    assert c["width"] == FACE_W and close(c["height"], 1.75 * MM, 0.01) and close(c["depth"], 0.31 * MM, 0.01)
    assert c["ru"] == 1 and c["mount"] == "rack-face"
    (window,) = [d for d in doc["views"]["front"]["panel"]["decor"] if d.get("pattern") == "brush"]
    (through,) = doc["views"]["front"]["passes"]
    assert through["cover"] == "brush" and through["at"] == window["at"] and through["size"] == window["size"]
    assert doc["provenance"]["brush"]["confidence"] == "estimated", "no page sizes the slot"
    assert any(g["what"] == "brush-slot" for g in doc["gaps"])


@pytest.mark.parametrize("name", VERTICALS)
def test_a_vertical_manager_is_the_pages_length_and_stands_beside_the_rack(name):
    ru, len_in = VERTICALS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert close(c["height"], len_in * MM, 0.01) and close(c["height"], ru * 44.45, 0.01), "the length is rack units of 1.75 in"
    assert close(c["width"], SECTION * MM, 0.01) and close(c["depth"], SECTION * MM, 0.01)
    assert c["ru"] == ru and c["mount"] == "rack-side" and c["shell"] == "sheet"
    assert doc["views"]["front"]["size"] == {"w": c["width"], "h": c["height"]}
    (duct,) = doc["views"]["front"]["guides"]
    assert duct["kind"] == "duct" and duct["run"] == "y"
    assert any(g["what"] == "section" for g in doc["gaps"]), "the 3.72 in width, depth and channel depth leave no wall"


# --- what is estimated is said so ----------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL)
def test_every_device_declares_that_its_figures_come_from_a_page_with_no_drawing(name):
    doc = device_yaml(name)
    method = doc["provenance"]["method"]
    assert method["confidence"] == "estimated"
    assert "NO DRAWING" in method["note"] and "photograph" in method["note"]
    assert any(g["what"] == "weight" for g in doc["gaps"]), "no page states a product weight"
    assert "weight-kg" not in doc["chassis"]
    assert len(doc["datasheet"]["sha256"]) == 64


# --- the build ----------------------------------------------------------------------------------------

@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_build_carries_the_envelope_to_the_rack_catalogue(name):
    doc = device_yaml(name)
    r = rack(name)
    c = doc["chassis"]
    assert (r["ru"], r["shell"], r["mount"]) == (c["ru"], "sheet", c["mount"])
    assert close(r["w"], c["width"]) and close(r["h"], c["height"]) and close(r["d"], c["depth"])

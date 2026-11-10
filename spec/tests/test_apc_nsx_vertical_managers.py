"""APC's vertical cable managers for NetShelter SX cabinets (roc-ops/Portrayal#1097, part of #1091): the AR7722,
a 23U and a 20U length sold as one set for a 600 mm wide 45U cabinet, and the AR7580A, two 20U lengths for a 750 mm
wide 42U cabinet.

Every figure below is what APC's own data sheet or installation sheet prints. What no document dimensions (a
finger's size, the split of the depth between the plate and the well) is estimated in the device and is held here
only to what the model itself declares. The envelope and the sizes of the parts are read from the contracts; the
built drawings are read from `library/dist` and skipped without it, like the other sweeps over compiled drawings.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
RU = 44.45

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# name -> (model, width, height, depth mm, net weight kg, rack units, fingers in a column): the data sheet's
# "Specifications", and the length each sheet's figures show (AR7722: 23U and 20U; AR7580A: two 20U).
PARTS = {
    "ar7722": ("AR7722", 107.0, 1911.0, 45.0, 2.27, 43, 43),
    "ar7580a": ("AR7580A", 97.0, 1778.0, 160.0, 4.09, 40, 40),
}


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "apc" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components" / "apc" / name / "v1" / "contract.yaml").read_text())


def svg(name, view):
    return ET.parse(DIST / f"{name}.base.{view}.svg").getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


@pytest.mark.parametrize("name", list(PARTS))
def test_the_envelope_is_the_size_the_data_sheet_prints(name):
    model, w, h, d, kg, ru, _ = PARTS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "APC" and doc["model"] == model
    assert close(c["width"], w) and close(c["height"], h, 0.5) and close(c["depth"], d)
    assert c["mount"] == "rack-side" and c["height"] > c["width"]
    assert close(c["weight-kg"], kg, 0.0005) and close(doc["attrs"]["physical"]["weight-kg"], kg, 0.0005)
    assert c["ru"] == ru, "the rack units of height the manager spans, as the other rack-side parts state them"


@pytest.mark.parametrize("name", list(PARTS))
def test_the_device_has_every_side_and_a_vertical_duct_at_one_rack_unit_pitch(name):
    doc = device_yaml(name)
    assert set(doc["views"]) == {"front", "rear", "top", "bottom", "left", "right"}
    guides = doc["views"]["front"]["guides"]
    assert len(guides) == 1 and guides[0]["kind"] == "duct" and guides[0]["run"] == "y"
    assert guides[0]["finger-pitch"] == RU and close(guides[0]["finger-gap"], RU - 31.0)
    assert close(guides[0]["size"][1], doc["chassis"]["height"])


def test_the_ar7722_is_the_23u_length_over_the_20u_length_and_they_make_its_1911_mm():
    """The installation sheet (990-5140A) labels the two lengths 20U and 23U; the data sheet's 1911 mm is both."""
    doc = device_yaml("ar7722")
    placed = {p["ref"].split("@")[0]: p for p in doc["views"]["front"]["components"]["placements"]}
    assert set(placed) == {"apc/nsx-vcm-23u", "apc/nsx-vcm-20u"}
    top, low = contract("nsx-vcm-23u"), contract("nsx-vcm-20u")
    assert placed["apc/nsx-vcm-23u"]["at"][1] == 0 and close(placed["apc/nsx-vcm-20u"]["at"][1], top["size"]["h"])
    assert close(top["size"]["h"] + low["size"]["h"], 1911.0, 0.5)
    for c, n in ((top, 23), (low, 20)):
        fingers = [k for k in c["elements"] if k.startswith("f")]
        assert len(fingers) == n and close(c["size"]["h"], n * RU)
        ys = sorted(c["elements"][k]["at"][1] for k in fingers)
        assert all(close(b - a, RU) for a, b in zip(ys, ys[1:])), "a finger to each rack unit"
        assert c["size"]["w"] == 107


def test_the_ar7580a_has_40_fingers_a_side_in_two_20u_lengths_against_a_back_plate():
    doc = device_yaml("ar7580a")
    placements = doc["views"]["front"]["components"]["placements"]
    sections = [p for p in placements if p["ref"] == "apc/nsx-vcm-750-fingers@1"]
    assert len(sections) == 4
    c = contract("nsx-vcm-750-fingers")
    per = len([k for k in c["elements"] if k.startswith("t")])
    assert per * 2 == 40 and close(c["size"]["h"] * 2, 1778.0, 0.5)
    base = contract("nsx-vcm-750-base")
    assert base["size"]["w"] == 97 and base["size"]["h"] == 1778
    assert {p["at"][0] for p in sections} == {5.0, 72.0}


@pytest.mark.heavy
def test_no_part_number_is_drawn_twice():
    """One maker part number is one device: AR7722 and AR7580A are each in the library once, and no component of
    this order shares a name with a part that was already there."""
    for name, (model, *_rest) in PARTS.items():
        found = [p for p in (LIB / "devices").glob("*/*/device.yaml") if yaml.safe_load(p.read_text()).get("model") == model]
        assert [p.parent.name for p in found] == [name]
    for name in ("nsx-vcm-23u", "nsx-vcm-20u", "nsx-vcm-750-base", "nsx-vcm-750-fingers"):
        assert len(list((LIB / "components").glob(f"*/{name}"))) == 1


@needs_dist
@pytest.mark.parametrize("name", list(PARTS))
def test_the_built_front_publishes_the_vertical_duct(name):
    el = by_id(svg(name, "front"))["guide--duct"]
    assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "y"
    assert float(el.get("data-guide-finger-pitch")) == RU
    assert close(float(el.get("height")), PARTS[name][2], 0.5)


@needs_dist
@pytest.mark.parametrize("name", list(PARTS))
def test_every_built_side_is_drawn_at_the_chassis_size(name):
    _, w, h, d, *_ = PARTS[name]
    for view, (vw, vh) in {"front": (w, h), "rear": (w, h), "top": (w, d), "bottom": (w, d), "left": (d, h), "right": (d, h)}.items():
        root = svg(name, view)
        assert root.get("viewBox") is not None
        box = [float(v) for v in root.get("viewBox").split()]
        assert close(box[2] / box[3], vw / vh, 0.02), f"{name} {view}"

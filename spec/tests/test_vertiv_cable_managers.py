"""Vertiv's VRA1000 and VRA1001 horizontal cable organizers with metal D rings (part of roc-ops/Portrayal#1095).

The maker's VR Rack selection guide (publication SL-11367) names each part, its unit height and its colour,
shows one picture of it, and states no dimension. Every figure of the two models is therefore scaled off the
picture or taken from EIA-310 and is estimated, and these tests pin that: the sizes, the four rings and the
three openings the picture shows, and that nothing the guide does not state (a weight, a cable capacity, a
material) is stated.

Most of it reads the library's sources. The tests that read the build (`library/dist`, `library/exports`)
skip without it, like the other sweeps over compiled drawings.
"""
import json
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
EXPORTS = LIB / "exports"

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# name -> (ru, height, ring height, screws a ring, opening width, opening height)
PARTS = {
    "vra1000": (1, 44.45, 36.45, 1, 80.0, 24.0),
    "vra1001": (2, 88.9, 80.9, 2, 100.0, 60.0),
}
WIDTH = 482.6
SHEET = 1.5
REACH = 75.0
RING_X = [40.3, 174.3, 308.3, 442.3]


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "vertiv" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components" / "vertiv" / name / "v1" / "contract.yaml").read_text())


def svg(name, view, config="base"):
    return ET.parse(DIST / f"{name}.{config}.{view}.svg").getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


@pytest.mark.parametrize("name", PARTS)
def test_each_part_cites_the_selection_guide_by_hash(name):
    doc = device_yaml(name)
    assert doc["manufacturer"] == "Vertiv" and doc["model"] == name.upper()
    sheet = doc["datasheet"]
    assert "SL-11367" in sheet["title"] and re.fullmatch(r"[0-9a-f]{64}", sheet["sha256"])


@pytest.mark.parametrize("name", PARTS)
def test_the_plate_is_a_19_inch_panel_of_the_stated_units_and_its_figures_are_estimates(name):
    ru, h, _rh, _s, _w, _sh = PARTS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert (c["width"], c["height"], c["ru"]) == (WIDTH, h, ru)
    assert c["depth"] == REACH + SHEET and c.get("mount") is None and c["full-depth"] is False and c["shell"] == "sheet"
    assert c["ears"]["positions"][0]["at"] == c["depth"] and c["ears"]["positions"][0]["default"]
    for key in ("chassis", "method", "thickness"):
        assert doc["provenance"][key]["confidence"] == "estimated", key
    assert any(g["what"] == "dimensions" for g in doc["gaps"]), "the guide gives no dimension: a gap says so"


@pytest.mark.parametrize("name", PARTS)
def test_four_rings_stand_on_the_plate_each_a_ring_guide_along_it(name):
    _ru, h, rh, screws, _w, _sh = PARTS[name]
    doc = device_yaml(name)
    rings = [p for p in doc["views"]["front"]["components"]["placements"] if p["ref"].endswith("-ring@1")]
    assert len(rings) == 4 and all(p["in"] == "panel" for p in rings)
    centres = [p["at"][0] + 5.0 for p in rings]
    assert [round(x, 1) for x in centres] == RING_X
    assert [round(b - a, 1) for a, b in zip(centres, centres[1:])] == [134.0] * 3
    ring = contract(f"{name}-ring")
    assert ring["size"] == {"w": 10.0, "h": rh}
    assert ring["guide"]["kind"] == "ring" and ring["guide"]["run"] == "x"
    fixings = {k: v for k, v in ring["elements"].items() if k.startswith("screw-")}
    assert len(fixings) == screws
    assert {v["class"] for v in fixings.values()} == {"fastener"}, "a fixing is not a place a lug lands: class screw would be read as one"
    assert set(ring["size-confidence"].values()) == {"estimated"}


@pytest.mark.parametrize("name", PARTS)
def test_every_ring_feature_stands_out_past_its_own_lift(name):
    """`out` is a distance from the plate, not a thickness: a feature lifted `lift` off the plate that stands `out` from it
    needs out above lift, or it is built inside out. The sweep over the compiled drawings reads the build; this reads the source."""
    features = contract(f"{name}-ring")["relief"]["features"]
    for f in features:
        assert f["out"] > float(f.get("lift") or 0), f["node"]
    # the screw heads stand 1.5 proud of the 5 mm foot they sit on
    heads = [f for f in features if f["node"].startswith("screw-")]
    assert len(heads) == PARTS[name][3]
    assert all(f["lift"] == 5 and f["out"] == 6.5 for f in heads)


@pytest.mark.parametrize("name", PARTS)
def test_three_oval_openings_between_the_rings_are_passes_and_open_holes_in_the_plate(name):
    _ru, h, _rh, _s, w, sh = PARTS[name]
    doc = device_yaml(name)
    passes = doc["views"]["rear"]["passes"]
    assert [p["size"] for p in passes] == [[w, sh]] * 3 and {p["cover"] for p in passes} == {"open"}
    mids = [round(p["at"][0] + w / 2.0, 1) for p in passes]
    assert mids == [107.3, 241.3, 375.3], "midway between the rings"
    assert {p["at"][1] for p in passes} == {round((h - sh) / 2.0, 3)}, "on the plate's middle line"
    skin = (LIB / "components" / "vertiv" / f"{name}-panel" / "v1" / "skins" / "default.svg").read_text()
    path = re.search(r'id="floor"[^>]*d="([^"]+)"', skin).group(1)
    assert path.count("Z") == 1 + 3 + 4, "the plate, three openings and four ear slots"


@pytest.mark.parametrize("name", PARTS)
def test_the_ears_are_the_ends_of_the_plate_with_two_slots_each(name):
    _ru, h, _rh, _s, _w, _sh = PARTS[name]
    doc = device_yaml(name)
    decor = {d["id"]: d for d in doc["views"]["rear"]["panel"]["decor"]}
    assert decor["panel-back"]["size"][0] == WIDTH
    slots = [decor[f"ear-hole-{k}"] for k in range(1, 5)]
    assert {tuple(s["size"]) for s in slots} == {(10.0, 6.5)}
    centre = lambda s: (round(s["at"][0] + 5.0, 2), round(s["at"][1] + 3.25, 2))
    left_top, left_bottom, right_top, right_bottom = (centre(s) for s in slots)
    assert right_top[0] - left_top[0] == 465.1, "EIA-310 hole spacing"
    assert (left_top[1], left_bottom[1]) == (6.35, round(h - 6.35, 2)) and left_top[1] == right_top[1]


@pytest.mark.parametrize("name", PARTS)
def test_nothing_the_guide_does_not_state_is_stated(name):
    doc = device_yaml(name)
    attrs = doc.get("attrs") or {}
    physical = attrs.get("physical") or {}
    assert "weight-kg" not in physical and "weight-kg" not in doc["chassis"]
    assert "material" not in physical, "the guide names a colour, not a material"
    assert "cable-capacity" not in (attrs.get("performance") or {})
    whats = {g["what"] for g in doc["gaps"]}
    assert {"weight", "cable-capacity", "ring-opening", "ring-extent"} <= whats


@pytest.mark.parametrize("name", PARTS)
def test_the_ring_opening_is_a_gap_and_no_slit_is_invented(name):
    assert "slit" not in contract(f"{name}-ring")["guide"]


def test_no_fill_is_pure_white_or_pure_black_so_each_face_reads_on_the_light_and_the_dark_stage():
    bad = re.compile(r"""fill\s*[=:]\s*["']?(#f{3}(?:f{3})?|#0{3}(?:0{3})?|white|black)\b""", re.I)
    devices = list((LIB / "devices" / "vertiv").rglob("device.yaml"))
    skins = [p for p in (LIB / "components" / "vertiv").rglob("*.svg") if "vra100" in str(p)]
    assert len(skins) == 4
    for p in devices:
        assert not bad.search(p.read_text()), p
    for p in skins:
        for tag in re.findall(r"<[^>]*>", p.read_text()):
            assert not bad.search(tag) or "fill-opacity" in tag, (p, tag)


@needs_dist
@pytest.mark.parametrize("name", PARTS)
def test_the_catalogue_carries_the_envelope_and_the_four_rings_publish_their_guide(name):
    ru, h, _rh, _s, _w, _sh = PARTS[name]
    r = rack(name)
    assert (r["w"], r["h"], r["ru"], r["shell"]) == (WIDTH, h, ru, "sheet")
    root = by_id(svg(name, "front"))
    for k in range(1, 5):
        e = root[f"guide-{k}"]
        assert e.get("data-guide") == "ring" and e.get("data-guide-run") == "x" and e.get("data-in") == "panel"
    assert sorted(rack(name)["rings"]) == [f"guide-{k}" for k in range(1, 5)]
    assert rack(name)["passes"] == {"rear": [f"pass-through-{k}" for k in range(1, 4)]}


@pytest.mark.parametrize("name", PARTS)
def test_the_dcim_device_types_say_the_rack_units_and_not_full_depth(name):
    doc = device_yaml(name)
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Vertiv" / f"{doc['model']}.yaml"
        assert path.is_file(), f"{path} is missing: run dcim_export.py --device {name}"
        out = yaml.safe_load(path.read_text())
        assert out["manufacturer"] == "Vertiv" and out["model"] == doc["model"]
        assert out["u_height"] == float(doc["chassis"]["ru"]) and out["is_full_depth"] is False

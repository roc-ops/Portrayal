"""Brushes and pass-throughs (docs/cable-managers-design.md sections 2 and 5).

A `brush` decor is a brush strip filling an opening: it paints itself solid and
is never an air aperture. A pass-through (`passes:`) declares that cables can
cross a face there. L129 keeps a pass on its face and off the parts; L130 keeps
a `cover: brush` and the brush drawn over it in step.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

import jsonschema
import pytest
import yaml

from portrayal import lint, render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())

WELL = """format: 1
kind: component
name: well
version: 1.0.0
class: mechanical
description: a plate 30 mm down, with a window
size: {w: 100, h: 40, d: 30}
elements:
  plate: {at: [0.0, 0.0], size: [100, 40], class: bezel}
skins: [default]
"""
POST = """format: 1
kind: component
name: post
version: 1.0.0
class: mechanical
behaviour: mounts
description: a post standing on the plate
size: {w: 10, h: 40}
elements:
  post: {at: [0.0, 0.0], size: [10, 40], class: bezel}
skins: [default]
"""


@pytest.fixture
def lib(tmp_path):
    for name, contract, w, h in (("well", WELL, 100, 40), ("post", POST, 10, 40)):
        d = tmp_path / "components" / "t" / name / "v1"
        (d / "skins").mkdir(parents=True)
        (d / "contract.yaml").write_text(contract)
        node = "plate" if name == "well" else "post"
        (d / "skins" / "default.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
            f'viewBox="0 0 {w} {h}"><rect id="{node}" width="{w}" height="{h}" fill="#222"/></svg>')
    return tmp_path


def good():
    """A plate with a brush window and an open hole, and a post between them."""
    return {"format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
            "manufacturer": "T", "model": "T", "profile": "passive", "description": "a fixture",
            "chassis": {"width": 100.0, "height": 40.0, "depth": 60.0, "ru": 1},
            "groups": {"g": {"term": "Part", "role": "furniture", "index-origin": 1}},
            "views": {"front": {
                "size": {"w": 100.0, "h": 40.0},
                "panel": {"decor": [{"id": "brush", "at": [10, 10], "size": [30, 20],
                                     "pattern": "brush", "bristle": "vertical"}]},
                "components": {"placements": [
                    {"ref": "t/well@1", "id": "plate", "at": [0.0, 0.0], "group": "g",
                     "rel-pos": 1},
                    {"ref": "t/post@1", "id": "post", "at": [45.0, 0.0], "group": "g",
                     "rel-pos": 2, "in": "plate"}]},
                "passes": [
                    {"id": "window", "at": [10, 10], "size": [30, 20], "shape": "obround",
                     "cover": "brush"},
                    {"id": "hole", "at": [65, 10], "size": [25, 20], "cover": "open"}]}}}


def findings(doc, lib, code):
    with lint.collecting() as found:
        lint.lint_device_passes("device.yaml", doc, [str(lib)])
    return [m for m in found.errors + found.warnings if f"[{code}]" in m]


def test_the_good_device_is_valid_and_clean(lib):
    jsonschema.validate(good(), SCHEMA)
    assert not findings(good(), lib, "L129")
    assert not findings(good(), lib, "L130")


def test_L129_a_pass_off_its_face(lib):
    d = good()
    d["views"]["front"]["passes"][1]["at"] = [90, 10]
    assert findings(d, lib, "L129")


def test_L129_a_pass_over_a_part(lib):
    d = good()
    d["views"]["front"]["passes"][1]["at"] = [40, 10]     # across the post
    f = findings(d, lib, "L129")
    assert f and "post" in f[0]


def test_L129_a_pass_only_partly_in_its_well(lib):
    """The plate a window is cut in may hold it - but only whole."""
    d = good()
    d["views"]["front"]["components"]["placements"][0]["at"] = [20.0, 0.0]
    d["views"]["front"]["components"]["placements"][1]["at"] = [65.0, 0.0]
    d["views"]["front"]["passes"] = [d["views"]["front"]["passes"][0]]
    assert findings(d, lib, "L129")


def test_L129_two_passes_one_id(lib):
    d = good()
    d["views"]["front"]["passes"][1]["id"] = "window"
    assert findings(d, lib, "L129")


def test_L130_a_brush_cover_with_no_brush_drawn(lib):
    d = good()
    d["views"]["front"]["panel"]["decor"] = []
    assert findings(d, lib, "L130")


def test_L130_a_brush_that_covers_half_the_opening(lib):
    d = good()
    d["views"]["front"]["panel"]["decor"][0]["size"] = [15, 20]
    assert findings(d, lib, "L130")


def test_L130_a_brush_drawn_over_an_open_pass(lib):
    d = good()
    d["views"]["front"]["passes"][0]["cover"] = "open"
    assert findings(d, lib, "L130")


def test_the_schema_refuses_an_unknown_cover_and_shape():
    for key, bad in (("cover", "flap"), ("shape", "circle")):
        d = good()
        d["views"]["front"]["passes"][0][key] = bad
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(d, SCHEMA)


# --- what the renderer writes -------------------------------------------------

def _front(lib):
    dev = good()
    out = render.render_view(dev, "front", dev["views"]["front"],
                             render.Library([str(lib)]), config={})
    out = out[0] if isinstance(out, tuple) else out
    return ET.fromstring(out) if isinstance(out, (str, bytes)) else out


def test_a_pass_compiles_to_an_invisible_named_outline(lib):
    root = _front(lib)
    ps = {el.get("data-pass"): el for el in root.iter() if el.get("data-class") == "pass"}
    assert set(ps) == {"window", "hole"}
    assert ps["window"].get("data-pass-shape") == "obround"
    assert ps["window"].get("data-pass-cover") == "brush"
    assert ps["hole"].get("data-pass-cover") == "open"
    for el in ps.values():
        assert el.get("fill") == "none" and el.get("stroke") == "none"
    # last on the face, so it covers nothing
    assert list(root)[-1].get("id") in ("--passes",) or any(
        c.get("id") == "--passes" for c in list(root)[-3:])


def test_a_brush_paints_itself_and_is_not_air(lib):
    """Unlike a vent, a brush's tile carries its own ground, so it needs no
    backing rect - and it is never declared an opening for air."""
    root = _front(lib)
    b = next(el for el in root.iter() if el.get("id") == "brush")
    assert b.get("data-kind") == "brush-field" and b.get("data-bristle") == "vertical"
    assert b.get("data-aperture") is None and b.get("data-vent") is None
    tile = next(el for el in root.iter() if el.get("id") == "portrayal-brush-vertical")
    w, h = float(tile.get("width")), float(tile.get("height"))
    ground = list(tile)[0]
    assert (float(ground.get("width")), float(ground.get("height"))) == (w, h)
    assert ground.get("fill") not in (None, "none")


def test_a_horizontal_brush_has_its_own_tile(lib):
    dev = good()
    dev["views"]["front"]["panel"]["decor"][0]["bristle"] = "horizontal"
    out = render.render_view(dev, "front", dev["views"]["front"],
                             render.Library([str(lib)]), config={})
    out = out[0] if isinstance(out, tuple) else out
    root = ET.fromstring(out) if isinstance(out, (str, bytes)) else out
    tile = next(el for el in root.iter() if el.get("id") == "portrayal-brush-horizontal")
    assert float(tile.get("width")) > float(tile.get("height"))


# --- the device that proves it -----------------------------------------------

def test_the_brush_manager_declares_what_it_draws():
    doc = yaml.safe_load((LIB / "devices/fs/cmh-4drb1u/device.yaml").read_text())
    passes = {(v, p["id"]): p for v, vw in doc["views"].items() for p in vw.get("passes") or []}
    covers = sorted(p.get("cover", "open") for p in passes.values())
    # five brush windows in the panel and the brush strip behind them; the two
    # end walls' holes are open
    assert covers.count("brush") == 6 and covers.count("open") == 2
    with lint.collecting() as found:
        lint.lint_device_passes("device.yaml", doc, [str(LIB)])
    assert not [m for m in found.errors + found.warnings if "[L129]" in m or "[L130]" in m]


def _l44(doc, lib):
    with lint.collecting() as found:
        lint.lint_device_decor("device.yaml", "front", doc["views"]["front"], [str(lib)])
    return [m for m in found.warnings if "[L44]" in m]


def test_L44_sees_a_brush_through_its_declared_window(lib):
    """The well's drawing has no relief `shape`, so by its box alone the brush
    behind it is buried; the declared pass is the hole it is seen through."""
    assert not _l44(good(), lib)
    doc = good()
    del doc["views"]["front"]["passes"]
    assert _l44(doc, lib)

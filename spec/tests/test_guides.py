"""Guides: where cables run, declared (docs/cable-managers-design.md, decision 8).

A `ring` is declared once on a component's contract and is on every placement
of it; a `duct` is declared on the device view it runs along. Nothing consumes
either yet. Both compile to attributes on the drawing, so that routing has
something to read, and L131 holds each inside what declares it.
"""
import copy
import json
import pathlib
import xml.etree.ElementTree as ET

import jsonschema
import pytest
import yaml

from portrayal import lint, render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE_SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
RING = LIB / "components/fs/d-ring-snap-in/v1/contract.yaml"
DUCT = {"id": "duct", "kind": "duct", "at": [10, 8], "size": [400, 27], "run": "x",
        "finger-pitch": 33.6, "finger-gap": 16.0}


def _ring():
    return yaml.safe_load(RING.read_text())


def component_findings(doc):
    with lint.collecting() as found:
        lint.lint_component_guide("contract.yaml", doc)
    return [m for m in found.errors + found.warnings if "[L131]" in m]


def device_findings(doc):
    with lint.collecting() as found:
        lint.lint_device_guides("device.yaml", doc)
    return [m for m in found.errors + found.warnings if "[L131]" in m]


def _view(*guides, size=(430.0, 42.0)):
    return {"views": {"front": {"size": {"w": size[0], "h": size[1]}, "guides": list(guides)}}}


# --- L131, the ring ------------------------------------------------------------

def test_the_d_ring_declares_a_ring_its_schema_accepts():
    doc = _ring()
    assert doc["guide"]["kind"] == "ring" and doc["guide"]["run"] == "x"
    jsonschema.validate(doc, COMPONENT_SCHEMA)


def test_L131_passes_the_d_ring_as_drawn():
    assert not component_findings(_ring())


def test_L131_fails_an_opening_wider_than_the_loop():
    """Run along x, so `w` lies down the drawing and is held by size.h (43.6)."""
    doc = _ring()
    doc["guide"]["aperture"]["w"] = 50.0
    assert component_findings(doc)


def test_L131_fails_an_opening_taller_than_the_part_stands():
    """`h` stands out of the face: the ring reaches 41 mm, the top bar's lift
    plus its own diameter, and an opening of 45 cannot be inside it."""
    doc = _ring()
    doc["guide"]["aperture"]["h"] = 45.0
    assert component_findings(doc)


def test_L131_fails_an_opening_out_of_the_face_on_a_flat_part():
    """A part with no relief and no size.d says nothing about the axis the
    opening stands along, so there is nothing to hold it inside."""
    doc = _ring()
    doc.pop("relief")
    assert component_findings(doc)


def test_L131_reads_the_face_axes_for_a_ring_seen_end_on():
    doc = _ring()
    doc["guide"] = {"kind": "ring", "aperture": {"w": 30.0, "h": 40.0}, "run": "z"}
    assert not component_findings(doc)
    doc["guide"]["aperture"]["w"] = 33.0      # size.w is 32.3
    assert component_findings(doc)


# --- L131, the duct ------------------------------------------------------------

def test_a_duct_guide_validates():
    doc = {"format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
           "manufacturer": "T", "model": "T", "profile": "passive",
           "chassis": {"width": 430.0, "height": 42.0, "depth": 87.0, "ru": 1},
           **_view(DUCT)}
    jsonschema.validate(doc, DEVICE_SCHEMA)
    bad = copy.deepcopy(doc)
    bad["views"]["front"]["guides"][0]["kind"] = "ring"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, DEVICE_SCHEMA)


def test_L131_passes_a_duct_inside_its_view():
    assert not device_findings(_view(DUCT))


def test_L131_fails_a_duct_off_its_view():
    assert device_findings(_view({**DUCT, "at": [40, 8]}))
    assert device_findings(_view({**DUCT, "at": [10, 20]}))


def test_L131_fails_fingers_with_no_width():
    assert device_findings(_view({**DUCT, "finger-gap": 33.6}))


def test_L131_fails_a_duct_declared_twice():
    assert device_findings(_view(DUCT, dict(DUCT)))


def test_the_finger_duct_declares_one_that_passes():
    doc = yaml.safe_load((LIB / "devices/fs/cmh-sfd1u/device.yaml").read_text())
    guides = [g for v in doc["views"].values() for g in (v or {}).get("guides") or []]
    assert [g["kind"] for g in guides] == ["duct"]
    assert not device_findings(doc)


# --- what the drawing carries ---------------------------------------------------

def _render(view):
    dev = {"format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
           "manufacturer": "T", "model": "T",
           "chassis": {"width": 430.0, "height": 42.0, "depth": 87.0, "ru": 1},
           "groups": {"rings": {"term": "Ring", "role": "furniture", "index-origin": 1}},
           "views": {"top": view}}
    out = render.render_view(dev, "top", view, render.Library([str(LIB)]), config={})
    out = out[0] if isinstance(out, tuple) else out
    return ET.fromstring(out) if isinstance(out, (str, bytes)) else out


def test_every_placement_of_a_ring_carries_its_guide():
    root = _render({"size": {"w": 430.0, "h": 87.0}, "components": {"placements": [
        {"ref": "fs/d-ring-snap-in@1", "id": f"guide-{n}", "at": [20.0 + 60 * n, 20.0],
         "group": "rings", "rel-pos": n} for n in (1, 2)]}})
    rings = [el for el in root.iter() if el.get("data-ref", "").startswith("fs/d-ring-snap-in@1")]
    assert len(rings) == 2
    for el in rings:
        assert (el.get("data-guide"), el.get("data-guide-run"), el.get("data-guide-aperture")) \
            == ("ring", "x", "32 29.5")


def test_a_duct_compiles_to_an_unpainted_rect():
    root = _render({"size": {"w": 430.0, "h": 87.0}, "guides": [DUCT]})
    r = next(el for el in root.iter() if el.get("id") == "guide--duct")
    assert r.get("data-class") == "guide" and r.get("data-guide") == "duct"
    assert r.get("data-guide-run") == "x"
    assert (r.get("data-guide-finger-pitch"), r.get("data-guide-finger-gap")) == ("33.6", "16")
    assert (r.get("x"), r.get("y"), r.get("width"), r.get("height")) == ("10", "8", "400", "27")
    assert r.get("fill") == "none" and r.get("stroke") == "none"


@pytest.mark.parametrize("guide", [
    {"kind": "ring", "aperture": {"w": 5, "h": 5}},
    {"kind": "ring", "aperture": {"w": "5", "h": 5}, "run": "x"},
    {"kind": "ring", "aperture": [5, 5], "run": "x"},
])
def test_L131_a_malformed_guide_is_the_schemas_to_report_not_a_traceback(guide):
    """lint runs on past a schema error, so the rule must not crash on one."""
    from portrayal import lint
    with lint.collecting():
        lint.lint_component_guide("c.yaml", {"size": {"w": 10, "h": 10, "d": 5}, "guide": guide})

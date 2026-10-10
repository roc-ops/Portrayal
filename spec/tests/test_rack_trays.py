"""Trays: a floor cables lie on (docs/cable-lay-design.md section 2, step 3 of
section 10).

A tray is declared as `tray:` on a component contract, so every placement of
the part carries it, or as `trays:` on a device view. It compiles to unpainted
`data-class="tray"` rects (one per floor rectangle) and `data-class="tie"`
rects (one per tie slot); rack_index.py reads them into rack.json's `trays`,
with the openings of the rings that stand on the floor. A ring states where
its opening is with `depth`, `sill` and `aperture.at`. L138 holds a ring's
opening inside its part and L170 a tray's floor and ties inside theirs.
"""
import copy
import json
import pathlib
import xml.etree.ElementTree as ET

import jsonschema
import pytest
import yaml

from portrayal import lint, rack_index, rack_solids, render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
DEVICE_SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
TRAY = LIB / "components/fs/fhd-cmp5dr-tray/v1/contract.yaml"
RING = LIB / "components/fs/d-ring-snap-in/v1/contract.yaml"
CMP5DR = LIB / "devices/fs/fhd-cmp5dr/device.yaml"
FIXTURE = pathlib.Path(__file__).resolve().parent / "js" / "cable-solids-catalogue.json"
SVG = 'xmlns="http://www.w3.org/2000/svg"'


def _load(p):
    return yaml.safe_load(p.read_text())


def _found(fn, *args, code):
    with lint.collecting() as found:
        fn(*args)
    return ([m for m in found.errors if f"[{code}]" in m], [m for m in found.warnings if f"[{code}]" in m])


# --- the library's tray and ring ------------------------------------------------

def test_the_cmp5dr_tray_states_its_floor_height_ties_and_slack():
    doc = _load(TRAY)
    jsonschema.validate(doc, COMPONENT_SCHEMA)
    t = doc["tray"]
    assert t["height"] == 3.0 and t["lip"] == 0 and t["run"] == "x" and t["slack"] == {"kind": "area"}
    # the strip and the two arms
    assert t["floor"] == [{"at": [0.0, 48.8], "size": [448.4, 61.2]}, {"at": [0.0, 15.4], "size": [10.5, 33.4]},
                          {"at": [437.9, 15.4], "size": [10.5, 33.4]}]
    # the sixteen slots the device's bottom view draws, moved by the placement's 17.3
    assert len(t["ties"]) == 16
    bottom = [d for d in _load(CMP5DR)["views"]["bottom"]["panel"]["decor"] if d.get("kind") == "slot"]
    assert sorted((round(d["at"][0] - 17.3, 2), d["at"][1], *d["size"]) for d in bottom) == \
        sorted((tie["at"][0], tie["at"][1], *tie["size"]) for tie in t["ties"])
    # the height is the 44 mm envelope less the well's 41
    assert 44.0 - doc["size"]["d"] == t["height"]
    assert "tray" in doc["provenance"] and doc["version"] == "1.1.0"


def test_the_snap_in_ring_places_its_opening():
    doc = _load(RING)
    jsonschema.validate(doc, COMPONENT_SCHEMA)
    g = doc["guide"]
    assert (g["depth"], g["sill"], g["aperture"]["at"]) == (6.8, 5.6, [12.75, 5.8])
    # the opening centred across the 43.6 ring, the band 12.75 to 19.55 of the 32.3 seat
    assert g["aperture"]["at"][1] * 2 + g["aperture"]["w"] == pytest.approx(doc["size"]["h"])
    assert g["aperture"]["at"][0] + g["depth"] == pytest.approx(doc["elements"]["top"]["at"][0] + doc["elements"]["top"]["size"][0])
    for k in ("guide-depth", "guide-sill", "guide-aperture-at"):
        assert doc["provenance"][k].startswith("drawing - "), k
    assert doc["version"] == "1.2.0"


def test_the_cmp5dr_takes_a_minor_for_its_tray():
    assert _load(CMP5DR)["version"] == "1.1.0"


# --- the schema -------------------------------------------------------------------

def _tray(**kw):
    t = {"floor": [{"at": [0, 0], "size": [100, 50]}], "height": 3.0, "run": "x"}
    t.update(kw)
    return t


@pytest.mark.parametrize("bad", [
    {"floor": [], "height": 3, "run": "x"},
    {"floor": [{"at": [0, 0], "size": [1, 1]}], "run": "x"},
    _tray(run="z"),
    _tray(lip=-1),
    _tray(slack={"kind": "spool"}),
    _tray(slack={"kind": "area", "diameter": 50}),
    _tray(ties=[{"at": [0, 0]}]),
    _tray(colour="black"),
])
def test_the_schema_refuses_a_malformed_tray(bad):
    doc = copy.deepcopy(_load(TRAY))
    doc["tray"] = bad
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, COMPONENT_SCHEMA)


def test_a_spool_states_where_and_how_wide():
    doc = copy.deepcopy(_load(TRAY))
    doc["tray"]["slack"] = {"kind": "spool", "at": [100, 80], "diameter": 60}
    jsonschema.validate(doc, COMPONENT_SCHEMA)


@pytest.mark.parametrize("bad", [{"depth": 0}, {"sill": -1}, {"aperture": {"w": 32, "h": 29.5, "at": [1]}}])
def test_the_schema_refuses_a_malformed_ring_placement(bad):
    doc = copy.deepcopy(_load(RING))
    doc["guide"].update(bad)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, COMPONENT_SCHEMA)


def _device(view):
    return {"format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
            "manufacturer": "T", "model": "T", "profile": "passive",
            "chassis": {"width": 430.0, "height": 44.0, "depth": 300.0, "ru": 1},
            "views": {"front": {"size": {"w": 430.0, "h": 44.0}, "empty": "a test device, its face drawn nowhere, only its plan read"},
                      "top": view}}


def test_a_view_declares_trays_by_id():
    doc = _device({"size": {"w": 430.0, "h": 300.0}, "trays": [{"id": "drawer", **_tray(ties=[{"at": [10, 10], "size": [3, 20]}])}]})
    jsonschema.validate(doc, DEVICE_SCHEMA)
    bad = copy.deepcopy(doc)
    del bad["views"]["top"]["trays"][0]["id"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, DEVICE_SCHEMA)


# --- L138: where the ring's opening is ---------------------------------------------

def _l138(doc):
    return _found(lint.lint_component_guide, "c.yaml", doc, code="L138")[0]


def test_L138_passes_the_snap_in_ring_as_stated():
    assert not _l138(_load(RING))


@pytest.mark.parametrize("change", [
    {"depth": 33.0},                                   # longer than the 32.3 seat it crosses
    {"sill": 12.0},                                    # 12 + 29.5 stands past the ring's 41
    {"aperture": {"w": 32.0, "h": 29.5, "at": [12.75, 12.0]}},   # 12 + 32 runs off the 43.6
    {"aperture": {"w": 32.0, "h": 29.5, "at": [26.0, 5.8]}},     # 26 + 6.8 runs off the 32.3
    {"aperture": {"w": 32.0, "h": 29.5, "at": [-1.0, 5.8]}},
])
def test_L138_fails_an_opening_placed_off_the_part(change):
    doc = copy.deepcopy(_load(RING))
    doc["guide"].update(change)
    assert _l138(doc)


def test_L138_a_sill_is_for_a_ring_whose_run_lies_in_the_face():
    doc = copy.deepcopy(_load(RING))
    doc["guide"] = {"kind": "ring", "aperture": {"w": 20.0, "h": 20.0}, "run": "z", "sill": 2.0}
    assert _l138(doc)
    del doc["guide"]["sill"]
    assert not _l138(doc)


# --- L170: the tray ---------------------------------------------------------------

def _l170_component(doc):
    return _found(lint.lint_component_tray, "c.yaml", doc, code="L170")[0]


def test_L170_passes_the_cmp5dr_tray():
    assert not _l170_component(_load(TRAY))


def test_L170_fails_a_floor_off_its_part_and_a_tie_off_its_floor():
    doc = copy.deepcopy(_load(TRAY))
    doc["tray"]["floor"][0]["size"] = [448.4, 70.0]          # 48.8 + 70 runs past the 110
    assert _l170_component(doc)
    doc = copy.deepcopy(_load(TRAY))
    doc["tray"]["ties"][0]["at"] = [54.85, 40.0]             # in the gap behind the strip
    assert _l170_component(doc)


def _l170_device(doc):
    return _found(lint.lint_device_trays, "device.yaml", doc, [LIB], code="L170")


def test_L170_passes_the_cmp5dr():
    assert _l170_device(_load(CMP5DR)) == ([], [])


def test_L170_an_id_names_one_pathway():
    doc = copy.deepcopy(_load(CMP5DR))
    # a view's own tray named as one of the rings
    doc["views"]["top"]["trays"] = [{"id": "guide-2", **_tray()}]
    errs, _ = _l170_device(doc)
    assert any("guide-2" in e for e in errs)
    # and a placement whose part carries a tray named as a view's tray
    doc["views"]["top"]["trays"] = [{"id": "tray", **_tray()}]
    errs, _ = _l170_device(doc)
    assert any("'tray'" in e or "top/tray" in e for e in errs)


def test_L170_a_view_tray_off_its_view_and_a_tie_off_its_floor():
    doc = _device({"size": {"w": 430.0, "h": 300.0}, "trays": [{"id": "d", **_tray(floor=[{"at": [400, 0], "size": [100, 50]}])}]})
    assert _l170_device(doc)[0]
    doc = _device({"size": {"w": 430.0, "h": 300.0}, "trays": [{"id": "d", **_tray(ties=[{"at": [200, 200], "size": [3, 20]}])}]})
    assert _l170_device(doc)[0]


def test_L170_warns_a_height_the_well_does_not_give():
    doc = copy.deepcopy(_load(CMP5DR))
    doc["chassis"]["height"] = 45.0
    _, warns = _l170_device(doc)
    assert any("puts its floor at 4" in w for w in warns)


def test_L170_warns_a_slot_drawn_and_not_declared_and_one_declared_and_not_drawn():
    doc = copy.deepcopy(_load(CMP5DR))
    decor = doc["views"]["bottom"]["panel"]["decor"]
    decor[:] = [d for d in decor if d["id"] != "slot-2a"]
    _, warns = _l170_device(doc)
    assert any("does not draw" in w for w in warns)
    doc = copy.deepcopy(_load(CMP5DR))
    doc["views"]["bottom"]["panel"]["decor"].append(
        {"id": "slot-x", "at": [230.0, 60.0], "size": [3, 10], "fill": "#0a0b0c", "kind": "slot"})
    _, warns = _l170_device(doc)
    assert any("slot-x" in w for w in warns)


# --- what the drawing carries ----------------------------------------------------

def _render(view, chassis=None):
    dev = {"format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
           "manufacturer": "T", "model": "T",
           "chassis": chassis or {"width": 483.0, "height": 44.0, "depth": 110.0, "ru": 1},
           "groups": {"tray": {"term": "Tray", "role": "furniture", "index-origin": 1}},
           "views": {"top": view}}
    out = render.render_view(dev, "top", view, render.Library([str(LIB)]), config={})
    out = out[0] if isinstance(out, tuple) else out
    return ET.fromstring(out) if isinstance(out, (str, bytes)) else out


def test_a_parts_tray_compiles_under_its_instance_unpainted_and_inert():
    root = _render({"size": {"w": 483.0, "h": 110.0}, "components": {"placements": [
        {"ref": "fs/fhd-cmp5dr-tray@1", "id": "tray", "at": [17.3, 0.0], "group": "tray", "rel-pos": 1}]}})
    inst = next(el for el in root.iter() if el.get("id") == "tray" and el.get("data-ref"))
    floors = [el for el in inst if el.get("data-class") == "tray"]
    ties = [el for el in inst if el.get("data-class") == "tie"]
    assert len(floors) == 3 and len(ties) == 16
    assert all(el.get("data-tray") == "tray" for el in floors + ties)
    f = floors[0]
    assert (f.get("x"), f.get("y"), f.get("width"), f.get("height")) == ("0", "48.8", "448.4", "61.2")
    assert (f.get("data-tray-height"), f.get("data-tray-lip"), f.get("data-tray-run"), f.get("data-tray-slack")) == ("3", "0", "x", "area")
    # nothing the 3D build, the elements file or the face tree reads
    for el in floors + ties:
        assert el.get("fill") == "none" and el.get("stroke") == "none" and el.get("pointer-events") == "none"
        assert not any(k.startswith("data-z-") for k in el.attrib)
        assert el.get("id") is None and el.get("data-path") is None and el.get("data-ref") is None


def test_a_rings_opening_reaches_the_drawing():
    root = _render({"size": {"w": 430.0, "h": 87.0}, "components": {"placements": [
        {"ref": "fs/d-ring-snap-in@1", "id": "guide-1", "at": [20.0, 20.0], "group": "tray", "rel-pos": 1}]}})
    el = next(el for el in root.iter() if el.get("id") == "guide-1")
    assert (el.get("data-guide-depth"), el.get("data-guide-sill"), el.get("data-guide-aperture-at")) == ("6.8", "5.6", "12.75 5.8")


def test_a_views_trays_compile_at_the_root():
    root = _render({"size": {"w": 430.0, "h": 300.0},
                    "trays": [{"id": "drawer", **_tray(ties=[{"at": [10, 10], "size": [3, 20]}], slack={"kind": "spool", "at": [50, 25], "diameter": 40})}]})
    g = next(el for el in root.iter() if el.get("data-class") == "trays")
    (f,), (t,) = [el for el in g if el.get("data-class") == "tray"], [el for el in g if el.get("data-class") == "tie"]
    assert f.get("data-tray") == "drawer" and t.get("data-tray") == "drawer"
    assert f.get("data-tray-slack") == "spool 50 25 40"


# --- rack.json -------------------------------------------------------------------

def test_trays_read_a_compiled_plan_into_the_device_frame():
    top = f'''<svg {SVG}>
      <g id="tray" data-ref="t@1" data-depth="41" transform="translate(17.3,0)">
        <rect data-class="tray" data-tray="tray" data-tray-height="3" data-tray-lip="0" data-tray-run="x"
              data-tray-slack="area" x="0" y="48.8" width="448.4" height="61.2"/>
        <rect data-class="tie" data-tray="tray" x="54.85" y="95" width="22.5" height="3"/></g>
      <g id="guide-1" data-ref="r@1" data-guide="ring" data-guide-run="x" data-guide-aperture="32 29.5"
         data-guide-depth="6.8" data-guide-sill="5.6" data-guide-aperture-at="12.75 5.8" data-z-lift="-41"
         transform="translate(19.55,66.4)"/></svg>'''
    out = rack_solids.trays({"top": ET.fromstring(top)}, {"w": 483, "h": 44, "d": 110, "shell": "sheet", "thickness": 1.5})
    assert out == [{"id": "tray", "top": 3.0, "thickness": 1.5, "lip": 0.0, "run": "x", "slack": {"kind": "area"},
                    "floor": [{"x": 17.3, "y": 1.5, "z": 0.0, "w": 448.4, "h": 1.5, "d": 61.2}],
                    "ties": [{"x": 72.15, "y": 1.5, "z": 12.0, "w": 22.5, "h": 1.5, "d": 3.0}],
                    "rings": [{"via": "guide-1", "run": "x",
                               "box": {"x": 32.3, "y": 8.6, "z": 5.8, "w": 6.8, "h": 29.5, "d": 32.0}}]}]


def test_a_ring_not_on_the_floor_is_not_the_trays():
    top = f'''<svg {SVG}>
      <g data-ref="t@1"><rect data-class="tray" data-tray="tray" data-tray-height="3" data-tray-run="x"
              x="0" y="48.8" width="100" height="61.2"/></g>
      <g id="guide-1" data-guide="ring" data-guide-run="x" data-guide-aperture="32 29.5" data-guide-depth="6.8"
         data-guide-sill="5.6" data-guide-aperture-at="12.75 5.8" data-z-lift="-20" transform="translate(19.55,66.4)"/>
      <g id="guide-2" data-guide="ring" data-guide-run="x" data-guide-aperture="32 29.5"
         data-z-lift="-41" transform="translate(40,66.4)"/></svg>'''
    (t,) = rack_solids.trays({"top": ET.fromstring(top)}, {"w": 483, "h": 44, "d": 110})
    # guide-1 stands 24 up, not on the 3 mm floor; guide-2 does not place its opening
    assert "rings" not in t and "ties" not in t and "slack" not in t
    assert t["thickness"] == rack_solids.DEFAULT_T


def test_a_device_without_a_tray_carries_none(tmp_path):
    (tmp_path / "devices.json").write_text(json.dumps({"devices": [{"name": "sw", "manufacturer": "X", "model": "SW"}]}))
    (tmp_path / "sw.configs.json").write_text(json.dumps({"chassis": {"w": 440, "h": 44, "d": 300}, "default": "base",
                                                          "configs": [{"name": "base"}], "attrs": {}}))
    assert "trays" not in rack_index.build(tmp_path)["devices"]["sw"]


def test_the_build_carries_the_cmp5dr_tray_and_the_kit_fixture_is_its_copy():
    rack = DIST / "rack.json"
    assert rack.is_file(), "no library/dist/rack.json: run ./build.sh first (the suite reads the build)"
    devices = json.loads(rack.read_text())["devices"]
    built = devices.get("fhd-cmp5dr")
    assert built is not None, "fhd-cmp5dr is not in library/dist/rack.json: run ./build.sh"
    (t,) = built["trays"]
    assert t["id"] == "tray" and t["top"] == 3.0 and t["thickness"] == 1.5 and t["run"] == "x"
    assert len(t["floor"]) == 3 and len(t["ties"]) == 16 and [r["via"] for r in t["rings"]] == [f"guide-{n}" for n in range(1, 6)]
    # the strapped width of the slot pairs that hold a cable along the tray: 89.7 to 98 from the rail
    across = [s for s in t["ties"] if s["w"] > s["d"]]
    assert round(110 - max(s["z"] + s["d"] for s in across), 2) == 89.7 and round(110 - min(s["z"] for s in across), 2) == 98.0
    # each ring's opening on its sill, 5.6 above the 3 mm floor
    assert {(r["box"]["y"], r["box"]["h"]) for r in t["rings"]} == {(8.6, 29.5)}
    assert json.loads(FIXTURE.read_text())["devices"]["fhd-cmp5dr"]["trays"] == built["trays"]
    # and only parts that declare a tray carry one
    assert [n for n, e in devices.items() if e.get("trays")] == ["fhd-cmp5dr"] or len(devices) < 50


def test_the_elements_file_does_not_see_a_tray():
    p = DIST / "fhd-cmp5dr.base.top.elements.json"
    assert p.is_file(), "run ./build.sh first"
    rows = json.loads(p.read_text())["elements"]
    tray = next(r for r in rows if r["id"] == "tray")
    # the part's own box, as before the tray was declared
    assert tray["box"] == {"x": 17.3, "y": 15.4, "w": 448.4, "h": 94.6}
    assert not [r for r in rows if r.get("class") in ("tray", "tie")]


# --- the kit's fallback tables follow the cable types table ------------------------

def test_restings_family_and_bend_tables_are_the_cable_types_tables():
    """kit/rack/resting.js keeps a media's family and installed bend radius for
    a page that gives no cable types lookup; each is the yaml's figure for the
    bare type of that id (`power`, which no bare type names, its power-c13)."""
    import re
    src = (ROOT / "kit/rack/resting.js").read_text()

    def table(name):
        body = re.search(r"export const " + name + r" = \{(.*?)\};", src, re.S).group(1)
        return {k: v.strip("'") for k, v in re.findall(r"(\w+): ('?[\w.]+'?)", body)}
    family, bend = table("FAMILY"), table("BEND")
    types = yaml.safe_load((ROOT / "spec/schemas/cable-types.yaml").read_text())["types"]

    def radius(t):
        r = t["min_bend_radius"]["installed"]
        return round(r["mm"] if "mm" in r else r["xOD"] * t["od_mm"], 2)
    assert set(family) == set(bend) and len(family) >= 9
    for media in family:
        t = types[media if media in types else "power-c13"]
        assert t["media"] == media, media
        assert family[media] == t["family"], media
        assert float(bend[media]) == radius(t), media


def test_trays_are_declared_on_the_plan_only():
    doc = _device({"size": {"w": 430.0, "h": 300.0}})
    doc["views"]["front"]["trays"] = [{"id": "d", **_tray()}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, DEVICE_SCHEMA)
    assert any("plan" in e for e in _l170_device(doc)[0])
    # a part that carries a tray, placed off the plan
    dev = copy.deepcopy(_load(CMP5DR))
    dev["views"]["front"].setdefault("components", {"placements": []})["placements"].append(
        {"ref": "fs/fhd-cmp5dr-tray@1", "id": "tray-2", "at": [0, 0], "group": "tray", "rel-pos": 9})
    assert any("tray-2" in e and "top view only" in e for e in _l170_device(dev)[0])

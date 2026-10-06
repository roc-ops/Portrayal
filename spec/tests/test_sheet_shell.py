"""A body that is bent sheet metal, not a box (docs/cable-managers-design.md s4).

Every device was a solid box in 3D: the viewer builds one from the chassis and
paints a view on each side. A lacer panel in front of a patch panel is a floor,
two ears and open air, and as a box it hides the ports it is there to serve.
`chassis.shell: sheet` says the painted metal of each view is a plate and the
rest is nothing.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

import pytest

from portrayal import devicelock, lint, render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())


def findings(doc):
    with lint.collecting() as found:
        lint.lint_device_shell("device.yaml", doc)
    return [m for m in found.errors + found.warnings if "[L127]" in m]


def test_the_schema_knows_the_two_keys():
    ch = SCHEMA["properties"]["chassis"]["properties"]
    assert ch["shell"]["enum"] == ["sheet"]
    assert ch["thickness"]["type"] == "number"


def test_L127_a_sheet_states_its_thickness():
    assert findings({"chassis": {"shell": "sheet"}})
    assert not findings({"chassis": {"shell": "sheet", "thickness": 1.5}})


def test_L127_a_box_has_no_sheet_thickness():
    assert findings({"chassis": {"thickness": 1.5}})
    assert not findings({"chassis": {"width": 440}})


@pytest.mark.parametrize("t", [0, -1, 12.5])
def test_L127_a_thickness_is_a_sheet_gauge(t):
    """0 and negatives are nonsense; over 10 mm is not sheet metal, it is a typo
    for a depth."""
    assert findings({"chassis": {"shell": "sheet", "thickness": t}})


def test_the_shell_is_shape_to_the_lock_and_its_gauge_is_not():
    """`shell` decides whether the envelope is solid, so adopting it is a major.
    `thickness` is a stated gauge nothing is built from, like the weight."""
    assert "shell" in devicelock.CHASSIS_SHAPE
    assert "thickness" in devicelock.CHASSIS_SURFACE


# --- what the renderer hands the viewer ---------------------------------------

def _device(shell):
    ch = {"width": 483.0, "height": 44.0, "depth": 109.0, "ru": 1, "mount": "rack-face"}
    if shell:
        ch.update(shell="sheet", thickness=1.5)
    return {"format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
            "manufacturer": "T", "model": "T", "chassis": ch,
            "views": {"front": {"panel": {"decor": [
                {"at": [0, 0], "size": [9, 44], "fill": "#1b1d20"}]}}}}


def _front(shell):
    """The entry point test_open_frame.py renders one in-memory view through."""
    dev = _device(shell)
    out = render.render_view(dev, "front", dev["views"]["front"],
                             render.Library([str(LIB)]), config={})
    out = out[0] if isinstance(out, tuple) else out
    root = ET.fromstring(out) if isinstance(out, (str, bytes)) else out
    plate = next(el for el in root.iter() if el.get("id") == "chassis-faceplate")
    return root, plate, ET.tostring(root, encoding="unicode")


def test_a_sheet_face_does_not_paint_the_envelope():
    root, plate, _ = _front(True)
    assert root.get("data-shell") == "sheet"
    assert plate.get("fill") == "none" and plate.get("stroke") is None


def test_a_box_face_still_paints_its_housing():
    root, plate, _ = _front(False)
    assert root.get("data-shell") is None
    assert plate.get("fill") not in (None, "none") and plate.get("stroke")


def test_a_sheet_face_still_draws_its_metal():
    """The ear plate in the fixture survives: a sheet face is not an empty one."""
    assert "#1b1d20" in _front(True)[2]


# --- a sloped plate standing on a well's floor -------------------------------

def test_a_profile_in_a_well_is_measured_from_the_wells_floor():
    """`in:` sinks a part's `out` to the floor of the well it stands in, and left
    its `profile` where it was - measured from the face the well is cut in. So a
    web sloping from 42 mm to nothing, standing on a tray 42 mm down, was a
    surface from 42 ABOVE the lid to the lid, on a skirt 84 mm tall. The profile
    is a height like `out` is, and moves with it."""
    dev = {"format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
           "manufacturer": "T", "model": "T",
           "chassis": {"width": 483.0, "height": 44.0, "depth": 110.0, "ru": 1,
                       "mount": "rack-face", "shell": "sheet", "thickness": 1.5},
           "groups": {"tray": {"term": "Tray", "role": "furniture", "index-origin": 1}},
           "views": {"top": {"size": {"w": 483.0, "h": 110.0}, "components": {"placements": [
               {"ref": "fs/fhd-cmp5dr-tray@1", "id": "tray", "at": [17.3, 0.0],
                "group": "tray", "rel-pos": 1},
               {"ref": "fs/fhd-cmp5dr-web@1", "id": "web", "at": [17.3, 0.0],
                "group": "tray", "rel-pos": 2, "in": "tray"}]}}}}
    out = render.render_view(dev, "top", dev["views"]["top"], render.Library([str(LIB)]), config={})
    out = out[0] if isinstance(out, tuple) else out
    root = ET.fromstring(out) if isinstance(out, (str, bytes)) else out
    plate = next(el for el in root.iter() if el.get("id") == "web--plate")
    pairs = [tuple(map(float, p.split(":"))) for p in plate.get("data-z-profile-y").split(",")]
    assert pairs[0] == (0.0, 0.0)            # 42 high on a floor 42 down: level with the lid
    assert pairs[-1][1] == pytest.approx(-40.5)   # 1.5 above that floor
    assert float(plate.get("data-z-out")) == 0.0

"""A body that is bent sheet metal, not a box (docs/cable-managers-design.md s4).

Every device was a solid box in 3D: the viewer builds one from the chassis and
paints a view on each side. A lacer panel in front of a patch panel is a floor,
two ears and open air, and as a box it hides the ports it is there to serve.
`chassis.shell: sheet` says the views are elevations with no housing behind
them, and that the solid is what their parts build.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

import pytest

from portrayal import lint, render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())


def findings(doc):
    with lint.collecting() as found:
        lint.lint_device_shell("device.yaml", doc)
    return [m for m in found.errors + found.warnings if "[L127]" in m]


def test_L127_a_sheet_states_its_thickness():
    assert findings({"chassis": {"shell": "sheet"}})
    assert not findings({"chassis": {"shell": "sheet", "thickness": 1.5}})


def test_L127_a_box_has_no_sheet_thickness():
    assert findings({"chassis": {"thickness": 1.5}})
    assert not findings({"chassis": {"width": 440}})


@pytest.mark.parametrize("t", [0, -1, 12.5, "1.5", True, [1.5]])
def test_L127_a_thickness_is_a_sheet_gauge(t):
    """0 and negatives are nonsense; over 10 mm is not sheet metal, it is a typo
    for a depth. Something that is not a number is a finding too, and not a
    traceback, on a file the schema has yet to refuse."""
    assert findings({"chassis": {"shell": "sheet", "thickness": t}})


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

WELL = """format: 1
kind: component
name: well
version: 1.0.0
class: mechanical
description: a floor 30 mm down
size: {w: 100, h: 60, d: 30}
elements:
  floor: {at: [0.0, 0.0], size: [100, 60], class: bezel}
skins: [default]
"""
PLATE = """format: 1
kind: component
name: plate
version: 1.0.0
class: mechanical
behaviour: mounts
description: a plate whose top edge falls from 20 mm to 5
size: {w: 2, h: 40}
elements:
  plate: {at: [0.0, 0.0], size: [2, 40], class: bezel}
relief:
  features:
    - {node: plate, out: 20.0, profile-y: [[0, 20], [40, 5]], confidence: estimated, source: a fixture}
skins: [default]
"""


@pytest.fixture
def well_library(tmp_path):
    for name, contract, w, h in (("well", WELL, 100, 60), ("plate", PLATE, 2, 40)):
        d = tmp_path / "components" / "t" / name / "v1"
        (d / "skins").mkdir(parents=True)
        (d / "contract.yaml").write_text(contract)
        node = "floor" if name == "well" else "plate"
        (d / "skins" / "default.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
            f'viewBox="0 0 {w} {h}"><rect id="{node}" width="{w}" height="{h}" fill="#222"/></svg>')
    return render.Library([str(tmp_path)])


def test_a_profile_in_a_well_is_measured_from_the_wells_floor(well_library):
    """`in:` sinks a part's `out` to the floor of the well it stands in, and left
    its `profile` where it was - measured from the face the well is cut in. So a
    plate sloping from 20 mm to 5, standing on a floor 30 mm down, was a surface
    from 20 ABOVE the lid, on a skirt 50 mm tall. The profile is a height like
    `out` is, and moves with it."""
    dev = {"format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
           "manufacturer": "T", "model": "T",
           "chassis": {"width": 100.0, "height": 44.0, "depth": 60.0},
           "groups": {"g": {"term": "Part", "role": "furniture", "index-origin": 1}},
           "views": {"top": {"size": {"w": 100.0, "h": 60.0}, "components": {"placements": [
               {"ref": "t/well@1", "id": "well", "at": [0.0, 0.0], "group": "g", "rel-pos": 1},
               {"ref": "t/plate@1", "id": "web", "at": [10.0, 5.0], "group": "g", "rel-pos": 2,
                "in": "well"}]}}}}
    out = render.render_view(dev, "top", dev["views"]["top"], well_library, config={})
    out = out[0] if isinstance(out, tuple) else out
    root = ET.fromstring(out) if isinstance(out, (str, bytes)) else out
    plate = next(el for el in root.iter() if el.get("id") == "web--plate")
    pairs = [tuple(map(float, p.split(":"))) for p in plate.get("data-z-profile-y").split(",")]
    assert pairs == [(0.0, -10.0), (40.0, -25.0)]     # 20 and 5 above a floor 30 down
    assert float(plate.get("data-z-out")) == -10.0

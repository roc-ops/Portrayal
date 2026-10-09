"""Rack devices with parts beyond their ears (#865).

A `rack` device is drawn between its ear folds, or at the rack face where its
ears carry parts, and until #865 nothing could stand outside that. Two keys
make the other cases statements:

- `chassis.overhang: {left, right}` - how far real parts reach beyond the rack
  face. L150 refuses a part outside its face that the side's figure does not
  cover; L151 warns when no part reaches a stated figure. The FS CMH-6DR1U's
  end rings reach 43 mm past each ear.
- `chassis.ears: behind` - the ear folds are behind the body, so a 482.6 mm
  front is the part and not a rack face; L43 stands down. The FS
  USCMH-SFDABSB2U is a duct the width of the rack.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from portrayal import dcim_export as dx
from portrayal import devicelock
from portrayal import lint

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
ROOTS = [str(LIB)]
RING = "fs/cmh-5dr1u-n-ring@1"      # 12.7 x 44, a real part to place


def _codes(doc, code):
    with lint.collecting() as found:
        lint.lint_device_overhang("device.yaml", doc, ROOTS)
    return [m for m in found.errors + found.warnings if f"[{code}]" in m]


def _dev(placements, view="front", w=482.6, h=44.0, **chassis):
    ch = {"width": 430.0, "height": 44.0, "depth": 100.0, "ru": 1, **chassis}
    return {"chassis": ch,
            "views": {view: {"size": {"w": w, "h": h},
                             "components": {"placements": placements}}}}


def _at(x, y=0.0, **kw):
    return {"ref": RING, "id": "p", "at": [x, y], **kw}


# --- L150 --------------------------------------------------------------------

def test_L150_a_part_on_the_face_is_quiet():
    assert not _codes(_dev([_at(0.0), _at(469.9)]), "L150")


def test_L150_a_part_past_the_face_with_no_overhang_is_an_error():
    found = _codes(_dev([_at(-20.0)]), "L150")
    assert found and "states no `chassis.overhang`" in found[0]
    assert _codes(_dev([_at(482.6)]), "L150")


def test_L150_an_overhang_is_measured_from_a_front_drawn_at_the_rack_face():
    """A front drawn at the body between the folds would call a part on an ear
    overhang, and the export would say it reaches past the rack."""
    found = _codes(_dev([_at(-20.0)], w=430.0, overhang={"left": 20.0}), "L150")
    assert any("measured from the rack face" in m for m in found)
    assert not _codes(_dev([_at(-20.0)], overhang={"left": 20.0}), "L150")


def test_L150_half_a_millimetre_is_the_face():
    """A fan bay at -0.05 is the face, not an overhang."""
    assert not _codes(_dev([_at(-0.4)]), "L150")


def test_L150_the_overhang_covers_its_own_side_only():
    assert not _codes(_dev([_at(-20.0)], overhang={"left": 20.0}), "L150")
    assert _codes(_dev([_at(-20.0)], overhang={"right": 20.0}), "L150")
    assert _codes(_dev([_at(-30.0)], overhang={"left": 20.0}), "L150")


def test_L150_the_rear_and_the_underside_are_mirrored():
    """On the rear, x below 0 is the device's right."""
    on_rear = _dev([_at(-20.0)], view="rear")
    assert _codes({**on_rear, "chassis": {**on_rear["chassis"], "overhang": {"left": 20.0}}}, "L150")
    assert not _codes({**on_rear, "chassis": {**on_rear["chassis"],
                                              "overhang": {"right": 20.0}}}, "L150")
    assert not _codes(_dev([_at(-20.0)], view="bottom", h=100.0, overhang={"right": 20.0}), "L150")


def test_L150_height_and_side_views_have_no_overhang():
    assert _codes(_dev([_at(10.0, -5.0)], overhang={"left": 50.0, "right": 50.0}), "L150")
    side = _dev([_at(-20.0)], view="left", w=100.0, overhang={"left": 50.0, "right": 50.0})
    assert _codes(side, "L150")


def test_L150_an_optional_part_is_not_drawn_and_not_reported():
    """37 devices place `optional: ears` brackets at negative x."""
    assert not _codes(_dev([_at(-20.0, optional=True)]), "L150")


def test_L150_decor_is_not_checked():
    """render.py clips decor to the face, so outside it nothing is drawn."""
    doc = _dev([])
    doc["views"]["front"]["panel"] = {"decor": [{"at": [-22.65, 0], "size": [22.5, 44]}]}
    assert not _codes(doc, "L150")


def test_L150_a_bay_or_cutout_past_the_face_is_reported():
    doc = _dev([])
    doc["views"]["front"]["components"]["bays"] = [{"id": "b", "at": [-10, 0], "size": [20, 20]}]
    assert _codes(doc, "L150")
    doc = _dev([])
    doc["views"]["front"]["panel"] = {"cutouts": [{"id": "c", "at": [477.6, 0], "size": [10, 10]}]}
    assert _codes(doc, "L150")


# --- L151 --------------------------------------------------------------------

def test_L151_a_reached_overhang_is_quiet():
    assert not _codes(_dev([_at(-20.0)], overhang={"left": 20.0}), "L151")


def test_L151_a_stale_or_overstated_overhang_warns():
    assert _codes(_dev([_at(0.0)], overhang={"left": 20.0}), "L151")
    assert _codes(_dev([_at(-10.0)], overhang={"left": 20.0}), "L151")
    found = _codes(_dev([_at(-20.0)], overhang={"left": 20.0, "right": 5.0}), "L151")
    assert len(found) == 1 and "overhang.right" in found[0]


def test_L151_an_optional_part_still_reaches():
    """A configuration can draw it, so the figure is not stale."""
    assert not _codes(_dev([_at(-20.0, optional=True)], overhang={"left": 20.0}), "L151")


# --- L125 and L43 ------------------------------------------------------------

def _l125(ch):
    with lint.collecting() as found:
        lint.lint_device_mount("device.yaml", {"chassis": ch})
    return [m for m in found.errors if "[L125]" in m]


@pytest.mark.parametrize("key,value", [("overhang", {"left": 10.0}), ("ears", "behind")])
def test_L125_overhang_and_ears_are_for_a_rack_device(key, value):
    assert not _l125({"ru": 1, key: value})
    assert _l125({"mount": "rack-face", "ru": 1, key: value})
    assert _l125({"mount": "wall", key: value})


def _l43(doc):
    with lint.collecting() as found:
        lint.lint_device_rack_ears("device.yaml", doc)
    return [m for m in found.errors + found.warnings if "[L43]" in m]


def test_L43_stands_down_when_the_ears_are_behind():
    views = {"front": {"size": {"w": 482.6, "h": 88.81}}}
    assert _l43({"chassis": {"width": 440.0, "ru": 2}, "views": views})
    assert not _l43({"chassis": {"width": 440.0, "ru": 2, "ears": "behind"}, "views": views})


# --- the export and the lock -------------------------------------------------

def test_the_overhang_is_said_in_the_comments():
    body = dx.comments_for({"chassis": {"ru": 1, "overhang": {"left": 43, "right": 43}}},
                           "base", {})
    assert "43 mm on each side" in body
    body = dx.comments_for({"chassis": {"ru": 8, "overhang": {"right": 47}}}, "base", {})
    assert "47 mm on the right only, seen from the front" in body
    body = dx.comments_for({"chassis": {"ru": 1, "overhang": {"left": 10, "right": 20}}},
                           "base", {})
    assert "10 mm on the left and 20 mm on the right" in body


def test_no_overhang_says_nothing():
    assert dx.overhang_prose(None) is None
    assert dx.overhang_prose({"left": 0}) is None
    assert "beyond the 19-inch" not in dx.comments_for({"chassis": {"ru": 1}}, "base", {})


def test_the_lock_files_overhang_and_ears_as_surface():
    """Stating the reach a device already had moves nothing; the parts past the
    face carry their own geometry (#865)."""
    assert "overhang" in devicelock.CHASSIS_SURFACE and "overhang" not in devicelock.CHASSIS_SHAPE
    assert "ears" in devicelock.CHASSIS_SURFACE


# --- the 3D frame ------------------------------------------------------------

@pytest.fixture(scope="module")
def js():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    script = ROOT / "spec/tests/js/face-declared.mjs"
    p = subprocess.run(["node", str(script)], capture_output=True, text=True,
                       cwd=str(script.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_drawing_states_its_face_only_when_it_is_bigger(js):
    assert js["ringed"] == [482.6, 44]
    assert js["plain"] is None and js["none"] is None


def test_the_face_is_cropped_back_to_its_declared_size(js):
    assert 'viewBox="0 0 482.6 44"' in js["cropped"]
    assert 'width="482.6mm"' in js["cropped"]


def test_a_part_beyond_the_face_is_laid_out_from_the_face_centre(js):
    """The left ring's centre is the face's left edge, -241.3 from its middle;
    read against the drawing's 568.6 it landed 43 mm further out."""
    assert js["ringCentreOnFace"] == pytest.approx(-241.3)
    assert js["ringCentreOnDrawing"] == pytest.approx(-284.3)


# --- the built devices -------------------------------------------------------

def _root(svg):
    return re.search(r"<svg\b[^>]*>", svg.read_text()).group(0)


@pytest.fixture(scope="module")
def built():
    if not (DIST / "cmh-6dr1u.configs.json").exists():
        pytest.skip("library/dist not built")
    return DIST


def test_the_ringed_front_states_its_face_and_reaches_past_it(built):
    root = _root(built / "cmh-6dr1u.base.front.svg")
    assert 'viewBox="-43 0 568.6 44"' in root
    assert 'data-face-w="482.6"' in root and 'data-face-h="44"' in root


def test_a_front_that_fits_its_face_states_nothing(built):
    for svg in ("cmh-6dr1u.base.rear.svg", "uscmh-sfdabsb2u.base.front.svg"):
        root = _root(built / svg)
        assert "data-face-w" not in root, svg


def test_configs_json_carries_the_two_keys(built):
    ringed = json.loads((built / "cmh-6dr1u.configs.json").read_text())["chassis"]
    assert ringed["overhang"] == {"left": 43.0, "right": 43.0}
    duct = json.loads((built / "uscmh-sfdabsb2u.configs.json").read_text())["chassis"]
    assert duct["ears"] == {"behind": True} and "overhang" not in duct
    plain = json.loads((built / "cmh-5dr1u.configs.json").read_text())["chassis"]
    assert "overhang" not in plain and "ears" not in plain

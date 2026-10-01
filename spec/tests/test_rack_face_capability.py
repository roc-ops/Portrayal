"""One face, one answer: L43 and the capability grader agree about rack ears.

Issue #105. The Dell R740xd draws its front at 482.6 mm because Dell builds the
mounting flanges into the faceplate and puts the VGA, the power button and the
system health lamp in them - a 434 mm face would leave real, field-visible ports
with nowhere to live. L43 looks at that face and correctly accepts it, because
something is SEATED in the flange. The capability grader looked at the same face,
compared it against the 434 mm body, and called the 48.6 mm a chassis-width
disagreement - so a device with all six views and every placement grouped sat at
level 2 with a 3D button that would not light.

Two rules, one face, opposite answers. The definition now lives in capability.py
and lint imports it, which is the direction the import graph allows: lint already
imported capability, so the reverse would have been circular.

The face is LEFT OUT of the width set rather than adjusted. The ear span is not
measured anywhere, and inferring it from the difference would be assuming the
answer.
"""
import pathlib
import sys

import yaml

import libdata

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import capability as C
from portrayal import lint

LIB = ROOT / "library"


def face(*xs):
    return {"components": {"placements": [{"id": f"p{i}", "at": [x, 20]}
                                          for i, x in enumerate(xs)]}}


# ---- the predicate's three conditions, each load-bearing --------------------

def test_a_rack_face_whose_ears_carry_parts_is_recognised():
    assert C.is_populated_rack_face(face(8.0), 482.6, 434.0)


def test_a_body_that_genuinely_is_that_wide_is_not_excused():
    """The face must EXCEED the body. A device whose body really is 482.6 mm
    gets compared normally rather than waved through."""
    assert not C.is_populated_rack_face(face(8.0), 482.6, 482.6)


def test_bare_flanges_are_still_an_error():
    """L43's whole test: bare ears have nothing in the outer 25 mm. Subtract
    them and nothing is lost, so the face should have been drawn at the body."""
    assert not C.is_populated_rack_face(face(200.0), 482.6, 434.0)


def test_an_arbitrarily_wide_face_is_still_an_error():
    """The band is what stops this becoming 'any wide face with a part near the
    edge'. 600 mm is not a rack face however it is populated."""
    assert not C.is_populated_rack_face(face(8.0), 600.0, 434.0)


def test_a_missing_width_or_body_decides_nothing():
    assert not C.is_populated_rack_face(face(8.0), None, 434.0)
    assert not C.is_populated_rack_face(face(8.0), 482.6, None)


# ---- one definition, not two ------------------------------------------------

def test_lint_uses_capabilitys_definition_rather_than_its_own():
    """The point of #105. If these ever become separate objects again, the two
    rules can drift apart and one face gets two answers."""
    assert lint._seated_in_an_ear is C.seated_in_an_ear
    assert lint.EAR_ZONE_MM is C.EAR_ZONE_MM
    assert lint.RACK_FACE_MM is C.RACK_FACE_MM


# ---- the grader --------------------------------------------------------------

def dev(front_w, body_w, ear_x):
    v = {"front": {"size": {"w": front_w, "h": 86.8}, **face(ear_x)},
         "rear": {"size": {"w": body_w, "h": 86.8}},
         "top": {"size": {"w": body_w, "h": 800.0}},
         "bottom": {"size": {"w": body_w, "h": 800.0}},
         "left": {"size": {"w": 800.0, "h": 86.8}},
         "right": {"size": {"w": 800.0, "h": 86.8}}}
    return {"kind": "device", "views": v,
            "chassis": {"width": body_w, "height": 86.8, "depth": 800.0}}


def test_a_populated_rack_face_no_longer_blocks_the_box():
    assert not C._consistency(dev(482.6, 434.0, 8.0)["views"],
                                          dev(482.6, 434.0, 8.0)["chassis"])


def test_a_bare_wide_face_still_blocks_it():
    """The regression that matters in the other direction: excusing this would
    hide a real modelling error, which is what DIM_TOL could never be widened
    enough to allow."""
    bad = C._consistency(dev(482.6, 434.0, 200.0)["views"],
                                     dev(482.6, 434.0, 200.0)["chassis"])
    assert bad and "chassis width" in bad[0]


def test_the_other_axes_are_untouched():
    """Only the width set learned about ears. A height or depth disagreement is
    still a disagreement."""
    d = dev(482.6, 434.0, 8.0)
    d["chassis"]["height"] = 99.9
    bad = C._consistency(d["views"], d["chassis"])
    assert bad and all("chassis height" in b for b in bad)


# ---- the library -------------------------------------------------------------

def test_the_r740xd_is_solid_and_nothing_else_regressed():
    profiles = C.load_profiles(ROOT / "spec" / "schemas")
    levels, dim_blocked = {}, []
    for _slug, f, d in libdata.library():
        cap, _ = C.assess(d, profiles=profiles)
        slug = f"{f.parent.parent.name}/{f.parent.name}"
        levels[slug] = cap["level"]
        if any("disagrees" in (b.get("needs") or "") for b in cap.get("blocked") or []):
            dim_blocked.append(slug)
    assert levels["dell/r740xd"] >= 3, levels["dell/r740xd"]
    # no device in the library is blocked by a dimension disagreement any more
    assert dim_blocked == [], dim_blocked
    # and the three that are incomplete are incomplete for their own reasons
    assert sorted(s for s, lv in levels.items() if lv < 4) == [
        "ufispace/s9502-12sm", "ufispace/s9620-32e", "ufispace/s9620-40dg"]

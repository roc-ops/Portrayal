"""The six defect classes a human found in the MX204 after every gate passed.

Each one is a CLASS, not a one-off, and each is invisible to the gates for a
structural reason - so the fix is a rule or a line of skill guidance, not a
correction to one device. See roc-ops/ndv#32.

Every rule here is exercised against a fixture that FAILS it, because a rule
that has only ever been observed staying quiet has not been shown to work. All
four are silent on the library today; that is the point, and it is also why the
fixtures matter.
"""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import lint  # noqa: E402

P = Path("fixture.yaml")


def caught(code, fn, *a):
    saved_w, saved_e = lint.WARNINGS[:], lint.ERRORS[:]
    lint.WARNINGS.clear()
    lint.ERRORS.clear()
    try:
        fn(*a)
        return [m for m in lint.WARNINGS + lint.ERRORS if f"[{code}]" in m]
    finally:
        lint.WARNINGS[:] = saved_w
        lint.ERRORS[:] = saved_e


# --- 1. rack ears ------------------------------------------------------------

def test_a_body_as_wide_as_the_rack_face_still_has_its_ears():
    """The MX204's own table calls the chassis 19 inches, so the model included
    the ear flanges faithfully. The convention - body is the metal between the
    folds - lived only in reviewers' heads."""
    bad = {"views": {"front": {"size": {"w": 482.0, "h": 44.0}}}}
    assert caught("L43", lint.lint_device_rack_ears, P, bad)
    ok = {"views": {"front": {"size": {"w": 443.0, "h": 44.0}}}}
    assert not caught("L43", lint.lint_device_rack_ears, P, ok)


def test_a_side_face_is_never_mistaken_for_a_rack_face():
    """A left or right view is a depth, and 482 mm of depth is a real chassis."""
    deep = {"views": {"left": {"size": {"w": 482.0, "h": 44.0}}}}
    assert not caught("L43", lint.lint_device_rack_ears, P, deep)


# --- 2. decor --------------------------------------------------------------

def _view(decor=(), placements=(), silk=(), w=100.0):
    return {"size": {"w": w, "h": 50.0},
            "panel": {"decor": list(decor)},
            "silkscreen": list(silk),
            "components": {"placements": list(placements)}}


def test_a_vent_field_buried_under_the_parts_is_reported():
    """The MX204 ran a vent field under an SFP block. The tell is not overlap -
    decor is what sits behind things - but a PATTERN drawn where nothing can
    see it."""
    v = _view(decor=[{"at": [0, 0], "size": [20.0, 12.0], "pattern": "vent"}],
              placements=[{"id": "p", "ref": "std/sfp-ganged@1", "at": [0, 0]},
                          {"id": "q", "ref": "std/sfp-ganged@1", "at": [0, 0]}])
    assert caught("L44", lint.lint_device_decor, P, "front", v, [str(LIB)])


def test_decor_a_part_merely_sits_on_is_left_alone():
    """206 overlaps across 11 devices are correct by construction: a grille
    behind a power shelf, a brand band under a wordmark. Erroring on those was
    the first idea and would reject the model on eleven devices to catch one."""
    v = _view(decor=[{"at": [0, 0], "size": [200.0, 40.0], "pattern": "grille"}],
              placements=[{"id": "p", "ref": "std/sfp-ganged@1", "at": [0, 0]}])
    assert not caught("L44", lint.lint_device_decor, P, "front", v, [str(LIB)])


def test_unpatterned_decor_is_never_reported():
    """A plain colour field has no pattern to lose, so burying it costs nothing."""
    v = _view(decor=[{"at": [0, 0], "size": [20.0, 12.0], "fill": "#8d949c"}],
              placements=[{"id": "p", "ref": "std/sfp-ganged@1", "at": [0, 0]},
                          {"id": "q", "ref": "std/sfp-ganged@1", "at": [0, 0]}])
    assert not caught("L44", lint.lint_device_decor, P, "front", v, [str(LIB)])


def test_printing_that_runs_off_the_face_is_reported():
    """The MX204's model name was clipped at the view edge."""
    v = _view(silk=[{"at": [90.0, 10.0], "text": "MX204 ROUTER", "font-size": 4}])
    assert caught("L44", lint.lint_device_decor, P, "front", v, [str(LIB)])
    inside = _view(silk=[{"at": [10.0, 10.0], "text": "MX204", "font-size": 2}])
    assert not caught("L44", lint.lint_device_decor, P, "front", inside, [str(LIB)])


# --- 3. a rotated part landing off its hole ---------------------------------

def test_a_rotated_part_must_land_on_its_own_cutout():
    """`rotate:` pivots on the part's own pre-rotation centre, so `at` has to be
    back-computed. The MX204's USB was the right size and the right way round
    and sat 3.75 mm outside its hole - invisible, because L39 only ever compared
    SIZES.
    """
    view = {"size": {"w": 100.0, "h": 50.0},
            "panel": {"cutouts": [{"id": "usb", "at": [50.0, 20.0],
                                   "size": [10.4, 14.25]}]},
            "components": {"placements": [
                {"id": "usb", "ref": "std/sfp-ganged@1", "at": [50.0, 20.0],
                 "rotate": 90}]}}
    # rotating about its own centre moves the landed box away from `at`
    assert caught("L39", lint.lint_device_cutouts, P, "front", view, [str(LIB)])


def test_a_rotated_part_placed_correctly_is_silent():
    """Same part, same turn, `at` recomputed so the landed box covers the hole."""
    w, h = 14.25, 10.4
    ax, ay = 50.0, 20.0                     # where the hole is
    # undo the pivot: at = landed - the half-difference the rotation introduces
    d = (w - h) / 2.0
    view = {"size": {"w": 100.0, "h": 50.0},
            "panel": {"cutouts": [{"id": "usb", "at": [ax, ay], "size": [h, w]}]},
            "components": {"placements": [
                {"id": "usb", "ref": "std/sfp-ganged@1", "at": [ax - d, ay + d],
                 "rotate": 90}]}}
    assert not caught("L39", lint.lint_device_cutouts, P, "front", view, [str(LIB)])


# --- 4. a face that is only a size ------------------------------------------

def test_a_size_only_face_does_not_count_as_drawn():
    """Four of them left the MX204 at capability level 2, blocked on `4 views`."""
    bad = {"maturity": "modelled",
           "views": {"top": {"size": {"w": 100.0, "h": 50.0}}}}
    assert caught("L45", lint.lint_device_empty_views, P, bad)


def test_a_draft_is_not_nagged_about_empty_faces():
    draft = {"views": {"top": {"size": {"w": 100.0, "h": 50.0}}}}
    assert not caught("L45", lint.lint_device_empty_views, P, draft)


def test_a_face_with_any_content_at_all_is_enough():
    ok = {"maturity": "modelled",
          "views": {"top": {"size": {"w": 100.0, "h": 50.0},
                            "panel": {"decor": [{"at": [0, 0], "size": [10, 10]}]}}}}
    assert not caught("L45", lint.lint_device_empty_views, P, ok)

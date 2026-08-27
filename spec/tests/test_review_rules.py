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


def test_a_face_the_device_has_declared_unknown_is_not_nagged_about():
    """The ASR 9910's underside carries a `needs-drawing` gap scoped to `bottom`:
    the author looked, found nothing, and wrote down what would close it.

    Warning at that asks twice for a fact somebody has already said the world is
    short of - and the gaps register exists precisely so that a declared unknown
    reads as knowledge rather than as work not done. A rule that fires on one
    teaches people to ignore the rule.
    """
    declared = {"maturity": "modelled",
                "gaps": [{"what": "rack-mounting-plane-not-dimensioned",
                          "scope": ["bottom"], "reason": "needs-drawing"}],
                "views": {"bottom": {"size": {"w": 100.0, "h": 50.0}}}}
    assert not caught("L45", lint.lint_device_empty_views, P, declared)
    # the exemption is per FACE, not per device: another empty view still fires
    two = dict(declared)
    two["views"] = {"bottom": {"size": {"w": 100.0, "h": 50.0}},
                    "top": {"size": {"w": 100.0, "h": 50.0}}}
    assert caught("L45", lint.lint_device_empty_views, P, two)


def test_a_face_with_any_content_at_all_is_enough():
    ok = {"maturity": "modelled",
          "views": {"top": {"size": {"w": 100.0, "h": 50.0},
                            "panel": {"decor": [{"at": [0, 0], "size": [10, 10]}]}}}}
    assert not caught("L45", lint.lint_device_empty_views, P, ok)


# --- the overlap family, one level down (#32 classes 10 and 12) --------------
#
# The MX reviews' own tally: every human-caught defect so far has been an overlap
# or occlusion, and every recurrence was inside a component skin - the one
# surface no rule inspected. L13 asks the question for a device's placements;
# L46 asks it for the parts a component composes.

def _component(parts=(), states=None):
    return {"name": "fx", "size": {"w": 40.0, "h": 20.0},
            "parts": list(parts), "states": list(states or [])}


def test_composed_parts_that_collide_are_reported():
    """The MX960's vertical 40GE DPC stacked sfp-ganged cages on a 7.2mm pitch
    when a rotated cage is 14.25mm tall - a 2:1 overlap that rendered as
    doubled-up ports and that no rule looked for."""
    bad = _component([
        {"id": "p0", "ref": "std/sfp-ganged@1", "at": [0.0, 0.0]},
        {"id": "p1", "ref": "std/sfp-ganged@1", "at": [0.0, 5.0]},   # 10.4 tall
    ])
    assert caught("L46", lint.lint_component_collisions, P, bad, [str(LIB)])


def test_ganged_cages_sharing_a_wall_are_not_reported():
    """261 pairs in the library abut to a hair because a ganged bezel shares
    walls by design. An absolute tolerance either floods or misses; as a
    fraction of the smaller part the distribution is empty between 10 and 50
    percent, which is where the threshold sits."""
    ok = _component([
        {"id": "p0", "ref": "std/sfp-ganged@1", "at": [0.0, 0.0]},
        {"id": "p1", "ref": "std/sfp-ganged@1", "at": [14.2, 0.0]},  # 14.25 wide
    ])
    assert not caught("L46", lint.lint_component_collisions, P, ok, [str(LIB)])


def test_a_lamp_state_nothing_draws_is_reported():
    """A part may declare ok/fail, generate CSS, offer the state in the viewer
    and change no pixel, because only `var(--led-color, ...)` lights anything."""
    d = yaml.safe_load((LIB / "components/juniper/mx204-psu-ac/v1/contract.yaml").read_text())
    hits = caught("L47", lint.lint_component_states_render,
                  LIB / "components/juniper/mx204-psu-ac/v1/contract.yaml", d, [str(LIB)])
    assert hits, "a static-filled lamp went unreported"
    assert "never light" in hits[0]


def test_a_lamp_that_does_light_is_silent():
    p = LIB / "components/juniper/dpc-r-4xge-xfp/v1/contract.yaml"
    d = yaml.safe_load(p.read_text())
    assert not caught("L47", lint.lint_component_states_render, p, d, [str(LIB)])


def test_the_search_follows_composition():
    """Checking only a part's own skin called 166 components broken when 37 are:
    a supply whose lamp is a composed led-dot lights correctly."""
    import glob as _g
    delegating = [p for p in _g.glob(str(LIB / "components/*/*/v*/contract.yaml"))
                  if "var(--led-color" not in "".join(
                      f.read_text() for f in Path(p).parent.glob("skins/*.svg"))
                  and lint._lights_up(Path(p), yaml.safe_load(Path(p).read_text()) or {},
                                      [str(LIB)], set())]
    assert delegating, "no component delegates its lamp - fixture assumption is stale"


# --- 14. a bay the skin never draws -----------------------------------------

def _carrier(tmp_path, drawn_id):
    """A one-bay carrier whose skin draws an element with `drawn_id`."""
    d = tmp_path / "v1"
    (d / "skins").mkdir(parents=True)
    (d / "skins/front.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg">'
        f'<rect id="{drawn_id}" x="0" y="0" width="10" height="10"/></svg>')
    return d / "contract.yaml", {
        "bays": {"bay-1": {"at": [1.0, 1.0], "size": [8.0, 8.0], "accepts": []}}}


def test_a_bay_no_skin_draws_orphans_its_occupant(tmp_path):
    """render.py nests a seated module under the element whose id matches its
    bay. With no such element there is nothing to stamp, so the occupant is hung
    off the chassis root - a tree that reads wrong while every gate passes."""
    p, d = _carrier(tmp_path, "body")
    hits = caught("L48", lint.lint_component_bays_drawn, p, d, [str(LIB)])
    assert hits, "a declared-but-undrawn bay went unreported"
    assert "bay-1" in hits[0]


def test_a_bay_the_skin_does_draw_is_silent(tmp_path):
    p, d = _carrier(tmp_path, "bay-1")
    assert not caught("L48", lint.lint_component_bays_drawn, p, d, [str(LIB)])


def test_the_library_draws_every_bay_it_declares():
    """The eight MX carriers were fixed before the rule was written, so L48 is a
    latch on a door that is already shut. This is the assertion that keeps it
    shut - the failure is silent at render time and invisible until someone
    opens the Explorer tree."""
    import glob as _g
    for p in _g.glob(str(LIB / "components/*/*/v*/contract.yaml")):
        d = yaml.safe_load(Path(p).read_text()) or {}
        assert not caught("L48", lint.lint_component_bays_drawn,
                          Path(p), d, [str(LIB)]), p


# --- 9. a confident mis-measurement, blessed by provenance -------------------

def _fans(*xs):
    return {"views": {"rear": {"components": {"bays": [
        {"id": f"fan-{i}", "group": "fans", "at": [x, 1.5],
         "size": {"w": 82.0, "h": 85.5}} for i, x in enumerate(xs)]}}}}


def test_bays_of_one_group_spaced_unevenly_are_reported():
    """The MX304's fans, as they were written: photo edge detection put fan 1's
    edges on its grille internals, and the provenance then asserted the
    asymmetry as a finding, which is what carried it through every gate."""
    hits = caught("L49", lint.lint_device_bay_pitch, P, _fans(116.4, 213.4, 334.2))
    assert hits, "a staggered fan row went unreported"
    assert "no majority pitch" in hits[0]


def test_the_even_row_that_replaced_it_is_silent():
    assert not caught("L49", lint.lint_device_bay_pitch, P, _fans(116.4, 225.4, 334.2))


def test_a_pitch_broken_by_a_cage_division_is_not_a_defect():
    """Spread alone flags three groups in the library and all three are correct.
    One pitch plus a wider break in the minority - the MX960's SCB column, the
    MX10016's four-slot cages - is a shape real sheet metal has."""
    for gaps in ([0.4] * 3 + [7.4] + [0.4] * 3,
                 ([0.4] * 3 + [7.4]) * 3 + [0.4] * 3,
                 [0.0] * 5 + [60.2] + [0.0] * 5):
        assert lint._bay_pitch_is_uneven(gaps) is None, gaps
    assert lint._bay_pitch_is_uneven([15.0, 38.8]), "the MX304 gaps must still fire"


def test_the_library_sits_on_an_even_pitch():
    import glob as _g
    for f in _g.glob(str(LIB / "devices/*/*/device.yaml")):
        d = yaml.safe_load(Path(f).read_text()) or {}
        assert not caught("L49", lint.lint_device_bay_pitch, Path(f), d), f


# --- 7. inside a skin's own geometry -----------------------------------------

def _skin(tmp_path, body):
    d = tmp_path / "v1"
    (d / "skins").mkdir(parents=True)
    (d / "skins/default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 40">'
        '<rect x="0" y="0" width="16" height="40" fill="#4fb832"/>' + body + "</svg>")
    return d / "contract.yaml", {}


def test_printing_that_runs_off_the_part_is_reported():
    """common/pull-tab set SERVICE INFO at 5.44 across a 16mm-wide tab; it
    overflowed by more than double and every gate passed, because no rule
    looked inside a component's own SVG."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p, d = _skin(Path(td), '<text x="8" y="20" font-size="5.44" '
                     'text-anchor="middle" fill="#000">SERVICE INFO</text>')
        hits = caught("L50", lint.lint_component_skin_printing, p, d, [str(LIB)])
        assert hits, "a label overflowing its part went unreported"
        assert "runs mostly off the part" in hits[0]


def test_printing_painted_over_after_it_is_reported():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p, d = _skin(Path(td), '<text x="2" y="20" font-size="2" fill="#000">ABC</text>'
                     '<rect id="chip" x="0" y="16" width="12" height="8" fill="#333"/>')
        hits = caught("L50", lint.lint_component_skin_printing, p, d, [str(LIB)])
        assert hits, "a buried label went unreported"
        assert "painted over" in hits[0]


def test_a_label_beside_its_own_lamp_is_not_buried():
    """The deepest overlap in the library is 22% - a STATUS legend next to its
    lamp, entirely legible. Text width is estimated at 0.6em per character with
    no font engine and runs about 20% wide, so the threshold is deliberately
    loose: a rule reporting near misses would be reporting the estimate."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p, d = _skin(Path(td), '<text x="2" y="20" font-size="2" fill="#000">STATUS</text>'
                     '<circle id="lamp" cx="9.5" cy="19" r="1.3" fill="#8d949c"/>')
        assert not caught("L50", lint.lint_component_skin_printing, p, d, [str(LIB)])


def test_a_rotated_label_is_measured_where_it_actually_lands():
    """SVG rotates about the point named in the transform, not the box centre.
    Spinning a vertical model name about its centre threw 38 correctly-placed
    labels clear of their parts."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p, d = _skin(Path(td), '<text x="14" y="4" transform="rotate(90 14 4)" '
                     'font-size="2" fill="#000">A9K-MPA-1X40GE</text>')
        assert not caught("L50", lint.lint_component_skin_printing, p, d, [str(LIB)])


def test_the_library_prints_where_it_can_be_read():
    import glob as _g
    for f in _g.glob(str(LIB / "components/*/*/v*/contract.yaml")):
        assert not caught("L50", lint.lint_component_skin_printing,
                          Path(f), {}, [str(LIB)]), f

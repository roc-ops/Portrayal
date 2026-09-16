"""The six defect classes a human found in the MX204 after every gate passed.

Each one is a CLASS, not a one-off, and each is invisible to the gates for a
structural reason - so the fix is a rule or a line of skill guidance, not a
correction to one device. See roc-ops/Portrayal#32.

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

from portrayal import lint

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


def _rackface(placements=(), bays=(), cutouts=(), w=482.6):
    return {"views": {"front": {
        "size": {"w": w, "h": 86.8},
        "panel": {"cutouts": list(cutouts)},
        "components": {"placements": list(placements), "bays": list(bays)}}}}


def test_a_populated_ear_is_part_of_the_face():
    """Dell builds the ears into the faceplate and puts ports in them. A
    PowerEdge R740xd carries a VGA and a USB in the right-hand ear; its front
    measures 482.6 x 86.8, which the render confirms at 2.10% against Gate 1
    where the 434 mm body fails at 13.5%. Modelling it at 434 would leave real
    addressable ports with nowhere to live."""
    dell = _rackface(placements=[
        {"ref": "std/usb-a@1", "id": "usb-front", "at": [465.0, 30.0]},
        {"ref": "std/vga@1", "id": "vga-front", "at": [462.0, 52.0]}])
    assert not caught("L43", lint.lint_device_rack_ears, P, dell)


def test_a_bare_flange_is_still_an_ear():
    """The MX204 case, which is why the rule exists: 482 mm of face with
    everything seated well inboard of both ends is a body wearing its ears."""
    mx = _rackface(placements=[
        {"ref": "std/sfp@1", "id": "p1", "at": [120.0, 20.0]},
        {"ref": "std/sfp@1", "id": "p2", "at": [360.0, 20.0]}])
    assert caught("L43", lint.lint_device_rack_ears, P, mx)


def test_either_ear_counts():
    """Dell's power button and status lamps live in the LEFT ear; the ports are
    in the right. One populated end is enough to say the ears are integral."""
    left = _rackface(placements=[{"ref": "x/y@1", "id": "pwr", "at": [8.0, 20.0]}])
    assert not caught("L43", lint.lint_device_rack_ears, P, left)


def test_a_bay_or_a_cutout_in_an_ear_counts_too():
    """A hole punched in the ear is the same evidence as a part seated in it -
    both say the vendor treated that metal as face rather than flange."""
    bay = _rackface(bays=[{"id": "ear-bay", "at": [460.0, 10.0],
                           "size": {"w": 18.0, "h": 20.0}}])
    assert not caught("L43", lint.lint_device_rack_ears, P, bay)
    cut = _rackface(cutouts=[{"id": "vga", "at": [4.0, 30.0], "size": [16.0, 8.0]}])
    assert not caught("L43", lint.lint_device_rack_ears, P, cut)


def test_the_exemption_does_not_apply_to_a_narrow_face():
    """The stand-down only exists inside the 480-487 band. A 443 mm body was
    never going to fire, and a part near its edge must not start it firing."""
    body = _rackface(placements=[{"ref": "x/y@1", "id": "p", "at": [2.0, 10.0]}],
                     w=443.0)
    assert not caught("L43", lint.lint_device_rack_ears, P, body)


def test_a_placement_with_no_anchor_is_not_read_as_an_ear():
    """An item missing `at` says nothing about where it sits, and treating a
    silence as evidence would let the rule be switched off by an omission."""
    vague = _rackface(placements=[{"ref": "x/y@1", "id": "somewhere"}])
    assert caught("L43", lint.lint_device_rack_ears, P, vague)


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


# --- L39 2b: concentric, not covering ------------------------------------

FAN = "common/fan-module@1"          # 48.6 x 40


def _landed(part_at, hole_wh, hole_at):
    return {"panel": {"cutouts": [{"id": "p", "at": list(hole_at), "size": list(hole_wh)}]},
            "components": {"placements": [{"id": "p", "ref": FAN, "at": list(part_at)}]}}


def _cut(view):
    return caught("L39", lint.lint_device_cutouts, P, "front", view, [str(LIB)])


def test_a_part_with_clearance_is_not_a_defect():
    """An ASR 9922 fan tray is 38.1 tall in a 41.5 opening because that is how
    trays fit; a 9006 tray holds six 92mm fans laid flat, so its height clears a
    fan\'s thickness and not its frame. The covering test reported both, and
    reporting correct hardware teaches people to resize correct hardware."""
    assert not _cut(_landed((1.7, 3.0), (52.0, 46.0), (0.0, 0.0)))


def test_a_part_wider_than_its_hole_is_not_a_defect():
    """That tray\'s end grips land ON the metal - the ASR 9922\'s plate measures
    434.98 inside a 475.95 envelope, against a 439 opening."""
    assert not _cut(_landed((0.0, 0.0), (40.0, 34.0), (4.3, 3.0)))


def test_a_part_sitting_off_centre_is_reported():
    """The MX204\'s USB: correctly sized, correctly rotated, 3.75mm out. The
    sizes agreed so the conforms check passed, and nothing else compared a
    landed part with the opening it fills."""
    hits = _cut(_landed((3.75, 0.0), (48.6, 40.0), (0.0, 0.0)))
    assert hits, "an off-centre part went unreported"
    assert "does not sit in its own cutout" in hits[0]


# --- component bays: a riser is a bay that holds bays ---------------------

def _validator():
    import json
    from jsonschema import Draft202012Validator
    return Draft202012Validator(json.loads((SPEC / "schemas/component.schema.json").read_text()))


def _bay(**kw):
    b = {"at": [1.0, 2.0], "size": [10.0, 20.0], "accepts": ["cisco/spa-2xt3e3@1"]}
    b.update(kw)
    return {"format": 1, "kind": "component", "name": "x", "version": "1.0.0",
            "size": {"w": 40.0, "h": 40.0}, "bays": {"bay-0": b}}


def test_a_component_bay_that_names_nothing_is_rejected():
    """`bays:` was `additionalProperties: true` and described as 'v0: unused'
    while 51 bays across 25 components already relied on it. a9k-sip-700-8g's
    four SPA bays carried geometry and no `accepts`, so they offered nothing
    while its identical 4GB twin offered twenty-two - and nothing validated it."""
    d = _bay()
    del d["bays"]["bay-0"]["accepts"]
    assert list(_validator().iter_errors(d)), "a bay naming nothing validated"


def test_a_component_bay_needs_its_geometry():
    for missing in ("at", "size"):
        d = _bay()
        del d["bays"]["bay-0"][missing]
        assert list(_validator().iter_errors(d)), f"a bay with no {missing} validated"


def test_a_face_only_field_is_rejected_on_a_nested_bay():
    """A nested bay numbers within its carrier, so `group`/`rel-pos` mean nothing
    here; a configuration varies a chassis and not a card, so nor does `only-in`."""
    for stray in ({"group": "spas"}, {"rel-pos": 0}, {"only-in": ["ac"]}):
        assert list(_validator().iter_errors(_bay(**stray))), f"{stray} validated"


def test_the_library_validates_under_it():
    import glob as _g
    v = _validator()
    for f in _g.glob(str(LIB / "components/*/*/v*/contract.yaml")):
        d = yaml.safe_load(Path(f).read_text()) or {}
        if not d.get("bays"):
            continue
        assert not list(v.iter_errors(d)), f


# --- a bay says what goes in it, one of two ways --------------------------

def _dev_validator():
    import json
    from jsonschema import Draft202012Validator
    return Draft202012Validator(json.loads((SPEC / "schemas/device.schema.json").read_text()))


def _with_bay(bay):
    return {"format": 1, "kind": "device", "name": "x", "version": "0.1.0",
            "maturity": "draft", "manufacturer": "M", "model": "M",
            "chassis": {"width": 440.0, "height": 44.0, "depth": 500.0, "ru": 1},
            "views": {"front": {"size": {"w": 440.0, "h": 44.0},
                                "components": {"bays": [bay]}}}}


def _bay_errs(bay):
    return [e for e in _dev_validator().iter_errors(_with_bay(bay))
            if "bays" in [str(x) for x in e.absolute_path]]


BASE = {"id": "slot-0", "at": [0.0, 0.0], "size": {"w": 100.0, "h": 20.0}}


def test_a_closed_vendor_matrix_still_validates():
    """476 bays carrying 2648 refs work this way, because a switch's card
    catalogue is closed and printed and the support tables ARE the lists."""
    assert not _bay_errs({**BASE, "accepts": ["cisco/spa-2xt3e3@1"]})


def test_an_open_form_factor_may_name_an_interface_instead():
    """Anyone may build a PCIe card, so a list is unbounded and one written
    anyway asserts something the vendor never said. See roc-ops/Portrayal#43."""
    assert not _bay_errs({**BASE, "interface": "pcie-x8"})


def test_a_bay_may_say_both():
    """A slot can be standard and have a published list."""
    assert not _bay_errs({**BASE, "interface": "pcie-x8",
                          "accepts": ["cisco/spa-2xt3e3@1"]})


def test_a_bay_that_says_neither_is_rejected():
    """A hole that promises nothing - which is why `accepts` was unconditionally
    required before, and why relaxing it needed the either/or rather than a drop."""
    assert _bay_errs(BASE), "a bay naming neither a list nor an interface validated"


# --- power roles: a class says which way its watts point ------------------

def _roles():
    return yaml.safe_load((SPEC / "schemas/power-roles.yaml").read_text())["roles"]


def test_every_class_in_use_has_a_power_role():
    """A totalling tool stopped at the MX craft interface. The contract was
    silent because `panel` and `display` were in neither set, so L27 never asked
    - a silence nothing had demanded be filled, indistinguishable from a part
    that draws nothing."""
    import glob as _g
    r = _roles()
    known = set(r["draw"]) | set(r["supply"]) | set(r["passive"])
    seen = {}
    for f in _g.glob(str(LIB / "components/*/*/v*/contract.yaml")):
        d = yaml.safe_load(Path(f).read_text()) or {}
        if d.get("class"):
            seen.setdefault(d["class"], f)
    missing = {c: seen[c] for c in seen if c not in known}
    assert not missing, f"classes in use with no power role: {sorted(missing)}"


def test_a_class_belongs_to_exactly_one_role():
    r = _roles()
    allc = r["draw"] + r["supply"] + r["passive"]
    dupes = {c for c in allc if allc.count(c) > 1}
    assert not dupes, f"a class in two roles cannot be totalled: {sorted(dupes)}"


def test_the_craft_interface_draws():
    """The class-set omission that caused the bug. A craft interface is an LCD,
    buttons, alarm lamps and a processor - it is not sheet metal.

    It used to check `panel` AND `display`, because the four MX craft interfaces
    were split between the two classes. #173 merged `panel` into `display`, so
    the check is now on the PARTS rather than on both names - which is what it
    was always about, and is a thing a later rename cannot quietly satisfy.
    """
    r = _roles()
    assert "display" in r["draw"], "the craft interfaces draw"
    import yaml
    for name in ("mx240-craft", "mx480-craft", "mx2000-craft", "mx960-craft"):
        c = next(iter(LIB.glob(f"components/juniper/{name}/*/contract.yaml")))
        cls = (yaml.safe_load(c.read_text()) or {}).get("class")
        assert cls in r["draw"], f"{name} is {cls!r}, which is in no draw role"


def test_a_cage_is_passive_and_the_optic_in_it_is_not():
    """A cage is a hole with a bezel; what draws is the thing fitted in it."""
    r = _roles()
    assert "port" in r["passive"]
    assert "transceiver" in r["draw"]


def test_an_undeclared_class_is_reported():
    hits = caught("L51", lint.lint_component_role, P, {"class": "flux-capacitor"})
    assert hits, "a class in no power role went unreported"
    assert "in no power role" in hits[0]


def test_a_declared_class_is_silent():
    for cls in ("line-card", "psu", "filter"):
        assert not caught("L51", lint.lint_component_role, P, {"class": cls}), cls


def _pw(attrs, prov=None):
    d = {"name": "card-x", "class": "line-card", "attrs": attrs}
    if prov is not None:
        d["provenance"] = {"power": prov}
    return d


def test_a_watt_figure_with_no_source_is_reported():
    """The number is only better than the warning if the row is written down."""
    hits = caught("L52", lint.lint_component_power, P,
                  _pw({"power-draw-max-w": 440}))
    assert hits, "an unsourced watt figure went unreported"
    assert "power-draw-max-w" in hits[0]
    # It has to say WHY, because the fix is archaeology and the reader needs to
    # know a bare number cannot say which rung of the ladder it is.
    assert "ambient" in hits[0]


def test_a_sourced_watt_figure_is_silent():
    assert not caught("L52", lint.lint_component_power, P,
                      _pw({"power-draw-max-w": 440}, "chassis guide, 440 W at 55 C"))


def test_a_supply_figure_is_asked_the_same_question():
    """L27 sends draw and supply down different branches; L52 predates the split."""
    d = _pw({"power-output-w": 2400})
    d["class"] = "psu"
    assert caught("L52", lint.lint_component_power, P, d)


def test_a_part_with_no_figure_at_all_is_left_to_l27():
    """L52 is about the number that arrived without a row, not the missing one."""
    assert not caught("L52", lint.lint_component_power, P, _pw({}))


def test_empty_provenance_does_not_count_as_a_source():
    assert caught("L52", lint.lint_component_power, P,
                  _pw({"power-draw-max-w": 440}, "   "))


def test_an_attestation_answers_l27():
    """`not-published` is a settled answer; L27's warning is for an open question."""
    d = _pw({"power-absent": "not-published"})
    d["provenance"] = {"power": "searched the corpus; the vendor gives input current only"}
    assert not caught("L27", lint.lint_component_power, P, d)


def test_a_part_with_neither_figure_nor_attestation_still_warns():
    assert caught("L27", lint.lint_component_power, P, _pw({}))


def test_an_unsourced_attestation_is_reported():
    """An absence claim is a fact about the world and needs sourcing like a number."""
    hits = caught("L52", lint.lint_component_power, P,
                  _pw({"power-absent": "not-published"}))
    assert hits, "an unsourced absence claim went unreported"
    assert "what was searched" in hits[0]
    # It has to carry the lesson, not just the rule: the seven MX contracts named
    # one book and read as the corpus.
    assert "chassis guides" in hits[0]


def test_a_tray_can_say_watts_are_the_wrong_unit():
    d = _pw({"power-absent": "not-applicable"})
    d["class"] = "power"
    d["provenance"] = {"power": "a tray: it carries current, it does not convert it"}
    assert not caught("L27", lint.lint_component_power, P, d)
    assert not caught("L52", lint.lint_component_power, P, d)


def test_provenance_keyed_by_the_attribute_counts():
    """Contracts predating L52 key the note by the attr, which is no less a source."""
    d = _pw({"power-draw-max-w": 400})
    d["provenance"] = {"power-draw-max-w": "guide: 'a power draw of approximately 400W'"}
    assert not caught("L52", lint.lint_component_power, P, d)


def test_a_power_named_key_on_an_attestation_counts_too():
    d = _pw({"power-absent": "not-published"})
    d["provenance"] = {"power-output-w": "searched the corpus; the vendor gives current only"}
    assert not caught("L52", lint.lint_component_power, P, d)


def test_an_unrelated_provenance_key_does_not_count():
    d = _pw({"power-draw-max-w": 400})
    d["provenance"] = {"size": "measured off the rear panel figure"}
    assert caught("L52", lint.lint_component_power, P, d)


# --- L13: a stack is not a sizing error ---------------------------------------
#
# Every L13 exemption before `under:` was a faceplate exemption: mate-to, for:,
# frames:, mounts, disjoint only-in - each lets two boxes share a plan because
# one of them is not really in it. The R740xd's top with the lid off is a
# section through four heights, and the board's box contains every other box
# because everything stands on it. The rule was right, and the model was right,
# and they could not both be said.

def _top(placements):
    return {"size": {"w": 434.0, "h": 737.5},
            "components": {"placements": list(placements)}}


BOARD = {"id": "board", "ref": "dell/system-board-14g@1", "at": [3.58, 267.74]}
FANS = {"id": "fans", "ref": "dell/fan-cage-14g@1", "at": [12.55, 245.38]}
SHROUD = {"id": "shroud", "ref": "dell/air-shroud-14g@1", "at": [1.36, 318.98]}
LID = {"id": "lid", "ref": "dell/system-cover-14g@1", "at": [0.0, 196.9]}


def test_a_board_under_a_fan_cage_is_not_an_overlap():
    """The fan cage's box runs 49mm into the board's, and neither is mounted -
    two wells, in the faceplate reading, cut through each other. Without the
    declaration that is the sizing error L13 exists for; with it, the board is
    a well and the cage stands over it."""
    assert caught("L13", lint.lint_device_overlap, P, "top", _top([BOARD, FANS]), [str(LIB)])
    ok = _top([dict(BOARD, under="fans"), FANS])
    assert not caught("L13", lint.lint_device_overlap, P, "top", ok, [str(LIB)])


def test_two_lids_in_one_place_are_still_reported_unless_one_is_under():
    """Mounted-over-mounted is two covers that cannot both be there - until the
    lower one says it is lower. The shroud and the system cover are both
    `mounts`, and only `under:` tells them apart."""
    assert caught("L13", lint.lint_device_overlap, P, "top", _top([SHROUD, LID]), [str(LIB)])
    ok = _top([dict(SHROUD, under="lid"), LID])
    assert not caught("L13", lint.lint_device_overlap, P, "top", ok, [str(LIB)])


def test_a_flat_part_cannot_claim_to_be_under_another_flat_part():
    """The declaration is checked, not trusted. Two riser clips - flat, neither
    mounted - one on top of the other is a sizing error wearing a new key, and
    it is reported as one."""
    lo = {"id": "a", "ref": "dell/riser-card-clip-14g@1", "at": [0.0, 0.0], "under": "b"}
    hi = {"id": "b", "ref": "dell/riser-card-clip-14g@1", "at": [1.0, 1.0]}
    hits = caught("L13", lint.lint_device_overlap, P, "top", _top([lo, hi]), [str(LIB)])
    assert hits and "no height between them" in hits[0]


def test_under_must_name_something_in_the_view():
    bad = _top([dict(BOARD, under="lid-that-is-not-here")])
    hits = caught("L13", lint.lint_device_overlap, P, "top", bad, [str(LIB)])
    assert hits and "not in this view" in hits[0]


def test_a_bay_can_be_under_a_well():
    """An opening under a recess. Without the declaration the well's box on
    the bay is the overlap L13 reports; with it the bay is a well by nature
    and the pair is not compared. The fan cage is the well here because it is
    a plain one - the mid tray this first used became `mounts` the day it got
    a pull handle, and mounted-over-unmounted is exempt before `under:` is
    even consulted."""
    cage = {"id": "cage", "ref": "dell/fan-cage-14g@1", "at": [12.55, 420.62]}
    sock = {"id": "sock", "at": [20.0, 430.0], "size": {"w": 3.8, "h": 40.0}}
    v = {"size": {"w": 434.0, "h": 737.5},
         "components": {"placements": [cage], "bays": [sock]}}
    assert caught("L13", lint.lint_device_overlap, P, "top", v, [str(LIB)])
    v["components"]["bays"] = [dict(sock, under="cage")]
    assert not caught("L13", lint.lint_device_overlap, P, "top", v, [str(LIB)])


def test_in_names_a_well_or_is_an_error():
    """`in:` is `under:` read from the other end - what stands in a well is
    over it - and it is checked the same way: the target has to be a recess.
    A DIMM socket in the system board is fine; a DIMM socket 'in' a flat
    riser clip has no floor to stand on and says so."""
    board = {"id": "board", "ref": "dell/system-board-14g@1", "at": [3.58, 0.07]}
    sock = {"id": "sock", "at": [20.0, 281.0], "size": {"w": 3.8, "h": 133.4}, "in": "board"}
    v = {"size": {"w": 434.0, "h": 737.5},
         "components": {"placements": [board], "bays": [sock]}}
    assert not caught("L13", lint.lint_device_overlap, P, "top", v, [str(LIB)])
    clip = {"id": "clip", "ref": "dell/riser-card-clip-14g@1", "at": [10.0, 280.0]}
    v = {"size": {"w": 434.0, "h": 737.5},
         "components": {"placements": [clip], "bays": [dict(sock, **{"in": "clip"})]}}
    hits = caught("L13", lint.lint_device_overlap, P, "top", v, [str(LIB)])
    assert hits and "not a well" in hits[0]


def test_a_shelf_cannot_put_its_card_through_the_lid():
    """`floor:` is where a bay's occupant stands, and the occupant rises its
    own `d` from there. A shelf 20.8 down under a 21.6 card puts 0.8 of the
    card above the face - riser 3's did - and a shelf deeper than its well
    is a hole in it. Both are the sizing error L13 exists for."""
    board = {"id": "board", "ref": "dell/system-board-14g@1", "at": [5.5, 6.2]}
    card = {"id": "c", "at": [3.9, 0.0], "size": {"w": 120.9, "h": 173.8},
            "accepts": ["common/pcie-card-plan@1"], "in": "board"}
    v = lambda floor: {"size": {"w": 434.0, "h": 737.5},
                       "components": {"placements": [board], "bays": [dict(card, floor=floor)]}}
    hits = caught("L13", lint.lint_device_overlap, P, "top", v(20.8), [str(LIB)])
    assert hits and "out of the face" in hits[0]
    hits = caught("L13", lint.lint_device_overlap, P, "top", v(90.0), [str(LIB)])
    assert hits and "only 79.9 deep" in hits[0]
    assert not caught("L13", lint.lint_device_overlap, P, "top", v(26.6), [str(LIB)])

"""A stepped housing that opens: `chassis.section` together with `chassis.halves`.

A housing that states a `section` builds in 3D as a stepped body, and one that states `halves`
opens in two. This change lets the two be stated together: the seam is the plane at `base.stands`
from `base.outer`, each half is the part of the stepped body on its side of it, and the lid turns
about the line where the seam meets the hinge face's outline. This module holds the lint rules
that make the combination well formed, what the lock asks for, and that a device with no
`section` keeps every halves rule it had. The geometry is held in test_section_split_js.py. The
test device is `spec/tests/fixtures/opening-section`, a synthetic box, never a library device.

Lint codes are read from `lint.SECTION_OPENS_CODES`, so the numbers can change at merge without
touching this module.
"""
import copy
import pathlib

import pytest
import yaml

from portrayal import devicelock as dl
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE_LIB = ROOT / "spec/tests/fixtures/opening-section/lib"
DEVICE = FIXTURE_LIB / "devices/fixture/stepped-open/device.yaml"
CLAM = ROOT / "spec/tests/fixtures/halves/lib/devices/fixture/clam/device.yaml"


def device():
    """The fixture device, as a fresh document a test may edit."""
    return copy.deepcopy(yaml.safe_load(DEVICE.read_text()))


def clam():
    return copy.deepcopy(yaml.safe_load(CLAM.read_text()))


def halves_of(doc):
    return doc["chassis"]["halves"]


def codes():
    return lint.SECTION_OPENS_CODES


def collect(doc, *fns):
    with lint.collecting() as got:
        for fn in fns:
            fn("device.yaml", doc, []) if fn is lint.lint_device_section else fn("device.yaml", doc)
    return got


def found(doc, *fns):
    """`{code: [message]}` over the errors and warnings of the rules in `fns`."""
    fns = fns or (lint.lint_device_section_opens,)
    got = collect(doc, *fns)
    out = {}
    for m in got.errors + got.warnings:
        code = m.split("[", 1)[1].split("]", 1)[0]
        out.setdefault(code, []).append(m.split("] ", 1)[1])
    return out


def severity(doc, code):
    got = collect(doc, lint.lint_device_section_opens)
    if any(f"[{code}]" in m for m in got.errors):
        return "error"
    if any(f"[{code}]" in m for m in got.warnings):
        return "warning"
    return None


def everything(doc):
    """Every rule that reads the halves or the section, as the lint run calls them."""
    with lint.collecting() as got:
        lint.lint_device_halves("device.yaml", doc)
        lint.lint_device_section("device.yaml", doc, [])
        lint.lint_device_section_opens("device.yaml", doc)
    return got.errors, got.warnings


# --- the fixture and the catalogue ---------------------------------------------------------

def test_the_fixture_is_quiet_to_every_rule():
    errors, warnings = everything(device())
    assert errors == [] and warnings == [], (errors, warnings)


def test_the_new_rules_are_in_the_catalogue_with_a_why_and_a_fix():
    assert set(codes()) == {"faces", "widest", "seam"}
    for code in codes().values():
        assert code in lint.RULES, code
        kind, what, fix, why, severity_ = lint.RULES[code]
        assert kind == "device" and what and fix and len(why) > 40


def test_the_codes_follow_the_last_rule_taken():
    # three codes in a row, each a rule in the catalogue; later rules take the numbers after them
    new = sorted(int(c[1:]) for c in codes().values())
    assert new == list(range(new[0], new[0] + 3)), new
    assert all(f"L{n}" in lint.RULES for n in new), new


# --- L206 no longer refuses halves ---------------------------------------------------------

def test_a_section_may_now_be_stated_with_halves():
    got = found(device(), lint.lint_device_section)
    assert lint.SECTION_CODES["kind"] not in got, got


def test_the_message_of_the_section_rule_no_longer_names_halves():
    what = lint.RULES[lint.SECTION_CODES["kind"]][1]
    assert "halves" not in what


@pytest.mark.parametrize("edit", [
    lambda c: c.update(bevel=[{"edges": ["front-left"], "size": 5}]),
    lambda c: c.update(rounded={"radius": 10}),
    lambda c: c.update(shell="sheet"),
    lambda c: c.update(ears={"h": 20}),
    lambda c: c.update(overhang={"left": 5}),
    lambda c: c.update(kits=[{"ref": "fixture/rail@1", "supply": "in-box"}]),
    lambda c: c.update(mount="rack"),
])
def test_the_other_clauses_of_the_section_rule_stand(edit):
    doc = device()
    edit(doc["chassis"])
    assert lint.SECTION_CODES["kind"] in found(doc, lint.lint_device_section)


# --- the faces: the seam is parallel to the extrusion and the hinge is a long face ---------

@pytest.mark.parametrize("outer", ["front", "rear", "left", "right"])
def test_a_base_whose_outer_face_is_not_top_or_bottom_is_an_error(outer):
    doc = device()
    halves_of(doc)["base"]["outer"] = outer
    assert codes()["faces"] in found(doc)
    assert severity(doc, codes()["faces"]) == "error"
    assert any("outer" in m for m in found(doc)[codes()["faces"]])


@pytest.mark.parametrize("hinge", ["top", "bottom", "left", "right"])
def test_a_hinge_that_is_not_the_front_or_the_rear_is_an_error(hinge):
    doc = device()
    halves_of(doc)["lid"]["hinge"] = hinge
    assert codes()["faces"] in found(doc)
    assert severity(doc, codes()["faces"]) == "error"
    assert any("hinge" in m for m in found(doc)[codes()["faces"]])


@pytest.mark.parametrize("outer,hinge", [("top", "front"), ("top", "rear"), ("bottom", "front"),
                                         ("bottom", "rear")])
def test_the_four_faces_that_work_are_quiet(outer, hinge):
    doc = device()
    halves_of(doc)["base"]["outer"] = outer
    halves_of(doc)["lid"]["hinge"] = hinge
    if outer == "bottom":
        halves_of(doc)["base"]["stands"], halves_of(doc)["lid"]["stands"] = 144.0, 144.0
    assert codes()["faces"] not in found(doc)


# --- the widest: a flange is expected at the seam -------------------------------------------

def test_a_seam_in_the_flange_is_quiet():
    doc = device()
    for stands in (133.0, 144.0, 154.0):
        halves_of(doc)["base"]["stands"] = stands
        assert codes()["widest"] not in found(doc), stands


@pytest.mark.parametrize("stands", [60.0, 200.0])
def test_a_seam_where_the_section_is_not_at_its_widest_is_a_warning(stands):
    doc = device()
    halves_of(doc)["base"]["stands"] = stands
    assert codes()["widest"] in found(doc)
    assert severity(doc, codes()["widest"]) == "warning"
    assert codes()["seam"] not in found(doc)


def test_the_widest_is_judged_from_the_bottom_when_the_base_is_the_bottom():
    doc = device()
    halves_of(doc)["base"]["outer"] = "bottom"
    halves_of(doc)["base"]["stands"] = 144.0             # 288 - 144 = 144 from the top: the flange
    assert codes()["widest"] not in found(doc)
    halves_of(doc)["base"]["stands"] = 60.0               # 228 from the top: the lower casting
    assert codes()["widest"] in found(doc)


# --- the seam: it cuts the section into two parts that each have outline -------------------

@pytest.mark.parametrize("stands,word", [
    (288.0, "outside"),         # on the bottom side of the section: the lid would be empty
    (300.0, "outside"),         # past it
    (132.0, "edge"),            # exactly on the flange's upper edge
    (155.0, "edge"),            # exactly on its lower edge
])
def test_a_seam_outside_the_section_or_on_a_horizontal_edge_is_an_error(stands, word):
    doc = device()
    halves_of(doc)["base"]["stands"] = stands
    assert codes()["seam"] in found(doc)
    assert severity(doc, codes()["seam"]) == "error"
    assert any(word in m for m in found(doc)[codes()["seam"]]), found(doc)


def test_a_seam_in_the_stretch_the_fins_cut_back_leaves_a_half_with_no_body():
    """The top field cuts the upper casting back 29 mm over the whole of its width: a seam 10
    down divides a body that has nothing there."""
    doc = device()
    halves_of(doc)["base"]["stands"] = 10.0
    assert codes()["seam"] in found(doc)
    assert any("cut back" in m for m in found(doc)[codes()["seam"]]), found(doc)
    del doc["chassis"]["fins"]
    assert codes()["seam"] not in found(doc)


def test_a_seam_through_wings_the_fins_leave_is_quiet():
    """Where the section is wider than the field's edge, rows above the core still have body."""
    doc = device()
    doc["chassis"].update(
        width=60.0, height=40.0, depth=50.0,
        section=[[10, 0], [40, 0], [40, 5], [50, 5], [50, 40], [0, 40], [0, 5], [10, 5]],
        fins=[{"on": "top", "span": [5.0, 55.0], "core": 15.0, "rib": 4.0, "gap": 4.0}])
    halves_of(doc)["base"]["stands"] = 8.0
    assert codes()["seam"] not in found(doc)


def test_a_seam_on_the_top_edge_is_an_error_from_the_bottom_too():
    doc = device()
    halves_of(doc)["base"]["outer"] = "bottom"
    halves_of(doc)["base"]["stands"] = 288.0           # 0 from the top: one half is empty
    assert codes()["seam"] in found(doc)


def test_a_seam_inside_the_section_is_quiet():
    doc = device()
    for stands in (30.0, 60.0, 131.0, 140.0, 156.0, 239.0):
        halves_of(doc)["base"]["stands"] = stands
        assert codes()["seam"] not in found(doc), stands
    del doc["chassis"]["fins"]
    for stands in (1.0, 287.0):                 # near an edge, but inside, and with no fins to cut back
        halves_of(doc)["base"]["stands"] = stands
        assert codes()["seam"] not in found(doc), stands


def test_a_section_that_cannot_be_read_is_left_to_the_section_rules():
    doc = device()
    doc["chassis"]["section"] = [[0, 0], [1, 0], [1, 1]]
    assert found(doc) == {}


# --- a device without a section keeps today's halves rules exactly --------------------------

def test_a_device_with_no_section_is_quiet_to_the_new_rules():
    assert found(clam()) == {}
    doc = clam()
    halves_of(doc)["base"]["outer"] = "left"        # not top or bottom, and no section to mind
    assert found(doc) == {}
    halves_of(doc)["lid"]["hinge"] = "top"
    assert found(doc) == {}


def test_the_halves_rules_judge_a_device_with_no_section_as_they_did():
    """The finding set of the halves rules on the box fixture and on four broken copies is
    pinned, so a change to them for a device with no `section` shows here."""
    def codes_of(doc):
        got = collect(doc, lint.lint_device_halves)
        return sorted(m.split("[", 1)[1].split("]", 1)[0] for m in got.errors + got.warnings)

    assert codes_of(clam()) == []
    bad_hinge = clam()
    halves_of(bad_hinge)["lid"]["hinge"] = "front"              # on the seam's own axis
    assert codes_of(bad_hinge) == ["L200"]
    bad_angle = clam()
    halves_of(bad_angle)["lid"]["angle"] = 200.0
    assert codes_of(bad_angle) == ["L200"]
    bad_sum = clam()
    halves_of(bad_sum)["lid"]["stands"] = 10.0
    assert codes_of(bad_sum) == ["L203"]
    bad_region = clam()
    bad_region["views"]["open"]["regions"][0]["half"] = "middle"
    assert codes_of(bad_region) == ["L201", "L201"]


# --- the lock treats the combination as stated ----------------------------------------------

def _bump(old, new):
    return dl.required_bump(dl.entry(old), dl.entry(new))


def _without_halves():
    doc = device()
    del doc["chassis"]["halves"]
    for view in doc["views"].values():
        view.pop("regions", None)
    return doc


def test_stating_halves_on_a_released_section_device_is_a_minor():
    assert _bump(_without_halves(), device()) == "minor"


def test_the_lock_records_the_halves_of_a_section_device():
    entry = dl.entry(device())
    # the geometry the lock holds apart is `outer` and `hinge`; `stands` and `angle` are hashed with the surface
    assert entry["halves"]["geometry"] == {"base": {"outer": "top"}, "lid": {"hinge": "rear"}}


def test_the_lock_hash_of_the_stands_is_unchanged_by_the_section():
    """`halves.stands` is hashed with the surface as before: moving it is a patch, whatever the
    device also states."""
    moved = device()
    halves_of(moved)["base"]["stands"] = 146.0
    assert _bump(device(), moved) == "patch"
    assert dl.buckets(device())["surface"] != dl.buckets(moved)["surface"]
    assert dl.buckets(device())["shape"] == dl.buckets(moved)["shape"]


def test_a_section_that_moves_the_widest_line_off_the_seam_is_a_major():
    """The flange is the widest part and the seam is in it. Moving the flange is a change to the
    section, which is shape class, and that is a major with halves or without them."""
    moved = device()
    pts = moved["chassis"]["section"]
    pts[2], pts[3], pts[4], pts[5] = [250.0, 60.0], [281.0, 60.0], [281.0, 83.0], [253.0, 83.0]
    pts[10], pts[11] = [0.0, 60.0], [14.0, 60.0]
    pts[9] = [0.0, 83.0]
    assert _bump(device(), moved) == "major"


def test_a_change_to_outer_or_hinge_is_still_a_major():
    moved = device()
    halves_of(moved)["lid"]["hinge"] = "front"
    assert _bump(device(), moved) == "major"
    moved = device()
    halves_of(moved)["base"]["outer"] = "bottom"
    assert _bump(device(), moved) == "major"

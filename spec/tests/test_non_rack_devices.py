"""A ceiling mount, and a powered device's PoE standard and draw.

The library could say what a switch hands out over PoE and could not describe
the box at the other end of the cable. `chassis.mount` had no value for a
ceiling, and nothing stated, as numbers, which 802.3 standard a powered device
needs or the most it takes in. This module holds what is now true of the
library: the schema's `ceiling` value and its four `poe-pd-*` keys, the lint
rule that relates them, what the DCIM exports say, and the two ReadyLinks
access points that are the first devices to use them.
"""
import copy
import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())

from portrayal import comparable        # noqa: E402
from portrayal import dcim_export as dx  # noqa: E402
from portrayal import lint              # noqa: E402

WALL_PLATE = "ipc-apwf6-poe-wp"
CEILING = "ipc-apwf7-poe-cl"
DEVICES = (WALL_PLATE, CEILING)
PD_KEYS = ("poe-pd-standard", "poe-pd-standard-min", "poe-pd-class", "poe-pd-max-w")
STANDARDS = ["802.3af", "802.3at", "802.3bt"]


def _device(name):
    return yaml.safe_load((LIB / "devices/readylinks" / name / "device.yaml").read_text())


def _export(vendor, name):
    model = name.upper()
    path = LIB / "exports" / vendor / "device-types/ReadyLinks" / f"{model}.yaml"
    return yaml.safe_load(path.read_text())


def _power_properties():
    return SCHEMA["properties"]["attrs"]["properties"]["power"]["properties"]


# --- the schema ---------------------------------------------------------------

def test_the_schema_names_a_ceiling_mount():
    mount = SCHEMA["properties"]["chassis"]["properties"]["mount"]
    assert "ceiling" in mount["enum"]
    assert "`ceiling` is one that fixes to a ceiling or hangs below it" in mount["description"]


def test_the_schema_defines_the_four_pd_keys_as_values_a_tool_can_read():
    props = _power_properties()
    assert all(key in props for key in PD_KEYS)
    assert props["poe-pd-standard"]["enum"] == STANDARDS
    assert props["poe-pd-standard-min"]["enum"] == STANDARDS
    assert props["poe-pd-class"]["type"] == "integer"
    assert (props["poe-pd-class"]["minimum"], props["poe-pd-class"]["maximum"]) == (0, 8)
    assert props["poe-pd-max-w"]["type"] == "number"
    assert props["poe-pd-max-w"]["exclusiveMinimum"] == 0


@pytest.mark.parametrize("key,value", [
    ("poe-pd-standard", "802.3at PoE+"),
    ("poe-pd-standard-min", "af"),
    ("poe-pd-class", "4"),
    ("poe-pd-class", 9),
    ("poe-pd-max-w", "25 W"),
    ("poe-pd-max-w", 0),
])
def test_the_schema_refuses_a_pd_value_a_tool_could_not_read(key, value):
    power = {"poe-pd-standard": "802.3at", "poe-pd-max-w": 25}
    power[key] = value
    doc = {"attrs": {"power": power}}
    validator = Draft202012Validator(SCHEMA["properties"]["attrs"])
    assert list(validator.iter_errors(doc["attrs"]))


@pytest.mark.parametrize("name", DEVICES)
def test_each_access_point_validates_against_the_schema(name):
    errors = list(Draft202012Validator(SCHEMA).iter_errors(_device(name)))
    assert not errors, [e.message for e in errors[:3]]


# --- the access points --------------------------------------------------------

def test_the_wall_plate_and_the_ceiling_unit_say_how_they_are_installed():
    assert _device(WALL_PLATE)["chassis"]["mount"] == "wall"
    assert _device(CEILING)["chassis"]["mount"] == "ceiling"
    for name in DEVICES:
        assert "ru" not in _device(name)["chassis"]


@pytest.mark.parametrize("name", DEVICES)
def test_a_tool_reads_each_access_points_standard_and_draw_as_numbers(name):
    power = _device(name)["attrs"]["power"]
    assert power["poe-pd-standard"] in STANDARDS
    assert STANDARDS.index(power["poe-pd-standard-min"]) < STANDARDS.index(power["poe-pd-standard"])
    for key in ("poe-pd-max-w", "poe-budget-w"):
        assert type(power[key]) in (int, float) and power[key] > 0, key
    assert "poe-pd-class" not in power, "neither data sheet prints a class"


def test_the_draw_that_is_the_whole_intake_is_never_below_what_the_unit_uses_and_hands_on():
    power = _device(CEILING)["attrs"]["power"]
    assert power["poe-pd-max-w"] == pytest.approx(power["power-self-max-w"] + power["poe-budget-w"])


@pytest.mark.parametrize("name", DEVICES)
def test_the_access_point_does_not_state_the_rack_fields_it_has_no_use_for(name):
    chassis = _device(name)["chassis"]
    assert not any(key in chassis for key in ("ru", "full-depth", "overhang", "ears", "kits"))


@pytest.mark.parametrize("vendor", ("netbox", "nautobot"))
@pytest.mark.parametrize("name", DEVICES)
def test_each_access_point_exports_as_a_box_that_takes_no_rack_unit(vendor, name):
    exported = _export(vendor, name)
    assert exported["u_height"] == 0
    assert exported["is_full_depth"] is False
    assert exported["manufacturer"] == "ReadyLinks"


@pytest.mark.parametrize("vendor", ("netbox", "nautobot"))
def test_the_export_comment_says_where_the_box_goes_and_what_it_needs(vendor):
    wall = _export(vendor, WALL_PLATE)["comments"]
    ceiling = _export(vendor, CEILING)["comments"]
    assert "Wall-mounted; not rack-mounted." in wall
    assert "Ceiling-mounted; not rack-mounted." in ceiling
    assert "PoE powered device: 802.3at (runs on 802.3af), at most 25 W at the PD input." in wall
    assert "PoE powered device: 802.3bt (runs on 802.3at), at most 72.95 W at the PD input." in ceiling


# --- the DCIM export ----------------------------------------------------------

def test_a_ceiling_box_exports_no_rack_units_and_says_so():
    assert dx.u_height({"mount": "ceiling"}) == 0.0
    assert dx.is_full_depth({"mount": "ceiling"}) is False
    assert dx.MOUNT_PROSE["ceiling"] == "Ceiling-mounted; not rack-mounted."


def test_the_pd_sentence_names_the_standard_the_floor_the_class_and_the_draw():
    power = {"poe-pd-standard": "802.3bt", "poe-pd-standard-min": "802.3at",
             "poe-pd-class": 6, "poe-pd-max-w": 60}
    comment = dx.comments_for({"attrs": {"power": power}}, "base", {})
    assert "PoE powered device: 802.3bt (runs on 802.3at), class 6, at most 60 W at the PD input." in comment


def test_a_box_that_states_no_pd_standard_gets_no_pd_sentence():
    assert "PoE powered device" not in dx.comments_for({"attrs": {"power": {"poe-budget-w": 120}}}, "base", {})


# --- the lint rule that relates the keys --------------------------------------

def _found(power):
    with lint.collecting() as found:
        lint.lint_device_poe_pd("device.yaml", {"attrs": {"power": power}})
    return ([m for m in found.errors if "[L199]" in m], [m for m in found.warnings if "[L199]" in m])


def test_L199_a_consistent_set_of_keys_is_quiet():
    assert _found({"poe-pd-standard": "802.3at", "poe-pd-standard-min": "802.3af",
                   "poe-pd-class": 4, "poe-pd-max-w": 25}) == ([], [])


def test_L199_the_floor_is_stated_with_the_standard_and_below_it():
    assert _found({"poe-pd-standard-min": "802.3af"})[0]
    assert _found({"poe-pd-standard": "802.3at", "poe-pd-standard-min": "802.3at"})[0]
    assert _found({"poe-pd-standard": "802.3at", "poe-pd-standard-min": "802.3bt"})[0]


def test_L199_a_class_is_stated_with_a_standard():
    assert _found({"poe-pd-class": 4})[0]


def test_L199_a_draw_with_no_standard_cannot_be_checked_against_a_port():
    errors, warnings = _found({"poe-pd-max-w": 25})
    assert not errors and warnings


def test_L199_the_intake_is_at_least_what_the_unit_uses_plus_what_it_hands_on():
    base = {"poe-pd-standard": "802.3bt", "power-self-max-w": 60, "poe-budget-w": 12.95}
    assert _found({**base, "poe-pd-max-w": 60})[1]
    assert not _found({**base, "poe-pd-max-w": 72.95})[1]
    # prose on either side is not a number and is not summed
    assert not _found({**base, "poe-budget-w": "12.95 W", "poe-pd-max-w": 60})[1]


def test_L199_a_box_that_gives_and_takes_poe_states_its_whole_intake():
    errors, warnings = _found({"poe-pd-standard": "802.3at", "poe-budget-w": 10})
    assert not errors and warnings
    assert not _found({"poe-pd-standard": "802.3at", "poe-budget-w": 10, "poe-pd-max-w": 25})[1]


def test_L199_is_in_the_catalogue_beside_the_others():
    assert "L199" in lint.RULES
    assert "PoE keys" in lint.RULES["L199"][1]


def test_L198_in_the_catalogue_is_still_the_airflow_rule():
    """The two rules never share a number: L198 is the airflow rule, L199 the PoE keys."""
    assert "airflow" in lint.RULES["L198"][1]
    assert "poe-pd" in lint.RULES["L199"][1]


def test_both_access_points_reach_the_highest_capability_level():
    import libdata
    from portrayal import capability
    profiles = capability.load_profiles(ROOT / "spec" / "schemas")
    levels = {}
    for _slug, f, d in libdata.library():
        if f.parent.parent.name == "readylinks" and f.parent.name in DEVICES:
            cap, _ = capability.assess(d, profiles=profiles)
            levels[f.parent.name] = (cap["level"], cap.get("blocked") or [])
    assert levels == {name: (4, []) for name in DEVICES}


@pytest.mark.parametrize("key", PD_KEYS)
def test_L28_a_module_states_no_pd_key(key):
    contract = {"kind": "module", "name": "m", "class": "line-card", "attrs": {key: 1}}
    with lint.collecting() as found:
        lint.lint_component_power("contract.yaml", contract)
    assert any("[L28]" in m and key in m for m in found.errors)


# --- L125 and the comparable facts --------------------------------------------

def test_L125_a_ceiling_box_states_no_rack_units():
    def l125(chassis):
        with lint.collecting() as found:
            lint.lint_device_mount("device.yaml", {"chassis": chassis})
        return [m for m in found.errors + found.warnings if "[L125]" in m]
    assert not l125({"mount": "ceiling"})
    assert l125({"mount": "ceiling", "ru": 1})
    assert l125({"mount": "ceiling", "full-depth": False})
    assert "ceiling" in lint.RULES["L125"][1]


def test_the_comparable_facts_read_the_standard_and_the_draw():
    facts = comparable.resolve(copy.deepcopy(_device(CEILING)))
    assert [r["value"] for r in facts["poe-pd-max-w"]["readings"]] == [72.95]
    assert [r["value"] for r in facts["poe-pd-standard"]["readings"]] == ["802.3bt"]


# --- the bodies ---------------------------------------------------------------
#
# Each unit is a solid with six faces, built from `chassis.bevel` (the wall plate's
# rounded edges) or `chassis.rounded` (the ceiling unit's large plan corners and its
# smaller face), and the face drawings are what that solid shows.

from portrayal import bevel                      # noqa: E402
from portrayal import render                     # noqa: E402

FACES = ("front", "rear", "left", "right", "top", "bottom")


def _solid(name):
    ch = _device(name)["chassis"]
    w, h, d = ch["width"], ch["height"], ch["depth"]
    return ch, bevel.solid(w, h, d, bevel.parse(ch))


def _area(polys, face):
    return sum(bevel._area(p["points"], p["normal"]) for p in polys if p["face"] == face)


def _svg(name, view):
    dev = _device(name)
    out = render.render_view(dev, view, dev["views"][view], render.Library([str(LIB)]), config={})
    return out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")


@pytest.mark.parametrize("name", DEVICES)
def test_each_body_has_all_six_faces_in_its_solid(name):
    ch, polys = _solid(name)
    for face in FACES:
        assert _area(polys, face) > 0, f"{name}: no {face} face in the solid"


@pytest.mark.parametrize("name", DEVICES)
def test_each_body_has_a_view_for_every_face_at_the_size_the_solid_draws(name):
    dev = _device(name)
    ch = dev["chassis"]
    for face in FACES:
        view = dev["views"][face]
        want = bevel.draw_size(face, ch["width"], ch["height"], ch["depth"])
        assert (view["size"]["w"], view["size"]["h"]) == want
        assert view.get("panel") or view.get("silkscreen") or view.get("empty")


@pytest.mark.parametrize("name", DEVICES)
def test_each_solid_is_closed_every_edge_shared_by_two_polygons(name):
    _, polys = _solid(name)
    seen = {}
    for poly in polys:
        pts = [tuple(round(c, 4) for c in p) for p in poly["points"]]
        for i, p in enumerate(pts):
            key = frozenset((p, pts[(i + 1) % len(pts)]))
            seen[key] = seen.get(key, 0) + 1
    assert set(seen.values()) == {2}


def test_the_wall_plate_edges_are_rounded_off_all_twelve():
    ch = _device(WALL_PLATE)["chassis"]
    assert sorted(bevel.parse(ch)) == bevel.EDGES
    # a body with its edges taken off is not a rectangle in any view
    for face in FACES:
        el = bevel.elevation(face, ch["width"], ch["height"], ch["depth"], bevel.parse(ch))
        assert not bevel.is_rectangle(el["outline"], *bevel.draw_size(
            face, ch["width"], ch["height"], ch["depth"]))


def test_the_ceiling_units_face_is_smaller_than_its_back():
    ch, polys = _solid(CEILING)
    assert _area(polys, "front") < _area(polys, "rear")
    taper = ch["rounded"]["taper"]
    assert taper["face"] == "front" and 0 < taper["inset"] < ch["rounded"]["radius"]
    front = bevel.elevation("front", ch["width"], ch["height"], ch["depth"], bevel.parse(ch))["flat"]
    assert max(p[0] for p in front) - min(p[0] for p in front) == pytest.approx(
        ch["width"] - 2 * taper["inset"], abs=0.01)


def test_the_ceiling_units_corner_radius_is_stated_and_the_corners_are_round():
    ch = _device(CEILING)["chassis"]
    assert ch["rounded"]["radius"] > 20
    rear = bevel.elevation("rear", ch["width"], ch["height"], ch["depth"], bevel.parse(ch))
    pts = rear["outline"]
    assert len(pts) > 20                             # an arc, not a square or a chamfer
    assert all(min(abs(x), abs(x - ch["width"])) > 1 or min(abs(y), abs(y - ch["height"])) > 1
               for x, y in pts)                      # no point sits on a square corner
    prov = _device(CEILING)["provenance"]["chassis-shape"]
    assert prov["confidence"] == "estimated"
    assert "radius" in prov["note"] and "taper" in prov["note"]


def test_the_ceiling_units_taper_and_radius_are_gaps_where_no_document_prints_them():
    gaps = {g["what"] for g in _device(CEILING)["gaps"]}
    assert {"corner-radius", "taper"} <= gaps


def test_the_ceiling_units_face_draws_its_ridges_wordmark_mark_and_slanted_lamp():
    front = _device(CEILING)["views"]["front"]
    refs = {p["id"]: p for p in front["components"]["placements"]}
    assert refs["ridges"]["ref"] == "readylinks/apwf7-ridges@1"
    assert refs["wifi-mark"]["ref"] == "readylinks/wifi-mark@1"
    assert refs["led-status"]["rotate"] not in (0, None)
    assert any(s["text"] == "ReadyLinks" for s in front["silkscreen"])
    svg = _svg(CEILING, "front")
    assert 'id="ridges"' in svg and 'id="wifi-mark"' in svg


def test_the_ceiling_units_front_is_drawn_as_the_tapered_outline():
    svg = _svg(CEILING, "front")
    assert 'id="chassis-bevels"' in svg
    assert svg.count("data-edge=") >= 36


@pytest.mark.parametrize("name,colour", [(WALL_PLATE, "#fcfcfc"), (CEILING, "#f9f9f8")])
def test_each_body_is_the_white_of_its_photograph_not_the_old_grey(name, colour):
    assert _device(name)["chassis"]["color"] == colour
    prov = _device(name)["provenance"]["chassis-colour"]
    assert prov["confidence"] == "photo-measured"


def test_the_wall_plates_poe_out_tag_is_blue_and_its_jacks_sit_in_a_dark_band():
    decor = _device(WALL_PLATE)["views"]["bottom"]["panel"]["decor"]
    fills = {d["fill"] for d in decor}
    assert "#1c60b7" in fills and "#131313" in fills


def test_the_wall_plates_wordmark_is_the_data_sheets_and_the_gap_says_the_photograph_differs():
    dev = _device(WALL_PLATE)
    assert [s["text"] for s in dev["views"]["front"]["silkscreen"]] == ["ReadyLinks"]
    note = dev["provenance"]["front-layout"]["note"]
    assert "data sheet" in note and "photograph" in note and "not the maker's logo" in note

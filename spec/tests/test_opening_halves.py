"""A box that opens in two halves: `chassis.halves` and `regions[].half`.

A node that mounts on a strand or a pedestal opens like a clamshell. The device
says so with a chassis-level `halves` mapping, a `base` that states its `outer`
face and a `lid` that states its `hinge` and `angle`, each with the depth it
`stands`, and with a `half` on the regions of the open drawing. A bay belongs to
the half of the one region whose box holds its centre. This module holds what is
now true of the format: the schema keys, the lint rules, what the lock asks for,
what the compiled drawing and `configs.json` carry, and what the DCIM export
says. The test device is `spec/tests/fixtures/halves`, a synthetic box, never a
library device.

Lint codes are read from `lint.HALVES_CODES`, so the numbers can change at merge
without touching this module.
"""
import copy
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml
from jsonschema import Draft202012Validator

import warmrender
from portrayal import dcim_export as dx
from portrayal import devicelock as dl
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FIXTURE_LIB = ROOT / "spec/tests/fixtures/halves/lib"
DEVICE = FIXTURE_LIB / "devices/fixture/clam/device.yaml"
RENDER = ROOT / "spec/tools/portrayal/render.py"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
SVG = "{http://www.w3.org/2000/svg}"


def device():
    """The fixture device, as a fresh document a test may edit."""
    return copy.deepcopy(yaml.safe_load(DEVICE.read_text()))


def halves_of(doc):
    return doc["chassis"]["halves"]


def region(doc, rid):
    return next(r for r in doc["views"]["open"]["regions"] if r["id"] == rid)


def bay(doc, bid):
    return next(b for b in doc["views"]["open"]["components"]["bays"] if b["id"] == bid)


def schema_errors(doc):
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(doc)]


def found(doc):
    """`{code: [message]}` over the errors and warnings of the halves rules."""
    from portrayal import lint as lint_mod
    with lint_mod.collecting() as got:
        lint_mod.lint_device_halves("device.yaml", doc)
    out = {}
    for m in got.errors + got.warnings:
        code = m.split("[", 1)[1].split("]", 1)[0]
        out.setdefault(code, []).append(m.split("] ", 1)[1])
    return out


def severity(doc, code):
    """('error' | 'warning') for the first finding of `code`, or None."""
    with lint.collecting() as got:
        lint.lint_device_halves("device.yaml", doc)
    if any(f"[{code}]" in m for m in got.errors):
        return "error"
    if any(f"[{code}]" in m for m in got.warnings):
        return "warning"
    return None


def codes():
    return lint.HALVES_CODES


# --- the schema ----------------------------------------------------------------------------

def test_the_fixture_validates():
    assert schema_errors(device()) == []


def test_the_schema_names_the_halves_and_the_region_key():
    chassis = SCHEMA["properties"]["chassis"]["properties"]
    assert "halves" in chassis
    half = chassis["halves"]["additionalProperties"]
    assert set(half["properties"]) == {"outer", "hinge", "angle", "stands"}
    region_props = SCHEMA["properties"]["views"]["additionalProperties"]["properties"]["regions"]["items"]["properties"]
    assert "half" in region_props


@pytest.mark.parametrize("edit", [
    lambda d: halves_of(d)["base"].update(outer="above"),     # not a face
    lambda d: halves_of(d)["lid"].update(hinge="up"),         # not a face
    lambda d: halves_of(d)["lid"].update(angle="wide"),       # not a number
    lambda d: halves_of(d)["lid"].update(stands="70 mm"),     # a number, not a string with a unit
    lambda d: halves_of(d)["lid"].update(spring=1.0),         # a key nobody defined
])
def test_a_half_that_is_not_made_of_faces_and_numbers_is_refused(edit):
    doc = device()
    edit(doc)
    assert schema_errors(doc)


def test_the_schema_leaves_the_ranges_to_lint():
    doc = device()
    halves_of(doc)["lid"]["angle"] = 400.0
    halves_of(doc)["base"]["stands"] = -3.0
    assert schema_errors(doc) == []


# --- lint ----------------------------------------------------------------------------------

def test_the_fixture_is_quiet():
    assert found(device()) == {}


def test_a_device_with_no_halves_is_quiet():
    doc = device()
    del doc["chassis"]["halves"]
    del doc["views"]["open"]["regions"]
    assert found(doc) == {}


def test_the_rules_are_in_the_catalogue():
    for code in set(codes().values()):
        assert code in lint.RULES, code
        assert lint.RULES[code][0] == "device"


def test_exactly_two_entries_named_base_and_lid():
    doc = device()
    halves_of(doc)["spare"] = {"stands": 5.0}
    assert codes()["halves"] in found(doc)
    doc = device()
    del halves_of(doc)["lid"]
    assert codes()["halves"] in found(doc)
    doc = device()
    halves_of(doc)["cover"] = halves_of(doc).pop("lid")
    assert codes()["halves"] in found(doc)


def test_the_base_states_its_outer_face():
    doc = device()
    del halves_of(doc)["base"]["outer"]
    assert codes()["halves"] in found(doc)


def test_the_lid_states_its_hinge():
    doc = device()
    del halves_of(doc)["lid"]["hinge"]
    assert codes()["halves"] in found(doc)


@pytest.mark.parametrize("hinge", ["front", "rear"])
def test_the_hinge_is_not_on_the_axis_the_halves_stack_along(hinge):
    """The base's outer face is the rear, so the halves stack front to rear and
    a hinge on the front or the rear would be a hinge on the seam's own plane."""
    doc = device()
    halves_of(doc)["lid"]["hinge"] = hinge
    assert codes()["halves"] in found(doc)


@pytest.mark.parametrize("hinge", ["left", "right", "top", "bottom"])
def test_a_hinge_on_a_side_of_the_seam_is_accepted(hinge):
    doc = device()
    halves_of(doc)["lid"]["hinge"] = hinge
    assert found(doc) == {}


def test_the_hinge_is_not_the_back_of_the_lid():
    """With the rear the base's outer face, the lid's back is the front."""
    doc = device()
    halves_of(doc)["lid"]["hinge"] = "front"
    messages = found(doc)[codes()["halves"]]
    assert any("back of the lid" in m for m in messages), messages


@pytest.mark.parametrize("angle,bad", [(0.0, False), (180.0, False), (110.0, False),
                                       (-1.0, True), (180.5, True)])
def test_the_angle_runs_from_0_to_180(angle, bad):
    doc = device()
    halves_of(doc)["lid"]["angle"] = angle
    assert (codes()["halves"] in found(doc)) is bad
    if bad:
        assert severity(doc, codes()["halves"]) == "error"


@pytest.mark.parametrize("half", ["base", "lid"])
@pytest.mark.parametrize("stands", [0.0, -5.0])
def test_stands_is_positive(half, stands):
    doc = device()
    halves_of(doc)[half]["stands"] = stands
    assert codes()["halves"] in found(doc)


def test_a_region_names_a_declared_half():
    doc = device()
    region(doc, "lid-half")["half"] = "cover"
    assert codes()["region"] in found(doc)
    assert severity(doc, codes()["region"]) == "error"


def test_a_region_names_no_half_where_the_device_declares_none():
    doc = device()
    del doc["chassis"]["halves"]
    assert codes()["region"] in found(doc)


def test_a_declared_half_no_region_uses_is_a_warning():
    """Both regions are the base's, so the lid is declared and owns nothing."""
    doc = device()
    region(doc, "lid-half")["half"] = "base"
    assert list(found(doc)) == [codes()["region"]]
    assert severity(doc, codes()["region"]) == "warning"


def test_a_region_that_states_a_half_has_a_box():
    doc = device()
    del region(doc, "lid-half")["size"]
    assert codes()["region"] in found(doc)


def test_a_bay_is_in_the_half_of_the_region_that_holds_its_centre():
    from portrayal import halves
    assert halves.bay_halves(device()) == {
        "open": {"lid-bay": "lid", "base-bay-a": "base", "base-bay-b": "base"}}


def test_the_centre_decides_not_the_corner():
    """A bay whose corner pokes into the other region is still in the half that
    holds its centre."""
    from portrayal import halves
    doc = device()
    bay(doc, "lid-bay")["at"] = [20.0, 70.0]     # 70..120 high: the centre, 95, is in the lid
    assert halves.bay_halves(doc)["open"]["lid-bay"] == "lid"
    assert found(doc) == {}


def test_a_bay_in_no_region_is_an_error():
    doc = device()
    bay(doc, "lid-bay")["at"] = [400.0, 30.0]    # out here it is in neither
    assert codes()["bay"] in found(doc)
    assert severity(doc, codes()["bay"]) == "error"


def test_a_bay_in_two_regions_is_an_error():
    doc = device()
    region(doc, "base-half")["at"] = [0.0, 100.0]     # overlaps the lid's region from 100 to 110
    bay(doc, "lid-bay")["at"] = [20.0, 80.0]          # centre at y = 105
    assert codes()["bay"] in found(doc)
    assert severity(doc, codes()["bay"]) == "error"


def test_a_view_with_no_half_region_judges_no_bay():
    doc = device()
    for r in doc["views"]["open"]["regions"]:
        del r["half"]
    del doc["chassis"]["halves"]
    assert found(doc) == {}


@pytest.mark.parametrize("stands,warns", [
    ((50.0, 70.0), False),       # exactly the 120 depth
    ((50.0, 71.5), False),       # 1.25 per cent over
    ((50.0, 75.0), True),        # 4 per cent over
    ((40.0, 70.0), True),        # 8 per cent short
])
def test_the_stands_sum_to_the_depth_within_the_tolerance(stands, warns):
    doc = device()
    halves_of(doc)["base"]["stands"], halves_of(doc)["lid"]["stands"] = stands
    assert (codes()["stands"] in found(doc)) is warns
    if warns:
        assert severity(doc, codes()["stands"]) == "warning"


def test_the_seam_axis_follows_the_base_outer_face():
    """An outer face on the left or right stacks the halves across the width."""
    doc = device()
    halves_of(doc)["base"]["outer"] = "left"
    halves_of(doc)["lid"]["hinge"] = "top"
    halves_of(doc)["base"]["stands"], halves_of(doc)["lid"]["stands"] = 80.0, 120.0
    assert codes()["stands"] not in found(doc)       # 200 wide
    halves_of(doc)["base"]["stands"], halves_of(doc)["lid"]["stands"] = 50.0, 70.0
    assert codes()["stands"] in found(doc)           # 120 against 200


def test_the_stands_are_not_judged_while_one_is_missing():
    doc = device()
    del halves_of(doc)["lid"]["stands"]
    assert codes()["stands"] not in found(doc)


# --- the lock ------------------------------------------------------------------------------

def _bump(old_doc, new_doc):
    return dl.required_bump(dl.entry(old_doc), dl.entry(new_doc))


def _without_halves():
    doc = device()
    del doc["chassis"]["halves"]
    for r in doc["views"]["open"]["regions"]:
        del r["half"]
    return doc


def test_every_key_of_a_half_is_classified_by_the_lock():
    """The guard `CHASSIS_SHAPE` and `CHASSIS_SURFACE` have, one level down: a
    fifth key of a half has to be sorted by whoever adds it."""
    half = SCHEMA["properties"]["chassis"]["properties"]["halves"]["additionalProperties"]
    keys = set(half["properties"])
    assert dl.HALF_GEOMETRY | dl.HALF_STATED == keys
    assert not (dl.HALF_GEOMETRY & dl.HALF_STATED)
    assert dl.HALF_GEOMETRY == {"outer", "hinge"}


def test_the_halves_are_a_chassis_key_the_lock_classifies():
    assert "halves" in (dl.CHASSIS_SHAPE | dl.CHASSIS_SURFACE)


def test_the_lock_sees_halves_on_the_entry_only_where_a_device_has_them():
    assert "halves" in dl.entry(device())
    assert "halves" not in dl.entry(_without_halves())


def test_a_device_with_no_halves_hashes_as_it_did():
    before = dl.buckets(_without_halves())
    assert set(before) == {"shape", "names", "surface", "placement-attrs", "placement-geometry",
                           "placement-surface", "gaps", "composed"}


def test_adding_halves_to_a_released_device_is_a_minor():
    assert _bump(_without_halves(), device()) == "minor"


def test_moving_a_stand_or_the_angle_is_a_patch():
    for edit in (lambda d: halves_of(d)["lid"].update(angle=95.0),
                 lambda d: halves_of(d)["base"].update(stands=52.0)):
        new = device()
        edit(new)
        assert _bump(device(), new) == "patch"


@pytest.mark.parametrize("edit", [
    lambda d: halves_of(d)["base"].update(outer="front"),
    lambda d: halves_of(d)["lid"].update(hinge="left"),
])
def test_changing_an_outer_face_or_a_hinge_is_a_major(edit):
    new = device()
    edit(new)
    assert _bump(device(), new) == "major"


def test_a_bay_that_changes_half_is_a_major_though_nothing_is_moved():
    """The two regions swap their halves: no bay and no box moves, and every bay
    is in the other half."""
    new = device()
    region(new, "lid-half")["half"], region(new, "base-half")["half"] = "base", "lid"
    assert dl.buckets(new)["shape"] == dl.buckets(device())["shape"]
    assert _bump(device(), new) == "major"


def test_a_region_that_gains_a_half_alone_is_a_patch():
    """A half stated on a region no bay sits in moves no bay."""
    old = device()
    old["views"]["open"]["regions"].append({"id": "margin", "at": [0.0, 110.0], "size": {"w": 200.0, "h": 10.0}})
    new = copy.deepcopy(old)
    region(new, "margin")["half"] = "base"
    assert _bump(old, new) == "patch"


def test_taking_the_halves_away_is_a_major():
    assert _bump(device(), _without_halves()) == "major"


def test_the_halves_do_not_enter_the_shape_digest_of_a_released_device():
    assert dl.buckets(device())["shape"] == dl.buckets(_without_halves())["shape"]


# --- the compiled drawing and configs.json ---------------------------------------------------

@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("halves-build")
    out = tmp / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(DEVICE), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


def _bay_groups(out, view="open"):
    root = ET.parse(out / f"clam.base.{view}.svg").getroot()
    return {g.get("id"): g for g in root.iter(f"{SVG}g") if g.get("data-class") == "bay"}


@pytest.mark.heavy
def test_the_bay_group_carries_its_half(built):
    groups = _bay_groups(built)
    assert {k: g.get("data-half") for k, g in groups.items()} == {
        "lid-bay": "lid", "base-bay-a": "base", "base-bay-b": "base"}


@pytest.mark.heavy
def test_a_view_with_no_half_region_draws_no_data_half(built):
    root = ET.parse(built / "clam.base.front.svg").getroot()
    assert not [e for e in root.iter() if e.get("data-half") is not None]


@pytest.mark.heavy
def test_configs_json_carries_the_halves_and_each_bays_half(built):
    cfg = json.loads((built / "clam.configs.json").read_text())
    assert cfg["chassis"]["halves"] == {"base": {"outer": "rear", "stands": 50.0},
                                        "lid": {"hinge": "top", "angle": 110.0, "stands": 70.0}}
    assert {b["id"]: b.get("half") for b in cfg["bays"]["open"]} == {
        "lid-bay": "lid", "base-bay-a": "base", "base-bay-b": "base"}
    assert all("half" not in b for b in cfg["bays"].get("front", []))


@pytest.mark.heavy
def test_a_device_with_no_halves_publishes_neither_key(built, tmp_path):
    doc = _without_halves()
    dev = tmp_path / "clam" / "device.yaml"
    dev.parent.mkdir()
    dev.write_text(yaml.safe_dump(doc, sort_keys=False))
    out = tmp_path / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(FIXTURE_LIB),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    cfg = json.loads((out / "clam.configs.json").read_text())
    assert "halves" not in cfg["chassis"]
    assert all("half" not in b for rows in cfg["bays"].values() for b in rows)
    assert not [e for e in ET.parse(out / "clam.base.open.svg").getroot().iter()
                if e.get("data-half") is not None]


def test_the_index_contract_stays_2():
    from portrayal import devices_index
    assert devices_index.CONTRACT == 2


# --- the DCIM export -----------------------------------------------------------------------

def _bay_rows():
    doc = device()
    cfg = doc["configurations"]["base"]
    return {b["position"]: b for b in dx.build(doc, "base", cfg, None)["module-bays"]}


def test_the_module_bay_description_names_the_half():
    rows = _bay_rows()
    assert rows["lid-bay"]["description"].startswith("In the lid. ")
    assert rows["base-bay-a"]["description"].startswith("In the base. ")
    assert rows["base-bay-b"]["description"].startswith("In the base. ")


def test_a_bay_of_a_device_with_no_halves_reads_as_it_did():
    doc = _without_halves()
    cfg = doc["configurations"]["base"]
    rows = {b["position"]: b for b in dx.build(doc, "base", cfg, None)["module-bays"]}
    assert rows["lid-bay"]["description"] == "Accepts: clam-card"

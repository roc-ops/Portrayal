"""#935: a rack is its own library product, `kind: rack`.

`library/racks/<vendor>/<name>/rack.yaml`, checked against
`spec/schemas/rack-product.schema.json` and versioned by a `rack.lock.json`
beside it, the way a listing is. These tests hold the schema (a good rack
passes; a missing key or an unknown form name fails), the walk that finds
racks and no other kind, the lock and the bump each change needs, and L193,
the rule a schema cannot state.

A rack product is not the Rack Builder's file: `rack.schema.json` stays what
it was.
"""
import copy
import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

from portrayal import devicelock, libwalk, lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA_FILE = ROOT / "spec/schemas/rack-product.schema.json"

GOOD = {
    "format": 1,
    "kind": "rack",
    "name": "frame-4p",
    "version": "1.0.0",
    "maturity": "modelled",
    "manufacturer": "Acme",
    "model": "FRAME-4P",
    "form": "4-post-frame",
    "ru": 42,
    "numbering": {"direction": "bottom-up", "start": 1},
    "width": 19,
    "holes": {"style": "square", "size": 9.5, "fixing": "M6"},
    "rails": [{"id": "front"}, {"id": "rear", "depth": {"fixed": 740}}],
    "max-device-depth": 740,
    "outer": {"w": 600, "h": 2000, "d": 747},
    "weight-kg": 40,
    "load": {"static-kg": 900},
    "provenance": {"ru": {"confidence": "datasheet", "note": "the sheet's rack unit row"}},
}


def validator():
    return Draft202012Validator(json.loads(SCHEMA_FILE.read_text()))


def errors(doc):
    return [e.message for e in validator().iter_errors(doc)]


def without(key):
    d = copy.deepcopy(GOOD)
    d.pop(key)
    return d


def with_(**kw):
    d = copy.deepcopy(GOOD)
    d.update(kw)
    return d


# ---- the schema ----------------------------------------------------------------

def test_the_schema_is_a_valid_published_schema():
    schema = json.loads(SCHEMA_FILE.read_text())
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == "https://portrayal.dev/schemas/v1/rack-product.schema.json"
    assert schema["properties"]["kind"] == {"const": "rack"}


def test_a_good_rack_passes():
    assert errors(GOOD) == []


@pytest.mark.parametrize("key", ["format", "kind", "name", "version", "maturity",
                                 "manufacturer", "model", "form", "ru", "numbering",
                                 "holes", "rails"])
def test_a_rack_missing_a_required_key_fails(key):
    assert errors(without(key)), key


def test_an_unknown_form_name_fails():
    assert errors(with_(form="four-post-open-frame"))
    assert errors(with_(form="4-post"))


@pytest.mark.parametrize("form", ["2-post-frame", "4-post-frame", "4-post-cabinet",
                                  "wall-frame", "wall-frame-vertical", "wall-cabinet",
                                  "wall-cabinet-vertical", "desktop-frame"])
def test_every_form_the_design_names_is_taken(form):
    assert errors(with_(form=form)) == []


def test_an_unknown_key_fails():
    assert errors(with_(colour="black"))


def test_the_width_is_one_of_the_four_nominal_rails():
    assert errors(with_(width=19)) == []
    assert errors(with_(width=24))


def test_tapped_holes_name_their_thread_and_square_holes_have_none():
    tapped = {"style": "tapped", "thread": "12-24"}
    assert errors(with_(holes=tapped)) == []
    assert errors(with_(holes={"style": "tapped"}))
    assert errors(with_(holes={"style": "tapped", "thread": "M4"}))
    assert errors(with_(holes={"style": "square", "thread": "M6"}))


def test_a_rail_depth_is_fixed_or_a_range_and_never_both():
    rng = {"min": 559, "max": 1016, "step": 25.4}
    ok = [{"id": "front"}, {"id": "rear", "depth": rng}]
    assert errors(with_(rails=ok)) == []
    both = [{"id": "front"}, {"id": "rear", "depth": {"fixed": 740, **rng}}]
    assert errors(with_(rails=both))
    assert errors(with_(rails=[{"id": "front"}, {"id": "rear", "depth": {}}]))


def test_a_name_and_a_version_have_the_shapes_a_device_gives_them():
    assert errors(with_(name="Frame 4P"))
    assert errors(with_(version="1.0"))
    assert errors(with_(ru=0))
    assert errors(with_(numbering={"direction": "sideways", "start": 1}))


def test_a_rack_that_is_not_in_the_design_yet_is_refused_rather_than_ignored():
    """Baying, options and the outside attachment points are not in the format yet.
    A key the schema does not know fails; it is never dropped silently."""
    for key in ("baying", "options", "points"):
        assert errors(with_(**{key: {}})), key


# ---- the walk --------------------------------------------------------------------

def test_a_rack_is_in_no_other_walk(tmp_path):
    d = tmp_path / "racks" / "acme" / "frame-4p"
    d.mkdir(parents=True)
    (d / "rack.yaml").write_text("format: 1\nkind: rack\n")
    assert libwalk.iter_racks([tmp_path]) == [d / "rack.yaml"]
    assert libwalk.rack_key(d / "rack.yaml") == "acme/frame-4p"
    assert libwalk.iter_devices([tmp_path]) == []
    assert libwalk.iter_listings([tmp_path]) == []
    assert libwalk.iter_components([tmp_path]) == []
    assert libwalk.iter_labs([tmp_path]) == []


def test_the_library_racks_are_found_in_order():
    racks = libwalk.iter_racks([LIB])
    assert racks and racks == sorted(racks)
    assert [libwalk.rack_key(r) for r in racks] == sorted(libwalk.rack_key(r) for r in racks)


# ---- the lock --------------------------------------------------------------------

def bump(**change):
    new = copy.deepcopy(GOOD)
    for k, v in change.items():
        new[k] = v
    return devicelock.rack_bump(devicelock.rack_entry(GOOD), devicelock.rack_entry(new))


def test_an_unchanged_rack_needs_no_bump():
    assert bump() is None


@pytest.mark.parametrize("change", [
    {"ru": 44},
    {"form": "2-post-frame"},
    {"numbering": {"direction": "top-down", "start": 1}},
    {"numbering": {"direction": "bottom-up", "start": 0}},
    {"width": 23},
    {"holes": {"style": "round", "size": 7}},
    {"rails": [{"id": "front"}, {"id": "rear", "depth": {"fixed": 800}}]},
    {"max-device-depth": 700},
])
def test_a_number_a_saved_rack_copies_is_major(change):
    assert bump(**change) == "major"


def test_a_rating_stated_where_there_was_none_is_minor_and_a_correction_a_patch():
    bare = copy.deepcopy(GOOD)
    bare.pop("load")
    added = devicelock.rack_bump(devicelock.rack_entry(bare), devicelock.rack_entry(GOOD))
    assert added == "minor"
    removed = devicelock.rack_bump(devicelock.rack_entry(GOOD), devicelock.rack_entry(bare))
    assert removed == "major", "a figure that goes away is not an addition"
    assert bump(load={"static-kg": 907}) == "patch"
    assert bump(**{"weight-kg": 41}) == "patch"


def test_hole_centres_stated_late_are_minor_and_changed_are_major():
    new = with_(**{"hole-centres": 465.1})
    assert devicelock.rack_bump(devicelock.rack_entry(GOOD), devicelock.rack_entry(new)) == "minor"
    moved = with_(**{"hole-centres": 465.1})
    again = with_(**{"hole-centres": 466})
    assert devicelock.rack_bump(devicelock.rack_entry(moved), devicelock.rack_entry(again)) == "major"


def test_prose_and_provenance_are_a_patch():
    assert bump(description="Open frame.") == "patch"
    assert bump(provenance={"ru": {"note": "reworded"}}) == "patch"
    assert bump(**{"part-numbers": {"X": "x"}}) == "patch"


def test_the_outer_box_is_a_statement_not_a_position():
    assert bump(outer={"w": 601, "h": 2000, "d": 747}) == "patch"


def write_rack(lib, doc=None, name="frame-4p"):
    import yaml
    d = lib / "racks" / "acme" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "rack.yaml").write_text(yaml.safe_dump(doc or GOOD, sort_keys=False))
    return d


def test_an_unlocked_rack_is_reported_and_update_records_it(tmp_path):
    d = write_rack(tmp_path)
    found = devicelock.check_racks(tmp_path)
    assert [f[1] for f in found] == ["unlocked"]
    assert devicelock.update_racks(tmp_path) == ["rack acme/frame-4p"]
    lock = json.loads((d / "rack.lock.json").read_text())
    assert lock["format"] == 1 and lock["version"] == "1.0.0"
    assert devicelock.check_racks(tmp_path) == []
    assert devicelock.update_racks(tmp_path) == [], "a second update has nothing to say"


def test_a_changed_rack_that_kept_its_version_is_unbumped(tmp_path):
    import yaml
    d = write_rack(tmp_path)
    devicelock.update_racks(tmp_path)
    (d / "rack.yaml").write_text(yaml.safe_dump(with_(ru=44), sort_keys=False))
    found = devicelock.check_racks(tmp_path)
    assert [f[1] for f in found] == ["unbumped"] and "major" in found[0][2]
    (d / "rack.yaml").write_text(yaml.safe_dump(with_(ru=44, version="1.1.0"), sort_keys=False))
    assert [f[1] for f in devicelock.check_racks(tmp_path)] == ["unbumped"], "minor is not enough"
    (d / "rack.yaml").write_text(yaml.safe_dump(with_(ru=44, version="2.0.0"), sort_keys=False))
    assert devicelock.check_racks(tmp_path) == []


def test_a_version_that_goes_backwards_is_reported(tmp_path):
    import yaml
    d = write_rack(tmp_path, with_(version="1.2.0"))
    devicelock.update_racks(tmp_path)
    (d / "rack.yaml").write_text(yaml.safe_dump(with_(version="1.1.0"), sort_keys=False))
    assert [f[1] for f in devicelock.check_racks(tmp_path)] == ["backwards"]


def test_a_removed_rack_leaves_a_lock_that_says_so(tmp_path):
    d = write_rack(tmp_path)
    devicelock.update_racks(tmp_path)
    (d / "rack.yaml").unlink()
    assert [f[1] for f in devicelock.check_racks(tmp_path)] == ["removed"]
    assert devicelock.update_racks(tmp_path) == ["rack acme/frame-4p (removed)"]
    assert not (d / "rack.lock.json").exists()


def test_the_main_check_reads_racks_too(tmp_path):
    write_rack(tmp_path)
    assert [f[1] for f in devicelock.check(tmp_path)] == ["unlocked"]
    assert devicelock.update(tmp_path) == ["rack acme/frame-4p"]
    assert devicelock.check(tmp_path) == []


def test_the_library_lock_agrees_with_its_racks():
    assert devicelock.check_racks(LIB) == []


def test_the_aggregate_lock_carries_the_racks(tmp_path):
    write_rack(tmp_path)
    devicelock.update_racks(tmp_path)
    out = tmp_path / "devices.lock.json"
    devicelock.aggregate(tmp_path, out)
    assert list(json.loads(out.read_text())["racks"]) == ["acme/frame-4p"]


# ---- L193 ------------------------------------------------------------------------

def findings(path, doc, roots=None):
    got = []
    real = lint.err
    lint.err = lambda p, rule, msg: got.append((rule, msg))
    try:
        lint.lint_rack(path, doc, [str(r) for r in (roots or [LIB])])
    finally:
        lint.err = real
    return got


def test_a_good_rack_passes_l193(tmp_path):
    assert findings(tmp_path / "racks/acme/frame-4p/rack.yaml", GOOD, [tmp_path]) == []


def test_a_four_post_frame_has_a_rear_rail_and_a_two_post_has_none(tmp_path):
    p = tmp_path / "racks/acme/frame-4p/rack.yaml"
    front_only = with_(rails=[{"id": "front"}])
    assert [r for r, _ in findings(p, front_only, [tmp_path])] == ["L193"]
    two = with_(form="2-post-frame", rails=[{"id": "front"}, {"id": "rear"}])
    assert [r for r, _ in findings(p, two, [tmp_path])] == ["L193"]
    ok = with_(form="2-post-frame", rails=[{"id": "front"}])
    assert findings(p, ok, [tmp_path]) == []


def test_the_directory_names_the_rack(tmp_path):
    got = findings(tmp_path / "racks/acme/other/rack.yaml", GOOD, [tmp_path])
    assert [r for r, _ in got] == ["L193"] and "frame-4p" in got[0][1]


def test_a_rack_does_not_take_a_devices_name_in_its_vendor(tmp_path):
    dev = tmp_path / "devices/acme/frame-4p"
    dev.mkdir(parents=True)
    (dev / "device.yaml").write_text("kind: device\n")
    got = findings(tmp_path / "racks/acme/frame-4p/rack.yaml", GOOD, [tmp_path])
    assert [r for r, _ in got] == ["L193"] and "device" in got[0][1]


def test_a_rail_depth_range_runs_from_less_to_more(tmp_path):
    p = tmp_path / "racks/acme/frame-4p/rack.yaml"
    backwards = with_(rails=[{"id": "front"},
                             {"id": "rear", "depth": {"min": 900, "max": 600, "step": 25}}])
    assert [r for r, _ in findings(p, backwards, [tmp_path])] == ["L193"]
    ok = with_(rails=[{"id": "front"},
                      {"id": "rear", "depth": {"min": 600, "max": 900, "step": 25}}])
    assert findings(p, ok, [tmp_path]) == []
    off = with_(rails=[{"id": "front"},
                       {"id": "rear", "depth": {"min": 600, "max": 900, "factory": 950}}])
    assert [r for r, _ in findings(p, off, [tmp_path])] == ["L193"], "the factory depth is in the range"


def test_a_rack_provenance_key_names_a_key_the_rack_has(tmp_path):
    p = tmp_path / "racks/acme/frame-4p/rack.yaml"
    stray = with_(provenance={"colour": {"note": "black"}})
    assert [r for r, _ in findings(p, stray, [tmp_path])] == ["L193"]


def test_an_estimate_is_a_declared_gap(tmp_path):
    p = tmp_path / "racks/acme/frame-4p/rack.yaml"
    guess = with_(provenance={"ru": {"confidence": "estimated", "note": "a stand-in"}})
    assert [r for r, _ in findings(p, guess, [tmp_path])] == ["L193"]
    declared = with_(provenance={"ru": {"confidence": "estimated", "note": "a stand-in"}},
                     gaps=[{"what": "ru", "reason": "vendor-silent", "wanted": "the sheet"}])
    assert findings(p, declared, [tmp_path]) == []


def test_l193_is_in_the_catalogue():
    assert "L193" in lint.RULES and lint.RULES["L193"][0] == "rack"
    assert lint.RULES["L193"][4] == "error"

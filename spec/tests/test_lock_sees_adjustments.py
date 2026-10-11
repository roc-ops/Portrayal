"""The lock records each adjustment with its members, at the bump each change needs.

docs/adjustable-positions-design.md section 9. `adjustments` is a top-level key
and `moves-with` a key of a placement, a bay and a decor entry. The lock as it
was would have recorded them badly in three ways, and each is held here:

- `moves-with` on a placement or a bay had to be sorted in the lock's key sets
  (test_lock_sees_placement_keys.py is that guard, and names the fourth set);
- decor is hashed whole in `surface`, a patch, so a decor member would have
  read as a patch whether it was added or dropped;
- no guard covered a new top-level key, so `adjustments` would have been
  hashed nowhere.

The table of section 9 is asked of the record: stating an adjustment, a wider
range, a stop or a member added is a minor; an id, a carrier, an axis, a
default, a narrower range, a stop or a member that changes or goes is a major;
`label`, `datum` and provenance are a patch.
"""
import copy
import json
import pathlib

import pytest

import adjustfixture as fx
from portrayal import devicelock as dl

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
AID = fx.AID


def bump(edit, base=None):
    before = base or fx.device()
    after = copy.deepcopy(before)
    edit(after)
    return dl.required_bump(dl.entry(before), dl.entry(after))


def plain():
    """The fixture as it would be with no adjustment stated: the same drawing."""
    doc = fx.device()
    del doc["adjustments"], doc["provenance"][AID]
    for view in doc["views"].values():
        for _kind, item in dl._adjust._items(view):
            item.pop("moves-with", None)
    for name in ("forward", "back"):
        del doc["configurations"][name]
    return doc


# --- the guards -------------------------------------------------------------------------

def test_every_top_level_key_is_sorted_by_whether_the_lock_reads_it():
    """THE GUARD for a new top-level key: whoever adds one says here whether
    the lock reads it, so it cannot land hashed nowhere without a word."""
    props = set(SCHEMA["properties"])
    assert props == dl.TOP_LEVEL_READ | dl.TOP_LEVEL_UNREAD
    assert not dl.TOP_LEVEL_READ & dl.TOP_LEVEL_UNREAD
    assert "adjustments" in dl.TOP_LEVEL_READ


def test_a_key_the_lock_says_it_reads_moves_the_lock():
    """The other half: a key in the read set that nothing reads is the hole
    the set exists to close. Each one, changed, changes the entry."""
    doc = fx.device()
    doc.update({"aliases": [{"name": "a", "kind": "vendor"}], "portfolio": {"family": "f"},
                "interfaces": [], "lint": {"waive": {"L13": "a reason"}}, "gaps": [],
                "stack-exceptions": {"x": "y"}})
    was = dl.entry(doc)
    shaped = {
        "version": lambda d: d.update(version="9.9.9"),
        "maturity": lambda d: d.update(maturity="modelled"),
        "description": lambda d: d.update(description="another"),
        "profile": lambda d: d.update(profile="networking"),
        "adjustments": lambda d: d["adjustments"][AID].update(default=61.0),
        "chassis": lambda d: d["chassis"].update(width=121.0),
        "views": lambda d: d["views"]["front"]["size"].update(w=121.0),
        "configurations": lambda d: d["configurations"].pop("back"),
        "groups": lambda d: d["groups"].pop("studs"),
        "interfaces": lambda d: d.update(
            interfaces=[{"physical": "panel", "name": "p0"}]),
    }
    for key in sorted(dl.TOP_LEVEL_READ):
        other = copy.deepcopy(doc)
        shaped.get(key, lambda d: d.update({key: {"changed": True}}))(other)
        assert dl.entry(other) != was, key


def test_the_record_names_each_adjustment_and_its_members():
    e = dl.entry(fx.device())
    assert e["adjustments"] == {AID: {
        "axis": "z", "carrier": "panel", "default": 60, "range": [20, 180],
        "stops": {"front": 20, "middle": 100, "rear": 180},
        "members": ["bottom/decor/panel", "bottom/decor/rail", "front/placements/panel",
                    "front/placements/rail", "left/decor/flange", "left/placements/stud",
                    "right/decor/flange", "right/placements/stud", "top/decor/panel",
                    "top/decor/rail"]}}


def test_a_device_with_no_adjustment_learns_no_key():
    """So no library lock moves for the lock learning about adjustments."""
    e = dl.entry(plain())
    assert "adjustments" not in e
    doc = plain()
    assert dl._decor(doc) == {v: ((w or {}).get("panel") or {}).get("decor")
                             for v, w in doc["views"].items()}


def test_decor_membership_is_out_of_the_surface_hash():
    """`surface` is a patch. A decor member added or dropped must not be
    judged there: the same decor with and without `moves-with` hashes alike."""
    with_members = fx.device()
    without = fx.device()
    for view in without["views"].values():
        for d in (view.get("panel") or {}).get("decor") or []:
            d.pop("moves-with", None)
    assert dl._decor(with_members) == dl._decor(without)
    assert any("moves-with" in d for v in with_members["views"].values()
               for d in (v.get("panel") or {}).get("decor") or [])


# --- the table of section 9 -------------------------------------------------------------

def test_stating_an_adjustment_at_the_position_drawn_is_a_minor():
    stated = fx.device()
    for name in ("forward", "back"):
        del stated["configurations"][name]
    assert dl.required_bump(dl.entry(plain()), dl.entry(stated)) == "minor"


MINOR = {
    "a wider range": lambda d: d["adjustments"][AID].update(range=[10.0, 190.0]),
    "a stop added": lambda d: d["adjustments"][AID]["stops"].update(near=40.0),
    "a placement member added": lambda d: fx.placement(d, "left", "side-left").update(
        {"moves-with": AID}),
    "a decor member added": lambda d: fx.decor(d, "rear", "panel-back").update(
        {"moves-with": AID}),
    "a second adjustment": lambda d: (
        d["adjustments"].update(lid={"label": "Lid", "carrier": "side-left", "axis": "y",
                                     "range": [0.0, 5.0], "default": 0.0, "datum": "the lid"}),
        fx.placement(d, "left", "side-left").update({"moves-with": "lid"})),
}
MAJOR = {
    "an id renamed": lambda d: d["adjustments"].update(setback=d["adjustments"].pop(AID)),
    "an id removed": lambda d: d.pop("adjustments"),
    "the carrier changed": lambda d: d["adjustments"][AID].update(carrier="rail"),
    "the axis changed": lambda d: d["adjustments"][AID].update(axis="x"),
    "the default changed": lambda d: d["adjustments"][AID].update(default=61.0),
    "a narrower range, at the top": lambda d: d["adjustments"][AID].update(range=[20.0, 170.0]),
    "a narrower range, at the bottom": lambda d: d["adjustments"][AID].update(range=[30.0, 180.0]),
    "the range taken away": lambda d: d["adjustments"][AID].pop("range"),
    "a stop removed": lambda d: d["adjustments"][AID]["stops"].pop("middle"),
    "a stop renamed": lambda d: d["adjustments"][AID]["stops"].update(
        back=d["adjustments"][AID]["stops"].pop("rear")),
    "a stop moved": lambda d: d["adjustments"][AID]["stops"].update(middle=90.0),
    "a placement member dropped": lambda d: fx.placement(d, "left", "stud").pop("moves-with"),
    "a decor member dropped": lambda d: fx.decor(d, "top", "rail").pop("moves-with"),
    "a member moved to another adjustment": lambda d: (
        d["adjustments"].update(lid={"label": "Lid", "carrier": "stud", "axis": "y",
                                     "range": [0.0, 5.0], "default": 0.0, "datum": "the lid"}),
        fx.placement(d, "left", "stud").update({"moves-with": "lid"})),
}
PATCH = {
    "the label": lambda d: d["adjustments"][AID].update(label="Setback of the panel"),
    "the datum": lambda d: d["adjustments"][AID].update(datum="the rear face of the panel"),
    "the provenance": lambda d: d["provenance"][AID].update(note="read again"),
}


@pytest.mark.parametrize("name", MINOR)
def test_a_minor(name):
    assert bump(MINOR[name]) == "minor"


@pytest.mark.parametrize("name", MAJOR)
def test_a_major(name):
    assert bump(MAJOR[name]) == "major"


@pytest.mark.parametrize("name", PATCH)
def test_a_patch(name):
    assert bump(PATCH[name]) == "patch"


def test_a_respelling_is_no_change():
    """The lock's first rule: 60 and 60.0 are one position."""
    def edit(d):
        d["adjustments"][AID].update(default=60, range=[20, 180])
    assert bump(edit) is None


def test_stops_alone_given_a_range_is_a_minor():
    base = fx.device()
    del base["adjustments"][AID]["range"]
    assert bump(lambda d: d["adjustments"][AID].update(range=[20.0, 180.0]), base) == "minor"


def test_the_lock_asks_no_library_device_for_a_bump():
    """Step 1's gate: the lock learning these keys moves no committed lock."""
    assert dl.check(fx.LIB) == []

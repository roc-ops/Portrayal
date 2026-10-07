"""Every key a placement can state is fingerprinted, at the bump it deserves.

Thirteen keys of a placement - `states`, `description`, `provenance`,
`physical-context`, `interfaces`, `optional`, `lift`, `under`, `in`, `inset`,
`frames`, `only-in`, `for` - and `rel-pos` beside them were hashed nowhere, so
editing any one made `required_bump` return None. `rel-pos` alone is stated
11,522 times across the library.

They are fingerprinted under three keys of their own - `placement-geometry`
(major), `placement-addressing` (major when a value changes or goes; stating a
`for` where there was none is a minor and a `rel-pos` nothing) and
`placement-surface` (patch) - each read only when the old lock has it, the
migration #522 used for `placement-attrs`.

The five keys only a bay states - `opening`, `floor`, `plan`, `rear` and
`interface` - were then still hashed nowhere. The first four are geometry and
`interface` is addressing (major when changed or dropped, minor when stated
where there was none), under the same three keys.
"""
import copy
import json
import pathlib

import pytest
import yaml

from portrayal import devicelock as dl

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "schemas" / "device.schema.json"
NEW = ("placement-geometry", "placement-addressing", "placement-surface")


def dev(version="1.0.0", **keys):
    pl = {"id": "port-1", "ref": "std/rj45@1", "at": [1, 1], "group": "ports",
          **keys}
    lamp = {"id": "led-1", "ref": "common/led-dot@1", "at": [5, 1]}
    return {
        "format": 1, "kind": "device", "name": "d", "version": version,
        "chassis": {"width": 100, "height": 40, "depth": 30},
        "groups": {"ports": {"term": "Port", "index-origin": 1}},
        "provenance": {"size": "a"},
        "gaps": [],
        "views": {"front": {"size": {"w": 100, "h": 40},
                            "components": {"placements": [pl, lamp]}}},
    }


def bump(before, after):
    return dl.required_bump(dl.entry(dev(**before)), dl.entry(dev(**after)))


def old_lock(doc):
    """A lock written before the three keys existed."""
    return {k: v for k, v in dl.entry(doc).items() if k not in NEW}


def _properties(kind):
    schema = json.loads(SCHEMA.read_text())
    comps = schema["properties"]["views"]["additionalProperties"][
        "properties"]["components"]["properties"]
    return set(comps[kind]["items"]["properties"])


SORTED = (dl.PLACEMENT_GEOMETRY, dl.PLACEMENT_ADDRESSING, dl.PLACEMENT_SURFACE)


def test_the_sets_are_exhaustive_over_the_schema():
    """THE GUARD. A placement key the schema gains has to be sorted into one of
    these by whoever adds it, rather than land hashed nowhere - which is how
    thirteen of them did."""
    sets = (dl.PLACEMENT_HASHED,) + SORTED
    assert _properties("placements") <= set().union(*sets)
    # ...and no key is in two, so no key has two bumps.
    assert sum(len(s) for s in sets) == len(set().union(*sets))


def test_the_sets_are_exhaustive_over_the_bay_schema():
    """THE SAME GUARD FOR A BAY, which is how the five keys only a bay states
    were found hashed nowhere after the placement keys were sorted."""
    sets = (dl.BAY_HASHED,) + SORTED
    assert _properties("bays") <= set().union(*sets)
    assert sum(len(s) for s in sets) == len(set().union(*sets))


def test_every_sorted_key_is_one_the_schema_has():
    """The other half of exhaustive: a key dropped from the schema must leave
    the sets too, or the guard above passes over a name nothing states."""
    assert set().union(*SORTED) <= \
        _properties("placements") | _properties("bays")
    assert dl.PLACEMENT_HASHED <= _properties("placements")
    assert dl.BAY_HASHED <= _properties("bays")


GEOMETRY = [
    ({}, {"inset": 2}),
    ({"inset": 2}, {"inset": 3}),
    ({}, {"lift": 1.5}),
    ({}, {"in": "well"}),
    ({}, {"under": ["lid"]}),
    ({"under": "lid"}, {"under": ["lid", "shroud"]}),
    ({}, {"only-in": ["ac"]}),
    ({"only-in": ["ac"]}, {}),
    ({}, {"optional": "ears"}),
    ({}, {"interfaces": ["port-1a", "port-1b"]}),
    ({"interfaces": ["a", "b"]}, {"interfaces": ["a", "c"]}),
]


@pytest.mark.parametrize("before, after", GEOMETRY)
def test_geometry_is_a_major(before, after):
    """Where the part sits in depth, whether it is drawn, and - for
    `interfaces` - which interfaces the DCIM export names in its place: each
    invalidates something a consumer cached, even when only added."""
    assert bump(before, after) == "major"


SURFACE = [
    ({}, {"states": [{"name": "link", "color": "green"}]}),
    ({}, {"description": "Blue = 100G, Green = 40G"}),
    ({"description": "Blue = 100G"}, {"description": "Blue = 100G, Green = 40G"}),
    ({}, {"provenance": {"at": "hig p12"}}),
    ({}, {"physical-context": "NetworkingDevice"}),
    ({}, {"frames": ["led-1"]}),
]


@pytest.mark.parametrize("before, after", SURFACE)
def test_surface_is_a_patch(before, after):
    assert bump(before, after) == "patch"
    assert bump(after, before) == "patch"


def test_binding_where_there_was_nothing_is_additive():
    """The case `_placement_groups` draws: nothing could have been held by a
    value that was not there."""
    assert bump({}, {"for": "led-1"}) == "minor"


def test_stating_a_rel_pos_where_there_was_none_asks_for_nothing():
    """The ruling test_device_versioning.py holds for the eight-chassis
    backfill, kept: numbering an unnumbered part needs no version. The lock
    still records it, so renumbering it later does."""
    assert bump({}, {"rel-pos": 1}) is None


@pytest.mark.parametrize("before, after", [
    ({"rel-pos": 1}, {"rel-pos": 2}),       # renumbered
    ({"for": "led-1"}, {"for": "port-2"}),  # rebound
    ({"rel-pos": 1}, {}),                   # unstated
    ({"for": "led-1"}, {"for": ["led-1", "port-2"]}),
])
def test_changing_or_removing_an_address_is_a_major(before, after):
    assert bump(before, after) == "major"


@pytest.mark.parametrize("before, after", [
    ({"for": "led-1"}, {"for": ["led-1"]}),
    ({"for": ["a", "b"]}, {"for": ["b", "a"]}),
    ({"under": "lid"}, {"under": ["lid"]}),
    ({"only-in": ["ac", "dc"]}, {"only-in": ["dc", "ac"]}),
    ({"frames": "led-1"}, {"frames": ["led-1"]}),
])
def test_respelling_a_set_is_not_a_change(before, after):
    """One id or a list of one, in any order, names the same set - and a
    change of spelling is not a change."""
    assert bump(before, after) is None


@pytest.mark.parametrize("key, value, other", [
    ("fed-by", "input-a", "input-b"),
    ("through", "breaker-a1", "breaker-a2"),
])
def test_an_outlets_feed_and_position_are_addressing(key, value, other):
    """#806. `fed-by` and `through` are written into the DCIM export, as the
    outlet's `power_port` and its description: stating one adds to what an
    import holds (minor), and changing or dropping one re-files an outlet a
    DCIM already holds (major)."""
    assert bump({}, {key: value}) == "minor"
    assert bump({key: value}, {key: other}) == "major"
    assert bump({key: value}, {}) == "major"
    assert bump({key: value}, {key: value}) is None


def test_interfaces_keep_their_order():
    """The DCIM export emits interfaces in the order written."""
    assert bump({"interfaces": ["a", "b"]}, {"interfaces": ["b", "a"]}) == "major"


def test_a_removed_placement_is_judged_by_ids_not_twice():
    """A placement that is gone takes its `rel-pos` with it; `ids` already
    says major, and the addressing check must not read the absence as its own
    finding (or crash on it)."""
    old = dl.entry(dev(**{"rel-pos": 1}))
    doc = dev()
    doc["views"]["front"]["components"]["placements"].pop(0)
    assert dl.required_bump(old, dl.entry(doc)) == "major"


def test_the_largest_demand_wins():
    """A surface patch beside a geometry major is still a major, one beside an
    additive binding is a minor, and a new `rel-pos` adds nothing to either."""
    assert bump({}, {"inset": 1, "description": "x"}) == "major"
    assert bump({}, {"for": "led-1", "description": "x"}) == "minor"
    assert bump({}, {"rel-pos": 1, "description": "x"}) == "patch"


def test_a_bay_states_them_too():
    """The walk covers bays, which share `for`, `rel-pos`, `in`, `under`,
    `only-in` and `physical-context` with a placement."""
    assert dl.required_bump(with_bay(), with_bay(**{"only-in": ["ac"]})) == "major"
    assert dl.required_bump(with_bay(**{"rel-pos": 1}),
                            with_bay(**{"rel-pos": 2})) == "major"
    assert dl.required_bump(with_bay(), with_bay(
        **{"physical-context": "PowerSupply"})) == "patch"


def _bay_doc(**keys):
    doc = dev()
    doc["views"]["front"]["components"]["bays"] = [
        {"id": "slot-1", "at": [50, 1], "size": {"w": 10, "h": 10}, **keys}]
    return doc


def with_bay(**keys):
    return dl.entry(_bay_doc(**keys))


PLAN = {"view": "top", "at": [10, 20]}
REAR = {"view": "rear", "at": [5, 5], "cutout": "window-1"}
BAY_GEOMETRY = [
    ({}, {"opening": {"w": 8, "h": 8}}),
    ({"opening": {"w": 8, "h": 8}}, {"opening": {"w": 8, "h": 7}}),
    ({"in": "well"}, {"in": "well", "floor": 26.6}),
    ({"in": "well", "floor": 26.6}, {"in": "well", "floor": 44.8}),
    ({}, {"plan": PLAN}),
    ({"plan": PLAN}, {"plan": {**PLAN, "at": [11, 20]}}),
    ({"plan": PLAN}, {"plan": {**PLAN, "mirror": True}}),
    ({"plan": PLAN}, {"plan": {**PLAN, "rotate": 180}}),
    ({}, {"rear": REAR}),
    ({"rear": REAR}, {"rear": {**REAR, "cutout": "window-2"}}),
    ({"rear": REAR}, {}),
]


@pytest.mark.parametrize("before, after", BAY_GEOMETRY)
def test_bay_geometry_is_a_major(before, after):
    """The hole that is punched, the shelf the occupant stands on, and where
    it is projected on another face: each is a coordinate a consumer holds."""
    assert dl.required_bump(with_bay(**before), with_bay(**after)) == "major"


def test_a_plans_under_is_a_set_too():
    before = {"plan": {**PLAN, "under": ["lid", "shroud"]}}
    after = {"plan": {**PLAN, "under": ["shroud", "lid"]}}
    assert dl.required_bump(with_bay(**before), with_bay(**after)) is None


def test_a_bay_interface_is_addressing():
    """Opening a slot to an interface admits occupants, as `accepts` growing
    does; changing or dropping it withdraws the ones it admitted."""
    assert dl.required_bump(with_bay(), with_bay(interface="pcie")) == "minor"
    assert dl.required_bump(with_bay(interface="pcie"),
                            with_bay(interface="ocp3")) == "major"
    assert dl.required_bump(with_bay(interface="pcie"), with_bay()) == "major"


def test_a_bay_key_moves_only_its_own_lock_key():
    """`opening`, `floor`, `plan` and `rear` each move `placement-geometry`
    and nothing else; `interface` moves `placement-addressing` and nothing
    else."""
    a = with_bay()
    for keys, moved in (({"opening": {"w": 8, "h": 8}}, "placement-geometry"),
                        ({"floor": 26.6}, "placement-geometry"),
                        ({"plan": PLAN}, "placement-geometry"),
                        ({"rear": REAR}, "placement-geometry"),
                        ({"interface": "pcie"}, "placement-addressing")):
        b = with_bay(**keys)
        assert [k for k in a if a[k] != b[k]] == [moved]


BAY_ONLY_SORTED = ((dl.PLACEMENT_GEOMETRY | dl.PLACEMENT_ADDRESSING)
                   & _properties("bays")) - _properties("placements")
# A DISTINCT, SCHEMA-TYPED VALUE FOR EVERY KEY `BAY_HASHED` LISTS AS ALREADY
# READ, plus the bay-only geometry/addressing keys `_placement_keys` reads via
# PLACEMENT_GEOMETRY/PLACEMENT_ADDRESSING. `test_bay_hashed_keys_cover_the_sets`
# below guards this dict against drifting from either set.
BAY_KEY_VALUES = {
    "id": "slot-2", "at": [60, 2], "size": {"w": 12, "h": 10},
    "rotate": 90, "mirror": True, "default": "std/rj45@1",
    "accepts": ["std/rj45@1"], "group": "widgets",
    "opening": {"w": 8, "h": 8}, "floor": 26.6, "plan": PLAN, "rear": REAR,
    "interface": "pcie",
}


def test_bay_hashed_keys_cover_the_sets():
    """Guards `BAY_KEY_VALUES`: a key added to `BAY_HASHED`, or to the
    bay-only keys among PLACEMENT_GEOMETRY/PLACEMENT_ADDRESSING, without a
    value added here would make the parametrised test below silently skip
    it rather than fail loud."""
    assert dl.BAY_HASHED | BAY_ONLY_SORTED == set(BAY_KEY_VALUES)


@pytest.mark.parametrize("key", sorted(BAY_KEY_VALUES))
def test_a_bay_hashed_key_moves_the_entry(key):
    """THE GUARD `test_the_sets_are_exhaustive_over_the_bay_schema` PROVES ONLY
    HALF OF: that every bay property is sorted into one of these sets, not
    that the sorting is true. `BAY_HASHED` claims `_placements`,
    `_placement_groups` and `_bay_accepts` already read its eight keys, and
    `opening`, `floor`, `plan`, `rear` and `interface` are claimed hashed via
    PLACEMENT_GEOMETRY/PLACEMENT_ADDRESSING. Setting one key alone must move
    `dl.entry()` - proving the claim - or a key sorted into a bucket nothing
    actually reads ships silent, which is how `floor` sat unread for a time
    (see the reverted experiment noted in the PR)."""
    assert with_bay(**{key: BAY_KEY_VALUES[key]}) != with_bay()


def test_the_old_buckets_do_not_move():
    """THE MIGRATION, half one: none of these keys is folded into `shape`,
    `names` or `surface`, so no device's existing digest moved."""
    a, b = dl.buckets(dev()), dl.buckets(dev(inset=2, description="x"))
    for key in ("shape", "names", "surface", "placement-attrs", "gaps"):
        assert a[key] == b[key], key


def test_an_unchanged_device_under_an_old_lock_is_not_a_finding():
    """THE MIGRATION, half two: a lock without the keys has nothing to compare."""
    doc = dev(inset=2, description="x", **{"rel-pos": 1, "for": "led-1"})
    assert dl.required_bump(old_lock(doc), dl.entry(doc)) is None


def test_an_old_lock_still_sees_everything_else():
    doc = dev(inset=2)
    moved = copy.deepcopy(doc)
    moved["views"]["front"]["components"]["placements"][0]["at"] = [2, 1]
    assert dl.required_bump(old_lock(doc), dl.entry(moved)) == "major"


def test_each_key_is_guarded_on_its_own():
    """A lock that has one of the three keys is held to that one only."""
    doc = dev(inset=2)
    now = dl.entry(dev(inset=3))
    geometry_only = {k: v for k, v in dl.entry(doc).items()
                     if k not in ("placement-addressing", "placement-surface")}
    assert dl.required_bump(geometry_only, now) == "major"
    surface_only = {k: v for k, v in dl.entry(doc).items()
                    if k not in ("placement-geometry", "placement-addressing")}
    assert dl.required_bump(surface_only, now) is None


def _library(tmp_path, doc, lock_entry):
    lib = tmp_path / "library"
    d = lib / "devices" / "acme" / "d"
    d.mkdir(parents=True)
    (d / "device.yaml").write_text(yaml.safe_dump(doc))
    (d / dl.DEVICE_LOCK_NAME).write_text(
        json.dumps({"format": dl.FORMAT, **lock_entry}))
    return lib


@pytest.mark.parametrize("doc_fn, before, after, says, need", [
    (dev, {}, {"inset": 2}, "placement geometry", "major"),
    (dev, {"rel-pos": 1}, {"rel-pos": 2}, "placement addressing", "major"),
    (dev, {}, {"for": "led-1"}, "placement addressing", "minor"),
    (dev, {}, {"states": [{"name": "on"}]}, "placement surface", "patch"),
    # A BAY ROW, so `check()`'s wording naming `opening`/`floor`/`plan`/`rear`
    # (geometry) and `interface` (addressing) - added for the bay-only keys -
    # is exercised too, not just the placement wording above.
    (_bay_doc, {}, {"opening": {"w": 8, "h": 8}}, "placement geometry", "major"),
    (_bay_doc, {}, {"interface": "pcie"}, "placement addressing", "minor"),
])
def test_check_names_the_key(tmp_path, doc_fn, before, after, says, need):
    """A finding has to say where to look; `changed ()` sends the reader nowhere."""
    lib = _library(tmp_path, doc_fn(**after), dl.entry(doc_fn(**before)))
    findings = [f for f in dl.check(lib) if f[1] == "unbumped"]
    assert len(findings) == 1, dl.check(lib)
    assert says in findings[0][2]
    assert f"at least a {need} bump" in findings[0][2]


def test_check_is_quiet_on_an_old_lock_and_update_adds_the_keys(tmp_path):
    doc = dev(inset=2, **{"rel-pos": 1})
    lib = _library(tmp_path, doc, old_lock(doc))
    assert dl.check(lib) == []
    assert dl.update(lib) == ["acme/d"]
    lock = json.loads(dl.lock_path(lib, "acme/d").read_text())
    for key in NEW:
        assert lock[key] == dl.entry(doc)[key]
    # ...and from then on the keys are held to it.
    moved = copy.deepcopy(doc)
    moved["views"]["front"]["components"]["placements"][0]["inset"] = 3
    (lib / "devices" / "acme" / "d" / "device.yaml").write_text(yaml.safe_dump(moved))
    assert [k for _, k, _ in dl.check(lib)] == ["unbumped"]


def test_the_committed_locks_all_carry_the_keys():
    """Every device was re-locked when the keys landed, so the guard exempts
    no device in this library - it exists for locks written elsewhere."""
    lib = pathlib.Path(__file__).resolve().parents[2] / "library"
    locks = sorted(lib.glob("devices/*/*/" + dl.DEVICE_LOCK_NAME))
    assert locks, "no device locks found - the check measured nothing"
    for f in locks:
        missing = [k for k in NEW if k not in json.loads(f.read_text())]
        assert not missing, f"{f}: {missing}"

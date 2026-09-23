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


def _placement_properties():
    schema = json.loads(SCHEMA.read_text())
    comps = schema["properties"]["views"]["additionalProperties"][
        "properties"]["components"]["properties"]
    return set(comps["placements"]["items"]["properties"])


def test_the_sets_are_exhaustive_over_the_schema():
    """THE GUARD. A placement key the schema gains has to be sorted into one of
    these by whoever adds it, rather than land hashed nowhere - which is how
    thirteen of them did."""
    sets = (dl.PLACEMENT_HASHED, dl.PLACEMENT_GEOMETRY,
            dl.PLACEMENT_ADDRESSING, dl.PLACEMENT_SURFACE)
    assert set().union(*sets) == _placement_properties()
    # ...and no key is in two, so no key has two bumps.
    assert sum(len(s) for s in sets) == len(set().union(*sets))


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
    def with_bay(**keys):
        doc = dev()
        doc["views"]["front"]["components"]["bays"] = [
            {"id": "slot-1", "at": [50, 1], "size": {"w": 10, "h": 10}, **keys}]
        return dl.entry(doc)
    assert dl.required_bump(with_bay(), with_bay(**{"only-in": ["ac"]})) == "major"
    assert dl.required_bump(with_bay(**{"rel-pos": 1}),
                            with_bay(**{"rel-pos": 2})) == "major"
    assert dl.required_bump(with_bay(), with_bay(
        **{"physical-context": "PowerSupply"})) == "patch"


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


@pytest.mark.parametrize("before, after, says, need", [
    ({}, {"inset": 2}, "placement geometry", "major"),
    ({"rel-pos": 1}, {"rel-pos": 2}, "placement addressing", "major"),
    ({}, {"for": "led-1"}, "placement addressing", "minor"),
    ({}, {"states": [{"name": "on"}]}, "placement surface", "patch"),
])
def test_check_names_the_key(tmp_path, before, after, says, need):
    """A finding has to say where to look; `changed ()` sends the reader nowhere."""
    lib = _library(tmp_path, dev(**after), dl.entry(dev(**before)))
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

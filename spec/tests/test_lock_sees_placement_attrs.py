"""A placement's own `attrs` are fingerprinted, and a patch.

A group's `attrs` sat in `surface`, but the same facts stated one port at a time
- `speed`, `media`, `usb` - were hashed nowhere: `speed: 100m-1g` retyped as `1g`
on a placement made `required_bump` return None. Found on #519, which retyped the
speed vocabulary and had to patch-bump some sixty devices by hand so that one
version number never covered two contents.

The fingerprint is a key of its own, `placement-attrs`, rather than part of the
`surface` digest, and `required_bump` reads it only when the old lock has it. A
lock written before the key existed must not turn every device that carries
placement attrs into a finding at once.
"""
import copy
import json
import pathlib

import yaml

from portrayal import devicelock as dl


def dev(version="1.0.0", attrs=None):
    pl = {"id": "port-1", "ref": "std/rj45@1", "at": [1, 1], "group": "ports"}
    if attrs is not None:
        pl["attrs"] = attrs
    return {
        "format": 1, "kind": "device", "name": "d", "version": version,
        "chassis": {"width": 100, "height": 40, "depth": 30},
        "groups": {"ports": {"term": "Port", "index-origin": 1,
                             "attrs": {"media": "copper"}}},
        "provenance": {"size": "a"},
        "gaps": [],
        "views": {"front": {"size": {"w": 100, "h": 40},
                            "components": {"placements": [pl]}}},
    }


def test_retyping_a_placement_attr_is_a_patch():
    """The case from #519, at its smallest."""
    a = dl.entry(dev(attrs={"speed": "100m-1g"}))
    assert dl.required_bump(a, dl.entry(dev(attrs={"speed": "1g"}))) == "patch"


def test_adding_or_removing_a_placement_attr_is_a_patch():
    bare, stated = dl.entry(dev()), dl.entry(dev(attrs={"speed": "1g"}))
    assert dl.required_bump(bare, stated) == "patch"
    assert dl.required_bump(stated, bare) == "patch"


def test_a_placement_attr_is_neither_shape_nor_names():
    """A fact about the port, not where it is or what it is called - nothing a
    consumer cached as a coordinate or an address is now wrong."""
    a = dl.buckets(dev(attrs={"speed": "100m-1g"}))
    b = dl.buckets(dev(attrs={"speed": "1g"}))
    assert a["shape"] == b["shape"] and a["names"] == b["names"]
    assert a["placement-attrs"] != b["placement-attrs"]


def test_placement_attrs_leave_the_surface_digest_where_it_was():
    """THE MIGRATION, half one: folding the attrs into `surface` would rehash
    the surface of every device that carries them - 98 of 124 when this landed -
    so they are hashed beside it and the old digest does not move."""
    assert dl.buckets(dev())["surface"] == \
        dl.buckets(dev(attrs={"speed": "1g"}))["surface"]


def test_an_unchanged_device_under_an_old_lock_is_not_a_finding():
    """THE MIGRATION, half two: a lock written before the key existed has
    nothing to compare against, so its absence is not a change."""
    now = dl.entry(dev(attrs={"speed": "1g"}))
    old = {k: v for k, v in now.items() if k != "placement-attrs"}
    assert dl.required_bump(old, now) is None


def test_an_old_lock_still_sees_everything_else():
    """The guard exempts the new key and nothing more."""
    old = {k: v for k, v in dl.entry(dev(attrs={"speed": "1g"})).items()
           if k != "placement-attrs"}
    moved = dev(attrs={"speed": "1g"})
    moved["provenance"]["size"] = "b"
    assert dl.required_bump(old, dl.entry(moved)) == "patch"


def _library(tmp_path, doc, lock_entry):
    lib = tmp_path / "library"
    d = lib / "devices" / "acme" / "d"
    d.mkdir(parents=True)
    (d / "device.yaml").write_text(yaml.safe_dump(doc))
    (d / dl.DEVICE_LOCK_NAME).write_text(
        json.dumps({"format": dl.FORMAT, **lock_entry}))
    return lib


def test_check_names_the_placement_attrs(tmp_path):
    """A finding has to say where to look; `changed ()` sends the reader nowhere."""
    lib = _library(tmp_path, dev(attrs={"speed": "1g"}),
                   dl.entry(dev(attrs={"speed": "100m-1g"})))
    findings = dl.check(lib)
    assert [k for _, k, _ in findings] == ["unbumped"], findings
    assert "placement attrs" in findings[0][2]
    assert "at least a patch bump" in findings[0][2]


def test_check_is_quiet_on_an_old_lock_and_update_adds_the_key(tmp_path):
    doc = dev(attrs={"speed": "1g"})
    old = {k: v for k, v in dl.entry(doc).items() if k != "placement-attrs"}
    lib = _library(tmp_path, doc, old)
    assert dl.check(lib) == []
    assert dl.update(lib) == ["acme/d"]
    lock = json.loads(dl.lock_path(lib, "acme/d").read_text())
    assert lock["placement-attrs"] == dl.entry(doc)["placement-attrs"]
    # ...and from then on the attrs are held to it.
    moved = copy.deepcopy(doc)
    moved["views"]["front"]["components"]["placements"][0]["attrs"]["speed"] = "10g"
    (lib / "devices" / "acme" / "d" / "device.yaml").write_text(yaml.safe_dump(moved))
    assert [k for _, k, _ in dl.check(lib)] == ["unbumped"]

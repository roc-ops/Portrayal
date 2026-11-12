"""A part that carries several wires ends one cable (#805).

A multi-wire plug is ONE cable with N conductors that fan out at the plug: the
cable ends at the plug's `mate` point, and `wire-1` to `wire-N` are where the
conductors land (docs/dc-power-design.md sections 5.4 and 8). Cable ends are
marked by the names of the connection points alone, `cable` and `wire-<n>`; no
schema key marks one. So a contract that names `wire-<n>` points holds to this:

- the wires are numbered from 1 without a gap, each at a place of its own;
- no other point is named `wire-` and something else, because nothing reads it;
- exactly one `cable` point, at the same place and facing the same way as `mate`;
- its description does not say the plug carries "not one cable".

These read the contracts only, so they need no build.
"""
import re

import pytest

import libdata

WIRE = re.compile(r"^wire-(0|[1-9][0-9]*)$")
NOT_ONE_CABLE = re.compile(r"not\s+one\s+cable")


def points(doc):
    return doc.get("connection-points") or {}


def wires_of(doc):
    return sorted(int(WIRE.match(n).group(1)) for n in points(doc) if WIRE.match(n))


WIRED = [p for p in libdata.each_component() if wires_of(p.values[2])]


def test_the_library_has_wired_parts():
    assert WIRED, "no contract names a wire-<n> point: the sweep below would pass on nothing"


@pytest.mark.parametrize("ref,path,doc", WIRED)
def test_the_wires_are_numbered_from_one_without_a_gap(ref, path, doc):
    nums = wires_of(doc)
    assert nums == list(range(1, len(nums) + 1)), f"{ref}: wires {nums}"


@pytest.mark.parametrize("ref,path,doc", WIRED)
def test_each_wire_is_at_a_place_of_its_own(ref, path, doc):
    at = {}
    for name, p in points(doc).items():
        if WIRE.match(name):
            at.setdefault(tuple(p["at"]), []).append(name)
    twins = [names for names in at.values() if len(names) > 1]
    assert not twins, f"{ref}: wires on one place: {twins}"


@pytest.mark.parametrize("ref,path,doc", WIRED)
def test_no_point_is_named_wire_and_something_else(ref, path, doc):
    odd = [n for n in points(doc) if n.startswith("wire-") and not WIRE.match(n)]
    assert not odd, f"{ref}: {odd} start with wire- and are not wire-<n>"


@pytest.mark.parametrize("ref,path,doc", WIRED)
def test_the_cable_ends_at_the_mate(ref, path, doc):
    pts = points(doc)
    assert "mate" in pts, f"{ref}: wires and no mate point"
    assert "cable" in pts, f"{ref}: names wires and no cable point, so no cable ends at it"
    assert pts["cable"]["at"] == pts["mate"]["at"], f"{ref}: cable is not where mate is"
    assert pts["cable"]["direction"] == pts["mate"]["direction"], f"{ref}: cable faces another way than mate"
    assert "on" not in pts["cable"], f"{ref}: the cable end stands on no feature of its own"


@pytest.mark.parametrize("ref,path,doc", WIRED)
def test_the_description_does_not_deny_the_cable(ref, path, doc):
    text = " ".join(str(doc.get("description", "")).split())
    assert not NOT_ONE_CABLE.search(text), f"{ref}: says it carries 'not one cable'"

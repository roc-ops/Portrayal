"""One fact, one section - held across the library and not just within a device.

`attrsections.py` opens by saying keys are globally unique and that L25 is an
error if two sections ever claim one. L25 is real and it is an error, but it
reads ONE DEVICE at a time, so `optics-qsfp28` under `features` here and
`performance` there sailed through it. Seventeen keys had two homes, which
makes a section-scoped lookup a coin flip on exactly the keys a comparison
wants.

The re-filing itself was pure: every device's FLATTENED attrs came out
byte-identical, because `flatten()` erases the section. Nothing a drawing, an
export or the search blob reads moved. What moved is which section a reader -
or a rule saying "has thermal data" - finds the key under.

Two of the seventeen were genuine ties at one device each, and the counts could
not settle them. They are recorded here because the reasoning, not the tally,
is the durable part.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint
from portrayal import attrsections

LIB = ROOT / "library"


# ONE PARSE, NOT ONE PER QUESTION. `homes()` walked all 84 manifests, and
# `where()` called it once per key - so asking where seven optics keys live
# parsed the library seven times and took 33 seconds. The `library` fixture is
# session-scoped, and this maps it once per session too.
@pytest.fixture(scope="session")
def homes(library):
    out = {}
    for slug, path, d in library:
        for section, body in (d.get("attrs") or {}).items():
            if isinstance(body, dict):
                for k in body:
                    out.setdefault(k, {}).setdefault(section, []).append(path.parent.name)
    return out


# ---- the state of the library ----------------------------------------------

def test_no_attrs_key_has_two_homes(homes):
    drift = {k: sorted(v) for k, v in homes.items() if len(v) > 1}
    assert not drift, drift


def test_every_section_used_is_a_declared_one(library):
    bad = set()
    for _, _, d in library:
        bad |= set(d.get("attrs") or {}) - set(attrsections.SECTIONS)
    assert not bad, bad


def test_no_section_is_left_empty(library):
    """Moving a section's only key out leaves `physical:` with nothing under
    it, which the schema rejects as `None is not of type object` - and it did,
    on the s9720-56ed, until the move learned to clean up after itself."""
    empty = []
    for slug, f, d in library:
        for s, b in (d.get("attrs") or {}).items():
            if b is None or (isinstance(b, dict) and not b):
                empty.append(f"{f.parent.name}:{s}")
    assert not empty, empty


# ---- the rule ---------------------------------------------------------------

def fire(docs):
    out = []
    re_, rw = lint.err, lint.warn
    lint.err = lambda p, r, m: out.append(("ERR", r))
    lint.warn = lambda p, r, m: out.append(("WARN", r))
    try:
        lint.lint_library_comparable_facts([pathlib.Path("library")], docs)
    finally:
        lint.err, lint.warn = re_, rw
    return out


def test_drift_is_an_ERROR_not_a_warning():
    """It was a warning for exactly as long as it took to empty. L25 is already
    an error for the same defect inside one device; being lenient across
    devices is what let the section axis become a suggestion."""
    docs = [(pathlib.Path("a"), {"attrs": {"features": {"asic": "x"}}}),
            (pathlib.Path("b"), {"attrs": {"platform": {"asic": "y"}}})]
    assert ("ERR", "L68") in fire(docs)


def test_one_home_does_not_fire():
    docs = [(pathlib.Path("a"), {"attrs": {"platform": {"asic": "x"}}}),
            (pathlib.Path("b"), {"attrs": {"platform": {"asic": "y"}}})]
    assert not [o for o in fire(docs) if o[0] == "ERR"]


# ---- where the two ties landed, and why -------------------------------------

def where(homes, key):
    return sorted(homes.get(key, {}))


def test_boot_time_follows_its_own_numeric_siblings(homes):
    """A 1-vs-1 tie the counts could not settle. `boot-time-s` and
    `oob-link-time-s` already sat in `management`, and prose describing the same
    measurement belongs with the numbers describing it."""
    assert where(homes, "boot-time") == ["management"]
    for sibling in ("boot-time-s", "oob-link-time-s"):
        if sibling in homes:
            assert where(homes, sibling) == ["management"], sibling


def test_every_optics_key_sits_in_one_section_as_a_family(homes):
    """Six `optics-*` keys were split across two sections, one of them 13-to-12
    and another 1-to-1. Settling them individually by count would have scattered
    a family that L40 already treats as one thing."""
    fams = {k: where(homes, k) for k in homes if k.startswith("optics-")}
    assert fams, "no optics keys found"
    assert {tuple(v) for v in fams.values()} == {("features",)}, fams


def test_the_redundancy_prose_key_is_filed_with_capabilities(homes):
    """Also 1-vs-1, and superseded: both devices carrying it now state the same
    thing structurally on their groups, which is where the comparison layer
    reads it from. Its home matters only for consistency."""
    assert where(homes, "redundancy") in ([], ["features"])

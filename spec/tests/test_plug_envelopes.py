"""The plug envelopes are registry entries too, so generic/lc-plug and
generic/rj45-plug can `conforms:` and have L9 hold their drawn size to a
cited figure the way a cage or a module envelope already does.

lc-plug carries no depth ON PURPOSE. SENKO's three LC plug drawings each give
an overall length only as a REFERENCE dimension in parentheses, and they
disagree every time - (42) on the 2PC 911/912, (38.6) on the XP Fit Plus 951,
(43) on the LC-HD 913/914 - while the front profile (body 5.58 wide, the
latch tiers) and the latch length (8.6) repeat across all three WITH
tolerances. There is no class-wide LC plug length to register: the class
fixes the front profile and the latch, and the back end is the vendor's.
Adding a `d` here would assert a figure no drawing actually fixes and let a
generic part inherit it. The first test below pins that absence, so a later
"helpful" fix that adds a depth from a single vendor's drawing does not
quietly turn an unsourced class-wide claim into one that looks sourced.

rj45-plug is the UNSHIELDED plug only (CommScope customer drawing 2843005 rev
K, sheet 1) - 11.68 wide, 7.93 high, 22.48 long. Sheet 2 of the same drawing
dimensions the SHIELDED variant and it is a genuinely different shape (8.26
high by 22.73 long); this entry must stay the unshielded figures exactly,
never an average of the two real shapes.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def test_lc_plug_is_registered_with_no_depth():
    e = REG.get("lc-plug")
    assert e, "lc-plug missing from spec/schemas/standards.yaml"
    assert e["confidence"] == "drawing", e
    assert e.get("source"), "lc-plug needs a source citation"
    assert e["w"] == 5.58, e
    assert e["h"] == 10.43, e
    # See the module docstring: an LC plug has no class-wide overall length,
    # only three disagreeing REFERENCE figures across SENKO's drawings.
    assert "d" not in e, "lc-plug must not carry a depth - it has none, see module docstring"
    assert "depth" not in e, "lc-plug must not carry a depth - it has none, see module docstring"


def test_rj45_plug_is_registered_as_the_unshielded_shape():
    e = REG.get("rj45-plug")
    assert e, "rj45-plug missing from spec/schemas/standards.yaml"
    assert e["confidence"] == "drawing", e
    assert e.get("source"), "rj45-plug needs a source citation"
    assert e["w"] == 11.68, e
    assert e["h"] == 7.93, e
    assert e["depth"] == 22.48, e

"""What runs in a cage is a different fact from what fits in it, and there are
THREE answers to it, not two.

L12 already holds a cage and a transceiver to the same `interface:`, which says
an SFP-shaped thing fits and nothing more. Which optics light up is unmodelled -
and the library is in three states about it: silent, prose in `attrs`, or
structured. Nothing is structured yet, deliberately (see #13): form factor x
reach x media x breakout is a large vocabulary and four devices' marketing prose
is not enough to derive it from.

The middle state is why these tests exist. A device carrying
`optics-qsfp28: 100GBASE-SR4/CWDM4/LR4...` did real work off a datasheet, and a
register that scores it the same as a device saying nothing throws that away.
"""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

from portrayal import attrsections
from portrayal import lint
from portrayal import libwalk

MANIFESTS = libwalk.iter_devices([LIB])


def warnings_for(man):
    d = yaml.safe_load(man.read_text())
    saved = lint.WARNINGS[:]
    lint.WARNINGS.clear()
    try:
        lint.lint_device_port_optics(man, d, [str(LIB)])
        return [w for w in lint.WARNINGS if "[L40]" in w]
    finally:
        lint.WARNINGS[:] = saved


def test_prose_is_not_silence():
    """The AS7726-32X records its QSFP28 optics and its breakout modes. It is
    not structured and it is not nothing, and only the middle answer is true."""
    man = LIB / "devices/edgecore/as7726-32x/device.yaml"
    d = yaml.safe_load(man.read_text())
    flat = attrsections.flatten(d["attrs"])
    assert "optics-qsfp28" in flat and "port-modes-qsfp28" in flat
    assert not [w for w in warnings_for(man) if "qsfp28" in w]


def test_silence_is_reported():
    """The AGR400 states nothing about any of its four cage groups."""
    man = LIB / "devices/edgecore/as7946-30xb/device.yaml"
    assert len(warnings_for(man)) == 4


def test_a_cage_that_takes_no_optic_is_not_asked():
    """A management cluster is RJ45, USB and a console, and a passive mux's
    `media: fiber` is a bonded LC adapter. Neither takes a pluggable optic, and
    asking them for one would make the count meaningless."""
    for name in ("edgecore/as7726-32x", "smartoptics/dcp-r-9d-cs"):
        man = LIB / "devices" / name / "device.yaml"
        assert not [w for w in warnings_for(man) if "mgmt" in w or "(fiber)" in w]


def test_optics_prose_must_reach_a_group():
    """Recorded and unreachable is worse than absent, because it looks done.

    The AS5912-54X was the case the rule was written around - it carried
    `optics-sfp` while its group declared `media: sfp-plus`, so the one device
    that had recorded its SFP optics was also a device whose SFP group read as
    silent. That is FIXED, which is why this builds the shape rather than
    pointing at the device: a test that pins a real defect passes only for as
    long as nobody repairs it, and this one broke the hour the key was renamed.
    """
    d = {"groups": {"ports": {"term": "Port", "attrs": {"media": "sfp-plus"}}},
         "attrs": {"performance": {"optics-sfp": "10GBASE-SR, 1000BASE-T"}}}
    saved = lint.WARNINGS[:]
    lint.WARNINGS.clear()
    try:
        lint.lint_device_port_optics(Path("x"), d, [str(LIB)])
        ws = [w for w in lint.WARNINGS if "[L40]" in w]
    finally:
        lint.WARNINGS[:] = saved
    assert any("names no port group's media" in w for w in ws), ws
    assert any("port group ports" in w for w in ws), ws


def test_the_library_has_no_unreachable_optics_left():
    """And the real device is now held to the fixed state, which is the
    assertion that was actually wanted."""
    for man in MANIFESTS:
        assert not [w for w in warnings_for(man)
                    if "names no port group's media" in w], man


def test_nothing_is_structured_yet_and_that_is_the_point():
    """If this ever fails, the vocabulary got designed and #13 wants revisiting -
    the harvest was the deliverable, not a schema."""
    for man in MANIFESTS:
        d = yaml.safe_load(man.read_text()) or {}
        for gdef in (d.get("groups") or {}).values():
            assert "optics" not in (gdef or {}), man

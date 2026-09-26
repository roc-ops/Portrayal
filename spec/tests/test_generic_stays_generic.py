"""L99: a generic stays generic.

A `generic/` transceiver stands for every module of its kind, so a rate, a reach,
a wavelength, a mode or a wattage on it is a specific product wearing a generic's
name - the defect `common/sfp-lc-duplex` carried for a year (`mode: single-mode,
reach: 30km, speed: 100m` on a shape that stands for every SFP). Decision 5 of
docs/pluggables-design.md says the rate lives on the vendor wrapper; this is what
keeps that true after the people who decided it have moved on.
"""
import pathlib

from portrayal import lint

GEN = pathlib.Path("library/components/generic/sfp-lc/v1/contract.yaml")
VEN = pathlib.Path("library/components/cisco/sfp-10g-lr/v1/contract.yaml")


def run(path, doc):
    with lint.collecting() as got:
        lint.lint_component_generic(path, doc)
        return [e for e in got.errors if "[L99]" in e]


def base(**attrs):
    return {"kind": "component", "name": "sfp-lc", "class": "transceiver",
            "behaviour": "occupies", "mates": "sfp",
            "attrs": {"power-absent": "not-applicable", **attrs}}


def test_a_clean_generic_passes():
    assert run(GEN, base()) == []


def test_a_rate_attr_on_a_generic_is_an_error():
    errs = run(GEN, base(speed="10g"))
    assert len(errs) == 1 and "is a generic and carries" in errs[0] and "speed" in errs[0]


def test_each_forbidden_attr_is_named():
    for key in ("speed", "reach", "wavelength", "mode",
                "power-draw-max-w", "power-draw-typical-w"):
        errs = run(GEN, base(**{key: "x"}))
        assert errs and key in errs[0], key


def test_a_rate_in_the_name_is_an_error():
    doc = dict(base(), name="sfp28-lc")
    errs = run(GEN, doc)
    assert len(errs) == 1 and "names a rate" in errs[0]


def test_the_same_attrs_on_a_vendor_wrapper_are_fine():
    """The rule is about the namespace, not the class: a vendor optic is SUPPOSED
    to carry these."""
    assert run(VEN, base(speed="10g", reach="10km", **{"power-draw-max-w": 1.0})) == []


def test_a_generic_that_is_not_a_transceiver_is_not_asked():
    doc = dict(base(speed="fast"), **{"class": "connector"})
    assert run(GEN, doc) == []


def test_l99_is_registered_as_a_component_rule():
    assert lint.RULES["L99"][0] == "component"


def test_1000base_in_the_name_is_a_rate():
    """`sfp-1000base-t` names a rate as surely as `sfp28-lc` does. The token list
    reached every `<n>G` spelling and every `<n>GBASE-x`, and walked straight past
    the one Ethernet rate whose name is not in gigabits."""
    errs = run(GEN, dict(base(), name="sfp-1000base-t"))
    assert len(errs) == 1 and "names a rate" in errs[0]


def test_a_directory_called_generic_above_the_checkout_is_not_the_namespace():
    """THE NAMESPACE IS A POSITION, NOT A SUBSTRING. The rule used to ask whether
    "/generic/" appeared anywhere in the path, which made every vendor optic in a
    checkout under `~/generic/` answer yes and lose the attrs it is supposed to
    carry."""
    outside = pathlib.Path(
        "/home/me/generic/Portrayal/library/components/cisco/sfp-10g-lr/v1/contract.yaml")
    assert run(outside, base(speed="10g", reach="10km")) == []


def test_a_cable_kind_on_a_generic_is_an_error():
    errs = run(GEN, base(**{"cable-kind": "dac"}))
    assert errs and "cable-kind" in errs[0]


def test_a_cable_kind_on_a_vendor_wrapper_is_fine():
    assert run(VEN, base(**{"cable-kind": "aoc"})) == []

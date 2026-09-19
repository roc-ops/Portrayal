"""L100: an attr with no value is a missing colon.

YAML flow style hides this one completely. Written inside a component's
`parts:` list as

    attrs: {media: sfp-plus, function: reserved, unused}

the last entry has no colon, so it is not `function: reserved, unused` - it is a
THIRD key, `unused`, whose value is null. Every schema in spec/schemas types
these maps as a bare `{"type": "object"}`, so nothing rejected it, and the run
went red much later and somewhere else: `presented_interface` returned a
two-tuple for the malformed part and L11 unpacked it into three names, which
reads as a fault in the linter rather than a typo in the contract, and sent the
author looking at the toolchain worktree (issue #346) instead of at their own
line.

An attr whose value is null carries nothing a renderer or an export can use, so
there is no reading of it that is not this mistake.
"""
import pathlib

from portrayal import lint

COMP = pathlib.Path("library/components/juniper/jnp10k-re1/v2/contract.yaml")
DEV = pathlib.Path("library/devices/juniper/mx304/device.yaml")


def run(path, doc):
    with lint.collecting() as got:
        lint.lint_attrs_null(path, doc)
        return [e for e in got.errors if "[L100]" in e]


def part(attrs):
    return {"kind": "component", "name": "jnp10k-re1",
            "parts": [{"ref": "std/sfp@1", "id": "xge-0", "at": [283.35, 16.4],
                       "attrs": attrs}]}


def test_the_missing_colon_in_a_parts_attrs_map_is_an_error():
    """The exact line that cost an afternoon."""
    errs = run(COMP, part({"media": "sfp-plus", "function": "reserved", "unused": None}))
    assert len(errs) == 1, errs
    assert "unused" in errs[0]
    assert "colon" in errs[0].lower(), "the message must name the usual cause"


def test_a_parts_attrs_map_with_values_passes():
    assert run(COMP, part({"media": "sfp-plus", "function": "reserved"})) == []


def test_the_message_names_the_part_that_carries_it():
    errs = run(COMP, part({"media": None}))
    assert "xge-0" in errs[0], errs


def test_each_valueless_key_is_named_separately():
    errs = run(COMP, part({"media": "sfp-plus", "unused": None, "spare": None}))
    assert len(errs) == 2, errs
    assert {"unused", "spare"} == {k for k in ("unused", "spare")
                                   if any(k in e for e in errs)}


def test_a_component_with_no_parts_is_not_asked():
    assert run(COMP, {"kind": "component", "name": "jnp10k-re1"}) == []


def test_a_null_on_a_device_placement_is_an_error():
    doc = {"kind": "device", "name": "mx304", "views": {"front": {"components": {
        "placements": [{"ref": "std/sfp@1", "id": "port-0", "at": [10, 10],
                        "attrs": {"media": "sfp-plus", "unused": None}}]}}}}
    errs = run(DEV, doc)
    assert len(errs) == 1 and "unused" in errs[0] and "port-0" in errs[0], errs


def test_a_null_on_a_device_bay_is_an_error():
    doc = {"kind": "device", "name": "mx304", "views": {"front": {"components": {
        "bays": [{"id": "fpc-0", "at": [0, 0], "size": [10, 10],
                  "attrs": {"role": "line-card", "hot-swap": None}}]}}}}
    errs = run(DEV, doc)
    assert len(errs) == 1 and "hot-swap" in errs[0] and "fpc-0" in errs[0], errs


def test_a_null_in_a_device_attrs_section_is_an_error():
    """The top-level map is filed by section, so the null is one level deeper."""
    doc = {"kind": "device", "name": "mx304",
           "attrs": {"power": {"power-max-w": 1200, "power-inlet": None}}}
    errs = run(DEV, doc)
    assert len(errs) == 1 and "power-inlet" in errs[0], errs


def test_a_null_on_a_group_is_an_error():
    doc = {"kind": "device", "name": "mx304",
           "groups": {"xe": {"role": "data", "attrs": {"media": "sfp-plus", "speed": None}}}}
    errs = run(DEV, doc)
    assert len(errs) == 1 and "speed" in errs[0], errs


def test_a_clean_device_passes():
    doc = {"kind": "device", "name": "mx304",
           "attrs": {"power": {"power-max-w": 1200}},
           "groups": {"xe": {"role": "data", "attrs": {"media": "sfp-plus"}}},
           "views": {"front": {"components": {
               "placements": [{"ref": "std/sfp@1", "id": "port-0", "at": [10, 10],
                               "attrs": {"media": "sfp-plus"}}]}}}}
    assert run(DEV, doc) == []


def test_a_null_outside_an_attrs_map_is_not_this_rule():
    """`only-in: ` empty, a blank `description:` - other rules own those, and a
    rule that claimed them would fire across the library on its first day."""
    doc = {"kind": "device", "name": "mx304", "description": None,
           "views": {"front": {"components": {
               "placements": [{"ref": "std/sfp@1", "id": "port-0", "for": None}]}}}}
    assert run(DEV, doc) == []


def test_l100_is_registered_in_the_catalogue():
    assert lint.RULES["L100"][0] == "component, device"

"""A component seated in a COMPONENT's bay must move the lock of the device that
draws it.

`_composed()` followed a component's `parts:` transitively and stopped there. A
component contract can host bays of its own - a Juniper SCB carries a routing
engine, a SIP carries SPAs, a riser carries cards - and the `default:` and
`accepts:` of those bays name further components the device draws. Editing one
of those redrew the device and devicelock asked for nothing: on #521 mx240,
mx480 and mx960 had to be bumped by hand because `juniper/re-s-1300@1` sits
inside an SCB's bay and not in a device bay.

A nested bay is now followed exactly as a device bay is - its `default` and every
ref it `accepts` - and at any depth, because the walk is the same transitive one
`parts:` already had.
"""
import pathlib

from portrayal import devicelock as dl


def _contract(name, extra=""):
    return (f"format: 1\nkind: module\nname: {name}\nversion: 1.0.0\n"
            "class: psu\nsize: {w: 10.0, h: 10.0}\nstates: [absent]\n"
            "skins: [default]\n" + extra)


SKIN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>'

# carrier -> (bay) -> engine -> (bay) -> daughter: two levels of nesting, and a
# `spare` that only the carrier's bay ACCEPTS, never seats by default.
CARRIER_BAYS = """\
bays:
  re:
    at: [0, 0]
    size: [5, 5]
    accepts: [acme/engine@1, acme/spare@1]
    default: acme/engine@1
"""
ENGINE_BAYS = """\
bays:
  sub:
    at: [0, 0]
    size: [2, 2]
    accepts: [acme/daughter@1]
    default: acme/daughter@1
"""

DEVICE_YAML = """\
format: 1
kind: device
name: box
version: 1.0.0
manufacturer: Acme
model: Box
chassis: {width: 100.0, height: 44.0, depth: 200.0, ru: 1}
groups:
  scbs: {term: SCB, role: service, index-origin: 0}
views:
  front:
    size: {w: 100.0, h: 44.0}
    components:
      bays:
      - id: scb-0
        at: [0, 0]
        size: {w: 10.0, h: 10.0}
        group: scbs
        rel-pos: 0
        accepts: [acme/carrier@1]
        default: acme/carrier@1
"""


def _library(tmp_path) -> pathlib.Path:
    lib = tmp_path / "library"
    for name, extra in (("carrier", CARRIER_BAYS), ("engine", ENGINE_BAYS),
                        ("spare", ""), ("daughter", "")):
        v1 = lib / "components" / "acme" / name / "v1"
        (v1 / "skins").mkdir(parents=True)
        (v1 / "contract.yaml").write_text(_contract(name, extra))
        (v1 / "skins" / "default.svg").write_text(SKIN)
    dev = lib / "devices" / "acme" / "box"
    dev.mkdir(parents=True)
    (dev / "device.yaml").write_text(DEVICE_YAML)
    dl.update(lib)
    assert dl.check(lib) == []
    return lib


def _edit(lib, name):
    ct = lib / "components" / "acme" / name / "v1" / "contract.yaml"
    ct.write_text(ct.read_text() + "description: redrawn in place\n")


def test_the_nested_default_occupant_is_in_composed_refs(tmp_path):
    lib = _library(tmp_path)
    refs = dl.load_lock(lib)["devices"]["acme/box"]["composed-refs"]
    assert {"acme/carrier@1", "acme/engine@1", "acme/spare@1",
            "acme/daughter@1"} <= set(refs), refs


def test_editing_a_nested_bay_s_default_names_the_seating_device(tmp_path):
    """The #521 case: the RE inside the SCB is rewritten, the device is named."""
    lib = _library(tmp_path)
    _edit(lib, "engine")
    findings = dl.check(lib)
    assert [(n, k) for n, k, _ in findings] == [("acme/box", "unbumped")], findings
    assert "acme/engine@1" in findings[0][2]


def test_a_ref_the_nested_bay_only_accepts_counts_too(tmp_path):
    """As on a device bay, where `accepts` is hashed beside `default`."""
    lib = _library(tmp_path)
    _edit(lib, "spare")
    findings = dl.check(lib)
    assert [n for n, _, _ in findings] == ["acme/box"], findings
    assert "acme/spare@1" in findings[0][2]


def test_two_levels_down_still_reaches_the_device(tmp_path):
    lib = _library(tmp_path)
    _edit(lib, "daughter")
    findings = dl.check(lib)
    assert [n for n, _, _ in findings] == ["acme/box"], findings
    assert "acme/daughter@1" in findings[0][2]

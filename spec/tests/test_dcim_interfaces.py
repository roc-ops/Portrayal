"""Which placements reach a DCIM as interfaces, and why it is not the id.

The exporter used to decide by asking whether a placement's id started with
`port-`. That is a spelling convention standing in for a fact, and it dropped
real ports in silence, with no rule anywhere to catch it:

  - every one of the UfiSpace S9710-76D's 76 ports, because they are `fab-N` and
    `svc-N`. Its export carried ZERO interfaces for a 76-port router.
  - the ASR-9001's `sfp-plus-N` and `cluster-N`, the MX104's and MX150's `xe-N`,
    the ReadyLinks GL-8xEP's eight PoE ports.
  - the MaiaEdge Port Extender's eight 100G uplinks, which is how it was found -
    and only because somebody read the export instead of trusting it.

A group already states what it is FOR. That is the structural answer, so that is
what selects now. These tests hold the two ends of it: the role split has to stay
exhaustive over the schema's enum, and an RJ45 has to keep being asked what it is
for rather than assumed to be Ethernet.
"""
import functools
import json
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import dcim_export as dx  # noqa: E402
from manifest import load_yaml, view_parts  # noqa: E402


# --- the role split ----------------------------------------------------------

def test_every_role_the_schema_allows_is_classified():
    """THE GUARD AGAINST THE SAME BUG ARRIVING AGAIN, one level up.

    A sixth role added to the schema must be put on one side or the other by
    whoever adds it. Without this, it falls silently to `not a port` and a
    device's ports vanish from its export exactly as they did before - the same
    failure, just later and harder to find.
    """
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    enum = set(schema["properties"]["groups"]["additionalProperties"]
               ["properties"]["role"]["enum"])
    assert dx.PORT_ROLES | dx.NON_PORT_ROLES == enum
    assert not (dx.PORT_ROLES & dx.NON_PORT_ROLES), "a role cannot be both"


def test_lamps_are_not_interfaces():
    """`indicator` is where every LED part in the library sits - 393 of them.

    They would otherwise type: `iface_type` reads the family out of the ref as a
    SUBSTRING, so `common/qsfp-lane-leds@1` contains 'qsfp' and comes back as a
    100G interface. The role is what keeps a lamp out, not the typing.
    """
    assert "indicator" in dx.NON_PORT_ROLES
    assert "furniture" in dx.NON_PORT_ROLES


# --- an RJ45 is not automatically Ethernet -----------------------------------

def _pl(ref):
    return {"ref": ref, "id": "x"}


def test_a_bare_rj45_in_a_management_group_is_not_a_gigabit_interface():
    """ToD, BITS, PPS, SYNC, an external reference clock, a console, an AUX
    port - 65 of the library's 73 bare-RJ45 placements are one of those, and
    typing them 1000base-t puts a timing input in a DCIM as a network port."""
    assert dx.iface_type(_pl("std/rj45@2"), {}, "management") is None
    assert dx.iface_type(_pl("std/rj45-ganged@2"), {}, "management") is None


def test_an_ethernet_jack_is_one_wherever_it_sits():
    """The `-eth` parts say what they are in their own name; that is the split
    docs/rj45-family-design.md draws and L76 polices."""
    assert dx.iface_type(_pl("common/rj45-eth@1"), {}, "management") == "1000base-t"
    assert dx.iface_type(_pl("common/rj45-ganged-eth@1"), {}, "traffic") == "1000base-t"


def test_a_bare_rj45_the_device_calls_traffic_is_an_interface():
    """The ReadyLinks GL-8xEP's eight PoE ports are fitted on the bare part and
    are unmistakably Ethernet - group `gbe-poe`, media rj45, speed 1g, PoE. The
    rule asks the device what the group is for rather than trusting the ref."""
    assert dx.iface_type(_pl("std/rj45-ganged@2"), {"speed": "1g"}, "traffic") == "1000base-t"


# --- the corpus, which is the only thing that can prove the fix works --------

@functools.lru_cache(maxsize=1)
def _exports():
    """Every published device type, parsed ONCE.

    The first draft re-globbed and re-parsed 90-odd export files for every
    device it checked, which cost this file three minutes on a five-minute
    suite. A test nobody wants to wait for is a test that gets skipped.
    """
    out = []
    for p in sorted((LIB / "exports/netbox/device-types").glob("*/*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        out.append((str(d.get("model", "")), d))
    return tuple(out)


def _export(model_startswith):
    for model, d in _exports():
        if model.startswith(model_startswith):
            return d
    return None


@pytest.mark.parametrize("model,least", [
    ("S9710-76D", 76),        # 40 fabric + 36 service, and it exported 0
    ("S9700-23D", 23),
    ("S9705-48D", 48),
    ("Port Extender", 56),    # 48 SFP28 + 8 QSFP28
])
def test_a_device_exports_at_least_the_ports_its_model_number_names(model, least):
    """These model numbers state a port count, so the export can be checked
    against something outside the model. Each carries a few management or
    console interfaces on top, hence `at least`."""
    d = _export(model)
    if d is None:
        pytest.skip(f"{model} is not in this library")
    n = len(d.get("interfaces") or [])
    assert n >= least, f"{model} exports {n} interface(s), fewer than the {least} it names"


def test_no_device_with_traffic_ports_exports_none_of_them():
    """THE SHAPE OF THE ORIGINAL DEFECT, swept across the library.

    A 76-port router exported an empty interface list and nothing said a word.
    Any device that places typable ports in a `traffic` group must reach its
    export with at least one interface.
    """
    bad, checked = [], 0
    for p in sorted((LIB / "devices").glob("*/*/device.yaml")):
        dev = load_yaml(p) or {}
        groups = dev.get("groups") or {}
        wanted = 0
        for cfg in (dev.get("configurations") or {"default": {}}):
            for view in dx.views_for(dev, cfg):
                for pl in dx.scoped(view_parts(view)["placements"], cfg):
                    g = groups.get(pl.get("group")) or {}
                    if g.get("role") != "traffic":
                        continue
                    a = {**(g.get("attrs") or {}), **(pl.get("attrs") or {})}
                    if dx.iface_type(pl, a, "traffic") is not None:
                        wanted += 1
        if not wanted:
            continue
        checked += 1
        d = _export(str(dev.get("model", "")))
        if d is None:
            continue
        if not (d.get("interfaces") or []):
            bad.append(f"{p.parent.parent.name}/{p.parent.name}: {wanted} typable "
                       f"traffic port(s) and an empty export")
    assert not bad, "\n".join(bad)
    # NOT VACUOUS, and this is not decoration. Run against the exports as they
    # were before the fix, this sweep fails on four devices - the ASR-9001, the
    # MX104, the DCP-M32-CSO-ZR and the S9710-76D, that last one with 152
    # typable traffic ports and an empty interface list. A sweep that walked an
    # empty collection would pass just as quietly as the bug it exists to find.
    assert checked >= 50, f"only {checked} device(s) reached the sweep"


# --- the type table, and the family it reads ---------------------------------
#
# 773 placements fell out of the exports for want of a row - 400 QSFP-DD at 800G,
# 192 OSFP at 800G, 80 QSFP56, 72 SFP56. An absent row reads exactly like a port
# that does not exist, which is the same silence the id prefix caused.

def test_osfp_is_not_an_sfp():
    """THE SUBSTRING TRAP, and it is the reason the S9321-64EO exported nothing.

    "osfp" contains "sfp", so the family test matched the wrong branch and every
    one of that switch's 192 800G ports was read as an SFP. It only failed
    SAFELY - returning None - because no ("sfp", "800g") row existed. Had one of
    those ports been declared at 25g it would have exported as SFP28: a wrong
    answer rather than a missing one.
    """
    assert dx.iface_type(_pl("std/osfp@1"), {"speed": "800g"}, "traffic") == "800gbase-x-osfp"
    assert dx.iface_type(_pl("std/sfp-ganged@1"), {"speed": "25g"}, "traffic") == "25gbase-x-sfp28"


def test_800g_names_the_cage_it_is_in():
    """800G is OSFP or QSFP-DD and they are different connectors. A DCIM that
    cannot tell them apart cannot tell you which optic to order."""
    a = dx.iface_type(_pl("std/osfp@1"), {"speed": "800g"}, "traffic")
    b = dx.iface_type(_pl("std/qsfp-dd@1"), {"speed": "800g"}, "traffic")
    assert a == "800gbase-x-osfp" and b == "800gbase-x-qsfpdd" and a != b


def test_a_cage_with_no_settled_default_does_not_guess_its_speed():
    """An OSFP is 400G or 800G and nothing makes one likelier. The families that
    do have a settled default keep it; this one gets no row rather than a coin
    toss, which is this function's own stated rule."""
    assert dx.iface_type(_pl("std/osfp@1"), {}, "traffic") is None
    assert dx.iface_type(_pl("std/qsfp28@1"), {}, "traffic") == "100gbase-x-qsfp28"


def test_every_plain_speed_the_library_uses_has_a_row():
    """THE SWEEP THAT WOULD HAVE CAUGHT ALL 773.

    Only speeds written as a plain token are required to type. That is the line
    between a missing row and a fact about the hardware: the MX304's GM/PTP port
    says "1g/10g (reserved for future use per the guide)" because Juniper says it
    is unsupported, and it is RIGHT that it does not export. A new device with
    1.6T ports will fail this until somebody adds the row and picks the cage.
    """
    import re
    plain = re.compile(r"^\d+(\.\d+)?[gm]$")
    bad = set()
    for p in sorted((LIB / "devices").glob("*/*/device.yaml")):
        dev = load_yaml(p) or {}
        groups = dev.get("groups") or {}
        for cfg in (dev.get("configurations") or {"default": {}}):
            for view in dx.views_for(dev, cfg):
                for pl in dx.scoped(view_parts(view)["placements"], cfg):
                    g = groups.get(pl.get("group")) or {}
                    if g.get("role") not in dx.PORT_ROLES:
                        continue
                    a = {**(g.get("attrs") or {}), **(pl.get("attrs") or {})}
                    if a.get("role") in ("mgmt", "console"):
                        continue
                    speed = str(a.get("speed") or "")
                    if not plain.match(speed):
                        continue
                    if dx.iface_type(pl, a, g.get("role")) is None:
                        bad.add(f"{p.parent.parent.name}/{p.parent.name}: {pl['ref']} "
                                f"at {speed} has no IFACE_TYPE row")
    assert not bad, "\n".join(sorted(bad))


@pytest.mark.parametrize("model,kind,least", [
    ("S9321-64EO", "800gbase-x-osfp", 32),
    ("S9725-64E", "800gbase-x-qsfpdd", 32),
    ("S9301-32DB", "200gbase-x-qsfp56", 24),
    ("S9620-54DC", "50gbase-x-sfp56", 8),
])
def test_the_devices_that_needed_a_row_now_export_those_ports(model, kind, least):
    """Each of these declares the cage in its own `media` attr and its
    description names the count - so the export is checked against the device
    rather than against the table it was written from."""
    d = _export(model)
    if d is None:
        pytest.skip(f"{model} is not in this library")
    n = sum(1 for i in (d.get("interfaces") or []) if i["type"] == kind)
    assert n >= least, f"{model} exports {n} {kind}, expected at least {least}"


def test_the_two_type_tables_do_not_disagree_about_a_cage():
    """A module's ports type by PART_IFACE and a device's by IFACE_TYPE, and
    both name XFP. One cage, two tables, one string - which is the arrangement
    this library gets wrong most often, so it is asserted rather than assumed."""
    assert dx.PART_IFACE["std/xfp"] == dx.IFACE_TYPE[("xfp", "10g")]


def test_an_xfp_placement_types():
    """20 placements on the MX80. XFP is nobody's substring, so the family test
    simply never looked for it."""
    assert dx.iface_type(_pl("std/xfp@1"), {"speed": "10g"}, "traffic") == "10gbase-x-xfp"

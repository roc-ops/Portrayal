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

from portrayal import dcim_export as dx
from portrayal.manifest import load_yaml, view_parts  # noqa: E402


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


def test_a_bare_rj45_the_device_gives_a_speed_is_an_ethernet_port():
    """The S9110-32X's out-of-band jack, and the reason it is on the bare part.

    It is modelled that way BY DESIGN: its two lamps are placed separately above
    the jack, where an 8x reading of the HIG photo puts them, carrying the HIG's
    own Management Port LED table - green 1G on the left, amber 10M/100M on the
    right. The `-eth` part brings its own pair, which would land INSIDE the jack
    at a different height and with a weaker state vocabulary. So the device is
    right and the exporter had to learn the difference.

    A declared Ethernet speed is what separates it from the 64 timing and serial
    jacks on the same part: a ToD or BITS input has no Ethernet speed to give,
    and not one of them states a speed.
    """
    assert dx.iface_type(_pl("std/rj45-ganged@2"), {"speed": "100m-1g"},
                         "management") == "1000base-t"
    assert dx.iface_type(_pl("std/rj45@2"), {}, "management") is None


def test_the_s9110_exports_its_out_of_band_jack():
    d = _export("S9110-32X")
    if d is None:
        pytest.skip("S9110-32X is not in this library")
    oob = [i for i in (d.get("interfaces") or []) if i["name"] == "oob"]
    assert oob == [{"name": "oob", "type": "1000base-t", "mgmt_only": True}], oob


# --- a management port exports however the device spells it -------------------
#
# The collector says "EITHER WAY OF SAYING IT COUNTS" - `attrs.role: mgmt` on the
# port, or `role: management` on its group - and marks both mgmt_only. But the
# loop in front of it SKIPPED any port whose own attrs said `role: mgmt`, so the
# same port exported or vanished by which of two equivalent spellings a device
# chose. 99 management ports on 70 devices were missing: every device that says
# it per port, while the EPS201, which says it only through its group, exported
# its own. #37dac1f4 counted "76 ports plus two management" as the goal; this is
# the rest of that.

def test_a_management_port_on_the_bare_jack_is_ethernet_when_the_device_says_so():
    """The guard that keeps ToD, BITS and serial jacks out of the DCIM asks for a
    speed because a timing input has none to give. `role: mgmt` is a stronger
    statement than a speed - the device is saying what the jack is FOR - and the
    AS5912-54X and CSR310 say it with no speed at all."""
    assert dx.iface_type(_pl("std/rj45@2"), {"role": "mgmt"}, "management") == "1000base-t"
    assert dx.iface_type(_pl("std/rj45@2"), {}, "management") is None


@pytest.mark.parametrize("model,port", [
    ("COR550", "mgmt-eth"),                 # role: mgmt on the port, lamped part
    ("ECS4530-54CSFP", "mgmt-eth"),         # role: mgmt, bare part, speed 1g
    ("5912-54X-O-AC-F", "mgmt-eth"),         # AS5912-54X: role: mgmt, bare part, no speed
    ("AS4630-54TE-O-AC-F-EU", "mgmt"),      # role only on the group: always worked
])
def test_a_management_port_exports_however_the_device_spells_it(model, port):
    d = _export(model)
    if d is None:
        pytest.skip(f"{model} is not in this library")
    hit = [i for i in (d.get("interfaces") or []) if i["name"] == port]
    assert hit == [{"name": port, "type": "1000base-t", "mgmt_only": True}], \
        (model, [i["name"] for i in (d.get("interfaces") or []) if i.get("mgmt_only")])


def test_a_10g_management_sfp_is_listed_once():
    """These already export through their own path, with a description saying the
    faceplate port is not a switch interface. Letting role: mgmt through the main
    collector must not list them a second time under a switch-port type."""
    d = _export("7326-56X-O-AC-F")
    if d is None:
        pytest.skip("AS7326-56X is not in this library")
    names = [i["name"] for i in (d.get("interfaces") or [])]
    for n in ("57", "58", "port-57", "port-58"):
        assert names.count(n) <= 1, (n, names.count(n))
    assert sum(1 for n in names if n in ("57", "port-57")) == 1, names


# --- where the cord goes in (#286) -------------------------------------------
#
# `power-ports` used to be written in exactly one place - build_module - so 0 of
# 89 device types carried one against 27 module types, and a DCIM built from
# these exports showed the MX150 drawing power from nothing.
#
# The reason it took a census to notice is the reason it is not simply a bug:
# on 39 devices the absence is CORRECT. The cord goes into the supply, the
# supply is a module type with its own inlet, and the DCIM instantiates that
# port when the module is seated. Only a chassis-mounted inlet is missing, and
# only two devices have one.

def test_a_fixed_device_exports_the_inlet_on_its_faceplate():
    """The MX150 has no PSU bay at all. Its C14 is the only way power enters the
    box, and it sat in the `mgmt` group beside the console and the USB service
    port - which is why a rule reading the group or the id would have missed it,
    and why the ref is what selects."""
    d = _export("MX150")
    if d is None:
        pytest.skip("MX150 is not in this library")
    assert d.get("power-ports") == [{"name": "inlet", "type": "iec-60320-c14"}]


def test_a_chassis_inlet_is_not_counted_twice_against_its_supply():
    """THE QUESTION #286 ASKED BEFORE IT COULD BE ANSWERED.

    The MX960 places four C20 receptacles AND has four PEM bays, which is the
    shape a double count would take. It is not one, and the library says so
    from both ends: the rear studio photograph the model is measured from shows
    an inlet strip above the supplies, the device's `inlets` group records that
    "the inlet is the cord's end and stays with the chassis while a PEM comes
    out", and `juniper/mx960-psu-ac` composes no inlet part because the supply
    has none.

    So the assertion is the pair, not either half: four on the chassis, none on
    the supply. Giving that supply an inlet later would break this test, which
    is the point - it would be describing different hardware.
    """
    d = _export("MX960")
    if d is None:
        pytest.skip("MX960 is not in this library")
    chassis = d.get("power-ports") or []
    assert len(chassis) == 4, f"MX960 exports {len(chassis)} chassis inlet(s)"
    assert {p["type"] for p in chassis} == {"iec-60320-c20"}

    psu = None
    for p in sorted((LIB / "exports/netbox/module-types").glob("*/*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        if doc.get("model") == "MX960 AC PSU":
            psu = doc
    assert psu is not None, "the MX960 AC PSU module type is missing"
    assert not psu.get("power-ports"), (
        "the MX960's supply has no inlet of its own - the chassis carries them. "
        "If this supply has grown one, the four chassis ports are now a double count")


def test_a_device_whose_supply_carries_the_inlet_exports_none_itself():
    """The other 39. The R740xd's C14 belongs to `dell/psu-1100w-ac-14g`, which
    exports it as a module type; the chassis places no inlet and must stay
    quiet, or every seated supply would arrive with two."""
    d = _export("PowerEdge R740xd")
    if d is None:
        pytest.skip("R740xd is not in this library")
    assert not d.get("power-ports")


# --- the same jack, the same answer (#285) -----------------------------------
#
# `build_module` has typed a timing connector as `other` carrying its connector
# or its function as a label since PART_RF was written - the schema's way of
# saying "a thing it has no name for". `build` had no path to PART_RF at all, so
# the identical jack on a chassis faceplate exported nothing: 263 placements
# across 33 devices, and the two halves of one exporter disagreeing about one
# piece of hardware.

def test_a_chassis_timing_jack_says_what_it_is():
    """The ASR 9001's two SYNC jacks and its ToD port. `other` alone would say
    only that a port exists; `other` + SYNC says what to plug into it."""
    d = _export("ASR 9001 Router")
    if d is None:
        pytest.skip("the ASR 9001 is not in this library")
    timing = {i["name"]: i.get("label") for i in (d.get("interfaces") or [])
              if i["type"] == "other"}
    assert timing == {"sync-0": "SYNC", "sync-1": "SYNC", "tod": "TOD"}


def test_the_two_passes_agree_about_std_smb():
    """The asymmetry itself, asserted as a pair rather than as two facts. An
    SMB on a route processor and an SMB on a chassis are the same connector,
    and before this they were an interface and nothing."""
    assert dx.PART_RF["std/smb"] == ("other", "SMB")
    on_a_card = dx.build_module(
        {"name": "x", "parts": [{"ref": "std/smb@1", "id": "mhz"}]}, "Test")
    assert on_a_card["interfaces"] == [{"name": "mhz", "type": "other", "label": "SMB"}]

    with_smb = [d for _m, d in _exports()
                if any(i.get("label") == "SMB" for i in (d.get("interfaces") or []))]
    assert with_smb, "no device type carries an SMB interface; the chassis path is gone"


def test_a_panel_mount_jack_is_listed_and_not_derived():
    """`common/smb-jack` is "a gold nut around a std/smb core" in its own words,
    and is in PART_RF by name rather than by following that composition.

    Six class:port parts compose a classified core and inheriting would be WRONG
    on three: `common/rj45-ganged-eth` composes `std/rj45-ganged`, which
    PART_CONSOLE calls a console - inheriting it would file every Ethernet jack
    in the library as a console port, which is #27 and #29 for a third time.
    """
    assert dx.PART_RF["common/smb-jack"] == ("other", "SMB")
    assert dx.PART_RF["common/sma-jack"] == ("other", "SMA")
    assert dx.PART_CONSOLE["std/rj45-ganged"] == "rj-45"
    assert "common/rj45-ganged-eth" not in dx.PART_CONSOLE, (
        "the Ethernet jack must not inherit its core's console type")


def test_no_device_type_names_one_port_twice():
    """Both libraries key ports by name within a type, and the timing list is a
    second source of names appended to the interface list. A collision would be
    rejected on import, which is a failure a person finds rather than a test."""
    bad = []
    for model, d in _exports():
        for key in ("interfaces", "console-ports", "power-ports", "module-bays"):
            names = [i.get("name") for i in (d.get(key) or [])]
            dupes = {n for n in names if names.count(n) > 1}
            if dupes:
                bad.append(f"{model}: {key} {sorted(dupes)}")
    assert not bad, "\n".join(bad)

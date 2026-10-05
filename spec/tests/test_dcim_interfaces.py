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
    assert "fabric" in dx.PORT_ROLES            # cabled like any port (#510)
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


def test_a_t1_e1_traffic_jack_is_not_ethernet():
    """The TM-3312's CES ports are traffic ports on the bare part, so the guard
    lets them through - and the 1g default then typed eight T1/E1 lines as
    gigabit Ethernet. The media says what they carry."""
    assert dx.iface_type(_pl("std/rj45-ganged@2"), {"media": "rj48"}, "traffic") == "other"
    # ...but a bare rj48 jack the guard keeps out stays out: mx104's ext-ref-clock
    assert dx.iface_type(_pl("std/rj45@2"), {"media": "rj48"}, "management") is None


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

    Every speed is a plain token now - lint L110 holds the library to the closed
    set in spec/schemas/speeds.yaml - so this reads every speed on a port. A new
    device with 1.6T ports will fail this until somebody adds the row and picks
    the cage.

    A port whose part NOT_A_DCIM_PORT registers is not a missing row: the register
    already says why it does not type. An ONT's SC/APC PON port is the one
    case - the HLX-TGV's states `speed: 10g` beside `pon: xgs-pon`, the ferrule
    is not an Ethernet cage family, and it types from `pon` instead.
    """
    import re
    plain = re.compile(r"^\d+(\.\d+)?[gmt]$")
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
                    if pl["ref"].split("@")[0] in dx.NOT_A_DCIM_PORT:
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
    assert dx.iface_type(_pl("std/rj45-ganged@2"), {"speed": "1g"},
                         "management") == "1000base-t"
    assert dx.iface_type(_pl("std/rj45@2"), {}, "management") is None


# --- one spelling per rate (#512) --------------------------------------------

def test_the_rj45_table_has_one_row_per_rate():
    """1G copper was spelled four ways and IFACE_TYPE carried two of them, so a
    port spelled either of the others typed as nothing. With one vocabulary the
    table needs one row, and a second spelling coming back is a regression."""
    rj45 = {s for (fam, s) in dx.IFACE_TYPE if fam == "rj45"}
    assert "100m-1g" not in rj45 and "1g" in rj45, rj45


def test_every_speed_the_export_tables_key_on_is_in_the_closed_set():
    """The tables and the library speak one vocabulary. A row keyed on a
    spelling lint L110 refuses is a row no port can ever reach."""
    from portrayal import lint
    keys = {s for (_f, s) in dx.IFACE_TYPE} | {s for (_m, s) in dx.PART_MEDIA if s}
    assert set(lint.PORT_SPEEDS), "spec/schemas/speeds.yaml loaded nothing"
    assert keys <= set(lint.PORT_SPEEDS), sorted(keys - set(lint.PORT_SPEEDS))


@pytest.mark.parametrize("model,ports", [
    ("AS5915-16X", ["port-13", "port-14", "port-15", "port-16"]),     # CSR180
    ("AS5915-18X", ["port-15", "port-16", "port-17", "port-18"]),     # CSR200
])
def test_the_csr_copper_ports_export_as_1000base_t(model, ports):
    """THE EIGHT PORTS THE SECOND SPELLING DROPPED. The CSR180's and CSR200's
    RJ45 traffic group said `100/1000base-t`, which had no IFACE_TYPE row, so
    their four copper ports each exported nothing, in every configuration."""
    found = [d for m, d in _exports() if m.startswith(model)]
    if not found:
        pytest.skip(f"{model} is not in this library")
    for d in found:
        got = {i["name"]: i["type"] for i in (d.get("interfaces") or [])}
        assert {p: got.get(p) for p in ports} == {p: "1000base-t" for p in ports}, d["model"]


def test_the_s9110_exports_its_out_of_band_jack():
    d = _export("S9110-32X")
    if d is None:
        pytest.skip("S9110-32X is not in this library")
    oob = [i for i in (d.get("interfaces") or []) if i["name"] == "oob"]
    assert oob == [{"name": "oob", "type": "1000base-t", "mgmt_only": True}], oob


def test_the_tm3312_ces_ports_export_as_t1_e1():
    """Eight CES ports, 3/1-3/8, each `other` labelled T1/E1 - each jack takes
    either line and nothing fixes which, so neither `t1` nor `e1` is true alone."""
    d = _export("TM-3312")
    assert d is not None, "TM-3312 is missing from the library exports"
    ces = [i for i in (d.get("interfaces") or []) if i["name"].startswith("port-3-")]
    assert ces == [{"name": f"port-3-{n}", "type": "other", "label": "T1/E1"} for n in range(1, 9)], ces


def test_the_xm8424h_exports_both_its_consoles():
    """CONSOLE is printed over an RJ45 and over a USB-A jack, and the data sheet lists a
    "USB console"; the device path knew only a USB-C console, so the USB-A one vanished."""
    d = _export("XM-8424H")
    assert d is not None, "XM-8424H is missing from the library exports"
    assert sorted((c["name"], c["type"]) for c in d.get("console-ports") or []) == [
        ("Console", "rj-45"), ("Console (USB-A)", "usb-a")]


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
    ("7926-40XKFB-O-AC-F", "mgmt-eth"),     # COR550: role: mgmt on the port, lamped part
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


# --- a card's ports are named per bay ----------------------------------------
#
# Two identical cards in one chassis both exported `p0`, and a component name is
# unique on its device in both targets, so the second install was rejected. A
# card's names now carry `{module}` and a bay's position is its whole id; the
# three tests below are the three halves of that, and the last one installs two
# cards the way NetBox would and reads the answer against the drawing.

def _module_exports():
    for p in sorted((LIB / "exports").glob("*/module-types/*/*.yaml")):
        yield p, yaml.safe_load(p.read_text()) or {}


def _resolve(name, position):
    """NetBox's rule for one bay level (dcim/utils.py resolve_module_placeholder
    at 9bcfd739): a single `{module}` is the position of the bay the card is in.
    Nautobot's `{module}` is the same (Module.render_component_names, f9cdca3d)."""
    assert name.count(dx.MODULE_TOKEN) == 1, name
    return name.replace(dx.MODULE_TOKEN, position)


def test_every_module_port_name_is_bay_scoped():
    bad, seen = [], 0
    for p, d in _module_exports():
        for key in dx.MODULE_PORT_KEYS:
            for row in d.get(key) or []:
                seen += 1
                if not str(row["name"]).startswith(dx.module_scoped("")):
                    bad.append(f"{p.parent.name}/{p.stem}: {key} {row['name']!r}")
    assert seen, "no module-type port was read - run ./publish.sh --no-images"
    assert not bad, "\n".join(bad[:20])


def test_no_device_type_puts_two_bays_at_one_position():
    """The position IS the `{module}` value. The trailing number alone put Fan 1,
    PSU 1 and slot-1 all at `1` on 167 of 205 bayed devices."""
    bad, seen = [], 0
    for p in sorted((LIB / "exports").glob("*/device-types/*/*.yaml")):
        bays = (yaml.safe_load(p.read_text()) or {}).get("module-bays") or []
        seen += len(bays)
        pos = [b["position"] for b in bays]
        dupes = {x for x in pos if pos.count(x) > 1}
        if dupes:
            bad.append(f"{p.parent.parent.name}/{p.stem}: {sorted(dupes)}")
    assert seen, "no module bay was read - run ./publish.sh --no-images"
    assert not bad, "\n".join(bad)


def test_two_identical_cards_install_as_the_drawing_names_them():
    """The DCP-2 as drawn with a DCP-404 in each traffic slot - the chassis the
    bug was worst on, its fan, first PSU and first slot all at position `1`.

    Installed as NetBox would install them, the two cards' ports do not collide,
    and every name is the drawing's path to that port with `/module/` taken out.
    """
    dev_p = LIB / "exports/netbox/device-types/Smartoptics/DCP-2.yaml"
    card_p = LIB / "exports/netbox/module-types/Smartoptics/DCP-404.yaml"
    face_p = LIB / "dist/dcp-2.dcp-404-x2.front.svg"
    missing = [p.name for p in (dev_p, card_p, face_p) if not p.exists()]
    if missing:
        pytest.skip(f"not built: {', '.join(missing)} - run ./publish.sh --no-images")
    dev = yaml.safe_load(dev_p.read_text())
    card = yaml.safe_load(card_p.read_text())
    face = face_p.read_text()
    positions = {b["name"]: b["position"] for b in dev["module-bays"]}
    names = [_resolve(i["name"], positions[bay])
             for bay in ("slot-1", "slot-2") for i in card["interfaces"]]
    assert len(names) == len(set(names)) == 2 * len(card["interfaces"]) > 0
    for n in names:
        bay, port = n.split("/", 1)
        assert f'data-path="{bay}/module/{port}"' in face, n


# --- a module's own bays -------------------------------------------------------

def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    p = LIB / "components" / ns / name / f"v{major}" / "contract.yaml"
    return load_yaml(p) if p.exists() else None


def _nested_bays(ref, seen=()):
    """Every bay id a module offers, through whatever it seats in turn."""
    c = _contract(ref)
    bays = (c or {}).get("bays") or {}
    if not isinstance(bays, dict) or ref in seen:
        return
    for bid, b in bays.items():
        yield bid
        for sub in (b or {}).get("accepts") or []:
            yield from _nested_bays(sub, seen + (ref,))


def test_a_module_exports_the_bays_it_declares():
    """A riser's slots are bays of the riser. No contract that declared `bays:`
    exported a module bay, so a DCIM had nowhere to seat a card."""
    bad, seen = [], 0
    for p in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = load_yaml(p)
        bays = c.get("bays")
        if c.get("kind") != "module" or not isinstance(bays, dict) or not bays:
            continue
        seen += 1
        doc = dx.build_module(c, "X")
        got = sorted(b["position"] for b in doc.get("module-bays") or [])
        if got != sorted(bays):
            bad.append(f"{p.parent.parent.name}: declares {sorted(bays)}, exports {got}")
    assert seen, "no module with bays was read"
    assert not bad, "\n".join(bad)


def _nested_paths(ref, prefix, seen=()):
    """Every nested bay under a module seated at `prefix`, as NetBox resolves it."""
    c = _contract(ref)
    bays = (c or {}).get("bays") or {}
    if not isinstance(bays, dict) or ref in seen:
        return
    for bid, b in bays.items():
        pos = f"{prefix}/{bid}"
        yield pos
        for sub in (b or {}).get("accepts") or []:
            yield from _nested_paths(sub, pos, seen + (ref,))


def test_a_nested_bay_is_written_for_netbox_and_not_for_nautobot():
    """`nested_bays_for`: NetBox templates a bay's position and Nautobot does not,
    so one gets `{module}/mic0` and the other no nested bay at all."""
    doc = {"model": "X", "module-bays": [{"name": "mic0", "position": "mic0"}],
           "interfaces": [{"name": "{module}/port-1"}]}
    nb = dx.nested_bays_for(doc, "netbox")
    assert nb["module-bays"] == [{"name": "{module}/mic0", "position": "{module}/mic0"}]
    assert "module-bays" not in dx.nested_bays_for(doc, "nautobot")
    assert doc["module-bays"][0]["position"] == "mic0", "the built document was changed"
    plain = {"model": "Y", "interfaces": []}
    assert dx.nested_bays_for(plain, "nautobot") is plain


def test_the_written_module_types_carry_nested_bays_only_for_netbox():
    """The files, not the function: every NetBox module type carries exactly the
    bays its contract declares, templated, and its Nautobot twin carries none."""
    nb = LIB / "exports/netbox/module-types"
    if not nb.exists():
        pytest.skip("not published - run ./publish.sh --no-images")
    declared = {}
    for p in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = load_yaml(p)
        if c.get("kind") == "module" and isinstance(c.get("bays"), dict) and c["bays"]:
            model = str((c.get("attrs") or {}).get("model") or c["name"]).replace("/", "-")
            declared.setdefault(model, set()).add(frozenset(c["bays"]))
    seen = 0
    for p in sorted(nb.glob("*/*.yaml")):
        bays = (yaml.safe_load(p.read_text()) or {}).get("module-bays") or []
        if not bays:
            assert p.stem not in declared, f"{p}: its contract declares bays and it exports none"
            continue
        seen += 1
        for b in bays:
            assert b["name"] == b["position"] and b["position"].startswith("{module}/"), (p, b)
        got = frozenset(b["position"].split("/", 1)[1] for b in bays)
        assert got in declared.get(p.stem, ()), f"{p}: exports {sorted(got)}"
        twin = LIB / "exports/nautobot/module-types" / p.parent.name / p.name
        assert twin.exists(), twin
        assert "module-bays" not in (yaml.safe_load(twin.read_text()) or {}), twin
    assert seen, "no module type with a nested bay was read - run ./publish.sh --no-images"


def _resolve_bay(template, parent_position):
    """NetBox's resolve_position on a nested bay: one `{module}`, the parent's."""
    return template.replace(dx.MODULE_TOKEN, parent_position)


def test_a_card_in_a_riser_slot_installs_as_the_drawing_names_it():
    """The nested sibling of the DCP-2 test, on the DL160 Gen10 as drawn with a
    card in each slot of its primary riser. Installed as NetBox installs them -
    the riser into the chassis' bay, each card into the bay the riser brought -
    every port is the drawing's path to it with each `/module/` taken out."""
    ex = LIB / "exports/netbox"
    dev_p = ex / "device-types/HPE/878972-B21.yaml"
    riser_p = ex / "module-types/HPE/riser-primary-dl160.yaml"
    cards = {"slot-1": ex / "module-types/NVIDIA/MCX515A tall bracket.yaml",
             "slot-2": ex / "module-types/NVIDIA/MCX516A short bracket.yaml"}
    face_p = LIB / "dist/dl160-gen10.lff4-options.rear.svg"
    missing = [p.name for p in (dev_p, riser_p, face_p, *cards.values()) if not p.exists()]
    if missing:
        pytest.skip(f"not built: {', '.join(missing)} - run ./publish.sh --no-images")
    dev = yaml.safe_load(dev_p.read_text())
    riser = yaml.safe_load(riser_p.read_text())
    face = face_p.read_text()
    outer = {b["name"]: b["position"] for b in dev["module-bays"]}["riser-primary"]
    inner = {_resolve_bay(b["name"], outer): _resolve_bay(b["position"], outer)
             for b in riser["module-bays"]}
    assert sorted(inner) == ["riser-primary/slot-1", "riser-primary/slot-2"]
    names = []
    for slot, card_p in cards.items():
        card = yaml.safe_load(card_p.read_text())
        assert card["interfaces"], card_p
        names += [_resolve(i["name"], inner[f"riser-primary/{slot}"]) for i in card["interfaces"]]
    assert len(names) == len(set(names)) == 3, names
    for n in names:
        bay, slot, port = n.split("/", 2)
        assert f'data-path="{bay}/module/{slot}/module/{port}"' in face, n


def test_two_line_cards_each_bring_their_own_nested_bays():
    """What the first design got wrong. With a nested bay positioned by its own
    id, the MIC bays of the MPCs in two FPC slots were one position, and the
    MICs in them named their ports alike."""
    p = LIB / "exports/netbox/module-types/Juniper/MX-MPC2E-3D.yaml"
    if not p.exists():
        pytest.skip("not published - run ./publish.sh --no-images")
    mpc = yaml.safe_load(p.read_text())
    assert mpc.get("module-bays"), p
    resolved = [_resolve_bay(b["position"], fpc) for fpc in ("fpc0", "fpc1") for b in mpc["module-bays"]]
    assert len(resolved) == len(set(resolved)) == 2 * len(mpc["module-bays"])
    assert "fpc0/mic0" in resolved and "fpc1/mic0" in resolved


def test_no_two_nested_bays_on_a_device_resolve_to_one_position():
    """The position a nested bay takes once NetBox has resolved `{module}` is its
    path from the chassis: `fpc3/mic0`. No two may land on one path, and each
    has to fit the 30 characters NetBox gives a bay's position."""
    bad, seen = [], 0
    for p in sorted((LIB / "devices").glob("*/*/device.yaml")):
        dev = load_yaml(p)
        owner = {}
        for vname, view in (dev.get("views") or {}).items():
            for b in view_parts(view)["bays"]:
                for ref in b.get("accepts") or []:
                    for pos in set(_nested_paths(ref, b["id"])):
                        seen += 1
                        if len(pos) > 30:
                            bad.append(f"{p.parent.name}: `{pos}` is {len(pos)} characters")
                        owner.setdefault(pos, set()).add((vname, b["id"]))
        for pos, under in sorted(owner.items()):
            if len({bid for _v, bid in under}) > 1:
                bad.append(f"{p.parent.name}: `{pos}` is reached from {sorted(under)}")
    assert seen, "no nested bay was read"
    assert not bad, "\n".join(sorted(set(bad))[:30])

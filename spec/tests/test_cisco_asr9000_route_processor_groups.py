"""Every port on an ASR 9000 route processor and modular port adapter belongs to a group.

A card's ports used to carry no group, so a port on a module seated in a bay could not say
what it was for or what rate it ran at. These are the route switch processors, route
processors and modular port adapters whose contracts compose a port part: each declares
`groups:` and every port part joins one.

A group or a port states a `media` or a `speed` only where a held Cisco document prints it:

  - Cisco ASR 9000 Series Aggregation Services Router Overview and Reference Guide: the
    management Ethernet ports are "dual-speed 100/1000 Mbit" and "triple-speed RJ-45", both
    of which top out at 1 Gbit, so `1g`; the CMP port is a "management Ethernet port" with no
    rate printed, so it states none; the console and auxiliary ports are EIA/TIA-232 RJ-45
    serial ports; the SFP/SFP+ ports are "10-GE";
  - Cisco ASR 9000 Series Aggregation Services Router Ethernet Line Card Installation Guide:
    its comparison table gives each modular port adapter's port count and cage (SFP, SFP+,
    XFP, QSFP+), and each adapter's own name its rate.

The SYNC, 1588, time-of-day and inter-chassis sync jacks, the SMB clock inputs, the USB port
and the alarm connector print no data rate; they state none.
"""
import re
from pathlib import Path

import pytest
import yaml

from portrayal import lint

LIB = Path(__file__).resolve().parents[2] / "library"
COMPONENTS = LIB / "components" / "cisco"

PORT_REFS = {
    "std/rj45-ganged@2", "common/rj45-ganged-eth@1", "std/smb@1", "std/usb-a@1",
    "common/db9-receptacle@1", "std/sfp-ganged@1", "std/qsfp28@1", "std/xfp@1", "std/sfp@1",
}

# route processor port id -> (group, media or None, speed or None)
RP_PORTS = {
    "mgt-lan-0": ("mgmt", "rj45", "1g"),
    "mgt-lan-1": ("mgmt", "rj45", "1g"),
    "cmp": ("mgmt", "rj45", None),
    "console": ("mgmt", "rj45-serial", None),
    "aux": ("mgmt", "rj45-serial", None),
    "usb": ("mgmt", None, None),
    "sync-0": ("timing", "rj48", None),
    "sync-1": ("timing", "rj48", None),
    "ieee-1588": ("timing", "rj45-tod", None),
    "ics-0": ("timing", "rj45-tod", None),
    "ics-1-tod": ("timing", "rj45-tod", None),
    "nv-sync-0": ("timing", "rj45-tod", None),
    "nv-sync-1-tod": ("timing", "rj45-tod", None),
    "gps-10mhz": ("timing", None, None),
    "gps-1pps": ("timing", None, None),
    "alarm-out": ("alarm", None, None),
}

# component -> (major, port count, {group: (role, media, speed)})
# a mixed group states no media or speed of its own
LEGACY = {"mgmt": ("management", None, None), "timing": ("management", "rj48", None),
          "alarm": ("management", None, None)}
MIXED = {"mgmt": ("management", None, None), "timing": ("management", None, None),
         "alarm": ("management", None, None)}
CLUSTER = {"sfp-plus-fabric": ("fabric", "sfp-plus", "10g")}
EXPECTED = {
    "a9k-rsp": (2, 7, LEGACY),
    "a9k-rsp-8g": (2, 7, LEGACY),
    "a9k-rsp440-se": (2, 15, {**MIXED, **CLUSTER}),
    "a9k-rsp440-tr": (2, 15, {**MIXED, **CLUSTER}),
    "a9k-rsp5-se": (2, 14, MIXED),
    "a9k-rsp5-tr": (2, 14, MIXED),
    "a9k-rsp880-se": (2, 18, {**MIXED, **CLUSTER}),
    "a9k-rsp880-tr": (2, 18, {**MIXED, **CLUSTER}),
    "a9k-rsp880-lt-se": (2, 14, MIXED),
    "a9k-rsp880-lt-tr": (2, 14, MIXED),
    "a99-rp3-se": (2, 14, MIXED),
    "a99-rp3-tr": (2, 14, MIXED),
    "a99-rsp-se": (2, 18, {**MIXED, **CLUSTER}),
    "asr-9922-rp-se": (2, 15, {**MIXED, "sfp-plus": ("traffic", "sfp-plus", "10g")}),
    "asr-9922-rp-tr": (2, 15, {**MIXED, "sfp-plus": ("traffic", "sfp-plus", "10g")}),
    "a9k-mpa-1x40ge": (1, 1, {"qsfp-40g": ("traffic", "qsfp", "40g")}),
    "a9k-mpa-2x40ge": (1, 2, {"qsfp-40g": ("traffic", "qsfp", "40g")}),
    "a9k-mpa-2x10ge": (1, 2, {"xfp": ("traffic", "xfp", "10g")}),
    "a9k-mpa-4x10ge": (1, 4, {"xfp": ("traffic", "xfp", "10g")}),
    "a9k-mpa-8x10ge": (1, 8, {"sfp-plus": ("traffic", "sfp-plus", "10g")}),
    "a9k-mpa-20x10ge": (1, 20, {"sfp-plus": ("traffic", "sfp-plus", "10g")}),
    "a9k-mpa-20x1ge": (1, 20, {"sfp": ("traffic", "sfp", "1g")}),
}
ROLES = {"traffic", "fabric", "management", "service", "indicator", "furniture"}


def _contract(name):
    major = EXPECTED[name][0]
    return yaml.safe_load((COMPONENTS / name / f"v{major}" / "contract.yaml").read_text())


def _ports(data):
    return [p for p in data.get("parts") or [] if p.get("ref") in PORT_REFS]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_port_part_joins_a_declared_group(name):
    data = _contract(name)
    groups = data.get("groups") or {}
    ports = _ports(data)
    assert len(ports) == EXPECTED[name][1], f"{name}: port count"
    assert groups, f"{name} declares no groups"
    for p in ports:
        assert p.get("group") in groups, f"{name}: port {p['id']} is in no declared group"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_group_states_the_role_media_and_speed_the_sources_give(name):
    groups = _contract(name).get("groups") or {}
    expected = EXPECTED[name][2]
    assert set(groups) == set(expected)
    for gname, (role, media, speed) in expected.items():
        g = groups[gname]
        attrs = g.get("attrs") or {}
        assert g.get("role") == role and role in ROLES, f"{name}/{gname} role"
        assert attrs.get("media") == media, f"{name}/{gname} media"
        # a rate no held document states is left out, never taken from the cage
        assert attrs.get("speed") == speed, f"{name}/{gname} speed"
        assert g.get("term") == "Port"
        assert g.get("index-origin") == 0


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_no_group_is_empty(name):
    data = _contract(name)
    used = {p.get("group") for p in _ports(data)}
    assert set(data.get("groups") or {}) <= used


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_lint_finds_nothing_to_say_about_the_groups(name):
    data = _contract(name)
    with lint.collecting() as got:
        lint.lint_component_groups(f"components/cisco/{name}", data, [LIB])
    assert not got.errors and not got.warnings, (got.errors, got.warnings)


@pytest.mark.parametrize("name", [n for n in sorted(EXPECTED) if not n.startswith("a9k-mpa")])
def test_a_route_processor_port_states_what_its_document_prints(name):
    for p in _ports(_contract(name)):
        pid = p["id"]
        if re.fullmatch(r"sfp-plus-\d+", pid):
            continue  # the group states the cage and rate; the part states nothing of its own
        group, media, speed = RP_PORTS[pid]
        attrs = p.get("attrs") or {}
        assert p["group"] == group, f"{name}/{pid} group"
        assert attrs.get("media") == media, f"{name}/{pid} media"
        assert attrs.get("speed") == speed, f"{name}/{pid} speed"


@pytest.mark.parametrize("name", [n for n in sorted(EXPECTED) if n.startswith("a9k-mpa")])
def test_an_adapter_port_states_nothing_its_group_does_not(name):
    data = _contract(name)
    (gname,) = EXPECTED[name][2]
    for p in _ports(data):
        assert re.fullmatch(r"p\d+", p["id"])
        assert p["group"] == gname
        assert not p.get("attrs"), f"{name}/{p['id']}"


def test_only_the_management_ethernet_ports_state_a_speed_on_a_route_processor():
    fast = set()
    for name in EXPECTED:
        if name.startswith("a9k-mpa"):
            continue
        for p in _ports(_contract(name)):
            if (p.get("attrs") or {}).get("speed"):
                fast.add(p["id"])
    assert fast == {"mgt-lan-0", "mgt-lan-1"}

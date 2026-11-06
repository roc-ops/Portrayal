"""The front I/O and lamp groups of six Dell servers are named for what they hold.

A group called `ports` or `leds` names nothing. On the R740xd the front I/O group is
`local-access` and the lamp under the iDRAC Direct port is `port-leds`; these six servers
carry the same front panel and take the same names. The tests read the device files, so a
port or lamp cannot be lost or left in the old group by the rename.
"""
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "devices"

DEVICES = ("dell/r660", "dell/r660xs", "dell/r6615", "dell/r6625", "dell/r760", "dell/r960")

# Views that draw the front I/O, and what each holds: ids and the part each one is.
FRONT_IO = {"usb-1": "std/usb-a@1", "idrac-direct": "std/micro-usb@1", "vga": "std/vga@1"}
LAMP = "idrac-direct-led"


def load(key):
    with open(LIB / key / "device.yaml") as fh:
        return yaml.safe_load(fh)


def placements(dev):
    for vname, view in (dev.get("views") or {}).items():
        for p in ((view.get("components") or {}).get("placements") or []):
            yield vname, p


@pytest.mark.parametrize("key", DEVICES)
def test_no_vague_group_is_declared_or_used(key):
    dev = load(key)
    assert not {"leds", "ports"} & set(dev["groups"]), f"{key} still declares a vague group"
    used = {p.get("group") for _, p in placements(dev)}
    assert not {"leds", "ports"} & used, f"{key} still places something in a vague group"


@pytest.mark.parametrize("key", DEVICES)
def test_local_access_holds_the_usb_micro_usb_and_vga_ports(key):
    dev = load(key)
    group = dev["groups"]["local-access"]
    assert group["role"] == "management" and group["term"] == "Port"
    assert group["mixed"] == "local console and service access"
    by_view = {}
    for vname, p in placements(dev):
        if p.get("group") == "local-access":
            by_view.setdefault(vname, {})[p["id"]] = p["ref"]
    assert by_view, f"{key} places nothing in local-access"
    for vname, got in by_view.items():
        assert got == FRONT_IO, f"{key} {vname} local-access holds {got}"


@pytest.mark.parametrize("key", DEVICES)
def test_port_leds_holds_the_lamp_that_belongs_to_the_micro_usb_port(key):
    dev = load(key)
    assert dev["groups"]["port-leds"]["role"] == "indicator"
    seen = 0
    for vname, p in placements(dev):
        if p.get("group") == "port-leds":
            seen += 1
            assert p["id"] == LAMP
            assert p["for"] == "idrac-direct", f"{key} {vname}: the lamp names {p['for']!r}"
    assert seen, f"{key} places nothing in port-leds"


@pytest.mark.parametrize("key", DEVICES)
def test_every_member_of_a_group_holds_a_position_of_its_own(key):
    dev = load(key)
    for group in ("local-access", "port-leds"):
        for vname in dev["views"]:
            ranks = [p["rel-pos"] for v, p in placements(dev)
                     if v == vname and p.get("group") == group]
            assert len(ranks) == len(set(ranks)), f"{key} {vname} {group}: {ranks}"

"""A lamp or port group is named for what it holds, and no two members of one group share a position.

A group called `leds` or `ports` names nothing, and the tree numbers a group's members by
`rel-pos`, so two lamps at one position leave that numbering ambiguous. These tests read the
seven device files this change settled and hold the ids each renamed group took over, so a
lamp cannot be lost or moved to the wrong family in the rename.
"""
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "devices"

VAGUE = {"leds", "ports"}

# (view, id) pairs each device held before the rename; the rename adds and drops none.
PLACEMENT_COUNT = {
    "dell/r740xd": 154,
    "edgecore/as7326-56x": 176,
    "edgecore/as7726-32x": 71,
    "edgecore/cor580": 80,
    "edgecore/dcs510": 98,
    "halny/hlx-tgv": 17,
    "ufispace/s8901-54xc": 171,
}

# new group -> the (view, id) pairs the old `leds` or `ports` group held and it took over.
TOOK_OVER = {
    "dell/r740xd": {
        "local-access": [("front", "usb-1"), ("front", "usb-2"), ("front", "idrac-direct"),
                         ("front", "vga"), ("front-lff-12", "usb-1"), ("front-lff-12", "usb-2"),
                         ("front-lff-12", "idrac-direct"), ("front-lff-12", "vga")],
        "port-leds": [("front", "idrac-direct-led"), ("front-lff-12", "idrac-direct-led")],
        "system-leds": [("rear", "sys-status")],
    },
    "edgecore/as7326-56x": {
        "system-leds": [("front", i) for i in
                        ("led-diag", "led-loc", "led-psu1", "led-psu2", "led-fan")],
    },
    "edgecore/as7726-32x": {
        "system-leds": [("front", i) for i in
                        ("led-diag", "led-loc", "led-fan", "led-psu1", "led-psu2")],
        "sfp-mgmt-leds": [("front", "sfp-leds")],
    },
    "edgecore/cor580": {
        "system-leds": [("front", i) for i in
                        ("led-sys-loc", "led-diag", "led-fan", "led-psu1", "led-psu2")],
        "oob-leds": [("front", "led-oob-0"), ("front", "led-oob-1")],
    },
    "edgecore/dcs510": {
        "system-leds": [("front", i) for i in
                        ("led-loc", "led-diag", "led-fan", "led-ps1", "led-ps2")],
        "sfp-mgmt-leds": [("front", "led-mgmt-sfp-1"), ("front", "led-mgmt-sfp-2")],
    },
    "halny/hlx-tgv": {
        "status-leds": [("top", i) for i in
                        ("led-power", "led-pon", "led-los", "led-net",
                         "led-lan", "led-10g", "led-tel1", "led-tel2")],
    },
}


def load(key):
    with open(LIB / key / "device.yaml") as fh:
        return yaml.safe_load(fh)


def members(dev):
    """Every placement and bay as (view name, entry)."""
    for vname, view in (dev.get("views") or {}).items():
        comp = view.get("components") or {}
        for p in (comp.get("placements") or []) + (comp.get("bays") or []):
            yield vname, p


def in_configuration(entry, config):
    only = entry.get("only-in")
    return not only or config in only


@pytest.mark.parametrize("key", sorted(PLACEMENT_COUNT))
def test_no_group_is_named_leds_or_ports(key):
    dev = load(key)
    assert not VAGUE & set(dev["groups"]), f"{key} still declares a vague group"
    used = {p.get("group") for _, p in members(dev)}
    assert not VAGUE & used, f"{key} still places something in a vague group"


@pytest.mark.parametrize("key", sorted(TOOK_OVER))
def test_each_new_group_holds_what_the_old_one_held(key):
    dev = load(key)
    for group, ids in TOOK_OVER[key].items():
        assert group in dev["groups"], f"{key} does not declare {group}"
        got = sorted((v, p["id"]) for v, p in members(dev) if p.get("group") == group)
        assert got == sorted(ids), f"{key} {group} holds {got}"


@pytest.mark.parametrize("key", sorted(PLACEMENT_COUNT))
def test_no_placement_was_lost_or_added(key):
    pairs = {(v, p["id"]) for v, p in members(load(key))}
    assert len(pairs) == PLACEMENT_COUNT[key]


@pytest.mark.parametrize("key", sorted(TOOK_OVER))
def test_a_replaced_group_is_declared_as_lamps_or_ports(key):
    dev = load(key)
    for group in TOOK_OVER[key]:
        term = dev["groups"][group].get("term")
        assert term in {"LED", "Port"}, f"{key} {group} has term {term!r}"


def test_the_lane_lamps_of_the_qsfp28_ports_each_hold_a_position():
    dev = load("ufispace/s8901-54xc")
    lamps = [p for v, p in members(dev) if v == "front" and p.get("group") == "port-leds"]
    positions = [p["rel-pos"] for p in lamps]
    assert len(positions) == len(set(positions)), "two port lamps share a position"
    lanes = [p for p in lamps if "lane" in (p.get("attrs") or {})]
    assert len(lanes) == 24
    ranked = sorted(lanes, key=lambda p: (int(p["attrs"]["port"]), int(p["attrs"]["lane"])))
    assert [p["rel-pos"] for p in ranked] == list(range(48, 72)), \
        "lane lamps are not numbered by port, then lane"


def test_the_r740xd_rear_furniture_holds_one_position_each_in_every_configuration():
    dev = load("dell/r740xd")
    rear = [p for v, p in members(dev) if v == "rear" and p.get("group") == "furniture"]
    for config in dev["configurations"]:
        seen = {}
        for p in rear:
            if in_configuration(p, config):
                seen.setdefault(p["rel-pos"], []).append(p["id"])
        clashes = {pos: ids for pos, ids in seen.items() if len(ids) > 1}
        assert not clashes, f"{config}: {clashes}"

"""The MaiaEdge Port Extender files its 56 ports under a group named for what they are.

A group called `ports` names no port family. The device's 48 SFP28 tenant ports and 8 QSFP28
uplinks are numbered 1 to 56 in one space by the vendor, so they stay one group; the group is
named `front-ports`, as Arista, Juniper and Oscilloquartz devices name the ports of their front panel. A group
name is published as `data-group`, so these tests hold what the rename must keep: every port id,
one group holding all 56, and the lamps, rear jacks and furniture where they were.
"""
from pathlib import Path

import pytest
import yaml

LIB = Path(__file__).resolve().parents[2] / "library" / "devices" / "maiaedge" / "port-extender"
GROUP = "front-ports"
PORT_IDS = [f"port-{n}" for n in range(1, 57)]


def _load(name):
    with open(LIB / name) as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def device():
    return _load("device.yaml")


def _front(dev):
    return dev["views"]["front"]["components"]["placements"]


def test_the_ports_group_is_named_for_the_front_panel(device):
    assert GROUP in device["groups"]
    assert "ports" not in device["groups"]


def test_no_placement_is_filed_under_the_old_name(device):
    for view, body in device["views"].items():
        for p in (body.get("components") or {}).get("placements") or []:
            assert p.get("group") != "ports", f"{view}: {p['id']} is still in `ports`"


def test_all_56_port_ids_are_unchanged_and_in_the_one_group(device):
    ports = [p for p in _front(device) if str(p["id"]).startswith("port-")]
    assert sorted(p["id"] for p in ports) == sorted(PORT_IDS)
    assert {p["group"] for p in ports} == {GROUP}


def test_the_group_still_numbers_its_ports_one_to_fifty_six(device):
    g = device["groups"][GROUP]
    assert g["role"] == "traffic" and g["term"] == "Port" and g["index-origin"] == 1
    assert "mixed" in g, "the group holds two media and must say so"
    positions = sorted(p["rel-pos"] for p in _front(device) if p.get("group") == GROUP)
    assert positions == list(range(1, 57))


def test_each_port_still_carries_its_own_media(device):
    media = {p["id"]: p["attrs"]["media"] for p in _front(device) if p.get("group") == GROUP}
    assert sum(1 for m in media.values() if m == "sfp28") == 48
    assert sum(1 for m in media.values() if m == "qsfp28") == 8


def test_the_lamps_and_the_other_groups_stay(device):
    assert [g for g in device["groups"]] == [GROUP, "port-leds", "mgmt", "psus", "fans", "furniture"]
    lamps = [p for p in _front(device) if p.get("group") == "port-leds"]
    assert sorted(p["id"] for p in lamps) == sorted(f"led-port-{n}" for n in range(1, 57))


def test_the_layout_blocks_that_generate_the_ports_name_the_same_group():
    layout = _load("layout.yaml")
    assert GROUP in layout["groups"] and "ports" not in layout["groups"]
    blocks = layout["views"]["front"]["components"]["blocks"]
    assert [b["id"] for b in blocks] == [GROUP] * 4

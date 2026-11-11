"""The Port Extender files its ports and lamps under the names of their port families.

The 48 SFP28 tenant ports and the 8 QSFP28 uplinks keep the vendor's one numbering
(1-56); only the groups they are filed under are named for the family, as the
library's other 48 + 8 devices name theirs.
"""
import collections
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "maiaedge" / "port-extender" / "device.yaml"


def _placements():
    device = yaml.safe_load(DEVICE.read_text())
    out = []
    for view in (device.get("views") or {}).values():
        out.extend(((view.get("components") or {}).get("placements")) or [])
    return device, out


def _by_id():
    _, placements = _placements()
    return {p["id"]: p for p in placements}


def test_port_family_groups_declared():
    device, _ = _placements()
    groups = device["groups"]
    for name in ("sfp28", "qsfp28", "sfp28-leds", "qsfp28-leds"):
        assert name in groups
    for name in ("ports", "port-leds"):
        assert name not in groups
    assert groups["sfp28"]["attrs"] == {"media": "sfp28", "speed": "25g"}
    assert groups["qsfp28"]["attrs"] == {"media": "qsfp28", "speed": "100g"}


def test_tenant_ports_in_sfp28():
    by_id = _by_id()
    for n in range(1, 49):
        p = by_id[f"port-{n}"]
        assert p["group"] == "sfp28"
        assert p["rel-pos"] == n
        assert p["attrs"]["media"] == "sfp28"


def test_uplinks_in_qsfp28():
    by_id = _by_id()
    for n in range(49, 57):
        p = by_id[f"port-{n}"]
        assert p["group"] == "qsfp28"
        assert p["rel-pos"] == n
        assert p["attrs"]["media"] == "qsfp28"


def test_all_ports_and_lamps_still_exist():
    by_id = _by_id()
    for n in range(1, 57):
        assert f"port-{n}" in by_id
        assert f"led-port-{n}" in by_id


def test_each_lamp_is_in_the_lamp_group_of_its_port():
    by_id = _by_id()
    for n in range(1, 57):
        want = by_id[f"port-{n}"]["group"] + "-leds"
        assert by_id[f"led-port-{n}"]["group"] == want


def test_no_group_repeats_a_rel_pos():
    _, placements = _placements()
    seen = collections.defaultdict(list)
    for p in placements:
        seen[(p["group"], p["rel-pos"])].append(p["id"])
    assert {k: v for k, v in seen.items() if len(v) > 1} == {}

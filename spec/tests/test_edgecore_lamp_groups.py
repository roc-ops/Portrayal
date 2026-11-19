"""The lamps of five Edgecore routers and switches are grouped by the port family they report on.

On the AGR110, AGR130, AGR560, CSR310 and ECS4120-28Fv2-I the front lamps of several port
families sat in one group, `port-leds`, and each family counted its lamps from its own port
numbers, so members of the group shared a position. A position names one member, so each
unlike family of lamps now has a group of its own, named for its port family as the library
names lamp groups elsewhere (`qsfp28-leds`, `qsfpdd-leds`), with the lamp lines the ports'
group states: the LED term, the indicator role and the port family's first index.

These read the device files and the lint baseline, not the build.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal.manifest import resolve_views, view_parts

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# device -> {lamp group: the port group every lamp in it reports on}
FAMILIES = {
    "edgecore/agr110": {"port-leds": "sfp-plus", "qsfp28-leds": "qsfp28"},
    "edgecore/agr130": {"port-leds": "sfp-plus", "qsfp28-leds": "qsfp28"},
    "edgecore/agr560": {"port-leds": "sfp-plus", "qsfp28-leds": "qsfp28", "qsfpdd-leds": "qsfp-dd"},
    "edgecore/csr310": {"sfp28-leds": "sfp28"},
    "edgecore/ecs4120-28fv2-i": {"rj45-combo-leds": "rj45-combo"},
}
NEW_GROUPS = [(dev, grp) for dev, fam in FAMILIES.items() for grp in fam if grp != "port-leds"]


def load(device):
    with open(LIB / "devices" / device / "device.yaml") as fh:
        return yaml.safe_load(fh)


def front_items(data):
    """(configuration, item) for every bay and placement a configuration draws on its front."""
    for cname, cfg in (data.get("configurations") or {"default": {}}).items():
        for face, (_vname, view) in sorted(resolve_views(data, cfg).items()):
            if face != "front":
                continue
            vp = view_parts(view)
            for item in vp["bays"] + vp["placements"]:
                if item.get("only-in") and cname not in item["only-in"]:
                    continue
                yield cname, item


def port_group_of(data, port_id):
    for _cname, item in front_items(data):
        if item.get("id") == port_id:
            return item.get("group")
    return None


@pytest.mark.parametrize("device", sorted(FAMILIES))
def test_no_group_gives_two_front_members_one_position(device):
    seen = {}
    for cname, item in front_items(load(device)):
        if item.get("group") is not None and item.get("rel-pos") is not None:
            seen.setdefault((cname, item["group"], item["rel-pos"]), []).append(item["id"])
    clashes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not clashes, f"{device}: {clashes}"


@pytest.mark.parametrize("device", sorted(FAMILIES))
def test_each_lamp_group_holds_the_lamps_of_one_port_family(device):
    data = load(device)
    items = list(front_items(data))
    for group, family in FAMILIES[device].items():
        lamps = [i for _c, i in items if i.get("group") == group]
        assert lamps, f"{device}: the group {group} holds no front lamp"
        for lamp in lamps:
            ports = lamp["for"] if isinstance(lamp.get("for"), list) else [lamp.get("for")]
            groups = {port_group_of(data, p) for p in ports}
            assert groups == {family}, f"{device}: {lamp['id']} in {group} reports on ports in {sorted(map(str, groups))}"


@pytest.mark.parametrize("device,group", NEW_GROUPS)
def test_a_new_lamp_group_is_declared_like_the_library_declares_one(device, group):
    data = load(device)
    family = FAMILIES[device][group]
    assert group in data["groups"], f"{device} does not declare {group}"
    decl = data["groups"][group]
    assert decl["term"] == "LED" and decl["role"] == "indicator", decl
    assert decl["index-origin"] == data["groups"][family]["index-origin"], decl


@pytest.mark.parametrize("device", ["edgecore/agr110", "edgecore/agr130"])
def test_a_qsfp28_status_lamp_takes_its_ports_number(device):
    data = load(device)
    lamps = {i["id"]: i for _c, i in front_items(data) if i.get("group") == "qsfp28-leds"}
    for n in range(6):
        assert lamps[f"led-uplink-{n}"]["rel-pos"] == n, f"{device}: led-uplink-{n}"


def test_the_lint_baseline_holds_no_rel_pos_entry_for_the_five():
    with open(LIB / "lint-baseline.json") as fh:
        baseline = json.load(fh)
    held = {f"devices/{d}/device.yaml": baseline.get(f"devices/{d}/device.yaml", {}) for d in FAMILIES}
    assert not {k: v for k, v in held.items() if "L144" in v}, held

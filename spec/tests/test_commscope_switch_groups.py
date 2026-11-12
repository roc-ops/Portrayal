"""The CommScope CH3000 alternate-routing and optical switches say what their ports are for.

An AB32S1G or AB32S1T A/B alternate-routing switch composes three F-type jacks (inputs A and B and the
output), and the OS32M2B dual 2x1 optical switch composes six SC/APC bores (an A input, a B input and an
output for each of its two switches). Without a group a port on a switch seated in a chassis is drawn with
no `data-group` and no `data-group-role`. Each of the three contracts below declares `groups:` in the
device shape, and each of its port parts joins one.

What these hold for every switch in the list:

  - it declares at least one group, and every port part joins a declared group;
  - every declared group has a term, a role from the schema's list, an index origin of 0 or 1, a
    description, and at least one member;
  - a group is one connector family (one interface), and its declared media agrees with each member's;
  - the data sheets print no data rate for an RF or an optical switch, so no group and no part states a
    speed;
  - the inputs and the output of a switch carry the work the switch is for, so the group is `traffic`.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

# switch -> {group: (role, media, interface, member part ids)}
SWITCHES = {
    "commscope/ab32s1g@1": {
        "rf": ("traffic", "coax-f", "f-type", ["rf-in-a", "rf-out", "rf-in-b"]),
    },
    "commscope/ab32s1t@1": {
        "rf": ("traffic", "coax-f", "f-type", ["rf-in-a", "rf-out", "rf-in-b"]),
    },
    "commscope/os32m2b@1": {
        "optical": ("traffic", "fiber", "sc", ["in-a1", "out-1", "in-b1", "in-a2", "out-2", "in-b2"]),
    },
}

ROLES = set(json.loads((SPEC / "schemas/component.schema.json").read_text())
            ["$defs"]["group"]["properties"]["role"]["enum"])


def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / ns / name / f"v{major}" / "contract.yaml").read_text())


def _is_port(ref):
    return _contract(ref).get("class") == "port"


def _ports(ref):
    return [p for p in _contract(ref).get("parts") or [] if _is_port(p["ref"])]


def _media(part):
    own = (part.get("attrs") or {}).get("media")
    return own or (_contract(part["ref"]).get("attrs") or {}).get("media")


def _interface(part):
    return _contract(part["ref"]).get("interface")


def test_the_list_is_three_distinct_switches():
    assert len(SWITCHES) == 3


@pytest.mark.parametrize("ref", SWITCHES)
def test_every_port_part_joins_a_declared_group(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} composes ports and declares no groups"
    ports = _ports(ref)
    assert ports, f"{ref} composes no port part"
    for part in ports:
        assert part.get("group") in groups, \
            f"{ref}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@pytest.mark.parametrize("ref", SWITCHES)
def test_every_group_says_what_it_is_for_and_has_members(ref):
    members = {}
    for part in _ports(ref):
        members.setdefault(part.get("group"), []).append(part["id"])
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} declares no groups"
    for name, group in groups.items():
        assert group.get("term"), f"{ref}: group {name} has no term"
        assert group.get("role") in ROLES, f"{ref}: group {name} role {group.get('role')!r}"
        assert group.get("index-origin") in (0, 1), f"{ref}: group {name} index-origin"
        assert (group.get("description") or "").strip(), f"{ref}: group {name} has no description"
        assert members.get(name), f"{ref}: group {name} has no member"


@pytest.mark.parametrize("ref", SWITCHES)
def test_each_group_is_the_role_and_the_members_the_data_sheet_gives(ref):
    groups = _contract(ref).get("groups") or {}
    assert set(groups) == set(SWITCHES[ref]), f"{ref}: groups {sorted(groups)}"
    for name, (role, _media_, _iface, ids) in SWITCHES[ref].items():
        assert groups[name].get("role") == role, f"{ref}: group {name} role {groups[name].get('role')!r}"
        joined = sorted(p["id"] for p in _ports(ref) if p.get("group") == name)
        assert joined == sorted(ids), f"{ref}: group {name} holds {joined}"


@pytest.mark.parametrize("ref", SWITCHES)
def test_a_groups_media_agrees_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for name, (_role, media, _iface, _ids) in SWITCHES[ref].items():
        assert (groups[name].get("attrs") or {}).get("media") == media, \
            f"{ref}: group {name} states media {(groups[name].get('attrs') or {}).get('media')!r}"
    for part in _ports(ref):
        assert _media(part) == SWITCHES[ref][part["group"]][1], \
            f"{ref}: {part['id']} is {_media(part)}, its group says {SWITCHES[ref][part['group']][1]}"


@pytest.mark.parametrize("ref", SWITCHES)
def test_a_port_group_is_one_interface(ref):
    families = {}
    for part in _ports(ref):
        assert part.get("group"), f"{ref}: port {part['id']} joins no group"
        families.setdefault(part["group"], set()).add(_interface(part))
    for name, fams in families.items():
        assert fams == {SWITCHES[ref][name][2]}, f"{ref}: group {name} holds {sorted(fams, key=str)}"


@pytest.mark.parametrize("ref", SWITCHES)
def test_a_switch_states_no_speed(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} declares no groups"
    for name, group in groups.items():
        attrs = group.get("attrs") or {}
        assert "speed" not in attrs and "speeds" not in attrs, f"{ref}: group {name} states a speed"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} states a speed"

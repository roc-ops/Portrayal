"""The CommScope CH3000 passive optical modules say what their ports are for.

A passive module (a filter, a multiplexer, a demultiplexer or a splitter of the
NP and OP families) composes its optical connectors as parts: an SC bore, or a
duplex LC adapter. Without a group a port on a module seated in a chassis is
drawn with no `data-group` and no `data-group-role`. Each of the twenty-seven
contracts below declares `groups:` in the device shape, and each of its port
parts joins one.

What these hold for every module in the list:

  - it declares at least one group, and every port part joins a declared group;
  - every declared group has a term, a role from the schema's list, an index
    origin of 0 or 1, a description, and at least one member;
  - a group's declared media agrees with each member's;
  - the data sheets print no data rate for these modules, so no group and no
    part states a speed;
  - a port group is one connector family.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

MODULES = [
    "commscope/np33f01@1", "commscope/np34b10s@1", "commscope/np34c01@1",
    "commscope/np34f01d@1", "commscope/np34m05@1", "commscope/np34m08@1",
    "commscope/np34s04@1", "commscope/np35c0x@1", "commscope/np35d04@1",
    "commscope/np35d08@1", "commscope/np35f01@1", "commscope/np35f04s@1",
    "commscope/np35m04@1", "commscope/np35m08@1",
    "commscope/op31m2d@1", "commscope/op33f1x@1", "commscope/op34d5x@1",
    "commscope/op34f1d@1", "commscope/op34m10c@1", "commscope/op34m5x@1",
    "commscope/op34m8c@1", "commscope/op34s4s@1", "commscope/op35d4x@1",
    "commscope/op35d8cf@1", "commscope/op35f1@1", "commscope/op35f1d@1",
    "commscope/op35f4s@1",
]

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


def _connector(part):
    return (part.get("attrs") or {}).get("connector")


def test_the_list_is_twenty_seven_distinct_modules():
    assert len(MODULES) == len(set(MODULES)) == 27


@pytest.mark.parametrize("ref", MODULES)
def test_every_port_part_joins_a_declared_group(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} composes ports and declares no groups"
    ports = _ports(ref)
    assert ports, f"{ref} composes no port part"
    for part in ports:
        assert part.get("group") in groups, \
            f"{ref}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@pytest.mark.parametrize("ref", MODULES)
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


@pytest.mark.parametrize("ref", MODULES)
def test_a_groups_media_agrees_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for part in _ports(ref):
        assert part.get("group") in groups, f"{ref}: port {part['id']} joins no declared group"
        attrs = groups[part["group"]].get("attrs") or {}
        assert attrs.get("media") == "fiber", f"{ref}: group {part['group']} states media {attrs.get('media')!r}"
        assert _media(part) == "fiber", f"{ref}: {part['id']} is {_media(part)}, its group says fiber"


@pytest.mark.parametrize("ref", MODULES)
def test_a_passive_module_states_no_speed(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} declares no groups"
    for name, group in groups.items():
        attrs = group.get("attrs") or {}
        assert "speed" not in attrs and "speeds" not in attrs, f"{ref}: group {name} gives a passive module a speed"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} gives a passive module a speed"


@pytest.mark.parametrize("ref", MODULES)
def test_a_port_group_is_one_connector_family(ref):
    families = {}
    for part in _ports(ref):
        assert part.get("group"), f"{ref}: port {part['id']} joins no group"
        families.setdefault(part["group"], set()).add(_connector(part))
    for name, fams in families.items():
        assert len(fams) == 1 and None not in fams, f"{ref}: group {name} holds {sorted(fams, key=str)}"

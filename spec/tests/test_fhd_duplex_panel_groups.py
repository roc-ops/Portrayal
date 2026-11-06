"""The FHD duplex fibre adapter panels say what their ports are for.

An FHD adapter panel composes its connectors as parts (an LC duplex or an SC
duplex adapter) on its front, and the same count on its rear face. Without a
group a port on a panel seated in an enclosure is drawn with no `data-group`
and no `data-group-role`. Each of the sixteen contracts below declares
`groups:` in the device shape, and each of its port parts joins one.

What these hold for every panel in the list:

  - it declares at least one group, and every port part joins a declared group;
  - every declared group has a term, a role from the schema's list, an index
    origin of 0 or 1, a description, and at least one member;
  - a group's declared media agrees with each member's;
  - a passive adapter has no data rate, so no group and no part states a speed;
  - a port group is one connector family;
  - a panel's front and rear groups hold the same number of ports.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

FRONTS = [
    "fs/fhd-fap12lcd-apc-os2@1", "fs/fhd-fap12lcd-om4@1", "fs/fhd-fap12lcd-os2@1",
    "fs/fhd-fap18lcd-om4@1", "fs/fhd-fap18lcd-os2@1",
    "fs/fhd-fap6scd-apc-os2@1", "fs/fhd-fap6scd-om4@1", "fs/fhd-fap6scd-os2@1",
]
PANELS = sorted(FRONTS + [ref.replace("@1", "-rear@1") for ref in FRONTS])

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
    return (_contract(part["ref"]).get("attrs") or {}).get("connector")


@pytest.mark.parametrize("ref", PANELS)
def test_every_port_part_joins_a_declared_group(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} composes ports and declares no groups"
    for part in _ports(ref):
        assert part.get("group") in groups, \
            f"{ref}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@pytest.mark.parametrize("ref", PANELS)
def test_every_group_says_what_it_is_for_and_has_members(ref):
    members = {}
    for part in _ports(ref):
        members.setdefault(part.get("group"), []).append(part["id"])
    for name, group in (_contract(ref).get("groups") or {}).items():
        assert group.get("term"), f"{ref}: group {name} has no term"
        assert group.get("role") in ROLES, f"{ref}: group {name} role {group.get('role')!r}"
        assert group.get("index-origin") in (0, 1), f"{ref}: group {name} index-origin"
        assert (group.get("description") or "").strip(), f"{ref}: group {name} has no description"
        assert members.get(name), f"{ref}: group {name} has no member"


@pytest.mark.parametrize("ref", PANELS)
def test_a_groups_media_agrees_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for part in _ports(ref):
        assert part.get("group") in groups, f"{ref}: port {part['id']} joins no declared group"
        attrs = groups[part["group"]].get("attrs") or {}
        if "media" in attrs:
            assert _media(part) == attrs["media"], \
                f"{ref}: {part['id']} is {_media(part)}, its group {part['group']} says {attrs['media']}"


@pytest.mark.parametrize("ref", PANELS)
def test_a_passive_adapter_states_no_speed(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} declares no groups"
    for name, group in groups.items():
        assert "speed" not in (group.get("attrs") or {}), f"{ref}: group {name} gives a passive adapter a speed"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} gives a passive adapter a speed"


@pytest.mark.parametrize("ref", PANELS)
def test_a_port_group_is_one_connector_family(ref):
    families = {}
    for part in _ports(ref):
        assert part.get("group"), f"{ref}: port {part['id']} joins no group"
        families.setdefault(part["group"], set()).add(_connector(part))
    for name, fams in families.items():
        assert len(fams) == 1, f"{ref}: group {name} holds {sorted(fams, key=str)}"


@pytest.mark.parametrize("ref", FRONTS)
def test_front_and_rear_hold_the_same_number_of_ports(ref):
    rear = ref.replace("@1", "-rear@1")
    assert len(_ports(ref)) == len(_ports(rear)), f"{ref} and {rear} compose different port counts"

"""The Fibrain adapter holders, their rear faces, the RJ45 modules and the LC adapter say what each port is for.

A Fibrain holder composes its adapters as parts, a module composes its RJ45
jack, and the LC adapter composes its two bores. Without a group a port seated
in a panel is drawn with no `data-group` and no `data-group-role`, so nothing
reading the drawing can tell which ports carry a user's link. Every Fibrain
contract that composes a port part declares `groups:` in the device shape, and
each of its port parts joins one.

What these hold for every Fibrain contract that composes a port part:

  - it declares at least one group, and every port part joins a declared group;
  - every declared group has a term, a role from the schema's list, an index
    origin of 0 or 1, a description, and at least one member;
  - a group's declared media agrees with each member's, and a declared speed is
    spelled from the closed set in spec/schemas/speeds.yaml;
  - a port group is one connector family;
  - the ports are passive and no held Fibrain data sheet prints a rate for an
    adapter or a jack, so neither a group nor a part states a speed.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

ROLES = set(json.loads((SPEC / "schemas/component.schema.json").read_text())
            ["$defs"]["group"]["properties"]["role"]["enum"])
SPEEDS = set(yaml.safe_load((SPEC / "schemas/speeds.yaml").read_text())["speeds"])
FAMILY = {"sfp-plus": "sfp", "sfp28": "sfp", "qsfp28": "qsfp", "qsfp-plus": "qsfp"}


def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / ns / name / f"v{major}" / "contract.yaml").read_text())


def _is_port(ref):
    return _contract(ref).get("class") == "port"


def _ports(ref):
    return [p for p in _contract(ref).get("parts") or [] if _is_port(p["ref"])]


def _fibrain_port_components():
    """Every Fibrain contract, every version, that composes a port part."""
    found = []
    for path in sorted((LIB / "fibrain").glob("*/v*/contract.yaml")):
        ref = f"fibrain/{path.parts[-3]}@{path.parts[-2][1:]}"
        if _ports(ref):
            found.append(ref)
    return found


COMPONENTS = _fibrain_port_components()


def _media(part):
    own = (part.get("attrs") or {}).get("media")
    return own or (_contract(part["ref"]).get("attrs") or {}).get("media")


def _family(media):
    return FAMILY.get(media, media)


def test_there_are_fibrain_components_that_compose_a_port_part():
    assert COMPONENTS


@pytest.mark.parametrize("ref", COMPONENTS)
def test_every_port_part_joins_a_declared_group(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} composes ports and declares no groups"
    for part in _ports(ref):
        assert part.get("group") in groups, \
            f"{ref}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@pytest.mark.parametrize("ref", COMPONENTS)
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


@pytest.mark.parametrize("ref", COMPONENTS)
def test_a_groups_media_agrees_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for part in _ports(ref):
        assert part.get("group") in groups, f"{ref}: port {part['id']} joins no declared group"
        attrs = groups[part["group"]].get("attrs") or {}
        if "media" in attrs:
            assert _family(_media(part)) == _family(attrs["media"]), \
                f"{ref}: {part['id']} is {_media(part)}, its group {part['group']} says {attrs['media']}"
            own = (part.get("attrs") or {}).get("media")
            if own:
                assert own == attrs["media"], f"{ref}: {part['id']} media differs from its group"
        if "speed" in attrs:
            assert attrs["speed"] in SPEEDS, f"{ref}: {part['group']} speed {attrs['speed']!r}"


@pytest.mark.parametrize("ref", COMPONENTS)
def test_a_port_group_is_one_connector_family(ref):
    families = {}
    for part in _ports(ref):
        assert part.get("group"), f"{ref}: port {part['id']} joins no group"
        families.setdefault(part["group"], set()).add(_family(_media(part)))
    for name, fams in families.items():
        assert len(fams) == 1, f"{ref}: group {name} holds {sorted(fams)}"


@pytest.mark.parametrize("ref", COMPONENTS)
def test_a_passive_port_states_no_speed(ref):
    groups = _contract(ref).get("groups") or {}
    for part in _ports(ref):
        assert part.get("group") in groups, f"{ref}: port {part['id']} joins no declared group"
        assert "speed" not in (groups[part["group"]].get("attrs") or {}), \
            f"{ref}: group {part['group']} states a speed for a passive port"
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} states a speed"

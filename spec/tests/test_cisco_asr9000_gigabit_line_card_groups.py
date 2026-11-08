"""The ASR 9000 Gigabit, 10 Gigabit and dual-rate Ethernet line cards say what each port is for.

A line card composes its cages as parts (SFP, SFP+ and XFP). Without a group a port on a card seated in
a chassis slot is drawn with no `data-group` and no `data-group-role`, so nothing reading the drawing can
tell a traffic port from a lamp. Each of the 17 contracts below declares `groups:` in the device shape,
and each of its port parts joins one.

What these hold for every contract of the family:

  - the family is every Cisco first, second and third generation Ethernet line card contract of the
    stems below that composes a port part (the census below), and each declares at least one group
    with every port part in a declared group;
  - every declared group has a term, a role from the schema's list, an index origin of 0 (the guide
    names a card's ports from 0), a description, and at least one member;
  - a group's declared media agrees with each member's cage family, and a declared speed (and each
    rate of `speeds`) is spelled from the closed set in spec/schemas/speeds.yaml;
  - a group holds one cage family, and its count is the card's printed port count;
  - every group is a traffic group.
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

SFP_1G = {"sfp-1g": ("sfp", "1g", None, 0)}
SFP_PLUS = {"sfp-plus-10g": ("sfp-plus", "10g", None, 0)}
DUAL = {"sfp-plus-10g-dual": ("sfp-plus", "10g", ["1g", "10g"], 0)}
XFP = {"xfp-10g": ("xfp", "10g", None, 0)}


def _one(groups, n):
    return {g: (m, s, ss, n) for g, (m, s, ss, _) in groups.items()}


# card -> {group: (media, speed, speeds or None, ports)}
CARDS = {
    "cisco/a9k-40ge-b@2": _one(SFP_1G, 40),
    "cisco/a9k-40ge-e@2": _one(SFP_1G, 40),
    "cisco/a9k-40ge-l@2": _one(SFP_1G, 40),
    "cisco/a9k-24x10ge-1g-se@1": _one(DUAL, 24),
    "cisco/a9k-48x10ge-1g-se@1": _one(DUAL, 48),
    "cisco/a9k-24x10ge-se@2": _one(SFP_PLUS, 24),
    "cisco/a9k-36x10ge-se@2": _one(SFP_PLUS, 36),
    "cisco/a9k-16t-8-b@2": _one(SFP_PLUS, 16),
    "cisco/a9k-4t-b@2": _one(XFP, 4),
    "cisco/a9k-4t-e@2": _one(XFP, 4),
    "cisco/a9k-4t-l@2": _one(XFP, 4),
    "cisco/a9k-8t-b@2": _one(XFP, 8),
    "cisco/a9k-8t-e@2": _one(XFP, 8),
    "cisco/a9k-8t-l@2": _one(XFP, 8),
    "cisco/a9k-8t-4-b@2": _one(XFP, 8),
    "cisco/a9k-8t-4-e@2": _one(XFP, 8),
    "cisco/a9k-8t-4-l@2": _one(XFP, 8),
}
FAMILY_STEMS = ("a9k-40ge-", "a9k-24x10ge-", "a9k-36x10ge-", "a9k-48x10ge-", "a9k-16t-", "a9k-4t-", "a9k-8t-")
# the cards of these stems with a second generation or later suffix are not this family
OTHER_STEMS = ("a9k-40ge-se", "a9k-40ge-tr", "a9k-24x10ge-tr", "a9k-36x10ge-tr", "a9k-48x10ge-1g-tr")
EACH = pytest.mark.parametrize("ref", sorted(CARDS))


def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / ns / name / f"v{major}" / "contract.yaml").read_text())


def _ports(ref):
    return [p for p in _contract(ref).get("parts") or [] if _contract(p["ref"]).get("class") == "port"]


def _media(part):
    own = (part.get("attrs") or {}).get("media")
    return own or (_contract(part["ref"]).get("attrs") or {}).get("media")


def _cage(media):
    """The cage family a media word names: an SFP+ cage is an SFP cage."""
    return {"sfp-plus": "sfp", "sfp28": "sfp", "sfp": "sfp", "xfp": "xfp"}[media]


def test_the_cards_are_every_contract_of_the_family_that_composes_a_port_part():
    found = []
    for path in sorted((LIB / "cisco").glob("*/v*/contract.yaml")):
        name = path.parts[-3]
        if not name.startswith(FAMILY_STEMS) or name.startswith(OTHER_STEMS):
            continue
        data = yaml.safe_load(path.read_text())
        if any(_contract(p["ref"]).get("class") == "port" for p in data.get("parts") or []):
            found.append(f"cisco/{name}@{path.parts[-2][1:]}")
    assert sorted(found) == sorted(CARDS)


@EACH
def test_every_port_part_joins_a_declared_group(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} composes ports and declares no groups"
    for part in _ports(ref):
        assert part.get("group") in groups, \
            f"{ref}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@EACH
def test_the_groups_are_the_ones_the_guide_prints(ref):
    groups = _contract(ref).get("groups") or {}
    assert sorted(groups) == sorted(CARDS[ref]), ref
    held = {}
    for part in _ports(ref):
        held.setdefault(part.get("group"), []).append(part["id"])
    for name, (media, speed, speeds, count) in CARDS[ref].items():
        attrs = groups[name].get("attrs") or {}
        assert attrs.get("media") == media, f"{ref}: {name} media {attrs.get('media')!r}"
        assert attrs.get("speed") == speed, f"{ref}: {name} speed {attrs.get('speed')!r}"
        assert attrs.get("speeds") == speeds, f"{ref}: {name} speeds {attrs.get('speeds')!r}"
        assert len(held.get(name, [])) == count, f"{ref}: {name} holds {len(held.get(name, []))}, expected {count}"


@EACH
def test_every_group_says_what_it_is_for_and_has_members(ref):
    members = {}
    for part in _ports(ref):
        members.setdefault(part.get("group"), []).append(part["id"])
    for name, group in (_contract(ref).get("groups") or {}).items():
        assert group.get("term"), f"{ref}: group {name} has no term"
        assert group.get("role") in ROLES, f"{ref}: group {name} role {group.get('role')!r}"
        assert group.get("index-origin") == 0, f"{ref}: group {name} index-origin"
        assert (group.get("description") or "").strip(), f"{ref}: group {name} has no description"
        assert members.get(name), f"{ref}: group {name} has no member"


@EACH
def test_a_groups_media_and_speed_agree_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for part in _ports(ref):
        attrs = groups[part["group"]].get("attrs") or {}
        own = part.get("attrs") or {}
        if "media" in attrs:
            assert _cage(_media(part)) == _cage(attrs["media"]), \
                f"{ref}: {part['id']} is {_media(part)}, its group {part['group']} says {attrs['media']}"
            if "media" in own:
                assert own["media"] == attrs["media"], f"{ref}: {part['id']} media differs from its group"
        if "speed" in attrs:
            assert attrs["speed"] in SPEEDS, f"{ref}: {part['group']} speed {attrs['speed']!r}"
            assert set(attrs.get("speeds") or []) <= SPEEDS, f"{ref}: {part['group']} speeds {attrs.get('speeds')!r}"
            if attrs.get("speeds"):
                assert attrs["speed"] == attrs["speeds"][-1], f"{ref}: {part['group']} speed is not its highest rate"
            if "speed" in own:
                assert own["speed"] == attrs["speed"], f"{ref}: {part['id']} speed differs from its group"


@EACH
def test_a_port_group_is_one_cage_family(ref):
    families = {}
    for part in _ports(ref):
        families.setdefault(part["group"], set()).add(_cage(_media(part)))
    for name, fams in families.items():
        assert len(fams) == 1, f"{ref}: group {name} holds {sorted(fams)}"


@EACH
def test_every_group_is_a_traffic_group(ref):
    for name, group in (_contract(ref).get("groups") or {}).items():
        assert group["role"] == "traffic", f"{ref}: group {name} role {group['role']!r}"

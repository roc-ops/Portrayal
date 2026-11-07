"""The ASR 9000 high-rate Ethernet line cards say what each port is for.

A line card composes its cages as parts (QSFP28, QSFP-DD, SFP+ and SFP28). Without a
group a port on a card seated in a chassis slot is drawn with no `data-group` and no
`data-group-role`, so nothing reading the drawing can tell a traffic port from a lamp.
Each of the 25 contracts below declares `groups:` in the device shape, and each of its
port parts joins one.

What these hold for every contract of the family:

  - the family is every Cisco 100G, 400G, combo and port-expansion line card contract
    that composes a port part (the census below), and each declares at least one group
    with every port part in a declared group;
  - every declared group has a term, a role from the schema's list, an index origin of 0
    (the guides name a card's ports from 0), a description, and at least one member;
  - a group's declared media agrees with each member's, and a declared speed is spelled
    from the closed set in spec/schemas/speeds.yaml;
  - a group holds one cage family, and its count and the port numbers the guides print
    for the split cards (the 400G combo card, the multi-rate cards and the port
    expansion card) are the ones below;
  - a group states a speed only where its ports share one rate: the 800G port expansion
    card has 25 Gb and 10 Gb cages in no printed order, so its group states none;
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


def _span(*spans):
    out = set()
    for s in spans:
        a, _, b = str(s).partition("-")
        out.update(f"p{n}" for n in range(int(a), int(b or a) + 1))
    return out


def _q28(n):
    return {"qsfp28-100g": ("qsfp28", "100g", n)}


COMBO4 = {"sfp-plus-10g": ("sfp-plus", "10g", 24), "sfp28-25g": ("sfp28", "25g", 16),
          "qsfp28-100g": ("qsfp28", "100g", 4)}
COMBO4_PORTS = {"sfp-plus-10g": _span("0-5", "10-15", "20-25", "30-35"),
                "sfp28-25g": _span("6-9", "16-19", "26-29", "36-39"),
                "qsfp28-100g": _span("40-43")}
DD_20 = {"qsfpdd-400g": ("qsfp-dd", "400g", 5), "qsfp28-100g": ("qsfp28", "100g", 15)}
DD_8 = {"qsfpdd-400g": ("qsfp-dd", "400g", 2), "qsfp28-100g": ("qsfp28", "100g", 6)}

# card -> {group: (media, speed or None, ports)}
CARDS = {
    "cisco/a99-10x400ge-x-se@2": {"qsfpdd-400g": ("qsfp-dd", "400g", 10)},
    "cisco/a99-10x400ge-x-tr@2": {"qsfpdd-400g": ("qsfp-dd", "400g", 10)},
    "cisco/a99-12x100ge@1": _q28(12),
    "cisco/a99-32x100ge-se@1": _q28(32),
    "cisco/a99-32x100ge-tr@1": _q28(32),
    "cisco/a99-32x100ge-x-se@1": _q28(32),
    "cisco/a99-32x100ge-x-tr@1": _q28(32),
    "cisco/a99-4hg-flex-se@2": COMBO4,
    "cisco/a99-4hg-flex-tr@2": COMBO4,
    "cisco/a9903-20hg-pec@1": DD_20,
    "cisco/a9903-20hg-pec@2": DD_20,
    "cisco/a9903-8hg-pec@1": {"sfp-plus": ("sfp-plus", None, 48)},
    "cisco/a9903-8hg-pec@2": {"sfp-plus": ("sfp-plus", None, 48)},
    "cisco/a9k-16x100ge-se@1": _q28(16),
    "cisco/a9k-16x100ge-tr@1": _q28(16),
    "cisco/a9k-20hg-flex-se@1": DD_20,
    "cisco/a9k-20hg-flex-tr@1": DD_20,
    "cisco/a9k-400g-dwdm-tr@2": {"sfp-plus-10g": ("sfp-plus", "10g", 20)},
    "cisco/a9k-4hg-flex-se@2": COMBO4,
    "cisco/a9k-4hg-flex-tr@2": COMBO4,
    "cisco/a9k-4x100ge@1": _q28(4),
    "cisco/a9k-8hg-flex-se@1": DD_8,
    "cisco/a9k-8hg-flex-tr@1": DD_8,
    "cisco/a9k-8x100ge-x-se@1": _q28(8),
    "cisco/a9k-8x100ge-x-tr@1": _q28(8),
}
# the ports the guides and data sheets print as QSFP-DD, on the cards that mix cages
DD_PORTS = {
    "cisco/a9k-20hg-flex-se@1": _span(0, 7, 8, 12, 19), "cisco/a9k-20hg-flex-tr@1": _span(0, 7, 8, 12, 19),
    "cisco/a9k-8hg-flex-se@1": _span(0, 7), "cisco/a9k-8hg-flex-tr@1": _span(0, 7),
    "cisco/a9903-20hg-pec@1": _span(0, 4, 8, 12, 16), "cisco/a9903-20hg-pec@2": _span(0, 4, 8, 12, 16),
}
FAMILY_STEMS = ("a9k-4hg-", "a9k-8hg-", "a9k-20hg-", "a9k-16x100ge-", "a9k-8x100ge-", "a9k-4x100ge",
                "a9k-400g-", "a99-4hg-", "a99-12x100ge", "a99-32x100ge-", "a99-10x400ge-",
                "a9903-8hg-", "a9903-20hg-")
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
    """The cage family a media word names: a QSFP28 cage is a QSFP cage, an SFP+ cage is an SFP cage."""
    return {"qsfp28": "qsfp", "qsfp": "qsfp", "qsfp-plus": "qsfp", "sfp-plus": "sfp", "sfp28": "sfp",
            "sfp": "sfp", "qsfp-dd": "qsfp-dd"}[media]


def test_the_cards_are_every_contract_of_the_family_that_composes_a_port_part():
    found = []
    for path in sorted((LIB / "cisco").glob("*/v*/contract.yaml")):
        name = path.parts[-3]
        if not name.startswith(FAMILY_STEMS):
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
def test_the_groups_are_the_ones_the_guides_print(ref):
    groups = _contract(ref).get("groups") or {}
    assert sorted(groups) == sorted(CARDS[ref]), ref
    held = {}
    for part in _ports(ref):
        held.setdefault(part.get("group"), []).append(part["id"])
    for name, (media, speed, count) in CARDS[ref].items():
        attrs = groups[name].get("attrs") or {}
        assert attrs.get("media") == media, f"{ref}: {name} media {attrs.get('media')!r}"
        assert attrs.get("speed") == speed, f"{ref}: {name} speed {attrs.get('speed')!r}"
        assert len(held.get(name, [])) == count, f"{ref}: {name} holds {len(held.get(name, []))}, expected {count}"


@EACH
def test_the_split_cards_put_the_printed_ports_in_each_group(ref):
    held = {}
    for part in _ports(ref):
        held.setdefault(part.get("group"), set()).add(part["id"])
    if ref in DD_PORTS:
        assert held["qsfpdd-400g"] == DD_PORTS[ref], ref
        assert {_media(p) for p in _ports(ref) if p["id"] in DD_PORTS[ref]} == {"qsfp-dd"}, ref
    if CARDS[ref] == COMBO4:
        assert held == COMBO4_PORTS, ref


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

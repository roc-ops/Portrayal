"""The Juniper MPC line cards say what each port is for.

A fixed MPC composes its cages as parts (SFP+, CFP, CFP2, QSFP+, QSFP28 and QSFP-DD). Without a group a
port on a card seated in a chassis slot is drawn with no `data-group` and no `data-group-role`, so nothing
reading the drawing can tell a traffic port from a lamp. Each card below declares `groups:` in the device
shape, and each of its port parts joins one.

What these hold for every card of the family:

  - the family is every Juniper contract of the stems below that composes a port part (the census
    below), and each declares at least one group with every port part in a declared group;
  - every declared group has a term, a role from the schema's list, an index origin of 0 (the module
    reference numbers a card's ports from 0), a description, and at least one member;
  - a group's media is the media each member states, and a declared speed (and each rate of `speeds`)
    is spelled from the closed set in spec/schemas/speeds.yaml, `speed` being the highest rate of `speeds`;
  - a group's member count is the card's printed port count, and a group states the rate the module
    reference prints for its ports;
  - every group is a traffic group, and every group of a card the book prints a rate for carries it.

A card is named without its major, so a later version of a card is held to the same table.
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

SFP_PLUS_10G = ("sfp-plus", "10g", None)
QSFP28_100G = ("qsfp28", "100g", ["10g", "40g", "100g"])
QSFP_PLUS_40G = ("qsfp-plus", "40g", ["10g", "40g"])
QSFP_DD_400G = ("qsfp-dd", "400g", ["10g", "40g", "100g", "400g"])


def _g(spec, n):
    return spec + (n,)


# card -> {group: (media, speed, speeds or None, ports)}
CARDS = {
    "juniper/mpc-3d-16xge-sfpp": {"sfp-plus-10g": _g(SFP_PLUS_10G, 16)},
    "juniper/mpc4e-3d-32xge-sfpp": {"sfp-plus-10g": _g(SFP_PLUS_10G, 32)},
    "juniper/mpc4e-3d-2cge-8xge": {"sfp-plus-10g": _g(SFP_PLUS_10G, 8), "cfp-100g": ("cfp", "100g", None, 2)},
    "juniper/mpc5e-40g10g": {"sfp-plus-10g": _g(SFP_PLUS_10G, 24), "qsfp-plus-40g": ("qsfp-plus", "40g", None, 6)},
    "juniper/mpc5e-100g10g": {"sfp-plus-10g": _g(SFP_PLUS_10G, 4), "cfp2-100g": ("cfp2", "100g", None, 2)},
    "juniper/mpc7e-10g": {"sfp-plus-10g": ("sfp-plus", "10g", ["1g", "10g"], 40)},
    "juniper/mpc7e-mrate": {"qsfp28-100g": _g(QSFP28_100G, 4), "qsfp-plus-40g": _g(QSFP_PLUS_40G, 8)},
    "juniper/mpc10e-10c-mrate": {"qsfp28-100g": _g(QSFP28_100G, 8), "qsfp-dd-400g": _g(QSFP_DD_400G, 2)},
    "juniper/mpc10e-15c-mrate": {"qsfp28-100g": _g(QSFP28_100G, 12), "qsfp-dd-400g": _g(QSFP_DD_400G, 3)},
    # Table 30 gives port 0 of each PIC a range of rates and the other four 100 Gbps; the contract's port ids
    # do not say which cage is port 0 of its PIC, so the group states a count and a media and no rate.
    "juniper/mx2k-mpc11e": {"qsfp28": ("qsfp28", None, None, 40)},
}
# the v2k drawings of the same cards are held to the same table
for _name in ("mpc-3d-16xge-sfpp", "mpc4e-3d-32xge-sfpp", "mpc4e-3d-2cge-8xge", "mpc5e-40g10g", "mpc5e-100g10g",
              "mpc7e-10g"):
    CARDS[f"juniper/{_name}-v2k"] = CARDS[f"juniper/{_name}"]
# the v2k drawing states all twelve cages as qsfp28, so its ten and forty gigabit group states no media
CARDS["juniper/mpc7e-mrate-v2k"] = {"qsfp28-100g": _g(QSFP28_100G, 4), "qsfp-plus-40g": (None, "40g", ["10g", "40g"], 8)}
CARDS["juniper/mx2k-mpc11e-v2k"] = CARDS.pop("juniper/mx2k-mpc11e")

FAMILY_STEMS = ("mpc-3d-16xge-", "mpc4e-", "mpc5e-", "mpc7e-", "mpc10e-", "mx2k-mpc11e")
EACH = pytest.mark.parametrize("card", sorted(CARDS))


def _latest(ns, name):
    majors = sorted(int(p.name[1:]) for p in (LIB / ns / name).glob("v*") if p.name[1:].isdigit())
    return LIB / ns / name / f"v{majors[-1]}" / "contract.yaml"


def _contract(card):
    ns, name = card.split("/", 1)
    return yaml.safe_load(_latest(ns, name).read_text())


def _ref_contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / ns / name / f"v{major}" / "contract.yaml").read_text())


def _ports(card):
    return [p for p in _contract(card).get("parts") or [] if _ref_contract(p["ref"]).get("class") == "port"]


def test_the_cards_are_every_contract_of_the_family_that_composes_a_port_part():
    found = set()
    for path in sorted((LIB / "juniper").glob("*/v*/contract.yaml")):
        name = path.parts[-3]
        if not name.startswith(FAMILY_STEMS):
            continue
        data = yaml.safe_load(path.read_text())
        if any(_ref_contract(p["ref"]).get("class") == "port" for p in data.get("parts") or []):
            found.add(f"juniper/{name}")
    assert found == set(CARDS)


@EACH
def test_every_port_part_joins_a_declared_group(card):
    groups = _contract(card).get("groups") or {}
    assert groups, f"{card} composes ports and declares no groups"
    for part in _ports(card):
        assert part.get("group") in groups, \
            f"{card}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@EACH
def test_the_groups_are_the_ones_the_module_reference_prints(card):
    groups = _contract(card).get("groups") or {}
    assert sorted(groups) == sorted(CARDS[card]), card
    held = {}
    for part in _ports(card):
        held.setdefault(part.get("group"), []).append(part["id"])
    for name, (media, speed, speeds, count) in CARDS[card].items():
        attrs = groups[name].get("attrs") or {}
        assert attrs.get("media") == media, f"{card}: {name} media {attrs.get('media')!r}"
        assert attrs.get("speed") == speed, f"{card}: {name} speed {attrs.get('speed')!r}"
        assert attrs.get("speeds") == speeds, f"{card}: {name} speeds {attrs.get('speeds')!r}"
        assert len(held.get(name, [])) == count, f"{card}: {name} holds {len(held.get(name, []))}, expected {count}"


@EACH
def test_every_group_says_what_it_is_for_and_has_members(card):
    members = {}
    for part in _ports(card):
        members.setdefault(part.get("group"), []).append(part["id"])
    for name, group in (_contract(card).get("groups") or {}).items():
        assert group.get("term"), f"{card}: group {name} has no term"
        assert group.get("role") in ROLES, f"{card}: group {name} role {group.get('role')!r}"
        assert group.get("index-origin") == 0, f"{card}: group {name} index-origin"
        assert (group.get("description") or "").strip(), f"{card}: group {name} has no description"
        assert members.get(name), f"{card}: group {name} has no member"


@EACH
def test_a_groups_media_and_speed_agree_with_its_members(card):
    groups = _contract(card).get("groups") or {}
    for part in _ports(card):
        attrs = groups[part["group"]].get("attrs") or {}
        own = part.get("attrs") or {}
        if "media" in attrs:
            assert own.get("media") == attrs["media"], \
                f"{card}: {part['id']} is {own.get('media')}, its group {part['group']} says {attrs['media']}"
        if "speed" in attrs:
            assert attrs["speed"] in SPEEDS, f"{card}: {part['group']} speed {attrs['speed']!r}"
            assert set(attrs.get("speeds") or []) <= SPEEDS, f"{card}: {part['group']} speeds {attrs.get('speeds')!r}"
            if attrs.get("speeds"):
                assert attrs["speed"] == attrs["speeds"][-1], f"{card}: {part['group']} speed is not its highest rate"
            if "speed" in own:
                assert own["speed"] == attrs["speed"], f"{card}: {part['id']} speed differs from its group"


@EACH
def test_every_group_is_a_traffic_group(card):
    for name, group in (_contract(card).get("groups") or {}).items():
        assert group["role"] == "traffic", f"{card}: group {name} role {group['role']!r}"


@EACH
def test_every_group_cites_its_source(card):
    prov = _contract(card).get("provenance") or {}
    assert (prov.get("groups") or "").strip(), f"{card}: provenance.groups is empty"


def test_the_mrate_100g_ports_are_the_four_the_book_names():
    for card in ("juniper/mpc7e-mrate", "juniper/mpc7e-mrate-v2k"):
        held = sorted(p["id"] for p in _ports(card) if p.get("group") == "qsfp28-100g")
        assert held == ["port-0-2", "port-0-5", "port-1-2", "port-1-5"], card

"""The ASR 9000 shared port adapters say what each port is for.

A shared port adapter composes its connectors as parts (an SFP or XFP cage, an
RJ45, a coax jack). Without a group a port on an adapter seated in a SIP
subslot is drawn with no `data-group` and no `data-group-role`, so nothing
reading the drawing can tell a circuit port from a lamp. Each of the 22
contracts below declares `groups:` in the device shape, and each of its port
parts joins one.

What these hold for every Cisco `spa-*` contract that composes a port part:

  - it declares at least one group, and every port part joins a declared group;
  - every declared group has a term, a role from the schema's list, an index
    origin of 0 (the guide numbers subslots and ports from 0), a description,
    and at least one member;
  - a group's declared media agrees with each member's, and a declared speed is
    spelled from the closed set in spec/schemas/speeds.yaml;
  - a port group is one connector family;
  - no group states a speed: SONET and T-carrier rates (155.52, 622.08 and
    2488.32 Mbps, 44.736 Mbps) have no word in that set, so the rate stays in
    the description, as the guide prints it;
  - a cage group names its cage, and the coax groups name no media of their own
    beyond what each jack declares.
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

# adapter -> (the cage or jack family its ports are, port parts)
ADAPTERS = {
    "cisco/spa-1choc3-ce-atm@1": ("sfp", 1),
    "cisco/spa-1xchoc48-ds3@1": ("sfp", 1),
    "cisco/spa-1xchstm1-oc3@1": ("sfp", 1),
    "cisco/spa-1xoc12-atm-v2@1": ("sfp", 1),
    "cisco/spa-1xoc3-atm-v2@1": ("sfp", 1),
    "cisco/spa-1xoc48pos-rpr@1": ("sfp", 1),
    "cisco/spa-2cht3-ce-atm@1": ("coax", 4),
    "cisco/spa-2xchoc12-ds0@1": ("sfp", 2),
    "cisco/spa-2xoc12-pos@1": ("sfp", 2),
    "cisco/spa-2xoc48pos-rpr@1": ("sfp", 2),
    "cisco/spa-2xt3e3@1": ("coax", 4),
    "cisco/spa-3xoc3-atm-v2@1": ("sfp", 3),
    "cisco/spa-4xct3-ds0@1": ("coax", 8),
    "cisco/spa-4xoc12-pos@1": ("sfp", 4),
    "cisco/spa-4xoc3-pos-v2@1": ("sfp", 4),
    "cisco/spa-4xoc48pos-rpr@1": ("sfp", 4),
    "cisco/spa-4xt3e3@1": ("coax", 8),
    "cisco/spa-8xcht1-e1-v2@1": ("rj45", 8),
    "cisco/spa-8xcht1-e1@1": ("rj45", 8),
    "cisco/spa-8xoc12-pos@1": ("sfp", 8),
    "cisco/spa-8xoc3-pos@1": ("sfp", 8),
    "cisco/spa-oc192pos-xfp@1": ("xfp", 1),
}
EACH = pytest.mark.parametrize("ref", sorted(ADAPTERS))


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


def _family(media):
    return "coax" if media.startswith("coax") else media


def _adapters_composing_ports():
    found = []
    for path in sorted((LIB / "cisco").glob("spa-*/v*/contract.yaml")):
        data = yaml.safe_load(path.read_text())
        if any(_is_port(p["ref"]) for p in data.get("parts") or []):
            found.append(f"cisco/{path.parts[-3]}@{path.parts[-2][1:]}")
    return found


def test_the_adapters_are_every_spa_contract_that_composes_a_port_part():
    assert sorted(_adapters_composing_ports()) == sorted(ADAPTERS)


@EACH
def test_each_adapter_composes_the_ports_the_guide_prints(ref):
    family, count = ADAPTERS[ref]
    ports = _ports(ref)
    assert len(ports) == count, f"{ref}: {len(ports)} port parts, expected {count}"
    assert {_family(_media(p)) for p in ports} == {family}, ref


@EACH
def test_every_port_part_joins_a_declared_group(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} composes ports and declares no groups"
    for part in _ports(ref):
        assert part.get("group") in groups, \
            f"{ref}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@EACH
def test_every_group_says_what_it_is_for_and_has_members(ref):
    members = {}
    for part in _ports(ref):
        members.setdefault(part.get("group"), []).append(part["id"])
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} declares no groups"
    for name, group in groups.items():
        assert group.get("term"), f"{ref}: group {name} has no term"
        assert group.get("role") in ROLES, f"{ref}: group {name} role {group.get('role')!r}"
        assert group.get("index-origin") == 0, f"{ref}: group {name} index-origin"
        assert (group.get("description") or "").strip(), f"{ref}: group {name} has no description"
        assert members.get(name), f"{ref}: group {name} has no member"


@EACH
def test_a_groups_media_and_speed_agree_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for part in _ports(ref):
        assert part.get("group") in groups, f"{ref}: port {part['id']} joins no declared group"
        attrs = groups[part["group"]].get("attrs") or {}
        own = part.get("attrs") or {}
        if "media" in attrs:
            assert _media(part) == attrs["media"], \
                f"{ref}: {part['id']} is {_media(part)}, its group {part['group']} says {attrs['media']}"
        if "speed" in attrs:
            assert attrs["speed"] in SPEEDS, f"{ref}: {part['group']} speed {attrs['speed']!r}"
            if "speed" in own:
                assert own["speed"] == attrs["speed"], f"{ref}: {part['id']} speed differs from its group"


@EACH
def test_a_port_group_is_one_connector_family(ref):
    families = {}
    for part in _ports(ref):
        assert part.get("group"), f"{ref}: port {part['id']} joins no group"
        families.setdefault(part["group"], set()).add(_family(_media(part)))
    for name, fams in families.items():
        assert len(fams) == 1, f"{ref}: group {name} holds {sorted(fams)}"


@EACH
def test_no_group_states_a_speed_the_closed_set_has_no_word_for(ref):
    for name, group in (_contract(ref).get("groups") or {}).items():
        assert "speed" not in (group.get("attrs") or {}), f"{ref}: group {name} states a speed"
        assert "speeds" not in (group.get("attrs") or {}), f"{ref}: group {name} lists speeds"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} states a speed"


@EACH
def test_a_cage_group_names_its_cage_and_a_coax_group_does_not_rename_its_jack(ref):
    family, _ = ADAPTERS[ref]
    for name, group in (_contract(ref).get("groups") or {}).items():
        media = (group.get("attrs") or {}).get("media")
        if family in ("sfp", "xfp", "rj45"):
            assert media == family, f"{ref}: group {name} media {media!r}, expected {family!r}"
        else:
            assert media in (None, "coax-din-1-0-2-3"), f"{ref}: group {name} media {media!r}"


@EACH
def test_every_group_is_a_traffic_group(ref):
    for name, group in (_contract(ref).get("groups") or {}).items():
        assert group["role"] == "traffic", f"{ref}: group {name} role {group['role']!r}"

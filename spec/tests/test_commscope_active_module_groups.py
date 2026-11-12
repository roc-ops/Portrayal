"""The CommScope CH3000 receivers, transmitter, control module and power supplies say what their ports are for.

Eleven contracts compose a micro-USB port, a front-panel RF test point, or both: the AR3002E, AR3044H,
AR3044L, DR3450N and DR3600N receivers, the HT358xH transmitter, the CC3008 control module and the four
power supplies (PS3006D, PS3006N, PS3248D and PS3248N). Without a group a port on one of them, seated in a
chassis, is drawn with no `data-group` and no `data-group-role`. Each contract below declares `groups:` in
the device shape, and each of its port parts joins one.

What these hold for every module in the list:

  - it declares at least one group, and every port part joins a declared group;
  - every declared group has a term, a role from the schema's list, an index origin of 0 or 1, a
    description, and at least one member;
  - a group is one connector family (one interface), and its declared media agrees with each member's;
  - the data sheets print no data rate for a micro-USB service port or an RF test point, so no group and
    no part states a speed;
  - a micro-USB port is a way into the module, so its group is `management`; a front-panel test point
    carries a sample of the signal the module handles, so its group is `traffic`;
  - the contract's provenance says where each group comes from.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

# module -> {group: (role, media, interface, member part ids)}
USB = ("management", "micro-usb-b", "micro-usb-b", ["usb"])
MODULES = {
    "commscope/ar3002e@1": {"mgmt": USB, "test-point": ("traffic", "coax-g", "g-type", ["rf-tp"])},
    "commscope/ar3044h@1": {"test-point": ("traffic", "coax-g", "g-type", ["rf-tp"])},
    "commscope/ar3044l@1": {"test-point": ("traffic", "coax-g", "g-type", ["rf-tp"])},
    "commscope/dr3450n@1": {"mgmt": USB, "test-point": ("traffic", "coax-g", "g-type", ["rf-tp"])},
    "commscope/dr3600n@1": {"mgmt": USB,
                            "test-point": ("traffic", "coax-g", "g-type-female", ["rf-tp"])},
    "commscope/ht358xh@1": {"test-point": ("traffic", "coax-mcx", "mcx", ["rf-tp"])},
    "commscope/cc3008@1": {"mgmt": USB},
    "commscope/ps3006d@1": {"mgmt": USB},
    "commscope/ps3006n@1": {"mgmt": USB},
    "commscope/ps3248d@1": {"mgmt": USB},
    "commscope/ps3248n@1": {"mgmt": USB},
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


def test_the_list_is_eleven_distinct_modules():
    assert len(MODULES) == 11


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
def test_each_group_is_the_role_and_the_members_the_data_sheet_gives(ref):
    groups = _contract(ref).get("groups") or {}
    assert set(groups) == set(MODULES[ref]), f"{ref}: groups {sorted(groups)}"
    for name, (role, _media_, _iface, ids) in MODULES[ref].items():
        assert groups[name].get("role") == role, f"{ref}: group {name} role {groups[name].get('role')!r}"
        joined = sorted(p["id"] for p in _ports(ref) if p.get("group") == name)
        assert joined == sorted(ids), f"{ref}: group {name} holds {joined}"


@pytest.mark.parametrize("ref", MODULES)
def test_a_groups_media_agrees_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for name, (_role, media, _iface, _ids) in MODULES[ref].items():
        assert (groups[name].get("attrs") or {}).get("media") == media, \
            f"{ref}: group {name} states media {(groups[name].get('attrs') or {}).get('media')!r}"
    for part in _ports(ref):
        assert _media(part) == MODULES[ref][part["group"]][1], \
            f"{ref}: {part['id']} is {_media(part)}, its group says {MODULES[ref][part['group']][1]}"


@pytest.mark.parametrize("ref", MODULES)
def test_a_port_group_is_one_interface(ref):
    families = {}
    for part in _ports(ref):
        assert part.get("group"), f"{ref}: port {part['id']} joins no group"
        families.setdefault(part["group"], set()).add(_interface(part))
    for name, fams in families.items():
        assert fams == {MODULES[ref][name][2]}, f"{ref}: group {name} holds {sorted(fams, key=str)}"


@pytest.mark.parametrize("ref", MODULES)
def test_a_module_states_no_speed(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} declares no groups"
    for name, group in groups.items():
        attrs = group.get("attrs") or {}
        assert "speed" not in attrs and "speeds" not in attrs, f"{ref}: group {name} states a speed"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} states a speed"


@pytest.mark.parametrize("ref", MODULES)
def test_the_provenance_says_where_the_groups_come_from(ref):
    text = (_contract(ref).get("provenance") or {}).get("groups", "")
    assert "data sheet" in text, f"{ref}: provenance/groups cites no data sheet"
    assert "No speed is stated" in text, f"{ref}: provenance/groups does not say why no speed is stated"

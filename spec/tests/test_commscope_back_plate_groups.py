"""The CommScope CH3000 back plates say what their ports are for.

A back plate (the BP-A, BP-F and BD31A8 plates and the BP3400C quad receiver plate) composes its
optical connectors, its SFP cages and its F-type jacks as parts. Without a group a port on a plate
seated in a chassis is drawn with no `data-group` and no `data-group-role`. Each of the seven
contracts below declares `groups:` in the device shape, and each of its port parts joins one.

What these hold for every plate in the list:

  - it declares at least one group, and every port part joins a declared group;
  - every declared group has a term, a role from the schema's list, an index origin of 0 or 1, a
    description, and at least one member;
  - a group is one connector family (one interface), and its declared media agrees with each
    member's;
  - the data sheets print no rate a group can state, so no group and no part states a speed;
  - the optical and RF ports carry traffic, and the one data port of the quad receiver plate, which
    carries the receivers' management traffic, is its own management group.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

# plate -> {group: (role, media, interface, member part ids)}
PLATES = {
    "commscope/bp-a5@1": {
        "optical": ("traffic", "fiber", "sc", ["optical-in-bore"]),
        "rf": ("traffic", "coax-f", "f-type", ["rf-out"]),
    },
    "commscope/bp-a10@1": {
        "optical": ("traffic", "fiber", "lc-duplex", ["optical-1-2", "optical-3-4"]),
        "rf": ("traffic", "coax-f", "f-type", ["rf-out-1", "rf-out-2", "rf-out-3", "rf-out-4"]),
    },
    "commscope/bp-f2@1": {
        "optical": ("traffic", "fiber", "sc", ["input", "output"]),
    },
    "commscope/bp-f2-al@1": {
        "optical": ("traffic", "fiber", "lc-duplex", ["optical"]),
    },
    "commscope/bp-f4@1": {
        "optical": ("traffic", "fiber", "sc", ["input-1", "output-1", "input-2", "output-2"]),
    },
    "commscope/bd31a8-h10f@1": {
        "optical": ("traffic", "fiber", "lc-duplex", ["optical-1-2", "optical-3-4", "optical-5-6", "optical-7-8"]),
        "rf": ("traffic", "coax-f", "f-type", ["rf-nc-1", "rf-nc-2", "rf-nc-3", "rf-nc-4", "rf-bc",
                                               "rf-nc-5", "rf-nc-6", "rf-nc-7", "rf-nc-8"]),
    },
    "commscope/bp3400c@1": {
        "optical": ("traffic", "sfp", "sfp", [f"in-{r}-{p}" for p in ("1-2", "3-4") for r in "dcba"]),
        "data": ("management", "sfp", "sfp", ["data-port"]),
        "rf": ("traffic", "coax-f", "f-type", [f"rf-{r}-{n}" for r in "dcba" for n in "1234"]),
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


def test_the_list_is_seven_distinct_plates():
    assert len(PLATES) == 7


@pytest.mark.parametrize("ref", PLATES)
def test_every_port_part_joins_a_declared_group(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} composes ports and declares no groups"
    ports = _ports(ref)
    assert ports, f"{ref} composes no port part"
    for part in ports:
        assert part.get("group") in groups, \
            f"{ref}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@pytest.mark.parametrize("ref", PLATES)
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


@pytest.mark.parametrize("ref", PLATES)
def test_each_group_is_the_role_and_the_members_the_data_sheet_gives(ref):
    groups = _contract(ref).get("groups") or {}
    assert set(groups) == set(PLATES[ref]), f"{ref}: groups {sorted(groups)}"
    for name, (role, _media_, _iface, ids) in PLATES[ref].items():
        assert groups[name].get("role") == role, f"{ref}: group {name} role {groups[name].get('role')!r}"
        joined = sorted(p["id"] for p in _ports(ref) if p.get("group") == name)
        assert joined == sorted(ids), f"{ref}: group {name} holds {joined}"


@pytest.mark.parametrize("ref", PLATES)
def test_a_groups_media_agrees_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for name, (_role, media, _iface, _ids) in PLATES[ref].items():
        assert (groups[name].get("attrs") or {}).get("media") == media, \
            f"{ref}: group {name} states media {(groups[name].get('attrs') or {}).get('media')!r}"
    for part in _ports(ref):
        assert _media(part) == PLATES[ref][part["group"]][1], \
            f"{ref}: {part['id']} is {_media(part)}, its group says {PLATES[ref][part['group']][1]}"


@pytest.mark.parametrize("ref", PLATES)
def test_a_port_group_is_one_interface(ref):
    families = {}
    for part in _ports(ref):
        assert part.get("group"), f"{ref}: port {part['id']} joins no group"
        families.setdefault(part["group"], set()).add(_interface(part))
    for name, fams in families.items():
        assert fams == {PLATES[ref][name][2]}, f"{ref}: group {name} holds {sorted(fams, key=str)}"


@pytest.mark.parametrize("ref", PLATES)
def test_a_back_plate_states_no_speed(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} declares no groups"
    for name, group in groups.items():
        attrs = group.get("attrs") or {}
        assert "speed" not in attrs and "speeds" not in attrs, f"{ref}: group {name} states a speed"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} states a speed"

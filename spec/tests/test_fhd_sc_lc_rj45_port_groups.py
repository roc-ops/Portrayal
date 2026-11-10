"""The FHD SC cassette, the OM5 LC panel and the RJ45 keystone panel say what their ports are for.

Each contract below composes port parts and, without a group, a port on it seated in an
enclosure is drawn with no `data-group` and no `data-group-role`. Each declares one group
in the device shape and every one of its port parts joins it:

  - the MTP-12 to six SC duplex cassette (front, and the rear face with its MTP adapter),
  - the 12-adapter OM5 LC duplex adapter panel (front and rear),
  - the six-jack RJ45 panel and the Cat6 keystone jack it takes.

What these hold for every contract in the list:

  - every port part joins a declared group and the group has the members the datasheet
    says it has;
  - every group has a term, a role from the schema's list, an index origin of 0 or 1 and a
    description;
  - a group's declared media agrees with each member's;
  - none of the three documents prints a data rate for these ports, so no group and no
    part states a speed;
  - a group holds one kind of part;
  - every group names its source in `provenance.groups`.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

# ref -> (group, how many ports join it, the document `provenance.groups` must cite)
GROUPED = {
    "fs/fhd-1mtp12-sc-os2-a@3": ("adapters", 6, "FHD MTP-12/24 Cassettes Datasheet"),
    "fs/fhd-1mtp12-sc-rear@3": ("adapters", 1, "FHD MTP-12/24 Cassettes Datasheet"),
    "fs/fhd-fap12lcd-om5@1": ("adapters", 12, "FHD Fiber Cabling System Guide"),
    "fs/fhd-fap12lcd-om5-rear@1": ("adapters", 12, "FHD Fiber Cabling System Guide"),
    "fs/fhd-fapm6-rj45@1": ("jacks", 6, "FHD-FAPM6 Multimedia Modular Panel Datasheet"),
    "fs/keystone-rj45-cat6@1": ("jack", 1, "FHD-FAPM6 Multimedia Modular Panel Datasheet"),
}

ROLES = set(json.loads((SPEC / "schemas/component.schema.json").read_text())
            ["$defs"]["group"]["properties"]["role"]["enum"])


def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / ns / name / f"v{major}" / "contract.yaml").read_text())


def _ports(ref):
    return [p for p in _contract(ref).get("parts") or [] if _contract(p["ref"]).get("class") == "port"]


def _media(part):
    own = (part.get("attrs") or {}).get("media")
    return own or (_contract(part["ref"]).get("attrs") or {}).get("media")


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_every_port_part_joins_the_group_and_the_count_is_the_documents(ref):
    name, count, _doc = GROUPED[ref]
    groups = _contract(ref).get("groups") or {}
    assert sorted(groups) == [name], f"{ref} declares {sorted(groups)}, not just {name!r}"
    ports = _ports(ref)
    assert [p["id"] for p in ports if p.get("group") == name] == [p["id"] for p in ports], \
        f"{ref}: a port part joins no group or another one"
    assert len(ports) == count, f"{ref}: {len(ports)} port parts, the documents say {count}"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_the_group_says_what_it_is_for(ref):
    name, _count, _doc = GROUPED[ref]
    group = _contract(ref)["groups"][name]
    assert group.get("term"), f"{ref}: group {name} has no term"
    assert group.get("role") in ROLES, f"{ref}: group {name} role {group.get('role')!r}"
    assert group.get("index-origin") in (0, 1), f"{ref}: group {name} index-origin"
    assert (group.get("description") or "").strip(), f"{ref}: group {name} has no description"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_a_groups_media_agrees_with_its_members(ref):
    name, _count, _doc = GROUPED[ref]
    attrs = _contract(ref)["groups"][name].get("attrs") or {}
    assert "media" in attrs, f"{ref}: group {name} states no media"
    for part in _ports(ref):
        assert _media(part) == attrs["media"], \
            f"{ref}: {part['id']} is {_media(part)}, its group says {attrs['media']}"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_no_port_states_a_speed_the_documents_do_not_print(ref):
    name, _count, _doc = GROUPED[ref]
    assert "speed" not in (_contract(ref)["groups"][name].get("attrs") or {}), f"{ref}: group {name} states a speed"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} states a speed"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_a_group_holds_one_kind_of_part(ref):
    kinds = {p["ref"] for p in _ports(ref)}
    assert len(kinds) == 1, f"{ref}: the group holds {sorted(kinds)}"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_the_group_names_its_source(ref):
    _name, _count, doc = GROUPED[ref]
    text = (_contract(ref).get("provenance") or {}).get("groups") or ""
    assert text.strip(), f"{ref}: provenance.groups is missing"
    assert doc in text, f"{ref}: provenance.groups does not cite {doc!r}"

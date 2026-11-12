"""The FHD splice cassette, its rear face and the rear face of the RJ45 panel say which family their ports belong to.

Each contract below composes port parts: the six LC duplex adapters of the splice cassette, the
splice tray on its rear face, and the six punch-down terminations behind the jacks of the RJ45
panel. Without a group, a port on one of them is drawn with no `data-group` and no
`data-group-role`. Each declares one group and every port part joins it:

  - a group's declared media agrees with each member's;
  - every group has a term, a role from the schema's list, an index origin and a description;
  - no group states a speed: no page or catalogue row held for these parts prints a data rate;
  - every group names its source in `provenance.groups`.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

# ref -> (group, port parts that join it, the document `provenance.groups` must cite)
GROUPED = {
    "fs/fhd-splice-12-lc@3": ("adapters", ["lc1", "lc2", "lc3", "lc4", "lc5", "lc6"], "382907"),
    "fs/fhd-splice-12-lc-rear@2": ("splices", ["splice"], "382907"),
    "fs/fhd-fapm6-rj45-rear@1": ("terminations", ["b1", "b2", "b3", "b4", "b5", "b6"],
                                 "FHD-FAPM6 Multimedia Modular Panel Datasheet"),
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
def test_every_port_part_joins_the_group(ref):
    name, ids, _doc = GROUPED[ref]
    groups = _contract(ref).get("groups") or {}
    assert sorted(groups) == [name], f"{ref} declares {sorted(groups)}, not just {name!r}"
    ports = _ports(ref)
    assert [p["id"] for p in ports] == ids, f"{ref}: port parts {[p['id'] for p in ports]}, not {ids}"
    assert [p["id"] for p in ports if p.get("group") == name] == ids, \
        f"{ref}: a port part joins no group or another one"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_the_group_says_what_it_is_for(ref):
    name, _ids, _doc = GROUPED[ref]
    group = _contract(ref)["groups"][name]
    assert group.get("term"), f"{ref}: group {name} has no term"
    assert group.get("role") in ROLES, f"{ref}: group {name} role {group.get('role')!r}"
    assert group.get("index-origin") in (0, 1), f"{ref}: group {name} index-origin"
    assert (group.get("description") or "").strip(), f"{ref}: group {name} has no description"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_a_groups_media_agrees_with_its_members(ref):
    name, _ids, _doc = GROUPED[ref]
    attrs = _contract(ref)["groups"][name].get("attrs") or {}
    assert "media" in attrs, f"{ref}: group {name} states no media"
    for part in _ports(ref):
        assert _media(part) == attrs["media"], \
            f"{ref}: {part['id']} is {_media(part)}, its group says {attrs['media']}"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_no_speed_is_stated(ref):
    """No page or catalogue row held for these parts prints a data rate."""
    name, _ids, _doc = GROUPED[ref]
    attrs = _contract(ref)["groups"][name].get("attrs") or {}
    assert "speed" not in attrs and "speeds" not in attrs, f"{ref}: group {name} states a speed"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} states a speed"


@pytest.mark.parametrize("ref", sorted(GROUPED))
def test_the_group_names_its_source(ref):
    _name, _ids, doc = GROUPED[ref]
    text = (_contract(ref).get("provenance") or {}).get("groups") or ""
    assert text.strip(), f"{ref}: provenance.groups is missing"
    assert doc in text, f"{ref}: provenance.groups does not cite {doc!r}"

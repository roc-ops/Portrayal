"""The generic CFP, CFP2, CFP4, CXP and XFP transceiver shapes say which family their ports belong to.

Each contract below stands for every module of its shape and composes port parts: the optical
bores or the MPO receptacle of the module. Without a group, a port on a module
seated in a cage is drawn with no `data-group` and no `data-group-role`. Each declares one
group, named for the form factor of the module, and every port part joins it:

  - what a shape stands for is its form factor, so the group is named for it;
  - the shape stands for every module of its kind, so rate, reach and watts belong on the
    vendor's wrapper and no group or part here states a speed;
  - a group's declared media agrees with each member's;
  - every group has a term, a role from the schema's list, an index origin and a description;
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
    "generic/cfp-lc@1": ("cfp", ["tx", "rx"], "CFP MSA Hardware Specification Rev 1.4"),
    "generic/cfp-mpo@1": ("cfp", ["mpo"], "Gigalight GCF-M101-SR10C"),
    "generic/cfp-sc@1": ("cfp", ["tx", "rx"], "CFP MSA Module Dimensions drawing"),
    "generic/cfp2-lc@1": ("cfp2", ["tx", "rx"], "CFP MSA CFP2 Hardware Specification Rev 1.0"),
    "generic/cfp2-mpo@1": ("cfp2", ["mpo"], "Gigalight GF2-M101-SR10C"),
    "generic/cfp4-lc@1": ("cfp4", ["tx", "rx"], "Finisar FTLC1141RDNL"),
    "generic/cfp4-mpo@1": ("cfp4", ["mpo"], "Gigalight GF4-M101-SR4C"),
    "generic/cxp-mpo@1": ("cxp", ["mpo"], "Finisar FTLD12CL3C"),
    "generic/xfp-lc@1": ("xfp", ["tx", "rx"], "INF-8077i"),
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
def test_the_group_is_named_for_the_form_factor(ref):
    name, _ids, _doc = GROUPED[ref]
    assert _contract(ref)["attrs"]["form-factor"] == name, \
        f"{ref}: group {name!r}, form-factor {_contract(ref)['attrs']['form-factor']!r}"


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
def test_a_shape_states_no_speed(ref):
    """The shape stands for every module of its kind: the rate is the wrapper's fact."""
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

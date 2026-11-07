"""The FHD MTP-to-LC cassettes say what their ports are for.

An FHD MTP cassette composes its front connectors as parts (LC duplex adapters,
shuttered on the 36-fibre cassette) and carries its MTP adapters on a rear face
of its own. Without a group a port on a cassette seated in an enclosure is drawn
with no `data-group` and no `data-group-role`. Each of the 29 contracts below
declares `groups:` in the device shape, and each of its port parts joins one.

What these hold for every contract in the list:

  - it declares at least one group, and every port part joins a declared group;
  - every declared group has a term, a role from the schema's list, an index
    origin of 0 or 1, a description, and at least one member;
  - a group's declared media agrees with each member's;
  - a passive adapter has no data rate, so no group and no part states a speed;
  - a port group is one connector family;
  - a cassette's front holds as many LC duplex adapters as its name counts, its
    rear as many MTP adapters, and the fibres on both sides agree;
  - every group names its source in `provenance.groups`.

The census at the end holds for every version of every cassette of the four
families: none composes ports and declares no groups.
"""
import json
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library" / "components"

# front, LC duplex adapters on the face: ref -> the number of adapters its name counts
FRONTS = {
    "fs/fhd-1mtp6lcd-os2-a@4": 6, "fs/fhd-1mtp6lcd-om4-a@2": 6, "fs/fhd-1mtp6lcd-om5-a@2": 6,
    "fs/fhd-1mtp6lcd-os2-af@3": 6, "fs/fhd-1mtp6lcd-os2-u@3": 6, "fs/fhd-1mtp6lcd-om4-u@2": 6,
    "fs/fhd-1mtp24-lc-os2-a@4": 12, "fs/fhd-1mtp24-lc-om4-a@2": 12, "fs/fhd-1mtp24-lc-om5-a@2": 12,
    "fs/fhd-1mtp24-lc-om3-a@2": 12, "fs/fhd-1mtp24-lc-os2-af@4": 12,
    "fs/fhd-2mtp12-lc-os2-a@4": 12, "fs/fhd-2mtp12-lc-om4-a@2": 12, "fs/fhd-2mtp12-lc-om5-a@2": 12,
    "fs/fhd-2mtp12-lc-om3-a@2": 12, "fs/fhd-2mtp12-lc-os2-af@4": 12, "fs/fhd-2mtp12-lc-os2-u@4": 12,
    "fs/fhd-2mtp12-lc-om4-u@2": 12,
    "fs/fhd-3mtp18-lc-os2-a@1": 18, "fs/fhd-3mtp18-lc-om4-a@1": 18,
}
# rear, MTP adapters on the face
REARS = {
    "fs/fhd-1mtp6lcd-rear@3": 1, "fs/fhd-1mtp6lcd-af-rear@2": 1, "fs/fhd-1mtp6lcd-u-rear@2": 1,
    "fs/fhd-1mtp24-lc-rear@3": 1, "fs/fhd-1mtp24-lc-af-rear@2": 1,
    "fs/fhd-2mtp12-lc-rear@2": 2, "fs/fhd-2mtp12-lc-af-rear@1": 2, "fs/fhd-2mtp12-lc-u-rear@1": 2,
    "fs/fhd-3mtp18-lc-rear@1": 3,
}
CASSETTES = sorted(list(FRONTS) + list(REARS))

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


def _connector(part):
    return (_contract(part["ref"]).get("attrs") or {}).get("connector")


def _fibres_of_mtp(part):
    return 24 if "mpo24" in part["ref"] else 12


@pytest.mark.parametrize("ref", CASSETTES)
def test_every_port_part_joins_a_declared_group(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} composes ports and declares no groups"
    for part in _ports(ref):
        assert part.get("group") in groups, \
            f"{ref}: port {part['id']} joins {part.get('group')!r}, declared: {sorted(groups)}"


@pytest.mark.parametrize("ref", CASSETTES)
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


@pytest.mark.parametrize("ref", CASSETTES)
def test_a_groups_media_agrees_with_its_members(ref):
    groups = _contract(ref).get("groups") or {}
    for part in _ports(ref):
        assert part.get("group") in groups, f"{ref}: port {part['id']} joins no declared group"
        attrs = groups[part["group"]].get("attrs") or {}
        if "media" in attrs:
            assert _media(part) == attrs["media"], \
                f"{ref}: {part['id']} is {_media(part)}, its group {part['group']} says {attrs['media']}"


@pytest.mark.parametrize("ref", CASSETTES)
def test_a_passive_adapter_states_no_speed(ref):
    groups = _contract(ref).get("groups") or {}
    assert groups, f"{ref} declares no groups"
    for name, group in groups.items():
        assert "speed" not in (group.get("attrs") or {}), f"{ref}: group {name} gives a passive adapter a speed"
    for part in _ports(ref):
        assert "speed" not in (part.get("attrs") or {}), f"{ref}: {part['id']} gives a passive adapter a speed"


@pytest.mark.parametrize("ref", CASSETTES)
def test_a_port_group_is_one_connector_family(ref):
    families = {}
    for part in _ports(ref):
        assert part.get("group"), f"{ref}: port {part['id']} joins no group"
        families.setdefault(part["group"], set()).add(_connector(part))
    for name, fams in families.items():
        assert len(fams) == 1, f"{ref}: group {name} holds {sorted(fams, key=str)}"


@pytest.mark.parametrize("ref", CASSETTES)
def test_every_group_names_its_source(ref):
    contract = _contract(ref)
    text = (contract.get("provenance") or {}).get("groups") or ""
    assert "Datasheet" in text and "page" in text, f"{ref}: provenance.groups names no datasheet page"
    assert "no data rate" in text, f"{ref}: provenance.groups does not say the page prints no rate"


@pytest.mark.parametrize("ref,count", sorted(FRONTS.items()))
def test_the_front_holds_the_adapters_its_name_counts(ref, count):
    assert len(_ports(ref)) == count, f"{ref}: {len(_ports(ref))} LC duplex adapters, expected {count}"
    assert {_connector(p) for p in _ports(ref)} == {"lc-duplex"} or \
        {_connector(p) for p in _ports(ref)} == {"lc"}, f"{ref}: a front port that is not an LC duplex adapter"


@pytest.mark.parametrize("ref,count", sorted(REARS.items()))
def test_the_rear_holds_the_mtp_adapters_its_name_counts(ref, count):
    ports = _ports(ref)
    assert len(ports) == count, f"{ref}: {len(ports)} MTP adapters, expected {count}"
    assert {_connector(p) for p in ports} == {"mpo"}, f"{ref}: a rear port that is not an MTP adapter"


@pytest.mark.parametrize("ref", sorted(FRONTS))
def test_the_fibres_on_the_front_and_the_rear_agree(ref):
    rear = _contract(ref)["faces"]["rear"]["ref"]
    assert rear in REARS, f"{ref}: its rear face {rear} is not in this list"
    front_fibres = 2 * len(_ports(ref))
    rear_fibres = sum(_fibres_of_mtp(p) for p in _ports(rear))
    assert front_fibres == rear_fibres, f"{ref}: {front_fibres} fibres on the front, {rear_fibres} on {rear}"


def test_no_cassette_of_the_four_families_composes_ports_without_groups():
    bad = []
    for path in sorted((LIB / "fs").glob("fhd-*/v*/contract.yaml")):
        name = path.parent.parent.name
        if not name.startswith(("fhd-1mtp6lcd", "fhd-1mtp24-lc", "fhd-2mtp12-lc", "fhd-3mtp18-lc")):
            continue
        contract = yaml.safe_load(path.read_text())
        ports = [p for p in contract.get("parts") or [] if _is_port(p["ref"])]
        if ports and not contract.get("groups"):
            bad.append(f"fs/{name}@{path.parent.name[1:]}")
    assert not bad, f"compose ports and declare no groups: {bad}"

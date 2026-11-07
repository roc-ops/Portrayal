"""The ports of the Juniper circuit MICs (SONET/SDH, ATM, DS3/E3 and E1/T1) belong to a port group.

A group is the vendor's name for a bank of ports: it says what the bank is for and, only where the
vendor's guide prints one, the media its ports share. These MICs take several rates in one cage (a
port is OC3 or OC12, DS3 or E3, E1 or T1), and the speed vocabulary has no word for any of those
rates, so no group states a speed.
"""
from pathlib import Path

import pytest
import yaml

COMPONENTS = Path(__file__).resolve().parents[2] / "library" / "components" / "juniper"

# family -> (the media the guide's title or connector row names for the whole bank, or None)
FAMILIES = {
    "mic-3d-4choc3-1oc12": "sfp",
    "mic-3d-4choc3-2choc12": "sfp",
    "mic-3d-8choc3-4choc12": "sfp",
    "mic-3d-4oc3oc12-1oc48": "sfp",
    "mic-3d-8oc3oc12-4oc48": "sfp",
    "mic-3d-8oc3-2oc12-atm": "sfp",
    "mic-3d-16che1-t1-ce": None,
    "mic-3d-8ds3-e3": "coax",
}

# every contract of the families whose ports this change joins to a group: the current form of each
# MIC and the earlier forms that stay published
CONTRACTS = (
    [(name, "v2") for name in FAMILIES]
    + [(name, "v1") for name in FAMILIES if name != "mic-3d-4choc3-1oc12"]
    + [(name + "-v", "v1") for name in FAMILIES if name != "mic-3d-4choc3-1oc12"]
)


def _load(name, version):
    return yaml.safe_load((COMPONENTS / name / version / "contract.yaml").read_text())


def _family(name):
    return name[:-2] if name.endswith("-v") else name


def _ports(contract):
    out = []
    for part in contract["parts"]:
        ref = part["ref"]
        base, _, ver = ref.partition("@")
        part_contract = COMPONENTS.parent / base / f"v{ver}" / "contract.yaml"
        if yaml.safe_load(part_contract.read_text()).get("class") == "port":
            out.append(part)
    return out


@pytest.fixture(params=CONTRACTS, ids=[f"{n}@{v}" for n, v in CONTRACTS])
def mic(request):
    name, version = request.param
    return name, version, _load(name, version)


def test_every_port_part_joins_a_declared_group(mic):
    name, version, contract = mic
    ports = _ports(contract)
    assert ports, f"juniper/{name}@{version} composes no port part"
    groups = contract.get("groups") or {}
    assert groups, f"juniper/{name}@{version} declares no groups"
    loose = [p["id"] for p in ports if p.get("group") not in groups]
    assert not loose, f"juniper/{name}@{version}: ports in no declared group: {loose}"


def test_a_group_is_for_the_circuits_a_customer_plugs_in(mic):
    name, version, contract = mic
    for gname, group in (contract.get("groups") or {}).items():
        assert group.get("role") == "traffic", f"{name}@{version} group {gname}"
        assert group.get("index-origin") == 0, f"{name}@{version} group {gname}"
        assert group.get("term"), f"{name}@{version} group {gname}"
        assert group.get("description"), f"{name}@{version} group {gname}"


def test_a_group_holds_a_port_and_no_group_is_empty(mic):
    name, version, contract = mic
    used = {p.get("group") for p in _ports(contract)}
    assert set(contract.get("groups") or {}) == used


def test_no_group_states_a_rate_the_vocabulary_cannot_spell(mic):
    name, version, contract = mic
    for gname, group in (contract.get("groups") or {}).items():
        attrs = group.get("attrs") or {}
        assert "speed" not in attrs and "speeds" not in attrs, f"{name}@{version} group {gname}"


def test_a_group_states_the_media_only_where_the_guide_names_one(mic):
    name, version, contract = mic
    want = FAMILIES[_family(name)]
    for gname, group in (contract.get("groups") or {}).items():
        attrs = group.get("attrs") or {}
        assert attrs.get("media") == want, f"{name}@{version} group {gname}"
        for p in _ports(contract):
            own = (p.get("attrs") or {}).get("media")
            assert want is None or own == want, f"{name}@{version} {p['id']} states {own}"


def test_the_source_of_a_group_is_in_the_provenance(mic):
    name, version, contract = mic
    text = (contract.get("provenance") or {}).get("groups", "")
    assert "Interface Module Reference" in text
    assert "No speed is stated" in text

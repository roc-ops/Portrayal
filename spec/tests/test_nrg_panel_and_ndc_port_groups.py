"""The ports of the Amphenol Network Solutions rear centre blocks and of the Dell 14G network daughter card
belong to a port group.

A group is the vendor's name for a bank of ports: it says what the bank is for and, only where a document
prints one, the media its ports share. Nothing here states a speed for the three rear blocks: the guides
print no data rate for an alarm relay header or for the nrgNET link.
"""
from pathlib import Path

import pytest
import yaml

COMPONENTS = Path(__file__).resolve().parents[2] / "library" / "components"

# contract -> {group: (term, role, media or None, [member part ids])}
EXPECTED = {
    "amphenol-ns/alarm-card-307608": {
        "alarms": ("Alarm", "management", None, ["alarm-b", "alarm-a"]),
    },
    "amphenol-ns/nrg-rear-block": {
        "alarms": ("Alarm", "management", None, ["alarm-b", "alarm-a"]),
        "nrgnet": ("Port", "management", None, ["nrgnet-in", "nrgnet-out"]),
    },
    "amphenol-ns/nrg-ils-rear-block": {
        "nrgnet": ("Port", "management", "rj45-serial", ["nrgnet-in", "nrgnet-out"]),
    },
    "dell/ndc-4x-rj45-14g": {
        "ports": ("Port", "traffic", "rj45", ["port-1", "port-2", "port-3", "port-4"]),
    },
}

ROLES = {"traffic", "fabric", "management", "service", "indicator", "furniture", "stack-control"}


def _load(ref):
    return yaml.safe_load((COMPONENTS / ref / "v1" / "contract.yaml").read_text())


def _port_parts(contract):
    out = []
    for part in contract.get("parts") or []:
        base, _, ver = part["ref"].partition("@")
        part_contract = yaml.safe_load((COMPONENTS / base / f"v{ver}" / "contract.yaml").read_text())
        if part_contract.get("class") == "port":
            out.append(part)
    return out


@pytest.fixture(params=sorted(EXPECTED), ids=sorted(EXPECTED))
def card(request):
    return request.param, _load(request.param)


def test_every_port_part_joins_a_declared_group(card):
    ref, contract = card
    ports = _port_parts(contract)
    assert ports, f"{ref} composes no port part"
    groups = contract.get("groups") or {}
    assert groups, f"{ref} declares no groups"
    loose = [p["id"] for p in ports if p.get("group") not in groups]
    assert not loose, f"{ref}: ports in no declared group: {loose}"


def test_each_group_is_the_one_stated_and_holds_the_parts_named(card):
    ref, contract = card
    groups = contract.get("groups") or {}
    assert set(groups) == set(EXPECTED[ref]), f"{ref}: groups {sorted(groups)}"
    for name, (term, role, media, members) in EXPECTED[ref].items():
        g = groups[name]
        assert g["term"] == term, f"{ref}/{name}: term {g['term']!r}"
        assert g["role"] == role and role in ROLES, f"{ref}/{name}: role {g.get('role')!r}"
        assert g.get("index-origin") == 1, f"{ref}/{name}: index-origin {g.get('index-origin')!r}"
        assert (g.get("attrs") or {}).get("media") == media, f"{ref}/{name}: media {(g.get('attrs') or {}).get('media')!r}"
        assert g.get("description"), f"{ref}/{name}: no description"
        held = [p["id"] for p in _port_parts(contract) if p.get("group") == name]
        assert held == members, f"{ref}/{name}: holds {held}"


def test_no_group_states_a_speed(card):
    ref, contract = card
    for name, g in (contract.get("groups") or {}).items():
        attrs = g.get("attrs") or {}
        assert "speed" not in attrs and "speeds" not in attrs, f"{ref}/{name} states a speed"


def test_the_contract_says_where_its_groups_come_from(card):
    ref, contract = card
    text = (contract.get("provenance") or {}).get("groups")
    assert text and len(text.split()) > 12, f"{ref}: no provenance.groups"


def test_the_dell_ports_keep_the_speed_each_one_states():
    contract = _load("dell/ndc-4x-rj45-14g")
    speeds = {p["id"]: (p.get("attrs") or {}).get("speed") for p in _port_parts(contract)}
    assert speeds == {"port-1": "10g", "port-2": "10g", "port-3": "1g", "port-4": "1g"}

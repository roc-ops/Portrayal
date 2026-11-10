"""The six Dell OCP NIC 3.0 cards put their ports in one group each.

Each contract declares `groups:` in the shape of a device group, and every port part joins it with
`group:`. Dell's PowerEdge technical guides list each card in a table of supported OCP cards by port
type, port speed and port count, so one card's ports are one kind at one rate. A group carries that
media and speed and nothing else. The guides print no label for an individual port, so the group
numbers its ports as the contract's part ids already do, from 1. No port id, position or part of any
contract is renamed or moved.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "library/components/dell"

ROLES = {"traffic", "fabric", "management", "service", "indicator", "furniture", "stack-control"}
SPEEDS = yaml.safe_load((ROOT / "spec/schemas/speeds.yaml").read_text())["speeds"]

# card -> (ports, media, speed)
CARDS = {
    "ocp3-2x100g-qsfp56": (2, "qsfp56", "100g"),
    "ocp3-2x10g-rj45": (2, "rj45", "10g"),
    "ocp3-4x10g-rj45": (4, "rj45", "10g"),
    "ocp3-4x1g-rj45": (4, "rj45", "1g"),
    "ocp3-2x25g-sfp28": (2, "sfp28", "25g"),
    "ocp3-4x25g-sfp28": (4, "sfp28", "25g"),
}


def load(name):
    return yaml.safe_load((COMP / name / "v1" / "contract.yaml").read_text())


def ports(data):
    return [p for p in data.get("parts") or [] if str(p["id"]).startswith("port-")]


def test_the_cards_are_the_six_the_guides_list():
    assert len(CARDS) == 6
    for name in CARDS:
        assert (COMP / name / "v1" / "contract.yaml").is_file(), name


@pytest.mark.parametrize("name", sorted(CARDS))
def test_every_port_part_joins_one_declared_group(name):
    data = load(name)
    declared = data.get("groups") or {}
    assert len(declared) == 1, f"{name} declares {len(declared)} groups"
    plist = ports(data)
    assert len(plist) == CARDS[name][0]
    loose = [p["id"] for p in plist if not p.get("group")]
    assert not loose, f"{name}: port parts in no group: {loose}"
    assert {p["group"] for p in plist} == set(declared)


@pytest.mark.parametrize("name", sorted(CARDS))
def test_the_group_says_what_it_is_for_and_where_numbering_starts(name):
    for gid, g in load(name)["groups"].items():
        assert g["term"] == "Port", gid
        assert g["role"] in ROLES, gid
        assert g["role"] == "traffic", f"{name}/{gid}: the ports carry the card's traffic"
        assert g["index-origin"] == 1, f"{name}/{gid}: the part ids number the ports from 1"
        assert (g.get("description") or "").strip(), gid


@pytest.mark.parametrize("name", sorted(CARDS))
def test_the_group_carries_the_media_and_speed_the_guide_lists(name):
    _, media, speed = CARDS[name]
    for g in load(name)["groups"].values():
        assert (g.get("attrs") or {}) == {"media": media, "speed": speed}, name
        assert g["attrs"]["speed"] in SPEEDS


@pytest.mark.parametrize("name", sorted(CARDS))
def test_a_port_keeps_the_media_and_speed_it_stated(name):
    _, media, speed = CARDS[name]
    for p in ports(load(name)):
        assert (p.get("attrs") or {}) == {"media": media, "speed": speed}, p["id"]


@pytest.mark.parametrize("name", sorted(CARDS))
def test_the_port_ids_are_still_numbered_from_1_in_order(name):
    count = CARDS[name][0]
    assert [p["id"] for p in ports(load(name))] == [f"port-{n}" for n in range(1, count + 1)]


@pytest.mark.parametrize("name", sorted(CARDS))
def test_provenance_names_the_guide_and_the_role(name):
    text = " ".join(str(load(name)["provenance"]["groups"]).split())
    assert "Technical Guide" in text
    assert "Supported OCP cards" in text
    assert "role is traffic" in text

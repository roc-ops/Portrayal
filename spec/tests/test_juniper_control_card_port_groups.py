"""The MX304 line card, the EX4500 Virtual Chassis module and three routing-engine boards put their ports in groups.

Each contract below declares `groups:` in the shape of a device group, and every port part joins
one with `group:`. A group's `attrs` carry a media and a speed only where a page prints one for that
port block: the MX304 hardware guide's port-speed table and figure (four cages at 400G/100G, the other
twelve at 100G), and nowhere else. The Virtual Chassis module's two ports have no rate on any page, and
the routing-engine boards' ports are a management cluster of mixed media, so those groups state none.
The one rate the CB-RE guide prints, 10/100/1000 Mbps for the MGMT port, is a port's own `speed`, as it
is on the sibling CB-RE. No port id, position or part of any contract is renamed or moved.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "library/components/juniper"

ROLES = {"traffic", "fabric", "management", "service", "indicator", "furniture", "stack-control"}
SPEEDS = yaml.safe_load((ROOT / "spec/schemas/speeds.yaml").read_text())["speeds"]

CB_RE_GROUPS = {"mgmt": ("management", None, 5), "timing": ("management", {}, 1)}

# component -> (live major, parts, {group: (its role, its attrs or None where `mixed:` says why, members)})
CARDS = {
    "mx304-lmic16": ("v1", 16, {
        "qsfp-dd-400g": ("traffic", {"media": "qsfp-dd", "speed": "400g", "speeds": ["100g", "400g"]}, 4),
        "qsfp-dd-100g": ("traffic", {"media": "qsfp-dd", "speed": "100g"}, 12),
    }),
    "ex4500-vc1": ("v1", 2, {"vcp": ("traffic", {}, 2)}),
    "re-s-2000": ("v2", 4, {"mgmt": ("management", None, 4)}),
    "mx2000-cb-re-128g-v": ("v2", 6, CB_RE_GROUPS),
    "mx2000-cb-re-1800-v": ("v2", 6, CB_RE_GROUPS),
}

CONTRACTS = sorted((name, spec[0]) for name, spec in CARDS.items())

FOUR_HUNDRED = {"port-0", "port-6", "port-8", "port-14"}
SERIAL = {"re-s-2000": {"aux", "console"}, "mx2000-cb-re-128g-v": {"aux", "console"},
          "mx2000-cb-re-1800-v": {"aux", "console"}}


def load(name, ver):
    return yaml.safe_load((COMP / name / ver / "contract.yaml").read_text())


def ids(case):
    return f"{case[0]}/{case[1]}"


def test_the_cards_cover_the_five_contracts():
    assert len(CONTRACTS) == 5
    for name, ver in CONTRACTS:
        assert (COMP / name / ver / "contract.yaml").is_file()


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_every_port_part_joins_a_declared_group(case):
    name, ver = case
    data = load(name, ver)
    declared = data.get("groups") or {}
    assert declared, f"{name}/{ver} declares no groups"
    assert len(data["parts"]) == CARDS[name][1]
    loose = [p["id"] for p in data["parts"] if not p.get("group")]
    assert not loose, f"{name}/{ver}: parts in no group: {loose}"
    unknown = {p["group"] for p in data["parts"]} - set(declared)
    assert not unknown, f"{name}/{ver}: groups used and not declared: {unknown}"
    for gid, (_, _, members) in CARDS[name][2].items():
        joined = [p["id"] for p in data["parts"] if p["group"] == gid]
        assert len(joined) == members, f"{name}/{ver}/{gid}: {joined}"


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_each_group_says_what_it_is_for_and_where_numbering_starts(case):
    name, ver = case
    for gid, g in load(name, ver)["groups"].items():
        assert g["term"] == "Port", gid
        assert g["role"] in ROLES, gid
        assert g["role"] == CARDS[name][2][gid][0], f"{name}/{ver}/{gid}"
        assert g["index-origin"] == 0, f"{name}/{ver}/{gid}: the ports are numbered from 0"
        if CARDS[name][2][gid][1] is None:
            assert (g.get("mixed") or "").strip(), f"{name}/{ver}/{gid}: mixed media need a mixed: sentence"
        else:
            assert (g.get("description") or "").strip(), gid


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_a_group_carries_only_what_the_page_prints(case):
    name, ver = case
    declared = load(name, ver)["groups"]
    assert set(declared) == set(CARDS[name][2])
    for gid, (_, attrs, _) in CARDS[name][2].items():
        assert (declared[gid].get("attrs") or {}) == (attrs or {}), f"{name}/{ver}/{gid}"
    for g in declared.values():
        a = g.get("attrs") or {}
        if "speed" in a:
            assert a["speed"] in SPEEDS
        assert set(a.get("speeds") or []) <= set(SPEEDS)
        if a.get("speeds"):
            assert a["speed"] in a["speeds"]


def test_the_four_400g_cages_of_the_mx304_card_are_the_ones_the_figure_colours():
    data = load("mx304-lmic16", "v1")
    got = {p["id"] for p in data["parts"] if p["group"] == "qsfp-dd-400g"}
    assert got == FOUR_HUNDRED
    for p in data["parts"]:
        assert p["attrs"]["speed"] == data["groups"][p["group"]]["attrs"]["speed"], p["id"]


def test_the_virtual_chassis_ports_state_no_media_and_no_rate():
    data = load("ex4500-vc1", "v1")
    assert [p["id"] for p in data["parts"]] == ["vcp-0", "vcp-1"]
    assert "attrs" not in data["groups"]["vcp"]
    assert all("speed" not in (p.get("attrs") or {}) for p in data["parts"])


@pytest.mark.parametrize("name", sorted(SERIAL))
def test_a_console_or_auxiliary_jack_is_typed_serial(name):
    ver = CARDS[name][0]
    for p in load(name, ver)["parts"]:
        media = (p.get("attrs") or {}).get("media")
        if p["id"] in SERIAL[name]:
            assert media == "rj45-serial", f"{name}/{p['id']}"
        else:
            assert media != "rj45-serial", f"{name}/{p['id']}"


@pytest.mark.parametrize("name", ["mx2000-cb-re-128g-v", "mx2000-cb-re-1800-v"])
def test_the_cb_re_management_jack_carries_the_one_rate_its_guide_prints(name):
    parts = {p["id"]: p for p in load(name, "v2")["parts"]}
    assert parts["mgmt"]["attrs"]["speed"] == "1g"
    assert parts["mgmt"]["attrs"]["media"] == "rj45"
    assert parts["bits"]["group"] == "timing"
    assert parts["bits"]["attrs"]["media"] == "rj48"
    assert all("speed" not in (p.get("attrs") or {}) for i, p in parts.items() if i != "mgmt")


def test_the_routing_engine_ethernet_jack_states_no_rate():
    parts = {p["id"]: p for p in load("re-s-2000", "v2")["parts"]}
    assert "speed" not in parts["ethernet"]["attrs"]
    assert parts["ethernet"]["attrs"]["media"] == "rj45"


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_provenance_names_the_source_of_the_groups(case):
    name, ver = case
    text = " ".join(str(load(name, ver)["provenance"]["groups"]).split())
    assert "Hardware Guide" in text
    assert "Juniper" in text

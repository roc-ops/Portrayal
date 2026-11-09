"""The Juniper MIC3 and MIC6 modules put every port in a group of their own.

Each contract below declares `groups:` in the shape of a device group, and every port part joins
one with `group:`. A group's `attrs` carry a media and a speed that the MX Series Interface Module
Reference prints for the port: 'speeds up to 10 Gbps' for the SFP+ MICs, 'speeds up to 40 Gbps' for
the QSFP+ MIC, and 100 Gbps for the CFP, CFP2 and CXP MICs. The book numbers every port from 0. No
port id, position or part of any contract is renamed or moved.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "library/components/juniper"

ROLES = {"traffic", "fabric", "management", "service", "indicator", "furniture", "stack-control"}
SPEEDS = yaml.safe_load((ROOT / "spec/schemas/speeds.yaml").read_text())["speeds"]

# family -> (the component names it covers, ports on one contract, {group: its attrs})
FAMILIES = {
    "mic3-10xge-sfpp": (("mic3-3d-10xge-sfpp", "mic3-3d-10xge-sfpp-v"), 10,
                        {"sfp-plus-10g": {"media": "sfp-plus", "speed": "10g"}}),
    "mic3-2x40ge-qsfpp": (("mic3-3d-2x40ge-qsfpp", "mic3-3d-2x40ge-qsfpp-v"), 2,
                          {"qsfp-plus-40g": {"media": "qsfp-plus", "speed": "40g"}}),
    "mic3-1x100ge-cfp": (("mic3-3d-1x100ge-cfp", "mic3-3d-1x100ge-cfp-v"), 1,
                         {"cfp-100g": {"media": "cfp", "speed": "100g"}}),
    "mic3-1x100ge-cxp": (("mic3-3d-1x100ge-cxp", "mic3-3d-1x100ge-cxp-v"), 1,
                         {"cxp-100g": {"media": "cxp", "speed": "100g"}}),
    "mic6-10g": (("mic6-10g",), 24,
                 {"sfp-plus-10g": {"media": "sfp-plus", "speed": "10g"}}),
    "mic6-100g-cxp": (("mic6-100g-cxp",), 4,
                      {"cxp-100g": {"media": "cxp", "speed": "100g"}}),
    "mic6-100g-cfp2": (("mic6-100g-cfp2",), 2,
                       {"cfp2-100g": {"media": "cfp2", "speed": "100g"}}),
}

CONTRACTS = sorted(
    (name, path.parent.name, family)
    for family, (names, _, _) in FAMILIES.items()
    for name in names
    for path in (COMP / name).glob("v*/contract.yaml")
)


def load(name, ver):
    return yaml.safe_load((COMP / name / ver / "contract.yaml").read_text())


def ports(data):
    return [p for p in data.get("parts") or [] if str(p["id"]).startswith("port-")]


def ids(case):
    return f"{case[0]}/{case[1]}"


def test_the_families_cover_every_contract_of_the_fifteen():
    assert len(CONTRACTS) == 15
    assert len({name for name, _, _ in CONTRACTS}) == 11


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_every_port_part_joins_a_declared_group(case):
    name, ver, family = case
    data = load(name, ver)
    declared = data.get("groups") or {}
    assert declared, f"{name}/{ver} declares no groups"
    plist = ports(data)
    assert len(plist) == FAMILIES[family][1]
    loose = [p["id"] for p in plist if not p.get("group")]
    assert not loose, f"{name}/{ver}: port parts in no group: {loose}"
    unknown = {p["group"] for p in plist} - set(declared)
    assert not unknown, f"{name}/{ver}: groups used and not declared: {unknown}"
    unused = set(declared) - {p["group"] for p in plist}
    assert not unused, f"{name}/{ver}: groups declared and empty: {unused}"


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_each_group_says_what_it_is_for_and_where_numbering_starts(case):
    name, ver, _ = case
    for gid, g in load(name, ver)["groups"].items():
        assert g["term"] == "Port", gid
        assert g["role"] in ROLES, gid
        assert g["role"] == "traffic", f"{name}/{ver}/{gid}: the ports carry the MIC's traffic"
        assert g["index-origin"] == 0, f"{name}/{ver}/{gid}: the book numbers ports from 0"
        assert (g.get("description") or "").strip(), gid


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_a_group_carries_only_what_the_book_prints(case):
    name, ver, family = case
    declared = load(name, ver)["groups"]
    wanted = FAMILIES[family][2]
    assert set(declared) == set(wanted)
    for gid, attrs in wanted.items():
        assert (declared[gid].get("attrs") or {}) == attrs, f"{name}/{ver}/{gid}"
    for g in declared.values():
        speed = (g.get("attrs") or {}).get("speed")
        assert speed in SPEEDS


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_a_port_keeps_the_media_it_stated_and_declares_no_speed_of_its_own(case):
    name, ver, family = case
    declared = load(name, ver)["groups"]
    for p in ports(load(name, ver)):
        attrs = p.get("attrs") or {}
        assert "speed" not in attrs, p["id"]
        assert attrs.get("media"), p["id"]
        assert attrs["media"] == declared[p["group"]]["attrs"]["media"], p["id"]


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_provenance_names_the_book_the_groups_come_from(case):
    name, ver, _ = case
    text = " ".join(str(load(name, ver)["provenance"]["groups"]).split())
    assert "Interface Module Reference" in text
    assert "role is traffic" in text

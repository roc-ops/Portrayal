"""The Juniper DWDM MIC, the MACsec 10GE MIC and six DPC cards put every port in a group of their own.

Each contract below declares `groups:` in the shape of a device group, and every port part joins
one with `group:`. A group's `attrs` carry a media, and a speed only where the MX Series Interface
Module Reference prints one for the port: 100 Gigabit for the DWDM MIC's one port, 'speeds up to
10 Gbps' for the SFP+ MIC and the XFP DPCs, 'speeds up to 1 Gbps' for the SFP DPCs, and 10, 100 or
1000 Mbps for the tri-rate DPC. The book numbers ports from 0 within each PIC. No port id, position
or part of any contract is renamed or moved.
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
    "mic3-100g-dwdm": (("mic3-100g-dwdm", "mic3-100g-dwdm-v"), 1,
                       {"cfp2-100g": {"media": "cfp2", "speed": "100g"}}),
    "mic-3d-10ge-sfp-e": (("mic-3d-10ge-sfp-e", "mic-3d-10ge-sfp-e-v"), 10,
                          {"sfp-plus-10g": {"media": "sfp-plus", "speed": "10g", "speeds": ["1g", "10g"]}}),
    "dpce-r-40ge-sfp": (("dpce-r-40ge-sfp",), 40, {"sfp-1g": {"media": "sfp", "speed": "1g"}}),
    "dpce-q-20ge-sfp": (("dpce-q-20ge-sfp",), 20, {"sfp-1g": {"media": "sfp", "speed": "1g"}}),
    "dpc-r-4xge-xfp": (("dpc-r-4xge-xfp",), 4, {"xfp-10g": {"media": "xfp", "speed": "10g"}}),
    "dpce-2xge-xfp": (("dpce-2xge-xfp",), 2, {"xfp-10g": {"media": "xfp", "speed": "10g"}}),
    "dpce-20ge-2xge": (("dpce-20ge-2xge",), 22,
                       {"sfp-1g": {"media": "sfp", "speed": "1g"},
                        "xfp-10g": {"media": "xfp", "speed": "10g"}}),
    "dpce-40ge-tx": (("dpce-40ge-tx",), 40,
                     {"rj45-1g": {"media": "rj45", "speed": "1g", "speeds": ["10m", "100m", "1g"]}}),
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


def test_the_families_cover_every_contract_of_the_eleven():
    assert len(CONTRACTS) == 11
    assert len({name for name, _, _ in CONTRACTS}) == 10


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_every_port_part_joins_a_declared_group(case):
    name, ver, family = case
    data = load(name, ver)
    declared = data.get("groups") or {}
    assert declared, f"{name}/{ver} declares no groups"
    plist = ports(data)
    assert len(plist) == FAMILIES[family][1]
    assert len(plist) == len(data["parts"]), f"{name}/{ver}: a part that is not a port"
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
        assert g["role"] == "traffic", f"{name}/{ver}/{gid}: the ports carry the card's traffic"
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
        attrs = g.get("attrs") or {}
        assert attrs.get("speed") in SPEEDS
        assert set(attrs.get("speeds") or []) <= set(SPEEDS)
        if attrs.get("speeds"):
            assert attrs["speed"] in attrs["speeds"]


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_a_port_keeps_the_media_it_stated_and_declares_no_speed_of_its_own(case):
    name, ver, family = case
    declared = load(name, ver)["groups"]
    for p in ports(load(name, ver)):
        attrs = p.get("attrs") or {}
        assert "speed" not in attrs, p["id"]
        if "media" in attrs:
            assert attrs["media"] == declared[p["group"]]["attrs"]["media"], p["id"]


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_provenance_names_the_book_the_groups_come_from(case):
    name, ver, _ = case
    text = " ".join(str(load(name, ver)["provenance"]["groups"]).split())
    assert "Interface Module Reference" in text
    assert "role is traffic" in text

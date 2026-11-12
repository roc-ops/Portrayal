"""Juniper's Ethernet and 10G-class MICs put every port in a group of their own.

Each contract below declares `groups:` in the shape of a device group, and every port part joins
one with `group:`. A group's `attrs` carry a media or a speed only where the Interface Module
Reference prints one for the port: 'speeds up to 1 Gbps' for the Gigabit SFP MICs, 'speeds up to
10 Gbps' for the XFP MICs, the tri-rate RJ-45 range for the 40-port MIC, and the two cages of the
MACsec Gigabit MIC that also run at 10 Gbps. The multi-rate MICs state no speed (a port's rate
depends on its carrier) and the OC192 MIC states none (the book prints a port name, not a rate).
No port id, position or part of any contract is renamed or moved.
"""
from pathlib import Path

import pytest
import yaml

COMP = Path(__file__).resolve().parents[2] / "library/components/juniper"

ROLES = {"traffic", "fabric", "management", "service", "indicator", "furniture"}
SPEEDS = yaml.safe_load((Path(__file__).resolve().parents[2] / "spec/schemas/speeds.yaml").read_text())["speeds"]

# family -> (the component names it covers, ports on one contract, {group: its attrs})
FAMILIES = {
    "20ge-sfp": (("mic-3d-20ge-sfp", "mic-3d-20ge-sfp-v"), 20,
                 {"sfp-1g": {"media": "sfp", "speed": "1g"}}),
    "2xge-xfp": (("mic-3d-2xge-xfp", "mic-3d-2xge-xfp-v"), 2,
                 {"xfp-10g": {"media": "xfp", "speed": "10g"}}),
    "4xge-xfp": (("mic-3d-4xge-xfp", "mic-3d-4xge-xfp-v"), 4,
                 {"xfp-10g": {"media": "xfp", "speed": "10g"}}),
    "40ge-tx": (("mic-3d-40ge-tx",), 40,
                {"rj45-1g": {"media": "rj45", "speed": "1g"}}),
    "1oc192-xfp": (("mic-3d-1oc192-xfp", "mic-3d-1oc192-xfp-v"), 1,
                   {"xfp": {"media": "xfp"}}),
    "macsec-20ge": (("mic-macsec-20ge", "mic-macsec-20ge-v"), 20,
                    {"sfp-1g": {"media": "sfp", "speed": "1g"},
                     "sfp-10g": {"media": "sfp", "speed": "10g", "speeds": ["1g", "10g"]}}),
    "mrate": (("mic-mrate", "mic-macsec-mrate"), 12,
              {"qsfp": {}}),
}
TEN_G = {"port-1-8", "port-1-9"}

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


def test_the_families_cover_every_contract_of_the_thirteen_names():
    assert len(CONTRACTS) == 22
    assert len({name for name, _, _ in CONTRACTS}) == 13


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
    name, ver, family = case
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
        for speed in [(g.get("attrs") or {}).get("speed"), *((g.get("attrs") or {}).get("speeds") or [])]:
            assert speed is None or speed in SPEEDS


@pytest.mark.parametrize("case", [c for c in CONTRACTS if c[2] == "macsec-20ge"], ids=ids)
def test_only_the_two_dual_rate_cages_of_the_macsec_mic_state_10g(case):
    name, ver, _ = case
    for p in ports(load(name, ver)):
        want = "sfp-10g" if p["id"] in TEN_G else "sfp-1g"
        assert p["group"] == want, f"{name}/{ver}/{p['id']}"


@pytest.mark.parametrize("case", [c for c in CONTRACTS if c[2] in ("mrate", "1oc192-xfp")], ids=ids)
def test_no_speed_is_stated_where_the_book_prints_none_for_the_port(case):
    name, ver, _ = case
    data = load(name, ver)
    for g in data["groups"].values():
        assert "speed" not in (g.get("attrs") or {})
    for p in ports(data):
        assert "speed" not in (p.get("attrs") or {}), p["id"]


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_provenance_names_the_book_the_groups_come_from(case):
    name, ver, _ = case
    text = " ".join(str(load(name, ver)["provenance"]["groups"]).split())
    assert "Interface Module Reference" in text
    assert "role is traffic" in text


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_a_port_keeps_the_media_it_stated_and_declares_no_speed_of_its_own(case):
    name, ver, family = case
    for p in ports(load(name, ver)):
        attrs = p.get("attrs") or {}
        assert "speed" not in attrs, p["id"]
        assert attrs.get("media"), p["id"]

"""The MX10000 line cards, the MX10003 line card and the Multi-Rate Ethernet MIC put their ports in groups.

Each contract below declares `groups:` in the shape of a device group, and every port part joins
one with `group:`. A group's `attrs` carry a media and a speed only where the hardware guide or the
module reference prints one for that port block: 'Each port supports a speed of 10 Gbps or 1 Gbps'
(MX10K-LC480), 'Each port is capable of supporting either 100 Gbps or 40 Gbps or 10 G'
(MX10K-LC2101), 'a maximum speed of 400 Gbps' (MX10K-LC9600), Table 15 of the MX10003 guide (PIC 0,
ports 0 to 5) and Table 40 of the module reference (JNP-MIC1, ports 0 to 11). The MX10003 line
card's GM/PTP jack is labelled in the guide's figure and nothing else is printed for it, so its
group states no media and no speed. No port id, position or part of any contract is renamed or
moved.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "library/components/juniper"

ROLES = {"traffic", "fabric", "management", "service", "indicator", "furniture", "stack-control"}
SPEEDS = yaml.safe_load((ROOT / "spec/schemas/speeds.yaml").read_text())["speeds"]

# component -> (parts, {group: (its role, its attrs)})
CARDS = {
    "jnp10k-lc480": (48, {"sfp-plus-10g": ("traffic", {"media": "sfp-plus", "speed": "10g",
                                                       "speeds": ["1g", "10g"]})}),
    "jnp10k-lc2101": (24, {"qsfp28-100g": ("traffic", {"media": "qsfp28", "speed": "100g",
                                                       "speeds": ["40g", "100g"]})}),
    "jnp10k-lc9600": (24, {"qsfp-dd-400g": ("traffic", {"media": "qsfp-dd", "speed": "400g"})}),
    "jnp10003-lc2103": (7, {"qsfp-plus-40g": ("traffic", {"media": "qsfp-plus", "speed": "40g"}),
                            "timing": ("management", {})}),
    "jnp-mic1": (12, {"qsfp28-100g": ("traffic", {"media": "qsfp28", "speed": "100g",
                                                  "speeds": ["40g", "100g"]})}),
}

CONTRACTS = sorted(
    (name, path.parent.name)
    for name in CARDS
    for path in (COMP / name).glob("v*/contract.yaml")
)


def load(name, ver):
    return yaml.safe_load((COMP / name / ver / "contract.yaml").read_text())


def ids(case):
    return f"{case[0]}/{case[1]}"


def test_the_cards_cover_every_live_contract_of_the_five():
    assert len(CONTRACTS) == 5
    assert {name for name, _ in CONTRACTS} == set(CARDS)


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_every_port_part_joins_a_declared_group(case):
    name, ver = case
    data = load(name, ver)
    declared = data.get("groups") or {}
    assert declared, f"{name}/{ver} declares no groups"
    assert len(data["parts"]) == CARDS[name][0]
    loose = [p["id"] for p in data["parts"] if not p.get("group")]
    assert not loose, f"{name}/{ver}: parts in no group: {loose}"
    unknown = {p["group"] for p in data["parts"]} - set(declared)
    assert not unknown, f"{name}/{ver}: groups used and not declared: {unknown}"
    unused = set(declared) - {p["group"] for p in data["parts"]}
    assert not unused, f"{name}/{ver}: groups declared and empty: {unused}"


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_each_group_says_what_it_is_for_and_where_numbering_starts(case):
    name, ver = case
    for gid, g in load(name, ver)["groups"].items():
        assert g["term"] == "Port", gid
        assert g["role"] in ROLES, gid
        assert g["role"] == CARDS[name][1][gid][0], f"{name}/{ver}/{gid}"
        assert g["index-origin"] == 0, f"{name}/{ver}/{gid}: the ports are numbered from 0"
        assert (g.get("description") or "").strip(), gid


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_a_group_carries_only_what_the_page_prints(case):
    name, ver = case
    declared = load(name, ver)["groups"]
    wanted = CARDS[name][1]
    assert set(declared) == set(wanted)
    for gid, (_, attrs) in wanted.items():
        assert (declared[gid].get("attrs") or {}) == attrs, f"{name}/{ver}/{gid}"
    for g in declared.values():
        attrs = g.get("attrs") or {}
        if "speed" in attrs:
            assert attrs["speed"] in SPEEDS
        assert set(attrs.get("speeds") or []) <= set(SPEEDS)
        if attrs.get("speeds"):
            assert attrs["speed"] in attrs["speeds"]


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_a_port_keeps_the_media_it_stated_and_declares_no_speed_of_its_own(case):
    name, ver = case
    data = load(name, ver)
    for p in data["parts"]:
        attrs = p.get("attrs") or {}
        assert "speed" not in attrs, p["id"]
        group_media = (data["groups"][p["group"]].get("attrs") or {}).get("media")
        if "media" in attrs:
            assert attrs["media"] == group_media, p["id"]


@pytest.mark.parametrize("case", CONTRACTS, ids=ids)
def test_provenance_names_the_source_of_the_groups(case):
    name, ver = case
    text = " ".join(str(load(name, ver)["provenance"]["groups"]).split())
    assert "Hardware Guide" in text or "Interface Module Reference" in text
    assert "role is traffic" in text


def test_the_timing_jack_of_the_mx10003_line_card_is_a_group_of_its_own_with_no_rate():
    data = load("jnp10003-lc2103", "v1")
    jack = [p for p in data["parts"] if p["id"] == "gm-ptp"]
    assert [p["group"] for p in jack] == ["timing"]
    assert "attrs" not in data["groups"]["timing"]
    assert "GM/PTP" in " ".join(str(data["provenance"]["groups"]).split())

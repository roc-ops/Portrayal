"""Juniper MX line cards state their port counts and rates (the cards that drew ports and said none).

A downstream reader counts a card's ports only from the integer attrs whose key is the cage
media; the rate rides in `provenance`, quoting the vendor's own words. Each card below states
its counts, the counts add up to the ports the contract places, and each count key carries a
`provenance` entry that quotes the source.

Where a source gives a rate to some ports only, the count is split along the ports it names and
those placements say so in `media`. Where the rate depends on the carrier, the count is the key
every port always runs.
"""
import re
from pathlib import Path

import pytest
import yaml

COMP = Path(__file__).resolve().parents[2] / "library/components/juniper"

# The integer keys a downstream reader counts ports from, plus the two this change adds.
PORT_KEYS = {
    "ports", "sfp", "sfp-plus", "sfp28", "qsfp", "qsfp-plus", "qsfp28", "qsfp-dd", "cfp",
    "cfp2", "cpak", "xfp", "xfp-10g", "oc3", "oc12", "oc48", "oc192", "cxp", "rj45",
}
# Integer attrs that are not port counts.
NOT_COUNTS = ("power-draw", "forwarding", "weight")

CAGE_WORDS = ("sfp", "cfp", "cxp", "xfp", "rj45", "smb")

SPLIT_100G_CARRIER = "MIC-MRATE/MACSEC: 100G on ports 0-3 and 6-9 in an MPC9E, on 4 in an MPC8E"

# name, version dir, counts, {provenance key: [quoted words]}
CARDS = [
    ("mpc7e-mrate", "v2", {"qsfp28": 4, "qsfp": 8}, {
        "qsfp28-rate": ["Port numbers 0/2, 0/5, 1/2 and 1/5 are the four 100-Gigabit Ethernet ports"],
        "qsfp-rate": ["Twelve Gigabit Ethernet ports that can be configured as 40-Gigabit Ethernet "
                      "port or as four 10-Gigabit Ethernet ports using a breakout cable"]}),
    ("mpc7e-10g", "v2", {"sfp-plus": 40}, {
        "sfp-plus-rate": ["Forty 10-Gigabit Ethernet ports. The ports support SFP+ transceivers. "
                          "Each port supports 10 Gbps or 1 Gbps speed."]}),
    ("mpc10e-15c-mrate", "v2", {"qsfp28": 12, "qsfp-dd": 3}, {
        "qsfp28-rate": ["QSFP28 ports-Port numbers 0/0 through 0/3, 1/0 through 1/3, and 2/0 through 2/3"],
        "qsfp-dd-rate": ["QSFP56-DD ports-Port numbers 0/4, 1/4, and 2/4"],
        "drawing-note": ["QSFP56-DD", "QSFP28"]}),
    ("mpc10e-10c-mrate", "v2", {"qsfp28": 8, "qsfp-dd": 2}, {
        "qsfp28-rate": ["QSFP28 ports-Port numbers 0/0 through 0/3, and 1/0 through 1/3"],
        "qsfp-dd-rate": ["QSFP56-DD ports-Port numbers 0/4, and 1/4"],
        "drawing-note": ["QSFP56-DD", "QSFP28"]}),
    ("mpc5e-40g10g", "v2", {"qsfp": 6, "sfp-plus": 24}, {
        "qsfp-rate": ["six 40-Gigabit Ethernet ports and twenty-four 10-Gigabit Ethernet ports"],
        "sfp-plus-rate": ["six 40-Gigabit Ethernet ports and twenty-four 10-Gigabit Ethernet ports"]}),
    ("mpc5e-100g10g", "v2", {"cfp2": 2, "sfp-plus": 4}, {
        "cfp2-rate": ["two 100-Gigabit Ethernet ports and four 10-Gigabit Ethernet ports"],
        "sfp-plus-rate": ["two 100-Gigabit Ethernet ports and four 10-Gigabit Ethernet ports"]}),
    ("mpc4e-3d-32xge-sfpp", "v2", {"sfp-plus": 32}, {
        "sfp-plus-rate": ["thirty-two 10-Gigabit Ethernet ports"]}),
    ("mpc4e-3d-2cge-8xge", "v2", {"cfp": 2, "sfp-plus": 8}, {
        "cfp-rate": ["two 100-Gigabit Ethernet ports and eight 10-Gigabit Ethernet ports"],
        "sfp-plus-rate": ["two 100-Gigabit Ethernet ports and eight 10-Gigabit Ethernet ports"]}),
    ("mpc-3d-16xge-sfpp", "v2", {"sfp-plus": 16}, {
        "sfp-plus-rate": ["sixteen 10-Gigabit Ethernet ports"]}),
    ("mic3-3d-10xge-sfpp", "v2", {"sfp-plus": 10}, {
        "sfp-plus-rate": ["Supports 10 SFP+ pluggable optic ports"]}),
    ("mic3-3d-1x100ge-cfp", "v2", {"cfp": 1}, {
        "cfp-rate": ["One 100-Gigabit Ethernet port"]}),
    ("mic3-3d-1x100ge-cxp", "v2", {"cxp": 1}, {
        "cxp-rate": ["One 100-gigabit Ethernet port"]}),
    ("jnp10k-lc2101", "v1", {"qsfp28": 24}, {
        "qsfp28-rate": ["can support 24 100-Gigabit Ethernet ports",
                        "All the ports are Multi-Rate ports. Each port is capable of supporting either "
                        "100 Gbps or 40 Gbps or 10 G"]}),
    ("jnp10k-lc480", "v1", {"sfp-plus": 48}, {
        "sfp-plus-rate": ["48 SFP/SFP+ ports. Each port supports a speed of 10 Gbps or 1 Gbps"]}),
    ("jnp10k-lc9600", "v1", {"qsfp-dd": 24}, {
        "qsfp-dd-rate": ["twenty-four QSFP-DD ports, each capable of supporting a maximum speed of 400 Gbps"]}),
    ("jnp-mic1", "v1", {"qsfp28": 12}, {
        "qsfp28-rate": ["Twelve 100-Gigabit Ethernet ports that support quad small form-factor "
                        "pluggable (QSFP28) transceivers"]}),
    ("mx304-lmic16", "v1", {"qsfp-dd": 16}, {
        "qsfp-dd-rate": ["16X100GbE. 4x400GbE on ports 0, 6, 8, and 14"]}),
    ("mx2k-mpc11e-v2k", "v1", {"qsfp28": 40}, {
        "qsfp28-rate": ["has 40 rate-selectable (multi-rate) ports that support quad small formfactor "
                        "pluggable plus (QSFP28) transceivers", "400-Gbps"]}),
    ("mic6-10g", "v1", {"sfp-plus": 24}, {
        "sfp-plus-rate": ["Supports 24 SFP+ pluggable optic ports"]}),
    ("mic6-100g-cfp2", "v1", {"cfp2": 2}, {
        "cfp2-rate": ["Two 100-Gigabit Ethernet CFP2 ports"]}),
    ("mic6-100g-cxp", "v1", {"cxp": 4}, {
        "cxp-rate": ["Four 100-Gigabit Ethernet ports", "Supports 100GBASE-SR10 over CXP pluggable optics"]}),
    ("mic-mrate", "v1", {"qsfp": 12}, {
        "qsfp-rate": ["Twelve Gigabit Ethernet ports that support quad small form-factor pluggable plus "
                      "(QSFP+) transceivers",
                      "Port numbers 0 through 3, and 6 through 9 are the eight 100-Gigabit Ethernet ports",
                      "4 ports out of the total 12 support 100-Gigabit Ethernet speed"]}),
    ("mic-macsec-mrate", "v1", {"qsfp": 12}, {
        "qsfp-rate": ["Twelve Gigabit Ethernet QSFP+ ports",
                      "Port numbers 0 through 3, and 6 through 9 are the eight 100-Gigabit Ethernet ports",
                      "Four ports out of the total twelve ports support 100-Gigabit Ethernet speed"]}),
    ("dpce-40ge-tx", "v2", {"rj45": 40}, {
        "rj45-rate": ["40 autonegotiating 10BASE-T, 100BASE-TX, or 1000BASE-T Megabit Ethernet ports"]}),
    ("mic-3d-16che1-t1-ce", "v2", {"ports": 16}, {
        "ports-count": ["Sixteen E1 or T1 ports"]}),
    ("mic-3d-8ds3-e3", "v2", {"ports": 8}, {
        "ports-count": ["Eight E3 or DS3 ports", "Tx0 through Tx7 and Rx0 through Rx7"]}),
]
BY_NAME = {c[0]: c for c in CARDS}

# Cards whose placed jacks are not their ports, with the reason.
SUM_EXEMPT = {
    "mic-3d-8ds3-e3": "eight ports, each drawn as a Tx and an Rx SMB jack: 16 placements",
}

# Placements whose media is set by a named-port rate.
MEDIA = {
    "mpc7e-mrate": {
        "port-0-2": "qsfp28", "port-0-5": "qsfp28", "port-1-2": "qsfp28", "port-1-5": "qsfp28",
        "port-0-0": "qsfp-plus", "port-0-1": "qsfp-plus", "port-0-3": "qsfp-plus",
        "port-0-4": "qsfp-plus", "port-1-0": "qsfp-plus", "port-1-1": "qsfp-plus",
        "port-1-3": "qsfp-plus", "port-1-4": "qsfp-plus"},
    "mpc10e-15c-mrate": {"port-0-4": "qsfp-dd", "port-1-4": "qsfp-dd", "port-2-4": "qsfp-dd",
                         "port-0-0": "qsfp28", "port-2-3": "qsfp28"},
    "mpc10e-10c-mrate": {"port-0-4": "qsfp-dd", "port-1-4": "qsfp-dd",
                         "port-0-0": "qsfp28", "port-1-3": "qsfp28"},
}


def contract(name):
    _, v, _, _ = BY_NAME[name]
    return yaml.safe_load((COMP / name / v / "contract.yaml").read_text())


def squash(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def placed_cages(c):
    return [p for p in c["parts"] if any(w in p["ref"] for w in CAGE_WORDS)]


names = [c[0] for c in CARDS]


@pytest.mark.parametrize("name", names)
def test_card_states_its_port_counts(name):
    c = contract(name)
    want = BY_NAME[name][2]
    got = {k: v for k, v in c["attrs"].items() if k in PORT_KEYS}
    assert got == want


@pytest.mark.parametrize("name", names)
def test_counts_add_up_to_the_ports_the_contract_places(name):
    c = contract(name)
    total = sum(BY_NAME[name][2].values())
    if name in SUM_EXEMPT:
        # the drawing places a jack per signal, and the source says so
        assert len(placed_cages(c)) == 2 * total, SUM_EXEMPT[name]
    else:
        assert len(placed_cages(c)) == total


@pytest.mark.parametrize("name", names)
def test_each_rate_quotes_its_source(name):
    prov = contract(name).get("provenance") or {}
    for key, quotes in BY_NAME[name][3].items():
        assert key in prov, f"{name}: no provenance entry {key}"
        text = squash(prov[key])
        for q in quotes:
            assert squash(q) in text, f"{name}: {key} does not quote {q!r}"


@pytest.mark.parametrize("name", sorted(MEDIA))
def test_named_ports_place_the_media_the_source_names(name):
    parts = {p["id"]: p for p in contract(name)["parts"]}
    for pid, media in MEDIA[name].items():
        assert parts[pid]["attrs"]["media"] == media, f"{name} {pid}"
    counts = BY_NAME[name][2]
    by_media = {}
    for p in placed_cages(contract(name)):
        m = p["attrs"]["media"]
        by_media[m] = by_media.get(m, 0) + 1
    # qsfp-plus is counted under `qsfp`; every other media under its own key
    assert {("qsfp" if m == "qsfp-plus" else m): n for m, n in by_media.items()} == counts


def test_carrier_dependent_cards_count_the_rate_every_port_always_runs():
    for name in ("mic-mrate", "mic-macsec-mrate"):
        c = contract(name)
        assert c["attrs"]["qsfp"] == 12
        assert "qsfp28" not in c["attrs"]


def test_the_drawing_notes_say_the_drawing_is_left():
    for name in ("mpc10e-10c-mrate", "mpc10e-15c-mrate"):
        note = squash(contract(name)["provenance"]["drawing-note"])
        assert "drawn" in note and "later" in note


def test_the_lc2103_is_left_as_it_was():
    c = yaml.safe_load((COMP / "jnp10003-lc2103/v1/contract.yaml").read_text())
    assert c["attrs"]["qsfp"] == 6 and c["version"] == "1.3.1"


def test_no_card_states_a_count_key_outside_the_libraries_port_keys():
    for name in names:
        for k, v in contract(name)["attrs"].items():
            if isinstance(v, int) and not isinstance(v, bool) and not k.startswith(NOT_COUNTS):
                assert k in PORT_KEYS, f"{name}: {k}"

"""Every port on a Smartoptics card belongs to a group that states its media.

A card's ports used to carry no group, so a port on a module seated in a bay
could not say what it was for or what rate it ran at. These are the cards of
the vendor whose contracts compose a port part: each declares `groups:` and
every port part joins one.

A group states a `speed` only where a held Smartoptics document prints one:

  - DCP-404: the manual says the client side supports 4x100GBE on QSFP28 and
    the card has one 400G line (s2.2.4, page 15);
  - DCP-F-A22: the datasheet lists RJ45 management ports as 10/100/1000
    Base-T and SFP management ports as 1000 Base-X (page 2), so 1g.

The passive plug-in modules, and the amplifier's EDFA and monitor ports, are
duplex LC fibre ports for which the documents give wavelengths and losses and
no data rate. Their groups state `media: fiber` and no `speed`; a rate is
never taken from the connector.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import lint

LIB = Path(__file__).resolve().parents[2] / "library"
COMPONENTS = LIB / "components" / "smartoptics"

PPM = ["ppm-ad1-1510", "ppm-ad1-1625", "ppm-dcm-10", "ppm-dcm-20", "ppm-dcm-40",
       "ppm-dcm-80", "ppm-ocu-50-50", "ppm-ocu-97-3"]

# component -> (major, {group: (media, speed or None)})
EXPECTED = {
    "dcp-1203": (1, {"qsfpdd-400g": ("qsfp-dd", "400g")}),
    "dcp-404": (1, {"client-100g": ("qsfp28", "100g"),
                    "line-400g": ("qsfp-dd", "400g")}),
    "dcp-f-a22": (2, {"mgmt-rj45": ("rj45", "1g"), "mgmt-sfp": ("sfp", "1g"),
                      "edfa": ("fiber", None), "monitor": ("fiber", None)}),
    **{name: (2, {"lc-optical": ("fiber", None)}) for name in PPM},
}

# every part ref whose contract is `class: port`, as a Smartoptics card composes it
PORT_REFS = {"std/qsfp-dd@1", "std/qsfp-ganged@1", "std/sfp@1",
             "common/rj45-eth@1", "common/lc-duplex-adapter@6"}


def _contract(name):
    major = EXPECTED[name][0]
    return yaml.safe_load((COMPONENTS / name / f"v{major}" / "contract.yaml").read_text())


def _ports(data):
    return [p for p in data.get("parts") or [] if p.get("ref") in PORT_REFS]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_port_part_joins_a_declared_group(name):
    data = _contract(name)
    groups = data.get("groups") or {}
    ports = _ports(data)
    assert ports, f"{name} composes no port part"
    assert groups, f"{name} declares no groups"
    for p in ports:
        assert p.get("group") in groups, f"{name}: port {p['id']} is in no declared group"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_group_states_the_media_and_speed_the_sources_give(name):
    data = _contract(name)
    groups = data.get("groups") or {}
    expected = EXPECTED[name][1]
    assert set(groups) == set(expected)
    for gname, (media, speed) in expected.items():
        attrs = groups[gname].get("attrs") or {}
        assert attrs.get("media") == media, f"{name}/{gname} media"
        # a rate no held document states is left out, never taken from the cage
        assert attrs.get("speed") == speed, f"{name}/{gname} speed"
        assert groups[gname].get("role"), f"{name}/{gname} has no role"
        assert groups[gname].get("term") == "Port"
        assert groups[gname].get("index-origin") == 1


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_no_group_is_empty(name):
    data = _contract(name)
    used = {p.get("group") for p in _ports(data)}
    assert set(data.get("groups") or {}) <= used


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_lint_finds_nothing_to_say_about_the_groups(name):
    data = _contract(name)
    with lint.collecting() as got:
        lint.lint_component_groups(f"components/smartoptics/{name}", data, [LIB])
    assert not got.errors and not got.warnings, (got.errors, got.warnings)


def test_passive_ports_state_no_rate():
    for name in PPM:
        for p in _ports(_contract(name)):
            assert "speed" not in (p.get("attrs") or {}), f"{name}/{p['id']}"


def test_the_dcp_404_ports_keep_their_ids_and_split_client_from_line():
    data = _contract("dcp-404")
    by_group = {}
    for p in _ports(data):
        by_group.setdefault(p["group"], []).append(p["id"])
    assert by_group == {"client-100g": ["c1", "c2", "c3", "c4"], "line-400g": ["line"]}

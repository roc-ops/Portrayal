"""The eight DPC and DPCE model numbers that Table 93 of the MX240 hardware guide groups with a DPC
the library already draws, or that make a card of their own.

Four numbers share a part with a sibling that prints the same watts and the same ports (model-variants);
four make two new parts of their own: the queuing 40-port SFP card (365 W) and the queuing 4-port XFP
card (330 W). Every slot of the MX240, MX480 and MX960 that takes the 40-port DPCE-R card takes the two
new cards.
"""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "library" / "components" / "juniper"
DEV = ROOT / "library" / "devices" / "juniper"

CHASSIS = ["mx240", "mx480", "mx960"]


def _contract(name, version):
    return yaml.safe_load((COMP / name / f"v{version}" / "contract.yaml").read_text())


def _variants(attrs):
    return {v.strip() for v in str(attrs.get("model-variants", "")).split(",") if v.strip()}


# part, version, model, variants, watts, ports
SHARED = [
    ("dpce-r-40ge-sfp", 2, "DPCE-R-40GE-SFP", {"DPC-R-40GE-SFP", "DPCE-X-40GE-SFP"}, 335, ("sfp-1g", 40)),
    ("dpc-r-4xge-xfp", 3, "DPC-R-4XGE-XFP", {"DPCE-R-4XGE-XFP", "DPCE-X-4XGE-XFP"}, 310, ("xfp-10g", 4)),
]
NEW = [
    ("dpce-q-40ge-sfp", "DPCE-R-Q-40GE-SFP", {"DPCE-X-Q-40GE-SFP"}, 365, ("sfp-1g", 40)),
    ("dpce-q-4xge-xfp", "DPCE-R-Q-4XGE-XFP", {"DPCE-X-Q-4XGE-XFP"}, 330, ("xfp-10g", 4)),
]


def _ports(contract, group):
    return [p for p in contract["parts"] if p.get("group") == group]


@pytest.mark.parametrize("name,version,model,variants,watts,ports", SHARED)
def test_a_variant_shares_the_part_with_the_same_watts_and_ports(name, version, model, variants, watts, ports):
    c = _contract(name, version)
    assert c["attrs"]["model"] == model
    assert _variants(c["attrs"]) == variants
    assert c["attrs"]["power-draw-max-w"] == watts
    group, count = ports
    assert len(_ports(c, group)) == count


@pytest.mark.parametrize("name,model,variants,watts,ports", NEW)
def test_a_new_card_carries_its_own_row_of_table_93(name, model, variants, watts, ports):
    c = _contract(name, 1)
    assert c["kind"] == "module"
    assert c["attrs"]["model"] == model
    assert _variants(c["attrs"]) == variants
    assert c["attrs"]["power-draw-max-w"] == watts
    group, count = ports
    assert len(_ports(c, group)) == count
    assert c["size"] == {"w": 413.5, "h": 29.5}


@pytest.mark.parametrize("name,model,variants,watts,ports", NEW)
def test_no_maker_number_names_two_parts(name, model, variants, watts, ports):
    numbers = {model} | variants
    for other in sorted(COMP.glob("*/v*/contract.yaml")):
        if other.parent.parent.name == name:
            continue
        a = yaml.safe_load(other.read_text()).get("attrs") or {}
        assert not ({a.get("model")} | _variants(a)) & numbers, other


def _accepts_lists(node):
    """Every `accepts` list in a loaded device, wherever it sits."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "accepts" and isinstance(value, list):
                yield value
            else:
                yield from _accepts_lists(value)
    elif isinstance(node, list):
        for value in node:
            yield from _accepts_lists(value)


@pytest.mark.parametrize("chassis", CHASSIS)
def test_every_slot_of_the_sibling_takes_the_new_cards(chassis):
    doc = yaml.safe_load((DEV / chassis / "device.yaml").read_text())
    sibling = "juniper/dpce-r-40ge-sfp@2"
    lists = [a for a in _accepts_lists(doc) if sibling in a]
    assert lists
    for accepts in lists:
        assert "juniper/dpce-q-40ge-sfp@1" in accepts
        assert "juniper/dpce-q-4xge-xfp@1" in accepts

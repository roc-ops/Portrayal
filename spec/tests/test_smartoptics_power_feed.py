"""The Smartoptics DCP-2 and DCP-M32 shelves say what feeds each build.

Both are sold with the supplies as separate options: the data sheets list
DCP-2-PSU-AC-FB and DCP-2-PSU-DC-FB beside the shelf, and the user manual
gives each its input (100-127 VAC and 200-240 VAC, -40 to -72 VDC). A tool
filtering by feed otherwise reads the build's name.

The DCP-2 offers an all-AC and an all-DC build; the DCP-M32 is one build whose
two bays take either supply, mixed or alike. These pin the feed each states, that
the lint finds nothing wrong with it, and that the supplies a build seats are
the ones its feed names.
"""
from pathlib import Path

import yaml

from portrayal import lint
from portrayal.manifest import config_power, device_options

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/smartoptics"


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def findings(doc, code):
    with lint.collecting() as found:
        lint.lint_device_power_stated("device.yaml", doc)
    return [m for m in found.errors + found.warnings if f"[{code}]" in m]


def test_the_dcp_2_states_one_feed_for_each_build_it_sells():
    dev = load("dcp-2")
    cfgs = dev["configurations"]
    assert config_power(dev, cfgs["ac-f2b"]) == ["ac"]
    assert config_power(dev, cfgs["dc-f2b"]) == ["dc"]
    assert device_options(dev)["power"] == ["ac", "dc"]


def test_the_dcp_2_builds_seat_the_supply_their_feed_names():
    dev = load("dcp-2")
    cfgs = dev["configurations"]
    assert cfgs["dc-f2b"]["bays"] == {"psu-1": "smartoptics/dcp-2-psu-dc@1",
                                      "psu-2": "smartoptics/dcp-2-psu-dc@1"}
    seated = lint._seated_supplies(dev, cfgs["ac-f2b"])
    assert {lint._supply_feed(r) for r in seated.values()} == {"ac"}
    seated = lint._seated_supplies(dev, cfgs["dc-f2b"])
    assert {lint._supply_feed(r) for r in seated.values()} == {"dc"}


def test_the_dcp_m32_takes_an_ac_or_a_dc_supply_in_either_bay():
    dev = load("dcp-m32-cso-zr")
    assert config_power(dev, {}) == ["ac", "dc"]
    bays = {b["id"]: b["accepts"]
            for b in dev["views"]["rear"]["components"]["bays"]
            if b["id"].startswith("psu-")}
    assert set(bays) == {"psu-1", "psu-2"}
    for accepts in bays.values():
        assert {lint._supply_feed(r) for r in accepts} == {"ac", "dc"}


def test_no_feed_is_unstated_or_contradicted_on_either_shelf():
    for name in ("dcp-2", "dcp-m32-cso-zr"):
        dev = load(name)
        assert not findings(dev, "L119"), name
        assert not findings(dev, "L120"), name

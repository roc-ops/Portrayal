"""The EX4400 spare chassis says what feeds it (#513).

Seven EX4400 switches offer a spare chassis (`s`, the -S model) that ships with no power
supply and no fan module, so its build seats nothing a feed can be read from, and each stated
no `power` on it. A tool filtering by feed found every other build of the switch and not the
spare. The spare now states the feeds the hardware guide prints for it, the way
`test_config_power.py` pins the field: a list only where the guide prints both inputs.

  - EX4400-24P-S, 24MP-S, 48P-S, 48MP-S: the guide lists the 2000 W DC supply for the spare
    ("Additional spare models" in the model overview and the DC power supply ratings table)
    and the 1600 W AC supply in the AC ratings table, so the build lists `ac` and `dc`.
  - EX4400-24T-S, 48T-S: "supports 550-W AC or DC power supplies" in the model's own section.
  - EX4400-48F-S: the same sentence for the model, and the -S takes the 550 W variable DC
    supply as well.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import lint
from portrayal.manifest import OFFERED_KINDS, config_power

LIB = Path(__file__).resolve().parents[2] / "library"
BASELINE = LIB / "lint-baseline.json"

# model -> the feeds its spare build resolves to
SPARE = {
    "ex4400-24mp": ["ac", "dc"],
    "ex4400-24p": ["ac", "dc"],
    "ex4400-24t": ["ac", "dc"],
    "ex4400-48f": ["ac", "dc"],
    "ex4400-48mp": ["ac", "dc"],
    "ex4400-48p": ["ac", "dc"],
    "ex4400-48t": ["ac", "dc"],
}
SUPPLY_BAYS = ("psu-0", "psu-1")


def device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def findings(fn, doc, code):
    with lint.collecting() as found:
        fn("device.yaml", doc)
    return [m for m in found.errors + found.warnings if f"[{code}]" in m]


@pytest.mark.parametrize("name", sorted(SPARE))
def test_the_spare_resolves_the_feeds_the_guide_prints_for_it(name):
    d = device(name)
    assert config_power(d, d["configurations"]["s"]) == SPARE[name]


@pytest.mark.parametrize("name", sorted(SPARE))
def test_the_spare_still_ships_with_no_supply(name):
    # the feed is read from the guide, not from a supply the build seats
    bays = device(name)["configurations"]["s"]["bays"]
    assert all(bays.get(b) == "" for b in SUPPLY_BAYS), bays


@pytest.mark.parametrize("name", sorted(SPARE))
def test_every_offered_build_resolves_a_feed(name):
    d = device(name)
    offered = [n for n, c in d["configurations"].items() if (c or {}).get("kind") in OFFERED_KINDS]
    assert "s" in offered
    assert all(config_power(d, d["configurations"][n]) for n in offered)
    assert not findings(lint.lint_device_power_stated, d, "L119")


@pytest.mark.parametrize("name", sorted(SPARE))
def test_the_feeds_are_stated_once_and_agree_with_the_seated_supplies(name):
    d = device(name)
    assert not findings(lint.lint_device_power_home, d, "L118")
    assert not findings(lint.lint_device_power_stated, d, "L120")


def test_the_baseline_no_longer_carries_the_missing_feed_for_these_devices():
    base = json.loads(BASELINE.read_text())
    still = [n for n in SPARE if "L119" in base.get(f"devices/juniper/{n}/device.yaml", {})]
    assert not still, still

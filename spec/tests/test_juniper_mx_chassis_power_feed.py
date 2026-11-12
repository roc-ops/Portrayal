"""The MX240, MX480 and MX960 say what feeds each build (#513).

These three chassis seated supplies and stated no feed, so a tool filtering by feed could only read
a build's name, and the `base` build has none. Each now states `power` the way
`test_config_power.py` pins the field: on the chassis for the build most of them take, and on a
configuration only where its build differs. The value comes from the supply the build seats and the
input table the hardware guide prints for that supply:

  - MX240: the normal-capacity AC supply takes 100 to 240 VAC (Juniper MX240 Universal Routing
    Platform Hardware Guide, AC Power Supply Electrical Specifications) and the DC supply -40.5 to
    -72 VDC (Power Supply Electrical Specifications). The chassis seats the DC supply unless a
    configuration says otherwise, so its `base` and `dc` builds take the DC feed and `ac` the AC one.
  - MX480: the same AC and DC supplies, the same two tables in its own guide. The chassis seats the
    AC supply, so `base` and `ac` take the AC feed and `dc` the DC one.
  - MX960: the AC supply takes 200 to 240 VAC (AC Power Supply Electrical Specifications). The
    chassis seats it in all four bays and the device offers no other supply, so every build takes
    the AC feed. The high-voltage universal supply the guide describes separately takes AC or DC
    and is not a part of this library.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import lint
from portrayal.manifest import config_power

LIB = Path(__file__).resolve().parents[2] / "library"
BASELINE = LIB / "lint-baseline.json"

AC, DC = ["ac"], ["dc"]

# device -> configuration -> the feed its build resolves to
FEEDS = {
    "mx240": {"base": DC, "dc": DC, "ac": AC},
    "mx480": {"base": AC, "ac": AC, "dc": DC},
    "mx960": {"base": AC, "ac": AC},
}
# the feed the chassis states, which the builds that take it do not restate (L118)
CHASSIS = {"mx240": DC, "mx480": AC, "mx960": AC}


def device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def findings(fn, doc, code):
    with lint.collecting() as found:
        fn("device.yaml", doc)
    return [m for m in found.errors + found.warnings if f"[{code}]" in m]


@pytest.mark.parametrize("name", sorted(FEEDS))
def test_each_build_resolves_the_feed_its_supplies_take(name):
    d = device(name)
    cfgs = d["configurations"]
    assert sorted(cfgs) == sorted(FEEDS[name]), "a configuration was added or removed: say what feeds it"
    for cfg, want in FEEDS[name].items():
        assert config_power(d, cfgs[cfg]) == want, f"{name}:{cfg}"


@pytest.mark.parametrize("name", sorted(FEEDS))
def test_the_chassis_states_the_feed_and_no_build_restates_it(name):
    d = device(name)
    assert config_power(d, {}) == CHASSIS[name]
    assert not [n for n, c in d["configurations"].items()
                if config_power({}, c) == CHASSIS[name]], "a build restates the chassis feed"


@pytest.mark.parametrize("name", sorted(FEEDS))
def test_the_feeds_are_stated_once_and_agree_with_the_seated_supplies(name):
    d = device(name)
    for code, fn in (("L118", lint.lint_device_power_home), ("L119", lint.lint_device_power_stated),
                     ("L120", lint.lint_device_power_stated)):
        assert not findings(fn, d, code), (name, code)


@pytest.mark.parametrize("name", sorted(FEEDS))
def test_a_build_seating_a_dc_supply_is_not_called_ac(name):
    """The supplies each build seats, read the way L120 reads them: the feed in the part's
    own name must be one of the build's feeds."""
    d = device(name)
    for cfg, c in d["configurations"].items():
        feeds = set(config_power(d, c))
        seated = lint._seated_supplies(d, c)
        assert seated, f"{name}:{cfg} seats no supply"
        for bay, ref in seated.items():
            named = lint._supply_feed(ref)
            assert named is None or named in feeds, f"{name}:{cfg} {bay} {ref}"


def test_the_baseline_no_longer_carries_the_missing_feed_for_these_devices():
    base = json.loads(BASELINE.read_text())
    still = [n for n in FEEDS if "L119" in base.get(f"devices/juniper/{n}/device.yaml", {})]
    assert not still, still

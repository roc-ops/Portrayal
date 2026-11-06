"""The MX routers say what feeds each build (#513).

Eight Juniper MX devices seated supplies and stated no feed, so a tool filtering by feed could
only read the build's name, and a build called `base` has none. Each now states `power` the way
`test_config_power.py` pins the field: on the chassis where every build takes one feed, and on a
configuration only where its build differs. The value comes from the supply the build seats and
the hardware guide's input table for that supply:

  - MX80, MX5/10/40: the AC supply takes 90 to 264 VAC (AC Power Supply Electrical Specifications).
  - MX104: the supply it seats takes 24, -48 or -60 VDC (DC Power Electrical Specifications).
  - MX204: the AC supply takes 100 to 127 and 200 to 240 VAC, the DC supply -40 to -72 VDC.
  - MX304: AC 90 to 264 VAC; DC -40 to -72 VDC; the HVAC/DC supply takes 200 to 277 VAC or
    240 to 380 VDC, so that build lists both feeds.
  - MX10003: the AC supply takes 90 to 140 and 180 to 264 VAC.
  - MX10004, MX10008, MX10016: JNP10K-PWR-AC2 takes 180 to 305 VAC or 190 to 410 VDC ("supports
    AC, HVAC, and HVDC"), so those builds list both, as the COR580's AC build does for its supply.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import lint
from portrayal.manifest import OFFERED_KINDS, config_power

LIB = Path(__file__).resolve().parents[2] / "library"
BASELINE = LIB / "lint-baseline.json"

AC, DC, AC_HVDC = ["ac"], ["dc"], ["ac", "hvdc"]

# device -> configuration -> the feed its build resolves to
FEEDS = {
    "mx80": {"base": AC, "mx80": AC, "mx40": AC, "mx10": AC, "mx5": AC},
    "mx104": {"base": DC},
    "mx204": {"ac": AC, "dc": DC},
    "mx304": {"base": AC, "dual-re-ac": AC, "one-re-3lmic-ac": AC, "dc": DC, "hvac-dc": AC_HVDC},
    "mx10003": {"base": AC},
    "mx10004": {"base": AC_HVDC},
    "mx10008": {"base": AC_HVDC},
    "mx10016": {"base": AC_HVDC, "premium": AC_HVDC},
}
# the chassis states the feed of its default build for these; the MX304 states it only for the
# builds that differ, and the MX204 has no feed that is the chassis's own
ON_THE_CHASSIS = {"mx80", "mx104", "mx304", "mx10003", "mx10004", "mx10008", "mx10016"}


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
def test_the_chassis_states_a_feed_where_every_build_takes_the_same_one(name):
    d = device(name)
    chassis = (d.get("chassis") or {}).get("power")
    assert bool(chassis) == (name in ON_THE_CHASSIS)
    if chassis:
        assert not [n for n, c in d["configurations"].items()
                    if (c or {}).get("power") == chassis], "a build restates the chassis feed"
    else:
        offered = [c for c in d["configurations"].values() if (c or {}).get("kind") in OFFERED_KINDS]
        assert offered and all((c or {}).get("power") for c in offered)


@pytest.mark.parametrize("name", sorted(FEEDS))
def test_the_feeds_are_stated_once_and_agree_with_the_seated_supplies(name):
    d = device(name)
    for code, fn in (("L118", lint.lint_device_power_home), ("L119", lint.lint_device_power_stated),
                     ("L120", lint.lint_device_power_stated)):
        assert not findings(fn, d, code), (name, code)


def test_a_build_seating_a_dc_supply_is_not_called_ac():
    """The supplies each build seats, read the way L120 reads them: the feed in the part's
    own name must be one of the build's feeds."""
    for name in FEEDS:
        d = device(name)
        for cfg, c in d["configurations"].items():
            feeds = set(config_power(d, c))
            for bay, ref in lint._seated_supplies(d, c).items():
                named = lint._supply_feed(ref)
                assert named is None or named in feeds, f"{name}:{cfg} {bay} {ref}"


def test_the_baseline_no_longer_carries_the_missing_feed_for_these_devices():
    base = json.loads(BASELINE.read_text())
    still = [n for n in FEEDS
             if "L119" in base.get(f"devices/juniper/{n}/device.yaml", {})]
    assert not still, still

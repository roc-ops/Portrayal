"""The Dell R740xd, the Casa C100G and the Casa C40G state what feeds their builds.

A device with supplies says what feeds each orderable build: `chassis.power` where the box has one feed, a configuration's own
`power` where its build differs (L118, L119). These three said nothing, so a tool filtering by feed could tell their builds apart
only by name.

What each states comes from the supply the build seats and the vendor's own input rows:

* R740xd - every configuration seats the default AC supply in both supply bays, so the chassis states `ac`.
* C100G - the one chassis the data sheet sells is for DC power, and the guide prints a -42 to -60 VDC input.
* C40G - `ac-power` seats the AC supplies, `dc-power` is the chassis for DC power, `docsis-non-redundant` seats the DC power
  entry modules. `base` seats neither supply and the vendor sells the chassis either way, so it states nothing here.
"""
from pathlib import Path

import pytest
import yaml

from portrayal.manifest import OFFERED_KINDS, config_power

LIB = Path(__file__).resolve().parents[2] / "library"


def load(name):
    return yaml.safe_load((LIB / "devices" / name / "device.yaml").read_text(encoding="utf-8"))


def supply_bays(device):
    out = {}
    for view in (device.get("views") or {}).values():
        for bay in (view.get("components") or {}).get("bays") or []:
            if str(bay.get("id", "")).startswith("psu-"):
                out[bay["id"]] = bay
    return out


R740XD = load("dell/r740xd")
OFFERED_R740XD = sorted(n for n, c in R740XD["configurations"].items() if c.get("kind") in OFFERED_KINDS)


@pytest.mark.parametrize("config", OFFERED_R740XD)
def test_every_r740xd_build_is_fed_from_ac(config):
    assert config_power(R740XD, R740XD["configurations"][config]) == ["ac"]


@pytest.mark.parametrize("config", OFFERED_R740XD)
def test_the_r740xd_supplies_a_build_seats_are_ac_supplies(config):
    # the statement above is read off these: a build that seated a DC supply would contradict `ac`
    seated = R740XD["configurations"][config].get("bays") or {}
    for bay_id, bay in supply_bays(R740XD).items():
        ref = seated.get(bay_id, bay.get("default"))
        assert ref and "-ac-" in ref, f"{config} seats {ref!r} in {bay_id}"


def test_the_c100g_chassis_is_fed_from_dc():
    device = load("casa/c100g")
    assert device["chassis"]["power"] == "dc"
    for name, cfg in device["configurations"].items():
        assert config_power(device, cfg) == ["dc"], name


@pytest.mark.parametrize("config, feed", [("ac-power", "ac"), ("dc-power", "dc"), ("docsis-non-redundant", "dc")])
def test_the_c40g_builds_state_the_feed_of_their_supplies(config, feed):
    device = load("casa/c40g")
    assert config_power(device, device["configurations"][config]) == [feed]


def test_the_c40g_ac_build_seats_only_ac_supplies_and_the_dc_builds_only_dc_modules():
    device = load("casa/c40g")
    cfgs = device["configurations"]
    assert set(cfgs["ac-power"]["bays"].values()) == {"casa/c40g-psu-ac@1"}
    seated_dc = cfgs["docsis-non-redundant"]["bays"]
    assert seated_dc["pem-1"] == seated_dc["pem-2"] == "casa/c40g-pem@1"
    assert "casa/c40g-psu-ac@1" not in seated_dc.values()

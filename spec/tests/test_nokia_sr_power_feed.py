"""The Nokia 7750 SR-1 AC, SR-1e, SR-2e and SR-3e say what feeds each build (#513).

A device with supplies has to say what feeds each of its builds (lint L119), so a tool
filtering by feed does not parse a configuration's name. The four devices here seat supplies
whose type the vendor's guide names - the SR-1 AC PSU, the SR-e AC PSU and the SR-e -48/-60 VDC
PSU - so each build states the feed of the supplies it seats and no other.

The SR-1 AC has one feed, so the chassis states it. The SR-e chassis takes either type of supply,
so each configuration states its own: `base` seats DC supplies and `ac` seats AC supplies.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from portrayal import lint
from portrayal.manifest import config_power

SPEC = Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
LINT = SPEC / "tools/portrayal/lint.py"

FEEDS = {
    "nokia/sr-1-ac": {"dual-psu": ["ac"], "shipped-bundle": ["ac"]},
    "nokia/sr-1e": {"base": ["dc"], "ac": ["ac"]},
    "nokia/sr-2e": {"base": ["dc"], "ac": ["ac"]},
    "nokia/sr-3e": {"base": ["dc"], "ac": ["ac"]},
}
BUILDS = [(d, c) for d, cfgs in FEEDS.items() for c in cfgs]


def load(name):
    return yaml.safe_load((LIB / "devices" / name / "device.yaml").read_text())


@pytest.mark.parametrize("device,config", BUILDS)
def test_each_build_states_the_feed_of_its_supplies(device, config):
    data = load(device)
    assert config_power(data, data["configurations"][config]) == FEEDS[device][config]


@pytest.mark.parametrize("device,config", BUILDS)
def test_the_stated_feed_rests_on_a_supply_the_build_seats(device, config):
    data = load(device)
    cfg = data["configurations"][config]
    seated = lint._seated_supplies(data, cfg)
    feeds = {lint._supply_feed(ref) for ref in seated.values()} - {None}
    assert feeds == set(config_power(data, cfg)), seated


def test_the_sr_1_ac_states_one_feed_on_the_chassis():
    data = load("nokia/sr-1-ac")
    assert data["chassis"]["power"] == "ac"
    assert not any("power" in c for c in data["configurations"].values())


@pytest.mark.parametrize("device", ["nokia/sr-1e", "nokia/sr-2e", "nokia/sr-3e"])
def test_the_sr_e_states_its_feed_on_each_configuration_and_not_the_chassis(device):
    data = load(device)
    assert "power" not in data["chassis"]
    assert all("power" in c for c in data["configurations"].values())


@pytest.mark.heavy
def test_lint_finds_no_unstated_feed_and_no_contradiction_on_these_devices():
    cmd = [sys.executable, str(LINT), "--schemas", str(SPEC / "schemas"), "--library", str(LIB)]
    for device in FEEDS:
        cmd += ["--device", device]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    assert "[L119]" not in out and "[L120]" not in out, out


def test_the_baseline_no_longer_records_an_unstated_feed_for_them():
    baseline = json.loads((LIB / "lint-baseline.json").read_text())
    for device in FEEDS:
        assert "L119" not in baseline.get(f"devices/{device}/device.yaml", {}), device

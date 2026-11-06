"""A group a device declares has members.

The tree lists the groups a device declares, so a group nothing joins is a category the hardware does
not have. The first test reads every device. The others hold what the ASR 9010 still draws and says
once its group is gone: both power shelf openings, the measured shelf figures and every placement.
"""
from pathlib import Path

import pytest
import yaml
from portrayal.manifest import view_parts

LIB = Path(__file__).resolve().parents[2] / "library" / "devices"


def load(key):
    with open(LIB / key / "device.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def members(dev):
    for vname, view in (dev.get("views") or {}).items():
        vp = view_parts(view)
        for item in vp["bays"] + vp["placements"]:
            yield vname, item


@pytest.mark.heavy
def test_no_device_declares_a_group_that_nothing_joins():
    orphans = []
    for path in sorted(LIB.glob("*/*/device.yaml")):
        dev = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        joined = {item.get("group") for _v, item in members(dev)}
        orphans += [f"{path.parent.parent.name}/{path.parent.name}: {g}"
                    for g in (dev.get("groups") or {}) if g not in joined]
    assert not orphans, orphans


def test_the_asr_9010_declares_the_groups_that_have_members():
    dev = load("cisco/asr-9010")
    assert sorted(dev["groups"]) == ["fan-trays", "grounding", "power-modules", "slots"]


def test_the_asr_9010_still_draws_both_power_shelf_openings_and_keeps_their_figures():
    dev = load("cisco/asr-9010")
    cutouts = {c["id"]: c for c in dev["views"]["front"]["panel"]["cutouts"]}
    assert cutouts["shelf-0"]["at"] == [13.96, 811.74]
    assert cutouts["shelf-1"]["at"] == [13.96, 873.33]
    assert "power-shelves" in dev["provenance"], "the measured shelf figures keep their entry"
    scoped = [g for g in dev["gaps"] if g["what"] == "bays-awaiting-components"][0]["scope"]
    assert "power-shelves" not in scoped and {"shelf-0", "shelf-1"} <= set(scoped)


def test_the_asr_9010_loses_no_placement_or_bay():
    assert len({(v, item["id"]) for v, item in members(load("cisco/asr-9010"))}) == 19

"""The PRO4X Switched POPS 4G16A has its input: a fixed cord part, the one thing its 36 outlets are fed by.

The cord is placed on the end face it leaves by, exported as a power port, and named in `fed-by` by every outlet, so the exports
say which input feeds each outlet and lint L134 has nothing left to report for the device.

These run against the real library, the exporter's tables and the lint baseline. They render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import portrayal.dcim_export as dcim_export

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SLUG = "servertech/pro4x-switched-pops-4g16a"
CORD = "servertech/pro4x-cord-60309"


def device():
    return yaml.safe_load((LIB / "devices" / SLUG / "device.yaml").read_text())


def placements():
    return [p for v in device()["views"].values() for p in ((v.get("components") or {}).get("placements") or [])]


def test_the_cord_is_placed_once_as_the_input():
    cords = [p for p in placements() if p["ref"].split("@")[0] == CORD]
    assert [p["id"] for p in cords] == ["input"], f"expected one placement `input` of {CORD}, found {[p['id'] for p in cords]}"


def test_every_outlet_is_fed_by_the_cord():
    outlets = [p for p in placements() if p["ref"].split("@")[0] in dcim_export.PART_OUTLET]
    assert len(outlets) == 36
    assert [p["id"] for p in outlets if p.get("fed-by") != "input"] == []


def test_the_cord_exports_a_power_port_the_input_plug_names():
    assert CORD in dcim_export.PART_POWER, f"{CORD} has no PART_POWER row, so its input exports no power port"
    stated = device()["attrs"]["power"]["input-plug"]
    assert stated == dcim_export.PART_POWER[CORD]
    if dcim_export.PART_POWER[CORD] == "other":
        assert CORD in dcim_export.POWER_LABEL, "an `other` power port says which connector it is"


def test_the_cord_part_says_why_nothing_lands_on_it():
    contract = yaml.safe_load((LIB / "components" / "servertech" / "pro4x-cord-60309" / "v1" / "contract.yaml").read_text())
    assert contract["class"] == "inlet"
    assert len(contract.get("unmated", "")) >= 40
    assert not [k for k in ("interface", "presents", "cages", "mates") if k in contract]


def test_the_device_has_no_gap_for_a_missing_input():
    assert "input-cord" not in [g["what"] for g in device().get("gaps") or []]


def test_the_baseline_holds_no_unfed_outlet_for_the_device():
    baseline = json.loads((LIB / "lint-baseline.json").read_text())
    entry = baseline[f"devices/{SLUG}/device.yaml"]
    assert "L134" not in entry

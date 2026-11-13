"""The Tripp Lite series PDU3MV6L2130A, a 0U three-phase metered rack PDU.

What is true of the strip and of the three parts only it places. The 45 outlets stand in three
sections on the pitch the maker's drawing gives. Each section runs through its own two-pole
breaker. The fixed cord exports the power port its plug is. The three meter rows are one part.
Every face is either drawn or says why it is not. Read from the real library, no build.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/eaton/pdu3mv6l2130a/device.yaml"
COMP = ROOT / "library/components"
FACES = ["front", "rear", "top", "bottom", "left", "right"]
NEW_PARTS = ["eaton/tripplite-cord-l21-30p", "eaton/tripplite-phase-meter", "eaton/tripplite-breaker-20a-2p"]


def device():
    return yaml.safe_load(DEVICE.read_text())


def contract(ref):
    return yaml.safe_load((COMP / ref / "v1/contract.yaml").read_text())


def placements(dev, face="front"):
    return dev["views"][face].get("components", {}).get("placements", [])


def outlets(dev):
    return [p for p in placements(dev) if p["id"].startswith("outlet-")]


def test_every_face_is_drawn_or_says_why_it_is_not():
    views = device()["views"]
    assert sorted(views) == sorted(FACES)
    for face in FACES:
        view = views[face]
        drawn = view.get("panel") or view.get("components")
        assert drawn or view.get("empty"), f"{face}: neither drawn nor an `empty` sentence"


def test_the_body_is_the_drawings_56_by_1776_44():
    chassis = device()["chassis"]
    assert chassis["width"] == 56 and chassis["height"] == 1776.44
    assert chassis["mount"] == "rack-side"


def test_45_outlets_are_36_c13_and_9_c19_in_three_sections_of_fifteen():
    rows = outlets(device())
    assert [p["id"] for p in rows] == [f"outlet-{n}" for n in range(1, 46)]
    refs = [p["ref"] for p in rows]
    assert refs.count("std/c13-outlet@1") == 36 and refs.count("std/c19-outlet@1") == 9
    by_breaker = {}
    for p in rows:
        by_breaker.setdefault(p["through"], []).append(p)
    assert sorted(by_breaker) == ["breaker-1", "breaker-2", "breaker-3"]
    for group in by_breaker.values():
        kinds = sorted(p["ref"] for p in group)
        assert kinds == ["std/c13-outlet@1"] * 12 + ["std/c19-outlet@1"] * 3
    assert {p["fed-by"] for p in rows} == {"input"}


def test_the_c19s_stand_at_the_drawn_pitch_and_the_c13_rows_at_theirs():
    rows = outlets(device())
    c19 = [p["at"][1] for p in rows[:3]]
    assert all(round(b - a, 1) == 34.5 for a, b in zip(c19, c19[1:])), "C19 pitch read off the drawing"
    c13 = sorted({p["at"][1] for p in rows[3:15]})
    assert len(c13) == 6
    assert all(round(b - a, 1) == 35.5 for a, b in zip(c13, c13[1:])), "C13 row pitch read off the drawing"
    first = [p["at"][1] for p in rows if p["id"] in ("outlet-1", "outlet-16", "outlet-31")]
    assert round(first[1] - first[0], 1) == 438.3 and round(first[2] - first[1], 1) == 529.8


def test_each_breaker_states_the_two_lines_it_is_across():
    breakers = [p for p in placements(device()) if p["id"].startswith("breaker-")]
    assert [p["id"] for p in breakers] == ["breaker-1", "breaker-2", "breaker-3"]
    assert {p["ref"] for p in breakers} == {"eaton/tripplite-breaker-20a-2p@1"}
    assert sorted(tuple(p["lines"]) for p in breakers) == [("L1", "L2"), ("L2", "L3"), ("L3", "L1")]


def test_the_three_meter_rows_are_one_part_between_the_second_and_third_sections():
    dev = device()
    meters = [p for p in placements(dev) if p["ref"] == "eaton/tripplite-phase-meter@1"]
    assert len(meters) == 1
    ys = [p["at"][1] for p in outlets(dev)]
    assert ys[29] < meters[0]["at"][1] < ys[30], "between the second section's last outlet and the third's first"


def test_the_two_buttons_stand_1556_apart_on_the_rear():
    buttons = [p for p in placements(device(), "rear") if p["ref"] == "eaton/tripplite-mounting-button@1"]
    assert len(buttons) == 2
    assert round(buttons[1]["at"][1] - buttons[0]["at"][1], 2) == 1556.0


def test_the_fixed_cord_exports_an_l21_30p_port():
    dev = device()
    cord = [p for p in placements(dev) if p["id"] == "input"] or [p for p in placements(dev, "bottom") if p["id"] == "input"]
    assert cord[0]["ref"] == "eaton/tripplite-cord-l21-30p@1"
    assert dx.PART_POWER["eaton/tripplite-cord-l21-30p"] == "nema-l21-30p"
    power = dev["attrs"]["power"]
    assert power["input-plug"] == "nema-l21-30p" and power["input-phase"] == "three"
    assert power["input-cord"] == "fixed"


@pytest.mark.parametrize("ref", NEW_PARTS)
def test_a_new_part_is_a_1_0_0_component_with_a_contract_and_one_skin(ref):
    c = contract(ref)
    assert c["version"] == "1.0.0"
    assert c["skins"] == ["default"]
    assert (COMP / ref / "v1/skins/default.svg").is_file()


def test_the_phase_meter_states_three_rows_of_three_characters():
    c = contract("eaton/tripplite-phase-meter")
    windows = [k for k, v in c["elements"].items() if v.get("characters") == 3]
    assert len(windows) == 3


def test_colours_no_photograph_shows_are_declared_a_gap():
    assert "colours" in {g["what"] for g in device()["gaps"]}

"""The Eaton ePDU G3 metered input rack PDUs EMIT03-10 and EMIT04-10.

What is true of the two 1U horizontal units and of the parts only they place: each
has twelve outlets in two sections of six, each section runs through its own breaker,
the fixed cord exports the power port its plug is, the outlets stand on the pitch the
maker's drawing shows, and every face is either drawn or says why it is not. Read from
the real library, no build.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/eaton"
COMP = ROOT / "library/components"
FACES = ["front", "rear", "top", "bottom", "left", "right"]
NAMES = ["emit03-10", "emit04-10"]
SECTION = {"a": ["breaker-a", "A"], "b": ["breaker-b", "B"]}


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def contract(ref):
    return yaml.safe_load((COMP / ref / "v1/contract.yaml").read_text())


def placements(dev, face):
    return dev["views"][face].get("components", {}).get("placements", [])


def outlets(dev):
    return [p for face in ("front", "rear") for p in placements(dev, face) if p["id"].startswith("outlet-")]


@pytest.mark.parametrize("name", NAMES)
def test_every_face_is_drawn_or_says_why_it_is_not(name):
    views = device(name)["views"]
    assert sorted(views) == sorted(FACES)
    for face in FACES:
        view = views[face]
        drawn = view.get("panel") or view.get("components")
        assert drawn or view.get("empty"), f"{name} {face}: neither drawn nor an `empty` sentence"


@pytest.mark.parametrize("name", NAMES)
def test_the_body_is_the_drawings_one_u_box(name):
    chassis = device(name)["chassis"]
    assert (chassis["height"], chassis["depth"], chassis["ru"]) == (42.9, 203.2, 1)
    # 482.6 over the ears, 19.05 an ear: the generic ears stand for the rest
    assert chassis["width"] == 444.5
    assert round(chassis["width"] + 2 * 19.05, 1) == 482.6


@pytest.mark.parametrize("name", NAMES)
def test_twelve_outlets_in_two_sections_each_through_its_own_breaker(name):
    dev = device(name)
    rows = outlets(dev)
    assert sorted(p["id"] for p in rows) == sorted(f"outlet-{s}{n}" for s in "ab" for n in range(1, 7))
    for p in rows:
        assert p["fed-by"] == "input"
        assert p["through"] == f"breaker-{p['id'][7]}"
    front = sorted(p["id"] for p in placements(dev, "front") if p["id"].startswith("outlet-"))
    assert front == ["outlet-a1", "outlet-a2"], "the controls face carries A1 and A2 only"
    breakers = {p["id"]: p for p in placements(dev, "front") if p["id"].startswith("breaker-")}
    assert sorted(breakers) == ["breaker-a", "breaker-b"]
    assert [breakers[k]["attrs"]["section"] for k in sorted(breakers)] == ["A", "B"]


def test_emit03_outlets_are_all_nema_5_20r_on_the_drawn_pair_pitch():
    dev = device("emit03-10")
    rows = outlets(dev)
    assert {p["ref"] for p in rows} == {"std/nema-5-20r@1"}
    rear = sorted((p for p in placements(dev, "rear") if p["id"].startswith("outlet-")), key=lambda p: p["at"][0])
    assert [p["id"][7:] for p in rear] == ["a3", "a4", "a5", "a6", "b1", "b2", "b3", "b4", "b5", "b6"]
    steps = [round(b["at"][0] - a["at"][0], 1) for a, b in zip(rear, rear[1:])]
    # inside a section 38.8 to 39.1 apart, from one section to the next 36.8
    assert steps[0] == 38.8 and steps[1] == 36.8 and steps[2] == 39.1
    assert all(36.7 <= s <= 39.2 for s in steps)


def test_emit04_has_eight_c13_and_four_c19_two_of_each_kind_per_section_end():
    dev = device("emit04-10")
    kinds = {}
    for p in outlets(dev):
        kinds.setdefault(p["ref"], []).append(p["id"][7:])
    assert sorted(kinds) == ["std/c13-outlet@1", "std/c19-outlet@1"]
    assert sorted(kinds["std/c13-outlet@1"]) == ["a1", "a2", "a3", "a4", "b1", "b2", "b3", "b4"]
    assert sorted(kinds["std/c19-outlet@1"]) == ["a5", "a6", "b5", "b6"]


@pytest.mark.parametrize("name, ref, plug, exported", [
    ("emit03-10", "eaton/g3-cord-l5-30p", "nema-l5-30p", "other"),
    ("emit04-10", "eaton/g3-cord-l6-30p", "nema-l6-30p", "nema-l6-30p"),
])
def test_the_fixed_cord_exports_the_power_port_its_plug_is(name, ref, plug, exported):
    dev = device(name)
    cord = [p for p in placements(dev, "rear") if p["id"] == "input"][0]
    assert cord["ref"] == f"{ref}@1"
    assert contract(ref)["attrs"]["plug"] == plug
    assert dx.PART_POWER[ref] == exported
    assert dev["attrs"]["power"]["input-plug"] == exported
    assert dev["attrs"]["power"]["input-cord"] == "fixed"


def test_the_l5_30p_cord_says_which_connector_it_is_when_it_exports_other():
    from portrayal import dcim_registers as regs

    assert regs.POWER_LABEL["eaton/g3-cord-l5-30p"] == "NEMA L5-30P locking plug on a fixed cord"


@pytest.mark.parametrize("name", NAMES)
def test_the_meter_module_has_three_rj45_a_usb_a_a_reset_a_display_and_four_buttons(name):
    refs = {}
    for p in placements(device(name), "front"):
        refs.setdefault(p["ref"], []).append(p["id"])
    assert refs["std/rj45@2"] == ["serial"]
    assert sorted(refs["common/rj45-eth@1"]) == ["daisy-chain", "network"]
    assert refs["std/usb-a@1"] == ["usb"]
    assert refs["common/reset-button@1"] == ["reset"]
    assert refs["eaton/g3-display@1"] == ["display"]
    assert sorted(refs["eaton/g3-nav-button@1"]) == ["button-down", "button-enter", "button-esc", "button-up"]
    for ref in ("g3-display", "g3-nav-button"):
        assert contract(f"eaton/{ref}")["version"] == "1.0.0"


@pytest.mark.parametrize("name", NAMES)
def test_the_metering_is_the_branch_and_nothing_switches(name):
    mgmt = device(name)["attrs"]["management"]
    assert mgmt["metering-scope"] == "branch"
    assert mgmt["outlet-switching"] is False

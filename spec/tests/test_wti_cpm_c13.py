"""The WTI CPM-800-2 and CPM-1600-2: the console server and PDU hybrids with IEC C13 outlets.

The maker's dimensional drawings for the -2 families draw the same outline, front and rear as the -1 families with a C13 outlet in
each outlet's place. What is true of the library once the two devices are in:

  - each model is a device of the maker, the size the drawing gives, one rack unit (800) or two (1600);
  - the outlets are IEC C13 library parts in the count the documents give, each fed by the C20 inlet of its bank (four to an inlet);
  - the front carries the same serial ports, Ethernet jacks, phone jack and USB set-up port as the -1 model of its size;
  - the colours and the positions say they are not checked against a photograph;
  - no part number is on two devices.

These read the device sources. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

MODELS = {
    "cpm-800-2": dict(model="CPM-800-2", twin="cpm-800-1", ru=1, outlets=8, inlets=2, serial=8, depth=220.98),
    "cpm-1600-2": dict(model="CPM-1600-2", twin="cpm-1600-1", ru=2, outlets=16, inlets=4, serial=16, depth=317.5),
}
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]


def device(name):
    return yaml.safe_load((LIB / "devices" / "wti" / name / "device.yaml").read_text())


def placements(name, view):
    comps = (device(name)["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_model_is_a_device_of_the_maker_at_the_size_the_drawing_gives(name):
    d = device(name)
    m = MODELS[name]
    assert (d["manufacturer"], d["model"]) == ("WTI", m["model"])
    ch = d["chassis"]
    assert ch["width"] == 435.6
    assert ch["ru"] == m["ru"]
    assert ch["height"] == (44.45 if m["ru"] == 1 else 88.9)
    assert ch["depth"] == m["depth"]


@pytest.mark.parametrize("name", sorted(MODELS))
def test_all_six_views_are_there_and_a_bare_one_says_why(name):
    views = device(name)["views"]
    assert sorted(views) == sorted(VIEWS)
    for view, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{name} {view}: neither drawn nor an `empty:` sentence"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_outlets_are_c13_parts_each_fed_by_the_inlet_of_its_bank(name):
    m = MODELS[name]
    rear = placements(name, "rear")
    refs = [p["ref"] for p in rear.values()]
    assert refs.count("std/c13-outlet@1") == m["outlets"]
    assert refs.count("std/c20-inlet@1") == m["inlets"]
    assert "std/nema-5-15r@1" not in refs
    feeds = {}
    for p in rear.values():
        if p["ref"] == "std/c13-outlet@1":
            assert p["fed-by"] in rear and rear[p["fed-by"]]["ref"] == "std/c20-inlet@1", p["id"]
            feeds.setdefault(p["fed-by"], []).append(p["id"])
    assert sorted(len(v) for v in feeds.values()) == [4] * m["inlets"]


@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_front_carries_the_console_server_ports_of_the_model_of_its_size(name):
    m = MODELS[name]
    front = placements(name, "front")
    refs = [p["ref"] for p in front.values()]
    assert refs.count("std/rj45-ganged@2") == m["serial"]
    assert refs.count("common/rj45-eth@1") == 2
    assert refs.count("common/rj11-jack@1") == 1
    assert refs.count("std/mini-usb@1") == 1
    serial = sorted(p["rel-pos"] for p in front.values() if p["ref"] == "std/rj45-ganged@2")
    assert serial == list(range(1, m["serial"] + 1))


def test_the_cpm_1600_banks_are_a1_a4_a5_a8_b1_b4_b5_b8():
    rear = placements("cpm-1600-2", "rear")
    bank = {p["id"]: p["fed-by"] for p in rear.values() if p["ref"] == "std/c13-outlet@1"}
    for row in "ab":
        for n in range(1, 9):
            assert bank[f"outlet-{row}{n}"] == f"inlet-{row}{1 if n <= 4 else 2}"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_colours_and_positions_say_no_photograph_is_held(name):
    d = device(name)
    assert "UNCHECKED" in d["provenance"]["colour"]["note"]
    assert "NO PHOTOGRAPH" in d["provenance"]["sources"]["note"]
    assert any(g["what"] == "photographs" for g in d["gaps"])


def test_no_part_number_is_on_two_devices_of_the_maker():
    seen = {}
    for path in sorted((LIB / "devices" / "wti").glob("*/device.yaml")):
        for pn in yaml.safe_load(path.read_text())["configurations"]["base"]["part-numbers"]:
            assert pn not in seen, f"{pn} is on {seen.get(pn)} and {path.parent.name}"
            seen[pn] = path.parent.name

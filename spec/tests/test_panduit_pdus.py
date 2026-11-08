"""The Panduit P24B14M basic PDU and the P32E06M G5 intelligent PDU: what the two devices state of their
outlets, breakers, input cord and controller, and that their parts are in the library and in the DCIM tables.

Everything is read from the sources (the device files, the contracts and the exporter's tables), so the module
needs no build.
"""
from pathlib import Path

import pytest

from portrayal import dcim_export as dx
from portrayal.manifest import load_yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = {"p24b14m": {"c13": 12, "c19": 12, "breakers": 6},
           "p32e06m": {"c13": 24, "c19": 8, "breakers": 1}}


def device(model):
    return load_yaml(LIB / f"devices/panduit/{model}/device.yaml")


def contract(ref):
    ns, rest = ref.split("/")
    name, ver = rest.split("@")
    return load_yaml(LIB / f"components/{ns}/{name}/v{ver}/contract.yaml")


def placements(doc, view):
    return doc["views"][view].get("components", {}).get("placements", [])


def landed(p):
    """The box an outlet lands on, turned about its own centre: x, y, w, h."""
    w, h = (35.6, 27.7) if p["ref"].endswith("c19-outlet@1") else (30.4, 22.0)
    cx, cy = p["at"][0] + w / 2, p["at"][1] + h / 2
    if p.get("rotate", 0) in (90, 270):
        w, h = h, w
    return cx - w / 2, cy - h / 2, w, h


def outlets(doc):
    return [p for p in placements(doc, "front") if p["ref"] in ("std/c13-outlet@1", "std/c19-outlet@1")]


@pytest.mark.parametrize("model", DEVICES)
def test_the_device_counts_its_outlets_by_kind(model):
    outs = outlets(device(model))
    got = {k: sum(1 for p in outs if p["ref"] == f"std/{k}-outlet@1") for k in ("c13", "c19")}
    assert got == {k: DEVICES[model][k] for k in ("c13", "c19")}


@pytest.mark.parametrize("model", DEVICES)
def test_every_outlet_is_fed_by_the_cord_and_sits_on_the_face(model):
    doc = device(model)
    ids = [p["id"] for p in outlets(doc)]
    assert len(ids) == len(set(ids))
    h, w = doc["chassis"]["height"], doc["chassis"]["width"]
    for p in outlets(doc):
        assert p["fed-by"] == "input", p["id"]
        x, y, bw, bh = landed(p)
        assert 0 <= x and x + bw <= w + 0.01 and 0 <= y and y + bh <= h, p["id"]


@pytest.mark.parametrize("model", DEVICES)
def test_the_input_is_a_panduit_cord_part_that_states_its_plug(model):
    doc = device(model)
    cord = [p for p in placements(doc, "bottom") if p["id"] == "input"]
    assert len(cord) == 1 and cord[0]["ref"].startswith("panduit/g5-cord-")
    c = contract(cord[0]["ref"])
    assert c["class"] == "inlet" and c["attrs"]["plug"].startswith("iec-60309-")
    assert doc["attrs"]["power"]["input-cord"] == "fixed"
    assert dx.PART_POWER[cord[0]["ref"].split("@")[0]] == "other"
    assert cord[0]["ref"].split("@")[0] in dx.POWER_LABEL


def test_each_outlet_of_the_basic_unit_runs_through_a_breaker_that_states_its_lines():
    doc = device("p24b14m")
    brk = {p["id"]: p for p in placements(doc, "front") if p["ref"] == "panduit/g5-breaker-20a@1"}
    assert len(brk) == DEVICES["p24b14m"]["breakers"]
    for b in brk.values():
        assert len(b["lines"]) == 2
    per = {}
    for p in outlets(doc):
        assert p["through"] in brk, p["id"]
        per[p["through"]] = per.get(p["through"], 0) + 1
    assert set(per.values()) == {4}


def test_the_intelligent_unit_seats_its_controller_in_a_bay_and_switches_its_outlets():
    doc = device("p32e06m")
    bay = doc["views"]["front"]["components"]["bays"]
    assert [b["default"] for b in bay] == ["panduit/g5-controller@1"]
    assert contract("panduit/g5-controller@1")["kind"] == "module"
    assert doc["attrs"]["management"]["outlet-switching"] is True
    assert all(p["states"] == ["on", "off"] for p in outlets(doc))


@pytest.mark.parametrize("model", DEVICES)
def test_the_two_mounting_buttons_are_the_dimensioned_1555_apart(model):
    doc = device(model)
    btn = [p for p in placements(doc, "rear") if p["ref"] == "panduit/g5-mounting-button@1"]
    assert len(btn) == 2
    assert abs(abs(btn[0]["at"][1] - btn[1]["at"][1]) - 1555.0) < 0.01
    assert contract("panduit/g5-mounting-button@1")["mates"] == "pdu-button"


@pytest.mark.parametrize("model", DEVICES)
def test_a_panduit_part_has_its_contract_and_one_skin(model):
    refs = {p["ref"] for v in device(model)["views"].values() for p in v.get("components", {}).get("placements", [])
            if p["ref"].startswith("panduit/")}
    for ref in refs:
        ns, rest = ref.split("/")
        name, ver = rest.split("@")
        base = LIB / f"components/{ns}/{name}/v{ver}"
        assert (base / "contract.yaml").exists() and (base / "skins/default.svg").exists(), ref


@pytest.mark.parametrize("model", DEVICES)
def test_no_two_outlets_overlap(model):
    boxes = [(p["id"], *landed(p)) for p in outlets(device(model))]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            overlap = a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]
            assert not overlap, (a[0], b[0])

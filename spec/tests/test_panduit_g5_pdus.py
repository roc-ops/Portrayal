"""The Panduit P36G18M and P42G20M G5 intelligent PDUs: what the two devices state of their outlets, breakers,
input cord and controller, and that their parts are in the library and in the DCIM tables.

Everything is read from the sources (the device files, the contracts and the exporter's tables), so the module
needs no build.
"""
from pathlib import Path

import pytest

from portrayal import dcim_export as dx
from portrayal import dcim_registers as dr
from portrayal.manifest import load_yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
COMBO = ("panduit/g5-outlet-c13-c15@1", "panduit/g5-outlet-c13-c15-c19@1")
KINDS = ("std/c13-outlet@1", "std/c19-outlet@1") + COMBO
DEVICES = {"p36g18m": {"std/c13-outlet@1": 30, "std/c19-outlet@1": 6, "breakers": 2, "cord": "panduit/g5-cord-l6-30p",
                       "per-breaker": [18, 18]},
           "p42g20m": {"panduit/g5-outlet-c13-c15@1": 21, "panduit/g5-outlet-c13-c15-c19@1": 21, "breakers": 6,
                       "cord": "panduit/g5-cord-60309-3pe-9h", "per-breaker": [8, 8, 8, 6, 6, 6]}}


def device(model):
    return load_yaml(LIB / f"devices/panduit/{model}/device.yaml")


def contract(ref):
    ns, rest = ref.split("/")
    name, ver = rest.split("@")
    return load_yaml(LIB / f"components/{ns}/{name}/v{ver}/contract.yaml")


def placements(doc, view):
    return doc["views"][view].get("components", {}).get("placements", [])


def outlets(doc):
    return [p for p in placements(doc, "front") if p["ref"] in KINDS]


def box(p):
    """The box a placed part lands on, turned about its own centre: x, y, w, h."""
    if p["ref"].startswith("std/"):
        w, h = (35.6, 27.7) if p["ref"].endswith("c19-outlet@1") else (30.4, 22.0)
    else:
        c = contract(p["ref"])
        w, h = c["size"]["w"], c["size"]["h"]
    cx, cy = p["at"][0] + w / 2, p["at"][1] + h / 2
    if p.get("rotate", 0) in (90, 270):
        w, h = h, w
    return cx - w / 2, cy - h / 2, w, h


@pytest.mark.parametrize("model", DEVICES)
def test_the_device_counts_its_outlets_by_kind(model):
    outs = outlets(device(model))
    want = {k: v for k, v in DEVICES[model].items() if k in KINDS}
    got = {k: sum(1 for p in outs if p["ref"] == k) for k in KINDS}
    assert {k: v for k, v in got.items() if v} == want


@pytest.mark.parametrize("model", DEVICES)
def test_every_outlet_is_fed_by_the_cord_switched_and_sits_on_the_face(model):
    doc = device(model)
    ids = [p["id"] for p in outlets(doc)]
    assert len(ids) == len(set(ids))
    h, w = doc["chassis"]["height"], doc["chassis"]["width"]
    for p in outlets(doc):
        assert p["fed-by"] == "input" and p["states"] == ["on", "off"], p["id"]
        x, y, bw, bh = box(p)
        assert 0 <= x and x + bw <= w + 0.01 and 0 <= y and y + bh <= h, p["id"]
    assert doc["attrs"]["management"]["outlet-switching"] is True


@pytest.mark.parametrize("model", DEVICES)
def test_the_input_is_a_panduit_cord_part_that_states_its_plug(model):
    doc = device(model)
    cord = [p for p in placements(doc, "bottom") if p["id"] == "input"]
    assert len(cord) == 1 and cord[0]["ref"].split("@")[0] == DEVICES[model]["cord"]
    c = contract(cord[0]["ref"])
    assert c["class"] == "inlet" and c["attrs"]["plug"]
    assert doc["attrs"]["power"]["input-cord"] == "fixed"
    assert dx.PART_POWER[DEVICES[model]["cord"]] == "other"
    assert DEVICES[model]["cord"] in dr.POWER_LABEL


@pytest.mark.parametrize("model", DEVICES)
def test_each_outlet_runs_through_a_breaker_that_states_its_lines(model):
    doc = device(model)
    brk = {p["id"]: p for p in placements(doc, "front") if p["ref"] == "panduit/g5-breaker-20a@1"}
    assert len(brk) == DEVICES[model]["breakers"]
    for b in brk.values():
        assert len(b["lines"]) == 2
    per = {}
    for p in outlets(doc):
        assert p["through"] in brk, p["id"]
        per[p["through"]] = per.get(p["through"], 0) + 1
    assert [per[b] for b in brk] == DEVICES[model]["per-breaker"]


def test_the_three_phase_unit_puts_each_breaker_across_a_different_pair_of_lines():
    brk = [p for p in placements(device("p42g20m"), "front") if p["ref"] == "panduit/g5-breaker-20a@1"]
    assert [tuple(b["lines"]) for b in brk] == [("L1", "L2"), ("L2", "L3"), ("L3", "L1")] * 2


@pytest.mark.parametrize("model", DEVICES)
def test_the_controller_sits_in_a_bay(model):
    doc = device(model)
    bay = doc["views"]["front"]["components"]["bays"]
    assert [b["default"] for b in bay] == ["panduit/g5-controller@1"]
    assert contract("panduit/g5-controller@1")["kind"] == "module"


@pytest.mark.parametrize("model", DEVICES)
def test_the_two_mounting_buttons_are_the_dimensioned_1555_apart(model):
    btn = [p for p in placements(device(model), "rear") if p["ref"] == "panduit/g5-mounting-button@1"]
    assert len(btn) == 2
    assert abs(abs(btn[0]["at"][1] - btn[1]["at"][1]) - 1555.0) < 0.01


@pytest.mark.parametrize("ref", COMBO)
def test_a_combination_outlet_is_one_panduit_part_in_the_exporter_tables(ref):
    c = contract(ref)
    name = ref.split("@")[0]
    assert c["class"] == "inlet" and c["attrs"]["media"] == "ac"
    if ref == COMBO[0]:   # the 10 A socket is a C13 with the C15 extension: the C13 key, upstream's C13 type
        assert c["interface"] == "iec-c13" and dr.PART_OUTLET[name] == "iec-60320-c13"
        assert name not in dr.OUTLET_LABEL
    else:
        assert c["interface"] == "panduit-combo" and dr.PART_OUTLET[name] == "other" and name in dr.OUTLET_LABEL


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
    boxes = [(p["id"], *box(p)) for p in outlets(device(model))]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            overlap = a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]
            assert not overlap, (a[0], b[0])

"""The Eaton ePDU G3 basic EPBZ77 and the Tripp Lite series PDUMV30.

What is true of the two strips and of the three parts only they place: the outlets
stand on the pitch their drawings give, each outlet runs through the breaker that
protects it, each fixed cord exports the power port its plug is, and every face is
either drawn or says why it is not. Read from the real library, no build.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/eaton"
COMP = ROOT / "library/components"
FACES = ["front", "rear", "top", "bottom", "left", "right"]


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def contract(ref):
    return yaml.safe_load((COMP / ref / "v1/contract.yaml").read_text())


def placements(dev, face="front"):
    return dev["views"][face].get("components", {}).get("placements", [])


def outlets(dev):
    return [p for p in placements(dev) if p["id"].startswith("outlet-")]


@pytest.mark.parametrize("name", ["epbz77", "pdumv30"])
def test_every_face_is_drawn_or_says_why_it_is_not(name):
    views = device(name)["views"]
    assert sorted(views) == sorted(FACES)
    for face in FACES:
        view = views[face]
        drawn = view.get("panel") or view.get("components")
        assert drawn or view.get("empty"), f"{name} {face}: neither drawn nor an `empty` sentence"


def test_epbz77_has_24_outlets_on_the_drawn_pitch():
    dev = device("epbz77")
    rows = outlets(dev)
    assert [p["id"] for p in rows] == [f"outlet-{n}" for n in range(1, 25)]
    assert {p["ref"] for p in rows} == {"std/nema-5-20r@1"}
    ys = [p["at"][1] for p in rows]
    assert all(round(a - b, 2) == 45.0 for a, b in zip(ys, ys[1:])), "the drawing's 45.0 pitch"
    assert {p["fed-by"] for p in rows} == {"input"}
    assert {p["through"] for p in rows} == {"breaker"}


def test_epbz77_cord_is_the_part_that_exports_an_l5_20p_port():
    dev = device("epbz77")
    cord = [p for p in placements(dev) if p["id"] == "input"][0]
    assert cord["ref"] == "eaton/g3-cord-l5-20p@1"
    assert dx.PART_POWER["eaton/g3-cord-l5-20p"] == "nema-l5-20p"
    assert dev["attrs"]["power"]["input-plug"] == "nema-l5-20p"


def test_pdumv30_has_two_banks_of_twelve_each_through_its_own_breaker():
    dev = device("pdumv30")
    rows = outlets(dev)
    assert len(rows) == 24 and {p["ref"] for p in rows} == {"std/nema-5-20r@1"}
    by_breaker = {}
    for p in rows:
        by_breaker.setdefault(p["through"], []).append(p)
    assert sorted(by_breaker) == ["breaker-1", "breaker-2"]
    for group in by_breaker.values():
        assert len(group) == 12
        ys = [p["at"][1] for p in group]
        assert all(round(b - a, 2) == 40.95 for a, b in zip(ys, ys[1:]))
    top = [p["at"][1] for p in by_breaker["breaker-2"]][0]
    bottom = [p["at"][1] for p in by_breaker["breaker-1"]][0]
    assert round(bottom - top, 1) == 723.2


def test_pdumv30_mounts_on_two_buttons_the_drawing_puts_1555_apart():
    dev = device("pdumv30")
    buttons = [p for p in placements(dev, "rear") if p["ref"] == "eaton/tripplite-mounting-button@1"]
    assert len(buttons) == 2
    assert round(buttons[1]["at"][1] - buttons[0]["at"][1], 2) == 1555.0
    assert len(dev["views"]["front"]["components"]["placements"]) > 24
    meters = [p for p in placements(dev) if p["ref"] == "eaton/tripplite-bank-meter@1"]
    assert len(meters) == 2


def test_the_l5_30p_cord_exports_an_other_port_and_names_its_connector():
    assert dx.PART_POWER["eaton/tripplite-cord-l5-30p"] == "other"
    assert "L5-30P" in dx.POWER_LABEL["eaton/tripplite-cord-l5-30p"]
    assert device("pdumv30")["attrs"]["power"]["input-plug"] == "other"


@pytest.mark.parametrize("ref", ["eaton/g3-cord-l5-20p", "eaton/tripplite-cord-l5-30p",
                                 "eaton/tripplite-bank-meter"])
def test_a_new_part_is_a_1_0_0_component_with_a_contract_and_one_skin(ref):
    c = contract(ref)
    assert c["version"] == "1.0.0"
    assert c["skins"] == ["default"]
    assert (COMP / ref / "v1/skins/default.svg").is_file()


def test_a_figure_read_off_a_drawing_with_no_dimension_is_declared_an_estimate():
    c = contract("eaton/tripplite-cord-l5-30p")
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}


@pytest.mark.parametrize("name", ["epbz77", "pdumv30"])
def test_colours_no_photograph_shows_are_declared_a_gap(name):
    assert "colours" in {g["what"] for g in device(name)["gaps"]}

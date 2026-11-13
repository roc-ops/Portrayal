"""The Enlogic EB0952, EN2333 and EN6324 PDUs and the L6-30P cord they share.

What is true of the library: each device places the outlets its data sheet counts and its breakers.
It states one fixed input cord and sits on two toolless buttons. It says what no document gives.
Reads the contracts and the device sources; none reads `library/dist`.
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

DEVICES = {
    "eb0952": dict(size=(56, 1780, 75), cord="enlogic/pdu-cord-60309-3pe-9h@1", breakers=6,
                   outlets={"enlogic/combo-outlet-c13-c15@1": 21, "enlogic/combo-outlet-c13-c15-c19@1": 21}),
    "en2333": dict(size=(52, 1750, 75), cord="enlogic/pdu-cord-l6-30p@1", breakers=2,
                   outlets={"std/c13-outlet@1": 30, "std/c19-outlet@1": 6}),
    "en6324": dict(size=(52, 1750, 53), cord="enlogic/pdu-cord-l6-30p@1", breakers=2,
                   outlets={"std/c13-outlet@1": 20, "std/c19-outlet@1": 4}),
}
BREAKERS = {"enlogic/en-breaker-20a-2p@1", "enlogic/eb-breaker-20a-2p@1", "enlogic/en2333-breaker-20a-2p@1"}


def _device(slug):
    return yaml.safe_load((LIB / "devices" / "enlogic" / slug / "device.yaml").read_text())


def _placements(slug, view):
    return _device(slug)["views"][view]["components"]["placements"]


@pytest.mark.parametrize("slug", DEVICES)
def test_the_chassis_is_the_drawn_strip(slug):
    chassis = _device(slug)["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == DEVICES[slug]["size"]
    assert chassis["mount"] == "rack-side"
    assert set(_device(slug)["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


@pytest.mark.parametrize("slug", DEVICES)
def test_the_outlets_are_the_ones_the_data_sheet_counts(slug):
    outlets = [p for p in _placements(slug, "front") if p["id"].startswith("outlet-")]
    assert Counter(p["ref"] for p in outlets) == DEVICES[slug]["outlets"]


@pytest.mark.parametrize("slug", DEVICES)
def test_every_outlet_is_behind_a_breaker_that_is_placed(slug):
    placed = _placements(slug, "front")
    breakers = {p["id"] for p in placed if p["ref"] in BREAKERS}
    assert len(breakers) == DEVICES[slug]["breakers"]
    for p in placed:
        if p["id"].startswith("outlet-"):
            assert p["fed-by"] == "input" and p["through"] in breakers


@pytest.mark.parametrize("slug", DEVICES)
def test_the_cord_is_the_one_input(slug):
    inputs = [p for p in _placements(slug, "top") if p["id"] == "input"]
    assert [p["ref"] for p in inputs] == [DEVICES[slug]["cord"]]


@pytest.mark.parametrize("slug", DEVICES)
def test_two_buttons_hold_the_strip_1555_apart(slug):
    buttons = sorted(p["at"][1] for p in _placements(slug, "rear") if p["ref"] == "enlogic/pdu-mounting-button@1")
    assert len(buttons) == 2
    assert buttons[1] - buttons[0] == pytest.approx(1555.0, abs=0.01)


@pytest.mark.parametrize("slug", DEVICES)
def test_the_gaps_name_what_no_document_gives(slug):
    gaps = {g["what"] for g in _device(slug)["gaps"]}
    assert {"weight", "colour"} <= gaps


FEEDS = {
    "en2333": {"breaker-b1": 18, "breaker-b2": 18},
    "en6324": {"breaker-b1": 12, "breaker-b2": 12},
    "eb0952": {"breaker-b1": 6, "breaker-b2": 6, "breaker-b3": 6, "breaker-b4": 8, "breaker-b5": 8, "breaker-b6": 8},
}


@pytest.mark.parametrize("slug", FEEDS)
def test_each_breaker_feeds_the_outlets_of_its_span(slug):
    outlets = [p for p in _placements(slug, "front") if p["id"].startswith("outlet-")]
    assert dict(Counter(p["through"] for p in outlets)) == FEEDS[slug]


def test_the_eb0952_marks_on_white_columns_are_dark():
    through = {p["id"]: p["through"] for p in _placements("eb0952", "front") if p["id"].startswith("outlet-")}
    marks = _device("eb0952")["views"]["front"]["silkscreen"]
    white = [m for m in marks if through[m["for"]] in ("breaker-b1", "breaker-b4")]
    assert len(white) == 4 * 7 and all(m.get("fill") == "#202020" for m in white)


def test_the_en6324_plates_use_the_label_first_skin():
    skins = _device("en6324")["configurations"]["base"]["skins"]
    assert skins == {"en2333-breaker-20a-2p": "label-first"}
    assert "skins" not in _device("en2333")["configurations"]["base"]


def test_the_l6_30p_cord_says_where_its_figures_come_from():
    contract = yaml.safe_load((LIB / "components" / "enlogic" / "pdu-cord-l6-30p" / "v1" / "contract.yaml").read_text())
    assert contract["name"] == "pdu-cord-l6-30p" and contract["class"] == "inlet"
    assert contract["attrs"]["plug"] == "nema-l6-30p" and contract["attrs"]["cord-length-m"] == 3
    assert {"size", "cord", "plug", "not-drawn"} <= set(contract["provenance"])

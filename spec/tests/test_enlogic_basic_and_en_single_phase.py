"""The Enlogic EB0952, EN2333 and EN6324 PDUs and the L6-30P cord they share.

What is true of the library: each device places the outlets its data sheet counts and its breakers.
It states one fixed input cord and sits on two toolless buttons. It says what no document gives.
Reads the contracts and the device sources; only the plate test reads `library/dist`, and it is heavy.
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


def test_the_en6324_feeds_each_outlet_from_the_breaker_of_its_span():
    through = {p["id"]: p["through"] for p in _placements("en6324", "front") if p["id"].startswith("outlet-")}
    assert through == {f"outlet-{n}": "breaker-b1" if n <= 12 else "breaker-b2" for n in range(1, 25)}


def test_the_en6324_export_gives_the_same_feed():
    export = yaml.safe_load((LIB / "exports" / "netbox" / "device-types" / "Enlogic" / "EN6324.yaml").read_text())
    feeds = {o["name"]: o["description"].split(",")[0] for o in export["power-outlets"]}
    assert feeds == {f"outlet-{n}": "Through breaker-b1" if n <= 12 else "Through breaker-b2" for n in range(1, 25)}


# Centres of the four rings on each side: mm along from the cord end, and mm from the front on the right face.
# The left face is the right face turned over, so its x is the face's depth less that figure.
RINGS = {
    "en6324": dict(depth=53.0, front=32.0, size=8.2, along=(40.51, 64.52, 1596.41, 1620.42)),
    "en2333": dict(depth=75.0, front=54.03, size=12.09, along=(40.53, 64.54, 1596.42, 1620.43)),
}


def _rings(slug, view):
    return [d for d in _device(slug)["views"][view]["panel"]["decor"] if d["kind"] == "button-location"]


@pytest.mark.parametrize("view", ["left", "right"])
@pytest.mark.parametrize("slug", RINGS)
def test_each_side_draws_the_four_button_location_rings(slug, view):
    want = RINGS[slug]
    rings = _rings(slug, view)
    assert len(rings) == 4
    centres = sorted((d["at"][0] + d["size"][0] / 2, d["at"][1] + d["size"][1] / 2) for d in rings)
    x = want["front"] if view == "right" else want["depth"] - want["front"]
    assert [c[0] for c in centres] == pytest.approx([x] * 4, abs=0.05)
    assert sorted(c[1] for c in centres) == pytest.approx(want["along"], abs=0.05)
    assert all(d["size"] == [want["size"], want["size"]] for d in rings)


# The end-on view of the drawing prints one round head. Its centre is across the width and mm from the rear edge.
HEADS = {"en6324": (26.0, 6.3, 53.0), "en2333": (26.0, 6.0, 75.0)}


@pytest.mark.parametrize("slug", HEADS)
def test_the_far_end_draws_the_one_round_head_of_the_end_view(slug):
    across, from_rear, depth = HEADS[slug]
    bottom = _device(slug)["views"]["bottom"]
    assert bottom["size"] == {"w": 52, "h": depth} and "empty" not in bottom
    heads = bottom["panel"]["decor"]
    assert len(heads) == 1 and heads[0]["kind"] == "screw-head" and heads[0]["size"] == [6.62, 6.62]
    assert heads[0]["at"][0] + 3.31 == pytest.approx(across, abs=0.05)
    assert heads[0]["at"][1] + 3.31 == pytest.approx(from_rear, abs=0.05)


@pytest.mark.parametrize("slug", HEADS)
def test_the_notes_no_longer_say_the_right_view_prints_no_head(slug):
    text = yaml.safe_dump(_device(slug)["provenance"]) + yaml.safe_dump(_device(slug)["gaps"])
    assert "prints no head" not in text and "draws this end as a plain outline" not in text


@pytest.mark.parametrize("slug", HEADS)
def test_the_flat_tab_outside_the_faces_is_a_gap_that_quotes_the_schema(slug):
    gaps = {g["what"]: g for g in _device(slug)["gaps"]}
    assert "cord-end-tab" in gaps
    gap = gaps["cord-end-tab"]
    assert gap["reason"] == "needs-drawing" and "bottom" in gap["scope"]
    assert "L150 refuses a part outside its view" in gap["note"] and "one near each end" in gap["note"]


# The part's own plate-local rocker x: the label comes first on the EN6324, so its rocker is at the other edge.
ROCKER_X = {"en2333": 28.3, "en6324": 8.9}


@pytest.mark.heavy
@pytest.mark.parametrize("slug", ROCKER_X)
def test_the_built_plates_put_the_rocker_where_the_skin_does(slug):
    import json
    path = LIB / "dist" / f"{slug}.front.elements.json"
    assert path.is_file(), f"no {path.name}: run ./build.sh first"
    boxes = {e["id"]: e["box"] for e in json.loads(path.read_text())["elements"] if e.get("class") == "breaker"}
    assert {"breaker-b1", "breaker-b2", "breaker-b1--rocker", "breaker-b2--rocker"} <= set(boxes)
    for bank in ("b1", "b2"):
        plate, rocker = boxes[f"breaker-{bank}"], boxes[f"breaker-{bank}--rocker"]
        assert rocker["x"] - plate["x"] == pytest.approx(ROCKER_X[slug], abs=0.01)
        assert rocker["y"] - plate["y"] == pytest.approx(27.65, abs=0.01)


def test_the_l6_30p_cord_says_where_its_figures_come_from():
    contract = yaml.safe_load((LIB / "components" / "enlogic" / "pdu-cord-l6-30p" / "v1" / "contract.yaml").read_text())
    assert contract["name"] == "pdu-cord-l6-30p" and contract["class"] == "inlet"
    assert contract["attrs"]["plug"] == "nema-l6-30p" and contract["attrs"]["cord-length-m"] == 3
    assert {"size", "cord", "plug", "not-drawn"} <= set(contract["provenance"])

"""The marks the data sheet photographs show at the ends of the APC 1U rack PDUs AP7821B and AP7921B.

The p.1 photograph of each outlet face shows two small round marks at each end of the face, one above the other.
The AP7921B's angled photograph also shows its display end: six marks in two rows of three. What is true of the
library once they are drawn:

  - the outlet face draws four round marks, two within 8 mm of each end, at two heights;
  - the display end (the `left` view, seen from behind) draws six, in two rows of three, inside the end;
  - the inlet end (the `right` view) stays undrawn, because no held photograph shows it;
  - every mark is declared an estimate and says how its position was read.

These read the device sources. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SKUS = {"ap7821b": (444, 44, 102), "ap7921b": (445, 44, 108)}


def device(sku):
    return yaml.safe_load((LIB / "devices" / "apc" / sku / "device.yaml").read_text())


def marks(sku, view):
    decor = (device(sku)["views"][view].get("panel") or {}).get("decor") or []
    return [d for d in decor if d.get("kind") == "end-screw"]


def centre(d):
    return (d["at"][0] + d["size"][0] / 2, d["at"][1] + d["size"][1] / 2)


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_outlet_face_draws_two_round_marks_at_each_end(sku):
    width = SKUS[sku][0]
    drawn = marks(sku, "rear")
    assert len(drawn) == 4
    for d in drawn:
        assert d["rx"] == d["size"][0] / 2 == d["size"][1] / 2, "round"
    cx = sorted(centre(d)[0] for d in drawn)
    assert all(x <= 8 for x in cx[:2]) and all(x >= width - 8 for x in cx[2:])
    assert len({round(centre(d)[1]) for d in drawn}) == 2, "two heights"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_display_end_draws_six_marks_in_two_rows_of_three(sku):
    _, height, depth = SKUS[sku]
    drawn = marks(sku, "left")
    assert len(drawn) == 6
    assert len({round(centre(d)[1]) for d in drawn}) == 2
    assert len({round(centre(d)[0]) for d in drawn}) == 3
    for d in drawn:
        x, y = centre(d)
        assert 0 < x < depth and 0 < y < height


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_inlet_end_stays_undrawn_and_says_why(sku):
    right = device(sku)["views"]["right"]
    assert not marks(sku, "right")
    assert len(str(right.get("empty", ""))) > 40


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_every_mark_is_an_estimate_with_its_method(sku):
    for view in ("rear", "left"):
        for d in marks(sku, view):
            assert d["confidence"] == "estimated", f"{sku} {view} {d['id']}"
            assert "photograph" in d["source"] and len(d["source"]) > 30


# --- the lamps, the Reset hole and the jacks at the display end of the outlet face -------------------------------
#
# Lamps are placed with the states the guides give and drawn in their off state; the viewer lights them.

GREEN, YELLOW, ORANGE, RED = "#39b54a", "#e5d800", "#f5a623", "#e02020"

# id -> (at, states). The load lamps' colours are the photograph's sample where it holds two pixels or more of
# the colour, else the library's colour for the state.
LOAD = {
    "ap7821b": {
        "lamp-load-ok": ([345.8, 1.4], "normal", "#509049"),
        "lamp-load-warning": ([345.8, 3.9], "near-overload", "#cad314"),
        "lamp-load-overload": ([345.8, 6.4], "overload", "#d92244"),
    },
    "ap7921b": {
        "lamp-load-ok": ([346.9, 2.0], "normal", "#507a3d"),
        "lamp-load-warning": ([346.9, 4.2], "near-overload", YELLOW),
        "lamp-load-overload": ([346.9, 6.4], "overload", RED),
    },
}
JACK_LAMPS = {
    "ap7821b": {"lamp-jack-1": [405.1, 6.1], "lamp-jack-2": [405.1, 15.7]},
    "ap7921b": {"lamp-jack-1": [405.1, 7.5], "lamp-jack-2": [405.1, 16.5]},
}
RESET = {"ap7821b": [322.9, 31.4], "ap7921b": [323.3, 34.5]}
# the guide pages each note cites: front panel, item table, then the LED tables (the Metered guide has the Link and
# Status tables on PDF p.16 and the load table on p.17; the Switched guide on p.14 and p.15)
GUIDE_PAGES = {
    "ap7821b": ("PDF p.11", "PDF p.15", "PDF p.16", "PDF p.17"),
    "ap7921b": ("PDF p.11", "PDF p.13", "PDF p.14", "PDF p.15"),
}

STATUS_STATES = [
    "off",
    {"name": "valid-tcp-ip", "color": GREEN},
    {"name": "invalid-tcp-ip", "color": GREEN, "behavior": "blinking"},
    {"name": "hardware-failure", "color": ORANGE},
    {"name": "bootp-request", "color": ORANGE, "behavior": "blinking"},
    {"name": "dhcp-request", "color": ORANGE, "behavior": {"mode": "alternating", "color": GREEN}},
]
LINK_STATES = [
    "off",
    {"name": "receiving-10m", "color": GREEN, "behavior": "blinking"},
    {"name": "receiving-100m", "color": ORANGE, "behavior": "blinking"},
    {"name": "no-traffic-green", "color": GREEN},
    {"name": "no-traffic-orange", "color": ORANGE},
]


def placements(sku):
    return {p["id"]: p for p in device(sku)["views"]["rear"]["components"]["placements"]}


def lamps(sku):
    return {i: p for i, p in placements(sku).items() if p["ref"] == "common/led-dot@1"}


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_display_end_places_five_lamps_with_their_identities(sku):
    assert sorted(lamps(sku)) == sorted(
        ["lamp-jack-1", "lamp-jack-2", "lamp-load-ok", "lamp-load-warning", "lamp-load-overload"]
    )
    assert "lamp-status" not in placements(sku), "the Status LED is lamp-jack-2"
    for p in lamps(sku).values():
        assert p["group"] == "lamps"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_load_lamps_stand_in_a_column_above_the_display(sku):
    placed = lamps(sku)
    for lamp_id, (at, state, color) in LOAD[sku].items():
        assert placed[lamp_id]["at"] == at, f"{sku} {lamp_id}"
        assert placed[lamp_id]["states"] == ["off", {"name": state, "color": color}], f"{sku} {lamp_id}"
    ys = [placed[i]["at"][1] for i in ("lamp-load-ok", "lamp-load-warning", "lamp-load-overload")]
    assert ys == sorted(ys) and all(y < 10 for y in ys), "above the display window, which starts at 10 mm"
    assert len({placed[i]["at"][0] for i in LOAD[sku]}) == 1, "one column"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_jack_lamps_are_the_link_above_and_the_status_below(sku):
    placed = lamps(sku)
    for lamp_id, at in JACK_LAMPS[sku].items():
        assert placed[lamp_id]["at"] == at, f"{sku} {lamp_id}"
    assert placed["lamp-jack-1"]["at"][1] < placed["lamp-jack-2"]["at"][1]
    assert placed["lamp-jack-1"]["states"] == LINK_STATES
    assert placed["lamp-jack-2"]["states"] == STATUS_STATES


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_every_lamp_is_drawn_off_not_as_decor(sku):
    for p in lamps(sku).values():
        assert p["states"][0] == "off"
    decor = device(sku)["views"]["rear"]["panel"]["decor"]
    assert not [d for d in decor if d.get("kind") in ("lamp", "led")], "a lit lamp is never decor"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_reset_hole_is_a_small_round_hole_left_of_the_display(sku):
    holes = [d for d in device(sku)["views"]["rear"]["panel"]["decor"] if d.get("kind") == "reset-hole"]
    assert len(holes) == 1
    (hole,) = holes
    assert hole["at"] == RESET[sku]
    assert hole["size"] == [2.5, 2.5] and hole["rx"] == 1.25
    assert hole["confidence"] == "estimated" and "photograph" in hole["source"]
    assert hole["at"][0] < placements(sku)["display"]["at"][0]


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_jacks_are_named_from_the_guides_figure(sku):
    placed = placements(sku)
    assert "10/100 Base-T" in placed["jack-1"]["description"] and "item 3" in placed["jack-1"]["description"]
    assert "RJ-12" in placed["jack-2"]["description"] and "item 6" in placed["jack-2"]["description"]
    for jack in ("jack-1", "jack-2"):
        assert placed[jack]["ref"] == "std/rj45@2", "the jack parts are unchanged"
        assert "not stated" not in placed[jack]["description"]
    assert "not stated" not in device(sku)["groups"]["jacks"]["description"]


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_lamp_notes_cite_the_guides_pages_and_the_photograph_samples(sku):
    note = device(sku)["provenance"]["lamps"]["note"]
    assert device(sku)["provenance"]["lamps"]["confidence"] == "estimated"
    for page in GUIDE_PAGES[sku]:
        assert page in note, f"{sku} {page}"
    assert "990-5569E" in note, "the B models' own guide is not held"
    assert "off state" in note
    for color in [c for _, _, c in LOAD[sku].values() if c.startswith("#5") or c.startswith("#c") or c.startswith("#d")]:
        assert color in note, f"{sku} sample {color} is stated"
    assert "count" in note and "mean" in note and "mask" in note


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_no_note_says_a_lamp_cannot_be_drawn_lit(sku):
    text = yaml.safe_dump(device(sku)).lower()
    for phrase in ("cannot be drawn lit", "drawn less", "no field to pick", "lamp-colours"):
        assert phrase not in text, f"{sku}: {phrase}"
    assert "their count, colours and meanings were not read" not in text


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_lamp_and_jack_notes_stay_within_25_words_a_sentence(sku):
    dev = device(sku)
    texts = [dev["provenance"]["lamps"]["note"], dev["provenance"]["jacks"]["note"]]
    texts += [placements(sku)[j]["description"] for j in ("jack-1", "jack-2", "button")]
    texts += [g["note"] for g in dev["gaps"] if g["what"] in ("lamp-marks", "jack-function", "jack-speed")]
    for text in texts:
        for sentence in " ".join(text.split()).replace("? ", ". ").split(". "):
            assert len(sentence.split()) <= 25, sentence

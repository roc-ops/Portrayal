"""Version 2 of the shared lamp parts: the same part, resting unlit grey.

common/led-rect@1 and common/led-rect-sm@1 paint a lamp at rest dark green
(`var(--led-color, #2a6b3f)`), so a lamp a photograph shows dark was drawn
green. A state paints only through its `state-*` class, so nothing on a
placement can change the resting colour: it is the skin's. A wrongly drawn
shared part gets a new version, not a patch (a patch would repaint the resting
lamps of every device that seats v1), so v2 differs from v1 in that one
fallback and v1 is left byte for byte as it was.
"""
import colorsys
import hashlib
import re
from pathlib import Path

import pytest
import yaml

from portrayal import render

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "library/components/common"

# sha256 of the v1 files as they were on main when v2 was added
V1_SHA = {
    "led-rect/v1/contract.yaml": "4c304d7e053f0e32638f0b75fa1617e7e442c496319623ae7e02df7f4968b46f",
    "led-rect/v1/skins/default.svg": "2a0f818d5fdae1145a86ecafdb2bdd5800e09379ded6b0add03ab65235379601",
    "led-rect-sm/v1/contract.yaml": "d6a82b23a4ce52cc3f3255d705480c8ae06e920b38ceaa7548f4a1ea38bd7c9b",
    "led-rect-sm/v1/skins/default.svg": "5725f6f020b08d2210cdbcd89a308fec358f50e78ec07ce56bd9a482d9770067",
    "led-dot/v1/contract.yaml": "086ee0ef7f92e6c51ef9a0a475b2b4afaed253e2eb64c786f537779ebabc5cb1",
    "led-dot/v1/skins/default.svg": "af26d7d037b490678b47c7a7ed580743f2e5567213847a708d703cadf98e59c2",
}
V1_GREEN = "#2a6b3f"
V1_DOT_GREY = "#3a3f44"
REST_GREY = "#3a3938"
RECT_PARTS = ["led-rect", "led-rect-sm"]

# every colour STATE_CSS lights a lamp with, read from the stylesheet itself
LIT = dict(re.findall(r"\.state-([a-z]+)\s*\{\s*--led-color:\s*(#[0-9a-f]{6});", render.STATE_CSS))
FALLBACK = re.compile(r"var\(\s*--led-color\s*,\s*(#[0-9a-fA-F]{6})\s*\)")


def skin(name, major):
    return (COMMON / name / f"v{major}/skins/default.svg").read_text()


def contract(name, major):
    return yaml.safe_load((COMMON / name / f"v{major}/contract.yaml").read_text())


def lamp_fill(svg_text):
    m = re.search(r'<[a-z]+ id="lamp"[^>]*fill="([^"]*)"', svg_text)
    assert m, "no lamp element"
    return m.group(1)


def paint(fill, led_color=None):
    """What a lamp is painted when `--led-color` is `led_color` (None: not set,
    the case dcim_export.rasterize resolves to the fallback)."""
    m = re.fullmatch(r"var\(\s*--led-color\s*,\s*([^)]*)\)", fill)
    assert m, fill
    return led_color or m.group(1).strip()


# --- v1 is as it was -----------------------------------------------------------

@pytest.mark.parametrize("rel", sorted(V1_SHA))
def test_v1_file_is_byte_identical(rel):
    assert hashlib.sha256((COMMON / rel).read_bytes()).hexdigest() == V1_SHA[rel]


@pytest.mark.parametrize("name,hexval", [("led-rect", V1_GREEN), ("led-rect-sm", V1_GREEN),
                                         ("led-dot", V1_DOT_GREY)])
def test_v1_lamp_rests_as_it_did(name, hexval):
    assert lamp_fill(skin(name, 1)) == f"var(--led-color, {hexval})"


# --- v2 rests grey -------------------------------------------------------------

@pytest.mark.parametrize("name", RECT_PARTS)
def test_v2_lamp_rests_in_the_grey_the_contract_declares(name):
    m = FALLBACK.fullmatch(lamp_fill(skin(name, 2)))
    assert m, "the lamp is not painted from var(--led-color, <rest colour>)"
    rest = contract(name, 2)["provenance"]["rest-colour"]
    assert m.group(1).lower() == REST_GREY
    assert REST_GREY in str(rest)
    assert "estimated" in str(rest)
    r, g, b = (int(m.group(1)[i:i + 2], 16) / 255 for i in (1, 3, 5))
    assert colorsys.rgb_to_hsv(r, g, b)[1] < 0.2


# --- v2 differs from v1 in that fallback only ----------------------------------

@pytest.mark.parametrize("name", RECT_PARTS)
def test_v2_skin_is_v1_skin_with_the_new_fallback(name):
    assert skin(name, 2) == skin(name, 1).replace(V1_GREEN, REST_GREY)
    assert V1_GREEN not in skin(name, 2)


@pytest.mark.parametrize("name", RECT_PARTS)
def test_v2_contract_differs_from_v1_in_the_declared_keys_only(name):
    v1, v2 = contract(name, 1), contract(name, 2)
    assert v2["version"] == "2.0.0"
    assert v2["unplaced"]
    assert "rest" in v2["description"] and "grey" in v2["description"]
    p1, p2 = dict(v1["provenance"]), dict(v2["provenance"])
    assert p2.pop("rest-colour")
    assert p2 == p1, "v1's provenance entries are carried unchanged"
    for doc in (v1, v2):
        for key in ("version", "description", "provenance", "unplaced"):
            doc.pop(key, None)
    # v1 states no size confidence; v2 states it (lint L97) beside the unchanged size
    if "size-confidence" not in v1:
        assert v2.pop("size-confidence") == {"w": "estimated", "h": "estimated"}
        assert v2.pop("size-notes")
    f1, f2 = v1["relief"]["features"], v2["relief"]["features"]
    assert [{k: v for k, v in f.items() if k != "source"} for f in f2] == \
           [{k: v for k, v in f.items() if k != "source"} for f in f1]
    assert all(f["confidence"] == "estimated" and f["source"] for f in f2)
    for doc in (v1, v2):
        doc["relief"]["features"] = []
    assert v2 == v1


@pytest.mark.parametrize("name", RECT_PARTS)
def test_v2_relief_dome_is_v1s(name):
    assert [f["dome"] for f in contract(name, 2)["relief"]["features"]] == \
           [f["dome"] for f in contract(name, 1)["relief"]["features"]]


# --- every lit colour is v1's --------------------------------------------------

def test_the_stylesheet_lights_lamps_in_the_colours_this_pins():
    assert set(LIT) >= {"on", "up", "link", "activity", "ok", "fault", "fail", "locate"}


@pytest.mark.parametrize("name", RECT_PARTS)
def test_v2_lamp_lights_in_the_same_paint_as_v1_and_rests_differently(name):
    f1, f2 = lamp_fill(skin(name, 1)), lamp_fill(skin(name, 2))
    for state, colour in LIT.items():
        assert paint(f2, colour) == paint(f1, colour) == colour, state
    assert paint(f2) != paint(f1)


# --- through the renderer --------------------------------------------------------

STATES = [{"name": "on", "color": "#22c55e"},
          {"name": "fault", "color": "#f59e0b", "behavior": "blinking"},
          {"name": "off"}]


def render_lamp(ref):
    lamp = {"id": "lamp-1", "ref": ref, "at": [10, 10], "states": STATES}
    doc = {"format": 1, "kind": "device", "name": "p", "version": "1.0.0",
           "manufacturer": "Acme", "model": "P1", "profile": "networking", "maturity": "modelled",
           "chassis": {"width": 60, "height": 44, "depth": 100, "ru": 1, "mount": "rack-side"},
           "views": {"front": {"size": {"w": 60, "h": 44},
                               "components": {"placements": [lamp]}}}}
    svg = render.render_view(doc, "front", doc["views"]["front"],
                             render.Library([ROOT / "library"]))
    fills = [n.get("fill") for n in svg.iter() if (n.get("id") or "").endswith("--lamp")]
    style = svg.find(f"{{{render.SVG_NS}}}style").text
    rules = [ln.strip() for ln in style.splitlines() if "lamp-1" in ln or "led-rect" in ln]
    return fills, [re.sub(r"led-rect(-sm)?@\d", "REF", r) for r in rules]


@pytest.mark.parametrize("name,rest_v1", [("led-rect", V1_GREEN), ("led-rect-sm", V1_GREEN)])
def test_a_rendered_v2_lamp_rests_grey_and_lights_as_v1_does(name, rest_v1):
    fills1, rules1 = render_lamp(f"common/{name}@1")
    fills2, rules2 = render_lamp(f"common/{name}@2")
    assert fills1 == [f"var(--led-color, {rest_v1})"]
    assert fills2 == [f"var(--led-color, {REST_GREY})"]
    assert rules1, "no state rules were written for the lamp"
    assert rules2 == rules1
    assert any("#22c55e" in r for r in rules2) and any("#f59e0b" in r for r in rules2)


# --- led-dot keeps its grey ------------------------------------------------------

def test_the_rest_colour_note_states_the_led_dot_grey_it_is_set_beside():
    for name in RECT_PARTS:
        note = str(contract(name, 2)["provenance"]["rest-colour"])
        assert "led-dot" in note and V1_DOT_GREY in note

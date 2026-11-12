"""The door of a single-sided Chatsworth Motive vertical cable manager draws what the maker's pictures show.

The data sheet's page 1 photograph shows the front door in three panels with a silver plate down its upper
part, with a white block at its top that carries the maker's mark. The installation instructions
(page 3) say the door has two blue latches on its back and draw them on the door seen from inside.
These tests hold, for the ten parts (32610 to 32614, each in -703 and -E03):

- the door component draws the two seams and the plate, reserves the mark's place without painting it,
  and declares them as elements;
- the plate is the same fraction of the door's width on every width, centred, and the same height down
  the door;
- the device draws the latches on its rear, left and right faces, and keeps one gap for the hook, which
  no held picture shows.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
HEIGHT = 2133.6
WIDTHS = {0: 150.0, 1: 200.0, 2: 250.0, 3: 300.0, 4: 380.0}
PARTS = [f"3261{w}-{c}" for w in WIDTHS for c in ("703", "e03")]
SKIN_IDS = {"seam-left", "seam-right", "door-plate", "logo-zone", "latch-tip-left", "latch-tip-right"}


def width(part):
    return WIDTHS[int(part[4])]


def door_dir(part):
    return LIB / "components" / "chatsworth" / f"motive-{part}-door" / "v1"


def door(part):
    return yaml.safe_load((door_dir(part) / "contract.yaml").read_text())


def skin_rects(part):
    text = (door_dir(part) / "skins" / "default.svg").read_text()
    out = {}
    for m in re.finditer(r"<(rect|path) id=\"([^\"]+)\"([^>]*)>", text):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(3)))
        out[m.group(2)] = attrs
    return out


def device(part):
    return yaml.safe_load((LIB / "devices" / "chatsworth" / part / "device.yaml").read_text())


def decor(doc, view):
    return {d["id"]: d for d in doc["views"][view]["panel"]["decor"]}


@pytest.mark.parametrize("part", PARTS)
def test_the_door_skin_draws_the_seams_and_the_plate_and_reserves_the_logo_zone(part):
    rects = skin_rects(part)
    assert SKIN_IDS <= set(rects)
    w = width(part)
    plate = rects["door-plate"]
    zone = rects["logo-zone"]
    assert zone["fill"] == "none" and "stroke" not in zone, "the maker's mark is reserved, never painted"
    assert zone["x"] == plate["x"] and zone["y"] == plate["y"], "the reserved block is at the plate's top"
    assert float(plate["width"]) == pytest.approx(0.49 * w, abs=0.06)
    assert float(plate["x"]) + float(plate["width"]) / 2 == pytest.approx(w / 2, abs=0.1), "the plate is centred"
    assert float(plate["y"]) == pytest.approx(378, abs=1) and float(plate["height"]) == pytest.approx(738, abs=1)
    for seam in ("seam-left", "seam-right"):
        x = float(rects[seam]["x"]) + float(rects[seam]["width"]) / 2
        assert x in (pytest.approx(0.21 * w, abs=0.1), pytest.approx(0.79 * w, abs=0.1))


@pytest.mark.parametrize("part", PARTS)
def test_the_door_contract_declares_the_plate_and_the_seams(part):
    doc = door(part)
    assert {"plate", "seam-left", "seam-right", "door-plate", "logo-zone", "latch-tip-left", "latch-tip-right"} <= set(doc["elements"])
    assert doc["size"]["w"] == width(part)
    for key in ("logo-zone", "seams", "latches", "hook"):
        assert key in doc["provenance"]
    assert "estimated" in doc["provenance"]["logo-zone"]


@pytest.mark.parametrize("part", PARTS)
def test_the_latches_are_drawn_where_the_back_of_the_door_is_seen(part):
    doc = device(part)
    rear = decor(doc, "rear")
    w = width(part)
    for side in ("left", "right"):
        housing, handle = rear[f"latch-{side}-housing"], rear[f"latch-{side}-handle"]
        centre = housing["at"][1] + housing["size"][1] / 2
        assert centre == pytest.approx(0.473 * HEIGHT, abs=2)
        assert handle["rx"] > 0, "a handle is a round part"
        edge = housing["at"][0] + housing["size"][0] if side == "left" else w - housing["at"][0]
        assert edge <= w / 2, "each latch sits at its own side edge"
    assert rear["latch-left-housing"]["at"][0] + rear["latch-right-housing"]["at"][0] + 17 == pytest.approx(w, abs=0.1)
    for view in ("left", "right"):
        assert {"latch-housing", "latch-handle"} <= set(decor(doc, view))


@pytest.mark.parametrize("part", PARTS)
def test_the_gaps_keep_only_the_hook(part):
    gaps = {g["what"]: g for g in device(part)["gaps"]}
    assert "door-features" not in gaps
    assert gaps["door-hook"]["scope"] == ["rear"]
    assert "no held picture shows it" in gaps["door-hook"]["note"]

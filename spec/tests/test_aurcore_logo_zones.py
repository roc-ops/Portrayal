"""AurCore: the printed mark's place is reserved on each front, and nothing is drawn.

Each switch's front carries a `logo-zone` region where the maker prints its
logotype, read off a square-on product photograph. The text AURCORE stays: it
is the plain wordmark the library draws. A face whose mark could not be
measured has no region, and is listed in LEFT_OUT so a later change sees it.
"""
import pathlib

import yaml

from portrayal import lint as L
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "aurcore"

FRONTS = ("ais2001", "ais2001p", "ais2002", "ais2002p", "ais2003", "ais2003p",
          "ais2004", "ais2004p", "ais4001", "ais4001p")

# (device, view): the finned right side of the AIS2001P is shown only in a
# three-quarter photograph, which gives no scale on that plane.
LEFT_OUT = (("ais2001p", "right"),)


def device(slug):
    return yaml.safe_load((DEVICES / slug / "device.yaml").read_text())


def zones(slug, view):
    return [r for r in (device(slug)["views"][view].get("regions") or [])
            if str(r.get("id", "")).startswith("logo-zone")]


@pytest.mark.parametrize("slug", FRONTS)
def test_the_front_reserves_one_logo_zone_inside_the_face(slug):
    view = device(slug)["views"]["front"]
    found = zones(slug, "front")
    assert len(found) == 1 and found[0]["id"] == "logo-zone", found
    zone = found[0]
    x, y = zone["at"]
    w, h = zone["size"]["w"], zone["size"]["h"]
    assert w > 0 and h > 0
    assert 0 <= x and 0 <= y and x + w <= view["size"]["w"] and y + h <= view["size"]["h"]
    assert "not drawn" in zone["label"]


@pytest.mark.parametrize("slug", FRONTS)
def test_the_zone_passes_the_logo_zone_rule(slug):
    with L.collecting() as found:
        L.lint_device_logo_zone(slug, device(slug))
    assert not [e for e in found.errors if "L172" in e]


@pytest.mark.parametrize("slug", FRONTS)
def test_the_plain_wordmark_is_still_drawn_on_the_front(slug):
    texts = [s.get("text") for s in device(slug)["views"]["front"].get("silkscreen") or []]
    assert "AURCORE" in texts


@pytest.mark.parametrize("slug", FRONTS)
def test_the_note_says_the_mark_is_reserved_and_the_text_is_the_wordmark(slug):
    note = device(slug)["provenance"]["silkscreen"]["note"]
    assert "logo-zone" in note and "not drawn" in note and "AURCORE" in note


@pytest.mark.parametrize("slug,view", LEFT_OUT)
def test_a_face_that_could_not_be_measured_has_no_zone(slug, view):
    assert zones(slug, view) == []

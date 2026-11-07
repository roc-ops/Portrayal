"""dell/ndc-4x-rj45-14g prints its two speed labels, and prints them turned.

Dell's faceplate lettering says "10Gb" between the first and second jacks and
"1Gb" between the third and fourth, reading bottom to top (#355). The labels
are what #287 read the four ports' speeds from, so the drawing has to carry
them, or the render shows less than the model claims.

The positions are measured off Dell's `2x10gb-bt-2x1gb-ndc` master (glyph
subpath boxes, 0.19843 mm per master unit): the "10Gb" ink is centred at card
x 21.7 and the "1Gb" ink at 65.8, each within 0.2 mm of its pair's midpoint, and
both at the plate's mid-height, 7.25.

READS THE BUILT DRAWING, so it skips with no `library/dist` (as every dist test
does) and fails if a build is present without the labels.
"""
import re
import xml.etree.ElementTree as ET

import pytest

import libdata

NS = "{http://www.w3.org/2000/svg}"
PLATE = (90.3, 14.5)
MID_Y = PLATE[1] / 2
# label -> (ink centre x, the two jacks' edges that bound its gap)
LABELS = {"10Gb": (21.7, 18.37, 24.77), "1Gb": (65.8, 62.77, 69.17)}
CAP = 0.36    # half a capital's height, in em: the ink sits this far left of the baseline at -90


def _silkscreen_text():
    root = ET.parse(libdata.built_component("dell/ndc-4x-rj45-14g")).getroot()
    found = {}

    def walk(el, inside):
        inside = inside or (el.get("id") or "").endswith("silkscreen")
        for ch in el:
            if ch.tag == NS + "text" and inside:
                found["".join(ch.itertext()).strip()] = ch
            walk(ch, inside)
    walk(root, False)
    return found


@pytest.mark.parametrize("label", LABELS)
def test_the_label_is_printed_in_the_silkscreen_group(label):
    assert label in _silkscreen_text(), (
        f"the NDC's silkscreen carries no {label!r}; Dell prints it on the faceplate")


@pytest.mark.parametrize("label", LABELS)
def test_the_label_reads_bottom_to_top_about_its_own_anchor(label):
    el = _silkscreen_text()[label]
    got = re.fullmatch(r"rotate\((\S+) (\S+) (\S+)\)", el.get("transform") or "")
    assert got, f"{label!r} is turned with rotate(deg x y): {el.get('transform')!r}"
    deg, px, py = map(float, got.groups())
    assert deg == -90, "bottom to top is spelled -90 for new work"
    assert (px, py) == (float(el.get("x")), float(el.get("y"))), "the pivot is the text's own x y"
    assert el.get("text-anchor") == "middle"


@pytest.mark.parametrize("label", LABELS)
def test_the_label_is_centred_in_its_gap_and_on_the_plate(label):
    centre_x, left_jack, right_jack = LABELS[label]
    el = _silkscreen_text()[label]
    fs = float(el.get("font-size"))
    x, y = float(el.get("x")), float(el.get("y"))
    ink_x = x - CAP * fs
    assert ink_x == pytest.approx(centre_x, abs=0.2), (
        f"{label!r}: ink centre x {ink_x:.2f}, measured {centre_x} on the master")
    assert y == pytest.approx(MID_Y, abs=0.2), "centred on the plate's mid-height"
    # the rotated box: caps run 0.72 em left of the baseline, the word runs 0.6 em a letter
    half_run = 0.6 * fs * len(label) / 2
    box = (x - 0.72 * fs, y - half_run, x, y + half_run)
    assert left_jack < box[0] and box[2] < right_jack, "inside the gap between the two jacks"
    assert 0 <= box[1] and box[3] <= PLATE[1], "inside the card's outline"

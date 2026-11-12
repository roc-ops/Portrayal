"""Middle Atlantic LBP-1A, the 19 in L-shaped lacing bar (roc-ops/Portrayal#1102).

The source for the part is the maker's generated cut sheet for LBP-1A and its SKU page.
They give the size (19 in wide, 0.5 in deep, 0.5 in high), two mounting points, no offset and packs of 10.
Neither gives a drawing of the bar or a weight for one. The overall size is the maker's.
The row of slots and the ear with its hole at each end are read off the maker's small photograph.
Every position and size for them is estimated, and the gaps that a dimensioned drawing would settle are named.
What is true of the library is held here.
The size is the maker's, the drawn features lie inside the bar, and the figures read from the photograph say they are estimates.

The size and drawing tests read only the device file.
The catalogue test reads the build (`library/dist`) and skips without it, like the other sweeps over compiled drawings.
"""
import json
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
MM = 25.4
NAME = "lbp-1a"

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")


def device():
    return yaml.safe_load((LIB / "devices" / "middle-atlantic" / NAME / "device.yaml").read_text())


def close(a, b, tol=0.01):
    return abs(a - b) <= tol


def test_middle_atlantic_is_a_hardware_vendor_with_its_source_named():
    vendors = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    v = vendors["middle-atlantic"]
    assert v["role"] == "hardware" and v["display"] == "Middle Atlantic"
    assert "cut sheet" in v["source"] and "LBP-1A" in v["source"]


def test_the_envelope_is_the_cut_sheets_and_the_bar_bolts_to_the_rail_face():
    doc = device()
    c = doc["chassis"]
    assert doc["manufacturer"] == "Middle Atlantic" and doc["model"] == "LBP-1A"
    assert c["width"] == 482.6, "19 in, the bar's own length"
    assert close(c["height"], 0.5 * MM) and close(c["depth"], 0.5 * MM)
    assert c["ru"] == 1 and c["mount"] == "rack-face" and c["shell"] == "sheet"
    phys = doc["attrs"]["physical"]
    assert phys["material"] == "Steel" and phys["finish"] == "Black Powder Coat" and phys["color"] == "Black"
    assert doc["datasheet"]["url"].endswith("/lbp_horizontal_lacer_bar/LBP-1A")
    assert len(doc["datasheet"]["sha256"]) == 64


def test_the_weight_is_a_named_gap_with_the_document_it_needs():
    gaps = {g["what"]: g for g in device()["gaps"]}
    assert "weight" in gaps
    assert gaps["weight"]["wanted"]


def decor(view, kind):
    return [d for d in device()["views"][view]["panel"]["decor"] if d.get("kind") == kind]


@pytest.mark.parametrize("view", ["front", "rear", "top", "bottom", "left", "right"])
def test_each_side_keeps_the_overall_size_and_every_drawn_feature_lies_inside_it(view):
    v = device()["views"][view]
    w, h = v["size"]["w"], v["size"]["h"]
    assert (w, h) in ((482.6, 12.7), (12.7, 12.7))
    for d in v["panel"]["decor"]:
        x, y = d["at"]
        dw, dh = d["size"]
        assert x >= 0 and y >= 0 and x + dw <= w + 1e-6 and y + dh <= h + 1e-6, d["id"]


@pytest.mark.parametrize("view", ["front", "rear", "top", "bottom"])
def test_the_bar_draws_ten_evenly_spaced_slots_between_its_ends(view):
    slots = sorted(decor(view, "tie-slot"), key=lambda d: d["at"][0])
    assert len(slots) == 10
    xs = [d["at"][0] for d in slots]
    pitches = {round(b - a, 3) for a, b in zip(xs, xs[1:])}
    assert len(pitches) == 1 and pitches.pop() > slots[0]["size"][0], "evenly spaced, with a web between slots"
    assert close(xs[0], 482.6 - (xs[-1] + slots[-1]["size"][0]), 1.0), "the row is centred on the bar"
    assert len({tuple(d["size"]) for d in slots}) == 1 and len({d["at"][1] for d in slots}) == 1


def test_the_slots_of_the_web_and_of_the_leg_sit_at_the_same_places_along_the_bar():
    front = [d["at"][0] for d in decor("front", "tie-slot")]
    assert len(front) == 10
    for view in ("rear", "top", "bottom"):
        assert [d["at"][0] for d in decor(view, "tie-slot")] == front


@pytest.mark.parametrize("view", ["front", "rear", "top", "bottom"])
def test_each_end_has_an_ear_that_reaches_the_end_of_the_bar_and_the_web_starts_where_it_stops(view):
    ears = sorted(decor(view, "ear"), key=lambda d: d["at"][0])
    assert len(ears) == 2
    left, right = ears
    assert left["at"][0] == 0 and close(right["at"][0] + right["size"][0], 482.6)
    assert close(left["size"][0], right["size"][0])
    body = [d for d in device()["views"][view]["panel"]["decor"] if d["kind"] == "base"]
    assert len(body) == 1
    assert close(body[0]["at"][0], left["size"][0]) and close(body[0]["at"][0] + body[0]["size"][0], right["at"][0])


@pytest.mark.parametrize("view", ["top", "bottom"])
def test_each_ear_carries_one_hole_inside_it(view):
    ears = sorted(decor(view, "ear"), key=lambda d: d["at"][0])
    holes = sorted(decor(view, "ear-hole"), key=lambda d: d["at"][0])
    assert len(holes) == 2
    for ear, hole in zip(ears, holes):
        assert ear["at"][0] <= hole["at"][0] and hole["at"][0] + hole["size"][0] <= ear["at"][0] + ear["size"][0]
        assert ear["at"][1] <= hole["at"][1] and hole["at"][1] + hole["size"][1] <= ear["at"][1] + ear["size"][1]
    assert close(holes[0]["at"][0], 482.6 - (holes[1]["at"][0] + holes[1]["size"][0])), "the two ends are alike"


@pytest.mark.parametrize("view", ["top", "bottom"])
def test_each_ear_hole_sits_near_its_end_of_the_bar_within_the_ears_length(view):
    ears = sorted(decor(view, "ear"), key=lambda d: d["at"][0])
    holes = sorted(decor(view, "ear-hole"), key=lambda d: d["at"][0])
    ear_length = ears[0]["size"][0]
    left, right = holes
    assert left["at"][0] + left["size"][0] <= ear_length, "the left hole ends within the ear's length of the left end"
    assert 482.6 - right["at"][0] <= ear_length, "the right hole starts within the ear's length of the right end"
    for hole in holes:
        assert hole["size"][0] > hole["size"][1] > 0, "an obround hole, longer along the bar than across"


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if s]


def prose(doc):
    yield "description", doc["description"]
    for key, entry in doc["provenance"].items():
        yield f"provenance.{key}", entry["note"]
    for gap in doc["gaps"]:
        yield f"gap.{gap['what']}", gap["note"]


def test_every_sentence_of_the_notes_gaps_and_description_is_short():
    longest = max(
        (len(s.split()), where)
        for where, text in prose(device())
        for s in sentences(text)
    )
    assert longest[0] <= 25, longest


@pytest.mark.parametrize("view", ["left", "right"])
def test_each_end_draws_the_section_as_a_web_and_a_leg(view):
    parts = {d["id"]: d for d in device()["views"][view]["panel"]["decor"]}
    assert set(parts) == {"web", "leg"}
    assert parts["web"]["size"][1] == 12.7 and parts["leg"]["size"][0] == 12.7
    assert parts["web"]["size"][0] == parts["leg"]["size"][1]


def test_the_figures_read_from_the_photograph_say_they_are_estimates():
    prov = device()["provenance"]
    for key in ("slots", "ears", "left", "front", "top"):
        assert prov[key]["confidence"] == "estimated"
        assert "estimated" in prov[key]["note"]


def test_the_figures_the_cut_sheet_does_not_give_are_named_gaps_with_the_document_each_needs():
    gaps = {g["what"]: g for g in device()["gaps"]}
    assert {"tie-points", "end-holes", "cross-section", "height-in-unit", "weight", "mounting-hardware"} <= set(gaps)
    for g in gaps.values():
        assert g["wanted"] and g["note"]


def test_the_colour_note_states_how_the_colour_was_read():
    note = device()["provenance"]["color"]["note"]
    assert re.search(r"\d+ dark pixels|sampled", note), note
    assert re.search(r"#[0-9a-f]{6}|RGB \d+, \d+, \d+", note), "the sampled value is stated"


@pytest.mark.heavy
@needs_dist
def test_the_build_carries_the_envelope_to_the_rack_catalogue():
    r = json.loads((DIST / "rack.json").read_text())["devices"][NAME]
    assert (r["ru"], r["w"], r["mount"]) == (1, 482.6, "rack-face")
    assert close(r["d"], 12.7) and close(r["h"], 12.7)

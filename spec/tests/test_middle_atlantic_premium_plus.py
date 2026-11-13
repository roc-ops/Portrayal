"""Middle Atlantic Premium+ rackmount PDUs with RackLink (roc-ops/Portrayal#1480).

The sources are the maker's specification sheet 190174 and the Premium+ user manual.
The sheet prints the size, the table of inlets and breakers, and elevations of both faces.
The manual names the outlet type, the lamps and the ports.
What is true of the library is held here.
The printed size, the nine outlets and which of them switch are checked.
So are the inlet and outlet of each model, every port the sheet labels, and all six sides drawn.
The tests read only the device files.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "middle-atlantic"

MODELS = {
    "rlnk-p915r": ("std/c14-inlet@1", "std/nema-5-15r@1", 15),
    "rlnk-p920r": ("std/c20-inlet@1", "std/nema-5-20r@1", 20),
    "rlnk-p915r-sp": ("std/c14-inlet@1", "std/nema-5-15r@1", 15),
    "rlnk-p920r-sp": ("std/c20-inlet@1", "std/nema-5-20r@1", 20),
}
PORTS = ["eth-1", "eth-2", "usb-a-1", "usb-a-2", "usb-b", "feature", "console", "expansion", "sensor"]
# Rated load stored, the sheet's full load input current, and the pages that print them.
CURRENTS = {
    "rlnk-p915r": (12, 15, "p.3", "p.234"),
    "rlnk-p920r": (16, 20, "p.3", "p.234"),
    "rlnk-p915r-sp": (12, 15, "p.4", "p.236"),
    "rlnk-p920r-sp": (16, 20, "p.4", "p.236"),
}


def device(slug):
    return yaml.safe_load((DEVICES / slug / "device.yaml").read_text())


def placements(dev, view):
    return {p["id"]: p for p in dev["views"][view]["components"]["placements"]}


@pytest.mark.parametrize("slug", MODELS)
def test_the_size_is_the_sheets_printed_body(slug):
    chassis = device(slug)["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"], chassis["ru"]) == (441, 44, 250, 1)


@pytest.mark.parametrize("slug", MODELS)
def test_nine_outlets_of_the_models_type_and_eight_switch(slug):
    inlet, outlet, _ = MODELS[slug]
    dev = device(slug)
    rear, front = placements(dev, "rear"), placements(dev, "front")
    outs = [p for p in list(rear.values()) + list(front.values()) if p["ref"] == outlet]
    assert len(outs) == 9
    assert sorted(rear[f"outlet-{n}"]["states"] == ["on", "off"] for n in range(1, 9)) == [True] * 8
    assert "states" not in front["outlet-9"]
    assert rear["input"]["ref"] == inlet


@pytest.mark.parametrize("slug", MODELS)
def test_every_port_the_sheet_labels_is_placed_on_the_rear(slug):
    rear = placements(device(slug), "rear")
    for port in PORTS:
        assert port in rear, port
    assert rear["console"]["attrs"]["role"] == "console"


@pytest.mark.parametrize("slug", MODELS)
def test_each_outlet_lamp_is_drawn_off_with_the_manuals_states(slug):
    rear = placements(device(slug), "rear")
    for n in range(1, 9):
        lamp = rear[f"lamp-{n}"]
        assert lamp["for"] == f"outlet-{n}"
        assert lamp["states"][0] == "off"
        assert len(lamp["states"]) == 4


@pytest.mark.parametrize("slug", MODELS)
def test_all_six_sides_are_drawn_none_is_declared_empty(slug):
    views = device(slug)["views"]
    assert sorted(views) == ["bottom", "front", "left", "rear", "right", "top"]
    for name, view in views.items():
        assert "empty" not in view, name


@pytest.mark.parametrize("slug", MODELS)
def test_the_lamps_are_the_sheets_rectangles_and_the_screws_are_crossed(slug):
    rear = placements(device(slug), "rear")
    for n in range(1, 9):
        assert rear[f"lamp-{n}"]["ref"] == "common/led-rect@2"
    for name in ("inlet-screw-1", "inlet-screw-2"):
        assert rear[name]["ref"] == "common/screw-head@1"


def gaps(slug):
    return {g["what"]: g for g in device(slug)["gaps"]}


@pytest.mark.parametrize("slug", MODELS)
def test_ear_holes_edge_tabs_and_printed_marks_are_gaps(slug):
    found = gaps(slug)
    assert found["ear-holes-and-tabs"]["scope"] == ["front", "rear"]
    assert found["printed-marks"]["scope"] == ["front", "rear"]
    assert "later touch" in found["printed-marks"]["note"]
    note = found["ear-holes-and-tabs"]["note"]
    assert "rack-face width" in note
    assert "9.5 by 6.35" in note
    assert "nothing could stand outside them" not in note


@pytest.mark.parametrize("slug", MODELS)
def test_the_notes_count_the_rear_ears_and_give_one_reason_for_the_marks(slug):
    notes = device(slug)["provenance"]
    ears = notes["ears"]["note"]
    assert "rear elevation" in ears
    assert "21 mm" in ears
    left_out = notes["left-out"]["note"]
    assert "153 by 52" in left_out
    assert "too small" not in left_out
    assert "later touch" in left_out


@pytest.mark.parametrize("slug", MODELS)
def test_the_notes_place_the_tabs_and_the_clip_where_the_sheet_shows_them(slug):
    left_out = device(slug)["provenance"]["left-out"]["note"]
    assert "under outlet 2." in left_out
    assert "outlets 2 and 3" not in left_out
    assert "front, rear and end views" in left_out


@pytest.mark.parametrize("slug", MODELS)
def test_only_the_sp_models_record_the_certification_disagreement(slug):
    found = gaps(slug)
    if slug.endswith("-sp"):
        assert found["certifications"]["reason"] == "sources-disagree"
        assert "UL 62368" in found["certifications"]["note"]
    else:
        assert "certifications" not in found


@pytest.mark.parametrize("slug", MODELS)
def test_the_input_note_says_which_current_it_states(slug):
    note = device(slug)["provenance"]["input"]["note"]
    assert "derated" in note
    assert "gaps: input-current" in note


@pytest.mark.parametrize("slug", MODELS)
def test_the_stored_input_current_is_the_derated_rated_load(slug):
    rated, _, _, _ = CURRENTS[slug]
    assert device(slug)["attrs"]["power"]["input-current-a"] == rated


@pytest.mark.parametrize("slug", MODELS)
def test_the_sheets_full_load_input_current_is_a_sources_disagree_gap(slug):
    rated, full, sheet_page, manual_page = CURRENTS[slug]
    gap = gaps(slug)["input-current"]
    assert gap["reason"] == "sources-disagree"
    assert gap["scope"] == []
    note = gap["note"]
    assert f"specification sheet 190174 {sheet_page}" in note
    assert f"user manual I-00826 {manual_page}" in note
    assert f"as {full} A" in note
    assert f"as {rated} A" in note
    assert "derated" in note


def decor(slug, view):
    return {d["id"]: d for d in device(slug)["views"][view]["panel"]["decor"]}


REAR_EDGE = ["rear-outlet-top-%d" % n for n in range(1, 9)] + [
    "rear-part-top-1", "rear-part-top-2", "rear-part-top-3", "front-flange-top"]


@pytest.mark.parametrize("slug", MODELS)
def test_the_top_draws_the_rear_edge_parts_and_the_front_flange(slug):
    top = decor(slug, "top")
    for name in REAR_EDGE:
        assert name in top, name
    assert "top-tab-hole" in top


@pytest.mark.parametrize("slug", MODELS)
@pytest.mark.parametrize("view,size", [("top", (441, 250)), ("bottom", (441, 250)), ("left", (250, 44)), ("right", (250, 44))])
def test_every_decor_of_a_side_stays_inside_its_view(slug, view, size):
    for name, d in decor(slug, view).items():
        x, y = d["at"]
        w, h = d["size"]
        assert x >= -0.01 and y >= -0.01, name
        assert x + w <= size[0] + 0.01 and y + h <= size[1] + 0.01, name


@pytest.mark.parametrize("slug", MODELS)
def test_the_bottom_mirrors_left_and_right_only(slug):
    top, bottom = decor(slug, "top"), decor(slug, "bottom")
    for name in REAR_EDGE:
        t, b = top[name], bottom[name]
        assert abs(t["at"][0] + t["size"][0] - (441 - b["at"][0])) < 0.3, name
        assert t["at"][1] == b["at"][1], name
    assert "bottom-tab-hole" in bottom


@pytest.mark.parametrize("slug", MODELS)
def test_the_end_views_run_their_depth_as_the_pitfalls_say(slug):
    left, right = decor(slug, "left"), decor(slug, "right")
    assert left["side-hole-1"]["at"][0] < 30 and right["side-hole-1"]["at"][0] > 200
    assert left["side-hole-4"]["at"][0] > 200 and right["side-hole-4"]["at"][0] < 40
    assert "inlet-housing-side" in left
    assert "front-bracket-plate-side" in left and "front-bracket-plate-side" in right
    for n in range(1, 5):
        assert "rear-plate-side-%d" % n in right


@pytest.mark.parametrize("slug", MODELS)
def test_the_logo_is_a_reserved_region_on_the_touch_strip(slug):
    regions = {r["id"]: r for r in device(slug)["views"]["front"]["regions"]}
    zone = regions["logo-zone"]
    x, y = zone["at"]
    assert 144 < x and x + zone["size"]["w"] < 382
    assert 15 < y and y + zone["size"]["h"] < 29
    assert 18 < zone["size"]["w"] < 20 and 6 < zone["size"]["h"] < 7


@pytest.mark.parametrize("slug", MODELS)
def test_the_breaker_rating_is_the_models(slug):
    _, _, amps = MODELS[slug]
    assert placements(device(slug), "rear")["breaker"]["attrs"]["rating-a"] == amps

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
    assert "nothing could stand outside them" in found["ear-holes-and-tabs"]["note"]


@pytest.mark.parametrize("slug", MODELS)
def test_the_notes_count_the_rear_ears_and_give_one_reason_for_the_marks(slug):
    notes = device(slug)["provenance"]
    assert "rear elevation" in notes["ears"]["note"]
    left_out = notes["left-out"]["note"]
    assert "153 by 52" in left_out
    assert "too small" not in left_out
    assert "later touch" in left_out


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
    assert "rated load" in note
    assert "maximum" in note


@pytest.mark.parametrize("slug", MODELS)
def test_the_breaker_rating_is_the_models(slug):
    _, _, amps = MODELS[slug]
    assert placements(device(slug), "rear")["breaker"]["attrs"]["rating-a"] == amps

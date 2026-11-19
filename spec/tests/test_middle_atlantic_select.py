"""Middle Atlantic Select Series rackmount PDUs with RackLink, RLNK-915R and RLNK-920R (roc-ops/Portrayal#1480).

The sources are the maker's specification sheet 96-01237 and the Select Series user manual.
The sheet prints the size and elevations of both faces, and the table of models.
The manual names the inlet, the outlets, the lamps and the ports.
What is true of the library is held here.
The printed size, the nine outlets and which of them are controlled are checked.
So are the inlet and outlet of each model, every port the sheet labels, and all six sides drawn.
The tests read only the device files.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "middle-atlantic"

MODELS = {
    "rlnk-915r": ("std/c14-inlet@1", "std/nema-5-15r@1", 12),
    "rlnk-920r": ("std/c20-inlet@1", "std/nema-5-20r@1", 16),
}


def device(slug):
    return yaml.safe_load((DEVICES / slug / "device.yaml").read_text())


def placements(dev, view):
    return {p["id"]: p for p in dev["views"][view]["components"]["placements"]}


def decor(dev, view):
    return dev["views"][view]["panel"]["decor"]


@pytest.mark.parametrize("slug", MODELS)
def test_the_size_is_the_sheets_printed_body(slug):
    chassis = device(slug)["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"], chassis["ru"]) == (441, 44.1, 245.7, 1)


@pytest.mark.parametrize("slug", MODELS)
def test_nine_outlets_of_the_models_type_and_eight_are_controlled(slug):
    inlet, outlet, rated = MODELS[slug]
    dev = device(slug)
    rear, front = placements(dev, "rear"), placements(dev, "front")
    outs = [p for p in list(rear.values()) + list(front.values()) if p["ref"] == outlet]
    assert len(outs) == 9
    assert all(rear[f"outlet-{n}"]["states"] == ["on", "off"] for n in range(1, 9))
    assert "states" not in front["outlet-9"]
    assert rear["input"]["ref"] == inlet
    assert dev["attrs"]["power"]["input-current-a"] == rated
    assert dev["attrs"]["management"]["outlet-count"] == 9


@pytest.mark.parametrize("slug", MODELS)
def test_the_rear_holds_the_reset_button_and_the_one_ethernet_jack(slug):
    rear = placements(device(slug), "rear")
    assert rear["reset"]["ref"] == "common/reset-button@1"
    assert rear["eth"]["ref"] == "common/rj45-eth@1"
    assert rear["eth"]["attrs"]["speed"] == "100m"
    assert sorted(i for i in rear if i.startswith("eth")) == ["eth", "eth-mark"]
    assert rear["eth-mark"]["ref"] == "common/nic-symbol@1"
    assert rear["ground-mark"]["ref"] == "common/ground-symbol@1"


@pytest.mark.parametrize("slug", MODELS)
def test_the_front_holds_an_alert_lamp_eight_outlet_lamps_and_the_switch(slug):
    front = placements(device(slug), "front")
    lamps = [p for p in front.values() if p["ref"] == "common/led-indicator@1"]
    assert len(lamps) == 9
    for lamp in lamps:
        assert lamp["states"][0] == "off"
    for n in range(1, 9):
        assert f"outlet {n} " in front[f"lamp-{n}"]["description"]
    assert front["power-switch"]["ref"] == "common/rocker-switch@1"
    assert len(front["alert-lamp"]["states"]) == 5


@pytest.mark.parametrize("slug", MODELS)
def test_all_six_sides_are_drawn_none_is_declared_empty(slug):
    views = device(slug)["views"]
    assert sorted(views) == ["bottom", "front", "left", "rear", "right", "top"]
    for name, view in views.items():
        assert "empty" not in view, name


@pytest.mark.parametrize("slug", MODELS)
def test_the_top_view_draws_its_counted_features(slug):
    dev = device(slug)
    top = decor(dev, "top")
    kinds = [d["kind"] for d in top]
    assert kinds.count("screw") == 2
    assert kinds.count("outlet-top") == 8
    assert kinds.count("lamp-edge") == 9
    assert kinds.count("label") == 2
    assert len(decor(dev, "bottom")) == len(top) - 2
    rear = decor(dev, "rear")
    assert [d["kind"] for d in rear].count("outlet-strip") == 1


@pytest.mark.parametrize("slug", MODELS)
def test_each_end_view_draws_a_plate_two_holes_and_a_screw(slug):
    dev = device(slug)
    for side in ("left", "right"):
        items = decor(dev, side)
        kinds = [d["kind"] for d in items]
        assert kinds.count("bracket-plate") == 1
        assert kinds.count("screw") == 3


def gaps(slug):
    return {g["what"]: g for g in device(slug)["gaps"]}


@pytest.mark.parametrize("slug", MODELS)
def test_what_no_page_gives_is_a_named_gap(slug):
    found = gaps(slug)
    for what in ("weight", "ground-stud-position", "front-outlet-control", "ear-holes", "cord-clip-past-depth"):
        assert what in found, what
    assert found["ear-holes"]["scope"] == ["front", "rear"]
    assert found["ground-stud-position"]["reason"] == "sources-disagree"
    assert found["front-outlet-control"]["reason"] == "sources-disagree"


@pytest.mark.parametrize("slug", MODELS)
def test_the_sheet_is_the_datasheet_and_its_hash_is_given(slug):
    sheet = device(slug)["datasheet"]
    assert "96-01237" in sheet["title"]
    assert len(sheet["sha256"]) == 64

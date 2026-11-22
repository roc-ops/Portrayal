"""Middle Atlantic Select Series half-width PDUs with RackLink, RLNK-415R and RLNK-420R (roc-ops/Portrayal#1480).

The sources are the maker's specification sheet 96-01237 and the Select Series user manual.
The sheet prints the size and the elevations of both faces, and the table of models.
The manual names the inlet, the outlets, the lamps and the ports.
What is true of the library is held here.
The printed size, the four controlled outlets, the inlet and outlet of each model and all six sides are checked.
The tests read only the device files.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "middle-atlantic"

MODELS = {
    "rlnk-415r": ("std/c14-inlet@1", "std/nema-5-15r@1", 12, "120V 12A 60Hz"),
    "rlnk-420r": ("std/c20-inlet@1", "std/nema-5-20r@1", 16, "120V 16A 60Hz"),
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
    assert (chassis["width"], chassis["height"], chassis["depth"], chassis["ru"]) == (222.5, 44.1, 245.7, 1)


@pytest.mark.parametrize("slug", MODELS)
def test_four_outlets_of_the_models_type_and_all_are_controlled(slug):
    inlet, outlet, rated, _ = MODELS[slug]
    dev = device(slug)
    rear, front = placements(dev, "rear"), placements(dev, "front")
    outs = [p for p in list(rear.values()) + list(front.values()) if p["ref"] == outlet]
    assert len(outs) == 4
    assert all(p["states"] == ["on", "off"] for p in outs)
    assert sorted(i for i in rear if i.startswith("outlet-")) == ["outlet-2", "outlet-3", "outlet-4"]
    assert "outlet-1" in front
    assert rear["input"]["ref"] == inlet
    assert dev["attrs"]["power"]["input-current-a"] == rated
    assert dev["attrs"]["management"]["outlet-count"] == 4
    assert dev["attrs"]["management"]["outlet-switching"] is True


@pytest.mark.parametrize("slug", MODELS)
def test_the_rear_holds_the_reset_button_and_the_one_ethernet_jack(slug):
    rear = placements(device(slug), "rear")
    assert rear["reset"]["ref"] == "common/reset-button@1"
    assert rear["eth"]["ref"] == "common/rj45-eth@1"
    assert rear["eth"]["attrs"]["speed"] == "100m"
    assert rear["eth-mark"]["ref"] == "common/nic-symbol@1"
    assert rear["ground-mark"]["ref"] == "common/ground-symbol@1"


@pytest.mark.parametrize("slug", MODELS)
def test_the_front_holds_an_alert_lamp_four_outlet_lamps_and_the_switch(slug):
    front = placements(device(slug), "front")
    lamps = [p for p in front.values() if p["ref"] == "common/led-indicator@1"]
    assert len(lamps) == 5
    for lamp in lamps:
        assert lamp["states"][0] == "off"
    for n in range(1, 5):
        assert f"outlet {n} " in front[f"lamp-{n}"]["description"]
    assert front["power-switch"]["ref"] == "common/rocker-switch@1"
    assert len(front["alert-lamp"]["states"]) == 5


@pytest.mark.parametrize("slug", MODELS)
def test_the_front_draws_the_outlet_plate_the_switch_bar_and_the_printed_legends(slug):
    dev = device(slug)
    front = decor(dev, "front")
    kinds = [d["kind"] for d in front]
    assert kinds.count("outlet-plate") == 1
    assert kinds.count("switch-bar") == 1
    texts = [t["text"] for t in dev["views"]["front"]["silkscreen"]]
    assert "CONTROLLED" in texts and "ALERT" in texts and "OUTLET STATUS" in texts
    assert [t for t in texts if t in "1234"] == ["1", "2", "3", "4", "1"]
    rear = [t["text"] for t in dev["views"]["rear"]["silkscreen"]]
    assert MODELS[slug][3] in rear
    assert [t for t in rear if t in "234"] == ["2", "3", "4"]


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
    assert kinds.count("screw") == 1
    assert kinds.count("outlet-top") == 3
    assert kinds.count("lamp-edge") == 5
    assert kinds.count("label") == 2, "two labels on the lid, as the p.1 photograph of the RLNK-415R shows"
    assert len(decor(dev, "bottom")) == len(top) - 2
    assert [d["kind"] for d in decor(dev, "rear")].count("outlet-strip") == 1
    rear_ids = [d["id"] for d in decor(dev, "rear")]
    for mark in ("ground-ring", "legend-ink-1", "legend-ink-2", "cord-retainer-loop"):
        assert rear_ids.count(mark) == 1, mark


@pytest.mark.parametrize("slug", MODELS)
def test_each_end_view_draws_its_plates_and_four_screws(slug):
    dev = device(slug)
    for side in ("left", "right"):
        kinds = [d["kind"] for d in decor(dev, side)]
        assert kinds.count("bracket-plate") == 2
        assert kinds.count("screw") == 4
        assert kinds.count("rail") == 1


def gaps(slug):
    return {g["what"]: g for g in device(slug)["gaps"]}


@pytest.mark.parametrize("slug", MODELS)
def test_what_no_page_gives_is_a_named_gap(slug):
    found = gaps(slug)
    for what in ("weight", "ground-stud-position", "ear-holes", "cord-clip-past-depth", "front-outlet-role",
                 "outlet-numbering", "half-rack-mounting"):
        assert what in found, what
    assert found["ear-holes"]["scope"] == ["front", "rear"]
    for what in ("ground-stud-position", "front-outlet-role", "outlet-numbering"):
        assert found[what]["reason"] == "sources-disagree"


@pytest.mark.parametrize("slug", MODELS)
def test_the_sheet_is_the_datasheet_and_its_hash_is_given(slug):
    sheet = device(slug)["datasheet"]
    assert "96-01237" in sheet["title"]
    assert len(sheet["sha256"]) == 64

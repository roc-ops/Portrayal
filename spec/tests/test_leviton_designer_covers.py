"""Leviton's designer covers 49265-DC1 and 49265-DC2 (roc-ops/Portrayal#1100): the two parts, with
the sizes Leviton's specification sheet gives them, and the VERSI-DUCT each fits.

The sheet prints each cover's width and depth. Its height is a label in the PDF's text layer that
the page's layout clips from view; the drawing's own scale agrees with it. The figures below are
those labels in inches, converted.

These read the contracts, skins and device files only, so they need no build.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
MM = 25.4

# part -> (height in, depth in, mark's left edge mm, mark's top edge mm)
COVERS = {
    "49265-dc1": (1.73, 0.86, 390.3, 16.7),
    "49265-dc2": (3.39, 0.99, 390.2, 37.8),
}
WIDTH = 17.50
# duct -> (cover, the views that carry it, the views whose black cover stays)
DUCTS = {
    "491ru-hfr": ("49265-dc1", ("front", "rear")),
    "492ru-hfr": ("49265-dc2", ("front",)),
    "492ru-hfo": ("49265-dc2", ("front",)),
}
CONFIG = "designer-cover"


def contract(name):
    p = LIB / "components" / "leviton" / name / "v1" / "contract.yaml"
    return yaml.safe_load(p.read_text())


def device(name):
    return yaml.safe_load((LIB / "devices" / "leviton" / name / "device.yaml").read_text())


def placements(dev, view):
    return dev["views"][view]["components"]["placements"]


@pytest.mark.parametrize("name", COVERS)
def test_a_cover_is_the_size_the_sheet_gives(name):
    height, depth, _, _ = COVERS[name]
    c = contract(name)
    assert c["behaviour"] == "mounts"
    assert abs(c["size"]["w"] - WIDTH * MM) < 0.06
    assert abs(c["size"]["h"] - height * MM) < 0.06
    assert c["size-confidence"] == {"w": "datasheet", "h": "datasheet"}
    reach = max(f["out"] for f in c["relief"]["features"])
    assert abs(reach - depth * MM) < 0.06, "the deepest feature is the sheet's depth"


@pytest.mark.parametrize("name", COVERS)
def test_a_cover_states_how_its_height_was_read_and_that_its_shade_is_an_estimate(name):
    c = contract(name)
    size = c["provenance"]["size"]
    assert "text layer" in size and "outside the page's visible area" in size
    assert c["provenance"]["color"].startswith("estimated")
    assert "gray" in c["provenance"]["color"]


@pytest.mark.parametrize("name", COVERS)
def test_a_cover_reserves_the_makers_mark_and_draws_none(name):
    _, _, x, y = COVERS[name]
    c = contract(name)
    zone = c["elements"]["logo-zone"]
    assert zone["at"] == [x, y]
    assert c["provenance"]["logo-zone"].startswith("reserved, not drawn")
    svg = (LIB / "components" / "leviton" / name / "v1" / "skins" / "default.svg").read_text()
    assert 'id="logo-zone"' in svg and 'fill="none"' in svg.split('id="logo-zone"')[1].split("/>")[0]
    assert "<text" not in svg and "<image" not in svg and "<path" not in svg


@pytest.mark.parametrize("name", DUCTS)
def test_a_duct_fits_its_cover_in_a_configuration_and_ships_as_before(name):
    cover, carried = DUCTS[name]
    dev = device(name)
    cfgs = dev["configurations"]
    assert cfgs["base"].get("default") is True
    assert CONFIG in cfgs and not cfgs[CONFIG].get("default")
    for view in carried:
        fitted = [p for p in placements(dev, view) if p["ref"] == f"leviton/{cover}@1"]
        assert len(fitted) == 1, f"{name} {view}: one {cover}"
        assert fitted[0]["only-in"] == [CONFIG]
        black = [p for p in placements(dev, view) if "cover" in p["ref"] and "designer" not in p["ref"]]
        assert black and all(p["only-in"] == ["base"] for p in black), "the black cover is the duct as shipped"
    for view in set(dev["views"]) - set(carried):
        for p in dev["views"][view].get("components", {}).get("placements", []):
            assert not p["ref"].startswith("leviton/49265"), f"{name} {view}: no cover on the other face"


def test_the_rear_cover_of_the_2ru_pack_is_a_named_gap_on_the_duct_with_a_rear_channel():
    gaps = {g["what"]: g for g in device("492ru-hfr")["gaps"]}
    gap = gaps["designer-cover-rear"]
    assert gap["reason"] == "vendor-silent"
    assert "1.5RU" in gap["note"] and "no size" in gap["note"]
    for name in ("491ru-hfr", "492ru-hfo"):
        assert "designer-cover-rear" not in {g["what"] for g in device(name)["gaps"]}

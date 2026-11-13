"""The Digi Connect EZ and Connect IT faces draw the shapes their held photographs show.

The fan grilles of the power supplies and of the system fan are hexagonal openings, not
dashed rings. The Connect IT front draws the bright metal frame that joins each block of
serial jacks. The Connect IT system fan on the rear is a honeycomb, not a plain disc.
Each test reads the library's source files, so none needs a build.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

GRILLE_PARTS = {
    "itps-psu": "fan-grille",
    "ezps-ac": "fan-grille",
    "ez-sysfan": "grille",
}


def _device(name):
    return yaml.safe_load((LIB / "devices" / "digi" / name / "device.yaml").read_text())


def _decor(device, view):
    return device["views"][view]["panel"].get("decor", [])


@pytest.mark.parametrize("part,group", sorted(GRILLE_PARTS.items()))
def test_the_fan_grille_skin_is_a_honeycomb(part, group):
    """Each skin's grille group holds one path of at least 80 hexagons and no dashed ring."""
    svg = (LIB / "components" / "digi" / part / "v1" / "skins" / "default.svg").read_text()
    block = re.search(rf'<g id="{group}">(.*?)</g>', svg, re.S)
    assert block, f"{part}: no group {group}"
    assert "stroke-dasharray" not in block.group(1), f"{part}: the grille still draws dashed rings"
    paths = re.findall(r'<path d="([^"]+)"', block.group(1))
    assert len(paths) == 1, f"{part}: expected one path of openings, found {len(paths)}"
    openings = paths[0].count(" Z")
    assert 80 <= openings <= 100, f"{part}: {openings} openings, expected about 85 to 91"


@pytest.mark.parametrize("name,frames", [("connect-it-16", 1), ("connect-it-48", 3)])
def test_the_connect_it_front_draws_one_metal_frame_per_block(name, frames):
    """One 2 x 8 block of jacks has one frame plate; the 48 has three."""
    plates = [d for d in _decor(_device(name), "front") if str(d.get("id", "")).startswith("serial-frame")]
    assert len(plates) == frames
    for p in plates:
        assert p["kind"] == "plate"
        assert p["size"] == [116.0, 31.0]


@pytest.mark.parametrize("part,screws", [("itps-psu", 6), ("ezps-ac", 4)])
def test_the_supply_skin_draws_the_case_screws_the_photograph_shows(part, screws):
    """The rear photograph shows six case screws on a Connect IT supply and four on a Connect EZ supply."""
    svg = (LIB / "components" / "digi" / part / "v1" / "skins" / "default.svg").read_text()
    block = re.search(r'<g id="screws"[^>]*>(.*?)</g>', svg, re.S)
    assert block, f"{part}: no screws group"
    assert len(re.findall(r"<circle ", block.group(1))) == screws


@pytest.mark.parametrize("name", ["connect-it-16", "connect-it-48"])
def test_the_connect_it_system_fan_is_a_honeycomb(name):
    """The rear fan grille is a hexagon motif of three cells on a 3.4 mm lattice."""
    fans = [d for d in _decor(_device(name), "rear") if d.get("id") == "fan-grille"]
    assert len(fans) == 1
    fan = fans[0]
    assert fan["pattern"] == "motif"
    assert fan["pattern-pitch"][0] == 3.4
    assert len(fan["pattern-cells"]) == 3

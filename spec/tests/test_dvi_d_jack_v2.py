"""The DVI-D jack is drawn at the size and contact pitch the Digital Display Working Group specification prints.

This is what is true of the library once `std/dvi-d-jack@2` is in it.
The part takes the shell, the contact pitch and the jackscrew spacing from the specification's receptacle drawing.
It declares what it estimates. Its skin draws the 24 cells and the blade where that drawing puts them.
The Raritan DSX2-32 seats it centred between its two screws, which stand the printed distance apart.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
PART = LIB / "components/std/dvi-d-jack/v2"
REF = "std/dvi-d-jack@2"
SHELL_W, SHELL_H = 24.03, 7.72
PITCH = 1.905
FIELD = 13.335
JACKSCREWS = 32.51
TOL = 0.011


def contract():
    return yaml.safe_load((PART / "contract.yaml").read_text())


def skin():
    root = ET.parse(PART / "skins/default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def cell_centres():
    out = {}
    for ident, el in skin().items():
        if ident.startswith("cell-"):
            _, r, c = ident.split("-")
            out[(int(r), int(c))] = (float(el.get("x")) + float(el.get("width")) / 2,
                                     float(el.get("y")) + float(el.get("height")) / 2)
    return out


def device():
    return yaml.safe_load((LIB / "devices/raritan/dsx2-32/device.yaml").read_text())


def test_the_size_is_the_printed_shell_and_says_where_it_is_printed():
    c = contract()
    assert (c["size"]["w"], c["size"]["h"]) == (SHELL_W, SHELL_H)
    assert c["size-confidence"] == {"w": "drawing", "h": "drawing"}
    text = c["provenance"]["size"]
    assert "Figure 5-1" in text and "24.03" in text and "7.72" in text and "page 45" in text
    assert "Digital Display Working Group" in text


def test_the_part_presents_the_key_and_has_no_analogue_pins():
    c = contract()
    assert c["class"] == "port" and c["interface"] == "dvi-d" and c["attrs"]["media"] == "dvi-d"
    assert not [i for i in skin() if i.startswith("analog")]
    assert "size" not in c.get("elements", {})


def test_every_estimate_the_specification_does_not_print_is_declared():
    prov = contract()["provenance"]
    for key in ("shell", "contacts", "blade", "colour", "mate", "depth"):
        assert key in prov
    assert "ESTIMATED" in prov["contacts"] and "ESTIMATED" in prov["shell"]
    assert "estimated" in prov["blade"].lower() and "estimated" in prov["mate"].lower()
    assert "not stated" in prov["depth"]


def test_the_skin_draws_24_cells_in_three_rows_of_eight_at_the_printed_pitch():
    cells = cell_centres()
    assert sorted(cells) == [(r, c) for r in (1, 2, 3) for c in range(1, 9)]
    for r in (1, 2, 3):
        for c in range(1, 8):
            assert cells[(r, c + 1)][0] - cells[(r, c)][0] == pytest.approx(PITCH, abs=TOL)
            assert cells[(r, c + 1)][1] == pytest.approx(cells[(r, c)][1])
    for c in range(1, 9):
        for r in (1, 2):
            assert cells[(r + 1, c)][1] - cells[(r, c)][1] == pytest.approx(PITCH, abs=TOL)
    assert cells[(1, 8)][0] - cells[(1, 1)][0] == pytest.approx(FIELD, abs=TOL)


def test_the_contact_field_sits_in_the_shell_with_the_blade_right_of_it_on_the_middle_row():
    cells = cell_centres()
    ids = skin()
    blade = ids["blade"]
    bx, by = float(blade.get("x")), float(blade.get("y"))
    bw, bh = float(blade.get("width")), float(blade.get("height"))
    middle = cells[(2, 1)][1]
    assert by + bh / 2 == pytest.approx(middle, abs=TOL)
    assert bx > cells[(2, 8)][0]
    assert bx + bw < SHELL_W
    assert middle == pytest.approx(SHELL_H / 2, abs=TOL)
    assert cells[(1, 1)][0] > 0 and cells[(1, 8)][0] < bx


def test_the_numerals_the_figure_prints_are_drawn():
    ids = skin()
    assert {i for i in ids if i.startswith("num-")} == {f"num-{n}" for n in (1, 8, 9, 16, 17, 24)}


def test_the_mate_point_is_the_centre_of_the_shell():
    mate = contract()["connection-points"]["mate"]
    assert mate["at"] == [pytest.approx(SHELL_W / 2, abs=TOL), pytest.approx(SHELL_H / 2, abs=TOL)]


def test_the_dsx2_32_seats_the_jack_once_centred_between_screws_the_printed_distance_apart():
    d = device()
    placed = [p for v in d["views"].values() for p in (v.get("components") or {}).get("placements", [])
              if p["ref"] == REF]
    assert len(placed) == 1
    jack = placed[0]
    decor = {x["id"]: x for x in d["views"]["rear"]["panel"]["decor"]}
    left, right = decor["dvi-screw-left"], decor["dvi-screw-right"]
    lx = left["at"][0] + left["size"][0] / 2
    rx = right["at"][0] + right["size"][0] / 2
    ly = left["at"][1] + left["size"][1] / 2
    assert rx - lx == pytest.approx(JACKSCREWS, abs=TOL)
    assert jack["at"][0] + SHELL_W / 2 == pytest.approx((lx + rx) / 2, abs=TOL)
    assert jack["at"][1] + SHELL_H / 2 == pytest.approx(ly, abs=TOL)
    assert jack["group"] == "video"


def test_each_screw_has_a_dark_centre_drawn_on_its_axis():
    decor = {x["id"]: x for x in device()["views"]["rear"]["panel"]["decor"]}
    for side in ("left", "right"):
        screw, bore = decor[f"dvi-screw-{side}"], decor[f"dvi-screw-{side}-bore"]
        for axis in (0, 1):
            screw_mid = screw["at"][axis] + screw["size"][axis] / 2
            assert bore["at"][axis] + bore["size"][axis] / 2 == pytest.approx(screw_mid, abs=TOL)
        assert 0 < bore["size"][0] < screw["size"][0]

"""The Lantronix LM4 console server.

What the maker's documents print is held as a fact of the library. That is the outline, the port counts, the
connector type of each port, the lamps' states and the places read from the straight front view. The tests
read the device file, never a build.
"""
import re
from pathlib import Path

import yaml

LIB = Path(__file__).resolve().parents[2] / "library"
VIEWS = {"front", "rear", "top", "bottom", "left", "right"}


def _lm4():
    return yaml.safe_load((LIB / "devices" / "lantronix" / "lm4" / "device.yaml").read_text())


def _front(device):
    comps = device["views"]["front"].get("components", {})
    return comps.get("placements", []) + comps.get("bays", [])


def _in_group(device, group):
    return [p for p in _front(device) if p.get("group") == group]


def _decor(device):
    return {d["id"]: d for d in device["views"]["front"]["panel"]["decor"]}


def _placed(device):
    return {p["id"]: p for p in _front(device)}


def test_the_chassis_is_the_size_the_maker_drawing_prints():
    lm4 = _lm4()
    chassis = lm4["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (159.0, 43.2, 155.5)
    note = " ".join(lm4["provenance"]["size"]["note"].split())
    for figure in ("159.0", "43.2", "155.5", "44.45", "158.75"):
        assert figure in note


def test_the_device_has_six_views_each_sized_to_the_chassis():
    lm4 = _lm4()
    views, chassis = lm4["views"], lm4["chassis"]
    assert set(views) == VIEWS
    w, h, d = chassis["width"], chassis["height"], chassis["depth"]
    want = {"front": (w, h), "rear": (w, h), "top": (w, d), "bottom": (w, d), "left": (d, h), "right": (d, h)}
    for name, (vw, vh) in want.items():
        assert (views[name]["size"]["w"], views[name]["size"]["h"]) == (vw, vh), name


def test_the_front_shows_the_ports_the_brief_lists():
    lm4 = _lm4()
    assert len(_in_group(lm4, "serial")) == 4
    assert len(_in_group(lm4, "network")) == 1
    assert len(_in_group(lm4, "sfp")) == 1
    assert len(_in_group(lm4, "console")) == 1
    usb = _in_group(lm4, "usb")
    assert len(usb) == 2 and all(p["ref"] == "std/usb-a@1" for p in usb)


def test_the_serial_and_console_jacks_are_serial_media_and_the_network_jack_is_not():
    lm4 = _lm4()
    for p in _in_group(lm4, "serial") + _in_group(lm4, "console"):
        assert p["attrs"]["media"] == "rj45-serial"
    assert lm4["groups"]["serial"]["attrs"]["media"] == "rj45-serial"
    assert lm4["groups"]["console"]["attrs"]["media"] == "rj45-serial"
    assert all("media" not in p.get("attrs", {}) for p in _in_group(lm4, "network"))


def test_the_two_and_four_port_part_numbers_are_listed():
    configs = _lm4()["configurations"]
    numbers = {n for c in configs.values() for n in c["part-numbers"]}
    assert {"LM4-4S", "LM4-2S"} <= numbers


def test_the_two_port_export_says_its_four_jacks_are_not_the_makers_count():
    configs = _lm4()["configurations"]
    assert "not the maker's count" in configs["ac-2s"]["export-description"]
    assert "not the maker's count" in configs["ac-2s"]["description"].replace("\n", " ")
    assert "export-description" not in configs["ac-4s"]


def test_the_network_jack_is_turned_so_its_latch_notch_is_at_the_top():
    assert _placed(_lm4())["net-1"]["rotate"] == 180


def test_the_front_parts_stand_at_the_places_read_from_the_straight_front_view():
    placed = _placed(_lm4())
    want = {"net-1": [47.3, 21.35], "port-2": [70.85, 25.15], "console": [95.55, 5.3], "usb-1": [95.9, 20.1],
            "usb-2": [95.9, 28.55], "serial-1": [117.85, 8.5], "serial-2": [134.1, 8.5],
            "serial-3": [117.85, 23.0], "serial-4": [134.1, 23.0]}
    for ident, at in want.items():
        assert placed[ident]["at"] == at, ident
    assert all("size" not in p for p in placed.values())


def test_the_serial_jack_columns_are_16_25_apart_and_the_rows_14_5_apart_about_the_part_centres():
    placed = _placed(_lm4())
    centre = {i: (placed[i]["at"][0] + 6.35, placed[i]["at"][1] + 5.5) for i in ("serial-1", "serial-2", "serial-3", "serial-4")}
    assert abs(centre["serial-2"][0] - centre["serial-1"][0] - 16.25) < 0.01
    assert abs(centre["serial-3"][1] - centre["serial-1"][1] - 14.5) < 0.01
    assert abs(centre["serial-1"][0] - 124.2) < 0.01 and abs(centre["serial-1"][1] - 14.0) < 0.01


def test_the_console_and_usb_ports_and_the_serial_jacks_each_sit_on_one_pale_housing_block():
    lm4 = _lm4()
    decor = _decor(lm4)
    colour = "#e5d9cf"
    assert decor["housing-console-usb"]["fill"] == decor["housing-serial"]["fill"] == colour
    box = decor["housing-console-usb"]
    for p in _in_group(lm4, "console") + _in_group(lm4, "usb"):
        assert box["at"][0] <= p["at"][0] and p["at"][0] + 12.0 <= box["at"][0] + box["size"][0] + 1.0
    serial = decor["housing-serial"]
    for p in _in_group(lm4, "serial"):
        assert serial["at"][0] <= p["at"][0] <= serial["at"][0] + serial["size"][0]
    assert serial["at"][1] + serial["size"][1] <= decor["bar-serial-bottom"]["at"][1] + 0.3
    assert decor["bar-serial-top"]["at"][1] + decor["bar-serial-top"]["size"][1] <= serial["at"][1] + 0.3


# The outer edge of each housing's black outline in the dimensions figure, mm: left, top, right, bottom.
# Each is the midpoint of two readings of the same edge, and the build stands within 0.3 mm of it.
FIGURE_HOUSINGS = {
    "housing-serial": (114.57, 6.99, 149.51, 35.45),
    "housing-console-usb": (91.69, 3.16, 111.96, 35.45),
    "housing-e1": (46.25, 20.72, 63.92, 35.44),
    "housing-sfp": (69.95, 24.25, 85.79, 35.44),
    "dc-housing": (11.03, 26.69, 19.40, 35.05),
    "dc-housing-tab": (12.50, 23.78, 17.97, 27.14),
}


def test_each_housing_stands_within_0_3_mm_of_the_outline_of_the_dimensions_figure():
    decor = _decor(_lm4())
    for ident, want in FIGURE_HOUSINGS.items():
        box = decor[ident]
        have = (box["at"][0], box["at"][1], box["at"][0] + box["size"][0], box["at"][1] + box["size"][1])
        for edge, w, h in zip(("left", "top", "right", "bottom"), want, have):
            assert abs(h - w) <= 0.3, (ident, edge, h, w)


def test_the_e1_and_sfp_housings_stand_behind_their_parts_and_reach_past_them_to_the_figure():
    decor = _decor(_lm4())
    placed = _placed(_lm4())
    for housing, part, (w, h) in (("housing-e1", "net-1", (15.8, 13.2)), ("housing-sfp", "port-2", (14.5, 10.0))):
        box, at = decor[housing], placed[part]["at"]
        assert box["at"][0] <= at[0] and box["at"][1] <= at[1], housing
        assert at[0] + w <= box["at"][0] + box["size"][0] and at[1] + h <= box["at"][1] + box["size"][1], housing
    ids = list(decor)
    assert ids.index("housing-sfp") < ids.index("sfp-rim-mark-1") and ids.index("housing-sfp") < ids.index("sfp-pull-tab")


def test_the_button_the_reset_pinhole_and_the_four_corner_screws_are_round():
    decor = _decor(_lm4())
    assert decor["button"]["size"] == [7.2, 7.2] and decor["button"]["rx"] == 3.6
    assert decor["reset-hole"]["size"] == [3.2, 3.2] and decor["reset-hole"]["rx"] == 1.6
    for name in ("screw-tl", "screw-tr", "screw-bl", "screw-br"):
        screw = decor[name]
        assert screw["size"] == [6.5, 6.5] and screw["rx"] == 3.25
    centres = {n: (decor[n]["at"][0] + 3.25, decor[n]["at"][1] + 3.25) for n in ("screw-tl", "screw-tr", "screw-bl", "screw-br")}
    assert all(abs(a - b) < 0.01 for a, b in zip(centres["screw-tl"], (5.2, 5.2)))
    assert all(abs(a - b) < 0.01 for a, b in zip(centres["screw-br"], (153.8, 38.0)))


def test_the_heatsink_has_six_fins_at_the_pitch_of_the_front_view_and_the_lid_repeats_them():
    lm4 = _lm4()
    fins = sorted((d for i, d in _decor(lm4).items() if i.startswith("heatsink-slat-")), key=lambda d: d["at"][0])
    assert len(fins) == 6 and all(f["size"][0] == 1.45 for f in fins)
    pitches = [b["at"][0] - a["at"][0] for a, b in zip(fins, fins[1:])]
    assert all(abs(p - 4.5) < 0.05 for p in pitches)
    top = {d["id"]: d for d in lm4["views"]["top"]["panel"]["decor"]}
    slats = sorted((d for i, d in top.items() if i.startswith("lid-slat-")), key=lambda d: d["at"][0])
    assert [s["at"][0] for s in slats] == [f["at"][0] for f in fins]
    assert top["lid-opening"]["size"][0] > 6 * 1.45 + 7 * 2.0
    assert top["lid-opening"]["at"][1] + top["lid-opening"]["size"][1] <= lm4["chassis"]["depth"]


def test_the_left_flank_draws_three_round_screws_and_the_right_flank_is_built_as_it_mirrored():
    lm4 = _lm4()
    views = lm4["views"]
    left = {d["id"]: d for d in views["left"]["panel"]["decor"] if d["id"].startswith("flank-screw-")}
    right = {d["id"]: d for d in views["right"]["panel"]["decor"] if d["id"].startswith("flank-screw-")}
    assert len(left) == 3 and all(d["size"] == [5.8, 5.8] and d["rx"] == 2.9 for d in left.values())
    depth = lm4["chassis"]["depth"]
    for ident, screw in left.items():
        mirror = right[ident]
        assert abs(mirror["at"][0] - (depth - screw["at"][0] - 5.8)) < 0.01 and mirror["at"][1] == screw["at"][1]
        assert mirror["fill"] == screw["fill"] and mirror["size"] == screw["size"]
    envelopes = {v: next(d for d in views[v]["panel"]["decor"] if d["kind"] == "envelope")["fill"] for v in ("left", "right")}
    assert envelopes["left"] == envelopes["right"]
    note = " ".join(lm4["provenance"]["body"]["note"].split())
    assert "built as the documented side" in note and "as no document shows this one" in note


def test_the_marks_and_icons_are_drawn_as_silkscreen_paths():
    silk = _lm4()["views"]["front"]["silkscreen"]
    paths = {s["id"]: s for s in silk if "path" in s}
    assert set(paths) == {"mark-prompt", "mark-dc", "mark-power", "mark-pulse", "mark-warning", "mark-network",
                          "mark-antenna-arcs", "mark-antenna-stem", "mark-antenna-dot", "mark-link",
                          "mark-arrows-shaft", "mark-arrows-head", "mark-10101", "dc-opening-foot-left",
                          "dc-opening-foot-right", "dc-centre-mark", "dc-tile-chamfer-1", "dc-tile-chamfer-2",
                          "dc-tile-chamfer-3", "dc-tile-chamfer-4"}
    assert all(s["path"].strip() and s["fill"].startswith("#") for s in paths.values())
    assert paths["mark-prompt"]["for"] == "console"


def test_every_silkscreen_mark_lies_on_the_front():
    front = _lm4()["views"]["front"]
    w, h = front["size"]["w"], front["size"]["h"]
    for s in front["silkscreen"]:
        assert 0 <= s["at"][0] <= w and 0 <= s["at"][1] <= h, s.get("id", s.get("text"))


def test_the_five_front_lamps_are_placed_with_states_and_drawn_off():
    placed = _placed(_lm4())
    ids = ["led-power", "led-pulse", "led-alert", "led-e2-link", "led-e2-activity"]
    assert [p["id"] for p in sorted(_in_group(_lm4(), "status-leds"), key=lambda p: p["rel-pos"])] == ids
    for ident in ids:
        states = placed[ident]["states"]
        assert states[0] == "off", ident
        assert all(isinstance(s, dict) and (s["color"].startswith("#") if "color" in s else s["behavior"]["mode"] == "sequence")
                   for s in states[1:]), ident
    decor = _decor(_lm4())
    assert not [d for d in decor.values() if d["id"] in ("dot-e1-e2", "dot-e2-right", "hole-lamps")]


def test_the_status_and_warning_lamps_carry_the_documented_flash_states():
    placed = _placed(_lm4())
    status = {s["name"]: s for s in placed["led-pulse"]["states"][1:]}
    warning = {s["name"]: s for s in placed["led-alert"]["states"][1:]}
    assert status["bootloader"]["behavior"] == {"mode": "blinking", "rate": 4}
    assert status["os-loading"]["behavior"] == {"mode": "blinking", "rate": 1}
    assert status["running"]["behavior"] == {"mode": "blinking", "rate": 0.5}
    assert set(warning) == {"software-installing", "factory-reset-running", "fips-failure"}
    assert set(status) == set(warning) | {"bootloader", "os-loading", "running", "factory-reset-beginning"}
    for lamp in (status, warning):
        for name in ("software-installing", "factory-reset-running", "fips-failure"):
            assert lamp[name]["behavior"]["mode"] == "sequence" and "color" not in lamp[name]
    assert placed["led-power"]["states"][1]["name"] == "on" and "behavior" not in placed["led-power"]["states"][1]


def _left_right_lit(placement):
    """The `on` colour of the lamp on the left and on the right; rotate 180 swaps the part's two windows."""
    on = {el: next(s["color"] for s in states if isinstance(s, dict) and s["name"] == "on") for el, states in placement["states"].items()}
    return (on["led-b"], on["led-a"]) if placement.get("rotate") == 180 else (on["led-a"], on["led-b"])


def _rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def test_the_console_and_serial_jacks_state_a_lit_green_lamp_on_the_left_and_a_lit_yellow_on_the_right():
    jacks = _in_group(_lm4(), "serial") + _in_group(_lm4(), "console")
    assert len(jacks) == 5 and all("states" in p for p in jacks)
    for p in jacks:
        left, right = (_rgb(c) for c in _left_right_lit(p))
        assert left[1] > left[0] + 20 and left[1] > left[2] + 20, p["id"]
        assert right[0] > right[2] + 80 and right[1] > right[2] + 80, p["id"]


def test_the_two_lamps_at_the_sfp_cage_are_green_on_the_left_and_brown_on_the_right():
    placed = _placed(_lm4())
    left = _rgb(placed["led-e2-link"]["states"][1]["color"])
    right = _rgb(placed["led-e2-activity"]["states"][1]["color"])
    assert left[1] > left[0] + 20 and left[1] > left[2] + 60
    assert right[0] > right[2] + 60 and right[1] > right[2] + 40 and right[0] > right[1]
    assert placed["led-e2-link"]["at"][0] < placed["port-2"]["at"][0] < placed["led-e2-activity"]["at"][0]


def test_the_wordmark_and_the_registered_mark_sit_in_the_logo_zone_and_no_gap_asks_for_them():
    lm4 = _lm4()
    zone = lm4["views"]["front"]["regions"][0]
    assert zone["id"] == "logo-zone" and zone["at"][0] <= 47.4 and zone["at"][0] + zone["size"]["w"] >= 86.3
    assert not [g for g in lm4["gaps"] if g["what"] in ("registered-mark", "front-positions", "indicator-led")]


def test_no_rack_ear_is_placed_on_the_desktop_unit_and_the_gap_and_the_note_say_why():
    lm4 = _lm4()
    assert lm4["chassis"]["mount"] == "desktop" and "ears" not in lm4["chassis"]
    assert not [p for p in _front(lm4) if p["ref"] == "common/rack-ear@1" or p.get("optional") == "ears"]
    assert not [p for p in _front(lm4) if p["id"] in ("ear-left", "ear-right")]
    note = " ".join(lm4["provenance"]["mount"]["note"].split())
    assert "one provided rack mounting ear" in note
    assert "states `ears` for a rack device only, so no ear is placed" in note
    gap = next(g for g in lm4["gaps"] if g["what"] == "mounting")
    assert gap["scope"] == ["front"] and gap["reason"] == "needs-drawing"
    assert "two loose screws" in " ".join(gap["note"].split())


def test_the_gaps_are_the_ones_no_held_document_answers():
    lm4 = _lm4()
    assert {g["what"] for g in lm4["gaps"]} == {"dc-input", "rear-panel", "lamp-colour", "din-rail-mount", "mounting",
                                                "envelope-faces-undetailed"}
    gap = next(g for g in lm4["gaps"] if g["what"] == "dc-input")
    note = " ".join(gap["note"].split())
    assert "No interface is known, so no connector part is placed" in note
    assert "four cells in two rows of two" in note
    rear = next(g for g in lm4["gaps"] if g["what"] == "rear-panel")
    assert "A web search found no rear picture" in " ".join(rear["note"].split())
    lid = next(g for g in lm4["gaps"] if g["what"] == "envelope-faces-undetailed")
    assert lid["scope"] == ["bottom", "right"]


def test_the_dc_housing_opening_is_drawn_as_decor_with_four_cells_and_no_part_is_placed_for_it():
    lm4 = _lm4()
    decor = _decor(lm4)
    cells = sorted((d for i, d in decor.items() if i.startswith("dc-cell-")), key=lambda d: (d["at"][1], d["at"][0]))
    assert len(cells) == 4
    assert abs(cells[1]["at"][0] - cells[0]["at"][0] - 3.15) < 0.02 and abs(cells[2]["at"][1] - cells[0]["at"][1] - 2.95) < 0.02
    body = decor["dc-housing"]
    assert abs(body["size"][0] - 8.35) < 0.01 and abs(decor["dc-housing-tab"]["at"][1] - 23.75) < 0.01
    interior = decor["dc-opening-interior"]
    for cell in cells:
        assert interior["at"][0] <= cell["at"][0] and cell["at"][0] + cell["size"][0] <= interior["at"][0] + interior["size"][0]
        assert interior["at"][1] <= cell["at"][1] and cell["at"][1] + cell["size"][1] <= interior["at"][1] + interior["size"][1]
    assert not [p for p in _front(lm4) if p["at"][0] < 20 and p["at"][1] > 23]
    note = " ".join(lm4["provenance"]["body"]["note"].split())
    assert "The DC housing at the lower left is drawn as decor" in note


# The pale parts of the DC latch tab in the dimensions figure, mm: left, top, right, bottom.
# Each is the midpoint of two readings of the same edge, and the build stands within 0.3 mm of it.
FIGURE_DC_LATCH = {
    "dc-latch-window": (12.87, 24.92, 17.50, 27.20),
    "dc-latch-bar": (12.87, 24.25, 17.50, 24.55),
    "dc-latch-notch": (14.27, 25.80, 16.24, 27.20),
    "dc-latch-notch-core": (14.64, 26.31, 15.72, 27.20),
}


def test_the_dc_latch_tab_draws_its_pale_window_bar_and_notch_within_0_3_mm_of_the_figure():
    decor = _decor(_lm4())
    for ident, want in FIGURE_DC_LATCH.items():
        assert ident in decor, ident
        box = decor[ident]
        have = (box["at"][0], box["at"][1], box["at"][0] + box["size"][0], box["at"][1] + box["size"][1])
        for edge, w, h in zip(("left", "top", "right", "bottom"), want, have):
            assert abs(h - w) <= 0.3, (ident, edge, h, w)
    assert decor["dc-latch-window"]["fill"] == "#aaafc7" and decor["dc-latch-bar"]["fill"] == "#b2b2b2"
    assert decor["dc-latch-notch-core"]["fill"] == "#d7dffe" and decor["dc-latch-notch"]["fill"] == "#101012"
    ids = list(decor)
    order = ["dc-housing", "dc-housing-tab", "dc-latch-window", "dc-latch-bar", "dc-latch-notch", "dc-latch-notch-core"]
    assert [ids.index(i) for i in order] == sorted(ids.index(i) for i in order)
    gap = next(g for g in _lm4()["gaps"] if g["what"] == "dc-input")
    note = " ".join(gap["note"].split())
    assert "pale window" in note and "over 63 px" in note
    assert "pale outline 0.2 mm thick" in note and "pale tile" in note
    body = " ".join(_lm4()["provenance"]["body"]["note"].split())
    assert "follow the dimensions figure, where the photograph shows the tab dark" in body


# The DC input's opening and cells in the dimensions figure, mm: left, top, right, bottom.
# Each is the midpoint of two readings of the same edge, and the build stands within 0.3 mm of it.
FIGURE_DC_INPUT = {
    "dc-opening": (11.93, 27.57, 18.38, 33.95),
    "dc-cell-1": (12.57, 28.37, 14.81, 30.41),
    "dc-cell-2": (15.74, 28.37, 17.79, 30.41),
    "dc-cell-3": (12.57, 31.32, 14.81, 33.36),
    "dc-cell-4": (15.74, 31.32, 17.79, 33.36),
    "dc-hole-1": (13.16, 28.77, 14.29, 29.87),
    "dc-hole-2": (16.12, 28.77, 17.24, 29.87),
    "dc-hole-3": (13.16, 31.71, 14.29, 32.99),
    "dc-hole-4": (16.11, 31.71, 17.24, 32.99),
}
# The pale wedges in the lower corners of the outline and the triangle at the centre, as boxes: the same readings.
FIGURE_DC_MARKS = {
    "dc-opening-foot-left": (12.20, 33.00, 13.15, 33.95),
    "dc-opening-foot-right": (17.40, 32.90, 18.40, 33.95),
    "dc-centre-mark": (14.60, 30.15, 15.85, 31.03),
}
DC_PIECES = ["dc-housing", "dc-housing-tab", "dc-latch-window", "dc-latch-bar", "dc-latch-notch", "dc-latch-notch-core",
             "dc-opening", "dc-opening-interior", "dc-cell-1", "dc-cell-2", "dc-cell-3", "dc-cell-4",
             "dc-hole-1", "dc-hole-2", "dc-hole-3", "dc-hole-4"]


def test_the_dc_opening_and_cells_stand_within_0_3_mm_of_the_figure_and_look_like_it():
    decor = _decor(_lm4())
    for ident, want in FIGURE_DC_INPUT.items():
        assert ident in decor, ident
        box = decor[ident]
        have = (box["at"][0], box["at"][1], box["at"][0] + box["size"][0], box["at"][1] + box["size"][1])
        for edge, w, h in zip(("left", "top", "right", "bottom"), want, have):
            assert abs(h - w) <= 0.3, (ident, edge, h, w)
    for ident in ("dc-opening", "dc-cell-1", "dc-cell-2", "dc-cell-3", "dc-cell-4"):
        assert decor[ident]["fill"] == "#aaafc7", ident
    for ident in ("dc-opening-interior", "dc-hole-1", "dc-hole-2", "dc-hole-3", "dc-hole-4"):
        assert decor[ident]["fill"] == "#101012", ident
    for ident in DC_PIECES:
        assert decor[ident].get("rx") == 0, ident
    ids = list(decor)
    assert [ids.index(i) for i in DC_PIECES] == sorted(ids.index(i) for i in DC_PIECES)
    outer, inner = decor["dc-opening"], decor["dc-opening-interior"]
    widths = (inner["at"][0] - outer["at"][0], inner["at"][1] - outer["at"][1],
              outer["at"][0] + outer["size"][0] - inner["at"][0] - inner["size"][0],
              outer["at"][1] + outer["size"][1] - inner["at"][1] - inner["size"][1])
    assert [round(w, 2) for w in widths] == [0.2, 0.27, 0.2, 0.2]
    for n in (1, 2, 3, 4):
        tile, hole = decor[f"dc-cell-{n}"], decor[f"dc-hole-{n}"]
        assert tile["at"][0] < hole["at"][0] and hole["at"][0] + hole["size"][0] < tile["at"][0] + tile["size"][0]
        assert tile["at"][1] < hole["at"][1] and hole["at"][1] + hole["size"][1] < tile["at"][1] + tile["size"][1]


# Each tile loses one lower corner in the figure, listed as the tile and the side of that corner.
# Tiles 1 and 4 lose the lower right, and tiles 2 and 3 lose the lower left.
DC_CHAMFERS = {"dc-tile-chamfer-1": ("dc-cell-1", "right"), "dc-tile-chamfer-2": ("dc-cell-2", "left"),
               "dc-tile-chamfer-3": ("dc-cell-3", "left"), "dc-tile-chamfer-4": ("dc-cell-4", "right")}


def test_each_dc_tile_has_one_lower_corner_cut_by_a_black_triangle_about_0_6_mm_across():
    lm4 = _lm4()
    decor = _decor(lm4)
    marks = {s["id"]: s for s in lm4["views"]["front"]["silkscreen"] if s.get("id") in DC_CHAMFERS}
    assert set(marks) == set(DC_CHAMFERS)
    for ident, (tile_id, side) in DC_CHAMFERS.items():
        mark, tile = marks[ident], decor[tile_id]
        assert mark["filled"] is True and mark["fill"] == "#101012" and mark["for"] == "chassis", ident
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", mark["path"])]
        xs = [mark["at"][0] + v for v in numbers[0::2]]
        ys = [mark["at"][1] + v for v in numbers[1::2]]
        assert len(xs) == 3, ident
        assert abs(max(ys) - (tile["at"][1] + tile["size"][1])) <= 0.05, ident
        edge = tile["at"][0] if side == "left" else tile["at"][0] + tile["size"][0]
        assert abs((min(xs) if side == "left" else max(xs)) - edge) <= 0.05, ident
        assert abs(max(xs) - min(xs) - 0.58) <= 0.05 and abs(max(ys) - min(ys) - 0.58) <= 0.05, ident


def test_the_dc_opening_has_its_two_corner_wedges_and_its_centre_triangle_as_filled_marks():
    marks = {s["id"]: s for s in _lm4()["views"]["front"]["silkscreen"] if s.get("id") in FIGURE_DC_MARKS}
    assert set(marks) == set(FIGURE_DC_MARKS)
    for ident, want in FIGURE_DC_MARKS.items():
        mark = marks[ident]
        assert mark["filled"] is True and mark["fill"] == "#aaafc7" and mark["for"] == "chassis", ident
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", mark["path"])]
        xs, ys = numbers[0::2], numbers[1::2]
        assert len(xs) == 3, ident
        have = (mark["at"][0] + min(xs), mark["at"][1] + min(ys), mark["at"][0] + max(xs), mark["at"][1] + max(ys))
        for edge, w, h in zip(("left", "top", "right", "bottom"), want, have):
            assert abs(h - w) <= 0.3, (ident, edge, h, w)


def test_each_corner_screw_has_a_plus_recess_and_the_sfp_cage_has_its_green_pull_tab():
    decor = _decor(_lm4())
    for corner in ("tl", "tr", "bl", "br"):
        screw, bar_h, bar_v = decor["screw-" + corner], decor[f"screw-cross-{corner}-h"], decor[f"screw-cross-{corner}-v"]
        centre = (screw["at"][0] + 3.25, screw["at"][1] + 3.25)
        for bar in (bar_h, bar_v):
            assert abs(bar["at"][0] + bar["size"][0] / 2 - centre[0]) < 0.01
            assert abs(bar["at"][1] + bar["size"][1] / 2 - centre[1]) < 0.01
    tab = decor["sfp-pull-tab"]
    assert tab["fill"].startswith("#") and 5.0 < tab["size"][0] < 7.0
    port = _placed(_lm4())["port-2"]
    assert port["at"][0] <= tab["at"][0] and tab["at"][0] + tab["size"][0] <= port["at"][0] + 14.5


def test_the_reset_pinhole_has_its_tan_ring_and_the_ring_sits_on_the_pinhole_disc_centre():
    decor = _decor(_lm4())
    assert "reset-ring" in decor and "reset-pinhole" in decor
    disc, ring, pinhole = decor["reset-hole"], decor["reset-ring"], decor["reset-pinhole"]
    assert ring["size"] == [1.8, 1.8] and ring["rx"] == 0.9
    assert pinhole["size"] == [0.9, 0.9] and pinhole["rx"] == 0.45
    for part in (ring, pinhole):
        assert part["size"][0] <= disc["size"][0]
    centre = (disc["at"][0] + 1.6, disc["at"][1] + 1.6)
    for part in (ring, pinhole):
        assert abs(part["at"][0] + part["size"][0] / 2 - centre[0]) < 0.01
        assert abs(part["at"][1] + part["size"][1] / 2 - centre[1]) < 0.01
    ids = list(decor)
    assert ids.index("reset-hole") < ids.index("reset-ring") < ids.index("reset-pinhole")
    note = " ".join(_lm4()["provenance"]["body"]["note"].split())
    assert "The Reset pinhole has a tan ring" in note


def test_the_sfp_cage_has_four_grey_marks_on_its_top_rim():
    decor = _decor(_lm4())
    marks = sorted((d for i, d in decor.items() if i.startswith("sfp-rim-mark-")), key=lambda d: d["at"][0])
    assert len(marks) == 4
    port = _placed(_lm4())["port-2"]
    for mark in marks:
        assert mark["kind"] == "bezel", "a rim mark is not a latch"
        assert 2.3 <= mark["size"][0] <= 2.7 and mark["size"][1] == 0.6
        assert port["at"][0] - 0.5 <= mark["at"][0] and mark["at"][0] + mark["size"][0] <= port["at"][0] + 16.0
    assert decor["sfp-pull-tab"]["kind"] == "latch"
    gaps = [b["at"][0] - (a["at"][0] + a["size"][0]) for a, b in zip(marks, marks[1:])]
    assert all(1.4 < g < 2.0 for g in gaps)
    note = " ".join(_lm4()["provenance"]["body"]["note"].split())
    assert "They are drawn as decor, estimated" in note and "sit on the SFP housing's top band" in note


def test_the_sources_that_disagree_are_each_said_in_the_notes():
    notes = " ".join(" ".join(p["note"].split()) for p in _lm4()["provenance"].values())
    assert "The dimensions figure draws the console lamps yellow at the left and green at the right" in notes
    assert "The dimensions figure draws the seven slots white" in notes
    assert "The dimensions figure prints a small 4 in the lower-left serial jack" in notes
    assert "The dimensioned view draws them blue" in notes
    assert "stated here as the difference and not drawn" in notes


def test_the_faint_engraving_on_the_lid_is_a_named_zone_inside_the_lid():
    lm4 = _lm4()
    zones = {z["id"]: z for z in lm4["views"]["top"]["regions"]}
    zone = zones["lid-marking"]
    assert zone["at"][0] + zone["size"]["w"] <= lm4["chassis"]["width"]
    assert zone["at"][1] + zone["size"]["h"] <= lm4["chassis"]["depth"]
    assert zone["at"][1] > lm4["chassis"]["depth"] / 2


def test_the_drawn_usb_tongue_is_said_to_be_pale_where_the_pictures_are_dark_or_blue():
    note = " ".join(_lm4()["provenance"]["body"]["note"].split())
    assert "The drawn tongue is pale" in note and "draws them blue" in note
    assert "no circle shape" not in note

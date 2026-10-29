"""MikroTik's Cloud Router Switch CRS5xx, batch 2: the 100G switch with the front-mounted supplies.

The CRS504-4XQ-IN takes its envelope from MikroTik's dimensions drawing, whose file is named 04-4XQ-RM... but whose title
block reads "504-4XQ-IN" (printed 02.10.2023): it draws the IN's two AC supply modules, four QSFP28 cages and rack ears
and nothing of the outdoor -OUT. The brochure's 320 x 185 x 44 agrees. Its two supplies are hot-swap modules in the
brochure and the photographs, but no held document prints a part number for either, so they are drawn as part of the
chassis (two C14 inlets) and no bay is added. The device names are lower case with no +.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/mikrotik"
MODELS = {
    "crs504-4xq-in": ("CRS504-4XQ-IN", "CRS504"),
    "crs520-4xs-16xq-rm": ("CRS520-4XS-16XQ-RM", "CRS520"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth
    "crs504-4xq-in": (320.0, 44.0, 185.0),
    "crs520-4xs-16xq-rm": (443.0, 44.0, 367.0),
}
CRS504 = "crs504-4xq-in"
CRS520 = "crs520-4xs-16xq-rm"


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return (d["views"][view].get("components") or {}).get("bays") or []


def refs(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def text_of(d, view):
    return {s.get("text") for s in d["views"][view]["silkscreen"]}


@pytest.mark.parametrize("name", NAMES)
def test_the_device_is_named_as_the_maker_prints_it(name):
    d = load(name)
    model, series = MODELS[name]
    assert d["name"] == name
    assert d["manufacturer"] == "MikroTik"
    assert d["model"] == model
    assert d["portfolio"] == {"line": "Switches", "family": "Cloud Router Switch", "series": series}
    assert "+" not in name
    assert d["version"] == "1.0.0"
    assert list(d["configurations"]["base"]["part-numbers"]) == [model]


@pytest.mark.parametrize("name", NAMES)
def test_the_envelope_is_the_drawings(name):
    d = load(name)
    w, h, depth = ENVELOPE[name]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, depth, 1)
    assert d["views"]["front"]["size"] == {"w": w, "h": h}
    assert d["views"]["top"]["size"] == {"w": w, "h": depth}
    assert d["views"]["left"]["size"] == {"w": depth, "h": h}
    assert d["views"]["right"]["size"] == {"w": depth, "h": h}


# --- CRS504-4XQ-IN -----------------------------------------------------------------------------------------------

def test_crs504_drawing_name_difference_is_declared():
    d = load(CRS504)
    note = d["provenance"]["sources"]["note"]
    assert "04-4XQ-RMoutlineanddimensiondrawings_250851.pdf" in note
    assert '"504-4XQ-IN"' in note and "02.10.2023" in note
    assert "320 x 185 x 44" in d["provenance"]["chassis"]["note"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["drawing-name"]["reason"] == "sources-disagree"
    assert gaps["power-figures"]["reason"] == "sources-disagree"
    assert "60 V" in gaps["power-figures"]["note"] and "57" in gaps["power-figures"]["note"]


def test_crs504_has_four_qsfp28_cages_in_one_row_each_with_two_lamps():
    d = load(CRS504)
    cages = [p for p in placements(d, "front") if p.get("group") == "qsfp28"]
    assert [p["id"] for p in cages] == [f"qsfp-{n}" for n in range(1, 5)]
    assert [p["rel-pos"] for p in cages] == [1, 2, 3, 4]
    assert all(p["ref"] == "std/qsfp28@1" and p["attrs"] == {"media": "qsfp28", "speed": "100g"} for p in cages)
    assert len({p["at"][1] for p in cages}) == 1
    for a, b in zip(cages, cages[1:]):
        assert b["at"][0] - a["at"][0] == pytest.approx(26.0, abs=0.1)
    assert len([p for p in placements(d, "front") if p.get("group") == "qsfp-leds"]) == 8  # ACT and 100G a cage
    assert not [p for p in placements(d, "front") if p["ref"].startswith("std/sfp")]


def test_crs504_front_carries_console_management_reset_dc_jack_and_three_lamps():
    d = load(CRS504)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "100m")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    assert not refs(d, "front", "common/dc-barrel@1")  # drawn as chassis art: the barrel census wants a current
    assert [x["id"] for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "dc-jack-art"] == [
        "dc-jack-housing", "dc-jack-rim", "dc-jack-bore", "dc-jack-pin"]
    assert [x["id"] for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "dc-terminal-art"] == [
        "dc-terminal-cap", "dc-terminal-housing", "dc-terminal-entry-1", "dc-terminal-entry-2"]
    assert len([p for p in placements(d, "front") if p.get("group") == "status-leds"]) == 5  # 3 bars, 2 supply lamps
    assert len(refs(d, "front", "common/led-rect@1")) == 11 and len(refs(d, "front", "common/led-dot@1")) == 2
    assert {"CONSOLE", "MGMT/PoE in", "RESET", "USER", "FAULT", "POWER", "36 - 60 V", "CRS504-4XQ-IN",
            "ACT", "100G", "1", "2", "3", "4"} <= text_of(d, "front")
    gaps = {g["what"] for g in d["gaps"]}
    assert {"dc-jack", "dc-terminal", "hot-swap-supplies", "led-states", "left-wall", "rear-face"} <= gaps
    assert not [p for p in placements(d, "front") if p["ref"].startswith("common/dc-terminal")]
    ports = [p for p in placements(d, "front") if p.get("group") in {"qsfp28", "mgmt", "console"}]
    assert len(ports) == 4 + 1 + 1  # page: 4 QSFP28 and one 100M Ethernet port; the console is on the metal


def test_crs504_supplies_are_two_front_modules_with_c14_inlets_and_no_bays():
    d = load(CRS504)
    assert not bays(d, "front") and not bays(d, "rear")
    inlets = refs(d, "front", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]  # the quick guide: 2 AC inputs
    assert all(p["group"] == "inlets" and p["rotate"] in (90, 270, -90) for p in inlets)
    assert {"PSU 1", "PSU 2", "100-240 V 50/60 Hz"} <= text_of(d, "front")
    assert d["chassis"]["power"] == "ac"
    assert d["attrs"]["power"]["power-max-w"] == 41 and d["attrs"]["power"]["power-without-attachments-w"] == 25
    assert "fan-redundancy" not in json.dumps(d["groups"])


def test_crs504_fans_are_on_the_right_wall_and_the_other_faces_are_empty():
    d = load(CRS504)
    fans = [x["id"] for x in d["views"]["right"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert fans == ["fan-0", "fan-1"]
    # unwarped from photograph 2158: guards 20 x 31 mm, centred 107.5 and 129.5 mm from the front, 2.5 mm apart
    f0, f1 = decor(d, "right", "fan-0"), decor(d, "right", "fan-1")
    assert (f0["at"], f0["size"], f0["rx"]) == ([97.5, 3.0], [20.0, 31.0], 10.0)
    assert (f1["at"], f1["size"]) == ([119.5, 3.0], [20.0, 31.0])
    for fan, hub in ((f0, decor(d, "right", "fan-hub-0")), (f1, decor(d, "right", "fan-hub-1"))):  # a clear hub in each ring
        assert hub["kind"] == "fan-hub" and hub["size"] == [12.5, 19.0] and hub["fill"] == d["chassis"]["color"]
        assert hub["at"][0] + 6.25 == pytest.approx(fan["at"][0] + 10.0) and hub["at"][1] + 9.5 == pytest.approx(fan["at"][1] + 15.5)
    for view in ("left", "top", "bottom"):
        assert d["views"][view].get("empty"), view
    gaps = {g["what"] for g in d["gaps"]}
    assert {"fan-count", "left-wall", "rear-face", "top-and-bottom"} <= gaps


def decor(d, view, id_):
    return next(x for x in d["views"][view]["panel"]["decor"] if x.get("id") == id_)


def test_crs504_cage_vent_is_a_motif_tile_of_the_measured_weave():
    d = load(CRS504)
    v = decor(d, "front", "cage-vent")
    assert v["pattern"] == "motif" and v["at"] == [144.7, 10.4] and v["size"] == [97.0, 11.5]
    assert v["pattern-pitch"] == [16.9, 11.5]
    assert v["rx"] == 0  # square field corners: no rounded clip at the ends
    assert len(v["pattern-cells"]) == 9
    pts = [p for cell in v["pattern-cells"] for p in cell]
    assert all(0 <= x <= 16.9 and 0 <= y <= 11.5 for x, y in pts)
    assert any(x == 0 for x, _ in pts) and any(x == 16.9 for x, _ in pts)  # cells flush with the tile's sides
    assert any(y == 11.5 for _, y in pts)
    assert v["pattern-offset"] == v["at"]  # the tile's phase starts at the field's left and top edges
    for x in d["views"]["front"]["panel"]["decor"]:
        assert x.get("pattern") != "vent", x["id"]


def test_crs504_cage_vent_small_holes_are_diamonds_and_the_ends_leave_no_slivers():
    v = decor(load(CRS504), "front", "cage-vent")
    small = [c for c in v["pattern-cells"]
             if max(p[0] for p in c) - min(p[0] for p in c) < 2 and max(p[1] for p in c) - min(p[1] for p in c) < 2]
    diamonds = [c for c in small if len(c) == 4]
    assert len(small) == len(diamonds) == 2  # the two small holes of the period, one at each edge of the band
    for c in diamonds:
        xs, ys = [p[0] for p in c], [p[1] for p in c]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        assert max(xs) - min(xs) == pytest.approx(1.6) and max(ys) - min(ys) == pytest.approx(1.6)
        # every corner sits on an axis through the centre: a square turned 45 degrees, not an upright one
        assert all(p[0] == pytest.approx(cx) or p[1] == pytest.approx(cy) for p in c)
    # the field ends on 12.5 mm of the 16.9 mm tile, where the cut leaves no sliver of a slot (measured: the
    # smallest piece touching the cut is 8.2 square mm; the earlier 97.7 left 0.4)
    assert v["size"][0] % 16.9 == pytest.approx(12.5, abs=0.01)


def test_crs504_cage_bracket_is_one_continuous_line_with_hooked_ends_and_set_in_numerals():
    d = load(CRS504)
    assert not [x for x in d["views"]["front"]["panel"]["decor"] if x["id"].startswith("cage-bracket-")]
    silk = d["views"]["front"]["silkscreen"]
    b = [s for s in silk if s.get("id") == "cage-bracket"]
    assert len(b) == 1 and b[0]["filled"] is False and b[0]["stroke-width"] == 0.25
    path = b[0]["path"].split()
    assert path[:3] == ["M", "144.9", "25.3"] and path[-3:] == ["L", "242.3", "25.3"]  # both ends hook down
    assert path.count("Q") == 2
    # the line breaks only for the numerals printed in it
    numerals = {s["text"]: s["at"] for s in silk if s.get("for", "").startswith("qsfp-")}
    assert sorted(numerals) == ["1", "2", "3", "4"]
    assert path.count("M") == 5  # four breaks, one per numeral


def test_crs504_supplies_carry_handles_latches_and_screw_holes_and_their_legends_are_drawn_larger():
    d = load(CRS504)
    for i, dx in ((1, 0.0), (2, 59.9)):
        h, latch = decor(d, "front", f"psu-{i}-handle"), decor(d, "front", f"psu-{i}-latch")
        assert (h["kind"], h["size"], h["fill"]) == ("handle", [6.0, 36.0], "#a4a5a5")  # drawing: 6.0 x 36 mm bar
        assert h["at"] == [pytest.approx(30.5 + dx), 4.3]
        assert (latch["kind"], latch["size"], latch["fill"]) == ("latch", [7.1, 14.3], "#4f566a")
        assert latch["at"] == [pytest.approx(13.7 + dx), 5.5]
    holes = [x for x in d["views"]["front"]["panel"]["decor"] if x["kind"] == "screw-hole"]
    assert len(holes) == 6 and all(x["fill"] == "#020202" and x["size"] == [2.0, 2.0] for x in holes)
    legend = {s["text"]: s["font-size"] for s in d["views"]["front"]["silkscreen"]
              if s.get("text") in ("100-240 V 50/60 Hz", "PSU 1", "PSU 2")}
    assert legend == {"100-240 V 50/60 Hz": 2.6, "PSU 1": 2.2, "PSU 2": 2.2}  # cap height 1.9 and 1.6 mm, was 1.1


def test_crs504_supply_vents_are_rects_of_slots_measured_on_the_drawing():
    d = load(CRS504)
    slots = {x["id"]: x for x in d["views"]["front"]["panel"]["decor"] if "-slot-" in x["id"]}
    assert len(slots) == 20
    assert all(s["fill"] == "#17191c" and s["vent"] == 1.0 and "pattern" not in s for s in slots.values())
    assert slots["psu-1-slot-a1"]["at"] == [16.3, 20.6] and slots["psu-1-slot-a1"]["size"] == [3.9, 7.8]
    assert slots["psu-1-slot-top-1"]["at"] == [23.6, 5.7] and slots["psu-1-slot-top-1"]["size"] == [6.4, 2.8]
    for k in ("a1", "a2", "a3", "b1", "b2", "b3", "top-1", "top-2", "top-3", "top-4"):
        first, second = slots[f"psu-1-slot-{k}"], slots[f"psu-2-slot-{k}"]
        assert second["at"][0] - first["at"][0] == pytest.approx(59.9, abs=0.01)
        assert second["at"][1] == first["at"][1] and second["size"] == first["size"]


def test_crs504_dc_terminal_and_jack_are_drawn_at_their_measured_places():
    d = load(CRS504)
    cap, housing, e1, e2 = (decor(d, "front", i) for i in (
        "dc-terminal-cap", "dc-terminal-housing", "dc-terminal-entry-1", "dc-terminal-entry-2"))
    assert (cap["at"], cap["size"]) == ([276.0, 25.1], [10.0, 4.1])
    assert (housing["at"], housing["size"]) == ([275.1, 29.2], [11.4, 8.2])
    assert cap["fill"] == housing["fill"] == "#90cc90" and e1["fill"] == e2["fill"] == "#405a40"
    assert e1["at"][0] < e2["at"][0] and e1["at"][1] == e2["at"][1] == 30.7
    jack = {i: decor(d, "front", i) for i in ("dc-jack-housing", "dc-jack-rim", "dc-jack-bore", "dc-jack-pin")}
    assert (jack["dc-jack-housing"]["at"], jack["dc-jack-housing"]["size"]) == ([289.8, 25.4], [10.3, 11.9])
    assert [jack[i]["fill"] for i in jack] == ["#464646", "#222222", "#141312", "#a49478"]
    # the rim and the bore are concentric on the pin
    centre = lambda x: (x["at"][0] + x["size"][0] / 2, x["at"][1] + x["size"][1] / 2)
    assert centre(jack["dc-jack-rim"]) == pytest.approx(centre(jack["dc-jack-bore"]))
    assert centre(jack["dc-jack-pin"])[0] == pytest.approx(centre(jack["dc-jack-bore"])[0])
    assert not [p for p in placements(d, "front") if p["ref"].startswith("common/dc-")]
    assert not [p for p in d["views"]["front"]["components"]["placements"] if p.get("id", "").startswith("dc-")]


def test_crs504_dc_legends_bracket_and_polarity_marks_are_drawn_for_the_chassis():
    d = load(CRS504)
    silk = {s.get("id"): s for s in d["views"]["front"]["silkscreen"] if s.get("id")}
    assert {"dc-bracket", "dc-terminal-polarity", "dc-jack-polarity"} <= set(silk)
    assert all(silk[i]["for"] == "chassis" and silk[i]["filled"] is False and silk[i]["stroke-width"] == 0.25
               for i in ("dc-bracket", "dc-terminal-polarity", "dc-jack-polarity"))
    assert silk["dc-bracket"]["at"] == [275.4, 20.8]
    assert silk["dc-terminal-polarity"]["at"] == [278.7, 23.5] and silk["dc-jack-polarity"]["at"] == [291.9, 23.5]
    legend = [s for s in d["views"]["front"]["silkscreen"] if s.get("text") == "36 - 60 V"]
    assert len(legend) == 1 and legend[0]["at"] == [288.6, 20.0] and legend[0]["for"] == "chassis"
    assert "36 - 60 V" in d["attrs"]["power"]["power-rating-label"] and "36 - 57 V" in d["attrs"]["power"]["power-dc-input"]
    assert "dc-terminal" in {g["what"] for g in d["gaps"]}


def test_crs504_rear_draws_only_the_earthing_stud_and_declares_the_rest():
    d = load(CRS504)
    rear = d["views"]["rear"]
    assert not rear.get("empty") and not rear.get("components")
    assert [x["id"] for x in rear["panel"]["decor"]] == ["rear-stud"]
    stud = rear["panel"]["decor"][0]
    assert stud["size"] == [4.3, 4.3] and stud["at"] == [8.85, 7.05]  # centred 11.0 mm from the right edge, 9.2 down
    gap = next(g for g in d["gaps"] if g["what"] == "rear-face")
    assert "4.3 mm" in gap["note"] and "11.0 mm" in gap["note"] and "9.2 mm" in gap["note"]


def test_crs504_colours_are_the_photographs_medians():
    d = load(CRS504)
    assert d["chassis"]["color"] == "#d4d4d4"
    assert decor(d, "front", "psu-1-module")["fill"] == decor(d, "front", "psu-2-module")["fill"] == "#9a9c9d"
    assert decor(d, "front", "mgmt-block")["fill"] == "#9a9c9c"
    note = d["provenance"]["colour"]["note"]
    for value in ("#d4d4d4", "#9a9c9d", "#9a9c9c", "#90cc90", "#405a40", "#464646", "#222222", "#141312", "#a49478"):
        assert value in note, value


def test_lamps_rest_with_the_lamp_components_colour_and_the_gap_says_so():
    for name in NAMES:
        d = load(name)
        note = next(g for g in d["gaps"] if g["what"] == "led-states")["note"]
        assert "resting colour comes from the lamp component and is not changed here" in note


# --- CRS520-4XS-16XQ-RM ------------------------------------------------------------------------------------------

def test_crs520_drawing_and_brochure_agree_and_the_power_legend_conflict_is_declared():
    d = load(CRS520)
    assert "443 x 367 x 44" in d["provenance"]["chassis"]["note"]
    assert "CRS520-4XS_DIMENSIONS_250534.pdf" in d["provenance"]["sources"]["note"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["power-figures"]["reason"] == "sources-disagree"
    assert "2,5 A" in gaps["power-figures"]["note"] and "10.25" in gaps["power-figures"]["note"]
    assert d["attrs"]["power"]["power-without-attachments-w"] == 123 and d["attrs"]["power"]["power-max-w"] == 150


def test_crs520_has_sixteen_qsfp28_cages_in_eight_stacked_pairs():
    d = load(CRS520)
    cages = [p for p in placements(d, "front") if p.get("group") == "qsfp28"]
    assert [p["id"] for p in cages] == [f"qsfp-{n}" for n in range(1, 17)]
    assert [p["rel-pos"] for p in cages] == list(range(1, 17))
    assert all(p["ref"] == "std/qsfp28@1" and p["attrs"] == {"media": "qsfp28", "speed": "100g"} for p in cages)
    by_id = {p["id"]: p for p in cages}
    for n in range(1, 17, 2):  # the metal prints 1 3 5 ... under the stacks and 2 4 6 ... over them
        assert by_id[f"qsfp-{n}"]["at"][1] > by_id[f"qsfp-{n + 1}"]["at"][1]
        assert by_id[f"qsfp-{n}"]["at"][0] == by_id[f"qsfp-{n + 1}"]["at"][0]
    assert by_id["qsfp-3"]["at"][0] - by_id["qsfp-1"]["at"][0] == pytest.approx(24.07, abs=0.05)
    assert len([p for p in placements(d, "front") if p.get("group") == "qsfp-leds"]) == 16 * 4  # four lamps a cage


def test_crs520_has_four_sfp28_cages_two_by_two_each_with_two_lamps():
    d = load(CRS520)
    cages = [p for p in placements(d, "front") if p.get("group") == "sfp28"]
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 5)]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp28", "speed": "25g"} for p in cages)
    by_id = {p["id"]: p for p in cages}
    assert by_id["cage-1"]["at"][1] > by_id["cage-2"]["at"][1] and by_id["cage-3"]["at"][1] > by_id["cage-4"]["at"][1]
    assert by_id["cage-3"]["at"][0] - by_id["cage-1"]["at"][0] == pytest.approx(19.3, abs=0.05)
    assert len([p for p in placements(d, "front") if p.get("group") == "sfp-leds"]) == 4 * 2


def test_crs520_front_carries_console_two_ten_gig_ports_reset_and_four_lamps():
    d = load(CRS520)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt-1", "10g"), ("mgmt-2", "10g")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    lamps = [p for p in placements(d, "front") if p.get("group") == "status-leds"]
    assert [p["id"] for p in lamps] == ["led-user", "led-power-2", "led-power-1", "led-fault"]
    assert {"CONSOLE", "RESET", "USER", "POWER 2", "POWER 1", "FAULT", "10G MGMT / BOOT", "100G QSFP28", "25G SFP28",
            "CRS520-4XS-16XQ"} <= text_of(d, "front")
    ports = [p for p in placements(d, "front") if p.get("group") in {"qsfp28", "sfp28", "mgmt", "console"}]
    assert len(ports) == 16 + 4 + 2 + 1  # page: 16 QSFP28, 4 SFP28, 2 x 10G; the console is on the metal
    gaps = {g["what"] for g in d["gaps"]}
    assert {"led-states", "left-wall", "top-and-bottom"} <= gaps


def test_crs520_supplies_and_fans_are_part_of_the_chassis_with_no_part_number():
    d = load(CRS520)
    assert not bays(d, "front") and not bays(d, "rear")
    assert d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]  # the page: 2 AC inputs
    assert all(p["group"] == "inlets" for p in inlets)
    decor = d["views"]["rear"]["panel"]["decor"]
    assert [x["id"] for x in decor if x.get("kind") == "fan-grille"] == ["fan-0", "fan-1", "fan-2", "fan-3"]
    assert {"POWER 1 / POWER 2", "1", "2", "3", "4"} <= text_of(d, "rear")
    gaps = {g["what"]: g for g in d["gaps"]}
    assert {"hot-swap-supplies", "hot-swap-fans", "optional-dc-supply"} <= set(gaps)
    assert "fan-redundancy" not in json.dumps(d["groups"])
    assert "G1483" not in json.dumps(d)  # no document prints the supply's number


def test_crs520_ears_and_the_rail_kit_are_declared_not_modelled():
    d = load(CRS520)
    gaps = {g["what"]: g for g in d["gaps"]}
    assert {"rack-rail-kit", "rear-support-ears"} <= set(gaps)
    assert "23-40 Rack Rail R0" in gaps["rack-rail-kit"]["note"] and "3-40_RACK_RAIL_R0_260621.pdf" in gaps["rack-rail-kit"]["note"]
    assert "kits" not in d["chassis"]


def test_crs520_walls():
    d = load(CRS520)
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["side-vent"]
    v = decor(d, "right", "side-vent")
    assert v["pattern"] == "holes"  # photograph 2352 shows round perforations
    assert (v["at"], v["size"]) == ([11.0, 14.0], [35.0, 17.0])  # unwarped from the photograph's wall quad
    assert (v["pattern-pitch"], v["pattern-offset"]) == ([3.6, 3.0], [11.0, 14.0])  # 10 columns and 6 rows of holes
    assert d["views"]["left"].get("empty")
    assert d["views"]["top"].get("empty") and d["views"]["bottom"].get("empty")


def test_crs520_front_strips_are_motif_tiles_of_the_measured_slots():
    d = load(CRS520)
    row1 = decor(d, "front", "top-vent-row-1")
    row2 = [decor(d, "front", f"top-vent-row-2-{k}") for k in "abc"]
    assert (row1["pattern"], row1["at"], row1["size"], row1["pattern-pitch"]) == ("motif", [4.1, 0.9], [434.0, 1.5], [5.09, 1.5])
    for f in [row1] + row2:
        assert f["pattern-offset"] == f["at"] and f["pattern-pitch"] == [5.09, 1.5] and f["rx"] == 0
        assert len(f["pattern-cells"]) == 1  # one row of slots in each field
        cell = f["pattern-cells"][0]
        assert (min(x for x, _ in cell), max(x for x, _ in cell)) == (0.55, 4.55)  # 4.0 mm slots, all one width
        assert (min(y for _, y in cell), max(y for _, y in cell)) == (0.0, 1.5)  # slots 1.5 mm tall
    assert all(f["at"][1] == 3.9 for f in row2)  # rows 3.0 mm apart: 0.9 and 3.9
    # the second row breaks at each legend: the gaps are whole slot pitches and hold the printed legends
    ends = [(f["at"][0], f["at"][0] + f["size"][0]) for f in row2]
    assert ends == [(4.1, pytest.approx(95.72)), (pytest.approx(110.99), pytest.approx(212.79)),
                    (pytest.approx(233.15), pytest.approx(438.1))]
    legends = {s["text"]: s for s in d["views"]["front"]["silkscreen"] if s.get("text") in ("100G QSFP28", "25G SFP28")}
    assert ends[0][1] < legends["100G QSFP28"]["at"][0] - 6 and legends["100G QSFP28"]["at"][0] + 6 < ends[1][0]
    assert ends[1][1] < legends["25G SFP28"]["at"][0] - 5 and legends["25G SFP28"]["at"][0] + 5 < ends[2][0]
    # the bottom edge is 54 shallow light notches 4.0 x 1.5 mm on the slot pitch, not black slots
    notches = [x for x in d["views"]["front"]["panel"]["decor"] if x["kind"] == "notch"]
    assert len(notches) == 54 and all(n["size"] == [4.0, 1.5] and n["fill"] == "#d3cac3" for n in notches)
    assert [n["at"][0] for n in notches][:3] == [4.65, 9.74, 14.83]
    assert notches[1]["at"][0] - notches[0]["at"][0] == pytest.approx(5.09, abs=0.01)
    assert all(n["at"][1] + n["size"][1] == 44.0 for n in notches)
    for x in d["views"]["front"]["panel"]["decor"]:
        assert x.get("pattern") != "vent", x["id"]


def test_crs520_front_prints_every_port_numeral_and_brackets_the_groups_and_lamps():
    d = load(CRS520)
    silk = d["views"]["front"]["silkscreen"]
    qsfp = {s["text"]: s["for"] for s in silk if s.get("for", "").startswith("qsfp-")}
    assert sorted(qsfp, key=int) == [str(n) for n in range(1, 17)]
    assert all(qsfp[n] == f"qsfp-{n}" for n in qsfp)
    sfp = {s["text"]: s["for"] for s in silk if s.get("for", "").startswith("cage-")}
    assert sorted(sfp) == ["1", "2", "3", "4"]
    ids = {s["id"]: s for s in silk if s.get("id", "").startswith("bracket-")}
    assert set(ids) == {"bracket-100g", "bracket-25g", "bracket-user", "bracket-fault"}
    assert all(s["filled"] is False and s["stroke-width"] == 0.2 for s in ids.values())
    # the hooks stop short of the lamps over the cages (3.0 and 2.0 mm long) so that no lamp paints over the line
    assert ids["bracket-100g"]["path"].startswith("M 7.6 9.3") and ids["bracket-100g"]["path"].endswith("198.1 9.3")
    assert ids["bracket-25g"]["path"].startswith("M 205.5 8.3") and ids["bracket-25g"]["path"].endswith("240.4 8.3")
    # the lamp brackets start over and under the left lamp column and run right to USER and FAULT
    assert ids["bracket-user"]["path"].startswith("M 279.6") and ids["bracket-fault"]["path"].startswith("M 279.6")


def test_crs520_rear_modules_carry_handles_thumbscrews_latches_chassis_screws_and_the_legend_underline():
    d = load(CRS520)
    for i, x in ((1, 171.3), (2, 240.4), (3, 309.0), (4, 376.8)):
        h, core = decor(d, "rear", f"fan-{i}-handle"), decor(d, "rear", f"fan-{i}-handle-core")
        assert (h["at"], h["size"], h["fill"]) == ([x, 5.0], [4.6, 38.0], "#776d64") and core["fill"] == "#524339"
        t = decor(d, "rear", f"fan-{i}-thumbscrew")
        assert (t["size"], t["fill"]) == ([7.2, 13.4], "#6d635c") and t["at"][0] < h["at"][0]  # left of the handle
    for i in (1, 2):
        h = decor(d, "rear", f"psu-{i}-handle")
        assert (h["size"], h["fill"]) == ([4.0, 39.8], "#776d64")
        assert decor(d, "rear", f"psu-{i}-thumbscrew")["fill"] == "#737268"
        assert decor(d, "rear", f"psu-{i}-latch-top")["fill"] == decor(d, "rear", f"psu-{i}-latch-bottom")["fill"] == "#89978e"
    screws = [x for x in d["views"]["rear"]["panel"]["decor"] if x["kind"] == "earth-screw"]
    assert len(screws) == 5 and all(s["size"] == [4.4, 4.4] and s["fill"] == "#51453b" for s in screws)
    silk = {s["id"]: s for s in d["views"]["rear"]["silkscreen"] if s.get("id")}
    assert silk["legend-underline"]["path"] == "M 131.8 17.4 L 157.6 17.4"  # under POWER 1 / POWER 2, 25.8 mm
    for i in range(1, 5):  # the arrowhead after each fan numeral is a filled triangle
        assert silk[f"fan-{i}-arrow"]["filled"] is True and silk[f"fan-{i}-arrow"]["path"].endswith("Z")
    assert len([k for k in silk if k.startswith("chassis-screw-cross-")]) == 5


def test_crs520_rear_honeycombs_are_scaled_to_the_photographs_hexagons():
    d = load(CRS520)
    for i in ("fan-0", "fan-1", "fan-2", "fan-3"):
        f = decor(d, "rear", i)
        assert f["pattern"] == "vent" and f["size"] == [37.5, 37.5] and f["rx"] == 18.75
        assert f["pattern-pitch"] == [8.1, 4.67]
        # a hole sits on the ring's centre: the lattice phase is the ring centre
        assert f["pattern-offset"] == [f["at"][0] + 18.75, f["at"][1] + 18.75]
    assert [decor(d, "rear", f"fan-{i}")["pattern-offset"][0] for i in range(4)] == [195.9, 265.0, 333.6, 401.4]
    # ratio of the scaled tile to the renderer's 8.86 x 5.11 tile is the same on both axes
    assert 8.1 / 8.86 == pytest.approx(4.67 / 5.11, abs=0.001)
    for i in range(4):
        h = decor(d, "rear", f"fan-hub-{i}")
        assert h["kind"] == "fan-hub" and h["size"] == [20.0, 20.0] and h["rx"] == 10.0 and h["fill"] == "#5d493d"
        g = decor(d, "rear", f"fan-{i}")
        assert (h["at"][0] + 10.0, h["at"][1] + 10.0) == pytest.approx(g["pattern-offset"])
    p1, p2 = decor(d, "rear", "psu-1-vent"), decor(d, "rear", "psu-2-vent")
    assert (p1["pattern-pitch"], p1["pattern-offset"], p1["at"], p1["size"]) == (
        [9.39, 5.42], [10.6, 10.3], [7.8, 8.0], [27.0, 28.4])
    assert p2["pattern-pitch"] == [9.39, 5.42] and p2["pattern-offset"] == [74.0, 10.3] and p2["at"] == [71.2, 8.0]
    assert 9.39 / 8.86 == pytest.approx(5.42 / 5.11, abs=0.001)


def test_crs520_colours_are_the_photographs_medians():
    d = load(CRS520)
    assert d["chassis"]["color"] == "#e0dcd5"
    for i in ("console-block", "mgmt-block"):
        assert decor(d, "front", i)["fill"] == "#e6e3df"
    for i in ("fan-1-module", "fan-2-module", "fan-3-module", "fan-4-module"):
        assert decor(d, "rear", i)["fill"] == "#5d493d"
    for i in ("psu-1-module", "psu-2-module"):
        assert decor(d, "rear", i)["fill"] == "#736f62"
    note = d["provenance"]["colour"]["note"]
    for value in ("#e0dcd5", "#e6e3df", "#4e3d33", "#5d493d", "#615d52", "#736f62", "#bbbbb7"):
        assert value in note, value


# --- every device ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", NAMES)
def test_the_ears_are_shipped_flush_and_never_placed(name):
    d = load(name)
    default = [p for p in d["chassis"]["ears"]["positions"] if p.get("default")]
    assert [p["name"] for p in default] == ["flush"]
    assert not [p for v in d["views"].values() for p in (v.get("components") or {}).get("placements") or []
                if p["ref"] == "common/rack-ear@1"]
    assert "kits" not in d["chassis"]


@pytest.mark.parametrize("name", NAMES)
def test_the_logo_is_reserved_not_drawn(name):
    front = load(name)["views"]["front"]
    assert [r["id"] for r in front["regions"]] == ["logo-zone"]
    assert not [s for s in front["silkscreen"] if "mikrotik" in str(s.get("text", "")).lower()]


@pytest.mark.parametrize("name", NAMES)
def test_every_legend_is_readable_at_the_device_pages_scale(name):
    d = load(name)
    for view in d["views"].values():
        for s in view.get("silkscreen") or []:
            if s.get("text"):
                assert s["font-size"] >= 1.5, s


# --- the DCIM export --------------------------------------------------------------------------------------------

def exported(name):
    model = MODELS[name][0]
    docs = [yaml.safe_load(f.read_text()) for f in (ROOT / "library/exports/netbox/device-types/MikroTik").glob("*.yaml")]
    mine = [x for x in docs if x["model"] == model]
    assert len(mine) == 1
    return mine[0]


def count(doc, kind):
    return sum(1 for i in doc["interfaces"] if i["type"] == kind)


@pytest.mark.parametrize("name", NAMES)
def test_dcim_device_type_exports_one_per_device(name):
    doc = exported(name)
    assert doc["u_height"] == 1 and doc["manufacturer"] == "MikroTik"


def test_dcim_crs504_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS504)
    assert count(a, "100gbase-x-qsfp28") == 4
    assert count(a, "100base-tx") == 1
    assert len(a["power-ports"]) == 2  # the two C14 inlets; the DC jack and the terminal are not placed
    assert len(a["console-ports"]) == 1


def test_dcim_crs520_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS520)
    assert count(a, "100gbase-x-qsfp28") == 16 and count(a, "25gbase-x-sfp28") == 4
    assert count(a, "10gbase-t") == 2
    assert len(a["power-ports"]) == 2  # the two C14 inlets at the rear
    assert len(a["console-ports"]) == 1


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES)
def test_the_committed_exports_are_what_the_exporter_writes_now(name, target, tmp_path, monkeypatch):
    dist = ROOT / "library/dist"
    assert (dist / "devices.json").exists(), "run the build first: this reads library/dist"
    monkeypatch.setattr(dx, "RASTER", False)
    dx.export_device(dx.Dist(str(dist)), name, str(tmp_path), str(dist))
    rel = Path(target) / "device-types" / "MikroTik" / f"{MODELS[name][0]}.yaml"
    assert (tmp_path / rel).read_text() == (ROOT / "library/exports" / rel).read_text()


def test_the_lock_files_match_the_devices():
    lib = ROOT / "library"
    assert not [f for f in devicelock.check(lib) if f[0].startswith("mikrotik/")]
    known = devicelock.load_lock(lib)["devices"]
    for name in NAMES:
        entry = known[f"mikrotik/{name}"]
        assert entry["version"] == load(name)["version"] == "1.0.0"
        per_device = json.loads((DEVICES / name / "device.lock.json").read_text())
        assert per_device["gaps"] == entry["gaps"]

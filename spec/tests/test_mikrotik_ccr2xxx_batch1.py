"""MikroTik's Cloud Core Routers CCR2xxx, batch 1: the CCR2116-12G-4S+ and the CCR2004-1G-12S+2XS.

Each takes its envelope from the brochure and the product page, which agree (no dimensions drawing is held):
443 x 199 x 44 mm and 443 x 224 x 44 mm. Each has two fixed AC inlets and no supply bay: the rear photographs show a
plain C14 inlet with a wire clip and no module, and no held document prints a supply part number. The CCR2004-16G-2S+
is not in this batch: its rear photograph shows two removable supply modules. The device names are lower case with
-plus for each +.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/mikrotik"
CCR2116 = "ccr2116-12g-4s-plus"
CCR2004 = "ccr2004-1g-12s-plus-2xs"
MODELS = {
    CCR2116: ("CCR2116-12G-4S+", "CCR2116"),
    CCR2004: ("CCR2004-1G-12S+2XS", "CCR2004"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth: the brochure and the page agree
    CCR2116: (443.0, 44.0, 199.0),
    CCR2004: (443.0, 44.0, 224.0),
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return (d["views"][view].get("components") or {}).get("bays") or []


def refs(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def group(d, view, name):
    return [p for p in placements(d, view) if p.get("group") == name]


def text_of(d, view):
    return {s.get("text") for s in d["views"][view]["silkscreen"]}


def decor(d, view):
    return {x["id"]: x for x in d["views"][view]["panel"]["decor"] if "id" in x}


def gaps(d):
    return {g["what"]: g for g in d["gaps"]}


@pytest.mark.parametrize("name", NAMES)
def test_the_device_is_named_as_the_maker_prints_it(name):
    d = load(name)
    model, series = MODELS[name]
    assert d["name"] == name
    assert d["manufacturer"] == "MikroTik"
    assert d["model"] == model
    assert d["portfolio"] == {"line": "Routers", "family": "Cloud Core Router", "series": series}
    assert "+" not in name
    assert d["version"] == "1.0.0"
    assert list(d["configurations"]["base"]["part-numbers"]) == [model]


@pytest.mark.parametrize("name", NAMES)
def test_the_envelope_is_the_brochures_and_the_pages(name):
    d = load(name)
    w, h, depth = ENVELOPE[name]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, depth, 1)
    assert d["views"]["front"]["size"] == {"w": w, "h": h}
    assert d["views"]["top"]["size"] == {"w": w, "h": depth}
    assert d["views"]["left"]["size"] == {"w": depth, "h": h}
    assert d["views"]["right"]["size"] == {"w": depth, "h": h}
    note = d["provenance"]["chassis"]["note"]
    assert f"443 x {int(depth)} x 44" in note  # brochure and page agree; no drawing is held
    assert "retaining clips" in note


def test_the_ccr2004_16g_2s_plus_is_left_out_whole():
    """Its rear photograph (2095) shows two removable supply modules with handles, which this batch does not model."""
    assert not (DEVICES / "ccr2004-16g-2s-plus").exists()


# --- CCR2116-12G-4S+ ---------------------------------------------------------------------------------------------

def test_ccr2116_has_twelve_lamped_gigabit_jacks_in_three_blocks_of_four():
    d = load(CCR2116)
    jacks = group(d, "front", "rj45")
    assert [p["id"] for p in jacks] == [f"port-{n}" for n in range(1, 13)]
    assert [p["rel-pos"] for p in jacks] == list(range(1, 13))
    assert all(p["ref"] == "common/rj45-ganged-eth@1" and p["attrs"] == {"media": "rj45", "speed": "1g"}
               for p in jacks)
    xs = [p["at"][0] for p in jacks]
    assert xs == sorted(xs) and len({p["at"][1] for p in jacks}) == 1
    step = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert step == [17.0, 17.0, 17.0, 21.2, 17.0, 17.0, 17.0, 21.2, 17.0, 17.0, 17.0]  # four to a gang, a gutter
    assert {"GIGABIT ETHERNET"} <= text_of(d, "front")
    assert {str(n) for n in range(1, 13)} <= text_of(d, "front")


def test_ccr2116_has_four_sfp_plus_cages_numbered_by_column_and_eight_arrow_lamps():
    d = load(CCR2116)
    cages = group(d, "front", "sfp-plus")
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 5)]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp-plus", "speed": "10g"} for p in cages)
    by_id = {p["id"]: p for p in cages}
    for n in (1, 3):  # the metal prints 1 and 3 under the stacks and 2 and 4 over them
        assert by_id[f"cage-{n}"]["at"][1] > by_id[f"cage-{n + 1}"]["at"][1]
        assert by_id[f"cage-{n}"]["at"][0] == by_id[f"cage-{n + 1}"]["at"][0]
    assert len(group(d, "front", "sfp-leds")) == 8
    assert "SFP+" in text_of(d, "front")


def test_ccr2116_has_console_management_usb_two_buttons_and_four_lamps():
    d = load(CCR2116)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "1g")]  # the brochure's 13th gigabit port
    assert [p["id"] for p in refs(d, "front", "std/usb-a@1")] == ["usb"]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-mode", "btn-reset"]
    assert len(group(d, "front", "status-leds")) == 4
    assert {"CONSOLE", "ETH/BOOT", "USB", "MODE", "RESET", "USER", "FAULT", "PWR 2", "PWR 1", "CCR2116-12G-4S+"} \
        <= text_of(d, "front")
    ports = [p for p in placements(d, "front") if p.get("group") in {"rj45", "sfp-plus", "mgmt", "console", "usb"}]
    assert len(ports) == 12 + 4 + 1 + 1 + 1


def test_ccr2116_m2_slot_is_a_gap_and_exports_no_port():
    d = load(CCR2116)
    g = gaps(d)["m2-slot"]
    assert "Number of M.2 slots" in g["note"]
    assert not [p for v in d["views"] for p in placements(d, v) if "m2" in p["ref"].lower() or "m.2" in str(p.get("attrs"))]
    assert "m2" not in json.dumps(exported(CCR2116)["interfaces"]).lower()


def test_ccr2116_rear_has_two_inlets_four_fans_and_one_more_round_opening():
    d = load(CCR2116)
    assert not bays(d, "rear") and d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]  # the page and the brochure: 2 AC inputs
    assert all(p["group"] == "inlets" for p in inlets)
    r = decor(d, "rear")
    assert [k for k, x in r.items() if x["kind"] == "fan-grille"] == ["fan-0", "fan-1", "fan-2", "fan-3"]  # page: 4 fans
    assert r["psu-opening"]["kind"] == "round-vent"  # the fifth opening, between the inlets, is a vent
    assert {"POWER 1", "POWER 2"} <= text_of(d, "rear")
    assert "100-240 V ~2 A MAX, 50/60 Hz" in text_of(d, "rear")
    assert {"psu-slots", "fan-count"} <= set(gaps(d))


def test_ccr2116_power_figures_conflict_is_declared():
    d = load(CCR2116)
    g = gaps(d)["power-figures"]
    assert g["reason"] == "sources-disagree"
    assert all(x in g["note"] for x in ("72", "83", "60", "12 V", "10.8"))
    p = d["attrs"]["power"]
    assert p["power-max-w"] == 72 and p["power-without-attachments-w"] == 60
    assert p["power-max-w-page"] == 83
    assert "adapter" in p["power-adapter-nominal"]


def test_ccr2116_right_wall_shows_a_vent_and_left_wall_is_plain():
    d = load(CCR2116)
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["side-vent"]
    assert d["views"]["left"].get("empty")


# --- CCR2004-1G-12S+2XS ----------------------------------------------------------------------------------------

def test_ccr2004_has_two_sfp28_cages_stacked_and_twelve_sfp_plus_cages_with_lamps():
    d = load(CCR2004)
    x28 = group(d, "front", "sfp28")
    assert [p["id"] for p in x28] == ["cage-28-1", "cage-28-2"]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp28", "speed": "25g"} for p in x28)
    assert x28[0]["at"][1] > x28[1]["at"][1] and x28[0]["at"][0] == x28[1]["at"][0]  # 1 lower, 2 upper, as printed
    assert len(group(d, "front", "sfp28-leds")) == 4
    cages = group(d, "front", "sfp-plus")
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 13)]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp-plus", "speed": "10g"} for p in cages)
    xs = [p["at"][0] for p in cages]
    assert all(round(b - a, 2) == 19.8 for a, b in zip(xs, xs[1:]))
    assert len(group(d, "front", "sfp-leds")) == 24  # ACT and 10G over each cage
    assert {f"SFP+ {n}" for n in range(1, 13)} <= text_of(d, "front")
    assert {"ACT", "10G", "25G SFP28"} <= text_of(d, "front")


def test_ccr2004_has_console_over_management_reset_and_four_lamps():
    d = load(CCR2004)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "1g")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    assert len(group(d, "front", "status-leds")) == 4
    assert {"CONSOLE", "MGMT/BOOT", "RESET", "USER", "FAULT", "PWR 2", "PWR 1", "CCR2004-1G-12S+2XS"} \
        <= text_of(d, "front")
    ports = [p for p in placements(d, "front") if p.get("group") in {"sfp28", "sfp-plus", "mgmt", "console"}]
    assert len(ports) == 2 + 12 + 1 + 1
    assert not refs(d, "front", "std/usb-a@1")  # no USB jack on this face


def test_ccr2004_rear_has_two_inlets_two_fans_and_a_finned_heatsink():
    d = load(CCR2004)
    assert not bays(d, "rear") and d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    r = decor(d, "rear")
    assert [k for k, x in r.items() if x["kind"] == "fan-grille"] == ["fan-0", "fan-1"]  # page: 2 fans
    assert r["heatsink"]["kind"] == "heatsink"  # chassis art, not a third fan
    assert "100-240 V ~1 A MAX 50/60 Hz" in text_of(d, "rear")
    assert {"psu-slots", "fan-count", "right-wall"} <= set(gaps(d))


def test_ccr2004_power_figures_conflict_is_declared():
    d = load(CCR2004)
    g = gaps(d)["power-figures"]
    assert g["reason"] == "sources-disagree"
    assert all(x in g["note"] for x in ("49", "60", "31"))
    p = d["attrs"]["power"]
    assert p["power-max-w"] == 49 and p["power-max-w-page"] == 60 and p["power-without-attachments-w"] == 31


def test_ccr2004_left_wall_is_plain_and_the_right_is_not_shown():
    d = load(CCR2004)
    assert d["views"]["left"].get("empty") and d["views"]["right"].get("empty")


# --- every device ---------------------------------------------------------------------------------------------

def slant_degrees(cell):
    """The angles from the vertical of a cell's edges that are neither horizontal nor vertical."""
    import math
    out = []
    for (x0, y0), (x1, y1) in zip(cell, cell[1:] + cell[:1]):
        if abs(y1 - y0) > 0.5 and abs(x1 - x0) > 0.5:
            out.append(round(math.degrees(math.atan2(abs(x1 - x0), abs(y1 - y0))), 1))
    return out


@pytest.mark.parametrize("name", NAMES)
def test_no_front_vent_is_drawn_with_the_hexagon_pattern(name):
    front = load(name)["views"]["front"]["panel"]["decor"]
    assert [x["id"] for x in front if x.get("pattern") == "vent"] == []
    assert [x["id"] for x in front if x.get("kind") == "vent-field" and x["pattern"] != "motif"] == []


def test_ccr2116_front_band_is_one_motif_period_of_v_and_lambda_strokes():
    band = decor(load(CCR2116), "front")["vent-field"]
    assert band["pattern"] == "motif" and band["pattern-pitch"] == [31.2, 7.0]
    # the tile is 0.2 mm taller than the strokes and begun 0.1 mm above the field, so no cell lies on its
    # top or bottom edge (a cell on the edge left a faint 1 px seam between the strokes along it)
    assert band["at"] == [44.3, 11.6] and band["pattern-offset"] == [44.3, 11.5]
    assert band["size"][1] == 6.8  # the field's height: one row of strokes
    cells = band["pattern-cells"]
    assert [len(c) for c in cells] == [4, 6, 4, 6, 4]  # "\", V, "/", lambda (cut at the tile's edge), its foot
    assert all(0 <= x <= 31.2 and 0.1 <= y <= 6.9 for c in cells for x, y in c)
    assert min(y for c in cells for _, y in c) == 0.1 and max(y for c in cells for _, y in c) == 6.9
    slants = {a for c in cells for a in slant_degrees(c)}
    assert slants == {45.0}  # every slanted edge, the V's and the lambda's too, at 45 degrees


def test_ccr2116_front_band_meets_in_a_v_and_a_lambda_and_runs_six_and_seven_tenths_periods():
    band = decor(load(CCR2116), "front")["vent-field"]
    v, lam = band["pattern-cells"][1], band["pattern-cells"][3]
    # the V's two strokes meet at the foot (its lowest point), the lambda's at the head
    assert max(y for _, y in v) > 6.8 and min(y for x, y in v if 0 < x < 31) == 0.1
    assert min(y for x, y in lam if 20 < x < 31) < 0.2 and max(y for _, y in lam) == 6.9
    assert abs(band["size"][0] / band["pattern-pitch"][0] - 6.75) < 0.05  # six periods and 0.7 of a seventh
    assert int(band["size"][0] // band["pattern-pitch"][0]) == 6
    assert -(-band["size"][0] // band["pattern-pitch"][0]) == 7  # seven V points are cut or whole across it


HEX_TILE = [10.184, 5.88]  # two columns of a honeycomb whose hexagons repeat every 5.88 mm down: photographs 2116 and 1936
HEX_ACROSS_CORNERS = 5.36
GUARDS = {
    CCR2116: {"psu-opening": [72.4, 20.9], "fan-0": [223.7, 21.6], "fan-1": [264.4, 21.6],
              "fan-2": [304.4, 21.6], "fan-3": [345.0, 21.6]},
    CCR2004: {"fan-0": [170.2, 23.9], "fan-1": [385.5, 23.0]},
}


def tile_area(cells):
    total = 0.0
    for c in cells:
        total += abs(sum(c[i][0] * c[(i + 1) % len(c)][1] - c[(i + 1) % len(c)][0] * c[i][1]
                         for i in range(len(c)))) / 2
    return total


@pytest.mark.parametrize("name", NAMES)
def test_rear_guards_are_hexagons_at_the_photographed_pitch_centred_on_their_fans(name):
    d = load(name)
    r = decor(d, "rear")
    assert [k for k, x in r.items() if x.get("pattern")] == list(GUARDS[name])
    for k, centre in GUARDS[name].items():
        g = r[k]
        assert g["pattern"] == "motif" and g["pattern-pitch"] == HEX_TILE and g["pattern-offset"] == centre
        assert [g["at"][i] + g["size"][i] / 2 for i in (0, 1)] == pytest.approx(centre)  # a hexagon at the hub's centre
        assert g["size"] == [37.0, 37.0] and g["rx"] == 18.5 and g["vent"] == 1.0
        widths = sorted(max(p[0] for p in c) - min(p[0] for p in c) for c in g["pattern-cells"])
        assert widths[-1] == pytest.approx(HEX_ACROSS_CORNERS, abs=0.01)  # the one whole hexagon of the tile
        # two hexagons of 5.36 mm across corners fill 2 x 3/2 x 3^0.5 x 2.68^2 mm of the tile: the pieces sum to it
        assert tile_area(g["pattern-cells"]) == pytest.approx(2 * 1.5 * 3 ** 0.5 * 2.68 ** 2, abs=0.05)


def test_the_hexagon_tile_is_a_regular_lattice_at_the_photographs_column_spacing():
    g = decor(load(CCR2004), "rear")["fan-0"]
    w, h = g["pattern-pitch"]
    assert w / 2 == pytest.approx(h * 3 ** 0.5 / 2, abs=0.002)  # columns 5.09 mm apart: photograph 1936 read 5.06, 2116 5.1
    assert decor(load(CCR2004), "rear")["fan-1"]["pattern-cells"] == g["pattern-cells"]


def test_ccr2116_has_no_vent_pattern_gap():
    assert "vent-pattern" not in gaps(load(CCR2116))


def test_ccr2116_right_wall_vent_is_round_holes_not_hexagons():
    side = {x["id"]: x for x in load(CCR2116)["views"]["right"]["panel"]["decor"]}["side-vent"]
    assert side["pattern"] == "holes"


def test_ccr2004_front_band_is_sixty_slanted_slots_in_five_drawings():
    d = load(CCR2004)
    f = decor(d, "front")
    main = f["vent-field"]
    pitch = main["pattern-pitch"][0]
    assert pitch == 4.736 and main["pattern-pitch"][1] == 9.5 and main["pattern-offset"] == [main["at"][0], 4.8]
    assert main["at"][1] == 4.9 and main["size"][1] == 9.3
    full = round((main["size"][0] - 2.4 - 2.70) / pitch) + 1
    assert full == 41  # slots 11 to 51
    assert [len(c) for c in main["pattern-cells"]] == [4, 8]  # the slot, and its corner wrapped past the tile's edge
    slants = [a for c in main["pattern-cells"] for a in slant_degrees(c)]
    assert slants and all(abs(a - 16.2) < 0.2 for a in slants)  # a 2.70 mm lean over 9.3 mm
    dashes = [f["vent-dashes-left"], f["vent-dashes-right"]]
    assert [round((x["size"][0] - 2.4 - 0.725) / pitch) + 1 for x in dashes] == [5, 5]
    assert all(x["size"][1] == 2.5 and x["pattern"] == "motif" for x in dashes)
    left = [f[f"vent-ramp-left-{n}"] for n in range(1, 6)]
    right = [f[f"vent-ramp-right-{n}"] for n in range(1, 5)]
    heights = [x["size"][1] for x in left + right]
    assert heights == sorted(heights[:5]) + sorted(heights[5:], reverse=True)  # the sweep down and back up
    assert 5 + 5 + full + 4 + 5 == 60
    # each shortened slot starts one pitch after the last, on the same row of slots
    xs = [x["at"][0] + 0.0 for x in left] + [main["at"][0]]
    assert all(abs((b - a) - pitch) < 0.7 for a, b in zip(xs, xs[1:])), xs
    for x in left + right:  # a tile 0.2 mm taller than the field, begun 0.1 mm above it
        assert x["pattern"] == "motif" and x["pattern-pitch"][0] == x["size"][0]
        assert x["pattern-pitch"][1] == pytest.approx(x["size"][1] + 0.2, abs=0.001)


def test_ccr2004_front_band_cells_keep_clear_of_the_tiles_top_and_bottom_edges():
    # A cell on the tile's top or bottom edge left a faint 1 px seam between the slots along it. Every
    # cell sits 0.1 mm inside both, and the tile is begun 0.1 mm above the field so the slots still
    # start where the photograph has them. (A slot is 4.93 mm across, wider than the 4.736 mm pitch, so
    # the main field's one slot is still cut where it crosses the tile's side edge.)
    f = decor(load(CCR2004), "front")
    fields = [x for x in f.values() if x.get("pattern") == "motif"]
    assert len(fields) == 12
    for x in fields:
        th = x["pattern-pitch"][1]
        ys = [p[1] for c in x["pattern-cells"] for p in c]
        assert min(ys) == pytest.approx(0.1, abs=0.001) and max(ys) == pytest.approx(th - 0.1, abs=0.001), x["id"]
        assert x["pattern-offset"][1] == pytest.approx(x["at"][1] - 0.1, abs=0.001), x["id"]


def test_ccr2004_vent_gap_names_the_curved_edge_and_no_chevrons_are_asked_for():
    g = gaps(load(CCR2004))["vent-pattern"]
    assert "curve" in g["note"] and "chevrons" not in json.dumps(g)


def test_ccr2004_face_and_plates_are_the_photographs_medians():
    d = load(CCR2004)
    assert d["chassis"]["color"] == "#c4c4c4"
    f = decor(d, "front")
    assert f["mgmt-block"]["fill"] == "#787674" and f["sfp28-strip"]["fill"] == "#898784"
    r = decor(d, "rear")
    assert all(r[k]["fill"] == "#c4c4c4" for k in ("fan-hub-0", "fan-hub-1"))
    note = d["provenance"]["colour"]["note"] + d["provenance"]["colour-sample"]["note"]
    for value in ("#c4c4c4", "#787674", "#898784", "#414142", "#a6a5a5", "#d9d9d9", "#9a9a98"):
        assert value in note


def test_ccr2116_front_face_is_the_front_median_and_the_rear_is_painted_from_unshaded_patches():
    d = load(CCR2116)
    assert d["chassis"]["color"] == "#dddddd"
    prov = d["provenance"]["colour-sample"]["note"] + d["provenance"]["colour"]["note"]
    assert "#dbdbde" in prov and "#dddddd" in prov and "68600" in prov
    r = decor(d, "rear")
    plate = r["rear-plate"]
    assert plate["kind"] == "rear-plate" and plate["at"] == [0.0, 0.0] and plate["size"] == [443.0, 44.0]
    assert plate["fill"] == "#c1c1c0"
    assert list(r)[0] == "rear-plate"  # painted first: under the grilles and the inlets
    hubs = [k for k, x in r.items() if x["kind"] == "fan-hub"]
    assert hubs == ["psu-opening-hub", "fan-hub-0", "fan-hub-1", "fan-hub-2", "fan-hub-3"]
    assert all(r[k]["fill"] == plate["fill"] for k in hubs)
    for sample in ("#c1c1c0", "#c0bfbf", "#c4c4c4", "78750", "35000", "8750", "#c0c0c0"):
        assert sample in prov  # the rear's three patches, their median, and the NetBox rear's median


def test_ccr2004_rear_face_agrees_with_the_front_and_keeps_its_sample():
    d = load(CCR2004)
    assert d["chassis"]["color"] == "#c4c4c4"
    assert "rear-plate" not in decor(d, "rear")
    assert "#c5c5c5" in d["provenance"]["colour"]["note"] and "26855" in d["provenance"]["colour"]["note"]


def test_ccr2004_heatsink_is_a_grey_base_with_twenty_one_silver_fins_and_two_rims():
    d = load(CCR2004)
    rear = d["views"]["rear"]
    r = decor(d, "rear")
    block = r["heatsink"]
    assert block["at"] == [200.0, 7.5] and block["size"] == [166.9, 36.5] and block["fill"] == "#414142"
    fins = [x for x in r.values() if x["kind"] == "heatsink-fin"]
    assert [x["id"] for x in fins] == [f"heatsink-fin-{n:02d}" for n in range(1, 22)]
    assert {x["fill"] for x in fins} == {"#a6a5a5"} and {x["size"][0] for x in fins} == {1.4}
    xs = [x["at"][0] for x in fins]
    assert xs == pytest.approx([211.25 + 7.31 * k for k in range(21)], abs=0.006)  # a fin every 7.31 mm
    for x in fins:  # the fins stand inside the block: depth is not held, so none is drawn past it
        assert x["at"][1] == block["at"][1] and x["size"][1] == block["size"][1]
        assert block["at"][0] <= x["at"][0] and x["at"][0] + x["size"][0] <= block["at"][0] + block["size"][0]
    sk = {s["id"]: s for s in rear["silkscreen"] if s.get("id")}
    assert "heatsink-fins" not in sk
    assert sk["heatsink-rim-left"]["at"][0] == 202.5 and sk["heatsink-rim-left"]["fill"] == "#d9d9d9"
    assert sk["heatsink-rim-right"]["at"][0] == 365.9 and sk["heatsink-rim-right"]["fill"] == "#9a9a98"
    note = d["provenance"]["rear-layout"]["note"] + d["provenance"]["colour"]["note"]
    assert "7.31" in note and "21 fins" in note and "1.4 mm" in note and "121688" in note and "13356" in note


def test_ccr2116_rear_has_two_dark_round_holes_at_the_fifth_openings_corners():
    d = load(CCR2116)
    r = decor(d, "rear")
    opening = r["psu-opening"]
    holes = [r["psu-hole-upper-left"], r["psu-hole-lower-right"]]
    assert [h["kind"] for h in holes] == ["rear-hole", "rear-hole"]
    assert all(h["size"] == [3.9, 3.9] and h["rx"] == 1.95 and h["fill"] == "#1b1b1a" for h in holes)  # 3.9 mm across
    centres = [[h["at"][i] + h["size"][i] / 2 for i in (0, 1)] for h in holes]
    middle = [opening["at"][i] + opening["size"][i] / 2 for i in (0, 1)]
    assert centres[0] == pytest.approx([middle[0] - 16.5, middle[1] - 16.7], abs=0.01)
    assert centres[1] == pytest.approx([middle[0] + 16.5, middle[1] + 16.7], abs=0.01)
    for c in centres:  # in the corner of the opening's square, outside its circle, inside the face
        assert ((c[0] - middle[0]) ** 2 + (c[1] - middle[1]) ** 2) ** 0.5 > opening["rx"] + 1.95
        assert 2.0 <= c[0] <= 441.0 and 2.0 <= c[1] <= 42.0
    note = d["provenance"]["rear-holes"]["note"]
    for word in ("3.9 mm", "#1b1b1a", "photograph 2116", "NetBox"):
        assert word in note


def test_ccr2116_jack_blocks_have_a_black_outline_round_them_and_each_jack_its_own_plate():
    d = load(CCR2116)
    f = decor(d, "front")
    backs = [f[f"jack-backing-{n}"] for n in (1, 2, 3)]
    assert {b["fill"] for b in backs} == {"#010101"} and {b["size"][1] for b in backs} == {13.6}
    assert [b["at"][0] for b in backs] == [42.9, 115.0, 187.3]
    plates = [f[f"jack-plate-{n:02d}"] for n in range(1, 13)]
    assert {p["fill"] for p in plates} == {"#bbbec3"} and {tuple(p["size"]) for p in plates} == {(15.5, 12.4)}
    for n, p in enumerate(plates):  # each plate is centred on its jack, 17 mm apart inside a block
        block = backs[n // 4]
        assert block["at"][0] < p["at"][0] and p["at"][0] + 15.5 < block["at"][0] + block["size"][0]
        assert p["at"][1] - block["at"][1] == pytest.approx(0.7) and block["size"][1] - 12.4 == pytest.approx(1.2)
    centres = [p["at"][0] + 7.75 for p in plates]
    assert centres == pytest.approx([c + 17.0 * k for c in (51.4, 123.5, 195.8) for k in range(4)], abs=0.01)
    outline, inner = f["mgmt-backing"], f["mgmt-block"]
    assert outline["fill"] == "#040404" and inner["fill"] == "#dedddf"
    assert inner["at"][0] > outline["at"][0] and inner["at"][0] + inner["size"][0] < outline["at"][0] + outline["size"][0]
    assert inner["at"][1] > outline["at"][1] and inner["at"][1] + inner["size"][1] < outline["at"][1] + outline["size"][1]
    assert not [k for k, x in f.items() if x.get("kind") == "jack-plate" and x["fill"] == "#c4c4c4"]  # the grey plate is gone
    note = d["provenance"]["front-outlines"]["note"]
    for word in ("#010101", "#bbbec3", "#040404", "#dedddf", "photograph 2625"):
        assert word in note


def test_ccr2116_sfp_plus_block_is_one_black_backing_with_its_bracket():
    d = load(CCR2116)
    f = decor(d, "front")
    back = f["sfp-backing"]
    assert back["fill"] == "#010101" and back["kind"] == "sfp-backing"
    cages = [p for p in d["views"]["front"]["panel"]["cutouts"] if str(p.get("id", "")).startswith("cage-")]
    assert len(cages) == 4
    for c in cages:  # the backing holds all four cages, with a margin
        assert back["at"][0] < c["at"][0] and c["at"][0] + c["size"][0] < back["at"][0] + back["size"][0]
        assert back["at"][1] < c["at"][1] and c["at"][1] + c["size"][1] < back["at"][1] + back["size"][1]
    strip = f["sfp-strip"]  # the light strip between the two rows of cages, over the backing
    rows = sorted({c["at"][1] for c in cages})
    assert strip["fill"] == "#b9b9bd" and strip["at"][1] == rows[0] + 10.4 and strip["at"][1] + strip["size"][1] == rows[1]
    assert list(f).index("sfp-strip") > list(f).index("sfp-backing")
    assert "#b9b9bd" in d["provenance"]["front-outlines"]["note"]
    sk = {s["id"]: s for s in d["views"]["front"]["silkscreen"] if s.get("id")}
    upper, lower = sk["sfp-bracket-upper"], sk["sfp-bracket-lower"]
    assert upper["at"][1] == back["at"][1] and lower["at"][1] + 11.5 == back["at"][1] + back["size"][1]
    assert upper["at"][0] < back["at"][0] and lower["at"][0] < back["at"][0]


LEGENDS = {  # the cap height read on each photograph, 1.65 to 1.9 mm, set in the face's own letter shapes
    CCR2116: {"front": 2.2, "rear": 2.2},
    CCR2004: {"front": 2.3, "rear": 2.2},
}
MODEL_TEXT = {"CCR2116-12G-4S+": 2.8, "CCR2004-1G-12S+2XS": 2.8, "Cloud Core Router": 5.3}
SFP28_LABELS = {"1▼": 1.9, "▲2": 1.9, "25G SFP28": 1.9}


@pytest.mark.parametrize("name", NAMES)
def test_every_legend_is_set_at_the_height_its_photograph_shows(name):
    d = load(name)
    for view in ("front", "rear"):
        for s in d["views"][view]["silkscreen"]:
            if not s.get("text"):
                continue
            want = MODEL_TEXT.get(s["text"]) or SFP28_LABELS.get(s["text"]) or LEGENDS[name][view]
            assert s["font-size"] == want, (view, s["text"])
    note = d["provenance"]["legends"]["note"]
    for word in (str(LEGENDS[name]["front"]), str(LEGENDS[name]["rear"]), "cap height", "px per mm"):
        assert word in note


@pytest.mark.parametrize("name", NAMES)
def test_the_lamps_resting_colour_is_the_components_and_the_gap_says_so(name):
    d = load(name)
    note = gaps(d)["led-states"]["note"]
    assert "resting colour" in note and "lamp component" in note
    lamps = [p for p in placements(d, "front") if p["ref"].startswith("common/led-")]
    assert lamps and not [p for p in lamps if "states" in p or "color" in p]  # no placement can state a resting colour


@pytest.mark.parametrize("name", NAMES)
def test_no_dc_input_and_no_barrel_plug(name):
    d = load(name)
    assert d["chassis"]["power"] == "ac"
    assert not [p for v in d["views"] for p in placements(d, v) if p["ref"] == "common/dc-barrel@1"]


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


@pytest.mark.parametrize("name", NAMES)
def test_the_common_gaps_are_declared(name):
    g = gaps(load(name))
    assert g["led-states"]["reason"] == "vendor-silent"
    assert g["weight"]["reason"] == g["eol"]["reason"] == "vendor-silent"
    assert g["top-and-bottom"]["reason"] == "needs-drawing"
    assert "fan-redundancy" not in json.dumps(load(name)["groups"])


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
    assert len(doc["power-ports"]) == 2  # two C14 inlets
    assert len(doc["console-ports"]) == 1


def test_dcim_ccr2116_interfaces_follow_the_front():
    a = exported(CCR2116)
    assert count(a, "1000base-t") == 13 and count(a, "10gbase-x-sfpp") == 4
    assert len(a["interfaces"]) == 17


def test_dcim_ccr2004_interfaces_follow_the_front():
    a = exported(CCR2004)
    assert count(a, "1000base-t") == 1 and count(a, "10gbase-x-sfpp") == 12 and count(a, "25gbase-x-sfp28") == 2
    assert len(a["interfaces"]) == 15


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

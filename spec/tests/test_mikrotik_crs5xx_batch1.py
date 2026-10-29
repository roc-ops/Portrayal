"""MikroTik's Cloud Router Switch CRS5xx, batch 1: the 25G and 100G models.

The CRS518-16XS-2XQ-RM takes its envelope from MikroTik's dimensions drawing (printed 20.09.2023): 443 wide, 44 high and
268 deep, where the brochure prints 443 x 265 x 44.5. Its two supplies and four fans are hot-swap modules in the
brochure and the photograph, but no held document prints a part number for either, so they are drawn as part of the
chassis (two C14 inlets, four fan openings) and no bay is added. The device names are lower case with no +.
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
    "crs518-16xs-2xq-rm": ("CRS518-16XS-2XQ-RM", "CRS518"),
    "crs510-8xs-2xq-in": ("CRS510-8XS-2XQ-IN", "CRS510"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth
    "crs518-16xs-2xq-rm": (443.0, 44.0, 268.0),
    "crs510-8xs-2xq-in": (320.0, 44.0, 185.0),
}
CRS518 = "crs518-16xs-2xq-rm"
CRS510 = "crs510-8xs-2xq-in"


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


# --- CRS518-16XS-2XQ-RM ------------------------------------------------------------------------------------------

def test_crs518_brochure_and_drawing_differences_are_declared():
    d = load(CRS518)
    note = d["provenance"]["chassis"]["note"]
    assert "268" in note and "265" in note and "44.5" in note
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["size-figures"]["reason"] == "sources-disagree"


def test_crs518_has_sixteen_sfp28_cages_in_eight_stacked_pairs():
    d = load(CRS518)
    cages = [p for p in placements(d, "front") if p.get("group") == "sfp28"]
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 17)]
    assert [p["rel-pos"] for p in cages] == list(range(1, 17))
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp28", "speed": "25g"} for p in cages)
    by_id = {p["id"]: p for p in cages}
    for n in range(1, 17, 2):  # the metal prints 1 and 2 under a stack: 1 is the lower cage
        assert by_id[f"cage-{n}"]["at"][1] > by_id[f"cage-{n + 1}"]["at"][1]
        assert by_id[f"cage-{n}"]["at"][0] == by_id[f"cage-{n + 1}"]["at"][0]
    assert by_id["cage-3"]["at"][0] - by_id["cage-1"]["at"][0] == pytest.approx(21.2, abs=0.05)


def test_crs518_has_two_qsfp28_cages_each_with_two_lamps():
    d = load(CRS518)
    cages = [p for p in placements(d, "front") if p.get("group") == "qsfp28"]
    assert [p["id"] for p in cages] == ["qsfp-1", "qsfp-2"]
    assert all(p["ref"] == "std/qsfp28@1" and p["attrs"] == {"media": "qsfp28", "speed": "100g"} for p in cages)
    assert cages[1]["at"][0] - cages[0]["at"][0] == pytest.approx(26.0, abs=0.05)
    assert len([p for p in placements(d, "front") if p.get("group") == "qsfp-leds"]) == 4
    assert len([p for p in placements(d, "front") if p.get("group") == "sfp-leds"]) == 32  # four per stack


def test_crs518_has_management_console_usb_reset_and_four_lamps():
    d = load(CRS518)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "100m")]
    assert [p["id"] for p in refs(d, "front", "std/usb-a@1")] == ["usb"]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    assert len([p for p in placements(d, "front") if p.get("group") == "status-leds"]) == 4
    assert {"CONSOLE", "ETH / BOOT", "MANAGEMENT", "RESET", "USER", "FAULT", "PWR 2", "PWR 1", "1", "2",
            "40G/100G", "1G/10G/25G", "CRS518-16XS-2XQ"} <= text_of(d, "front")
    ports = [p for p in placements(d, "front") if p.get("group") in {"sfp28", "qsfp28", "mgmt", "console", "usb"}]
    assert len(ports) == 16 + 2 + 1 + 1 + 1  # page: 16 SFP28, 2 QSFP28, 1 x 100M, one USB, one console


def test_crs518_supplies_and_fans_are_part_of_the_chassis_with_no_part_number():
    d = load(CRS518)
    assert not bays(d, "rear")
    assert d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]  # the page: 2 AC inputs
    assert all(p["group"] == "inlets" for p in inlets)
    fans = [x["id"] for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert fans == ["fan-0", "fan-1", "fan-2", "fan-3"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert {"hot-swap-supplies", "hot-swap-fans"} <= set(gaps)
    assert "fan-redundancy" not in json.dumps(d["groups"])
    p = d["attrs"]["power"]
    assert p["power-max-w"] == 77 and p["power-without-attachments-w"] == 45


def _decor(d, view):
    return {x["id"]: x for x in d["views"][view]["panel"]["decor"]}


def _render_decor(decor, w=443.0, h=44.0):
    import re
    from portrayal import render
    view = {"size": {"w": w, "h": h}, "panel": {"decor": decor}}
    dev = {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
           "chassis": {"width": w, "height": h, "depth": 100.0}, "views": {"front": view}}
    out = render.render_view(dev, "front", view, render.Library([str(ROOT / "library")]), config={})
    return out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")


BAND_PITCH = [16.5, 6.07]


def _pattern_of(svg, rect_id):
    import re
    m = re.search(rf'<rect id="{rect_id}"[^>]*fill="url\(#([^)]+)\)"', svg)
    assert m, svg[:600]
    pat = re.search(rf'<pattern [^>]*id="{re.escape(m.group(1))}"[^>]*>(.*?)</pattern>', svg, re.S)
    assert pat
    return m.group(1), pat.group(0)


def test_crs518_front_vent_band_is_alternating_v_and_lambda_openings_drawn_as_a_motif():
    """The drawing and photograph 2196 show separate solid V and lambda openings, alternating, each end cut level.
    One period is 16.5 mm (the lambdas, 27 of them, run from the band's left end to its right; the 26 Vs sit between
    them), so the band is 26 periods and the 27th lambda is drawn by its own rect."""
    d = load(CRS518)
    decor = _decor(d, "front")
    assert "vent-field" not in decor
    start, band, end = decor["vent-band-start"], decor["vent-band"], decor["vent-band-end"]
    for rect in (start, band, end):
        assert rect["pattern"] == "motif" and rect["vent"] and rect.get("rx") == 0  # square-cornered
        assert rect["pattern-offset"] == rect["at"] and rect["at"][1] == 2.2
        assert rect["size"][1] == BAND_PITCH[1] == rect["pattern-pitch"][1]  # the rect is as tall as the tile
        assert all(0 <= x <= rect["pattern-pitch"][0] and 0 <= y <= BAND_PITCH[1]
                   for c in rect["pattern-cells"] for x, y in c)  # no cell runs outside its tile
    for rect in (band, end):
        assert rect["pattern-pitch"] == BAND_PITCH
    # The seam: a tile edge that touches ink is filtered against the ink on the opposite edge, which drew a hairline
    # dash along the band's top and bottom edges. The tile is the 5.67 mm the cells span plus 0.2 mm clear each
    # side, so no cell touches the tile's top or foot; the rect is 0.2 mm taller than the ink and the ink stays at
    # 2.4 to 8.07 mm.
    for rect in (start, band, end):
        ys = [y for c in rect["pattern-cells"] for _, y in c]
        assert min(ys) == pytest.approx(0.2) and max(ys) == pytest.approx(BAND_PITCH[1] - 0.2)
        assert max(ys) - min(ys) == pytest.approx(5.67)
        assert rect["at"][1] + min(ys) == pytest.approx(2.4) and rect["at"][1] + max(ys) == pytest.approx(8.07)
    assert len(band["pattern-cells"]) == 3  # the lambda, the V, and the V's right arm that runs into the next tile
    lam, v, wrap = band["pattern-cells"]
    assert min(x for x, _ in lam) == 0.0 and min(y for _, y in lam) == 0.2
    assert sorted({y for _, y in v if y == 0.2}) == [0.2] and max(y for _, y in v) > 5.0
    # the left end: the first mark is the lambda (photograph 2196 shows no V before it), so no 1.2 mm sliver. The
    # first rect has its own tile, 18.4 mm wide: 0.2 mm clear at the left, the lambda, the V, and the V's arm tip
    # carried to 17.94 mm so that the next rect, which starts where the arm does, joins it without a seam.
    assert start["at"] == [2.1, 2.2] and start["size"] == [18.4, 6.07] and start["pattern-pitch"] == [18.4, 6.07]
    s_lam, s_v, s_arm = start["pattern-cells"]
    shift = lambda cell: [[round(x + 0.2, 2), y] for x, y in cell]
    assert s_lam == shift(lam) and s_v == shift(v)
    assert max(x for x, _ in s_arm) == 17.94 and min(x for x, _ in s_lam) == 0.2
    assert all(max(x for x, _ in c) - min(x for x, _ in c) > 5 for c in (s_lam, s_v))
    assert min(x for c in start["pattern-cells"] for x, _ in c) > 0.0  # no cell touches the tile's left edge
    assert band["at"][0] == pytest.approx(start["at"][0] + 16.7, abs=0.001)
    # the band runs on from the end of the first period: 25 whole periods and the V's arm of the 26th
    assert (band["size"][0] - 1.3) / 16.5 == pytest.approx(25, abs=0.001)
    assert end["at"][0] == pytest.approx(band["at"][0] + 25 * 16.5, abs=0.001)
    assert len(end["pattern-cells"]) == 1 and end["pattern-cells"][0] == lam  # the 27th lambda
    assert end["size"][0] >= max(x for x, _ in lam)  # no cell runs outside the rect
    assert end["at"][0] + end["size"][0] == pytest.approx(440.7, abs=0.2)  # 2.3 mm in from the right edge
    svg = _render_decor([start, band, end])
    pid, pat = _pattern_of(svg, "vent-band")
    assert 'width="16.5"' in pat and 'height="6.07"' in pat and pat.count("<path") == 3
    assert 'data-aperture="air"' in svg  # still an opening, not paint
    assert "chevrons" not in svg


def test_the_motif_band_states_its_tile_once_in_provenance():
    note = load(CRS518)["provenance"]["front-layout"]["note"]
    assert "16.5" in note and "estimated" in note and "5.62" in note and "motif" in note
    assert "16.7" not in note and "chevrons" not in note
    assert "no V before the first lambda" in note and "grey" in note and "5.67" in note


def _centre(x):
    return [round(x["at"][0] + x["size"][0] / 2, 2), round(x["at"][1] + x["size"][1] / 2, 2)]


@pytest.mark.parametrize("name, ids, corners, pitch", [
    (CRS518, [f"fan-{i}" for i in range(4)], 4.31, 4.88),
    (CRS518, ["psu-1-vent", "psu-2-vent"], 5.34, 5.88),
    (CRS510, ["fan-0", "fan-1"], 5.32, 5.43),
])
def test_rear_hexagon_fields_state_the_photographs_pitch_and_a_lattice_that_starts_at_a_hexagon(name, ids, corners,
                                                                                               pitch):
    """Photograph 2197 (5.80 px per mm) reads openings 4.31 mm across the corners on a 4.88 mm nearest-neighbour
    pitch on the CRS518's fans and 5.34 on 5.88 on its supply grilles; photograph 2233 (8.84 px per mm) 5.32 on 5.43
    on the CRS510's fans. The renderer's plain vent tile (hexagons 5.1 mm on a 5.11 mm pitch) cannot give those webs,
    so each field is a motif tile of one regular hexagon period: a whole hexagon at the middle of the tile and a
    quarter of one at each corner, the tile 1.732 pitches wide and one pitch high."""
    decor = _decor(load(name), "rear")
    for i in ids:
        d = decor[i]
        assert d["pattern"] == "motif"
        tw, th = d["pattern-pitch"]
        assert th == pitch and tw == pytest.approx(pitch * 3 ** 0.5, abs=0.01), i  # regular: column step = pitch x 0.866
        full, *quarters = d["pattern-cells"]
        assert len(full) == 6 and len(quarters) == 4
        xs = [x for x, _ in full]
        assert max(xs) - min(xs) == pytest.approx(corners, abs=0.02), i  # across the corners
        assert (min(xs) + max(xs)) / 2 == pytest.approx(tw / 2, abs=0.01)  # the whole hexagon sits at the tile's middle
        assert sum(y for _, y in full) / 6 == pytest.approx(th / 2, abs=0.01)
        for cell in d["pattern-cells"]:
            assert all(0 <= x <= tw and 0 <= y <= th for x, y in cell), i
        if d["kind"] == "fan-grille":
            assert d["pattern-offset"] == _centre(d), i  # a hexagon is centred under the hub, as the photographs show
        else:  # a supply grille: a whole column of hexagons starts 5.3 mm in from the left and 5.1 mm down
            assert d["pattern-offset"] == [round(d["at"][0] + 5.3, 2), round(d["at"][1] + 5.1, 2)], i
    note = load(name)["provenance"]["rear-layout"]["note"]
    assert "column step" in note and "estimated" in note and "pattern-pitch" in note


@pytest.mark.parametrize("name, fans", [(CRS518, 4), (CRS510, 2)])
def test_every_fan_opening_has_a_plain_hub_in_its_centre(name, fans):
    """Photographs 2197 and 2233 show each fan as a ring of mesh round a plain hub, not a disc of mesh."""
    decor = _decor(load(name), "rear")
    for i in range(fans):
        g, hub = decor[f"fan-{i}"], decor[f"fan-hub-{i}"]
        centre = lambda x: (round(x["at"][0] + x["size"][0] / 2, 2), round(x["at"][1] + x["size"][1] / 2, 2))
        assert centre(g) == centre(hub)
        assert 0.4 <= hub["size"][0] / g["size"][0] <= 0.6
        assert "pattern" not in hub and not hub.get("vent")


def test_crs510_front_has_no_vent_band_along_the_top():
    """The drawing's front view and photograph 2232 show a plain top edge: no chevrons on this box."""
    d = load(CRS510)
    assert not [x for x in d["views"]["front"]["panel"]["decor"]
                if x.get("pattern") == "chevrons" or x["id"] == "vent-field"]


@pytest.mark.parametrize("psu, left", [("psu-1", 12.6), ("psu-2", 72.0)])
def test_crs510_supply_vent_is_slots_not_perforations(psu, left):
    """Each supply shows six tall slots (three across, two down) and a row of four short ones along its top edge, in
    the drawing's front view and in photograph 2232. Sizes are read off the drawing at 3.94 px per mm and are
    estimates to about 0.4 mm; the photograph, at 8.74 px per mm, agrees on the count."""
    d = load(CRS510)
    decor = _decor(d, "front")
    assert f"{psu}-vent" not in decor  # the round-perforation field is gone
    tall = [decor[f"{psu}-slot-{r}{c}"] for r in "ab" for c in "123"]
    short = [decor[f"{psu}-slot-top-{i}"] for i in range(1, 5)]
    for s in tall + short:
        assert s["kind"] == "vent-field" and s["vent"] and "pattern" not in s
        assert left <= s["at"][0] and s["at"][0] + s["size"][0] <= left + 52.1
    assert {tuple(s["size"]) for s in tall} == {(3.8, 7.6), (3.8, 7.5)}
    xs = sorted({round(s["at"][0] - left, 2) for s in tall})
    assert xs == [3.7, 8.7, 13.7]  # a 5.0 mm pitch
    assert sorted({s["at"][1] for s in tall}) == [20.0, 29.2]
    assert all(s["at"][1] < 12 and s["size"][1] == 2.5 for s in short)
    lay = d["provenance"]["vent-slots"]
    assert lay["confidence"] == "estimated"


def test_crs518_walls():
    d = load(CRS518)
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["side-vent"]
    assert d["views"]["left"].get("empty")
    assert d["views"]["top"].get("empty")


# --- CRS510-8XS-2XQ-IN ------------------------------------------------------------------------------------------

def test_crs510_drawing_and_brochure_agree_and_the_power_figures_conflict_is_declared():
    d = load(CRS510)
    assert "320 x 185 x 44" in d["provenance"]["chassis"]["note"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["power-figures"]["reason"] == "sources-disagree"
    assert "27" in gaps["power-figures"]["note"] and "31" in gaps["power-figures"]["note"]
    assert d["attrs"]["power"]["power-without-attachments-w"] == 31 and d["attrs"]["power"]["power-max-w"] == 51


def test_crs510_has_eight_sfp28_and_two_qsfp28_cages_in_stacks():
    d = load(CRS510)
    sfp = [p for p in placements(d, "front") if p.get("group") == "sfp28"]
    assert [p["id"] for p in sfp] == [f"cage-{n}" for n in range(1, 9)]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp28", "speed": "25g"} for p in sfp)
    by_id = {p["id"]: p for p in sfp}
    for n in range(1, 9, 2):  # the metal prints 1 3 5 7 under the stacks and 2 4 6 8 over them
        assert by_id[f"cage-{n}"]["at"][1] > by_id[f"cage-{n + 1}"]["at"][1]
        assert by_id[f"cage-{n}"]["at"][0] == by_id[f"cage-{n + 1}"]["at"][0]
    assert by_id["cage-3"]["at"][0] - by_id["cage-1"]["at"][0] == pytest.approx(17.4, abs=0.05)
    assert by_id["cage-5"]["at"][0] - by_id["cage-3"]["at"][0] == pytest.approx(21.1, abs=0.05)  # the gutter
    q = [p for p in placements(d, "front") if p.get("group") == "qsfp28"]
    assert [p["id"] for p in q] == ["qsfp-1", "qsfp-2"] and q[0]["at"][1] > q[1]["at"][1]
    assert all(p["ref"] == "std/qsfp28@1" and p["attrs"] == {"media": "qsfp28", "speed": "100g"} for p in q)
    assert len([p for p in placements(d, "front") if p.get("group") == "sfp-leds"]) == 16 + 4  # four arrows a stack
    assert len([p for p in placements(d, "front") if p.get("group") == "qsfp-leds"]) == 2  # and the QSFP28's two dots
    ports = [p for p in placements(d, "front") if p.get("group") in {"sfp28", "qsfp28", "mgmt", "console"}]
    assert len(ports) == 8 + 2 + 1 + 1


def test_crs510_front_carries_console_management_reset_dc_jack_and_three_lamps():
    d = load(CRS510)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "100m")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    assert not refs(d, "front", "common/dc-barrel@1")  # drawn as chassis art: the barrel census wants a current
    assert [x["id"] for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "dc-jack-art"] == [
        "dc-jack-housing", "dc-jack-rim", "dc-jack-bore", "dc-jack-pin"]
    assert len([p for p in placements(d, "front") if p.get("group") == "status-leds"]) == 5  # 3 bars, 2 supply lamps
    assert {"CONSOLE", "MGMT/PoE in", "RESET", "USER", "FAULT", "POWER", "36-57 V", "CRS510-8XS-2XQ-IN"} <= text_of(d, "front")
    gaps = {g["what"] for g in d["gaps"]}
    assert {"dc-jack", "dc-terminal", "hot-swap-supplies", "led-states", "left-wall"} <= gaps  # neither DC input is placed
    assert not [p for p in placements(d, "front") if p["ref"].startswith("common/dc-terminal")]


TERMINAL_GREEN = "#82967a"


def test_crs510_two_pin_terminal_is_chassis_art_at_the_drawings_place_and_size():
    """The drawing's front view: 11.4 x 11.8 mm at 275.4 mm, 24.8 mm down, a cap 10.4 mm wide over a body 11.4 x 7.9
    with two wire entries on a 5.08 mm pitch. It stands 9 mm proud of the front in the drawing and is drawn flat."""
    d = load(CRS510)
    decor = _decor(d, "front")
    art = {k: v for k, v in decor.items() if v.get("kind") == "dc-terminal-art"}
    assert sorted(art) == ["dc-terminal-cap", "dc-terminal-entry-1", "dc-terminal-entry-2", "dc-terminal-housing"]
    cap, body = art["dc-terminal-cap"], art["dc-terminal-housing"]
    assert cap["at"] == [275.9, 24.8] and cap["size"] == [10.4, 3.9]
    assert body["at"] == [275.4, 28.7] and body["size"] == [11.4, 7.9]
    assert body["at"][1] + body["size"][1] == pytest.approx(24.8 + 11.8)  # the overall 11.8
    assert cap["fill"] == body["fill"] == TERMINAL_GREEN
    e1, e2 = art["dc-terminal-entry-1"], art["dc-terminal-entry-2"]
    assert e2["at"][0] - e1["at"][0] == pytest.approx(5.05, abs=0.05)
    for e in (e1, e2):
        assert body["at"][0] <= e["at"][0] and e["at"][0] + e["size"][0] <= body["at"][0] + body["size"][0]
        assert e["fill"] == "#051203"
    assert not [p for p in placements(d, "front") if "terminal" in p["ref"]]  # no part is placed
    gaps = {g["what"]: g for g in d["gaps"]}
    note = gaps["dc-terminal"]["note"]
    assert "chassis art" in note and "no power port" in note and "no held document names the part" in note
    assert "left out" not in note and "not drawn" not in note
    prov = d["provenance"]["dc-inputs"]["note"]
    assert "9 mm" in prov and "flat" in prov and "11.4 x 11.8" in prov and TERMINAL_GREEN in prov
    assert "polarity marks above the terminal are not drawn" not in prov


def test_crs510_barrel_jack_is_a_rimmed_socket_with_a_centre_pin_and_no_part():
    """Photograph 2232 (8.77 px per mm across the 320 mm face): a dark housing 10.3 x 11.8 mm, a round bore 5.7 mm
    across inside a 6.5 mm rim ring, and a small bright centre pin. Fills are the medians of the pixels: the rim
    ring is #292929 (506 pixels, radius 25 to 28 px about 2825.5,960), the bore #030303 (1954 pixels, radius under
    25 px) and the pin #b0b0af (27 pixels brighter than 120 in box 2815,944 to 2831,958)."""
    d = load(CRS510)
    art = {k: v for k, v in _decor(d, "front").items() if v.get("kind") == "dc-jack-art"}
    assert sorted(art) == ["dc-jack-bore", "dc-jack-housing", "dc-jack-pin", "dc-jack-rim"]
    want = {"dc-jack-housing": ([290.1, 24.8], [10.3, 11.8], "#3e3e3d"),
            "dc-jack-rim": ([291.9, 26.25], [6.5, 6.5], "#292929"),
            "dc-jack-bore": ([292.3, 26.65], [5.7, 5.7], "#030303"),
            "dc-jack-pin": ([294.25, 27.75], [1.1, 1.1], "#b0b0af")}
    for key, (at, size, fill) in want.items():
        assert (art[key]["at"], art[key]["size"], art[key]["fill"]) == (at, size, fill), key
    for key in ("dc-jack-rim", "dc-jack-bore", "dc-jack-pin"):
        assert art[key]["rx"] == art[key]["size"][0] / 2  # round
    assert _centre(art["dc-jack-rim"]) == _centre(art["dc-jack-bore"])
    assert not [p for p in placements(d, "front") if "dc-" in p["ref"] or p["id"].startswith("dc-jack")]
    note = d["provenance"]["dc-inputs"]["note"]
    assert all(v in note for v in ("#292929", "#030303", "#b0b0af", "1954", "506"))


def _paths(d):
    return {s["id"]: s for s in d["views"]["front"]["silkscreen"] if s.get("path")}


def test_crs510_dc_legends_are_the_bracket_the_voltage_and_the_polarity_marks():
    """Photograph 2232: one bracket over both inputs, "36-57 V" centred over it, a circled minus and plus over the
    terminal (left to right) and a circled minus, the barrel symbol with its centre pin dot, and a circled plus over
    the jack: the centre pin is the positive pole."""
    d = load(CRS510)
    paths = _paths(d)
    assert {"dc-bracket", "dc-terminal-polarity", "dc-jack-polarity"} <= set(paths)
    for s in paths.values():
        assert s["filled"] is False and s["stroke-width"] == 0.25 and s["for"] == "chassis"
    bracket = paths["dc-bracket"]
    left, right = bracket["at"][0], bracket["at"][0] + 24.7  # the path runs 24.7 mm across
    assert "L 23.7 0" in bracket["path"] and "L 24.7 2.1" in bracket["path"]  # 24.7 across, the right leg 2.1 down
    volt = [s for s in d["views"]["front"]["silkscreen"] if s.get("text") == "36-57 V"]
    assert len(volt) == 1 and volt[0]["for"] == "chassis"
    assert volt[0]["at"][0] == pytest.approx((left + right) / 2, abs=0.5)  # centred on the bracket, not on the jack
    assert volt[0]["at"][1] < bracket["at"][1]  # printed above it
    term, jack = paths["dc-terminal-polarity"], paths["dc-jack-polarity"]
    assert term["at"][0] < jack["at"][0] < right
    # two circles of two arcs each, and one vertical stroke: one minus and one plus
    assert term["path"].count(" a 1.2 1.2 ") == 4 and term["path"].count("v 1.2") == 1
    assert jack["path"].count(" a 1.2 1.2 ") == 4 and jack["path"].count("v 1.2") == 1
    # the centre pin dot sits on the plus side of the barrel symbol: its line runs to the plus circle at the right
    assert "M 2.9 0 h 1.4" in jack["path"]
    prov = d["provenance"]["dc-inputs"]["note"]
    assert "centre pin" in prov and "positive" in prov


def test_crs510_unlit_lamps_are_left_as_the_component_draws_them():
    """common/led-rect fills its lamp from var(--led-color, #2a6b3f); a placement cannot set that variable's
    resting value, and a component on main is not edited here. The photograph shows unlit grey (#878686, #858584 and
    #898888 for USER, FAULT and POWER)."""
    d = load(CRS510)
    note = d["provenance"]["lamps"]["note"]
    assert all(v in note for v in ("#878686", "#858584", "#898888", "#5e6d52"))
    assert "common/led-rect" in note and "left" in note and "#2a6b3f" in note
    leds = {p["id"]: p for p in refs(d, "front", "common/led-rect@1")}
    assert sorted(leds) == ["led-fault", "led-power", "led-user"]
    assert not [p for p in placements(d, "front") if p["ref"] == "common/led-rect@1" and "color" in str(p)]


CRS510_COLOURS = {  # drawn value -> where it sits
    "psu-1-module": "#a3a5a7", "psu-2-module": "#a3a5a7", "mgmt-block": "#949290", "dc-jack-housing": "#3e3e3d",
    "dc-terminal-housing": TERMINAL_GREEN, "dc-terminal-cap": TERMINAL_GREEN,
}
CRS518_COLOURS = {
    "psu-1-module": "#6f6d68", "psu-2-module": "#6f6d68", "mgmt-block": "#63625f",
    "fan-module-0": "#878682", "fan-module-1": "#878682", "fan-module-2": "#878682", "fan-module-3": "#878682",
    "fan-hub-0": "#817f7c", "fan-hub-1": "#817f7c", "fan-hub-2": "#817f7c", "fan-hub-3": "#817f7c",
}


@pytest.mark.parametrize("name, colours, face", [(CRS510, CRS510_COLOURS, "#dddddd"), (CRS518, CRS518_COLOURS, "#c0bfbf")])
def test_every_painted_part_is_the_colour_sampled_from_its_photograph(name, colours, face):
    d = load(name)
    assert d["chassis"]["color"] == face
    note = d["provenance"]["colour"]["note"]
    assert face in note and "median" in note and "pixel" in note
    front, rear = _decor(d, "front"), _decor(d, "rear")
    for part, hexval in colours.items():
        decor = front if part in front else rear  # the CRS518's supplies and fans are on its rear
        assert decor[part]["fill"] == hexval, part
        assert hexval in note, f"{part}: {hexval} has no sample in the colour note"


def test_crs518_face_colour_is_the_median_of_three_plain_patches_across_the_lit_gradient():
    """Photograph 2196 and the brochure's straight-on figure are lit left to right (#bbbbbb to #c9c9c9): three plain
    patches each, the face being the channel-wise median of the photograph's three patch medians."""
    d = load(CRS518)
    assert d["chassis"]["color"] == "#c0bfbf"
    note = d["provenance"]["colour"]["note"]
    for token in ("#bbbbbb", "#c0bfbf", "#c7c7c7", "8398", "4254", "20980", "3112", "2673", "4800", "fig-0001"):
        assert token in note, token


def test_crs510_supplies_are_two_front_modules_with_c14_inlets_and_no_bays():
    d = load(CRS510)
    assert not bays(d, "front") and not bays(d, "rear")
    inlets = refs(d, "front", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    assert all(p["group"] == "inlets" and p["rotate"] in (90, 270, -90) for p in inlets)
    assert {"PSU 1", "PSU 2", "100-240 V 50/60 Hz"} <= text_of(d, "front")
    assert d["chassis"]["power"] == "ac"
    fans = [x["id"] for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert fans == ["fan-0", "fan-1"]
    assert d["views"]["right"]["panel"]["decor"] and d["views"]["left"].get("empty")


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


def test_dcim_crs518_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS518)
    assert count(a, "25gbase-x-sfp28") == 16 and count(a, "100gbase-x-qsfp28") == 2
    assert count(a, "100base-tx") == 1
    assert len(a["power-ports"]) == 2  # two C14 inlets
    assert len(a["console-ports"]) == 1


def test_dcim_crs510_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS510)
    assert count(a, "25gbase-x-sfp28") == 8 and count(a, "100gbase-x-qsfp28") == 2
    assert count(a, "100base-tx") == 1
    assert len(a["power-ports"]) == 2  # the two C14 inlets; the DC jack and the terminal are not placed
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

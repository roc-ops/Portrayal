"""The seven Rittal DK 7979 metered PDUs and the controller they share.

What is true of the library: each device is the strip its dimensioned drawing gives. It takes the outlets its
maker's table counts, on the parts the library holds. It carries the controller of the PDU metered, with three RJ45
jacks, one RJ12 jack, one USB-A port and the two small headers. Its input is the fixed 16 A CEE cord and it has no
breaker. Every lamp states what it shows. Reads the device and component sources only; none reads `library/dist`.
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

C13, C19 = "std/c13-outlet@1", "std/c19-outlet@1"
CORD_3P, CORD_1P = "rittal/pdu-cord-cee-16a@1", "rittal/pdu-cord-cee-16a-1p@1"

# sku -> (length mm, C13, C19, cord, the span between the two rear buttons)
DEVICES = {
    "210": (845, 12, 1, CORD_1P, 622.3),
    "230": (845, 0, 9, CORD_3P, 622.3),
    "235": (1094, 18, 3, CORD_3P, 933.45),
    "236": (1494, 24, 6, CORD_3P, 1244.6),
    "238": (1696, 18, 12, CORD_3P, 1555.75),
    "240": (1895, 36, 6, CORD_3P, 1600.2),
    "242": (1696, 42, 0, CORD_3P, 1555.75),
}
SKUS = sorted(DEVICES)


def _device(sku):
    return yaml.safe_load((LIB / "devices" / "rittal" / f"dk-7979-{sku}" / "device.yaml").read_text())


def _placements(sku, view="front"):
    return _device(sku)["views"][view]["components"]["placements"]


def _by_id(sku):
    return {p["id"]: p for p in _placements(sku)}


@pytest.mark.parametrize("sku", SKUS)
def test_the_device_is_new_and_the_strip_the_drawing_gives(sku):
    device = _device(sku)
    length = DEVICES[sku][0]
    assert device["name"] == f"dk-7979-{sku}" and device["model"] == f"DK 7979.{sku}"
    assert device["version"] == "0.1.0" and device["maturity"] == "modelled"
    chassis = device["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"]) == (44, length, 72.1)
    assert chassis["mount"] == "rack-side"
    assert device["views"]["front"]["size"] == {"w": 44, "h": length}


@pytest.mark.parametrize("sku", SKUS)
def test_every_face_is_stated(sku):
    views = _device(sku)["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for face in ("top", "bottom", "left", "right"):
        assert views[face].get("empty"), f"{face} states neither parts nor why it is empty"


@pytest.mark.parametrize("sku", SKUS)
def test_the_outlets_are_the_ones_the_maker_counts(sku):
    _, c13, c19, _, _ = DEVICES[sku]
    outlets = [p for p in _placements(sku) if p["id"].startswith("outlet-")]
    assert Counter(p["ref"] for p in outlets) == Counter({k: v for k, v in {C13: c13, C19: c19}.items() if v})
    assert all(p["fed-by"] == "input" for p in outlets)
    ys = [p["at"][1] for p in outlets]
    assert ys == sorted(ys, reverse=True), "outlets count from the foot, the highest y"


@pytest.mark.parametrize("sku", SKUS)
def test_the_input_is_the_fixed_16_a_cord_and_there_is_no_breaker(sku):
    cord = DEVICES[sku][3]
    placements = _placements(sku)
    assert [p["ref"] for p in placements if p["id"] == "input"] == [cord]
    power = _device(sku)["attrs"]["power"]
    assert power["input-cord"] == "fixed" and power["input-current-a"] == 16
    assert not [p for p in placements if "breaker" in p["ref"] or "breaker" in p["id"]]


@pytest.mark.parametrize("sku", SKUS)
def test_the_controller_carries_three_rj45_one_rj12_one_usb_and_two_headers(sku):
    by_id = _by_id(sku)
    refs = Counter(p["ref"] for p in by_id.values())
    assert refs["common/rj45-eth@1"] == 2 and refs["std/rj45@2"] == 1
    assert refs["common/rj11-jack@1"] == 1
    assert refs["std/usb-a@1"] == 1 and by_id["usb"]["skin"] == "usb2", "USB 2.0, a white tongue, and no trident part"
    shell = [d for d in _device(sku)["views"]["front"]["panel"]["decor"] if d.get("kind") == "port-shell"]
    assert [d["fill"] for d in shell] == ["#c5c5c5"]
    assert refs["rittal/pdu-controller@1"] == 1
    assert refs["rittal/pdu-digital-input@1"] == 1 and refs["rittal/pdu-alarm-relay@1"] == 1
    assert {"eth1", "eth2", "can", "rs232", "usb", "digital-input", "alarm-relay"} <= set(by_id)


@pytest.mark.parametrize("sku", SKUS)
def test_every_lamp_states_what_it_shows(sku):
    lamps = [p for p in _placements(sku) if p["ref"].startswith("common/led-")]
    assert {p["id"] for p in lamps} == {"lamp-power", "lamp-status", "lamp-can-green", "lamp-can-red"}
    for lamp in lamps:
        assert "states" in lamp, f"{lamp['id']} states nothing"
    by_id = _by_id(sku)
    assert by_id["can"]["attrs"]["media"] == "rj45-telemetry", "the CAN jack must not export as Ethernet"
    for jack in ("eth1", "eth2"):
        assert set(by_id[jack]["states"]) == {"led-a", "led-b"}


@pytest.mark.parametrize("sku", SKUS)
def test_the_two_buttons_are_the_dimensioned_span_apart(sku):
    buttons = [p for p in _placements(sku, "rear") if p["id"].startswith("button-")]
    assert len(buttons) == 2
    assert abs(abs(buttons[0]["at"][1] - buttons[1]["at"][1]) - DEVICES[sku][4]) < 0.5


@pytest.mark.parametrize("sku", SKUS)
def test_the_front_is_tiled_end_to_end_by_the_cells(sku):
    length = DEVICES[sku][0]
    cell_kinds = {"end-cap", "spacer", "phase-plate", "controller-cell"}
    decor = [d for d in _device(sku)["views"]["front"]["panel"]["decor"] if d["kind"] in cell_kinds]
    edge = 0.0
    for cell in sorted(decor, key=lambda d: d["at"][1]):
        assert abs(cell["at"][1] - edge) < 0.15, f"{cell['id']} leaves a gap or overlaps"
        edge = cell["at"][1] + cell["size"][1]
    assert abs(edge - length) < 0.15


# sku -> outlet blocks in one phase plate, as the drawing's cell lines group them
BLOCKS = {"210": 0, "230": 1, "235": 2, "236": 2, "238": 3, "240": 3, "242": 2}
# sku -> the small circles on the plan view's centre line, mm from the foot (drawing, read twice at 600 dpi)
CIRCLES = {
    "210": [422.5],
    "230": [422.2],
    "235": [],
    "236": [435.4, 746.4, 1057.5],
    "238": [381.3, 1314.6],
    "240": [191.9, 458.7, 1436.4, 1703.2],
    "242": [381.4, 1314.6],
}


@pytest.mark.parametrize("sku", SKUS)
def test_the_pink_and_white_plates_are_frames_round_each_outlet_block(sku):
    decor = _device(sku)["views"]["front"]["panel"]["decor"]
    frames = [d for d in decor if d.get("kind") == "phase-frame"]
    strokes = Counter(d["stroke"] for d in frames)
    want = BLOCKS[sku]
    assert strokes == (Counter({"#ee488f": want, "#fefefe": want}) if want else Counter())
    assert all(d["stroke-width"] == 3.5 and d["confidence"] == "estimated" for d in frames)
    assert not [d for d in decor if d.get("fill") in ("#ee488f", "#fefefe")], "a plate is a solid pink or white"


@pytest.mark.parametrize("sku", SKUS)
def test_the_label_cover_is_a_raised_part_not_bare_decor(sku):
    device = _device(sku)
    assert not [d for d in device["views"]["front"]["panel"]["decor"] if d.get("kind") == "cover-plate"]
    cover = _by_id(sku)["cover-plate"]
    assert cover["ref"] == "rittal/pdu-cover-plate@1" and cover["at"][0] == 2.1
    contract = yaml.safe_load((LIB / "components" / "rittal" / "pdu-cover-plate" / "v1" / "contract.yaml").read_text())
    feature = contract["relief"]["features"][0]
    assert feature["out"] == 13.2 and feature["profile-y"][1][1] == 13.2 and contract["size"] == {"w": 40.2, "h": 107.3}


@pytest.mark.parametrize("sku", SKUS)
def test_the_plan_view_circles_sit_on_the_centre_line(sku):
    length = DEVICES[sku][0]
    marks = [d for d in _device(sku)["views"]["rear"]["panel"]["decor"] if d.get("kind") == "centre-mark"]
    got = sorted(round(length - (d["at"][1] + d["size"][1] / 2), 1) for d in marks)
    assert len(got) == len(CIRCLES[sku])
    assert all(abs(a - b) < 0.3 for a, b in zip(got, CIRCLES[sku]))
    assert all(d["size"] == [2.4, 2.4] and abs(d["at"][0] + 1.2 - 22.2) < 0.01 for d in marks)


@pytest.mark.parametrize("sku", SKUS)
def test_the_controller_plate_steps_in_at_each_end_and_has_a_rim_there(sku):
    decor = {d["id"]: d for d in _device(sku)["views"]["front"]["panel"]["decor"]}
    foot = decor["plate-lower"]["at"][1] + decor["plate-lower"]["size"][1]
    for name in ("notch-foot-1", "notch-foot-2"):
        assert decor[name]["size"] == [0.6, 23.0] and abs(decor[name]["at"][1] - (foot - 23.0)) < 0.01
    # an inner rim open toward the middle: two side lines, a closing line 7.05 from the end, and a jog at each side
    for side in ("rim-foot-a", "rim-foot-b"):
        assert decor[side]["size"] == [0.35, 17.25] and abs(decor[side]["at"][1] - (foot - 24.3)) < 0.01
    assert decor["rim-foot-c"]["size"] == [35.95, 0.35] and abs(decor["rim-foot-c"]["at"][1] - (foot - 7.225)) < 0.01
    assert decor["rim-foot-d"]["size"][0] == 1.75 and decor["rim-foot-e"]["size"][0] == 1.575
    assert "rim-foot" not in decor, "a closed box would draw a line across the plate that the drawing does not"


# sku -> the ribs inside the head cap, mm from the head end (drawing's vector paths and a 1800 dpi render, read twice)
RIBS = {
    "210": [10.1],
    "230": [10.0],
    "235": [9.95],
    "236": [10.05, 16.4],
    "238": [9.95, 17.2, 27.25],
    "240": [10.05, 17.25],
    "242": [10.1],
}
# sku -> where each C19's outer frame starts, mm from the head end (it is 42.1 long, 34.11 across, R1.5)
FRAMES = {
    "210": [244.37],
    "230": [17.51, 63.0, 108.51, 354.01, 399.5, 445.0, 490.49, 536.0, 581.49],
    "235": [21.63, 447.72, 673.81],
    "236": [28.1, 70.6, 603.2, 645.68, 952.48, 994.98],
    "238": [39.26, 81.75, 129.85, 172.35, 689.84, 732.34, 780.44, 822.95, 1096.04, 1138.54, 1186.64, 1229.14],
    "240": [29.34, 71.84, 769.93, 812.43, 1221.62, 1264.12],
    "242": [],
}
# the controller plate's five section lines, mm from the plate's head end; the first is in the part's skin
SECTIONS = [74.0, 104.0, 131.0, 142.7, 160.0]


@pytest.mark.parametrize("sku", SKUS)
def test_the_head_cap_carries_the_ribs_the_drawing_shows(sku):
    decor = _device(sku)["views"]["front"]["panel"]["decor"]
    cap = next(d for d in decor if d["id"] == "head-cap")
    ribs = sorted((d for d in decor if d.get("kind") == "cap-rib"), key=lambda d: d["at"][1])
    assert len(ribs) == len(RIBS[sku])
    for rib, want in zip(ribs, RIBS[sku]):
        assert rib["size"] == [44, 0.35] and rib["at"][0] == 0 and rib["fill"] == "#55585c"
        assert abs(rib["at"][1] + 0.175 - want) < 0.1
        assert rib["at"][1] + 0.35 < cap["size"][1], "a rib stands inside the head cap"


@pytest.mark.parametrize("sku", SKUS)
def test_each_c19_sits_in_the_outer_frame_the_drawing_shows(sku):
    decor = _device(sku)["views"]["front"]["panel"]["decor"]
    frames = sorted((d for d in decor if d.get("kind") == "c19-flange"), key=lambda d: d["at"][1])
    assert len(frames) == len(FRAMES[sku]) == DEVICES[sku][2]
    for frame, want in zip(frames, FRAMES[sku]):
        assert abs(frame["at"][1] - want) < 0.05
        assert frame["at"][0] == 4.94 and frame["size"] == [34.11, 42.1] and frame["rx"] == 1.5
        assert frame["stroke"] == "#55585c" and frame["stroke-width"] == 0.3 and "fill" not in frame
        assert frame["confidence"] == ("estimated" if (sku, want) == ("235", 673.81) else "drawing")
    outlets = sorted((p for p in _placements(sku) if p["ref"] == C19), key=lambda p: p["at"][1])
    for frame, outlet in zip(frames, outlets):
        assert abs((frame["at"][1] + 21.05) - (outlet["at"][1] + 13.85)) < 1.0, "the frame is round its outlet"


@pytest.mark.parametrize("sku", SKUS)
def test_the_controller_plate_carries_its_five_section_lines(sku):
    decor = _device(sku)["views"]["front"]["panel"]["decor"]
    head = next(p for p in _placements(sku) if p["id"] == "controller")["at"][1]
    lines = sorted((d for d in decor if d.get("kind") == "plate-section"), key=lambda d: d["at"][1])
    assert len(lines) == 4
    for line, want in zip(lines, SECTIONS[1:]):
        assert line["size"] == [39.1, 0.35] and line["at"][0] == 2.57 and line["fill"] == "#26272a"
        assert abs(line["at"][1] + 0.175 - (head + want)) < 0.05
    skin = (LIB / "components" / "rittal" / "pdu-controller" / "v1" / "skins" / "default.svg").read_text()
    assert '<rect id="section-1" x="0" y="73.825" width="39.1" height="0.35" fill="#26272a"/>' in skin


@pytest.mark.parametrize("sku", SKUS)
def test_the_notes_say_the_ribs_frames_and_section_lines_are_drawn(sku):
    notes = {k: v["note"] for k, v in _device(sku)["provenance"].items() if "note" in v}
    assert "full-width" in notes["head-cap-ribs"] and "1800 dpi" in notes["head-cap-ribs"]
    assert "five full-height section lines" in notes["plate-sections"]
    assert "No shared part draws a USB-A metal shell" in notes["usb-port"]
    assert ("c19-frames" in notes) == bool(DEVICES[sku][2])
    if DEVICES[sku][2]:
        assert "outer" in notes["c19-frames"] and "R1.5" in notes["c19-frames"]


@pytest.mark.parametrize("sku", SKUS)
def test_the_notes_name_their_sources_and_say_what_is_estimated(sku):
    device = _device(sku)
    notes = {k: v["note"] for k, v in device["provenance"].items() if "note" in v}
    assert "The instructions (7979204) mark the phases" in notes["phase-plates"] or sku == "210"
    assert "dri2108029en) states neither" in notes["phase-plates"] or sku == "210"
    lamps = notes["lamps"]
    assert "ETH1 jack body" in lamps and "contact pad" in lamps and "approximation" in lamps
    assert "lit lamp" not in lamps.replace("no lit lamp", "")
    assert "as the DK 7979.110" not in " ".join(notes.values())
    colour = next(g for g in device["gaps"] if g["what"] == "colour")
    assert colour["reason"] == "sources-disagree" and "RAL 9005" in colour["note"] and "#8a8a8a" in colour["note"]


def test_the_controller_part_draws_the_lamp_slots_at_the_drawings_size_and_the_head_end_notch():
    skin = (LIB / "components" / "rittal" / "pdu-controller" / "v1" / "skins" / "default.svg").read_text()
    assert skin.count('width="4.5" height="1.9"') == 2
    assert 'id="notch-head-1"' in skin and 'id="notch-head-2"' in skin
    assert '<path id="rim-head" d="M 0.6 24.3 H 1.75 V 1.0 H 37.35 V 24.3 H 38.5"' in skin, "open toward the middle"


def test_the_controller_part_carries_no_port():
    contract = yaml.safe_load((LIB / "components" / "rittal" / "pdu-controller" / "v1" / "contract.yaml").read_text())
    assert contract["version"] == "1.0.0" and "parts" not in contract
    assert {"esc", "up", "enter", "down", "display", "reset"} <= set(contract["elements"])


def test_the_two_headers_share_the_registered_key_and_their_plugs_mate_it():
    registry = yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())
    entry = next(v for k, v in _flatten(registry).items() if k == "pdu-io-header")
    assert "claims none" in entry["note"] and "unmated" not in entry
    for name in ("pdu-digital-input", "pdu-alarm-relay"):
        path = LIB / "components" / "rittal" / name / "v1" / "contract.yaml"
        assert yaml.safe_load(path.read_text())["interface"] == "pdu-io-header"
        assert 'fill="#838788"' in (path.parent / "skins" / "default.svg").read_text()
        assert "pixels" in yaml.safe_load(path.read_text())["provenance"]["colour"], "a colour read off a picture needs a count"
        plug = LIB / "components" / "rittal" / f"{name}-plug" / "v1" / "contract.yaml"
        assert yaml.safe_load(plug.read_text())["mates"] == "pdu-io-header"


# sku -> C13 frames the drawing shows, and the ones under the plug that are estimated
C13_FRAMES = {"210": (12, 0), "230": (0, 0), "235": (12, 6), "236": (24, 0), "238": (13, 5), "240": (30, 6), "242": (35, 7)}
# sku -> full-height lines other than the head-cap ribs
CELL_LINES = {"210": 7, "230": 13, "235": 8, "236": 13, "238": 15, "240": 14, "242": 10}
# sku -> where the plan view's grooves and ridge start along the strip, and how long they are
REAR_RUN = {"210": (124.1, 597.3), "230": (124.1, 597.3), "235": (92.76, 908.46), "236": (137.46, 1219.6),
            "238": (82.63, 1530.75), "240": (159.89, 1575.2), "242": (82.63, 1530.75)}


@pytest.mark.parametrize("sku", SKUS)
def test_each_c13_sits_in_the_outer_frame_the_drawing_shows(sku):
    decor = _device(sku)["views"]["front"]["panel"]["decor"]
    frames = sorted((d for d in decor if d.get("kind") == "c13-flange"), key=lambda d: d["at"][1])
    assert len(frames) == DEVICES[sku][1]
    assert sum(1 for f in frames if f["confidence"] == "estimated") == C13_FRAMES[sku][1]
    assert len(frames) - C13_FRAMES[sku][1] == C13_FRAMES[sku][0]
    outlets = sorted((p for p in _placements(sku) if p["ref"] == C13), key=lambda p: p["at"][1])
    for frame, outlet in zip(frames, outlets):
        assert frame["at"][0] == 4.1 and frame["size"] == [35.8, 28.0] and frame["rx"] == 2.5
        assert frame["stroke"] == "#55585c" and frame["stroke-width"] == 0.3 and "fill" not in frame
        assert abs((frame["at"][1] + 14.0) - (outlet["at"][1] + 11.0)) < 1.0, "the frame is round its outlet"


@pytest.mark.parametrize("sku", SKUS)
def test_the_full_height_lines_of_the_drawing_are_drawn(sku):
    decor = _device(sku)["views"]["front"]["panel"]["decor"]
    lines = [d for d in decor if d.get("kind") == "cell-line"]
    assert len(lines) == CELL_LINES[sku]
    for line in lines:
        assert line["at"][0] == 0 and line["size"][0] == 44 and line["size"][1] in (0.2, 0.35)
        assert line["fill"] == "#55585c" and line["confidence"] == "drawing"


@pytest.mark.parametrize("sku", SKUS)
def test_the_grooves_and_ridge_are_the_vector_paths_of_the_plan_view(sku):
    decor = {d["id"]: d for d in _device(sku)["views"]["rear"]["panel"]["decor"]}
    start, run = REAR_RUN[sku]
    for key, x, w in (("groove-1", 10.77, 3.0), ("groove-2", 30.18, 3.0), ("ridge", 21.2, 1.55), ("ridge-crest", 21.88, 0.2)):
        d = decor[key]
        assert d["at"][0] == x and d["size"][0] == w
        assert abs(d["at"][1] - start) < 0.05 and abs(d["size"][1] - run) < 0.05


@pytest.mark.parametrize("sku", SKUS)
def test_the_two_foot_screws_carry_the_socket_the_head_screws_have(sku):
    decor = _device(sku)["views"]["front"]["panel"]["decor"]
    heads = [d for d in decor if d.get("kind") == "screw-head"]
    sockets = [d for d in decor if d.get("kind") == "screw-socket"]
    assert len(heads) == len(sockets) == 2
    for head, socket in zip(heads, sockets):
        assert socket["size"] == [2.4, 2.4] and socket["rx"] == 1.2
        assert abs((socket["at"][0] + 1.2) - (head["at"][0] + 3)) < 0.01
        assert abs((socket["at"][1] + 1.2) - (head["at"][1] + 3)) < 0.01


@pytest.mark.parametrize("sku", SKUS)
def test_the_notes_say_the_c13_frames_lines_and_grooves_are_drawn(sku):
    notes = {k: v["note"] for k, v in _device(sku)["provenance"].items() if "note" in v}
    assert ("c13-frames" in notes) == bool(DEVICES[sku][1])
    if DEVICES[sku][1]:
        assert "outer" in notes["c13-frames"] and "R2.5" in notes["c13-frames"]
    assert "full-height" in notes["cell-lines"] and "block" in notes["cell-lines"]
    assert "3.0 wide" in notes["rear"] and "vector" in notes["rear"]


def test_the_label_cover_carries_its_rim_and_the_button_its_three_rings_and_bands():
    cover = (LIB / "components" / "rittal" / "pdu-cover-plate" / "v1" / "skins" / "default.svg").read_text()
    assert 'id="rim"' in cover and cover.count("M 0.61 2.0 V 104.52") == 1
    part = LIB / "components" / "rittal" / "pdu-metered-button" / "v1"
    contract = yaml.safe_load((part / "contract.yaml").read_text())
    assert contract["mates"] == "pdu-button" and contract["size"] == {"w": 35.0, "h": 25.0}
    skin = (part / "skins" / "default.svg").read_text()
    assert skin.count('r="7.5"') == 1 and skin.count('r="3.75"') == 1 and "M 0 5 H 35 M 0 20 H 35" in skin
    for sku in SKUS:
        buttons = [p for p in _placements(sku, "rear") if p["id"].startswith("button-")]
        assert [p["ref"] for p in buttons] == ["rittal/pdu-metered-button@1"] * 2 and all(p["at"][0] == 4.47 for p in buttons)


def test_the_controller_keys_are_the_two_rings_the_drawing_shows_and_the_headers_hold_their_holes():
    skin = (LIB / "components" / "rittal" / "pdu-controller" / "v1" / "skins" / "default.svg").read_text()
    assert skin.count('r="3.245"') == 4 and skin.count('r="4.0"') == 4
    for name, holes in (("pdu-digital-input", 2), ("pdu-alarm-relay", 3)):
        svg = (LIB / "components" / "rittal" / name / "v1" / "skins" / "default.svg").read_text()
        assert svg.count('width="5.65" height="3.1" rx="1.8"') == holes
        assert svg.count('r="0.8"') == holes


def _flatten(node, out=None):
    out = {} if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, dict) and "note" in v:
                out[k] = v
            _flatten(v, out)
    return out

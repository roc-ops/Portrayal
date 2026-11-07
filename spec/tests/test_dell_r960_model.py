"""The Dell PowerEdge R960's top view, bezel and double-width slots, against Dell's service model.

Dell's R960 service model (working/intake/dell/3d-models/r960.glb, read with glbparts.py) is held but is
Dell's CAD and is not committed, so the numbers below are written out from it, each with the node it was
read from. Positions come from the un-exploded `Main Assembly` node only (the scene also holds exploded
copies under `Extra content`). The mapping from the model's frame to the top view is

    plan x = 228.0 - cad x1        (the cover, cad x -216.0..228.0, is the 444.0 body; mirrored for the view from above)
    plan y = 883.94 - cad z1       (the rear wall: cad front face 17.2 + the ISM's 866.74 depth; the model's `Hole` cubes sit at 883.6)

and every size is the node's world box. The tests fail on a device that still carries the first pass's
figure-read estimates (ISM figure 12, 2.7% and 15% out) and pass on the model's readings.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "dell" / "r960" / "device.yaml"
COMPONENTS = LIB / "components" / "dell"

_DOC = None


def doc():
    global _DOC
    if _DOC is None:
        _DOC = yaml.safe_load(DEVICE.read_text())
    return _DOC


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1" / "contract.yaml").read_text())


def skin(name):
    return (COMPONENTS / name / "v1" / "skins" / "default.svg").read_text()


def top_bays():
    return {b["id"]: b for b in doc()["views"]["top"]["components"]["bays"]}


def top_placements():
    return {p["id"]: p for p in doc()["views"]["top"]["components"]["placements"]}


def rear_bays():
    return {b["id"]: b for b in doc()["views"]["rear"]["components"]["bays"]}


FRONTS = ["front", "front-sff8", "front-sff24", "front-sff32", "front-e3s16", "front-sff8-e3s16"]


def near(a, b, tol=0.05):
    return abs(a - b) <= tol


def gap(what):
    return next((g for g in doc()["gaps"] if g["what"] == what), None)


# --- the fans: CoolingFan Assembly, `CoolingFan_ Prefab` x 6 (nodes 65 78 91 104 117 130) ----------

def test_the_six_fans_stand_where_the_model_puts_them():
    # plan x 20.5 84.9 149.4 233.6 298.1 362.5, y 552.3: 62.7 wide, 88.2 deep. The centre post is the 84.2 between 3 and 4
    want = {"fan-1": 20.5, "fan-2": 84.9, "fan-3": 149.4, "fan-4": 233.6, "fan-5": 298.1, "fan-6": 362.5}
    bays = top_bays()
    for fid, x in want.items():
        assert near(bays[fid]["at"][0], x), (fid, bays[fid]["at"])
        assert near(bays[fid]["at"][1], 552.3), (fid, bays[fid]["at"])


def test_a_fan_is_62_7_by_88_2_and_153_2_tall_measured():
    c = contract("r960-fan")
    assert (c["size"]["w"], c["size"]["h"], c["size"]["d"]) == (62.7, 88.2, 153.2)
    assert c["size-confidence"] == {"w": "measured", "h": "measured", "d": "measured"}


def test_the_fan_cage_is_the_models_426_6_by_117_5_and_156_5_tall():
    c = contract("r960-fan-cage")
    assert (c["size"]["w"], c["size"]["h"], c["size"]["d"]) == (426.6, 117.5, 156.5)
    assert c["size-confidence"] == {"w": "measured", "h": "measured", "d": "measured"}
    at = top_placements()["fan-cage"]["at"]
    assert near(at[0], 8.7) and near(at[1], 546.8)


# --- the heatsinks: `HeatSink Prefab` x 2 on the system board, `HeatSink PEM` x 2 above them ---------

def test_each_heatsink_is_128_by_182_1_and_24_6_tall_where_the_model_puts_it():
    c = contract("r960-heatsink")
    assert (c["size"]["w"], c["size"]["h"]) == (128.0, 182.1)
    assert c["size-confidence"] == {"w": "measured", "h": "measured"}
    heights = {f["node"]: f["out"] for f in c["relief"]["features"]}
    assert heights["block"] == 23.5 and heights["pack"] == 24.7
    assert {f["confidence"] for f in c["relief"]["features"]} == {"measured"}
    pl = top_placements()
    for hid, x in {"heatsink-1": 235.3, "heatsink-2": 32.4, "heatsink-3": 235.3, "heatsink-4": 32.4}.items():
        assert near(pl[hid]["at"][0], x) and near(pl[hid]["at"][1], 349.3), (hid, pl[hid]["at"])


def test_the_heatsink_blocks_lie_between_the_memory_banks():
    # the 78.9 wide fin block is the prefab's right-hand part: at + 48.7. CPU 1 between A12 and A9, CPU 2 between B12 and B9
    pl, bays = top_placements(), top_bays()
    for hid, lo, hi in (("heatsink-1", "dimm-a12", "dimm-a9"), ("heatsink-2", "dimm-b12", "dimm-b9")):
        x = pl[hid]["at"][0]
        assert bays[lo]["at"][0] + bays[lo]["size"]["w"] < x + 48.7
        assert x + 48.7 + 78.9 < bays[hi]["at"][0]


# --- the memory: `Memory Module_SB` / `_PEM`, z 397.8..531.1 -> plan y 352.8 --------------------------

def test_every_socket_is_where_the_model_puts_its_row():
    sockets = [b for i, b in top_bays().items() if i.startswith("dimm-")]
    assert len(sockets) == 64
    assert {b["at"][1] for b in sockets} == {352.8}
    assert {b["size"]["h"] for b in sockets} == {133.4}


# --- shrouds, support bar, covers -------------------------------------------------------------------

def test_the_shrouds_and_support_bar_are_the_models():
    pl = top_placements()
    checks = {
        # name: (component, size, position)
        "air-shroud-top": ("r960-air-shroud-top-cover", (434.9, 173.8), (4.6, 362.3)),       # AirShroudTopCover
        "air-shroud-bottom": ("r960-air-shroud-bottom-cover", (438.5, 327.9), (2.8, 224.1)),  # GPU_AirShroud
        "support-bar": ("r960-support-bar", (438.3, 59.7), (2.8, 339.9)),                    # SupportBar
    }
    for pid, (name, size, at) in checks.items():
        c = contract(name)
        assert (c["size"]["w"], c["size"]["h"]) == size, name
        assert c["size-confidence"] == {"w": "measured", "h": "measured"}, name
        assert near(pl[pid]["at"][0], at[0]) and near(pl[pid]["at"][1], at[1]), (pid, pl[pid]["at"])


def test_the_shrouds_and_bar_stand_as_tall_as_the_model_says():
    # world box heights: AirShroudTopCover 80.7, GPU_AirShroud 98.0, SupportBar 29.2
    for name, out in (("r960-air-shroud-top-cover", 80.7), ("r960-air-shroud-bottom-cover", 98.0), ("r960-support-bar", 29.2)):
        feats = contract(name)["relief"]["features"]
        assert feats[0]["out"] == out and feats[0]["confidence"] == "measured", name


def test_the_system_cover_is_444_by_754_1_and_13_deep_with_its_latch_where_the_model_puts_it():
    c = contract("r960-system-cover")
    assert (c["size"]["w"], c["size"]["h"]) == (444.0, 754.1)
    assert c["size-confidence"] == {"w": "measured", "h": "measured"}
    feats = {f["node"]: f for f in c["relief"]["features"]}
    assert feats["cover"]["out"] == 13.0 and feats["cover"]["confidence"] == "measured"
    # the latch, `SystemCover_ latch`: plan x 209.4, y 599.4 as the model has the lid (slid 11.4 back), 610.8 seated; 25.2 x 63.8
    el = c["elements"]["latch"]
    assert near(el["at"][0], 209.4) and near(el["at"][1], 610.8)
    assert near(el["size"][0], 25.2) and near(el["size"][1], 63.8)
    at = top_placements()["system-cover"]["at"]
    assert near(at[0], 0.0) and near(at[1], 0.0)


# --- the supplies: `PSU Prefab` x 4 ------------------------------------------------------------------

def test_the_86_mm_supplies_run_233_5_into_the_chassis_and_stand_2_6_past_the_rear_wall():
    plan = contract("r960-psu-plan")
    assert (plan["size"]["w"], plan["size"]["h"]) == (86.3, 233.5)
    assert plan["size-confidence"] == {"w": "measured", "h": "measured"}
    for name in ("r960-psu-2800w-ac", "r960-psu-2400w-ac"):
        c = contract(name)
        assert c["size"]["d"] == 233.5 and c["size-confidence"]["d"] == "measured", name
        assert c["size-confidence"]["h"] == "measured", name      # Body_6.011, 40.1: the borrowed height confirmed
        grip = next(f for f in c["relief"]["features"] if f["node"] == "grip")
        # the model's handle is 33.5 from a face 30.9 inside the wall, 2.6 past it (ISM table 7: 2.455); a bay cannot
        # recess its occupant, so the face stands at the wall and only the 2.6 is built (the envelope test reads it)
        assert grip["uhandle"] == 2.6 and grip["confidence"] == "measured", name
    # the upper supplies project into the top view at the model's x, the can starting 30.9 in from the rear wall
    bays = rear_bays()
    assert near(bays["psu-3"]["plan"]["at"][0], 346.3) and near(bays["psu-3"]["plan"]["at"][1], 30.9)
    assert near(bays["psu-4"]["plan"]["at"][0], 11.8) and near(bays["psu-4"]["plan"]["at"][1], 30.9)


# --- the risers: Riser 1B_FL, Riser 4A - FL, Riser 3A - FL, Riser 2 ----------------------------------

def test_the_riser_plans_are_the_models_boards():
    want = {   # plan component: (w, h), rear bay: (plan x, plan y)
        "r960-riser-plan": ((159.9, 357.0), "riser-1", (280.2, 1.2)),
        "r960-riser-4-plan": ((148.4, 357.0), "riser-4", (4.7, 1.1)),
        "r960-riser-3-plan": ((134.7, 356.3), "riser-3", (148.4, 1.1)),
        "r960-riser-2-plan": ((158.3, 275.5), "riser-2", (168.7, 12.7)),
    }
    bays = rear_bays()
    for name, (size, bay, at) in want.items():
        c = contract(name)
        assert (c["size"]["w"], c["size"]["h"]) == size, name
        assert c["size-confidence"] == {"w": "measured", "h": "measured"}, name
        p = bays[bay]["plan"]["at"]
        assert near(p[0], at[0]) and near(p[1], at[1]), (bay, p)


def test_the_risers_the_model_holds_carry_its_depth_and_the_rest_say_they_borrow_it():
    held = {"r960-riser-1b": 357.0, "r960-riser-4a": 357.0, "r960-riser-3a": 356.3, "r960-riser-2": 275.5}
    for name, d in held.items():
        c = contract(name)
        assert c["size"]["d"] == d and c["size-confidence"]["d"] == "measured", name
    for name in ("r960-riser-1a", "r960-riser-1c", "r960-riser-3b", "r960-riser-3b-scale-out", "r960-riser-4b", "r960-riser-4c"):
        c = contract(name)
        assert c["size-confidence"]["d"] == "estimated", name


# --- the bezel: FrontBezel (nodes 19..46), plate `Body_3_4.003` -----------------------------------------

def test_the_bezel_is_the_models_430_8_by_168_5_and_sits_where_it_does():
    c = contract("r960-bezel")
    assert (c["size"]["w"], c["size"]["h"]) == (430.8, 168.5)
    assert c["size-confidence"]["w"] == "measured" and c["size-confidence"]["h"] == "measured"
    assert c["size-confidence"]["d"] == "datasheet"          # ISM table 7's 14.0; the model's front sits 13.5 off the face
    for view in FRONTS:
        pl = next(p for p in doc()["views"][view]["components"]["placements"] if p["id"] == "bezel")
        assert near(pl["at"][0], 25.5) and near(pl["at"][1], 2.7), (view, pl["at"])


def test_the_bezels_honeycomb_is_the_models_staggered_lattice():
    # 42 holes in the plate: columns every 38.5, 44.45 apart down a column, alternate columns offset by 22.2, 37.5 across the flats
    svg = skin("r960-bezel")
    root = ET.fromstring(svg)
    ns = {"s": "http://www.w3.org/2000/svg"}
    pat = root.find(".//s:pattern", ns)
    assert float(pat.get("width")) == 77.0 and float(pat.get("height")) == 44.45
    assert re.search(r'stroke-width="6\.9"', svg)
    assert len(pat.findall(".//s:polygon", ns)) >= 5


def test_the_release_button_is_drawn_where_the_model_has_it():
    # `FrontBezel_ Button`: 20.8 x 43.9, at the bezel's right end, 62.3 down
    svg = skin("r960-bezel")
    m = re.search(r'<rect id="release"[^>]*>', svg)
    assert m, "the release button is not drawn"
    tag = m.group(0)
    for key, val in (("x", 410.0), ("y", 62.3), ("width", 20.8), ("height", 43.9)):
        assert near(float(re.search(rf'{key}="([\d.]+)"', tag).group(1)), val), (key, tag)


# --- the gaps ---------------------------------------------------------------------------------------

def test_the_gaps_the_model_answers_are_gone_and_the_ones_it_cannot_say_why():
    assert gap("top-view-geometry-estimated") is None
    assert gap("psu-adapter-side-and-86mm-depth") is None
    shape = gap("security-bezel-shape-estimated")
    assert shape is not None and "r960.glb" in shape["note"] and "LCD" in shape["note"]
    adapter = gap("psu-adapter-not-in-the-model")
    assert adapter and adapter["reason"] == "needs-photo" and "r960.glb" in adapter["note"]


def test_where_the_model_and_the_ism_disagree_both_are_recorded():
    reasons = {g["what"]: g["reason"] for g in doc()["gaps"]}
    for what in ("top-view-model-vs-ism", "psu-x-model-vs-figure-10", "memory-sockets-model-vs-figure-95", "riser-length-model-vs-table-13"):
        assert reasons.get(what) == "sources-disagree", what
    text = {g["what"]: g["note"] for g in doc()["gaps"]}
    assert "30" in text["memory-sockets-model-vs-figure-95"] and "32" in text["memory-sockets-model-vs-figure-95"]
    assert "5.2" in text["psu-x-model-vs-figure-10"] and "16.9" in text["psu-x-model-vs-figure-10"]
    assert "half" in text["riser-length-model-vs-table-13"]


def test_the_top_views_provenance_cites_the_model():
    prov = doc()["provenance"]["top"]
    assert prov["confidence"] in ("measured", "mixed") or "measured" in prov["confidence"]
    assert "r960.glb" in prov["note"] and "Main Assembly" in prov["note"]
    assert "r960.glb" in doc()["provenance"]["bezel"]["note"]
    for name in ("r960-fan", "r960-fan-cage", "r960-heatsink", "r960-air-shroud-top-cover", "r960-air-shroud-bottom-cover",
                 "r960-support-bar", "r960-system-cover", "r960-psu-plan", "r960-psu-2800w-ac", "r960-psu-2400w-ac", "r960-bezel",
                 "r960-riser-plan", "r960-riser-2-plan", "r960-riser-3-plan", "r960-riser-4-plan"):
        text = yaml.safe_dump(contract(name)["provenance"])
        assert "r960.glb" in text, name


def test_the_header_no_longer_says_no_service_model_was_used():
    head = DEVICE.read_text().split("format: 1")[0]
    assert "no stencil, service model" not in head and "r960.glb" in head


# --- rc3's double-width slots -------------------------------------------------------------------------

def test_the_double_width_filler_draws_one_tall_vent_window_declared_estimated():
    svg = skin("r960-pcie-filler-fh-2slot")
    root = ET.fromstring(svg)
    ns = {"s": "http://www.w3.org/2000/svg"}
    windows = [r for r in root.findall(".//s:rect", ns) if r.get("id") != "plate" and float(r.get("height", 0)) > 20]
    assert len(windows) == 1, "one window spanning both slots"
    w = windows[0]
    assert float(w.get("height")) > 30.0 and float(w.get("y")) < 6.0
    # and no second window under it: nothing but the one rect is wider than 80 mm
    assert len([r for r in root.findall(".//s:rect", ns) if float(r.get("width", 0)) > 80 and r.get("id") != "plate"]) == 1
    prov = yaml.safe_dump(contract("r960-pcie-filler-fh-2slot")["provenance"])
    assert "one tall" in prov and "ESTIMATED" in prov.upper()


# --- the nits -------------------------------------------------------------------------------------------

def test_mest_carries_its_source():
    lines = DEVICE.read_text().splitlines()
    i = next(n for n, line in enumerate(lines) if "text: 'MEST'" in line)
    assert "printed on the chassis under the BOSS bay, ISM figure 10" in lines[i - 1]


@pytest.mark.parametrize("view", FRONTS)
def test_every_cpu_tag_on_a_number_strip_is_boxed_as_figure_2_boxes_them(view):
    sil = doc()["views"][view]["silkscreen"]
    tags = [s for s in sil if str(s.get("text", "")).startswith("CPU")]
    boxes = [s for s in sil if "path" in s and s["path"].rstrip().endswith("Z") and re.fullmatch(r"M 0 0 H [\d.]+ V [\d.]+ H 0 Z", s["path"])
             and "for" not in s]
    for t in tags:
        cx, base = t["at"]
        hit = [b for b in boxes if b["at"][0] < cx < b["at"][0] + float(b["path"].split()[4]) and b["at"][1] < base]
        assert hit, (view, t)

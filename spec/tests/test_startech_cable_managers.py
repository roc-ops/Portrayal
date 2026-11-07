"""StarTech.com's cable managers (roc-ops/Portrayal#1098, part of #1091): two finger ducts, two D-ring
panels, a brush panel and three D-ring hooks.

Every figure below is what StarTech.com's own dimensioned drawing (`<SKU>_Diagram.pdf`, millimetres,
third angle projection) or data sheet states, so a model that drifts from its drawing fails by name.
What the drawings do not dimension is scaled off them and is estimated; the tests say which.
The rack kit's half of the features (a cable laid through a ring, along a duct, through a pass, a hook
placed on one rail with `side`) is `spec/tests/js/rack-startech-managers.mjs`, run by
`test_rack_kit_js.py`.

These read the build (`library/dist`, `library/exports`) and skip without it, like the other sweeps
over compiled drawings.

The six panels and ducts are `rack` parts and export their rack units, as the FS horizontal managers
and Leviton's do: a 1U plate fills its unit. Only the three hooks are `rack-face`, export
`u_height: 0` and are placed with `side`.
"""
import json
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
EXPORTS = LIB / "exports"

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# name -> (width, height, depth, ru, ear plane mm behind the part's front)
# CMDUCT1UX/CMDUCT2U drawings: 482.60, 44.00 / 88.45, 71.60; CABLMANAGERH: 482.60, 43.69, 95.00 and 6.21
# between the ear plane and the folds; CABLMANAGER2: 482.6, 43.5, the rings 76.6 out of the ear plane and the
# body 12 behind it (the data sheet's 88.6); CMBRUSH1U: 482.0, 43.7, 17.2
PANELS = {
    "cmduct1ux": (482.6, 44.0, 71.6, 1, 71.6),
    "cmduct2u": (482.6, 88.45, 71.6, 2, 71.6),
    "cablmanagerh": (482.6, 43.69, 95.0, 1, 88.79),
    "cablmanager2": (482.6, 43.5, 88.6, 1, 76.6),
    "cmbrush1u": (482.0, 43.7, 17.2, 1, 0.0),
}
# CMHOOK1U/1UN: 57.0 / 45.0 across, 44.6 high, 101.3 out; CMHOOKMW: 111.0 x 70.1 x 117.0 (15.0 + 102.0), "1.5U"
HOOKS = {
    "cmhook1u": (57.0, 44.6, 101.3, 1),
    "cmhook1un": (45.0, 44.6, 101.3, 1),
    "cmhookmw": (111.0, 70.1, 117.0, 1.5),
}
DUCTS = ("cmduct1ux", "cmduct2u")
ALL = list(PANELS) + list(HOOKS)
SLOT_PITCH = 27.84
SLOT_GAP = 11.0
SLOTS = 15


def svg(name, view, config="base"):
    return ET.parse(DIST / f"{name}.{config}.{view}.svg").getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "startech" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components" / "startech" / name / "v1" / "contract.yaml").read_text())


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def translate(el):
    m = re.match(r"translate\(([-\d.]+),([-\d.]+)\)", el.get("transform") or "")
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)


# --- the maker ---------------------------------------------------------------------------------

def test_startech_is_a_hardware_vendor_listed_directly_after_celestica():
    text = (ROOT / "spec/schemas/vendors.yaml").read_text()
    keys = [l.strip().rstrip(":") for l in text.splitlines() if l.startswith("  ") and not l.startswith("   ") and l.rstrip().endswith(":")]
    assert keys.index("startech") == keys.index("celestica") + 1 and keys[keys.index("startech") + 1] == "maiaedge"
    vendors = yaml.safe_load(text)["vendors"]
    assert vendors["startech"]["role"] == "hardware" and vendors["startech"]["display"] == "StarTech.com"
    assert "data sheet" in vendors["startech"]["source"] and "drawing" in vendors["startech"]["source"]


@pytest.mark.parametrize("name", ALL)
def test_each_part_cites_its_data_sheet_and_its_drawing_by_url_and_hash(name):
    doc = device_yaml(name)
    sheet = doc["datasheet"]
    assert doc["manufacturer"] == "StarTech.com"
    assert sheet["url"] == f"https://media.startech.com/cms/pdfs/{name}_datasheet.pdf" and re.fullmatch(r"[0-9a-f]{64}", sheet["sha256"])
    drawing = next(r for r in doc["references"] if r["url"].endswith(f"{name.upper()}_Diagram.pdf"))
    assert drawing["url"].startswith("https://media.startech.com/downloads/image/") and re.fullmatch(r"[0-9a-f]{64}", drawing["sha256"])


# --- each device's envelope against its drawing -------------------------------------------------

@pytest.mark.parametrize("name", list(PANELS))
def test_a_panel_or_duct_is_the_size_its_drawing_dimensions(name):
    w, h, d, ru, ear = PANELS[name]
    c = device_yaml(name)["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, d, ru)
    assert c.get("mount") is None and c["full-depth"] is False and c["shell"] == "sheet"
    # the plate is the whole width of the rack, its ears the ends of the sheet: the face is drawn whole
    assert c["width"] >= 480
    at = c["ears"]["positions"][0]
    assert at["default"] and close(at["at"], ear, 0.01)


@needs_dist
@pytest.mark.parametrize("name", list(PANELS))
def test_the_catalogue_carries_the_same_envelope_and_ears(name):
    w, h, d, ru, ear = PANELS[name]
    r = rack(name)
    assert (r["w"], r["h"], r["d"], r["ru"]) == (w, h, d, ru) and r["ears"]["default"]["at"] == ear and r["shell"] == "sheet"


@pytest.mark.parametrize("name", list(PANELS))
def test_the_back_plate_runs_the_full_width(name):
    """The owner sent earlier lines back for a back plate that stopped short of the ends: the plate each
    part stands on is as wide as the part, ears included."""
    c = device_yaml(name)["chassis"]
    comp = {"cmduct1ux": "cmduct1ux-base", "cmduct2u": "cmduct2u-base", "cablmanagerh": "cablmanagerh-panel",
            "cablmanager2": "cablmanager2-panel", "cmbrush1u": "cmbrush1u-panel"}[name]
    assert contract(comp)["size"]["w"] == c["width"]
    rear = device_yaml(name)["views"]["rear"]
    assert rear["size"]["w"] == c["width"]
    if name != "cmbrush1u":
        assert any(d["size"][0] == c["width"] for d in rear["panel"]["decor"]), "a rear piece spans the whole width"


@pytest.mark.parametrize("name", list(HOOKS))
def test_a_hook_is_a_rack_face_part_narrower_than_the_opening_and_states_no_whole_unit(name):
    w, h, d, ru = HOOKS[name]
    c = device_yaml(name)["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, d, ru)
    assert c["mount"] == "rack-face" and c["width"] < 450, "narrower than the 19-inch opening, so it takes a `side`"
    assert "full-depth" not in c and "ears" not in c


def test_the_hook_that_is_one_and_a_half_units_states_1_5_and_does_not_change_the_format():
    c = device_yaml("cmhookmw")["chassis"]
    assert c["ru"] == 1.5 and c["height"] == 70.1
    assert any(g["what"] == "hook-facing" for g in device_yaml("cmhookmw")["gaps"])


# --- the ducts: fingers on both walls, a duct a cable runs along, a cover that comes off ---------

@needs_dist
@pytest.mark.parametrize("name", DUCTS)
def test_each_duct_publishes_its_duct_with_the_drawn_slot_and_the_scaled_pitch(name):
    el = by_id(svg(name, "front"))["guide--duct"]
    assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "x"
    assert float(el.get("data-guide-finger-gap")) == SLOT_GAP, "the drawing's 11.00"
    assert float(el.get("data-guide-finger-pitch")) == SLOT_PITCH
    assert float(el.get("width")) == 435.0, "the drawing's 435.00 duct"
    clear = {"cmduct1ux": 42.0, "cmduct2u": 86.45}[name]
    assert close(float(el.get("height")), clear, 0.03), "the 44 / 88.45 less a 1.0 wall each side"
    assert rack(name)["guides"] == {"front": ["duct"]}


@needs_dist
@pytest.mark.parametrize("name", DUCTS)
def test_the_slots_are_fifteen_a_wall_eleven_wide_on_the_scaled_pitch(name):
    for view in ("top", "bottom"):
        el = by_id(svg(name, view))
        slots = sorted((e for i, e in el.items() if re.fullmatch(r"wall-(top|bottom)--s\d+", i)), key=lambda e: int(e.get("id").split("--s")[1]))
        assert len(slots) == SLOTS, view
        xs = [float(re.match(r"M([-\d.]+),", s.get("d")).group(1)) for s in slots]
        assert [round(b - a, 2) for a, b in zip(xs, xs[1:])] == [SLOT_PITCH] * (SLOTS - 1)
        for s in slots:
            nums = [float(v) for v in re.findall(r"[-\d.]+", s.get("d"))]
            assert close(nums[8] - nums[0], SLOT_GAP, 0.01), "each slot's width is the drawing's 11.00"


@needs_dist
@pytest.mark.parametrize("name", DUCTS)
def test_fingers_stand_on_both_the_top_and_the_bottom_wall_each_with_its_root(name):
    """"Fingers on either side" read from the quick-start guide's "available along the length on both sides":
    the top wall and the bottom wall of the one open face. Each wall is sixteen fingers on a solid root, so the
    fingers are attached to the body and not loose tongues."""
    el = by_id(svg(name, "front"))
    for wall in ("fingers-upper", "fingers-lower"):
        assert wall in el and f"{wall}--root" in el
        fingers = [i for i in el if re.fullmatch(wall + r"--f\d+", i)]
        assert len(fingers) == 16, wall
        # the fingers reach 13.5 mm short of the front (under the cover's 21.7); the root stops 52.5 short of it,
        # at the slot roots: z-out is measured back from the part's front
        assert float(el[f"{wall}--f0"].get("data-z-out")) == -13.5 and float(el[f"{wall}--root"].get("data-z-out")) == -52.5


@needs_dist
@pytest.mark.parametrize("name", DUCTS)
def test_the_cover_ships_fitted_is_a_removable_part_and_the_drawing_without_it_shows_the_fingers(name):
    cfgs = device_yaml(name)["configurations"]
    assert cfgs["base"]["default"] is True and cfgs["cover-off"]["kind"] == "example"
    on, off = by_id(svg(name, "front")), by_id(svg(name, "front", "cover-off"))
    assert on["cover"].get("data-behaviour") == "mounts", "fitted as it ships, with a pull handle"
    assert "cover" not in off, "and the drawing without it"
    assert "fingers-upper" in off and "fingers-lower" in off, "taking the cover off shows the fingers"
    comp = contract({"cmduct1ux": "cmduct1ux-cover", "cmduct2u": "cmduct2u-cover"}[name])
    assert comp["behaviour"] == "mounts" and comp["lid"] is True
    for view, ids in (("top", ("cover-top",)), ("bottom", ("cover-bottom",))):
        assert all(i in by_id(svg(name, view)) for i in ids)
        open_view = by_id(svg(name, view, "cover-off"))
        assert not any(i.startswith("cover") for i in open_view), f"{view}: no cover once it is off"
        assert any(i.endswith("--s15") for i in open_view), f"{view}: the fifteen slots show, open to the front"
    for view in ("left", "right"):
        assert any("cover" in (e.get("data-kind") or "") for e in by_id(svg(name, view)).values())
        assert not any("cover" in (e.get("data-kind") or "") for e in by_id(svg(name, view, "cover-off")).values())


@pytest.mark.parametrize("name", DUCTS)
def test_no_mechanism_is_invented_for_the_cover_latches(name):
    doc = device_yaml(name)
    assert any(g["what"] == "cover-latches" for g in doc["gaps"]), "four latches, one a corner; the format has none"
    assert "latch" not in json.dumps(doc["views"]).lower() and "hinge" not in json.dumps(doc["views"]).lower()


# --- the pass-throughs: three in each duct, four holes in the D-ring panel, the brush window ------

@needs_dist
@pytest.mark.parametrize("name,shape,size", [("cmduct1ux", "obround", [100.0, 25.0]), ("cmduct2u", "rect", [100.0, 69.0])])
def test_each_duct_has_three_open_pass_throughs_in_its_plate(name, shape, size):
    el = by_id(svg(name, "rear"))
    passes = [e for e in el.values() if e.get("data-class") == "pass"]
    assert len(passes) == 3
    assert {e.get("data-pass-shape") for e in passes} == {shape} and {e.get("data-pass-cover") for e in passes} == {"open"}
    declared = device_yaml(name)["views"]["rear"]["passes"]
    assert [p["size"] for p in declared] == [size] * 3
    assert [p["at"][0] for p in declared] == [51.3, 191.3, 331.3], "140 apart, centred on the plate"
    assert rack(name)["passes"] == {"rear": [f"pass-through-{k}" for k in range(1, 4)]}


@needs_dist
def test_cablmanagerh_has_four_round_holes_of_the_drawn_diameter_and_records_the_makers_power_cable_note():
    declared = device_yaml("cablmanagerh")["views"]["rear"]["passes"]
    assert [p["size"] for p in declared] == [[29.0, 29.0]] * 4, 'the drawing\'s "phi 29.00"'
    assert {p["cover"] for p in declared} == {"open"}
    assert [p["at"][0] for p in declared] == [76.8, 176.8, 276.8, 376.8]
    assert len(by_id(svg("cablmanagerh", "rear"))) and sum(1 for e in svg("cablmanagerh", "rear").iter() if e.get("data-class") == "pass") == 4
    assert "Power cables may not fit" in device_yaml("cablmanagerh")["attrs"]["features"]["pass-through-note"]


@needs_dist
def test_the_brush_panel_has_a_brush_pass_across_its_window_with_the_brush_drawn_over_it():
    declared = device_yaml("cmbrush1u")["views"]["front"]
    window = declared["passes"][0]
    assert (window["size"], window["cover"]) == ([382.0, 23.3], "brush"), "the drawing's 382.0 by 23.3"
    el = svg("cmbrush1u", "front")
    p = by_id(el)["pass--brush-window"]
    assert p.get("data-pass-cover") == "brush"
    brush = declared["panel"]["decor"][0]
    assert brush["pattern"] == "brush" and brush["at"] == window["at"] and brush["size"] == window["size"]
    # the window sits 12.4 below the top edge and 8.0 above the bottom, as the drawing dimensions it
    assert close(window["at"][1], 12.4) and close(43.7 - window["at"][1] - window["size"][1], 8.0)


# --- the rings -----------------------------------------------------------------------------------

@needs_dist
def test_cablmanagerh_publishes_five_ring_guides_each_standing_on_the_panel():
    root = by_id(svg("cablmanagerh", "front"))
    rings = [root[f"guide-{k}"] for k in range(1, 6)]
    for e in rings:
        assert e.get("data-guide") == "ring" and e.get("data-guide-run") == "x" and e.get("data-guide-depth") == "9.1"
        assert e.get("data-guide-aperture") == "22.6 79.59" and e.get("data-in") == "panel"
    xs = [translate(e)[0] + 4.55 for e in rings]
    assert [round(b - a, 1) for a, b in zip(xs, xs[1:])] == [100.0] * 4 and close(xs[2], 482.6 / 2, 0.01)
    # the loop stands out of the panel to the front of the part, the drawing's 95.00 less the 6.21 fold and the
    # sheet above the plate: its bars reach z-out 0, measured back from the front
    assert float(root["guide-1--bar-top"].get("data-z-out")) == 0 and float(root["guide-1--tip"].get("data-z-out")) == 0
    assert rack("cablmanagerh")["rings"]["guide-1"]["z"] > 0


@needs_dist
def test_cablmanager2_publishes_five_rings_the_middle_three_along_the_panel_and_the_ends_up_and_down_it():
    root = by_id(svg("cablmanager2", "front"))
    runs = [root[f"guide-{k}"].get("data-guide-run") for k in range(1, 6)]
    assert runs == ["y", "x", "x", "x", "y"]
    xs = [translate(root[f"guide-{k}"])[0] + (20.0 if runs[k - 1] == "y" else 5.2) for k in range(1, 6)]
    assert [round(x - 241.3, 1) for x in xs] == [-184.0, -105.0, 0.0, 105.0, 184.0]
    assert float(root["guide-2--bar-top"].get("data-z-out")) == 0, "the loop stands out to the front of the part"


@needs_dist
@pytest.mark.parametrize("name,opening", [("cmhook1u", 8.0), ("cmhook1un", 11.0), ("cmhookmw", None)])
def test_each_hook_publishes_a_ring_guide_and_its_loop_is_attached_to_the_plate(name, opening):
    root = by_id(svg(name, "front"))
    ring = root["guide-1"]
    assert ring.get("data-guide") == "ring" and ring.get("data-guide-run") == "y" and ring.get("data-in") == "plate"
    aperture = {"cmhook1u": "50.6 92.6", "cmhook1un": "38.6 92.6", "cmhookmw": "57.6 95.6"}[name]
    assert ring.get("data-guide-aperture") == aperture, "the datasheet's internal width and depth"
    # the loop starts on the plate's floor: its near wall is on it, and the loop stands the whole way out
    assert float(root["guide-1--near"].get("data-z-lift") or 0) >= 0
    far = root["guide-1--far-left"] if "guide-1--far-left" in root else root["guide-1--far"]
    assert float(far.get("data-z-out")) == 0, "the far end of the loop is the front of the part, the 101.3 or 117.0"
    if opening:
        left, right = root["guide-1--far-left"], root["guide-1--far-right"]
        gap = float(right.get("x")) - (float(left.get("x")) + float(left.get("width")))
        assert close(gap, opening, 0.01), "the opening a cable is slipped in through is the drawing's"


@pytest.mark.parametrize("name", list(HOOKS))
def test_the_hook_opening_is_drawn_and_said_to_be_a_gap_not_declared_as_a_slit(name):
    ring = contract({"cmhook1u": "cmhook1u-ring", "cmhook1un": "cmhook1un-ring", "cmhookmw": "cmhookmw-ring"}[name])
    assert "slit" not in ring["guide"], "a slit is a range along a leg's height; no mechanism is invented"
    assert any(g["what"] == "hook-opening" for g in device_yaml(name)["gaps"])


@needs_dist
def test_cablmanager2_rings_are_removable_parts_that_ship_fitted_and_the_drawing_without_them_shows_the_panel():
    cfgs = device_yaml("cablmanager2")["configurations"]
    assert cfgs["base"]["default"] is True and cfgs["rings-off"]["kind"] == "example"
    for comp in ("cablmanager2-ring", "cablmanager2-ring-end"):
        assert contract(comp)["behaviour"] == "mounts"
    on, off = by_id(svg("cablmanager2", "front")), by_id(svg("cablmanager2", "front", "rings-off"))
    for k in range(1, 6):
        assert on[f"guide-{k}"].get("data-behaviour") == "mounts", "fitted as it ships, with a pull handle"
        assert f"guide-{k}" not in off, "and the drawing without it"
    assert "panel" in off, "the panel and its open seats show"
    assert any(e.get("data-kind") == "ring" for e in by_id(svg("cablmanager2", "top")).values())
    for view in ("top", "bottom", "left", "right"):
        assert not any(e.get("data-kind") == "ring" for e in by_id(svg("cablmanager2", view, "rings-off")).values()), view


def test_the_end_rings_turn_is_a_gap_and_no_mechanism_is_invented_for_it():
    doc = device_yaml("cablmanager2")
    assert any(g["what"] == "ring-turn" for g in doc["gaps"]), 'the maker says the end hooks "can be turned 90"; the format cannot turn a ring'
    assert "turn" not in json.dumps(contract("cablmanager2-ring-end")["guide"])


# --- the faces are real: nothing is a plain slab, nothing hard-coded white or black --------------

def test_no_fill_is_pure_white_or_pure_black_so_each_face_reads_on_the_light_and_the_dark_stage():
    """A part is black steel drawn in greys that read on both stages. The one white in a skin is the light
    on the steel, a low-opacity overlay (`fill-opacity`) that lifts a dark plate off a dark stage; a device
    file states no white or black fill at all."""
    bad = re.compile(r"""fill\s*[=:]\s*["']?(#f{3}(?:f{3})?|#0{3}(?:0{3})?|white|black)\b""", re.I)
    devices = list((LIB / "devices" / "startech").rglob("device.yaml"))
    skins = list((LIB / "components" / "startech").rglob("*.svg"))
    assert devices and skins
    for p in devices:
        assert not bad.search(p.read_text()), p
    for p in skins:
        for tag in re.findall(r"<[^>]*>", p.read_text()):
            assert not bad.search(tag) or "fill-opacity" in tag, (p, tag)
    assert any("floor-lit" in p.read_text() for p in skins), "the plates carry their light"


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_each_part_builds_a_solid_that_is_its_plates_and_not_a_box(name):
    assert rack(name)["shell"] == "sheet"
    solids = rack(name)["solids"]
    assert solids and all(s["box"]["w"] > 0 and s["box"]["h"] > 0 and s["box"]["d"] > 0 for s in solids)
    # the plate the part stands on is among them, as wide as the part
    floor = next(s for s in solids if s["part"] in ("base/floor", "panel/floor", "plate/floor"))
    # a panel's plate is as wide as the panel; a hook's is the strip that bolts to the rail
    assert floor["box"]["w"] == (rack(name)["w"] if name in PANELS else {"cmhook1u": 19.0, "cmhook1un": 19.0, "cmhookmw": 55.0}[name])


# --- capacity: none stated, none invented ------------------------------------------------------------

@pytest.mark.parametrize("name", ALL)
def test_no_cable_capacity_is_stated_because_no_source_states_one(name):
    doc = device_yaml(name)
    perf = (doc.get("attrs") or {}).get("performance") or {}
    assert "cable-capacity" not in perf and "cable-capacity-estimated" not in perf
    assert any(g["what"] == "cable-capacity" and g["reason"] == "vendor-silent" for g in doc["gaps"])


# --- the DCIM device types: panels fill their unit, hooks occupy none ----------------------------------

@pytest.mark.parametrize("name", ALL)
def test_the_dcim_device_types_say_the_rack_units_and_not_full_depth(name):
    doc = device_yaml(name)
    model = doc["model"]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "StarTech.com" / f"{model}.yaml"
        assert path.is_file(), f"{path} is missing: run dcim_export.py --device {name}"
        out = yaml.safe_load(path.read_text())
        assert out["manufacturer"] == "StarTech.com" and out["model"] == model
        if name in HOOKS:
            assert out["u_height"] == 0 and out["is_full_depth"] is False, "a rack-face part occupies no unit"
        else:
            assert out["u_height"] == float(doc["chassis"]["ru"]) and out["is_full_depth"] is False

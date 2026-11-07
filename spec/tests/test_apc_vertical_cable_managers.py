"""APC's Performance vertical cable managers for 2 and 4 post open frame racks (roc-ops/Portrayal#1097,
part of #1091): the single-sided AR8615, AR8635 and AR8665 and the double-sided AR8625, AR8645 and AR8675.

Every figure below is what APC's own data sheet or instruction sheet (990-4576A-001) prints, in the units
it prints them. What no APC document dimensions (a finger's size, the door's, the split of the depth
between the channels and the spine) is estimated in the device and is held here only to what the model
itself declares. The rack kit's half of the features (a cable laid down a duct beside the rack) is
`spec/tests/js/rack-apc-verticals.mjs`, run by `test_rack_kit_js.py`.

These read the build (`library/dist`, `library/exports`) and skip without it, like the other sweeps over
compiled drawings.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

from portrayal import labs

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
EXPORTS = LIB / "exports"
RU = 44.45

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# name -> (model, sides, width mm, depth mm, net weight kg): the "Specifications" of each product data sheet.
# 10 in is printed 253 mm and is drawn as printed; the instruction sheet (990-4576A-001) splits the six
# into single-sided AR8615, AR8635 and AR8665 and double-sided AR8625, AR8645 and AR8675.
PARTS = {
    "ar8615": ("AR8615", 1, 152.0, 360.0, 27.2),
    "ar8625": ("AR8625", 2, 152.0, 660.0, 29.9),
    "ar8635": ("AR8635", 1, 253.0, 360.0, 29.5),
    "ar8645": ("AR8645", 2, 253.0, 660.0, 34.0),
    "ar8665": ("AR8665", 1, 304.0, 360.0, 30.4),
    "ar8675": ("AR8675", 2, 304.0, 660.0, 36.3),
}
HEIGHT = 2134.0           # 84.02 in (2134 mm) on every data sheet
FINGERS = 44              # a finger to each of 44 rack units, a column down each side of the channel
FINGER_PITCH = 44.45      # "smooth plastic fingers at 1U increments"
FINGER_ACROSS = 22.0      # estimated; the channel is the width less this on each side and a 6 mm margin
CHANNEL_MARGIN = 6.0 + FINGER_ACROSS


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "apc" / name / "device.yaml").read_text())


def contract(ref):
    return yaml.safe_load((LIB / "components" / ref.split("@")[0] / "v1" / "contract.yaml").read_text())


def svg(name, view, config="base"):
    return ET.parse(DIST / f"{name}.{config}.{view}.svg").getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


def faces(name):
    """The working faces of a part: front only for a single-sided one, front and rear for a double-sided."""
    return ("front", "rear") if PARTS[name][1] == 2 else ("front",)


# --- the maker ------------------------------------------------------------------------------------

def test_apc_is_already_a_hardware_vendor_and_this_change_adds_no_entry():
    vendors = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    assert vendors["apc"]["role"] == "hardware"


# --- each device's envelope against its data sheet, and its sides against the instruction sheet ----

@pytest.mark.parametrize("name", list(PARTS))
def test_the_envelope_is_the_size_the_data_sheet_prints(name):
    model, sides, w, d, kg = PARTS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "APC" and doc["model"] == model
    assert close(c["width"], w) and close(c["height"], HEIGHT) and close(c["depth"], d)
    assert c["mount"] == "rack-side" and c["shell"] == "sheet"
    assert c["height"] > c["width"], "a vertical manager is drawn as it stands, portrait"
    assert close(c["weight-kg"], kg, 0.0005) and close(doc["attrs"]["physical"]["weight-kg"], kg, 0.0005)


@pytest.mark.parametrize("name", list(PARTS))
def test_the_sidedness_is_the_instruction_sheets(name):
    """990-4576A-001: single-sided AR8615, AR8635 and AR8665; double-sided AR8625, AR8645 and AR8675.
    The data sheets' depth says the same: 14.2 in (360 mm) for one channel, 26.0 in (660 mm) for two."""
    _, sides, _, d, _ = PARTS[name]
    doc = device_yaml(name)
    rear = (doc["views"]["rear"].get("components") or {}).get("placements", [])
    guides = doc["views"]["rear"].get("guides", [])
    assert bool(guides) == (sides == 2) and bool(rear) == (sides == 2)
    assert len(doc["views"]["front"]["guides"]) == 1
    doors = [p for v in doc["views"].values() for p in (v.get("components") or {}).get("placements", [])
             if "door" in p["ref"]]
    assert len(doors) == sides, "one door to each working face"
    assert ("both faces" in doc["description"] or "double-sided" in doc["description"]) == (sides == 2)


def test_the_height_is_stated_as_44_units_so_one_part_stands_beside_either_rack():
    """The part is 2134 mm; the AR201 is 45U and 2136 mm outer, the AR203A 44U and 2130. `ru: 44` is the
    rack height it runs beside, the fingers' 44 units, and the one figure that fits both (L154)."""
    for name in PARTS:
        assert device_yaml(name)["chassis"]["ru"] == 44
    ar201 = yaml.safe_load((LIB / "racks/apc/ar201/rack.yaml").read_text())
    ar203a = yaml.safe_load((LIB / "racks/apc/ar203a/rack.yaml").read_text())
    assert (ar201["ru"], ar203a["ru"]) == (45, 44)
    assert abs(ar201["outer"]["h"] - HEIGHT) < 5 and abs(ar203a["outer"]["h"] - HEIGHT) < 5


# --- the fingers: a duct with run y on each working face, a finger to each rack unit ------------------

@needs_dist
@pytest.mark.parametrize("name", list(PARTS))
def test_each_working_face_publishes_its_vertical_duct_at_one_rack_unit_pitch(name):
    _, _, w, _, _ = PARTS[name]
    published = rack(name)["guides"]
    for face in faces(name):
        gid = "duct" if face == "front" else "rear-duct"
        el = by_id(svg(name, face))[f"guide--{gid}"]
        assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "y"
        assert float(el.get("data-guide-finger-pitch")) == FINGER_PITCH
        assert close(float(el.get("data-guide-finger-gap")), FINGER_PITCH - 31.0)
        assert close(float(el.get("width")), w - 2 * CHANNEL_MARGIN) and close(float(el.get("height")), HEIGHT)
        assert gid in published[face]
    if PARTS[name][1] == 1:
        assert "rear" not in published or not published["rear"]


@needs_dist
@pytest.mark.parametrize("name", list(PARTS))
def test_each_face_has_a_finger_to_each_of_44_rack_units_down_both_sides_of_the_channel(name):
    for face in faces(name):
        el = by_id(svg(name, face))
        stem = "fingers-" if face == "front" else "rear-fingers-"
        for side in ("left", "right"):
            sections = {i.split("--")[0] for i in el if i.startswith(stem + side) and "--a" in i}
            assert len(sections) == 4, "four sections of 11, a side"
            arms = [i for i in el if i.split("--")[0] in sections and "--a" in i]
            assert len(arms) == FINGERS, (name, face, side)


@needs_dist
def test_the_fingers_are_one_rack_unit_apart_down_the_whole_height():
    """The finger sections are placed 11 fingers apart and each holds its fingers at 44.45, so the
    pitch is one rack unit from the top finger to the last and never drifts between sections."""
    doc = device_yaml("ar8615")
    sections = [p for p in doc["views"]["front"]["components"]["placements"] if p["id"].startswith("fingers-left-")]
    ys = [p["at"][1] for p in sections]
    assert [round(b - a, 2) for a, b in zip(ys, ys[1:])] == [round(11 * RU, 2)] * 3
    comp = contract(sections[0]["ref"])
    arms = sorted((e["at"][1] for n, e in comp["elements"].items() if n.startswith("a")))
    assert [round(b - a, 2) for a, b in zip(arms, arms[1:])] == [RU] * 10
    first, last = ys[0] + arms[0], ys[-1] + arms[-1]
    assert abs(first - (HEIGHT - (last + 31.0)) ) < 0.5, "the 44 fingers are centred on the height"


def _spans(root, stems):
    spans = []
    for g in root.iter("{http://www.w3.org/2000/svg}g"):
        if not (g.get("id") or "").startswith(stems) or g.get("data-z-lift") is None:
            continue
        for r in g.iter():
            if r.get("data-z-out") is not None:
                spans.append((r.get("data-path"), float(g.get("data-z-lift")) + float(r.get("data-z-lift") or 0),
                              float(r.get("data-z-out"))))
    return spans


@needs_dist
@pytest.mark.parametrize("name", list(PARTS))
def test_the_fingers_stand_on_the_floor_of_their_channel_and_not_through_the_back_plate(name):
    """Fingers drawn as flat tongues, or detached from the body, were what earlier cable-manager lines were
    sent back for. Each finger rises from the floor of its well and reaches toward the face, inside it."""
    _, sides, _, d, _ = PARTS[name]
    for face in faces(name):
        root = svg(name, face)
        depths = {float(e.get("data-depth")) for e in root.iter() if e.get("data-depth")}
        assert depths == {300.0}, depths
        spans = _spans(root, ("fingers-", "rear-fingers-"))
        assert spans, f"{name} {face}: no finger carries relief"
        for path, start, end in spans:
            assert start >= -300.0 - 0.15, f"{face} {path}: starts behind its floor"
            assert end > start and end <= 0.15, f"{face} {path}: ends {end}"
        assert min(s for _, s, _ in spans) == pytest.approx(-300.0, abs=0.15), "fingers stand ON the floor"
    spine = d - 300.0 * sides
    assert close(spine, 60.0), "the back plate zone between the wells"


@pytest.mark.parametrize("name", ["perf-vcm-finger-section"])
def test_a_finger_is_an_arm_with_a_hooked_tip_and_not_a_flat_tongue(name):
    comp = contract("apc/" + name)
    feats = {f["node"]: f for f in comp["relief"]["features"]}
    assert set(feats) == set(comp["elements"]), "every drawn element is a feature"
    for k in range(1, 12):
        arm, tip = feats[f"a{k}"], feats[f"t{k}"]
        assert arm.get("lift", 0) == 0 and arm["out"] > 250, "the arm rises from the floor"
        assert tip["lift"] < arm["out"] < tip["out"] <= 300, "the tip is a hook on the arm's end, in the face"
        assert tip["color"] != arm["color"]
        ta, tt = comp["elements"][f"a{k}"], comp["elements"][f"t{k}"]
        assert tt["size"][0] > ta["size"][0] and tt["size"][1] == ta["size"][1], "the tip is wider than the arm"
    assert all(f["confidence"] == "estimated" and f["source"] for f in feats.values())


@pytest.mark.parametrize("width", [6, 10, 12])
def test_the_back_plate_runs_the_full_width_of_the_part(width):
    base = contract(f"apc/perf-vcm-base-{width}")
    w = {6: 152.0, 10: 253.0, 12: 304.0}[width]
    assert base["size"]["w"] == w and base["size"]["h"] == HEIGHT and base["size"]["d"] == 300
    floor = base["elements"]["floor"]
    assert floor["at"] == [0.0, 0.0] and floor["size"] == [w, HEIGHT]


# --- doors: one a working face, shipped fitted, and they come off -------------------------------------

@needs_dist
@pytest.mark.parametrize("name", list(PARTS))
def test_each_door_is_a_removable_part_and_the_drawing_without_it_shows_the_fingers(name):
    doc = device_yaml(name)
    cfgs = doc["configurations"]
    assert cfgs["base"]["default"] is True and cfgs["doors-off"]["kind"] == "example", \
        "a door that comes with the part is an illustration, never a device type"
    for face in faces(name):
        door = "door-front" if face == "front" else "door-rear"
        stem = "fingers-" if face == "front" else "rear-fingers-"
        on, off = by_id(svg(name, face)), by_id(svg(name, face, "doors-off"))
        assert door in on and on[door].get("data-behaviour") == "mounts", "fitted as it ships, with a pull handle"
        assert door not in off, "and the drawing without it"
        assert sum(1 for i in off if i.startswith(stem) and "--a" in i) == 2 * FINGERS, "the fingers are in it"
        assert any(i.startswith(stem) for i in on), "and under the door when it is on"


@pytest.mark.parametrize("width", [6, 10, 12])
def test_a_door_is_a_lid_with_a_rim_and_two_latches_and_no_hinge_is_invented(width):
    doc = contract(f"apc/perf-vcm-door-{width}")
    assert doc["behaviour"] == "mounts" and doc["lid"] is True
    feats = {f["node"]: f for f in doc["relief"]["features"]}
    assert set(feats) == set(doc["elements"]), "every drawn element is a feature, and the other way round"
    plate = feats["plate"]
    assert feats["rim-left"]["out"] > plate["out"] and feats["rim-right"]["out"] > plate["out"]
    assert feats["rim-left"]["lift"] == plate["lift"]
    knobs = [n for n in feats if n.startswith("latch-")]
    assert len(knobs) == 2 and all(feats[n]["out"] > feats["rim-left"]["out"] for n in knobs), "two latches stand proud"
    for n in ("rim-left", "rim-right", *knobs):
        assert feats[n]["color"] != plate["color"], f"{n} reads apart from the panel"
    assert all(f["confidence"] == "estimated" and f["source"] for f in feats.values())
    assert "hinge" not in json.dumps(doc["elements"]).lower()
    for i, a in enumerate(doc["relief"]["features"]):
        for b in doc["relief"]["features"][i + 1:]:
            if a["out"] != b["out"]:
                continue
            ra, rb = doc["elements"][a["node"]], doc["elements"][b["node"]]
            ox = min(ra["at"][0] + ra["size"][0], rb["at"][0] + rb["size"][0]) - max(ra["at"][0], rb["at"][0])
            oy = min(ra["at"][1] + ra["size"][1], rb["at"][1] + rb["size"][1]) - max(ra["at"][1], rb["at"][1])
            assert not (ox > 1e-6 and oy > 1e-6), f"{a['node']} and {b['node']} share a top plane where they overlap"


@pytest.mark.parametrize("name", list(PARTS))
def test_the_gaps_say_what_the_sources_do_not(name):
    gaps = {g["what"] for g in device_yaml(name)["gaps"]}
    assert {"door-hinge", "tie-off-points", "grounding-point", "cable-capacity", "finger-shape"} <= gaps
    doc = device_yaml(name)
    assert "hinge" not in json.dumps(doc["views"]).lower() and "hinge" not in json.dumps(doc["chassis"]).lower()
    assert "performance" not in doc["attrs"], "no APC document states a cable capacity for these parts"


# --- placed beside a 2- or 4-post rack ------------------------------------------------------------------

def _rack_ru(path):
    return yaml.safe_load((LIB / "racks/apc" / path / "rack.yaml").read_text())["ru"]


def _lab(height, devices):
    return {"format": 1, "kind": "lab", "name": "apc-verticals", "rack": {"height-ru": height},
            "devices": devices, "links": []}


def _codes(lab):
    found, _ = labs.check(lab, [LIB])
    return [c for c, sev, _ in found if sev == "error"], found


@pytest.mark.parametrize("rack_name,left,right", [("ar201", "left", "right"), ("ar203a", "left-front", "right-front")])
@pytest.mark.parametrize("name", list(PARTS))
def test_each_part_places_beside_the_rack_on_either_side(name, rack_name, left, right):
    lab = _lab(_rack_ru(rack_name), [{"id": "l", "ref": name, "side": left}, {"id": "r", "ref": name, "side": right}])
    assert labs.schema_errors(lab) == []
    errors, found = _codes(lab)
    assert errors == [], found
    _, placed = labs.check(lab, [LIB])
    got = {p["id"]: p for p in placed}
    assert (got["l"]["side"], got["l"]["mount"], got["l"]["ru"]) == (left, "rack-side", 1)
    assert got["r"]["side"] == right


@pytest.mark.parametrize("rack_name,side", [("ar201", "left"), ("ar203a", "left-front")])
@pytest.mark.parametrize("name", list(PARTS))
def test_two_on_one_side_of_one_rack_overlap_and_lint_says_so(name, rack_name, side):
    lab = _lab(_rack_ru(rack_name), [{"id": "a", "ref": name, "side": side}, {"id": "b", "ref": name, "side": side}])
    errors, found = _codes(lab)
    assert errors == ["L154"], found


def test_a_part_stacked_above_another_runs_off_the_top():
    lab = _lab(45, [{"id": "a", "ref": "ar8615", "side": "left", "ru": 1}, {"id": "b", "ref": "ar8615", "side": "left", "ru": 2}])
    assert _codes(lab)[0] == ["L154"]


# --- the DCIM device types: a part beside the rack takes no rack unit -------------------------------------

@pytest.mark.parametrize("name", list(PARTS))
def test_the_dcim_device_types_export_no_rack_unit_and_not_full_depth(name):
    model = device_yaml(name)["model"]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "APC" / f"{model}.yaml"
        assert path.is_file(), f"{path} is missing: run dcim_export.py --device {name}"
        out = yaml.safe_load(path.read_text())
        assert out["manufacturer"] == "APC" and out["model"] == model
        assert out["u_height"] == 0.0 and out["is_full_depth"] is False


# --- what the library holds for the rack kit ----------------------------------------------------------

@needs_dist
@pytest.mark.parametrize("name", list(PARTS))
def test_the_rack_catalogue_carries_each_part_as_a_rack_side_part_of_44_units(name):
    r = rack(name)
    assert r["mount"] == "rack-side" and r["ru"] == 44 and close(r["w"], PARTS[name][2], 0.01)
    assert r.get("capacity") in (None, {}), "no capacity is stated, so none is shown"

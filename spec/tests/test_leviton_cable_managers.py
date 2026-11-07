"""Leviton's horizontal cable managers (roc-ops/Portrayal#1100, part of #1091): the five 49253
five-ring managers and their two covers, and the three VERSI-DUCT slotted ducts.

Every figure below is what Leviton's own dimensional drawing (DXF) or specification sheet states,
in inches as printed and converted here, so a model that drifts from its drawing fails by name.
The rack kit's half of the features (a cable laid through a ring, along a duct, through a pass)
is `spec/tests/js/rack-leviton-managers.mjs`, run by `test_rack_kit_js.py`.

These read the build (`library/dist`, `library/exports`) and skip without it, like the other
sweeps over compiled drawings.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
EXPORTS = LIB / "exports"
MM = 25.4

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# name -> (height in, depth in, ru, ear plane in, ring depth in, ring height in, opening w x h in, cover)
# 49253: 49253-xxx specification sheet page 2 and each drawing's own dimensions (19.00 in wide,
# 1.72 / 3.47 in high, 4.50 / 2.50 / 6.50 in deep, rings 4.0 / 2.0 / 6.0 in); the opening is the
# drawing's clear 1.25 / 2.75 in between the bars and 3.25 / 1.25 / 5.25 in between the legs
MANAGERS = {
    "49253-lpm": (1.72, 4.50, 1, 4.06, 4.0, 1.5, (1.25, 3.25), "49253-1cv"),
    "49253-bcm": (3.47, 4.50, 2, 4.06, 4.0, 3.0, (2.75, 3.25), "49253-2cv"),
    "49253-2cm": (3.47, 2.50, 2, 2.06, 2.0, 3.0, (2.75, 1.25), "49253-2cv"),
    "49253-6pm": (1.72, 6.50, 1, 6.06, 6.0, 1.5, (1.25, 5.25), "49253-1cv"),
    "49253-6mr": (3.47, 6.50, 2, 6.06, 6.0, 3.0, (2.75, 5.25), "49253-2cv"),
}
# the ring's band across the run, 3/8 in, and the five centred 4.236 in apart on the plate
RING_BAND = 9.5
RING_PITCH = 107.6
BODY_W = 444.5      # 17.50 in, the plate between its folds

# name -> (height in, depth in, ru, ear plane in, front clear in, rear clear in or None)
DUCTS = {
    "491ru-hfr": (1.8865, 10.038, 1, 3.306, (1.125, 2.75), (1.125, 3.75)),
    "492ru-hfr": (3.475, 10.025, 2, 3.3247, (2.75, 3.00), (1.625, 3.75)),
    "492ru-hfo": (3.475, 3.325, 2, 3.325, (2.75, 3.00), None),
}
SLOT_PITCH = 49.375
SLOT_GAP = 22.45
SLOTS = 9
OVAL = (75.88, 38.1)
COVERS = ("49253-1cv", "49253-2cv")
ALL = list(MANAGERS) + list(DUCTS)


def svg(name, view, config="base"):
    p = DIST / f"{name}.{config}.{view}.svg"
    return ET.parse(p).getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def device_yaml(name):
    vendor_dir = LIB / "devices" / "leviton" / name / "device.yaml"
    return yaml.safe_load(vendor_dir.read_text())


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


# --- the maker ---------------------------------------------------------------------------------

def test_leviton_is_a_hardware_vendor_listed_directly_after_apc():
    text = (ROOT / "spec/schemas/vendors.yaml").read_text()
    keys = [l.strip().rstrip(":") for l in text.splitlines() if l.startswith("  ") and not l.startswith("   ") and l.rstrip().endswith(":")]
    assert keys.index("leviton") == keys.index("apc") + 1 and keys[keys.index("leviton") + 1] == "fs"
    vendors = yaml.safe_load(text)["vendors"]
    assert vendors["leviton"]["role"] == "hardware" and vendors["leviton"]["display"] == "Leviton"
    assert "specification" in vendors["leviton"]["source"]


# --- each device's envelope against its drawing -------------------------------------------------

@pytest.mark.parametrize("name", list(MANAGERS))
def test_a_five_ring_manager_is_the_size_its_drawing_dimensions(name):
    h, d, ru, ear, ring_d, ring_h, _ap, _cover = MANAGERS[name]
    c = device_yaml(name)["chassis"]
    assert close(c["width"], BODY_W) and close(c["height"], h * MM, 0.1) and close(c["depth"], d * MM, 0.1)
    assert c["ru"] == ru and c["full-depth"] is False and c["shell"] == "sheet"
    # the ears bolt to the back face of the plate: the rings' depth plus the 1.5 mm sheet
    at = c["ears"]["positions"][0]
    assert at["default"] and close(at["at"], ring_d * MM + 1.5, 0.1)
    r = rack(name)
    assert (r["w"], r["ru"]) == (c["width"], ru) and r["ears"]["default"]["at"] == at["at"]


@pytest.mark.parametrize("name", list(DUCTS))
def test_a_versi_duct_is_the_size_its_drawing_dimensions(name):
    h, d, ru, ear, _front, _rear = DUCTS[name]
    c = device_yaml(name)["chassis"]
    assert close(c["width"], BODY_W) and close(c["height"], h * MM) and close(c["depth"], d * MM)
    assert c["ru"] == ru and c["full-depth"] is False
    assert close(c["ears"]["positions"][0]["at"], ear * MM)


# --- the 49253 rings: five a manager, from the drawing ----------------------------------------

@needs_dist
@pytest.mark.parametrize("name", list(MANAGERS))
def test_each_five_ring_manager_publishes_five_ring_guides(name):
    ring_d = MANAGERS[name][4]
    ap_w, ap_h = MANAGERS[name][6]
    root = svg(name, "front")
    rings = sorted((e for e in root.iter() if e.get("data-guide") == "ring"), key=lambda e: e.get("id"))
    assert [e.get("id") for e in rings] == [f"guide-{k}" for k in range(1, 6)]
    xs = []
    for e in rings:
        assert e.get("data-guide-run") == "x"
        assert [round(float(v) / MM, 2) for v in e.get("data-guide-aperture").split()] == [ap_w, ap_h], \
            "the opening is the drawing's clear size between the bars and between the legs"
        assert float(e.get("data-guide-depth")) == RING_BAND
        tx = float(e.get("transform").split("(")[1].split(",")[0])
        xs.append(tx + RING_BAND / 2)
    assert [round(b - a, 1) for a, b in zip(xs, xs[1:])] == [RING_PITCH] * 4
    assert close(xs[2], BODY_W / 2, 0.01), "the middle ring is on the centre line"
    # the rack kit reads each ring's place in depth off the plan: the middle of the loop
    for via in ("guide-1", "guide-5"):
        z = rack(name)["rings"][via]
        assert close(z["z"], ring_d * MM / 2) and z["depth"] == RING_BAND


@needs_dist
@pytest.mark.parametrize("name", list(MANAGERS))
def test_the_ring_is_an_open_loop_with_a_slit_not_a_closed_one(name):
    """The loop's inner leg hangs 3.5 in (or 12.7 mm behind the front on the other rings) and the
    outer leg rises at the front, with 9.5 mm between them over 12.7 mm of height: a cord is laid
    in through that slit. Both legs are in the compiled drawing's relief."""
    root = by_id(svg(name, "front"))
    inner, outer = root["guide-1--leg-inner"], root["guide-1--leg-outer"]
    top = root["guide-1--bar-top"]
    ring_d = MANAGERS[name][4] * MM
    # the outer leg stands at the front tips, the inner leg 12.7 mm behind them
    assert float(outer.get("data-z-out")) == 0
    assert close(float(inner.get("data-z-out")), -12.7, 0.01)
    # a leg is 3.175 mm [1/8 in] thick: back to front over the same span as the top bar's end
    assert close(float(top.get("data-z-out")), -12.7, 0.01)
    assert close(float(inner.get("data-z-lift")), ring_d - 15.875, 0.01)
    # 9.5 mm clear between the two in the plane of the loop, over 12.7 mm where they overlap
    oy, iy = float(outer.get("y")), float(inner.get("y")) + float(inner.get("height"))
    assert close(iy - oy, 12.7, 0.01)


# --- the covers: separate parts a manager can take, and that come off ------------------------

@needs_dist
@pytest.mark.parametrize("name", list(MANAGERS))
def test_the_49253_cover_is_sold_separately_so_the_manager_ships_without_it(name):
    cfgs = device_yaml(name)["configurations"]
    assert cfgs["base"]["default"] is True and cfgs["with-cover"]["kind"] == "example", \
        "the cover is a second purchase: an illustration, never a device type"
    assert "cover" not in by_id(svg(name, "front")), "as shipped, no cover is on it"
    assert "cover" in by_id(svg(name, "front", "with-cover"))


@needs_dist
@pytest.mark.parametrize("name", list(MANAGERS))
def test_the_49253_cover_seats_on_the_outer_rings_and_comes_off(name):
    h = MANAGERS[name][0] * MM
    ring_d = MANAGERS[name][4] * MM
    cover_ref = MANAGERS[name][7]
    root = svg(name, "front", "with-cover")
    el = by_id(root)
    cover = el["cover"]
    assert cover.get("data-ref", "").startswith(f"leviton/{cover_ref}@1"), "1RU managers take the 1CV, 2RU the 2CV"
    assert cover.get("data-behaviour") == "mounts", "a cover with a pull handle in the explorer"
    plate = el["cover--plate"]
    # the drawing's front view: a plate 438.76 mm wide and, at each end, the fold's strip 1.98 mm
    # outside its edge, 442.7 mm over both
    lip_l, lip_r = el["cover--lip-left"], el["cover--lip-right"]
    assert close(float(plate.get("width")), 438.74, 0.01) and close(float(plate.get("height")), h, 0.1)
    assert close(float(lip_l.get("width")), 1.98, 0.01) and close(float(lip_r.get("width")), 1.98, 0.01)
    assert close(float(lip_l.get("x")) + float(plate.get("width")) + float(lip_l.get("width")) * 2, 442.7, 0.01)
    assert close(float(plate.get("x")), float(lip_l.get("x")) + float(lip_l.get("width")), 0.01)
    assert close(float(lip_r.get("x")), float(plate.get("x")) + float(plate.get("width")), 0.01)
    # the strips and the plate stand in the same plane: one sheet wrapping round, not two
    assert close(float(lip_l.get("data-z-out")), float(plate.get("data-z-out")), 0.01)
    # its plate is flush with the ring tips to within the 0.1 mm a placement adds so the legs
    # do not share its plane, so it stays inside the manager's own depth
    assert close(float(plate.get("data-z-out")), float(el["guide-1--leg-outer"].get("data-z-out")), 0.15)
    # each end's pocket is 3.81 mm between plate and tab, over a ring leg 3.175 mm thick
    pocket = abs(float(el["cover--hook-left"].get("data-z-out"))) - 1.22
    assert pocket > 3.175 and close(pocket, 3.81, 0.01)
    # and its pockets span the two outer rings' bands (the 1.4 mm margin the drawing leaves)
    cx = float(cover.get("transform").split("(")[1].split(",")[0])
    for ring, hook in (("guide-1", "cover--hook-left"), ("guide-5", "cover--hook-right")):
        rx = float(el[ring].get("transform").split("(")[1].split(",")[0])
        hx, hw = cx + float(el[hook].get("x")), float(el[hook].get("width"))
        assert hx <= rx and rx + RING_BAND <= hx + hw
    # the rings and the slit are still there with the cover on: the cover only hides them
    assert all(f"guide-{k}" in el for k in range(1, 6))
    # the cover is its own contract, listing nothing that is a hinge
    contract = yaml.safe_load((LIB / "components/leviton" / cover_ref / "v1/contract.yaml").read_text())
    assert contract["behaviour"] == "mounts" and "hinge" not in json.dumps(contract.get("elements", {})).lower()
    assert ring_d > 0


@needs_dist
@pytest.mark.parametrize("name", list(MANAGERS))
def test_the_side_and_top_drawings_with_the_cover_on_draw_it_and_without_it_do_not(name):
    for view in ("top", "bottom", "left", "right"):
        on = by_id(svg(name, view, "with-cover"))
        off = by_id(svg(name, view))
        assert any(i.startswith("cover") or "cover" in (e.get("data-kind") or "") for i, e in on.items()), view
        assert not any("cover" in (e.get("data-kind") or "") for e in off.values()), view


# --- VERSI-DUCT: channels, fingers, passes, covers that ship fitted -----------------------------

@needs_dist
@pytest.mark.parametrize("name", list(DUCTS))
def test_each_versi_duct_publishes_its_duct_or_ducts_with_the_drawn_pitch_and_gap(name):
    front, rear = DUCTS[name][4], DUCTS[name][5]
    wanted = {"front": "front-duct" if rear else "duct"}
    if rear:
        wanted["rear"] = "rear-duct"
    for view, gid in wanted.items():
        el = by_id(svg(name, view))[f"guide--{gid}"]
        assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "x"
        assert float(el.get("data-guide-finger-pitch")) == SLOT_PITCH and float(el.get("data-guide-finger-gap")) == SLOT_GAP
        clear_h = (front if view == "front" else rear)[0] * MM
        assert close(float(el.get("height")), clear_h, 0.03), "the application note's usable height"
        assert float(el.get("width")) == BODY_W
    assert {k: v for k, v in rack(name)["guides"].items()} == {k: [v] for k, v in wanted.items()}


@needs_dist
@pytest.mark.parametrize("name", list(DUCTS))
def test_the_slots_are_nine_a_wall_on_the_drawn_pitch(name):
    top = by_id(svg(name, "top"))
    for prefix in (("front-slot", "rear-slot") if DUCTS[name][5] else ("slot",)):
        slots = sorted((e for i, e in top.items() if i.startswith(prefix + "-")), key=lambda e: float(e.get("x")))
        assert len(slots) == SLOTS, prefix
        assert [round(float(b.get("x")) - float(a.get("x")), 3) for a, b in zip(slots, slots[1:])] == [SLOT_PITCH] * (SLOTS - 1)
        assert all(float(s.get("width")) == SLOT_GAP for s in slots)


@needs_dist
@pytest.mark.parametrize("name", list(DUCTS))
def test_each_wall_is_ten_fingers_end_on_with_a_slot_between_each_pair(name):
    for view in ("front", "rear"):
        if view == "rear" and not DUCTS[name][5]:
            continue
        el = by_id(svg(name, view))
        walls = [i for i in el if i.endswith("fingers-upper") or i.endswith("fingers-lower")]
        assert len(walls) == 2, view
        for wall in walls:
            fingers = [i for i in el if i.startswith(wall + "--f")]
            assert len(fingers) == 10, wall


@needs_dist
@pytest.mark.parametrize("name", [n for n in DUCTS if DUCTS[n][5]])
def test_a_front_and_rear_duct_draws_four_oval_pass_throughs_top_and_bottom(name):
    for view in ("top", "bottom"):
        el = by_id(svg(name, view))
        passes = [e for e in el.values() if e.get("data-class") == "pass"]
        assert len(passes) == 4, view
        assert {e.get("data-pass-shape") for e in passes} == {"obround"} and {e.get("data-pass-cover") for e in passes} == {"open"}
    assert rack(name)["passes"]["top"] == [f"top-pass-{k}" for k in range(1, 5)]
    # 75.88 x 38.1 mm, the drawing's 2.99 x 1.50 in
    d = device_yaml(name)["views"]["top"]["passes"][0]
    assert close(d["size"][0], OVAL[0], 0.01) and close(d["size"][1], OVAL[1], 0.06)


def test_the_front_only_duct_draws_no_pass_through_because_its_drawing_has_none():
    assert "passes" not in json.dumps(device_yaml("492ru-hfo")["views"])


@needs_dist
@pytest.mark.parametrize("name", list(DUCTS))
def test_the_duct_covers_ship_fitted_and_come_off(name):
    covers = ["front-cover", "rear-cover"] if DUCTS[name][5] else ["cover"]
    cfgs = device_yaml(name)["configurations"]
    assert cfgs["base"]["default"] is True and cfgs["cover-off"]["kind"] == "example"
    for view, cid in zip(("front", "rear"), covers):
        on = by_id(svg(name, view))
        off = by_id(svg(name, view, "cover-off"))
        assert cid in on and on[cid].get("data-behaviour") == "mounts", "fitted as it ships, with a pull handle"
        assert cid not in off, "and the drawing without it"
        # the fingers are there in both: taking the cover off shows them
        assert any(i.endswith("fingers-upper") for i in off) and any(i.endswith("fingers-lower") for i in off)
    for view in ("top", "left"):
        assert any("cover" in (e.get("data-kind") or "") for e in by_id(svg(name, view)).values())
        assert not any("cover" in (e.get("data-kind") or "") for e in by_id(svg(name, view, "cover-off")).values())


@pytest.mark.parametrize("name", list(DUCTS))
def test_no_mechanism_is_invented_for_the_duct_cover_hinge(name):
    doc = device_yaml(name)
    assert any(g["what"] == "cover-hinge" for g in doc["gaps"]), \
        "the hinge is a separate accessory (49265-HNG) and the format has none"
    assert "hinge" not in json.dumps(doc["views"]).lower() and "hinge" not in json.dumps(doc["chassis"]).lower()


# --- capacity: only what the application note states, and its basis -------------------------------

CAPACITY = {"49253-lpm": 26, "49253-bcm": 59, "49253-2cm": 31, "49253-6pm": 43, "49253-6mr": 95,
            "491ru-hfr": 20, "492ru-hfr": 54, "492ru-hfo": 54}


@pytest.mark.parametrize("name", list(CAPACITY))
def test_cable_capacity_is_the_application_notes_figure_with_its_basis_and_no_kind(name):
    perf = device_yaml(name)["attrs"]["performance"]
    assert perf["cable-capacity"] == CAPACITY[name]
    assert "NS-AN-23-006-05-30-23" in perf["cable-capacity-basis"] and "30 percent" in perf["cable-capacity-basis"]
    # the note names a cord by Leviton part number (6AS10), never by category: no kind is stated
    assert "cable-capacity-media" not in perf and "cable-capacity-estimated" not in perf


@needs_dist
@pytest.mark.parametrize("name", list(CAPACITY))
def test_the_rack_catalogue_carries_the_count_to_be_shown_and_never_compared(name):
    cap = rack(name)["capacity"]
    assert cap["count"] == CAPACITY[name] and cap["media"] is None and "estimated" not in cap


# --- the DCIM device types: manager parts that occupy their unit but not the depth --------------

@pytest.mark.parametrize("name", ALL)
def test_the_dcim_device_types_say_the_rack_units_and_not_full_depth(name):
    model = device_yaml(name)["model"]
    ru = device_yaml(name)["chassis"]["ru"]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Leviton" / f"{model}.yaml"
        assert path.is_file(), f"{path} is missing: run dcim_export.py --device {name}"
        doc = yaml.safe_load(path.read_text())
        assert doc["manufacturer"] == "Leviton" and doc["model"] == model
        assert doc["u_height"] == float(ru) and doc["is_full_depth"] is False

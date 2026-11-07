"""Panduit's cable managers (roc-ops/Portrayal#1092, part of #1091): the NetManager High Capacity
horizontals NM1, NM2 and NMF1 to NMF4, the NetManager NCMH2 and its front-only NCMHF2, the
PatchRunner 2 horizontals PR2HF3WH and PR2HF4WH, the PatchRunner 2 verticals PR2VSD06, PR2VD08 and
PR2VD10, and the NetRunner vertical WMPVHC45E.

Every figure below is what Panduit's own customer drawing, specification sheet, bulletin or
calculator prints, in the units it prints them and converted here, so a model that drifts from its
source fails by name. What the drawings do not dimension (finger counts and pitches read off a
picture, the ring's loop, the holes' places) is estimated in the device and is held here only to
what the model itself declares. The rack kit's half of the features (a cable laid through a ring,
along a duct, through a pass-through) is `spec/tests/js/rack-panduit-managers.mjs`, run by
`test_rack_kit_js.py`.

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

BODY_W = 444.83   # 17.51 in, the NCMH2 and NCMHF2 drawings' body between the ears

# name -> (model, ru, height mm, depth mm, ear plane mm from the front, width mm)
# NetManager High Capacity: RKSP237 table and the 10404-xx drawings (1.7 / 3.5 / 5.2 / 7.0 in high, 6.2 in
# deep front only and 13.1 in front and rear, the front channel "5.5 REF [140]")
# NCMH2 / NCMHF2: drawings 00787-07 and 00787-10 (88.14 high, 247.71 and 95.10 deep, front "3.24 REF")
# PR2HF: the table of 00224EAE-DC (132.6 / 177.0 high, 483.9 wide, 201.7 deep, 181.4 mounting depth)
HORIZONTALS = {
    "nmf1": ("NMF1", 1, 44.0, 157.0, 139.7, BODY_W),
    "nmf2": ("NMF2", 2, 88.0, 157.0, 139.7, BODY_W),
    "nmf3": ("NMF3", 3, 133.0, 157.0, 139.7, BODY_W),
    "nmf4": ("NMF4", 4, 177.0, 157.0, 139.7, BODY_W),
    "nm1": ("NM1", 1, 44.0, 332.0, 139.7, BODY_W),
    "nm2": ("NM2", 2, 88.0, 332.0, 139.7, BODY_W),
    "ncmh2": ("NCMH2", 2, 88.14, 247.71, 82.27, BODY_W),
    "ncmhf2": ("NCMHF2", 2, 88.14, 95.1, 82.27, BODY_W),
    "pr2hf3wh": ("PR2HF3WH", 3, 132.6, 201.7, 181.4, 483.9),
    "pr2hf4wh": ("PR2HF4WH", 4, 177.0, 201.7, 181.4, 483.9),
}
# name -> (model, width mm, height mm, depth mm): the PR2VD / PR2VSD tables (A, B, C) and the
# WMPVHC45E drawing (6.7 x 83.0 x 14.1 in)
VERTICALS = {
    "pr2vsd06": ("PR2VSD06", 152.4, 2130.4, 526.4),
    "pr2vd08": ("PR2VD08", 203.2, 2130.4, 526.4),
    "pr2vd10": ("PR2VD10", 254.0, 2130.4, 526.4),
    "wmpvhc45e": ("WMPVHC45E", 170.0, 2108.0, 357.0),
}
ALL = list(HORIZONTALS) + list(VERTICALS)

# name -> (front duct id, rear duct id or None, finger pitch, finger gap, clear height or width: front, rear)
DUCTS = {
    "nmf1": ("duct", None, 34.925, 5.4, 24.0, None), "nmf2": ("duct", None, 34.925, 5.4, 68.0, None),
    "nmf3": ("duct", None, 34.925, 5.4, 113.0, None), "nmf4": ("duct", None, 34.925, 5.4, 157.0, None),
    "nm1": ("duct", None, 34.925, 5.4, 24.0, None), "nm2": ("duct", None, 34.925, 5.4, 68.0, None),
    # RKSP225: "finger spacing 3/8 in" is the 9.5 gap; its 34.925 pitch is the finger + spacing
    "ncmh2": ("duct", "rear-duct", 34.925, 9.5, 60.0, 60.0), "ncmhf2": ("duct", None, 34.925, 9.5, 60.0, None),
    "pr2hf3wh": ("duct", None, 72.8, 57.8, 102.6, None), "pr2hf4wh": ("duct", None, 72.8, 57.8, 147.0, None),
    # the width less what the calculator's front (9.3 sq in an inch of width) and rear (6.23) areas leave
    "pr2vsd06": ("duct", "rear-duct", 44.45, 11.45, 123.2, 111.2),
    "pr2vd08": ("duct", "rear-duct", 44.45, 11.45, 174.0, 162.0),
    "pr2vd10": ("duct", "rear-duct", 44.45, 11.45, 224.8, 212.8),
    # Detail A of 10225-25: a finger on the rack unit with 1.00 in [25.4] between two
    "wmpvhc45e": ("duct", "rear-duct", 44.45, 25.4, 132.0, 132.0),
}
# the fingers of each face: (placement stem, element prefix, fingers per placement, placements) per face
FINGERS = {
    "nmf1": {"front": ("fingers-", "b", 12, 2)}, "nmf2": {"front": ("fingers-", "b", 12, 2)},
    "nmf3": {"front": ("fingers-", "b", 12, 2)}, "nmf4": {"front": ("fingers-", "b", 12, 2)},
    "nm1": {"front": ("fingers-", "b", 12, 2)}, "nm2": {"front": ("fingers-", "b", 12, 2)},
    "ncmh2": {"front": ("fingers-", "f", 12, 2), "rear": ("rear-fingers-", "f", 12, 2)},
    "ncmhf2": {"front": ("fingers-", "f", 12, 2)},
    "pr2hf3wh": {"front": ("fingers-", "f", 7, 2)}, "pr2hf4wh": {"front": ("fingers-", "f", 7, 2)},
    "pr2vsd06": {"front": ("fingers-", "f", 15, 6), "rear": ("rear-fingers-", "f", 15, 6)},
    "pr2vd08": {"front": ("fingers-", "f", 15, 6), "rear": ("rear-fingers-", "f", 15, 6)},
    "pr2vd10": {"front": ("fingers-", "f", 15, 6), "rear": ("rear-fingers-", "f", 15, 6)},
    "wmpvhc45e": {"front": ("fingers-", "f", 15, 6), "rear": ("rear-fingers-", "f", 15, 6)},
}
# the covers (or doors) that ship fitted, by face, and the configuration that takes them off
COVERS = {
    "nmf1": ({"front": ["cover"]}, "cover-off"), "nmf2": ({"front": ["cover"]}, "cover-off"),
    "nmf3": ({"front": ["cover"]}, "cover-off"), "nmf4": ({"front": ["cover"]}, "cover-off"),
    "nm1": ({"front": ["cover"], "rear": ["rear-cover"]}, "cover-off"),
    "nm2": ({"front": ["cover"], "rear": ["rear-cover"]}, "cover-off"),
    "ncmh2": ({"front": ["cover"], "rear": ["rear-cover"]}, "cover-off"), "ncmhf2": ({"front": ["cover"]}, "cover-off"),
    "pr2hf3wh": ({"front": ["cover"]}, "cover-off"), "pr2hf4wh": ({"front": ["cover"]}, "cover-off"),
    "pr2vsd06": ({"front": ["door-front"]}, "door-off"),
    "pr2vd08": ({"front": ["door-front"], "rear": ["door-rear"]}, "doors-off"),
    "pr2vd10": ({"front": ["door-front"], "rear": ["door-rear"]}, "doors-off"),
    "wmpvhc45e": ({"front": ["cover-front-1", "cover-front-2"], "rear": ["cover-rear-1", "cover-rear-2"]}, "covers-off"),
}
# name -> (window or hole count, size mm of the first, shape): the pass-throughs the drawings show
PASSES = {
    "nmf1": (2, (98.5, 17.0)), "nmf2": (2, (98.5, 40.0)), "nmf3": (2, (98.5, 85.0)), "nmf4": (2, (98.5, 129.0)),
    "nm1": (2, (98.5, 17.0)), "nm2": (2, (98.5, 40.0)), "ncmh2": (2, (98.5, 38.0)), "ncmhf2": (2, (98.5, 38.0)),
    "pr2hf3wh": (2, (118.0, 102.6)), "pr2hf4wh": (2, (118.0, 147.0)),
    # 3.0 in [76.2 mm] "CABLE PASS THROUGH", four a 7 ft manager (PR2VD** sheet 2)
    "pr2vsd06": (4, (76.2, 76.2)), "pr2vd08": (4, (76.2, 76.2)), "pr2vd10": (4, (76.2, 76.2)),
    # 8X 2.20 [55.9] wide, 4X 5.20 [132.1] and 4X 2.70 [68.6] long (10225-25)
    "wmpvhc45e": (8, (55.9, 68.6)),
}
# the stated cable capacity (30 per cent recommended fill) front, rear, the kind it is stated for
CAPACITY = {
    "nmf1": (22, None, "cat6"), "nmf2": (67, None, "cat6"), "nmf3": (119, None, "cat6"), "nmf4": (168, None, "cat6"),
    "nm1": (22, 28, "cat6"), "nm2": (67, 76, "cat6"),
    "pr2hf3wh": (159, None, "cat6"), "pr2hf4wh": (232, None, "cat6"),
    "pr2vd08": (440, 274, "cat6"), "pr2vd10": (569, 361, "cat6"),
    # Panduit's calculator, entered cable 0.185 in: no kind is stated
    "ncmh2": (66, 89, None), "ncmhf2": (66, None, None), "wmpvhc45e": (342, 342, None),
}
WEIGHTS_KG = {"nmf1": 0.513, "nmf2": 0.73, "nmf3": 0.998, "nmf4": 1.179, "nm1": 0.816, "nm2": 1.134,
              "ncmh2": 1.2837, "ncmhf2": 0.381, "pr2hf3wh": 1.0, "pr2hf4wh": 1.2,
              "pr2vsd06": 18.68, "pr2vd08": 24.76, "pr2vd10": 27.74, "wmpvhc45e": 10.43}


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "panduit" / name / "device.yaml").read_text())


def svg(name, view, config="base"):
    return ET.parse(DIST / f"{name}.{config}.{view}.svg").getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


# --- the maker -----------------------------------------------------------------------------------

def test_panduit_is_a_hardware_vendor_listed_directly_before_accton():
    text = (ROOT / "spec/schemas/vendors.yaml").read_text()
    keys = [l.strip().rstrip(":") for l in text.splitlines() if l.startswith("  ") and not l.startswith("   ") and l.rstrip().endswith(":")]
    assert keys.index("panduit") + 1 == keys.index("accton")
    vendors = yaml.safe_load(text)["vendors"]
    assert vendors["panduit"]["role"] == "hardware" and vendors["panduit"]["display"] == "Panduit"
    assert "specification sheets" in vendors["panduit"]["source"] and "panduit.com" in vendors["panduit"]["source"]


# --- each device's envelope against its source ----------------------------------------------------

@pytest.mark.parametrize("name", list(HORIZONTALS))
def test_a_horizontal_manager_is_the_size_its_source_prints(name):
    model, ru, h, d, ear, w = HORIZONTALS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "Panduit" and doc["model"] == model
    assert close(c["width"], w) and close(c["height"], h) and close(c["depth"], d)
    assert c["ru"] == ru and c["full-depth"] is False and c["shell"] == "sheet"
    assert "mount" not in c, "a manager that fills its rack units is a `rack` part: its ears are in its own face"
    at = c["ears"]["positions"][0]
    assert at["default"] and close(at["at"], ear, 0.01)
    assert close(c["weight-kg"], WEIGHTS_KG[name], 0.0005)


@pytest.mark.parametrize("name", list(VERTICALS))
def test_a_vertical_manager_is_the_size_its_source_prints(name):
    model, w, h, d = VERTICALS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "Panduit" and doc["model"] == model
    assert close(c["width"], w) and close(c["height"], h) and close(c["depth"], d)
    assert c["mount"] == "rack-side" and c["ru"] == 45 and c["shell"] == "sheet"
    assert h > w, "a vertical manager is drawn as it stands, portrait"
    assert close(c["weight-kg"], WEIGHTS_KG[name], 0.0005)


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_rack_catalogue_carries_each_part_with_its_units_and_ears(name):
    r = rack(name)
    doc = device_yaml(name)["chassis"]
    assert r["ru"] == doc["ru"] and close(r["w"], doc["width"], 0.01)
    if name in HORIZONTALS:
        assert r["ears"]["default"]["at"] == doc["ears"]["positions"][0]["at"]


# --- the rings: five open D-rings on the rear of a front-and-rear NetManager High Capacity -----------

RINGED = {"nm1": (24.0, 110.0), "nm2": (68.0, 105.0)}   # the opening: clear height and depth, from the calculator's rear area
RING_PITCH = 107.0
RING_BAND = 15.0


@needs_dist
@pytest.mark.parametrize("name", list(RINGED))
def test_each_netmanager_rear_publishes_five_ring_guides(name):
    ap_w, ap_h = RINGED[name]
    root = svg(name, "rear")
    rings = sorted((e for e in root.iter() if e.get("data-guide") == "ring"), key=lambda e: e.get("id"))
    assert [e.get("id") for e in rings] == [f"guide-{k}" for k in range(1, 6)]
    xs = []
    for e in rings:
        assert e.get("data-guide-run") == "x"
        assert [float(v) for v in e.get("data-guide-aperture").split()] == [ap_w, ap_h]
        assert float(e.get("data-guide-depth")) == RING_BAND
        tx = float(e.get("transform").split("(")[1].split(",")[0])
        xs.append(tx + RING_BAND / 2)
    assert [round(b - a, 1) for a, b in zip(xs, xs[1:])] == [RING_PITCH] * 4
    assert close(xs[2], BODY_W / 2, 0.02), "the middle ring is on the centre line"
    assert rack(name)["guides"]["rear"] == [f"guide-{k}" for k in range(1, 6)]
    # the rack kit reads each ring's place in depth off the plan: the middle of the 175 mm post, 244.5 behind the front of the 332
    for via in ("guide-1", "guide-5"):
        z = rack(name)["rings"][via]
        assert close(z["z"], 244.5, 0.1) and z["depth"] == RING_BAND


@needs_dist
@pytest.mark.parametrize("name", list(RINGED))
def test_the_ring_is_an_open_loop_whose_far_end_is_a_hook_not_a_closed_one(name):
    el = by_id(svg(name, "rear"))
    bar_top, hook, back = el["guide-1--bar-top"], el["guide-1--hook"], el["guide-1--back"]
    # in the rear well (175 deep) the bars and the hook reach the open rear face; the back leg is on the plate
    assert float(bar_top.get("data-z-out")) == 0 and float(hook.get("data-z-out")) == 0
    assert float(back.get("data-z-out")) == -172 and float(hook.get("data-z-lift")) == 172
    ring_h = float(el["guide-1--back"].get("height"))
    # the hook is the lower third of the ring: the upper two thirds are open, the slit a cable is laid in through
    assert float(hook.get("height")) < ring_h / 2 + 1 and float(hook.get("y")) > ring_h / 2


# --- the ducts: a finger channel with the drawn pitch and gap, front and rear where there is one ---------

@needs_dist
@pytest.mark.parametrize("name", list(DUCTS))
def test_each_part_publishes_its_duct_or_ducts_with_the_drawn_pitch_and_gap(name):
    front, rear, pitch, gap, clear_front, clear_rear = DUCTS[name]
    wanted = {"front": front}
    if rear:
        wanted["rear"] = rear
    for view, gid in wanted.items():
        el = by_id(svg(name, view))[f"guide--{gid}"]
        assert el.get("data-guide") == "duct"
        assert el.get("data-guide-run") == ("y" if name in VERTICALS else "x")
        assert float(el.get("data-guide-finger-pitch")) == pitch and float(el.get("data-guide-finger-gap")) == gap
        extent = float(el.get("height" if name in HORIZONTALS else "width"))
        assert close(extent, clear_front if view == "front" else clear_rear, 0.03), "the channel's clear height (or width)"
    published = rack(name)["guides"]
    assert {k: v for k, v in published.items() if k in wanted} == {k: [v] for k, v in wanted.items()} or all(
        v in published[k] for k, v in wanted.items())


@needs_dist
@pytest.mark.parametrize("name", list(FINGERS))
def test_each_face_has_the_fingers_its_drawing_counts(name):
    for face, (stem, prefix, per, placements) in FINGERS[name].items():
        el = by_id(svg(name, face))
        fingers = [i for i in el if i.startswith(stem) and f"--{prefix}" in i and i.split("--")[1][len(prefix):].isdigit()]
        assert len(fingers) == per * placements, (name, face)


@needs_dist
@pytest.mark.parametrize("name", ["pr2vsd06", "pr2vd08", "pr2vd10", "wmpvhc45e"])
def test_a_vertical_face_has_one_finger_to_each_of_the_45_rack_units(name):
    for face in ("front", "rear"):
        el = by_id(svg(name, face))
        stem = "fingers-" if face == "front" else "rear-fingers-"
        left = {i.split("--")[0] for i in el if i.startswith(stem + "left") and "--f" in i}
        right = {i.split("--")[0] for i in el if i.startswith(stem + "right") and "--f" in i}
        # three sections of 15 on each side: the maker's 15-finger kit, 45 fingers a side
        assert len(left) == len(right) == 3
        assert sum(1 for i in el if i.split("--")[0] in left and "--f" in i) == 45
        assert sum(1 for i in el if i.split("--")[0] in right and "--f" in i) == 45


# --- pass-throughs: the windows and holes the drawings show --------------------------------------------

@needs_dist
@pytest.mark.parametrize("name", list(PASSES))
def test_a_pass_through_is_drawn_open_where_the_drawing_shows_one(name):
    count, (w0, h0) = PASSES[name]
    el = svg(name, "front")
    passes = [e for e in el.iter() if e.get("data-class") == "pass"]
    assert len(passes) == count
    assert {e.get("data-pass-cover") for e in passes} == {"open"}
    first = device_yaml(name)["views"]["front"]["passes"][0]
    assert close(first["size"][0], w0, 0.01) and close(first["size"][1], h0, 0.01)
    ids = [f"pass-through-{k}" for k in range(1, count + 1)]
    assert rack(name)["passes"]["front"] == ids


@needs_dist
@pytest.mark.parametrize("name", list(PASSES))
def test_the_pass_through_is_a_hole_in_the_floor_of_the_well_not_covered_paint(name):
    """The base is painted as a path with the windows cut out of it (even-odd), so a cable laid in
    the channel can go through them: nothing is drawn over a window but the cover, a lid."""
    base = device_yaml(name)["views"]["front"]["components"]["placements"][0]["ref"]
    skin = (LIB / "components" / base.split("@")[0] / "v1" / "skins" / "default.svg").read_text()
    assert 'fill-rule="evenodd"' in skin and skin.count("Z") >= PASSES[name][0] + 1


# --- covers: ship fitted, come off, and what is under them is still there ------------------------------

@needs_dist
@pytest.mark.parametrize("name", list(COVERS))
def test_the_covers_ship_fitted_and_come_off_leaving_the_fingers_and_rings(name):
    faces, off = COVERS[name]
    cfgs = device_yaml(name)["configurations"]
    assert cfgs["base"]["default"] is True and cfgs[off]["kind"] == "example", \
        "a cover that comes with the part is an illustration, never a device type"
    for face, ids in faces.items():
        on = by_id(svg(name, face))
        gone = by_id(svg(name, face, off))
        for cid in ids:
            assert cid in on and on[cid].get("data-behaviour") == "mounts", "fitted as it ships, with a pull handle"
            assert cid not in gone, "and the drawing without it"
        stem = {"front": "fingers-", "rear": "rear-fingers-"}[face]
        if name in RINGED and face == "rear":
            assert all(f"guide-{k}" in gone for k in range(1, 6)), "the rings are in the drawing with the cover off"
        elif name in FINGERS and face in FINGERS[name]:
            assert any(i.startswith(stem) and "--" in i for i in gone), "the fingers are in the drawing with the cover off"


@pytest.mark.parametrize("name", list(COVERS))
def test_the_cover_contracts_say_lid_and_no_mechanism_is_invented_for_the_hinge(name):
    doc = device_yaml(name)
    assert any(g["what"] in ("cover-hinge", "door-hinge") for g in doc["gaps"]) or name == "pr2vsd06" and any(
        g["what"] == "door-hinge" for g in doc["gaps"])
    assert "hinge" not in json.dumps(doc["views"]).lower() and "hinge" not in json.dumps(doc["chassis"]).lower()
    for view in doc["views"].values():
        for p in (view.get("components") or {}).get("placements", []):
            comp = p["ref"].split("@")[0]
            contract = yaml.safe_load((LIB / "components" / comp / "v1" / "contract.yaml").read_text())
            if "cover" in comp or "door" in comp:
                assert contract["behaviour"] == "mounts" and contract["lid"] is True, comp
                assert "hinge" not in json.dumps(contract.get("elements", {})).lower()


# --- fingers: in front of the backbone, not through it ---------------------------------------------------

def _well_depth(root):
    """How deep the face's well is: the one element the build gives a `data-depth`."""
    depths = {float(e.get("data-depth")) for e in root.iter() if e.get("data-depth")}
    assert len(depths) == 1, depths
    return depths.pop()


def _finger_spans(root):
    """Every finger feature of a face as (path, start, end): where it stands from, and
    to, measured from the face's own plane with `out` the way the viewer reads it -
    a negative number is inside the chassis. A feature starts at its group's lift
    plus its own, and ends at its `data-z-out`."""
    spans = []
    for g in root.iter("{http://www.w3.org/2000/svg}g"):
        if not (g.get("id") or "").startswith(("fingers-", "rear-fingers-")) or g.get("data-z-lift") is None:
            continue
        for r in g.iter():
            if r.get("data-z-out") is not None:
                spans.append((r.get("data-path"), float(g.get("data-z-lift")) + float(r.get("data-z-lift") or 0),
                              float(r.get("data-z-out"))))
    return spans


def depth_order_faults(front_spans, front_depth, rear_spans, rear_depth, D, tol=0.15):
    """What is wrong with the depth order of a manager's fingers, as readable strings.
    The backbone is the slab between the two wells' floors: D less the front well's
    depth and the rear well's. A finger must stand ON its floor or in front of it
    (start no deeper than the floor), reach out (end past its start) and stay inside
    the chassis (end no further than the face); and the two wells must not overlap,
    or one side's fingers stand in the other's."""
    faults = []
    for face, spans, depth in (("front", front_spans, front_depth), ("rear", rear_spans, rear_depth)):
        if depth is None:
            continue
        for path, start, end in spans:
            if start < -depth - tol:
                faults.append(f"{face} {path}: starts {-start - depth:.2f} mm behind its floor, through the backbone")
            if end <= start:
                faults.append(f"{face} {path}: ends at {end}, not past its start {start}")
            if end > tol:
                faults.append(f"{face} {path}: ends {end} mm outside the face")
    if front_depth is not None and rear_depth is not None and D - front_depth - rear_depth < 0:
        faults.append(f"the two wells overlap by {front_depth + rear_depth - D:.2f} mm: no backbone between them")
    return faults


def test_the_depth_order_check_catches_a_finger_through_the_backbone():
    """The check itself, on numbers: a finger that starts 20 mm behind its floor, one
    that ends outside the face, one that does not reach out, and wells that overlap."""
    good = [("f1", -303.0, -43.0)]
    assert depth_order_faults(good, 303.0, [("r1", -203.0, -28.0)], 203.0, 526.4) == []
    assert depth_order_faults([("f1", -323.0, -43.0)], 303.0, [], None, 526.4)
    assert depth_order_faults([("f1", -303.0, 5.0)], 303.0, [], None, 526.4)
    assert depth_order_faults([("f1", -303.0, -303.0)], 303.0, [], None, 526.4)
    assert depth_order_faults(good, 303.0, [("r1", -203.0, -28.0)], 203.0, 500.0)


@needs_dist
@pytest.mark.parametrize("name", list(FINGERS))
def test_the_fingers_stand_in_front_of_the_backbone_and_not_through_it(name):
    """The drawing says so in numbers the viewer builds from: each finger rises from
    the floor of its face's well to inside the face, the front's and the rear's wells
    leave the backbone between them, and nothing of a front finger is behind a rear
    one's floor. The two vertical managers' 90 fingers a side are the ones this was
    asked of: they were read as passing through the central spine, and do not."""
    per_face = {}
    for face in FINGERS[name]:
        root = svg(name, face)
        spans = _finger_spans(root)
        assert spans, f"{name} {face}: no finger carries relief"
        per_face[face] = (spans, _well_depth(root))
    front, rear = per_face.get("front"), per_face.get("rear")
    chassis_d = float(device_yaml(name)["chassis"]["depth"])
    faults = depth_order_faults(front[0], front[1], rear[0] if rear else [], rear[1] if rear else None, chassis_d)
    assert not faults, faults[:5]


def _contract(ref):
    return yaml.safe_load((LIB / "components" / ref / "v1" / "contract.yaml").read_text())


def _rect(doc, node):
    (x, y), (w, h) = doc["elements"][node]["at"], doc["elements"][node]["size"]
    return x, y, x + w, y + h


@pytest.mark.parametrize("ref", ["panduit/nm-cover-2ru", "panduit/nm-rear-cover-2ru"])
def test_a_2ru_cover_is_a_panel_in_a_rim_with_knuckles_and_not_one_slab(ref):
    """The NM2's cover read as a flat board in 3D: a plate and two lips, all of them
    one colour. It is a panel sunk inside a raised rim with five hinge knuckles along
    each of its top and bottom edges. What no Panduit view draws (the rim, the panel's
    thickness, the knuckles' count and size) is declared a stand-in, in the sources
    and on every feature, and not left looking measured."""
    doc = _contract(ref)
    feats = {f["node"]: f for f in doc["relief"]["features"]}
    assert set(feats) == set(doc["elements"]), "every drawn element is a feature, and the other way round"
    levels = {f["out"] for f in feats.values()}
    assert len(levels) >= 2 and feats["plate"]["out"] == min(levels), \
        f"the panel stands below the rim, the knuckles and the lips: {sorted(levels)}"
    top = sorted(n for n in feats if n.startswith("knuckle-top-"))
    bottom = sorted(n for n in feats if n.startswith("knuckle-bottom-"))
    assert len(top) == len(bottom) == 5
    assert all(_rect(doc, n)[1] < 10 for n in top) and all(_rect(doc, n)[3] > doc["size"]["h"] - 10 for n in bottom)
    plate = feats["plate"]
    for n in top + bottom + ["rim-left", "rim-right"]:
        # standing on the panel and above it: the rim and the knuckles are the cover's full thickness
        assert feats[n]["lift"] == plate["lift"] and feats[n]["out"] > plate["out"], n
        assert feats[n]["out"] == feats["lip-top"]["out"], n
        assert feats[n]["color"] != plate["color"], f"{n} reads apart from the panel"
    # every figure no document gives is estimated, and the provenance says it is a stand-in
    assert all(f["confidence"] == "estimated" for f in feats.values())
    assert "STAND-IN" in doc["provenance"]["detail"]
    assert all(f["source"] for f in feats.values())


@pytest.mark.parametrize("ref", ["panduit/nm-cover-2ru", "panduit/nm-rear-cover-2ru"])
def test_no_two_features_of_a_2ru_cover_share_a_top_face_where_they_overlap(ref):
    """Two boxes whose tops are one plane and whose footprints overlap z-fight in 3D,
    and a render picks one of them at random from one frame to the next."""
    doc = _contract(ref)
    feats = doc["relief"]["features"]
    for i, a in enumerate(feats):
        ra = _rect(doc, a["node"])
        for b in feats[i + 1:]:
            if a["out"] != b["out"]:
                continue
            rb = _rect(doc, b["node"])
            overlap = min(ra[2], rb[2]) - max(ra[0], rb[0]) > 1e-6 and min(ra[3], rb[3]) - max(ra[1], rb[1]) > 1e-6
            assert not overlap, (a["node"], b["node"])


# --- capacity: only what a Panduit table or calculator states, and its basis ------------------------------

@pytest.mark.parametrize("name", list(CAPACITY))
def test_cable_capacity_is_the_makers_figure_with_its_basis(name):
    front, rear, media = CAPACITY[name]
    perf = device_yaml(name)["attrs"]["performance"]
    assert perf["cable-capacity"] == front
    assert "Panduit" in perf["cable-capacity-basis"] and "30%" in perf["cable-capacity-basis"]
    if rear is not None:
        assert perf["cable-capacity-rear"] == rear and "usable area" in perf["cable-capacity-rear-basis"]
        assert "30%" in perf["cable-capacity-rear-basis"]
    if media:
        assert perf["cable-capacity-media"] == media and "0.235 in" in perf["cable-capacity-basis"]
    else:
        assert "cable-capacity-media" not in perf, "the calculator's cable is a 0.185 in cord: no kind is stated"
    assert "cable-capacity-estimated" not in perf, "nothing here is an estimate"


def test_the_pr2vsd06_states_no_capacity_because_no_panduit_document_does():
    doc = device_yaml("pr2vsd06")
    assert "performance" not in doc["attrs"] and any(g["what"] == "cable-capacity" for g in doc["gaps"])


@needs_dist
@pytest.mark.parametrize("name", list(CAPACITY))
def test_the_rack_catalogue_carries_the_count_for_the_kit_to_show(name):
    front, rear, media = CAPACITY[name]
    cap = rack(name)["capacity"]
    assert cap["count"] == front and cap["media"] == media and "estimated" not in cap


# --- the DCIM device types: horizontals fill their rack units, verticals beside the rack take none -----------

@pytest.mark.parametrize("name", ALL)
def test_the_dcim_device_types_say_the_rack_units_and_not_full_depth(name):
    doc = device_yaml(name)
    model = doc["model"]
    want = 0.0 if name in VERTICALS else float(doc["chassis"]["ru"])
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Panduit" / f"{model}.yaml"
        assert path.is_file(), f"{path} is missing: run dcim_export.py --device {name}"
        out = yaml.safe_load(path.read_text())
        assert out["manufacturer"] == "Panduit" and out["model"] == model
        assert out["u_height"] == want and out["is_full_depth"] is False

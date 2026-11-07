"""Belden's horizontal cable managers (roc-ops/Portrayal#1103, part of #1091): the four BHH molded-finger
managers with a hinging cover, the 9512-1901 finger stock manager with its cover, the 9510-1901 ring panel
with six saddle rings and the 9511-1903 and 9511-1904 ring managers.

Every size below is what Belden's technical data sheets state (revision date 05-31-2024), in inches as
printed and converted here, so a model that drifts from its data sheet fails by name. The data sheets
carry no dimensioned drawing: the finger pitch, the ring size and the cover's shape are read off their
thumbnails and are estimates, which the contracts say. The rack kit's half of the features (a cable laid
through a ring, along a duct) is `spec/tests/js/rack-belden-managers.mjs`, run by `test_rack_kit_js.py`.

The lacing bar 9512-1903 is not modelled: the format has no tie point on a ring or a duct yet (#1009), and
a cable is tied to a lacing bar, not laid through it. `test_the_lacing_bar_waits_for_the_tie_point_issue`
holds that, so adding it later is a decision and not an accident.

These read the build (`library/dist`, `library/exports`) and skip without it, like the other sweeps over
compiled drawings.
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
LB = 0.45359237

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")

# name -> (rack units, height in, depth in, weight lb): each from the part's own data sheet, the 9511
# heights being the two conflicts settled from the rack units (3U is 5.25 in, 4U is 7.0 in; the 9511-1903
# data sheet also says 3.0 in, the 9511-1904 data sheet 5.25 in and 6.9 in)
PARTS = {
    "bhh191ur": (1, 1.75, 7.22, 3.0),
    "bhh192ur": (2, 3.5, 7.22, 3.5),
    "bhh193ur": (3, 5.25, 7.22, 4.4),
    "bhh194ur": (4, 7.0, 7.22, 5.2),
    "9512-1901": (1, 1.5, 2.0, 1.1),
    "9510-1901": (1, 1.65, 3.0, 2.2),
    "9511-1903": (3, 5.25, 3.0, 4.5),
    "9511-1904": (4, 7.0, 3.0, 6.5),
}
FINGERED = {"bhh191ur": 10, "bhh192ur": 10, "bhh193ur": 10, "bhh194ur": 10, "9512-1901": 20}   # openings a row
RINGED = {"9510-1901": 6, "9511-1903": 8, "9511-1904": 8}
COVERED = {"bhh191ur": "bhh-cover-1u", "bhh192ur": "bhh-cover-2u", "bhh193ur": "bhh-cover-3u",
           "bhh194ur": "bhh-cover-4u", "9512-1901": "9512-1901-cover"}
FACE_W = 482.6                       # 19 in, ears included: a rack-face part is its ears and what hangs off them
# the finger pitch and opening, the estimates the contracts state: ten openings across the 450 between the ears
PITCH = {"bhh": (42.5, 34.0), "9512-1901": (21.5, 14.5)}
RING_BAND = 10.0
RING_APERTURE = (34.0, 68.7)
ALL = list(PARTS)
STAGES = {"light": "#ffffff", "dark": "#101214"}   # the explorer's two stages: white, and the shell's dark


def svg(name, view, config="base"):
    return ET.parse(DIST / f"{name}.{config}.{view}.svg").getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def device_yaml(name):
    return yaml.safe_load((LIB / "devices" / "belden" / name / "device.yaml").read_text())


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


def close(a, b, tol=0.06):
    return abs(a - b) <= tol


def luminance(hexcolour):
    h = hexcolour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    chan = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in chan]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def blend(fill, over, alpha):
    f, o = fill.lstrip("#"), over.lstrip("#")
    return "#" + "".join("%02x" % round(int(f[i:i + 2], 16) * (1 - alpha) + int(o[i:i + 2], 16) * alpha) for i in (0, 2, 4))


# --- the maker ----------------------------------------------------------------------------------

def test_belden_is_a_hardware_vendor_listed_directly_after_credo():
    text = (ROOT / "spec/schemas/vendors.yaml").read_text()
    keys = [l.strip().rstrip(":") for l in text.splitlines() if l.startswith("  ") and not l.startswith("   ") and l.rstrip().endswith(":")]
    assert keys.index("belden") == keys.index("credo") + 1 and keys[keys.index("belden") + 1] == "siemon"
    vendors = yaml.safe_load(text)["vendors"]
    assert vendors["belden"]["role"] == "hardware" and vendors["belden"]["display"] == "Belden"
    assert "Belden, Inc" in vendors["belden"]["source"] and "data sheet" in vendors["belden"]["source"]


def test_exactly_these_eight_parts_are_modelled_and_the_lacing_bar_waits_for_the_tie_point_issue():
    names = sorted(p.name for p in (LIB / "devices" / "belden").iterdir() if p.is_dir())
    assert names == sorted(ALL), "the lacing bar 9512-1903 is left out: no tie point on a ring or a duct yet (#1009)"


# --- each device's envelope against its data sheet -------------------------------------------------

@pytest.mark.parametrize("name", ALL)
def test_the_envelope_is_the_data_sheets_and_the_part_bolts_to_the_rail_face(name):
    ru, h_in, d_in, lb = PARTS[name]
    doc = device_yaml(name)
    c = doc["chassis"]
    assert doc["manufacturer"] == "Belden"
    assert c["width"] == FACE_W, "19 in, ears included"
    assert close(c["height"], h_in * MM, 0.01) and close(c["depth"], d_in * MM, 0.05)
    assert c["ru"] == ru and c["mount"] == "rack-face" and c["shell"] == "sheet"
    assert close(c["weight-kg"], lb * LB, 0.01) and c["weight-kg"] == doc["attrs"]["physical"]["weight-kg"]
    assert doc["views"]["front"]["size"] == {"w": c["width"], "h": c["height"]}
    assert doc["datasheet"]["url"] == f"https://catalog.belden.com/techdata/EN/{name.upper()}_techdata.pdf"
    assert len(doc["datasheet"]["sha256"]) == 64


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_build_carries_the_envelope_to_the_rack_catalogue(name):
    ru, h_in, d_in, _lb = PARTS[name]
    r = rack(name)
    assert (r["ru"], r["w"], r["shell"], r["mount"]) == (ru, FACE_W, "sheet", "rack-face")
    assert close(r["d"], d_in * MM, 0.05) and close(r["h"], h_in * MM, 0.01)


def test_the_two_height_conflicts_are_settled_from_the_rack_units_and_say_so():
    """9511-1903: 'Overall Height 3.0 in' against 5.25 in; 9511-1904: 'Overall Height 5.25 in' against
    6.9 in. 3U is 5.25 in and 4U is 7.0 in, and the maker's BHH193UR and BHH194UR sheets state those."""
    for name, said, taken in (("9511-1903", ("3.0 in", "5.25 in"), "5.25"), ("9511-1904", ("5.25 in", "6.9 in"), "7.0")):
        doc = device_yaml(name)
        note = doc["provenance"]["chassis"]["note"]
        assert all(s in note for s in said) and taken in note, "both figures and the one used are in the note"
        gap = next(g for g in doc["gaps"] if g["what"] == "height-conflict")
        assert gap["reason"] == "sources-disagree" and all(s in gap["note"] for s in said[-1:])
    assert close(device_yaml("9511-1903")["chassis"]["height"], 5.25 * MM) and close(device_yaml("9511-1904")["chassis"]["height"], 7.0 * MM)


# --- the molded fingers and the finger stock: a duct a cable runs along -------------------------------------

@pytest.mark.parametrize("name", list(FINGERED))
def test_each_finger_part_declares_its_duct_with_the_estimated_pitch_and_gap(name):
    doc = device_yaml(name)
    ch = doc["chassis"]
    (duct,) = doc["views"]["front"]["guides"]
    pitch, gap = PITCH["9512-1901" if name == "9512-1901" else "bhh"]
    assert duct["kind"] == "duct" and duct["run"] == "x"
    assert (duct["finger-pitch"], duct["finger-gap"]) == (pitch, gap)
    assert duct["confidence"] == "estimated", "no Belden document dimensions a finger"
    plate = 6.0 if name == "9512-1901" else 10.0
    assert duct["at"] == [16.3, plate] and duct["size"][0] == 450.0
    assert close(duct["size"][1], ch["height"] - 2 * plate, 0.01), "the channel between the two finger rows"
    assert doc["provenance"]["fingers"]["confidence"] == "estimated"


@needs_dist
@pytest.mark.parametrize("name", list(FINGERED))
def test_each_finger_part_publishes_its_duct_in_the_build(name):
    pitch, gap = PITCH["9512-1901" if name == "9512-1901" else "bhh"]
    el = by_id(svg(name, "front"))["guide--duct"]
    assert el.get("data-guide") == "duct" and el.get("data-guide-run") == "x"
    assert float(el.get("data-guide-finger-pitch")) == pitch and float(el.get("data-guide-finger-gap")) == gap
    assert float(el.get("width")) == 450.0
    assert rack(name)["guides"] == {"front": ["duct"]}


@pytest.mark.parametrize("name", list(FINGERED))
def test_the_fingers_are_a_row_top_and_bottom_with_an_opening_between_each_pair(name):
    n = FINGERED[name]
    doc = device_yaml(name)
    fingers = [p for p in doc["views"]["front"]["components"]["placements"] if p["group"] == "fingers"]
    assert len(fingers) == 2 * (n + 1), "n openings, n + 1 fingers, two rows"
    upper = sorted(p["at"][0] for p in fingers if p["at"][1] == 0.0)
    assert len(upper) == n + 1
    gaps = [round(b - a, 2) for a, b in zip(upper[1:-1], upper[2:-1])]
    assert set(gaps) == {PITCH["9512-1901" if name == "9512-1901" else "bhh"][0]}, "the pitch, finger to finger"
    assert {p["at"][1] for p in fingers} == {0.0, round(doc["chassis"]["height"] - (6.0 if name == "9512-1901" else 10.0), 2)}
    # the openings of the plan: n a row, as wide as the gap, on the pitch
    top = device_yaml(name)["views"]["top"]["panel"]["decor"]
    slots = sorted((d for d in top if d["id"].startswith("slot-") and not d["id"].endswith("-neck")), key=lambda d: d["at"][0])
    assert len(slots) == n
    pitch, gap = PITCH["9512-1901" if name == "9512-1901" else "bhh"]
    assert all(s["size"][0] == gap for s in slots)
    assert [round(b["at"][0] - a["at"][0], 2) for a, b in zip(slots, slots[1:])] == [pitch] * (n - 1)
    # no row at the rear: the sources show none, and the device says so
    assert not doc["views"]["rear"].get("components")
    assert any(g["what"] == "rear-fingers" for g in doc["gaps"])


@pytest.mark.parametrize("name", list(FINGERED))
def test_the_fingers_stand_in_the_back_plate_under_the_cover(name):
    for p in (p for p in device_yaml(name)["views"]["front"]["components"]["placements"] if p["group"] == "fingers"):
        assert p["in"] == "base" and p["under"] == "cover"


# --- the saddle rings: a ring a cable is laid through -------------------------------------------------

@needs_dist
@pytest.mark.parametrize("name", list(RINGED))
def test_each_ring_part_publishes_a_ring_guide_for_every_ring_with_the_estimated_opening(name):
    n = RINGED[name]
    root = svg(name, "front")
    rings = sorted((e for e in root.iter() if e.get("data-guide") == "ring"), key=lambda e: int(e.get("id").split("-")[1]))
    assert [e.get("id") for e in rings] == [f"guide-{k}" for k in range(1, n + 1)], "one for every ring, no more"
    for e in rings:
        assert e.get("data-guide-run") == "x"
        assert tuple(float(v) for v in e.get("data-guide-aperture").split()) == RING_APERTURE
        assert float(e.get("data-guide-depth")) == RING_BAND
    assert rack(name)["guides"]["front"] == [f"guide-{k}" for k in range(1, n + 1)]
    contract = yaml.safe_load((LIB / "components/belden/saddle-ring/v1/contract.yaml").read_text())
    assert contract["guide"]["aperture"] == {"w": 34.0, "h": 68.7} and contract["size-confidence"]["w"] == "estimated"


@needs_dist
@pytest.mark.parametrize("name", list(RINGED))
def test_the_rings_stand_on_the_face_at_the_drawn_columns(name):
    n = RINGED[name]
    h = device_yaml(name)["chassis"]["height"]
    root = svg(name, "front")
    pos = []
    for e in root.iter():
        if e.get("data-guide") == "ring":
            tx, ty = (float(v) for v in e.get("transform").split("(")[1].rstrip(")").split(","))
            pos.append((tx, ty))
            assert tx >= 0 and tx + RING_BAND <= FACE_W and ty >= 0 and ty + 40.0 <= h + 1e-6, "a ring inside its face"
    assert len(pos) == n
    columns = sorted({round(x + RING_BAND / 2, 1) for x, _ in pos})
    # six columns 80.0 apart, symmetric about the middle (an even spread read off the thumbnail or photograph)
    expect = [41.3, 121.3, 201.3, 281.3, 361.3, 441.3] if name != "9510-1901" else [46.3, 124.3, 202.3, 280.3, 358.3, 436.3]
    assert columns == expect
    assert close(sum(columns) / len(columns), FACE_W / 2, 0.01)
    if name != "9510-1901":
        assert len(pos) == 8 and sorted(x for x, _ in pos).count(36.3) == 2, "two stacked at each end, four between"


@needs_dist
@pytest.mark.parametrize("name", list(RINGED))
def test_the_ring_is_an_open_loop_with_a_slit_attached_at_its_real_depth(name):
    """A ring is a strap bent to a loop: back leg on the plate, top and bottom bars, a front leg at the
    part's front, and an upturned hook that ends the bottom bar leaving a slit a cable is laid in through.
    Nothing stands past the part's front face, and the back leg is on the plate, so the ring is attached to
    the body at the depth the data sheet states and does not float or stand proud."""
    d = device_yaml(name)["chassis"]["depth"]
    el = by_id(svg(name, "front"))
    plate = d - 74.7
    assert close(plate, 1.5, 0.05)
    for k in range(1, RINGED[name] + 1):
        back, top, bottom = el[f"guide-{k}--back"], el[f"guide-{k}--top"], el[f"guide-{k}--bottom"]
        front, hook = el[f"guide-{k}--front"], el[f"guide-{k}--hook"]
        assert close(float(front.get("data-z-out")), 0, 0.15) and close(float(top.get("data-z-out")), 0, 0.15), "to the front"
        assert close(float(back.get("data-z-out")), -(74.7 - 3.0), 0.01), "the back leg is 3.0 mm on the plate"
        assert all(float(e.get("data-z-out") or 0) <= 0.15 for e in (back, top, bottom, front, hook)), "nothing proud of the front"
        # the slit: the hook stands 18.0 from the plate, its 3.0 leaving 15.0 between it and the back leg
        assert close(float(hook.get("data-z-lift")), 18.0, 0.01) and close(float(bottom.get("data-z-lift")), 18.0, 0.01)
        slit = float(hook.get("data-z-lift")) - 3.0
        assert slit == 15.0
        # the hook rises from the bottom bar to 8.0 mm above it
        assert close(float(hook.get("y")) + float(hook.get("height")), float(bottom.get("y")), 0.01)


# --- the covers: parts a manager ships with and that come off ----------------------------------------

@pytest.mark.parametrize("name", list(COVERED))
def test_the_cover_is_a_removable_lid_that_ships_fitted_and_is_the_only_thing_the_other_config_drops(name):
    doc = device_yaml(name)
    ref = COVERED[name]
    placed = [p for p in doc["views"]["front"]["components"]["placements"] if p["ref"] == f"belden/{ref}@1"]
    assert [p["id"] for p in placed] == ["cover"] and placed[0]["only-in"] == ["base"], "fitted as it ships, off in cover-off"
    c = yaml.safe_load((LIB / "components/belden" / ref / "v1/contract.yaml").read_text())
    assert c["behaviour"] == "mounts" and c["lid"] is True, "a pull handle in the explorer, and a pass may lie under it"
    cfgs = doc["configurations"]
    assert cfgs["base"]["default"] is True and cfgs["cover-off"]["kind"] == "example"
    assert set(cfgs["cover-off"]["views"]) == {"top", "bottom", "left", "right"}


@needs_dist
@pytest.mark.parametrize("name", list(COVERED))
def test_the_drawing_with_the_cover_off_shows_the_fingers_and_the_cover_is_gone_from_every_view(name):
    on, off = by_id(svg(name, "front")), by_id(svg(name, "front", "cover-off"))
    assert "cover" in on and on["cover"].get("data-behaviour") == "mounts"
    assert "cover" not in off and not any(i.startswith("cover--") for i in off), "the cover and its parts are gone"
    fingers_on = {i for i in on if i.startswith("finger-")}
    fingers_off = {i for i in off if i.startswith("finger-")}
    assert fingers_on == fingers_off and len(fingers_off) >= 2 * (FINGERED[name] + 1), "every finger is still drawn"
    for view in ("top", "bottom", "left", "right"):
        a = by_id(svg(name, view))
        b = by_id(svg(name, view, "cover-off"))
        assert any("cover" in (e.get("data-kind") or "") for e in a.values()), view
        assert not any("cover" in (e.get("data-kind") or "") for e in b.values()), view
        assert any(e.get("data-kind") == "finger-wall" or "wall" in i for i, e in b.items()), "the fingers' wall shows"
    # the covered drawing's cover stands in the part's front 14 (BHH) or 8 mm (9512-1901) and no further
    cover_plate = on["cover--plate"]
    assert close(float(cover_plate.get("data-z-out")), 0, 0.15)


def test_the_hinge_is_a_gap_and_no_mechanism_is_invented():
    for name in COVERED:
        doc = device_yaml(name)
        gaps = {g["what"] for g in doc["gaps"]}
        assert ("cover-hinge" in gaps) == name.startswith("bhh"), name
        assert "cover-fixing" in gaps or name.startswith("bhh")
        blob = json.dumps(doc["views"]).lower() + json.dumps(doc["chassis"]).lower()
        assert "hinge" not in blob, "the format has no hinge: the cover is a part that is on or off"


# --- no maker figure is invented ----------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL)
def test_no_cable_capacity_or_bend_radius_is_recorded_because_no_source_states_one(name):
    doc = device_yaml(name)
    flat = json.dumps(doc["attrs"])
    assert "cable-capacity" not in flat and "bend" not in flat
    whats = {g["what"] for g in doc["gaps"]}
    assert {"cable-capacity", "bend-radius"} <= whats
    assert doc["provenance"]["capacity"]["confidence"] == "datasheet", "the data sheet states none: that is what the note says"


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_the_rack_catalogue_has_no_capacity_to_compare(name):
    assert rack(name).get("capacity") is None


@pytest.mark.parametrize("name", ALL)
def test_every_inner_detail_says_it_is_estimated_and_how(name):
    doc = device_yaml(name)
    prov = doc["provenance"]
    for key in ("method", "ears", "shell", "thickness", "front", "guides", "color"):
        assert prov[key]["confidence"] == "estimated", key
    assert "Cloudflare" in prov["method"]["note"], "the product page was refused, and the note says so"
    assert any(k in prov for k in ("fingers", "rings"))
    assert "estimated" in prov["fingers" if "fingers" in prov else "rings"]["note"]


# --- the faces: attached at their depth, and readable on both stages ----------------------------------------

@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_no_part_stands_past_the_front_of_its_envelope_and_the_plate_is_the_full_width(name):
    root = svg(name, "front")
    for e in root.iter():
        z = e.get("data-z-out")
        if z is not None:
            assert float(z) <= 0.15, f"{e.get('id')} stands proud of the part's front ({z})"
    floor = by_id(root)[("base" if name in FINGERED else "panel") + "--floor"]
    assert float(floor.get("width")) == FACE_W and float(floor.get("x")) == 0, "the back plate runs the full width"


@needs_dist
@pytest.mark.parametrize("name", ALL)
def test_every_drawn_part_reads_on_the_light_stage_and_on_the_dark_one(name):
    """Each fill a part is drawn in stands off both the white stage and the dark one, with the lit and
    shaded layers over it taken into account: nothing is drawn black on black."""
    root = svg(name, "front")
    checked = 0
    for e in root.iter():
        i, fill = e.get("id") or "", e.get("fill") or ""
        if not (fill.startswith("#") and e.tag.endswith("rect")) or fill in ("#fff", "#000", "#ffffff", "#0a0b0c"):
            continue
        if any(s in i for s in ("shade", "-lit", "rim")):
            continue
        if i.endswith("--floor"):
            fill = blend(fill, "#ffffff", 0.1)
        for stage in STAGES.values():
            assert contrast(fill, stage) >= 1.5, f"{name} {i} {fill} on {stage}: {contrast(fill, stage):.2f}"
        checked += 1
    assert checked >= 5
    # and no colour is a token a stage could swallow: the skins paint a fixed value, a figure checked here
    for view in ("top", "left"):
        for e in svg(name, view).iter():
            f = e.get("fill") or ""
            if f.startswith("#") and f not in ("#0a0b0c", "#fff", "#000") and e.get("data-kind") not in (None, "finger-gap"):
                assert all(contrast(f, s) >= 1.5 for s in STAGES.values()), f"{name} {view} {e.get('id')} {f}"


# --- the DCIM device types: manager parts that bolt to the rail face and occupy no unit ----------------------

@pytest.mark.parametrize("name", ALL)
def test_the_dcim_device_types_export_zero_u_and_not_full_depth(name):
    model = device_yaml(name)["model"]
    for target in ("netbox", "nautobot"):
        path = EXPORTS / target / "device-types" / "Belden" / f"{model}.yaml"
        assert path.is_file(), f"{path} is missing: run dcim_export.py --device {name}"
        doc = yaml.safe_load(path.read_text())
        assert doc["manufacturer"] == "Belden" and doc["model"] == model
        assert doc["u_height"] == 0.0 and doc["is_full_depth"] is False
        assert "occupies none" in doc["comments"] or "occupies no rack unit" in doc["comments"]

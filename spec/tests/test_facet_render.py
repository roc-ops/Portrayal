"""render.py draws a part on a facet foreshortened and marks it for 3D."""
import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC, LIB = ROOT / "spec", ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"

SKIN = ('<svg xmlns="http://www.w3.org/2000/svg" width="25mm" height="100mm" viewBox="0 0 25 100">'
        '<rect id="face" width="25" height="100" fill="#ccc"/>'
        '<rect id="housing" x="0" y="40" width="25" height="30" fill="#999"/></svg>')

# std/qsfp28@1's own `mate`, and generic/qsfp-lc@1's own `mate` - the two
# local connection points the position assertions carry through a full
# transform chain, read straight from the library contracts rather than
# hand-copied so a future edit to either contract cannot silently desync
# these tests from what render.py is actually projecting.
QSFP28 = yaml.safe_load((LIB / "components/std/qsfp28/v1/contract.yaml").read_text())
QSFP_LC = yaml.safe_load((LIB / "components/generic/qsfp-lc/v1/contract.yaml").read_text())
QSFP28_MATE = QSFP28["connection-points"]["mate"]["at"]
QSFP_LC_MATE = QSFP_LC["connection-points"]["mate"]["at"]


def _apply_transform(tf, pt):
    """A local point through one SVG `transform` string, composed in the
    order the string applies to a point: the RIGHTMOST function first."""
    x, y = pt
    for token, args in reversed(re.findall(r"(\w+)\(([^)]*)\)", tf or "")):
        nums = [float(a) for a in re.split(r"[,\s]+", args.strip()) if a]
        if token == "translate":
            dx, dy = nums[0], (nums[1] if len(nums) > 1 else 0.0)
            x, y = x + dx, y + dy
        elif token == "scale":
            sx = nums[0]
            sy = nums[1] if len(nums) > 1 else sx
            x, y = x * sx, y * sy
        elif token == "rotate":
            deg = nums[0]
            cx, cy = (nums[1], nums[2]) if len(nums) == 3 else (0.0, 0.0)
            rad = math.radians(deg)
            x0, y0 = x - cx, y - cy
            x = cx + x0 * math.cos(rad) - y0 * math.sin(rad)
            y = cy + x0 * math.sin(rad) + y0 * math.cos(rad)
    return x, y


def device_point(root, el, local_pt):
    """`local_pt` (in `el`'s own untransformed frame) carried out to
    device-frame coordinates, through `el`'s own transform and every
    ancestor's, innermost first - however deep `el` is nested."""
    parents = {c: p for p in root.iter() for c in p}
    pt = local_pt
    node = el
    while node is not None:
        tf = node.get("transform")
        if tf:
            pt = _apply_transform(tf, pt)
        node = parents.get(node)
    return pt


def device_bbox(root, el, size):
    """The device-space (width, height) `el`'s own local box (0,0)-(w,h)
    occupies, through its full transform chain - pins the FORESHORTENED
    axis down, which two coincident mate points cannot: a scale on the
    wrong axis still lands the single point it was solved for correctly,
    and only shows up as the wrong dimension foreshortened."""
    corners = [(0, 0), (size["w"], 0), (size["w"], size["h"]), (0, size["h"])]
    pts = [device_point(root, el, c) for c in corners]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


def plant_card(tmp, rotate=None, occupant=False, card_rotate=None,
               feat_lift=0.0, chained=False):
    lib = tmp / "lib"
    d = lib / "components/acme/tilt-card/v1"
    (d / "skins").mkdir(parents=True)
    part = {"ref": "std/qsfp28@1", "id": "p1", "at": [2.5, 45.0], "on": "housing"}
    if rotate:
        part["rotate"] = rotate
    feature = {"node": "housing", "facet": {"deg": 30, "facing": "up"},
               "confidence": "drawing", "source": "fixture"}
    if feat_lift:
        feature["lift"] = feat_lift
    (d / "contract.yaml").write_text(yaml.safe_dump({
        "format": 1, "kind": "module", "name": "tilt-card", "version": "1.0.0",
        "class": "line-card", "behaviour": "fills", "size": {"w": 25.0, "h": 100.0},
        "elements": {"face": {"at": [0, 0], "size": [25, 100], "class": "panel"},
                     "housing": {"at": [0.0, 40.0], "size": [25.0, 30.0], "class": "panel"}},
        "relief": {"features": [feature]},
        "parts": [part],
        "connection-points": {"mate": {"at": [12.5, 50.0], "direction": "rear"}},
        "skins": ["default"]}))
    (d / "skins/default.svg").write_text(SKIN)
    if chained:
        # A THIRD, SYNTHETIC PART, mate-to'd to `optic` itself - the fixture
        # for a CHAINED seat (a cap on an optic that is itself seated on a
        # tilted cage). Its own geometry is arbitrary; only its `mate`
        # matters.
        cd = lib / "components/acme/cap/v1"
        (cd / "skins").mkdir(parents=True)
        (cd / "contract.yaml").write_text(yaml.safe_dump({
            "format": 1, "kind": "component", "name": "cap", "version": "1.0.0",
            "class": "accessory", "size": {"w": 5.0, "h": 5.0},
            "connection-points": {"mate": {"at": [2.5, 2.5], "direction": "front"}},
            "skins": ["default"]}))
        (cd / "skins/default.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="5mm" height="5mm" '
            'viewBox="0 0 5 5"><rect width="5" height="5" fill="#333"/></svg>')
    dev = tmp / "device.yaml"
    card_placement = {"ref": "acme/tilt-card@1", "id": "card", "at": [0, 0]}
    if card_rotate:
        card_placement["rotate"] = card_rotate
    placements = [card_placement]
    if occupant:
        # `mate-to` targets a device-level PLACEMENT id, not a path into it
        # (render.py's `hosts` dict is keyed by placement id only). "card"
        # forwards to `p1`'s own `mate` connection-point through
        # `presented_interface` exactly as any other composed aperture
        # does, since `card` composes exactly one part (`p1`) that declares
        # an `interface` + `mate`.
        placements.append({"ref": "generic/qsfp-lc@1", "id": "optic", "mate-to": "card"})
        if chained:
            placements.append({"ref": "acme/cap@1", "id": "cap", "mate-to": "optic"})
    dev.write_text(yaml.safe_dump({
        "format": 1, "kind": "device", "name": "tilt-dev", "version": "0.1.0",
        "maturity": "draft", "manufacturer": "Acme", "model": "T", "profile": "networking",
        "chassis": {"width": 25, "height": 100, "depth": 200},
        "views": {"front": {"size": {"w": 25, "h": 100},
                            "components": {"placements": placements}}}}, sort_keys=False))
    out = tmp / "o"
    out.mkdir()
    r = subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                        "--library", str(lib), "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return ET.parse(out / "tilt-dev.front.svg").getroot()


def by_id(root, suffix):
    return next(e for e in root.iter() if (e.get("id") or "").endswith(suffix))


def test_the_facet_node_carries_its_derived_wedge(tmp_path):
    root = plant_card(tmp_path)
    h = by_id(root, "--housing")
    assert h.get("data-facet-deg") == "30" and h.get("data-facet-facing") == "up"
    assert h.get("data-z-profile-y").startswith("0:0,30:")
    assert float(h.get("data-z-out")) > 17.3          # 30 x tan 30 = 17.32


def test_a_facet_features_own_lift_offsets_the_whole_wedge(tmp_path):
    """`lift` moves the root edge too, not just the proud one: root at
    `lift`, proud edge at `lift + proud_extent`."""
    root = plant_card(tmp_path, feat_lift=5.0)
    h = by_id(root, "--housing")
    assert h.get("data-z-out") == "22.3205"           # 5 + 30 x tan 30
    assert h.get("data-z-profile-y") == "0:5,30:22.3205"


def test_a_part_on_a_facet_is_scaled_and_marked(tmp_path):
    root = plant_card(tmp_path)
    p = by_id(root, "--p1")
    assert "scale(1,0.866025)" in p.get("transform")
    assert p.get("data-tilt") == "30" and p.get("data-tilt-facing") == "up"
    assert p.get("data-tilt-on").endswith("--housing")


def test_the_scale_comes_before_the_parts_own_rotate(tmp_path):
    tf = by_id(plant_card(tmp_path, rotate=90), "--p1").get("transform")
    assert tf.index("scale(") < tf.index("rotate(")


def test_an_occupant_inherits_the_tilt(tmp_path):
    root = plant_card(tmp_path, occupant=True)
    o = next(e for e in root.iter() if (e.get("data-path") or e.get("id") or "").endswith("optic"))
    assert o.get("data-tilt") == "30"
    assert o.get("data-tilt-on").endswith("--housing")
    # POSITION, not just the label: the optic's own mate point and the
    # aperture (p1's) it seats on must land on the SAME device-frame point,
    # each carried out through its own full transform (translate, the
    # tilt's scale, any rotate). A wrong projection moves the label nowhere
    # but visibly separates the two.
    p1 = by_id(root, "--p1")
    p1_pt = device_point(root, p1, QSFP28_MATE)
    o_pt = device_point(root, o, QSFP_LC_MATE)
    assert math.isclose(p1_pt[0], o_pt[0], abs_tol=0.01)
    assert math.isclose(p1_pt[1], o_pt[1], abs_tol=0.01)
    # SHAPE, not just position: coincident mate points cannot tell a scale
    # on the right axis from one on the wrong axis. Card unrotated, facing
    # up (axis y): width stays true (18.35), height foreshortens by cos 30
    # (8.5 x 0.866025 = 7.3612).
    ow, oh = device_bbox(root, o, QSFP_LC["size"])
    assert math.isclose(ow, 18.35, abs_tol=0.01)
    assert math.isclose(oh, 7.3612, abs_tol=0.01)


def test_a_chained_seat_inherits_the_tilt(tmp_path):
    """A cap mate-to'd to the OPTIC (not the card) - a seat on a seat -
    inherits the tilt the optic itself only just inherited."""
    root = plant_card(tmp_path, occupant=True, chained=True)
    o = next(e for e in root.iter() if (e.get("data-path") or e.get("id") or "").endswith("optic"))
    cap = next(e for e in root.iter() if (e.get("data-path") or e.get("id") or "").endswith("cap"))
    assert cap.get("data-tilt") == "30"
    assert cap.get("data-tilt-on") == o.get("data-tilt-on")
    o_pt = device_point(root, o, QSFP_LC_MATE)
    cap_pt = device_point(root, cap, [2.5, 2.5])
    assert math.isclose(o_pt[0], cap_pt[0], abs_tol=0.01)
    assert math.isclose(o_pt[1], cap_pt[1], abs_tol=0.01)


def test_a_card_rotated_90_still_seats_its_occupant_on_the_facet(tmp_path):
    """The host card itself at rotate: 90. p1 (nested inside the card's own
    rotated group, no rotate of its own) is turned by the CARD from
    outside its own transform, so its foreshortening lands on device-x
    (R90.Sy = Sx.R90). The optic is a top-level seat: it inherits rotate:
    90 as its OWN `rotate`, baked into the SAME transform string as its
    scale, in the OPPOSITE order (rotate first, then scale) - so its scale
    has to swap to the OTHER local axis to still foreshorten the same
    PHYSICAL dimension p1 does. This fails if render.py forgets that swap,
    even though the two mate points can still coincide with the scale on
    the wrong axis - only the drawn shape gives it away."""
    root = plant_card(tmp_path, occupant=True, card_rotate=90)
    o = next(e for e in root.iter() if (e.get("data-path") or e.get("id") or "").endswith("optic"))
    assert o.get("data-tilt") == "30"
    p1 = by_id(root, "--p1")
    p1_pt = device_point(root, p1, QSFP28_MATE)
    o_pt = device_point(root, o, QSFP_LC_MATE)
    assert math.isclose(p1_pt[0], o_pt[0], abs_tol=0.01)
    assert math.isclose(p1_pt[1], o_pt[1], abs_tol=0.01)
    # p1 itself: true width foreshortens to 8.79 (20 x cos 30), true height
    # 10.15 stays - both swapped into device space by the card's own
    # rotate: 8.79 wide, 20.0 tall.
    pw, ph = device_bbox(root, p1, {"w": 20.0, "h": 10.15})
    assert math.isclose(pw, 8.7913, abs_tol=0.01)
    assert math.isclose(ph, 20.0, abs_tol=0.01)
    # the optic: true width 18.35 stays, true height 8.5 foreshortens to
    # 7.3612 - the SAME physical dimension p1's foreshortens, even though
    # the optic's own local scale axis has to swap (facing "up" -> "left")
    # to land there once ITS OWN rotate is baked into the same string.
    ow, oh = device_bbox(root, o, QSFP_LC["size"])
    assert math.isclose(ow, 7.3612, abs_tol=0.01)
    assert math.isclose(oh, 18.35, abs_tol=0.01)


def plant_two_facet_card(tmp, chained=False):
    """A card with TWO facets, seated in a bay, with an optic seated via
    `occupants:` into the SECOND one - the ordinary path for a multi-cage
    card, and the one `_seat_nested_occupants` (not the device-level
    `mate-to` loop) resolves. `chained=True` seats a SECOND occupant, a cap,
    onto the optic itself - a boot on a plug, entirely within the nested
    path."""
    lib = tmp / "lib"
    if chained:
        cd = lib / "components/acme/cap/v1"
        (cd / "skins").mkdir(parents=True)
        (cd / "contract.yaml").write_text(yaml.safe_dump({
            "format": 1, "kind": "component", "name": "cap", "version": "1.0.0",
            "class": "accessory", "size": {"w": 5.0, "h": 5.0},
            "connection-points": {"mate": {"at": [2.5, 2.5], "direction": "front"}},
            "skins": ["default"]}))
        (cd / "skins/default.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="5mm" height="5mm" '
            'viewBox="0 0 5 5"><rect width="5" height="5" fill="#333"/></svg>')
    d = lib / "components/acme/dual-facet-card/v1"
    (d / "skins").mkdir(parents=True)
    (d / "contract.yaml").write_text(yaml.safe_dump({
        "format": 1, "kind": "module", "name": "dual-facet-card", "version": "1.0.0",
        "class": "line-card", "behaviour": "fills", "size": {"w": 25.0, "h": 100.0},
        "elements": {"face": {"at": [0, 0], "size": [25, 100], "class": "panel"},
                     "housing-1": {"at": [0.0, 10.0], "size": [25.0, 30.0], "class": "panel"},
                     "housing-2": {"at": [0.0, 60.0], "size": [25.0, 30.0], "class": "panel"}},
        "relief": {"features": [
            {"node": "housing-1", "facet": {"deg": 20, "facing": "up"},
             "confidence": "drawing", "source": "fixture"},
            {"node": "housing-2", "facet": {"deg": 25, "facing": "up"},
             "confidence": "drawing", "source": "fixture"}]},
        "parts": [
            {"ref": "std/qsfp28@1", "id": "p1", "at": [2.5, 15.0], "on": "housing-1"},
            {"ref": "std/qsfp28@1", "id": "p2", "at": [2.5, 65.0], "on": "housing-2"}],
        "skins": ["default"]}))
    (d / "skins/default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="25mm" height="100mm" viewBox="0 0 25 100">'
        '<rect id="face" width="25" height="100" fill="#ccc"/>'
        '<rect id="housing-1" x="0" y="10" width="25" height="30" fill="#999"/>'
        '<rect id="housing-2" x="0" y="60" width="25" height="30" fill="#999"/></svg>')
    dev = tmp / "device.yaml"
    occupants = {"slot/p2": "generic/qsfp-lc@1"}
    if chained:
        occupants["slot/p2-occupant"] = "acme/cap@1"
    device = {
        "format": 1, "kind": "device", "name": "dual-dev", "version": "0.1.0",
        "maturity": "draft", "manufacturer": "Acme", "model": "T", "profile": "networking",
        "chassis": {"width": 25, "height": 100, "depth": 200},
        "views": {"front": {"size": {"w": 25, "h": 100},
                            "components": {"bays": [
                                {"id": "slot", "at": [0, 0], "size": {"w": 25.0, "h": 100.0},
                                 "accepts": ["acme/dual-facet-card@1"],
                                 "default": "acme/dual-facet-card@1"}]}}},
        "configurations": {"default": {"kind": "base", "default": True,
                                       "occupants": occupants}},
    }
    dev.write_text(yaml.safe_dump(device, sort_keys=False))
    out = tmp / "o"
    out.mkdir()
    r = subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                        "--library", str(lib), "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return ET.parse(out / "dual-dev.front.svg").getroot()


def test_an_occupant_seated_via_occupants_inherits_the_second_facet(tmp_path):
    root = plant_two_facet_card(tmp_path)
    o = by_id(root, "--p2-occupant")
    assert o.get("data-tilt") == "25" and o.get("data-tilt-facing") == "up"
    assert o.get("data-tilt-on").endswith("--housing-2")
    p2 = by_id(root, "--p2")
    p2_pt = device_point(root, p2, QSFP28_MATE)
    o_pt = device_point(root, o, QSFP_LC_MATE)
    assert math.isclose(p2_pt[0], o_pt[0], abs_tol=0.01)
    assert math.isclose(p2_pt[1], o_pt[1], abs_tol=0.01)
    # THE FIRST facet's cage (20 deg) carries no occupant - a cheap check
    # that the fixture seated into the SECOND entry specifically, not
    # whichever one happened to be present. p1 itself still carries its
    # OWN tilt (it sits `on` housing-1 too), just a different `deg`.
    p1 = by_id(root, "--p1")
    assert p1.get("data-tilt") == "20"
    ids = {e.get("id") for e in root.iter() if e.get("id")}
    assert not any(i.endswith("p1-occupant") for i in ids)


def test_a_nested_chained_seat_inherits_the_tilt(tmp_path):
    """A boot on an optic that is itself seated in a card's own tilted
    cage - entirely within `_seat_nested_occupants`, no device-level
    `mate-to` involved."""
    root = plant_two_facet_card(tmp_path, chained=True)
    o = by_id(root, "--p2-occupant")
    cap = by_id(root, "--p2-occupant-occupant")
    assert cap.get("data-tilt") == "25"
    assert cap.get("data-tilt-on") == o.get("data-tilt-on")
    o_pt = device_point(root, o, QSFP_LC_MATE)
    cap_pt = device_point(root, cap, [2.5, 2.5])
    assert math.isclose(o_pt[0], cap_pt[0], abs_tol=0.01)
    assert math.isclose(o_pt[1], cap_pt[1], abs_tol=0.01)


def test_a_facet_feature_shifts_with_an_inset(tmp_path):
    """A facet on a part composed WITH A LIFT - the derived `out` and
    profile must move by the same amount `_inset_feature` moves a
    hand-written one by: a derived number is exactly as "declared" as a
    hand-written `out`."""
    lib = tmp_path / "lib"
    riser_dir = lib / "components/acme/riser/v1"
    (riser_dir / "skins").mkdir(parents=True)
    (riser_dir / "contract.yaml").write_text(yaml.safe_dump({
        "format": 1, "kind": "component", "name": "riser", "version": "1.0.0",
        "class": "bracket", "size": {"w": 25.0, "h": 30.0},
        "elements": {"plate": {"at": [0, 0], "size": [25, 30], "class": "panel"}},
        "relief": {"features": [{"node": "plate", "facet": {"deg": 30, "facing": "up"},
                                 "confidence": "drawing", "source": "fixture"}]},
        "skins": ["default"]}))
    (riser_dir / "skins/default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="25mm" height="30mm" viewBox="0 0 25 30">'
        '<rect id="plate" width="25" height="30" fill="#999"/></svg>')
    card_dir = lib / "components/acme/riser-card/v1"
    (card_dir / "skins").mkdir(parents=True)
    (card_dir / "contract.yaml").write_text(yaml.safe_dump({
        "format": 1, "kind": "module", "name": "riser-card", "version": "1.0.0",
        "class": "line-card", "behaviour": "fills", "size": {"w": 25.0, "h": 100.0},
        "elements": {"face": {"at": [0, 0], "size": [25, 100], "class": "panel"}},
        "parts": [{"ref": "acme/riser@1", "id": "riser", "at": [0.0, 40.0], "lift": 10.0}],
        "skins": ["default"]}))
    (card_dir / "skins/default.svg").write_text(SKIN)
    dev = tmp_path / "device.yaml"
    placements = [{"ref": "acme/riser-card@1", "id": "card", "at": [0, 0]}]
    components = {"placements": placements}
    front = {"size": {"w": 25, "h": 100}, "components": components}
    device = {
        "format": 1, "kind": "device", "name": "inset-dev", "version": "0.1.0",
        "maturity": "draft", "manufacturer": "Acme", "model": "T", "profile": "networking",
        "chassis": {"width": 25, "height": 100, "depth": 200},
        "views": {"front": front},
    }
    dev.write_text(yaml.safe_dump(device, sort_keys=False))
    out = tmp_path / "o"
    out.mkdir()
    r = subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                        "--library", str(lib), "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    root = ET.parse(out / "inset-dev.front.svg").getroot()
    plate = by_id(root, "--plate")
    assert plate.get("data-z-out") == "27.3205"        # 30 x tan 30 + the 10mm lift
    assert plate.get("data-z-profile-y") == "0:10,30:27.3205"

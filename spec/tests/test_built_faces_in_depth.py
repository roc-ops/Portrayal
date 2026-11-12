"""Every built face of a rack-side or zero-U part stands inside the part.

The solids test (test_rack_side_solids_in_depth.py) reads the boxes rack.json
derives from the default configuration. A frame drawn as a well in front of its
part shows there, but a door or a guide that rack.json does not turn into a box
(it is `mounted`, or inside a duct) does not. This reads the faces themselves.

Each compiled face in library/dist (`<name>.<config>.<view>.svg`, or the shared
file the configs index names for it) is walked for every element that carries
`data-z-out`. relief.js reads `data-z-out` as an absolute distance out from the
face and sums `data-z-lift` up the ancestor chain, so an element covers, along
the face's normal, from -out to -(summed lift) back from that face: the same
frame as rack.json (rack_solids.py), where a part `n` deep has every element
between 0 and `n`. `n` is the depth for the front and rear views, the height
for top and bottom and the width for left and right: the part's extent along
that face's normal, from the configs index. An element that covers any of
-inf..0 or n..inf stands outside the part by the distance it covers there.

Parts that stand a control proud of a face, as a breaker, a button or an LED
lens does, are listed in PROUD by name with the distance, which the sweep holds
to: a part not listed fails; a listed part that no longer stands outside fails
(delete its entry); a listed part that stands further out than its entry fails.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from portrayal.rack_index import face_file

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
# the faces' numbers are written to two decimals
TOL = 0.01
VIEWS = {"front": "d", "rear": "d", "top": "h", "bottom": "h", "left": "w", "right": "w"}

# part -> (the most it stands outside any face, in mm; why that is not a defect)
_BUTTON_REAR = ("the plate of its button-1 stands 3 mm proud of the rear face, a control on a face and not a frame, "
                "door or guide stood in front of the part; whether the stated depth includes it is not checked")
_LED = ("the lens of one LED stands 0.3 mm proud of the front face, drawn so that it relieves in the 3D view; "
        "it is not a frame, door or guide stood in front of the part")
_BUTTON_FRONT = ("the cap of its button-up stands 0.5 mm proud of the front face, a control on a face and not a "
                 "frame, door or guide stood in front of the part; whether the stated depth includes it is not checked")
PROUD = {
    **{f"dk-7979-{n}": (3.0, _BUTTON_REAR)
       for n in ("110", "130", "132", "133", "135", "136", "138", "140", "142", "175")},
    **{n: (0.3, _LED) for n in ("en2951", "en6952", "pdumv20hvnetlx", "pro4x-smart-4c16a",
                                "pro4x-smart-pops-4t16a", "pro4x-switched-4f16a",
                                "pro4x-switched-pops-4g16a", "px3-1045")},
    **{f"px4-{n}-e7m26v2": (0.5, _BUTTON_FRONT) for n in ("132awa", "1551wa", "532awa", "5551wa")},
    "epbz77": (3.2, "the nut of its ground stud stands 3.2 mm proud of the front face, a fastener on a face and not "
                    "a frame, door or guide stood in front of the part; whether the stated depth includes it is not checked"),
    "pdumv30": (2.5, "the nut of its breaker-2 stands 2.5 mm proud of the front face, a fastener on a face and not a "
                     "frame, door or guide stood in front of the part; whether the stated depth includes it is not checked"),
    "px2-2475": (6.73, "the opening of its console port stands 6.73 mm proud of the front face, a connector on a face "
                       "and not a frame, door or guide stood in front of the part; whether the depth includes it is not checked"),
    "evma8365x": (7.5, "the plates of its breakers stand 7.5 mm proud of the front face, controls on a face and not a "
                       "frame, door or guide stood in front of the part; whether the stated depth includes them is not checked"),
    "evmi2130x": (7.5, "the plates of its breakers stand 7.5 mm proud of the front face, controls on a face and not a "
                       "frame, door or guide stood in front of the part; whether the stated depth includes them is not checked"),
}


def element_spans(root):
    """(id, lo, hi) for every element with a numeric data-z-out: the span it
    covers back from the face, -out to -(its lift and its ancestors' lifts)."""
    parent = {c: p for p in root.iter() for c in p}
    out = []
    for el in root.iter():
        raw = el.get("data-z-out")
        if raw is None:
            continue
        try:
            far = float(raw)
        except ValueError:
            continue
        lift, node = 0.0, el
        while node is not None:
            try:
                lift += float(node.get("data-z-lift") or 0)
            except ValueError:
                pass
            node = parent.get(node)
        out.append((el.get("id"), min(-far, -lift), max(-far, -lift)))
    return out


def outside_by(root, extent):
    """(id, mm) of the element that stands furthest outside 0..extent, or None."""
    worst = None
    for ident, lo, hi in element_spans(root):
        mm = max(-lo, hi - extent, 0.0)
        if mm > TOL and (worst is None or mm > worst[1]):
            worst = (ident, mm)
    return worst


def _svg(body):
    return ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>')


def test_a_frame_stood_in_front_of_its_part_is_outside_it():
    # the shape the solids test caught: a frame 389 deep, out 389, no lift, on a part 392 deep
    frame = _svg('<g id="frame" data-z-out="389"/>')
    assert outside_by(frame, 392) == ("frame", pytest.approx(389))


def test_a_door_or_guide_in_a_group_stood_in_front_is_outside_it():
    # the lift of a group counts for what is inside it: a door 3 thick on a group lifted nowhere
    door = _svg('<g id="door-group"><g id="door" data-z-out="3"/></g>')
    assert outside_by(door, 392) == ("door", pytest.approx(3))
    # a part that reaches past its back face is outside it there
    behind = _svg('<g id="rail" data-z-out="-60" data-z-lift="-30"/>')
    assert outside_by(behind, 45) == ("rail", pytest.approx(15))


def test_an_element_placed_in_a_well_is_inside_the_part():
    # a well 392 deep lifts its group to -392; the frame in it covers 3..392
    well = _svg('<g id="well" data-z-lift="-392"><g id="frame" data-z-out="-3"/></g>')
    assert outside_by(well, 392) is None
    # the same frame with its lift written on itself
    own = _svg('<g id="frame" data-z-out="-3" data-z-lift="-392"/>')
    assert outside_by(own, 392) is None


def _device_faces():
    """(name, {view: extent}, [(config, view, path)]) for every rack-side or zero-U part."""
    devices = json.loads((DIST / "devices.json").read_text())["devices"]
    parts = []
    for d in devices:
        index = DIST / f"{d['name']}.configs.json"
        if not index.is_file():
            continue
        idx = json.loads(index.read_text())
        chassis = idx.get("chassis") or {}
        if not (chassis.get("mount") == "rack-side" or chassis.get("ru") == 0):
            continue
        extents = {v: chassis.get(k) for v, k in VIEWS.items()}
        faces = []
        for cfg in idx.get("configs", []):
            for view in VIEWS:
                path = DIST / face_file(idx, d["name"], cfg["name"], view)
                if path.is_file() and extents[view] is not None:
                    faces.append((cfg["name"], view, path))
        parts.append((d["name"], extents, faces))
    return parts


@pytest.mark.heavy
def test_every_built_face_of_a_rack_side_or_zero_u_part_stands_inside_it():
    assert (DIST / "devices.json").is_file(), "no library/dist/devices.json: run ./build.sh first (the suite reads the build)"
    parts = _device_faces()
    assert len(parts) > 50, "few rack-side or zero-U parts found: the check would be vacuous"
    assert sum(len(faces) for _, _, faces in parts) > 100, "few faces found: the check would be vacuous"
    found = {}
    for name, extents, faces in parts:
        for cfg, view, path in faces:
            hit = outside_by(ET.parse(path).getroot(), extents[view])
            if hit and hit[1] > found.get(name, (None, 0.0, None, None))[1]:
                found[name] = (hit[0], hit[1], f"{cfg}.{view}", extents[view])
    unlisted = {n: f for n, f in found.items() if n not in PROUD}
    assert not unlisted, "\n".join(
        f"{n}: {ident} stands {mm:.2f} mm outside the part on {face} (extent {extent}); "
        "a frame, door or guide drawn in front of its part needs a base well, and a control proud of a face is listed in PROUD"
        for n, (ident, mm, face, extent) in sorted(unlisted.items()))
    stale = sorted(n for n in PROUD if n not in found)
    assert not stale, f"in PROUD but no longer standing outside any face, delete the entry: {stale}"
    further = {n: (found[n][0], found[n][1], found[n][2], PROUD[n][0]) for n in PROUD if found[n][1] > PROUD[n][0] + TOL}
    assert not further, "\n".join(
        f"{n}: {ident} stands {got:.2f} mm outside the part on {face}, its PROUD entry says {said}"
        for n, (ident, got, face, said) in sorted(further.items()))


def test_every_proud_entry_says_why():
    for name, (mm, why) in PROUD.items():
        assert mm > 0, name
        assert len(why) >= 40, f"{name}: the reason is under 40 characters"

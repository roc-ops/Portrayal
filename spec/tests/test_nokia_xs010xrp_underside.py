"""The Nokia XS-010XR-P draws what its product guide's underside figure and side render show.

Figure 5-8 of the product guide draws four slanted slots, three wall-mounting holes and two pegs
on the underside; Figure 5-9 and the data sheet render show a slatted vent field on the short
side at the fibre end. The device states each of them, and states what stays a gap and why.
Figure 5-9 draws two seams across the vented wall, one at each end of the slat field, and none
along its depth, so the left face carries the two end seams and no long seam.
"""
import json
import math
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "nokia" / "xs-010xr-p" / "device.yaml"


def load():
    return yaml.safe_load(DEVICE.read_text())


def decor(face):
    return load()["views"][face]["panel"].get("decor", [])


def cutouts(face):
    return load()["views"][face]["panel"].get("cutouts", [])


def test_four_slanted_slots_are_cut_in_the_underside_at_45_degrees():
    slots = [c for c in cutouts("bottom") if c["id"].startswith("slot-")]
    assert len(slots) == 4
    for slot in slots:
        assert slot["shape"] == "slot" and slot["rotate"] in (-45, -45.0)
        assert slot["size"] == [15.0, 5.5]
        assert slot.get("empty") is True


def test_the_third_wall_mounting_hole_is_cut_in_the_underside():
    holes = {c["id"] for c in cutouts("bottom") if c["id"].startswith("wall-hole-")}
    assert holes == {"wall-hole-3-slot", "wall-hole-3-head"}
    gaps = {g["what"] for g in load()["gaps"]}
    assert "wall-hole-shapes" in gaps, "the first two holes are the shared keyhole, and say so"


def test_two_pegs_stand_on_the_front_margin_of_the_underside():
    pegs = [d for d in decor("bottom") if d.get("kind") == "peg"]
    assert len(pegs) == 2
    for peg in pegs:
        assert peg["size"] == [8.7, 8.7] and peg["rx"] == 4.35
    assert all(not d.get("out") for d in pegs), "no document states how far a peg stands"


def test_the_underside_plate_has_the_corner_radius_the_figure_draws():
    plate = next(d for d in decor("bottom") if d["id"] == "plate")
    assert plate["rx"] == 7.8


def test_the_left_face_has_a_field_of_22_vent_slots():
    slots = [d for d in decor("left") if d.get("kind") == "vent-slot"]
    assert len(slots) == 22
    pitches = {round(b["at"][0] - a["at"][0], 2) for a, b in zip(slots, slots[1:])}
    assert pitches == {4.75}
    assert not [d for d in decor("right") if d.get("kind") == "vent-slot"], "no held picture shows the right side"


def test_the_vented_wall_has_the_two_end_seams_and_no_seam_along_its_depth():
    ids = {d["id"]: d for d in decor("left")}
    assert "seam-upper" not in ids and "seam-lower" not in ids
    assert ids["seam-end-1"]["at"][0] == 19.0 and ids["seam-end-2"]["at"][0] == 122.8
    slats = [d for d in decor("left") if d.get("kind") == "vent-slot"]
    for d in decor("left"):
        if d.get("kind") == "vent-slot":
            continue
        x, y = d["at"]
        w, h = d["size"]
        for s in slats:
            sx, sy = s["at"]
            sw, sh = s["size"]
            crosses = x < sx + sw and sx < x + w and y < sy + sh and sy < y + h
            assert not crosses, f"{d['id']} crosses {s['id']}"
    assert {"seam-upper", "seam-lower"} <= {d["id"] for d in decor("right")}, "the right face keeps its two"
    assert {"seam-upper", "seam-lower"} <= {d["id"] for d in decor("rear")}


def test_the_underside_creases_are_eight_drawn_as_nine_paths():
    paths = {s["id"]: s for s in load()["views"]["bottom"]["silkscreen"] if s["id"].startswith("crease-")}
    assert len(paths) == 9

    def line(s):
        nums = [float(n) for n in s["path"].replace("M", " ").replace("L", " ").split()]
        x, y = s["at"]
        return (x + nums[0], y + nums[1]), (x + nums[2], y + nums[3])

    a, b = line(paths["crease-2"]), line(paths["crease-3"])
    (x0, y0), (x1, y1) = a
    # the broken crease: the second path lies on the line through the first, within 0.2 mm
    for px, py in b:
        distance = abs((x1 - x0) * (y0 - py) - (x0 - px) * (y1 - y0)) / math.hypot(x1 - x0, y1 - y0)
        assert distance < 0.2
    assert len(paths) - 1 == 8
    notes = load()["provenance"]["bottom-layout"]["note"]
    assert "eight creases, nine paths: the one at the case screw is broken round the screw" in " ".join(notes.split())


def test_the_feet_have_the_inner_ring_and_the_housing_has_two_thin_lines():
    ids = {d["id"]: d for d in decor("bottom")}
    for n in (1, 2, 3, 4):
        ring = ids[f"foot-{n}-ring"]
        foot = ids[f"foot-{n}"]
        assert ring["size"] == [10.0, 10.0] and ring["rx"] == 5.0 and "fill" not in ring
        centre = lambda d: (round(d["at"][0] + d["size"][0] / 2, 3), round(d["at"][1] + d["size"][1] / 2, 3))
        assert centre(ring) == centre(foot)
    assert ids["lip"]["at"] == [1.4, 1.4] and ids["lip-2"]["at"] == [2.1, 2.1]
    assert ids["lip"]["rx"] == 17.6 and ids["lip-2"]["rx"] == 16.9


def test_the_third_wall_hole_has_its_recess_and_each_peg_its_crescent():
    silk = {s["id"]: s for s in load()["views"]["bottom"]["silkscreen"]}
    assert "wall-hole-3-recess" in silk
    assert silk["peg-1-crescent"]["at"] == [148.8, 133.0] and silk["peg-2-crescent"]["at"] == [59.3, 133.0]
    for key in ("wall-hole-3-recess", "peg-1-crescent", "peg-2-crescent"):
        assert silk[key]["path"].startswith("M ") and silk[key]["for"] == "chassis"


def test_the_notes_say_what_is_drawn_on_the_vented_wall_and_what_is_not():
    notes = load()["provenance"]["side-layout"]["note"]
    assert "carried round from the back elevation" not in notes
    assert "stay as an estimate" not in notes
    assert "19.0 and 122.8 mm" in notes
    assert "draws no seam along the depth" in notes
    assert "right face keeps the two carried from the rear" in notes


def test_the_provenance_no_longer_says_the_underside_holes_are_not_drawn():
    doc = load()
    assert "NOT DRAWN: four slanted slots" not in doc["provenance"]["bottom-layout"]["note"]
    gaps = {g["what"] for g in doc["gaps"]}
    assert "underside-holes" not in gaps
    assert "side-vents" not in gaps


def test_the_device_validates_against_the_device_schema():
    schema = json.loads((ROOT / "spec" / "schemas" / "device.schema.json").read_text())
    jsonschema.validate(load(), schema)

"""The Nokia XS-010XR-P draws what its product guide's underside figure and side render show.

Figure 5-8 of the product guide draws four slanted slots, three wall-mounting holes and two pegs
on the underside; Figure 5-9 and the data sheet render show a slatted vent field on the short
side at the fibre end. The device states each of them, and states what stays a gap and why.
"""
import json
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


def test_the_provenance_no_longer_says_the_underside_holes_are_not_drawn():
    doc = load()
    assert "NOT DRAWN: four slanted slots" not in doc["provenance"]["bottom-layout"]["note"]
    gaps = {g["what"] for g in doc["gaps"]}
    assert "underside-holes" not in gaps
    assert "side-vents" not in gaps


def test_the_device_validates_against_the_device_schema():
    schema = json.loads((ROOT / "spec" / "schemas" / "device.schema.json").read_text())
    jsonschema.validate(load(), schema)

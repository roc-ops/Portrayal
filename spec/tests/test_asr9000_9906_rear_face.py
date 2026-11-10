"""The rest of the ASR 9906's rear face: vents, power tray, ESD jack, ground pad.

Cisco's stencil master "ASR-9906 Rear" draws, besides the fabric cage, a hexagon vent field at the
lower left and one at the upper right, the power tray's six IEC receptacles, its I2C connector and
the DC output blades below them, an ESD jack, a two-hole ground pad, rack ears and screw heads. The
face draws the vents, the tray plate and the housing's outline, the ESD jack, the pad, the ears and
the screw heads, and says where it read each one. It does not paint a connector: the receptacles,
the I2C connector and the DC input are named gaps.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CHASSIS = ROOT / "library/devices/cisco/asr-9906/device.yaml"


def device():
    return yaml.safe_load(CHASSIS.read_text())


def rear():
    return device()["views"]["rear"]


def decor():
    return rear()["panel"]["decor"]


def box(item):
    (x, y), (w, h) = item["at"], item["size"]
    return x, y, x + w, y + h


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_the_rear_draws_two_air_vent_fields():
    vents = {d["id"]: d for d in decor() if d.get("pattern") == "motif"}
    assert set(vents) == {"rear-vent-lower-left", "rear-vent-upper-right"}
    for d in vents.values():
        assert d["vent"] > 0 and d["pattern-cells"]
        x0, y0, x1, y1 = box(d)
        assert 0 <= x0 and x1 <= 447.0 and 0 <= y0 and y1 <= 619.51
    low, high = vents["rear-vent-lower-left"], vents["rear-vent-upper-right"]
    assert box(low)[0] < 223.5 < box(high)[0]
    centre = lambda d: (box(d)[1] + box(d)[3]) / 2
    assert centre(low) > 619.51 / 2 > centre(high)


def test_the_power_tray_is_drawn_as_a_bare_plate_with_no_connector_painted_on_it():
    plate = next(d for d in decor() if d.get("id") == "rear-power-tray-plate")
    assert box(plate)[2] - box(plate)[0] > 40 and box(plate)[3] - box(plate)[1] > 290
    on_plate = [d for d in decor() if d.get("id") not in ("rear-power-tray-plate", "rear-power-tray-frame")
                and overlaps(box(d), box(plate))]
    assert not on_plate, on_plate


def test_the_dc_housing_keeps_its_outline_and_screws_but_not_the_blade_slot():
    housing = next(d for d in decor() if d.get("id") == "rear-dc-output-housing")
    inside = [d for d in decor() if d.get("id") != "rear-dc-output-housing" and overlaps(box(d), box(housing))]
    assert any(d.get("stroke") and d["size"] == housing["size"] for d in inside)
    assert sum(1 for d in inside if d.get("rx") == d["size"][0] / 2 and d.get("stroke")) == 2
    slots = [d for d in inside if d["size"][1] > 10 and d.get("id") != "rear-power-tray-frame"]
    assert [d for d in slots if d["size"] != housing["size"]] == []


def test_no_receptacle_is_placed_as_a_part_and_the_gaps_say_why():
    refs = [p["ref"] for p in rear()["components"]["placements"]]
    assert not [r for r in refs if "inlet" in r or "c19" in r or "c20" in r or "iec" in r]
    note = device()["provenance"]["rear-power-inlets"]["note"]
    assert "Figure 66" in note and "IEC input" in note
    gaps = {g["what"]: g for g in device()["gaps"]}
    for name in ("rear-power-receptacles", "rear-i2c-connector", "rear-dc-input"):
        assert gaps[name]["scope"] == ["rear"] and gaps[name]["wanted"]


def test_the_esd_jack_sits_in_its_own_cutout_on_the_rear():
    face = rear()
    jack = next(p for p in face["components"]["placements"] if p["id"] == "esd-jack-rear")
    assert jack["ref"] == "common/esd-jack@1" and jack["group"] == "grounding"
    cut = next(c for c in face["panel"]["cutouts"] if c["id"] == "esd-rear")
    cx, cy = cut["at"][0] + cut["size"][0] / 2, cut["at"][1] + cut["size"][1] / 2
    assert abs(jack["at"][0] + 3.0 - cx) < 0.1 and abs(jack["at"][1] + 3.0 - cy) < 0.1
    assert any(s["text"] == "ESD" and s["for"] == "esd-jack-rear" for s in face["silkscreen"])


def test_the_ground_pad_sits_in_its_cutout_and_the_chassis_says_where_the_master_draws_it():
    face = rear()
    pad = next(p for p in face["components"]["placements"] if p["id"] == "ground-pad-rear")
    cut = next(c for c in face["panel"]["cutouts"] if c["id"] == "ground-pad-rear")
    assert pad["at"] == cut["at"]
    note = device()["provenance"]["rear-ground-pad-position"]["note"]
    assert "523.6" in note and "20.2" in note


def test_nothing_drawn_on_the_rear_covers_a_fabric_bay_or_leaves_the_face():
    bays = [box({"at": b["at"], "size": [b["size"]["w"], b["size"]["h"]]}) for b in rear()["components"]["bays"]]
    for d in decor():
        b = box(d)
        assert 0 <= b[0] and b[2] <= 447.0 and 0 <= b[1] and b[3] <= 619.51, d.get("id", d["at"])
        assert not [x for x in bays if overlaps(b, x)], d.get("id", d["at"])


def test_the_chassis_says_where_each_rear_feature_was_read_and_what_is_not_drawn():
    prov = device()["provenance"]
    entry = prov["rear-face"]
    assert entry["confidence"] == "drawing"
    assert "ASR-9906 Rear" in entry["note"] and "NOT DRAWN" in entry["note"]
    assert "20.2" in prov["rear-ground-pad-position"]["note"]


def test_the_ears_are_the_span_the_rear_master_draws():
    ears = device()["chassis"]["ears"]
    assert abs(ears["h"] - 533.7) < 0.1 and abs(ears["y"] - 72.5) < 0.1

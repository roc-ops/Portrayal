"""L34: front and rear occupants of one slot column fit around the midplane.

The first L34 paired a front bay with a rear bay only when both groups were
named `slot`/`slots` and they shared a `rel-pos`. The CH3000 names its rear
groups `back-plates` and `inlet-plates`, so once half-depth modules could seat
in the rear, a full-depth AR3002E (d 330) in front of an NP35 (d 165.1) - 495 mm
in a 337.8 mm chassis - passed unflagged. The pairing is now by the columns two
bays physically share, with the rear face mirrored, and the depths compared are
the occupants of each configuration the device publishes.

The synthetic chassis below is 100 wide and 300 deep with four 25 mm columns.
Seen from behind, column N sits at x = 100 - 25*N, so `rear-4` is drawn at the
LEFT of the rear view and is the same column as `slot-4` at the right of the
front: a rule that forgot to mirror would pair it with `slot-1`.
"""
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint as L


@pytest.fixture
def lib(tmp_path):
    """A library holding three parts: full depth, half depth, and a plate."""
    for name, d in (("full", 280.0), ("half", 150.0), ("plate", 20.0), ("fan", 280.0)):
        f = tmp_path / "components" / "t" / name / "v1" / "contract.yaml"
        f.parent.mkdir(parents=True)
        f.write_text(f"kind: module\nname: {name}\nsize: {{w: 25.0, h: 50.0, d: {d}}}\n")
    return [str(tmp_path)]


def column(bid, x, group, w=25.0, **kw):
    b = {"id": bid, "at": [x, 0.0], "size": {"w": w, "h": 50.0},
         "accepts": ["t/full@1", "t/half@1", "t/plate@1"], "group": group}
    b.update(kw)
    return b


def device(front, rear, configurations=None):
    doc = {"kind": "device", "chassis": {"width": 100.0, "height": 50.0, "depth": 300.0},
           "views": {"front": {"size": {"w": 100.0, "h": 50.0}, "components": {"bays": front}},
                     "rear": {"size": {"w": 100.0, "h": 50.0}, "components": {"bays": rear}}}}
    if configurations is not None:
        doc["configurations"] = configurations
    return doc


def front_slots(**defaults):
    return [column(f"slot-{n}", 25.0 * (n - 1), "psus" if n == 1 else "slots",
                   **({"default": defaults[f"s{n}"]} if f"s{n}" in defaults else {}))
            for n in (1, 2, 3, 4)]


def rear_slots(**defaults):
    return [column(f"rear-{n}", 100.0 - 25.0 * n, "back-plates",
                   **({"default": defaults[f"r{n}"]} if f"r{n}" in defaults else {}))
            for n in (1, 2, 3, 4)]


def run(doc, lib):
    with L.collecting() as found:
        L.lint_device_midplane_depth("t/device.yaml", doc, lib)
    return [w for w in found.warnings + found.errors if "[L34]" in w]


def test_default_build_full_front_and_half_rear_in_one_column_is_caught(lib):
    """Groups `slots` and `back-plates` - the CH3000 shape the old rule skipped."""
    hits = run(device(front_slots(s2="t/full@1"), rear_slots(r2="t/half@1")), lib)
    assert len(hits) == 1, hits
    assert "slot-2" in hits[0] and "rear-2" in hits[0] and "430" in hits[0]


def test_full_front_and_plate_rear_fit(lib):
    assert run(device(front_slots(s2="t/full@1"), rear_slots(r2="t/plate@1")), lib) == []


def test_the_rear_face_is_mirrored(lib):
    """rear-4 is drawn at x 0-25 of the rear view, which is column 4, not 1."""
    assert run(device(front_slots(s1="t/full@1"), rear_slots(r4="t/half@1")), lib) == []
    hits = run(device(front_slots(s4="t/full@1"), rear_slots(r4="t/half@1")), lib)
    assert len(hits) == 1 and "slot-4" in hits[0] and "rear-4" in hits[0], hits


def test_every_configuration_is_checked_not_only_the_default(lib):
    cfgs = {"base": {"kind": "base", "default": True},
            "mixed": {"kind": "example", "bays": {"slot-3": "t/full@1", "rear-3": "t/half@1"}}}
    hits = run(device(front_slots(), rear_slots(), cfgs), lib)
    assert len(hits) == 1, hits
    assert "mixed" in hits[0] and "slot-3" in hits[0] and "rear-3" in hits[0]


def test_a_configuration_emptying_a_bay_clears_its_default(lib):
    cfgs = {"base": {"kind": "base", "default": True, "bays": {"rear-2": ""}}}
    assert run(device(front_slots(s2="t/full@1"), rear_slots(r2="t/half@1"), cfgs), lib) == []


def test_a_double_bay_pairs_with_each_column_it_covers(lib):
    """slot-1-2 spans columns 1 and 2; a half-depth rear-2 collides with it."""
    front = front_slots() + [column("slot-1-2", 0.0, "slots", w=50.0,
                                    default="t/full@1", **{"only-in": ["double"]})]
    cfgs = {"base": {"kind": "base", "default": True},
            "double": {"kind": "example", "bays": {"rear-2": "t/half@1"}}}
    hits = run(device(front, rear_slots(), cfgs), lib)
    assert len(hits) == 1, hits
    assert "double" in hits[0] and "slot-1-2" in hits[0] and "rear-2" in hits[0]


def test_a_rear_quad_bay_pairs_with_the_front_columns_it_covers(lib):
    rear = rear_slots() + [column("rear-1-4", 0.0, "back-plates", w=100.0, default="t/half@1")]
    hits = run(device(front_slots(s3="t/full@1"), rear), lib)
    assert len(hits) == 1 and "slot-3" in hits[0] and "rear-1-4" in hits[0], hits


def test_a_bay_scoped_out_of_the_configuration_seats_nothing(lib):
    front = front_slots() + [column("slot-1-2", 0.0, "slots", w=50.0,
                                    default="t/full@1", **{"only-in": ["double"]})]
    cfgs = {"base": {"kind": "base", "default": True, "bays": {"rear-2": "t/half@1"}},
            "double": {"kind": "example"}}
    assert run(device(front, rear_slots(), cfgs), lib) == []


def test_bays_at_different_heights_do_not_share_a_column(lib):
    """A front fan strip above a rear card is not in the card's column."""
    fan = {"id": "fan", "at": [0.0, 0.0], "size": {"w": 100.0, "h": 10.0},
           "accepts": ["t/fan@1"], "default": "t/fan@1", "group": "cooling"}
    card = {"id": "card", "at": [0.0, 20.0], "size": {"w": 100.0, "h": 30.0},
            "accepts": ["t/half@1"], "default": "t/half@1", "group": "cards"}
    assert run(device([fan], [card]), lib) == []


def test_a_sliver_of_overlap_at_an_edge_is_not_a_shared_column(lib):
    """Bay outlines are drawn to faceplate precision, and a mirrored rear cage a
    few mm off the front one (Casa C40G's fan strip, 5.6 mm) is not a column."""
    fan = {"id": "fan", "at": [80.0, 0.0], "size": {"w": 20.0, "h": 50.0},
           "accepts": ["t/fan@1"], "default": "t/fan@1", "group": "cooling"}
    card = {"id": "card", "at": [0.0, 0.0], "size": {"w": 23.0, "h": 50.0},
            "accepts": ["t/half@1"], "default": "t/half@1", "group": "cards"}
    # card mirrored: x 77-100, which overlaps the fan's 80-100 by 20 of 20 - a column
    assert len(run(device([fan], [card]), lib)) == 1
    card["size"]["w"] = 24.0
    card["at"] = [18.0, 0.0]          # mirrored: x 58-82, 2 mm into the fan
    assert run(device([fan], [card]), lib) == []


def test_one_warning_per_pair_of_parts(lib):
    """Two columns seating the same two parts are one finding, not two."""
    hits = run(device(front_slots(s2="t/full@1", s3="t/full@1"),
                      rear_slots(r2="t/half@1", r3="t/half@1")), lib)
    assert len(hits) == 1, hits


def test_the_real_ch3000_configurations_stay_clean():
    path = ROOT / "library/devices/commscope/ch3000/device.yaml"
    doc = L.load_yaml(path)
    assert len(doc.get("configurations") or {}) >= 5      # guard: it has builds to check
    assert run(doc, [str(ROOT / "library")]) == []


def test_the_real_ch3000_seats_front_and_rear_in_shared_columns():
    """Guard the guard: the clean result above means something only if the rule
    pairs CH3000 bays at all. Seat a full-depth receiver in front of a rear bay
    and give the rear bay the depth of a front module: that must be caught."""
    path = ROOT / "library/devices/commscope/ch3000/device.yaml"
    doc = L.load_yaml(path)
    for b in doc["views"]["rear"]["components"]["bays"]:
        if b["id"] == "rear-3":
            b["accepts"] = b["accepts"] + ["commscope/ar3002e@1"]
    doc["configurations"]["ar3002e-x14"].setdefault("bays", {})["rear-3"] = "commscope/ar3002e@1"
    hits = run(doc, [str(ROOT / "library")])
    assert len(hits) == 1, hits
    assert "ar3002e-x14" in hits[0] and "slot-3" in hits[0] and "rear-3" in hits[0]

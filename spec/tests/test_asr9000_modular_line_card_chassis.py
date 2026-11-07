"""The ASR 9000 400G and 200G modular line cards fit seven chassis.

Cisco data sheet c78-735809 says so twice: p4, "Features and benefits", and p6,
Table 2, "Chassis compatibility", with a per-chassis maximum card count on p7.
The library seated the four carriers on the ASR 9010 only. These tests hold the
other six chassis to the sheet: every line card slot takes the four carriers, no
slot that holds only RSPs does, and the slot counts agree with Table 2. The
MOD80 and MOD160 are not in that sheet and stay where they were.
"""
import math
import pathlib

import pytest

from portrayal import libwalk
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

CARRIERS = {"cisco/a9k-mod400-se@2", "cisco/a9k-mod400-tr@2",
            "cisco/a9k-mod200-se@2", "cisco/a9k-mod200-tr@2"}
NOT_COVERED = {"cisco/a9k-mod80-se@2", "cisco/a9k-mod80-tr@2",
               "cisco/a9k-mod160-se@2", "cisco/a9k-mod160-tr@2"}
# Table 2, "Card density": the most modular line cards each chassis takes
MAX_CARDS = {"asr-9922": 20, "asr-9912": 10, "asr-9910": 8, "asr-9906": 4,
             "asr-9904": 2, "asr-9010": 8, "asr-9006": 4}
SUPERVISOR_SLOTS = {"asr-9006": 2, "asr-9904": 2, "asr-9906": 2, "asr-9910": 2}
GAINED = sorted(set(MAX_CARDS) - {"asr-9010"})


def _bays(chassis):
    dev = load_yaml(LIB / "devices/cisco" / chassis / "device.yaml")
    return [bay for view in dev["views"].values()
            for bay in (view.get("components") or {}).get("bays", [])]


def _slots(chassis):
    """(line card slots, other slots) of a chassis: a slot is a line card slot
    when it accepts a part whose contract class is line-card."""
    line, other = [], []
    for bay in _bays(chassis):
        if bay.get("group") != "slots":
            continue
        classes = {(libwalk.load_contract(ref, [LIB]) or {}).get("class")
                   for ref in bay["accepts"]}
        (line if "line-card" in classes else other).append(bay)
    return line, other


@pytest.mark.parametrize("chassis", sorted(MAX_CARDS))
def test_every_line_card_slot_takes_the_four_carriers(chassis):
    line, _ = _slots(chassis)
    missing = {b["id"]: sorted(CARRIERS - set(b["accepts"])) for b in line
               if CARRIERS - set(b["accepts"])}
    assert missing == {}


@pytest.mark.parametrize("chassis", sorted(MAX_CARDS))
def test_the_line_card_slot_count_is_table_2s_maximum(chassis):
    line, _ = _slots(chassis)
    assert len(line) == MAX_CARDS[chassis]


@pytest.mark.parametrize("chassis", GAINED)
def test_only_line_card_slots_take_a_carrier(chassis):
    line, other = _slots(chassis)
    # these chassis put an RSP in a slot of the line card size; the others
    # keep their RPs outside the slot group
    assert len(other) == SUPERVISOR_SLOTS.get(chassis, 0)
    takers = {b["id"] for b in _bays(chassis) if CARRIERS & set(b["accepts"])}
    assert takers == {b["id"] for b in line}


def _rotated_line_slots(chassis):
    """The line card slots a chassis draws with the card turned."""
    line, _ = _slots(chassis)
    return [b["id"] for b in line if b.get("rotate")]


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _device_point(transform, x, y):
    """Where `translate(a,b) rotate(r) translate(c,d)` sends a point."""
    import re
    nums =[[float(n) for n in re.split(r"[ ,]+", args.strip())]
            for _, args in re.findall(r"(\w+)\(([^)]*)\)", transform)]
    (a, b), (r,), (c, d) = nums
    x, y = x + c, y + d
    t = math.radians(r)
    return (a + x * math.cos(t) - y * math.sin(t),
            b + x * math.sin(t) + y * math.cos(t))


def _faceplate(chassis, slot, ref):
    """What a part seated in `slot` draws, in device millimetres: the plate,
    the two ears (the grey tabs at the ends) and the two screw heads."""
    from xml.etree import ElementTree as ET
    from portrayal import render
    dev = load_yaml(LIB / "devices/cisco" / chassis / "device.yaml")
    out = render.render_view(dev, "front", dev["views"]["front"],
                             render.Library([str(LIB)]),
                             config={"bays": {slot: ref}})
    root = ET.fromstring(out) if isinstance(out, str) else out
    seat = next(e for e in root.iter()
                if e.get("data-path") == f"{slot}/module")
    tf = seat.get("transform")

    def box(e):
        x, y = float(e.get("x")), float(e.get("y"))
        w, h = float(e.get("width")), float(e.get("height"))
        pts = [_device_point(tf, px, py)
               for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return tuple(round(v, 2) for v in (min(xs), min(ys), max(xs), max(ys)))

    kids, walk = [], list(seat)
    while walk:
        e = walk.pop()
        if e.get("data-class") != "bay":  # an MPA in a bay has a frame of its own
            kids.append(e)
            walk.extend(e)
    plate = next(e for e in kids if (e.get("id") or "").endswith("--plate"))
    at_end = lambda v: float(v) < 20 or float(v) > 370
    ears = [e for e in kids if _local(e.tag) == "rect"
            and float(e.get("width", 0)) < 15 and float(e.get("rx", 0)) >= 1.0
            and at_end(e.get("y"))]
    screws = [_device_point(tf, float(e.get("cx")), float(e.get("cy")))
              for e in kids if _local(e.tag) == "circle"
              and float(e.get("r")) > 3.0 and at_end(e.get("cy"))]
    bars = [e for e in kids if e.get("fill") == "#2e7489"]
    return {"plate": box(plate), "ears": sorted(box(e) for e in ears),
            "screws": sorted((round(x, 2), round(y, 2)) for x, y in screws),
            "bars": [box(e) for e in bars]}


ROTATED = [(c, s) for c in sorted(MAX_CARDS) for s in _rotated_line_slots(c)]


def test_there_are_rotated_chassis_to_check():
    assert {c for c, _ in ROTATED} >= {"asr-9006", "asr-9904"}


@pytest.mark.parametrize("ref", ["cisco/a9k-mod400-se@2", "cisco/a9k-mod400-tr@2"])
@pytest.mark.parametrize("chassis,slot", ROTATED)
def test_a_seated_mod400_has_its_ears_where_the_cover_has_them(chassis, slot, ref):
    """In a slot drawn turned, the card's ejector ears, screws and plate sit
    on the cover's: the covers above and below it are the ruler, and a card
    drawn a few millimetres along its length stands out of the row."""
    card = _faceplate(chassis, slot, ref)
    cover = _faceplate(chassis, slot, "cisco/a9k-slot-cover@1")
    assert card["ears"] == cover["ears"]
    assert card["screws"] == cover["screws"]
    assert card["plate"] == cover["plate"]


@pytest.mark.parametrize("chassis,slot", ROTATED)
def test_a_seated_mod400_ear_does_not_touch_the_status_bar(chassis, slot):
    card = _faceplate(chassis, slot, "cisco/a9k-mod400-se@2")
    (bar,) = card["bars"]
    for ear in card["ears"]:
        apart = (ear[0] >= bar[2] or bar[0] >= ear[2]
                 or ear[1] >= bar[3] or bar[1] >= ear[3])
        assert apart and (max(ear[0] - bar[2], bar[0] - ear[2],
                              ear[1] - bar[3], bar[1] - ear[3]) > 0.5), (ear, bar)


CARRIER_SKINS = ["cisco/a9k-mod400-se@2", "cisco/a9k-mod400-tr@2",
                 "cisco/a9k-mod200-se@2", "cisco/a9k-mod200-tr@2"]


def _drawn(chassis, slot, ref):
    """Every box the part seated in `slot` draws, in device millimetres, as
    (kind, id-or-text, (x0, y0, x1, y1)), read from the rendered SVG.
    A text's box is estimated from its font size (0.7 em a character, wide
    on purpose), turned by its own `rotate` and then by the seat's."""
    import re
    from xml.etree import ElementTree as ET
    from portrayal import render
    dev = load_yaml(LIB / "devices/cisco" / chassis / "device.yaml")
    out = render.render_view(dev, "front", dev["views"]["front"],
                             render.Library([str(LIB)]),
                             config={"bays": {slot: ref}})
    root = ET.fromstring(out) if isinstance(out, str) else out
    seat = next(e for e in root.iter() if e.get("data-path") == f"{slot}/module")
    tf = seat.get("transform")
    boxes = []

    def add(kind, name, pts):
        pts = [_device_point(tf, px, py) for px, py in pts]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        boxes.append((kind, name, tuple(round(v, 3) for v in
                                        (min(xs), min(ys), max(xs), max(ys)))))

    def corners(x, y, w, h):
        return ((x, y), (x + w, y), (x, y + h), (x + w, y + h))

    walk = list(seat)
    while walk:
        e = walk.pop()
        tag = _local(e.tag)
        if e.get("data-class") == "bay":
            # an MPA in a bay has a frame of its own: take only the opening
            for o in e:
                if (o.get("id") or "").endswith("--opening"):
                    walk.append(o)
            continue
        walk.extend(e)
        if tag == "rect":
            x, y = float(e.get("x")), float(e.get("y"))
            add("rect", e.get("id") or e.get("fill"),
                corners(x, y, float(e.get("width")), float(e.get("height"))))
        elif tag == "circle":
            cx, cy, r = (float(e.get(k)) for k in ("cx", "cy", "r"))
            add("circle", e.get("id") or e.get("fill"),
                corners(cx - r, cy - r, 2 * r, 2 * r))
        elif tag == "text" and (e.text or "").strip():
            x, y = float(e.get("x")), float(e.get("y"))
            size = float(e.get("font-size"))
            w = 0.7 * size * len(e.text.strip())
            x0 = x - w / 2 if e.get("text-anchor") == "middle" else x
            pts = corners(x0, y - 0.9 * size, w, 1.2 * size)
            m = re.match(r"rotate\(([-\d.]+) ([-\d.]+) ([-\d.]+)\)",
                         e.get("transform") or "")
            if m:
                a, px, py = (float(v) for v in m.groups())
                c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
                pts = [(px + (u - px) * c - (v - py) * s,
                        py + (u - px) * s + (v - py) * c) for u, v in pts]
            add("text", e.text.strip(), pts)
    return boxes


def _union(boxes):
    return (min(b[2][0] for b in boxes), min(b[2][1] for b in boxes),
            max(b[2][2] for b in boxes), max(b[2][3] for b in boxes))


def _gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy)


@pytest.mark.parametrize("ref", CARRIER_SKINS)
@pytest.mark.parametrize("chassis,slot", ROTATED)
def test_a_seated_carrier_draws_the_covers_extent(chassis, slot, ref):
    """Everything the card draws - plate, recess, bays, label, STATUS bar and
    text, ears, screws - spans the slot as the cover does: the union box is
    the cover's to 0.01 mm along the card's length and across its width."""
    card = _union(_drawn(chassis, slot, ref))
    cover = _union(_drawn(chassis, slot, "cisco/a9k-slot-cover@1"))
    assert card == pytest.approx(cover, abs=0.01)


@pytest.mark.parametrize("ref", CARRIER_SKINS)
@pytest.mark.parametrize("chassis,slot", ROTATED)
def test_a_seated_carrier_recess_runs_edge_to_edge_like_the_cover(chassis, slot, ref):
    """The recessed field the bays are cut into is what a person reads as the
    card: it runs the cover plate's whole length, not 14 mm short at each end."""
    card = _drawn(chassis, slot, ref)
    cover = _drawn(chassis, slot, "cisco/a9k-slot-cover@1")
    plate = next(b[2] for b in cover if str(b[1]).endswith("--plate"))
    # the recess is the one card rect that is neither the plate nor an ear/bar
    recess = next(b[2] for b in card if b[0] == "rect" and b[1] == "#dcdee0"
                  and max(b[2][2] - b[2][0], b[2][3] - b[2][1]) > 300)
    along = (0, 2) if plate[2] - plate[0] > plate[3] - plate[1] else (1, 3)
    assert recess[along[0]] == pytest.approx(plate[along[0]], abs=0.01)
    assert recess[along[1]] == pytest.approx(plate[along[1]], abs=0.01)


@pytest.mark.parametrize("ref", CARRIER_SKINS)
@pytest.mark.parametrize("chassis,slot", ROTATED)
def test_a_seated_carrier_draws_nothing_near_its_ears(chassis, slot, ref):
    """STATUS (bar, lamp and text), the label and the 0 and 1 stand at least
    1.5 mm clear of both ejector ears, and every legend is inside the plate."""
    card = _drawn(chassis, slot, ref)
    plate = next(b[2] for b in _drawn(chassis, slot, "cisco/a9k-slot-cover@1")
                 if str(b[1]).endswith("--plate"))
    ears = [b[2] for b in card if b[0] == "rect" and b[1] == "#b8bdc2"
            or b[0] == "rect" and b[1] == "#bfbfbf"]
    assert len(ears) == 2
    legends = [b for b in card if b[0] == "text"
               or (b[0] == "rect" and b[1] in ("#2e7489", "#ffef5c"))
               or (b[0] == "circle" and b[1] == f"{slot}--module--status")]
    assert {b[1] for b in legends} >= {"STATUS", "0", "1", "#2e7489", "#ffef5c"}
    for kind, name, box in legends:
        for ear in ears:
            assert _gap(box, ear) >= 1.5, (name, box, ear)
        if kind == "text":
            assert plate[0] <= box[0] and box[2] <= plate[2], (name, box, plate)
            assert plate[1] <= box[1] and box[3] <= plate[3], (name, box, plate)


@pytest.mark.parametrize("chassis", GAINED)
def test_the_mod80_and_mod160_are_not_added(chassis):
    seated = {ref for bay in _bays(chassis) for ref in bay["accepts"]}
    assert seated & NOT_COVERED == set()

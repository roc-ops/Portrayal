"""The ASR 9006's right-side air filter is a bay that takes a part, not an opening with nothing in it.

Cisco ASR 9000 Series Aggregation Services Router Hardware Installation Guide, Table 17 "Air Filter Locations" puts the ASR 9006's
filter "along the right side of the chassis ... accessible from the rear", and Figure 207 shows it withdrawn with its thumb screw.
Cisco ASR 9000 Series Aggregation Services Routers Data Sheet lists it as "Cisco ASR 9006 fan filter, 1 per chassis",
ASR-9006-FILTER. No held page dimensions it, so the opening keeps the size the chassis already drew and the part says so.

These read the library's own files. They read no library/dist and render nothing.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
REF = "cisco/asr-9006-filter@1"
CUTOUT = "air-filter-opening"


def device():
    return yaml.safe_load((LIB / "devices/cisco/asr-9006/device.yaml").read_text())


def contract():
    return yaml.safe_load((LIB / "components/cisco/asr-9006-filter/v1/contract.yaml").read_text())


def box(item):
    w, h = item["size"]["w"], item["size"]["h"]
    return (item["at"][0], item["at"][1], item["at"][0] + w, item["at"][1] + h)


def cutout_box(cutout):
    w, h = cutout["size"]
    return (cutout["at"][0], cutout["at"][1], cutout["at"][0] + w, cutout["at"][1] + h)


def overlap(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    return ix * iy if ix > 0 and iy > 0 else 0.0


def test_the_opening_is_seated_by_a_bay_that_accepts_the_filter():
    right = device()["views"]["right"]
    cutout = next(c for c in right["panel"]["cutouts"] if c["id"] == CUTOUT)
    bays = [b for b in right["components"]["bays"] if REF in b["accepts"]]
    assert len(bays) == 1, "exactly one right-side bay takes the filter"
    bay = bays[0]
    assert bay["default"] == REF
    area = (cutout_box(cutout)[2] - cutout_box(cutout)[0]) * (cutout_box(cutout)[3] - cutout_box(cutout)[1])
    assert overlap(box(bay), cutout_box(cutout)) / area >= 0.5, "the bay sits over the opening it fills"


def test_every_hole_on_the_right_face_has_something_in_it():
    right = device()["views"]["right"]
    items = list(right["components"].get("placements", [])) + list(right["components"].get("bays", []))
    ids = {i["id"] for i in items}
    for cutout in right["panel"]["cutouts"]:
        if cutout["id"] in ids:
            continue
        sized = [box(i) for i in right["components"]["bays"]]
        covered = sum(overlap(cutout_box(cutout), b) for b in sized)
        cb = cutout_box(cutout)
        assert covered / ((cb[2] - cb[0]) * (cb[3] - cb[1])) >= 0.5, f"cutout {cutout['id']} has nothing in it"


def test_the_part_carries_the_printed_part_number_and_declares_its_size():
    part = contract()
    assert part["name"] == "asr-9006-filter"
    assert part["class"] == "filter"
    assert part["attrs"]["part-number"] == "ASR-9006-FILTER"
    right = device()["views"]["right"]
    cutout = next(c for c in right["panel"]["cutouts"] if c["id"] == CUTOUT)
    assert [part["size"]["w"], part["size"]["h"]] == cutout["size"]
    assert part["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert "d" not in part["size"], "no document gives the filter's depth"


def test_the_position_gap_stays_open_until_a_drawing_dimensions_the_filter():
    gaps = {g["what"]: g for g in device()["gaps"]}
    assert "air-filter-position" in gaps
    assert gaps["air-filter-position"]["reason"] == "needs-drawing"

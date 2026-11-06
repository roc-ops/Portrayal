"""Edgecore fronts reserve the printed mark as a `logo-zone` region and draw nothing.

Each face below prints the maker's boxed logotype. Its place is a region on the
front view (never a drawn box or mark), measured from a held picture of the
face. A face whose picture is not square-on, or whose device another change is
editing, has no region yet and is listed so a later change sees it.
"""
import pathlib

import yaml

from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]
EDGECORE = ROOT / "library" / "devices" / "edgecore"

# device -> (at, size) in millimetres on the front view
ZONES = {
    "agr560": ((411.0, 18.3), (24.5, 4.9)),
    "ais800-64d": ((411.2, 2.3), (25.0, 4.5)),
    "ais800-64o": ((411.2, 2.6), (25.0, 4.5)),
    "as7946-30xb": ((410.0, 69.4), (25.8, 4.8)),
    "as7946-74xksb": ((409.3, 65.4), (25.9, 4.7)),
    "cor550": ((4.6, 77.9), (30.9, 5.4)),
    "cor580": ((30.2, 32.2), (20.7, 4.1)),
    "csr200": ((406.0, 3.9), (29.0, 5.2)),
    "csr430": ((183.3, 34.6), (25.4, 4.5)),
    "csr440": ((256.9, 35.2), (20.7, 3.7)),
    "eps112": ((6.1, 7.3), (36.0, 6.3)),
    "exp100-32x": ((410.2, 33.5), (18.5, 3.5)),
    "exp400-32x": ((410.2, 33.5), (18.5, 3.5)),
}

# Faces that print the mark and have no region yet, with the reason.
LEFT_OUT = (
    "csr180",  # the picture is taken from above: its two axes disagree by 4.5 percent
    "csr310",  # another open change edits this device's version and lock
    "exp800-16o",  # the photograph is angled: its two axes disagree by 5.7 percent
)

# The model name is plain text on these fronts and stays drawn next to the zone.
PLAIN_TEXT_KEPT = ("csr180", "csr200", "csr430", "csr440")


def front(name):
    doc = yaml.safe_load((EDGECORE / name / "device.yaml").read_text())
    return doc, doc["views"]["front"]


def zones(view):
    return [r for r in view.get("regions") or [] if str(r.get("id", "")).startswith("logo")]


def test_each_measured_face_has_one_logo_zone():
    for name, (at, size) in ZONES.items():
        doc, view = front(name)
        found = zones(view)
        assert [r["id"] for r in found] == ["logo-zone"], (name, found)
        region = found[0]
        assert region["at"] == list(at), name
        assert (region["size"]["w"], region["size"]["h"]) == size, name
        assert "not drawn" in region["label"], name


def test_the_zone_lies_inside_the_front_and_has_a_size():
    for name in ZONES:
        _, view = front(name)
        region = zones(view)[0]
        (x, y), (w, h) = region["at"], (region["size"]["w"], region["size"]["h"])
        assert w > 0 and h > 0, name
        assert x >= 0 and y >= 0, name
        assert x + w <= view["size"]["w"] and y + h <= view["size"]["h"], name


def test_lint_has_nothing_to_say_about_the_zone():
    for name in ZONES:
        doc, _ = front(name)
        with L.collecting() as found:
            L.lint_device_logo_zone(name, doc)
        assert [e for e in found.errors if "L172" in e] == [], name


def test_nothing_that_is_drawn_is_named_for_a_logo():
    for name in ZONES:
        _, view = front(name)
        drawn = (view.get("panel") or {}).get("decor") or []
        assert not [d for d in drawn if "logo" in str(d.get("id", ""))], name


def test_the_face_left_out_has_no_zone():
    for name in LEFT_OUT:
        _, view = front(name)
        assert zones(view) == [], name


def test_the_plain_text_wordmark_stays_where_it_is_drawn():
    for name in PLAIN_TEXT_KEPT:
        doc, view = front(name)
        text = [t for t in (view.get("silkscreen") or []) if t.get("text") == "Edge-core"]
        assert len(text) == 1, name


def test_the_layout_and_the_expanded_device_agree_on_the_zone():
    for name in ZONES:
        device = EDGECORE / name / "device.yaml"
        layout = EDGECORE / name / "layout.yaml"
        if not layout.exists():
            continue
        expanded = zones(yaml.safe_load(device.read_text())["views"]["front"])
        authored = zones(yaml.safe_load(layout.read_text())["views"]["front"])
        assert expanded == authored, name

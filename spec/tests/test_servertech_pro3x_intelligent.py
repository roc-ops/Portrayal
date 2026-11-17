"""The Server Technology PRO3X Smart 3C01, Switched 3F01 and Switched POPS 3G01, and their controller panel.

What is true of the library once they are in it: each device has the 36 outlets of the Basic 3A01 chassis.
Each has a bay for the controller between the banks.
The controller's seven jacks are modelled parts with interface keys.
Switched units declare on and off on every outlet. The Smart unit declares no outlet state.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "servertech"
CONTROLLER = ROOT / "library" / "components" / "servertech" / "pro3x-controller" / "v1" / "contract.yaml"

CASES = {
    "pro3x-smart-3c01": ("branch", False),
    "pro3x-switched-3f01": ("branch", True),
    "pro3x-switched-pops-3g01": ("outlet", True),
}
OUTLET_REFS = ("servertech/hdot-cx-outlet@1", "std/c13-outlet@1")


def _device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text(encoding="utf-8"))


def _outlets(dev):
    return [p for p in dev["views"]["front"]["components"]["placements"] if p["ref"] in OUTLET_REFS]


def test_each_device_has_thirty_six_outlets_numbered_from_the_far_end():
    for name in CASES:
        outlets = _outlets(_device(name))
        assert sorted(int(p["id"].rsplit("-", 1)[1]) for p in outlets) == list(range(1, 37)), name
        refs = [p["ref"] for p in outlets]
        assert (refs.count("std/c13-outlet@1"), refs.count("servertech/hdot-cx-outlet@1")) == (18, 18), name


def test_each_device_has_a_controller_bay_between_the_banks():
    for name in CASES:
        dev = _device(name)
        bay = dev["views"]["front"]["components"]["bays"][0]
        assert bay["accepts"] == ["servertech/pro3x-controller@1"], name
        assert dev["configurations"]["base"]["bays"] == {"controller": "servertech/pro3x-controller@1"}, name
        far = max(p["at"][1] for p in _outlets(dev) if int(p["id"].rsplit("-", 1)[1]) <= 18)
        near = min(p["at"][1] for p in _outlets(dev) if int(p["id"].rsplit("-", 1)[1]) > 18)
        assert far < bay["at"][1] and bay["at"][1] + bay["size"]["h"] < near, name


def test_capability_follows_the_family():
    for name, (scope, switching) in CASES.items():
        management = _device(name)["attrs"]["management"]
        assert management["metering-scope"] == scope, name
        assert management["outlet-switching"] is switching, name
        states = {tuple(p.get("states", ())) for p in _outlets(_device(name))}
        assert states == ({("on", "off")} if switching else {()}), name


def _decor(dev, face):
    return dev["views"][face]["panel"]["decor"]


def _kind(dev, face, kind):
    return [i for i in _decor(dev, face) if i.get("kind") == kind]


def test_each_numeral_has_a_hole_beside_it():
    """The data sheet photographs show a hole by every numeral: 36 holes, each before its numeral."""
    for name in CASES:
        dev = _device(name)
        holes = {i["id"]: i for i in _kind(dev, "front", "hole") if i["id"].startswith("numeral-hole-")}
        assert len(holes) == 36, name
        numerals = {p["id"].rsplit("-", 1)[1]: p for p in dev["views"]["front"]["components"]["placements"]
                    if p["id"].startswith("numeral-")}
        for n, p in numerals.items():
            hole = holes[f"numeral-hole-{n}"]
            centre = hole["at"][1] + hole["size"][1] / 2
            assert p["at"][1] < centre < p["at"][1] + 18.0, (name, n)
            assert hole["at"][0] + hole["size"][0] <= p["at"][0], (name, n)


def test_the_cover_has_two_screw_holes_and_the_ground_point_is_a_ring_with_a_dot():
    """The cord-end cover has two screw holes. The ground point is a ring round a centre dot."""
    for name in CASES:
        dev = _device(name)
        cover = next(i for i in _decor(dev, "front") if i["id"] == "front-entry-plate")
        holes = [i for i in _decor(dev, "front") if i["id"].startswith("cover-hole-")]
        assert len(holes) == 2, name
        for h in holes:
            assert cover["at"][0] < h["at"][0] and h["at"][0] + h["size"][0] < cover["at"][0] + cover["size"][0], name
            assert cover["at"][1] < h["at"][1] and h["at"][1] + h["size"][1] < cover["at"][1] + cover["size"][1], name
        ring = next(i for i in _decor(dev, "front") if i["id"] == "ground-point")
        dot = next(i for i in _decor(dev, "front") if i["id"] == "ground-point-dot")
        assert ring.get("stroke") and "fill" not in ring, name
        assert abs(ring["at"][0] + ring["size"][0] / 2 - dot["at"][0] - dot["size"][0] / 2) < 0.01, name
        assert abs(ring["at"][1] + ring["size"][1] / 2 - dot["at"][1] - dot["size"][1] / 2) < 0.01, name
        assert dot["size"][0] < ring["size"][0] / 2, name


def test_each_side_has_two_perforated_zones_a_seam_screws_and_nubs():
    """Each side draws a short cord-end block and a long band of dots, a seam between them, 11 screws and 2 nubs."""
    for name in CASES:
        dev = _device(name)
        for face in ("left", "right"):
            decor = _decor(dev, face)
            zones = sorted((i for i in decor if i.get("pattern") == "holes"), key=lambda i: i["at"][1])
            assert len(zones) == 2, (name, face)
            short, long_ = sorted(zones, key=lambda i: i["size"][1])
            assert short["size"][1] < 100 < 1500 < long_["size"][1], (name, face)
            seam = [i for i in decor if i.get("kind") == "seam"]
            assert len(seam) == 1, (name, face)
            lo, hi = sorted(zones, key=lambda i: -i["at"][1])  # lo is the cord-end block (larger y)
            assert hi["at"][1] + hi["size"][1] < seam[0]["at"][1] < lo["at"][1], (name, face)
            assert len([i for i in decor if i.get("kind") == "screw-head"]) == 11, (name, face)
            assert len([i for i in decor if i.get("kind") == "mount-nub" and i["id"].endswith("-cap")]) == 2, (name, face)


def test_each_bank_has_end_lugs_and_each_outlet_has_edge_tabs():
    """Each of the six banks has two lugs on its far end. Each outlet has a tab on each long edge: 36 and 36."""
    for name in CASES:
        dev = _device(name)
        assert len(_kind(dev, "front", "bank-lug")) == 12, name
        tabs = _kind(dev, "front", "edge-tab")
        assert len([i for i in tabs if "-top-" in i["id"]]) == 36, name
        assert len([i for i in tabs if "-bottom-" in i["id"]]) == 36, name
        housings = sorted(i["at"][1] for i in _decor(dev, "front") if i["id"].startswith("housing-"))
        for h in housings:
            near = [i for i in _kind(dev, "front", "bank-lug") if h - 4 <= i["at"][1] <= h]
            assert len(near) == 2, (name, h)


def test_the_controller_plate_has_a_notched_outline():
    """The notched outline is the part's plate and two tabs beyond the bay's edge, beside the bay."""
    for name in CASES:
        dev = _device(name)
        bay = dev["views"]["front"]["components"]["bays"][0]
        tabs = [i for i in _decor(dev, "front") if i["id"].startswith("controller-outline-")]
        assert len(tabs) == 2, name
        for t in tabs:
            assert bay["at"][1] < t["at"][1] and t["at"][1] + t["size"][1] < bay["at"][1] + bay["size"]["h"], name
        left, right = sorted(tabs, key=lambda t: t["at"][0])
        assert left["at"][0] < bay["at"][0] < left["at"][0] + left["size"][0], name
        assert right["at"][0] < bay["at"][0] + bay["size"]["w"] < right["at"][0] + right["size"][0], name


def test_a_plain_plate_stands_between_the_controller_and_the_far_breaker():
    """A plate with no holes stands between the controller bay and the far breaker plate."""
    for name in CASES:
        dev = _device(name)
        bay = dev["views"]["front"]["components"]["bays"][0]
        plate = next(i for i in _decor(dev, "front") if i["id"] == "plate-plain")
        far_breaker = next(i for i in _decor(dev, "front") if i["id"] == "plate-3")
        assert plate["at"][1] + plate["size"][1] <= bay["at"][1] + 0.01, name
        assert far_breaker["at"][1] + far_breaker["size"][1] <= plate["at"][1] + 5.0, name
        assert not [i for i in _decor(dev, "front") if i["id"].startswith("screw-") and
                    plate["at"][1] <= i["at"][1] <= plate["at"][1] + plate["size"][1]], name


def test_the_controller_jacks_are_modelled_parts():
    part = yaml.safe_load(CONTROLLER.read_text(encoding="utf-8"))
    refs = {p["id"]: p["ref"] for p in part["parts"]}
    assert refs == {
        "eth1": "common/rj45-eth@1",
        "eth2": "common/rj45-eth@1",
        "console": "std/rj45@2",
        "sensor": "std/rj45@2",
        "aux": "common/rj11-jack@1",
        "usb-a": "std/usb-a@1",
        "usb-b": "raritan/pxo-usb-b@1",
    }

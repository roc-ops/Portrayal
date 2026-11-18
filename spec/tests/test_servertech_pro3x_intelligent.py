"""The Server Technology PRO3X Smart 3C01, Switched 3F01 and Switched POPS 3G01, and their controller panel.

What is true of the library once they are in it: each device has the 36 outlets of the Basic 3A01 chassis.
Each has a bay for the controller between the banks.
The controller's seven jacks are modelled parts with interface keys.
Switched units declare on and off on every outlet. The Smart unit declares no outlet state.
"""
import importlib.util
import pathlib
import re

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


def test_the_symbol_labels_stand_beside_the_ground_ring_as_the_sheet_draws_them():
    """The cord-end crop reads the two labels at 31.7 to 40.2 and 44.3 to 51.8 across and 66.6 to 78.0 along from the cord end."""
    for name in CASES:
        decor = {i["id"]: i for i in _decor(_device(name), "front")}
        for key, lo, hi in (("symbol-label-1", 31.0, 41.0), ("symbol-label-2", 43.5, 53.0)):
            label = decor[key]
            assert lo <= label["at"][0] and label["at"][0] + label["size"][0] <= hi, (name, key)
            along = (1778.0 - label["at"][1] - label["size"][1], 1778.0 - label["at"][1])
            assert 66.0 <= along[0] and along[1] <= 78.6, (name, key)


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
        housings = sorted(i["at"][1] for i in _decor(dev, "front") if re.fullmatch(r"housing-\d", i["id"]))
        assert len(housings) == 6, name
        for h in housings:
            # the sheet puts each lug 2.4 inside its bank's far edge
            near = [i for i in _kind(dev, "front", "bank-lug") if abs(i["at"][1] - (h + 2.4)) < 0.01]
            assert len(near) == 2, (name, h)


def _tabs(dev):
    return [i for i in _decor(dev, "front") if i["id"].startswith("controller-outline-")]


def test_the_controller_plate_has_a_notched_outline():
    """The notched outline is the part's plate and four tabs beyond the bay's edges: two stretches, two sides each."""
    for name in CASES:
        dev = _device(name)
        bay = dev["views"]["front"]["components"]["bays"][0]
        tabs = _tabs(dev)
        assert len(tabs) == 4, name
        for t in tabs:
            assert bay["at"][1] < t["at"][1] and t["at"][1] + t["size"][1] < bay["at"][1] + bay["size"]["h"], name
        left = [t for t in tabs if t["at"][0] < 28]
        right = [t for t in tabs if t["at"][0] >= 28]
        assert all(t["at"][0] < bay["at"][0] < t["at"][0] + t["size"][0] for t in left), name
        assert all(t["at"][0] < bay["at"][0] + bay["size"]["w"] < t["at"][0] + t["size"][0] for t in right), name
        # the notch is 1.9 deep, read on the sheet: each tab reaches that far beyond the bay's edge
        assert all(bay["at"][0] - t["at"][0] >= 1.8 for t in left), name
        assert all(t["at"][0] + t["size"][0] - (bay["at"][0] + bay["size"]["w"]) >= 1.8 for t in right), name


def test_the_controller_plate_is_wider_over_the_jack_group_as_well_as_the_display():
    """Two stretches: about 31 along over the display and about 21 along over the jack group, nearer the far end."""
    for name in CASES:
        tabs = sorted((t for t in _tabs(_device(name)) if t["at"][0] < 28), key=lambda t: t["at"][1])
        assert len(tabs) == 2, name
        far, near = tabs
        assert 19.0 < far["size"][1] < 24.0, name
        assert 28.0 < near["size"][1] < 34.0, name
        assert far["at"][1] + far["size"][1] < near["at"][1], name


def test_the_controller_panel_size_is_read_from_the_sheet_and_not_lent_by_another_model():
    """52.0 across and 141.6 along, read on the sheet's front view, and written the same in the bay and the part."""
    part = yaml.safe_load(CONTROLLER.read_text(encoding="utf-8"))
    skin = (CONTROLLER.parent / "skins" / "default.svg").read_text(encoding="utf-8")
    assert part["size"]["w"] == 52.0 and part["size"]["h"] == 141.6
    assert 'viewBox="0 0 52 141.6"' in skin
    for name in CASES:
        bay = _device(name)["views"]["front"]["components"]["bays"][0]
        assert (bay["size"]["w"], bay["size"]["h"]) == (52.0, 141.6), name
        assert abs(bay["at"][0] * 2 + bay["size"]["w"] - 55.9) < 0.01, name
    text = CONTROLLER.read_text(encoding="utf-8") + skin
    assert "PRO4X" not in text and "borrowed" not in text
    for name in CASES:
        dev = _device(name)
        gaps = {g["what"]: g["note"] for g in dev["gaps"]}
        for what in ("controller-scale", "cord-and-plug"):
            assert "PRO4X" not in gaps[what] or "stand-in" in gaps[what], (name, what)
            assert "borrowed" not in gaps[what], (name, what)
        assert "stand-in" in gaps["cord-and-plug"], name


def test_each_housing_steps_in_where_the_cx_outlets_change_to_c13():
    """Each bank's housing is full width over its Cx outlets and 3.0 narrower each side over its C13 outlets."""
    for name in CASES:
        decor = {i["id"]: i for i in _decor(_device(name), "front")}
        for n in range(1, 7):
            c13, cx = decor[f"housing-{n}"], decor[f"housing-{n}-cx"]
            assert abs(c13["at"][1] + c13["size"][1] - cx["at"][1]) < 0.01, (name, n)
            assert abs(c13["at"][0] - cx["at"][0] - 3.0) < 0.01, (name, n)
            assert abs(cx["size"][0] - c13["size"][0] - 6.0) < 0.01, (name, n)
            assert 60.0 < c13["size"][1] < 70.0, (name, n)
            # the sheet's housing lines read 9.9 and 45.6 from the strip's top edge, to about 1 mm
            assert 9.0 <= cx["at"][0] <= 10.9 and 44.6 <= cx["at"][0] + cx["size"][0] <= 46.6, (name, n)
        bumps = [i for i in decor.values() if i.get("kind") == "housing-bump"]
        assert len(bumps) == 24, name


def test_the_side_pegs_are_named_in_the_side_gap_with_the_kit_reason():
    """The 36 lever pegs stand under the body beyond a face's width: a gap says so and says where the sheet shows them."""
    for name in CASES:
        gaps = {g["what"]: g for g in _device(name)["gaps"]}
        note = gaps["side-nubs"]["note"]
        for phrase in ("pegs", "36", "page 5", "side view", "body's width"):
            assert phrase in note, (name, phrase)
        assert gaps["side-nubs"]["scope"] == ["left", "right"], name


def test_every_estimate_gap_states_its_tolerance():
    for name in CASES:
        gaps = {g["what"]: g["note"] for g in _device(name)["gaps"]}
        for what in ("numeral-hole", "outlet-lever", "controller-outline", "controller-scale", "housing-step",
                     "raster-detail", "side-detail", "side-nubs", "cord-and-plug", "outlet-across-position"):
            assert "tolerance" in gaps[what], (name, what)
        assert "taken figure" in gaps["numeral-hole"], name


def test_the_proud_entries_of_the_three_devices_stand_for_the_sheets_81_8_reach():
    spec = importlib.util.spec_from_file_location("built_faces_in_depth", ROOT / "spec" / "tests" / "test_built_faces_in_depth.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in CASES:
        mm, why = module.PROUD[name]
        assert abs(mm - (81.8 - 63.5)) < 0.01, name
        assert "81.8" in why and "63.5" in why, name
        assert len(why.split()) <= 25 and "ISS-" not in why, name


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


def _bank_of(item_id):
    return (int(item_id.rsplit("-", 2)[-2] if item_id.endswith(("-a", "-b")) else item_id.rsplit("-", 1)[1]) - 1) // 6


def test_each_top_tab_has_two_holes_and_each_c13_tab_a_notch():
    """Each of the 36 top tabs has two holes: 12 a bank. Each of the 18 C13 tabs also has a notch."""
    for name in CASES:
        dev = _device(name)
        holes = _kind(dev, "front", "tab-hole")
        assert len(holes) == 72, name
        for bank in range(6):
            assert len([h for h in holes if _bank_of(h["id"]) == bank]) == 12, (name, bank)
        tabs = {i["id"]: i for i in _kind(dev, "front", "edge-tab") if "-top-" in i["id"]}
        for h in holes:
            tab = tabs[f"edge-tab-top-{h['id'].split('-')[2]}"]
            assert tab["at"][0] < h["at"][0] and h["at"][0] + h["size"][0] < tab["at"][0] + tab["size"][0], (name, h["id"])
            assert tab["at"][1] < h["at"][1] and h["at"][1] + h["size"][1] < tab["at"][1] + tab["size"][1], (name, h["id"])
        notches = [i for i in _kind(dev, "front", "tab-notch") if not i["id"].endswith("-stub")]
        assert len(notches) == 18, name
        c13 = {int(p["id"].rsplit("-", 1)[1]) for p in _outlets(dev) if p["ref"] == "std/c13-outlet@1"}
        assert {int(n["id"].rsplit("-", 1)[1]) for n in notches} == c13, name
        for bank in range(6):
            assert len([n for n in notches if _bank_of(n["id"]) == bank]) == 3, (name, bank)


def test_each_bank_has_six_bottom_bumps_six_dots_and_three_rings():
    """The bottom edge of each bank: a bump and a dot at each outlet and a ring at each Cx outlet."""
    for name in CASES:
        dev = _device(name)
        bumps = [i for i in _kind(dev, "front", "edge-tab") if "-bottom-" in i["id"]]
        dots = _kind(dev, "front", "bottom-dot")
        rings = _kind(dev, "front", "bottom-ring")
        assert (len(bumps), len(dots), len(rings)) == (36, 36, 18), name
        for bank in range(6):
            assert len([i for i in bumps if _bank_of(i["id"]) == bank]) == 6, (name, bank)
            assert len([i for i in dots if _bank_of(i["id"]) == bank]) == 6, (name, bank)
            assert len([i for i in rings if _bank_of(i["id"]) == bank]) == 3, (name, bank)


def test_the_outlets_stand_at_the_centres_read_on_the_sheet():
    """The centres along the strip are read from the sheet's raster: spot checks at both ends and the middle, to 0.1 mm."""
    for name in CASES:
        outlets = {int(p["id"].rsplit("-", 1)[1]): p for p in _outlets(_device(name))}
        for k, centre in ((36, 256.7), (31, 379.2), (19, 824.3), (18, 1185.2), (1, 1753.0)):
            p = outlets[k]
            h = 24.0 if p["ref"] == "servertech/hdot-cx-outlet@1" else 22.0
            assert abs(1778.0 - p["at"][1] - h / 2 - centre) < 0.1, (name, k)
        gaps = {g["what"]: g["note"] for g in _device(name)["gaps"]}
        assert "tolerance" in gaps["outlet-along-position"] and "0.485" in gaps["outlet-along-position"], name


def test_the_controller_skin_draws_the_notches_and_the_lip():
    """Eight notches at the stretch ends, four near the ring end and a lip at each side of the cord end, in the part's skin."""
    skin = (CONTROLLER.parent / "skins" / "default.svg").read_text(encoding="utf-8")
    assert len(re.findall(r'id="stretch-notch-\d"', skin)) == 8
    assert len(re.findall(r'id="ring-notch-\d"', skin)) == 4
    assert len(re.findall(r'id="lip-[lr]"', skin)) == 2


def test_the_outlet_size_gap_says_why_the_shared_part_is_not_changed_here():
    """The sheet reads the Cx body 24.2 across and the part draws it 30.1. A shared part is changed in its own pull request."""
    for name in CASES:
        note = {g["what"]: g["note"] for g in _device(name)["gaps"]}["outlet-size"]
        for phrase in ("24.2", "30.1", "shared", "new version", "its own change"):
            assert phrase in note, (name, phrase)


def test_the_outlet_lever_gap_says_the_tabs_and_pegs_may_be_the_levers():
    for name in CASES:
        note = {g["what"]: g["note"] for g in _device(name)["gaps"]}["outlet-lever"]
        assert "top-edge tabs" in note and "pegs" in note and "same part" in note, name


def test_the_proud_entries_say_the_levers_place_and_across_are_photograph_estimates():
    spec = importlib.util.spec_from_file_location("built_faces_in_depth", ROOT / "spec" / "tests" / "test_built_faces_in_depth.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in CASES:
        why = module.PROUD[name][1]
        assert "photograph" in why and "2.0" in why and "place" in why, name
        assert len(why.split()) <= 25, name

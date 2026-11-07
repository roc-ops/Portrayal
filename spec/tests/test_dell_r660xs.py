"""The Dell PowerEdge R660xs (dell/r660xs), against Dell's Installation and Service Manual.

The envelope, each front and its bay numbering, the slots of each riser
configuration's rear, the supply bays, the top view's fans, heatsinks and DIMM
slots, and the DCIM device types. The sources are the ISM's tables 8 and 95,
its figures 1 to 3, 7, 8 and 60.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "dell" / "r660xs" / "device.yaml"
DIST = LIB / "dist"
EXPORTS = LIB / "exports"


@pytest.fixture(scope="module")
def doc():
    return yaml.safe_load(DEVICE.read_text())


def _bays(doc, view):
    return doc["views"][view]["components"]["bays"]


def _built_paths(name):
    svg = DIST / f"r660xs.{name}.svg"
    assert svg.exists(), f"{svg.name} is not built: run ./build.sh first"
    return {n.get("data-path") for n in ET.parse(svg).iter() if n.get("data-path")}


# --- the envelope: ISM table 8 -------------------------------------------------

def test_the_envelope_is_ism_table_8(doc):
    ch = doc["chassis"]
    assert ch["width"] == 434.0, "Xb, between the ears"
    assert ch["height"] == 42.8, "Y"
    # Zb, ear to rear wall, 677.1 for 10 or 4 drives, plus Za without the bezel, 22
    assert ch["depth"] == pytest.approx(677.1 + 22.0)
    assert ch["ru"] == 1


@pytest.mark.parametrize("view", ["front", "front-sff8", "front-lff4"])
def test_every_front_is_the_rack_face_across_the_ears(doc, view):
    # Xa, 482 across the ears (482.6 as the rack's face), carrying both control panels
    assert doc["views"][view]["size"] == {"w": 482.6, "h": 42.8}
    ids = {b["id"] for b in _bays(doc, view)}
    assert "panel-left" in ids


def test_the_top_and_sides_run_the_chassis_depth(doc):
    assert doc["views"]["top"]["size"] == {"w": 434.0, "h": doc["chassis"]["depth"]}
    assert doc["views"]["left"]["size"]["w"] == doc["chassis"]["depth"]


# --- the fronts: ISM figures 1 to 3 --------------------------------------------

FRONTS = {
    # view: (bay ids in Dell's order, the numbering each bay carries)
    "front": ([f"drive-{n}" for n in range(10)], list(range(10))),
    "front-sff8": ([f"drive-{n}" for n in range(8)], list(range(8))),
    "front-lff4": ([f"lff-drive-{n}" for n in range(4)], list(range(4))),
}


@pytest.mark.parametrize("view", sorted(FRONTS))
def test_each_front_has_its_bays_numbered_as_dell_numbers_them(doc, view):
    ids, numbers = FRONTS[view]
    drives = [b for b in _bays(doc, view) if b["id"].startswith(("drive-", "lff-drive-"))]
    assert [b["id"] for b in drives] == ids
    assert [b["rel-pos"] for b in drives] == numbers
    assert all(b["default"].endswith(("blank-25@2", "blank-35@1")) for b in drives), \
        "every bay defaults to a blank"


def test_the_8_drive_front_has_its_vent_block_over_columns_4_and_5(doc):
    drives = {b["id"]: b for b in _bays(doc, "front-sff8")}
    # bays 6 and 7 are the lower row of columns 4 and 5: no upper bay there
    assert drives["drive-6"]["at"][0] == pytest.approx(281.1)
    assert drives["drive-7"]["at"][0] == pytest.approx(363.95)
    assert drives["drive-6"]["at"][1] == drives["drive-1"]["at"][1]
    assert drives["drive-7"]["at"][1] == drives["drive-1"]["at"][1]


def test_each_front_is_bound_by_a_configuration(doc):
    views = {}
    for name, cfg in doc["configurations"].items():
        views[name.split("-")[0]] = (cfg.get("views") or {}).get("front", "front")
    assert views == {"sff10": "front", "sff8": "front-sff8", "lff4": "front-lff4"}


def test_the_bezel_hides_the_drives_and_not_the_vga(doc):
    for view, (ids, _) in FRONTS.items():
        bezel = next(p for p in doc["views"][view]["components"]["placements"] if p["id"] == "bezel")
        assert bezel["ref"] == "dell/bezel-1u-16g@1"
        assert bezel["hides"] == ids
        assert "vga" not in bezel["hides"]


# --- the rear for each riser configuration: ISM table 95 -----------------------

SLOTS = {
    # riser configuration: the slots Dell numbers on its risers
    "rc1-1a2a": {"slot-1", "slot-2", "slot-3"},
    "rc2-1a2e": {"slot-1", "slot-2"},
    "rc3-1a": {"slot-1"},
    "rc4-1a-rear2": {"slot-1"},
    "rc5-1a2d": {"slot-1", "slot-2"},
    "rc6-1b2e": {"slot-1", "slot-2"},
}


@pytest.mark.parametrize("rc", sorted(SLOTS))
def test_each_riser_configurations_rear_has_its_slots(rc):
    # the build writes a rear once per distinct rear, so the first front's name stands for all three
    paths = _built_paths(f"sff10-{rc}.rear")
    slots = {p.split("/")[-1] for p in paths if p.count("/") == 2 and "/module/slot-" in p}
    assert slots == SLOTS[rc]
    rear_drives = {p for p in paths if p.startswith("rear-drive-") and "/" not in p}
    assert rear_drives == ({"rear-drive-0", "rear-drive-1"} if rc == "rc4-1a-rear2" else set())


def test_slots_are_numbered_across_the_risers_not_per_riser(doc):
    risers = {}
    for ref in ("riser-1a", "riser-1b", "riser-2a", "riser-2d", "riser-2e"):
        c = yaml.safe_load((LIB / "components" / "dell" / f"r660xs-{ref}" / "v1" / "contract.yaml").read_text())
        risers[ref] = {k for k, b in c["bays"].items() if "slot" in b}
    assert risers == {"riser-1a": {"slot-1"}, "riser-1b": {"slot-1"}, "riser-2a": {"slot-2", "slot-3"},
                      "riser-2d": {"slot-2"}, "riser-2e": {"slot-2"}}


def test_the_riser_widths_are_table_95s():
    def lanes(ref):
        c = yaml.safe_load((LIB / "components" / "dell" / f"r660xs-{ref}" / "v1" / "contract.yaml").read_text())
        return {k: b["slot"]["lanes"] for k, b in c["bays"].items() if "slot" in b}
    assert lanes("riser-1a") == {"slot-1": 16}
    assert lanes("riser-1b") == {"slot-1": 8}
    assert lanes("riser-2a") == {"slot-2": 8, "slot-3": 8}
    assert lanes("riser-2d") == {"slot-2": 8}
    assert lanes("riser-2e") == {"slot-2": 16}


# --- the chassis print on the rear: ISM figure 7 ---------------------------------

def _num(tok):
    return float(tok)


def _path_box(d):
    """The box a silkscreen path of absolute M, L, H, V, A and Z commands spans, from its origin."""
    toks = d.replace(",", " ").split()
    xs, ys, i, cmd, x, y = [0.0], [0.0], 0, None, 0.0, 0.0
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd == "Z":
                continue
        if cmd in "ML":
            x, y = _num(toks[i]), _num(toks[i + 1]); i += 2
        elif cmd == "H":
            x = _num(toks[i]); i += 1
        elif cmd == "V":
            y = _num(toks[i]); i += 1
        elif cmd == "A":
            rx = _num(toks[i])
            x, y = _num(toks[i + 5]), _num(toks[i + 6]); i += 7
            xs += [x - rx, x + rx]; ys += [y - rx, y + rx]
        else:
            raise AssertionError(f"path command {cmd} is not read here: {d}")
        xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _mark_box(m):
    """The box one rear silkscreen mark covers, in the rear face's mm."""
    x, y = m["at"]
    if "path" in m:
        x0, y0, x1, y1 = _path_box(m["path"])
        return x + x0, y + y0, x + x1, y + y1
    size = m.get("font-size", 2.2)
    w = 0.62 * size * len(m["text"])
    anchor = m.get("anchor", "middle")
    left = x if anchor == "start" else x - w if anchor == "end" else x - w / 2
    return left, y - size, left + w, y


def _rear_bay_boxes(doc):
    return [(b["id"], b["at"][0], b["at"][1], b["at"][0] + b["size"]["w"], b["at"][1] + b["size"]["h"])
            for b in _bays(doc, "rear")]


def test_no_chassis_print_is_under_a_bay(doc):
    # a module paints over the chassis silkscreen, so a mark inside a bay's extent is hidden
    # in every build that seats it: the PSU 1 bolt sat under riser 2's cage, "iDRAC" lost its i
    bays = _rear_bay_boxes(doc)
    buried = []
    for m in doc["views"]["rear"]["silkscreen"]:
        mx0, my0, mx1, my1 = _mark_box(m)
        for bid, bx0, by0, bx1, by1 in bays:
            if mx0 < bx1 and mx1 > bx0 and my0 < by1 and my1 > by0:
                buried.append((m.get("text") or m["path"][:24], bid))
    assert not buried, f"printed under a bay: {buried}"


def _contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_the_rear_print_is_legible_on_the_light_wall_and_plate(doc):
    panel = doc["views"]["rear"]["panel"]
    plate = next(d["fill"] for d in panel["decor"] if d["size"] == [71.2, 15.93])
    for m in doc["views"]["rear"]["silkscreen"]:
        if m["fill"] == plate:
            continue   # the i's knock-out, drawn in the plate's own colour on its dark disc
        assert _contrast(m["fill"], plate) >= 4.5, m
    # the kit's symbols are drawn in light ink for a dark panel: seated on the light plate they vanish
    placed = {p["ref"] for p in doc["views"]["rear"]["components"]["placements"]}
    assert "common/vga-symbol@1" not in placed


def _marks_for(doc, target):
    return [m for m in doc["views"]["rear"]["silkscreen"] if target in (m.get("for") if isinstance(m.get("for"), list) else [m.get("for")])]


def test_the_rear_prints_the_icons_figure_7_draws(doc):
    # the USB trident by SS (USB 3.0) and the one over the USB 2.0 port, the circled i by the ID button,
    # and the VGA monitor mark; the LOM's link icons are in its skin
    assert any("path" in m for m in _marks_for(doc, "usb-2")), "no trident by SS"
    assert any("path" in m for m in _marks_for(doc, "usb-1")), "no trident by the USB 2.0 port"
    assert any("path" in m for m in _marks_for(doc, "system-id")), "no i by the system ID button"
    assert any("path" in m for m in _marks_for(doc, "video")), "no VGA mark"


def test_idrac_clears_the_lom_bracket(doc):
    mark = next(m for m in doc["views"]["rear"]["silkscreen"] if m.get("text") == "iDRAC")
    lom = next(b for b in doc["views"]["rear"]["components"]["bays"] if b["id"] == "lom")
    assert mark.get("anchor") == "start"
    assert mark["at"][0] >= lom["at"][0] + lom["size"]["w"], "the word begins right of the LOM bracket"


def _skin(name):
    return ET.parse(LIB / "components" / "dell" / name / "v1" / "skins" / "default.svg").getroot()


def test_the_lom_bracket_prints_the_link_icons_beside_1_and_2():
    ids = {n.get("id") for n in _skin("r660xs-lom-2x1g").iter() if n.get("id")}
    assert {"link-1", "link-2"} <= ids


def test_riser_2s_cage_carries_the_psu_1_mark_on_its_latch_strip():
    # figure 7 prints the bolt and the 1 on the cage's own end strip, so they belong to the cage
    ids = {n.get("id") for n in _skin("r660xs-riser-2-cage").iter() if n.get("id")}
    assert "psu-1-mark" in ids


# --- the supplies --------------------------------------------------------------

def test_the_supplies_stand_side_by_side_at_the_right(doc):
    bays = {b["id"]: b for b in _bays(doc, "rear")}
    p1, p2 = bays["psu-1"], bays["psu-2"]
    assert p1["at"][0] > doc["chassis"]["width"] / 2, "not at opposite ends, as on the R660"
    assert p1["at"][0] + p1["size"]["w"] <= p2["at"][0]
    assert p2["at"][0] + p2["size"]["w"] <= doc["chassis"]["width"]
    want = ["dell/psu-1400w-ac-60mm@1", "dell/psu-1100w-ac-60mm@1",
            "dell/psu-800w-ac-60mm@1", "dell/psu-700w-ac-60mm@1"]
    assert p1["accepts"] == p2["accepts"] == want


# --- the top view: ISM figures 8 and 60 ----------------------------------------

def test_the_top_view_carries_seven_fans_two_heatsinks_and_sixteen_dimm_slots(doc):
    bays = _bays(doc, "top")
    fans = [b for b in bays if b["id"].startswith("fan-")]
    dimms = [b["id"] for b in bays if b["id"].startswith("dimm-")]
    assert len(fans) == 7
    assert sorted(dimms) == sorted(f"dimm-{c}{n}" for c in "ab" for n in range(1, 9))
    heatsinks = [p for p in doc["views"]["top"]["components"]["placements"] if p["id"].startswith("heatsink-")]
    assert len(heatsinks) == 2


def test_the_dimm_slots_run_in_figure_60s_order(doc):
    dimms = sorted((b for b in _bays(doc, "top") if b["id"].startswith("dimm-")), key=lambda b: b["at"][0])
    assert [b["id"][5:] for b in dimms] == [
        "b8", "b2", "b6", "b4", "b1", "b7", "b3", "b5", "a8", "a2", "a6", "a4", "a1", "a7", "a3", "a5"]


def test_the_top_view_shows_the_seated_parts_from_above():
    svg = DIST / "r660xs.sff10-rc1-1a2a.top.svg"
    ids = {n.get("id") for n in ET.parse(svg).iter() if n.get("id")}
    assert {"psu-1-plan", "psu-2-plan", "riser-1-plan", "riser-2-plan"} <= ids, "the supplies and risers project"
    paths = _built_paths("sff10-rc1-1a2a.top")
    assert "system-board" in paths
    assert sum(1 for p in paths if p.startswith("fan-") and "/" not in p) == 7


def test_the_top_face_has_no_opaque_decor_over_the_chassis(doc):
    # decor is painted into the face the 3D viewer draws on the top: a floor rectangle the size of
    # the chassis stood there as an opaque white lid. The floor is a part with an interior now,
    # so the top is open over it (the R660's top has a cover or no decor at all)
    top = doc["views"]["top"]
    area = top["size"]["w"] * top["size"]["h"]
    for d in (top.get("panel") or {}).get("decor", []):
        assert d["size"][0] * d["size"][1] < 0.1 * area, d.get("id")
    floor = next(p for p in top["components"]["placements"] if p["id"] == "chassis-floor")
    comp = yaml.safe_load((LIB / "components" / "dell" / "r660xs-chassis-floor" / "v1" / "contract.yaml").read_text())
    assert floor["ref"] == "dell/r660xs-chassis-floor@1"
    assert (comp["size"]["w"], comp["size"]["h"]) == (top["size"]["w"], top["size"]["h"])
    assert comp["relief"]["walls"] == "inside"


def _gap(doc, what):
    return next((g for g in doc["gaps"] if g["what"] == what), None)


def test_the_top_view_declares_what_it_does_not_draw(doc):
    # figure 8's fan cage is the frame round the seven fans; the air shroud's gap names it
    shroud = _gap(doc, "air-shroud-covers-backplane-in-top-view")
    assert "fan cage" in shroud["note"]
    # the 4 x 3.5 inch bays carry no top `plan:`, so a fitted 3.5 inch drive never shows from above
    lff = _gap(doc, "lff-drives-have-no-top-plan")
    assert lff and lff["scope"] == ["top"]
    assert not any("plan" in b for b in _bays(doc, "front-lff4") if b["id"].startswith("lff-drive-"))


def _translate(node):
    m = re.match(r"translate\(([-\d.]+),([-\d.]+)\)", node.get("transform", ""))
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)


def test_the_supply_plans_reach_the_interposer_board():
    # figure 8: the supplies' cans end where the power interposer board begins; they did not touch
    # Compared as rendered: `in: system-board` orders a plan, it does not move it into the board's
    # coordinates, so only the interposer takes the board's offset
    root = ET.parse(DIST / "r660xs.sff10-rc1-1a2a.top.svg").getroot()
    by_id = {n.get("id"): n for n in root.iter() if n.get("id")}
    pib_top = _translate(by_id["system-board"])[1] + float(by_id["system-board--pib"].get("y"))
    for plan in ("psu-1-plan", "psu-2-plan"):
        node = by_id[plan]
        can = next(r for r in node.iter() if r.tag.endswith("rect"))
        can_end = _translate(node)[1] + float(can.get("y")) + float(can.get("height"))
        assert abs(pib_top - can_end) <= 0.5, (plan, can_end, pib_top)


def test_the_chassis_floor_lies_beneath_the_system_board_in_3d():
    # a well is painted by its depth: the floor at the board's depth painted over the board.
    # The floor's well must be deeper than the board's, so the board stands above it
    svg = DIST / "r660xs.sff10-rc1-1a2a.top.svg"
    depth = {n.get("id"): float(n.get("data-depth")) for n in ET.parse(svg).iter()
             if n.get("id") in ("chassis-floor", "system-board") and n.get("data-depth")}
    assert set(depth) == {"chassis-floor", "system-board"}
    assert depth["chassis-floor"] > depth["system-board"]


# --- the DCIM device types -----------------------------------------------------

def _types():
    found = sorted((EXPORTS / "netbox" / "device-types" / "Dell").glob("PowerEdge R660xs *.yaml"))
    assert found, "no R660xs device type is exported: run ./publish.sh --no-images"
    return found


def test_the_device_types_are_one_u_and_full_depth():
    for f in _types():
        t = yaml.safe_load(f.read_text())
        assert t["u_height"] == 1.0, f.name
        assert t["is_full_depth"] is True, f.name


def test_a_device_type_is_exported_for_every_front_and_the_default():
    names = {f.stem.split(" ", 2)[2] for f in _types()}
    assert "sff10-rc1-1a2a" in names
    assert {n.split("-")[0] for n in names} == {"sff10", "sff8", "lff4"}

"""A back seen through a turned bay's rear cutout is turned with its module.

fs/fhd-4ufce stands twelve FHD modules on edge: its bays are 35.05 wide and
108.97 tall and say `rotate: 90`, so the occupant's 108.97 x 35.05 plate is
turned into them. The rear projection (`rear:`) was drawn unturned, a 99 x 31
cassette back lying across a 35.05-wide hole, and the enclosure could not say
where its backs were seen at all. The turn is the bay's own - a module on its
side shows its back on its side - and seen from behind a clockwise turn reads
anticlockwise, so the back is drawn at `rotate: -bay.rotate`, about the hole's
centre, with its footprint found in the bay's unturned box
(faces.rear_place). The hole says the turn for a swap to use
(`data-rear-rotate`), swap.js places a swapped-in back by the same rule, and
relief.js turns the module's body, and the back hung on it, in 3D.

The fixture is fs/fhd-1ufce cut down to one turned bay and one unturned one.
The cassette is the real fs/fhd-1mtp6lcd-os2-a@4, whose 99 x 31 body is
centred behind its plate; the stand-in's 60 x 30 body sits at the plate's left
end, so a turn the wrong way, or about the wrong point, lands it elsewhere.
"""
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import warmrender
from test_nested_occupants import LIB, SPEC

from portrayal.faces import rear_at, rear_place, rear_turn

CASSETTE = "fs/fhd-1mtp6lcd-os2-a@4"
ODD = "test/fhd-odd@1"
ODD_BACK = "test/fhd-odd-rear@1"
ODD_FP = {"at": [0.0, 3.0], "size": [60.0, 30.0]}
PLATE = {"w": 108.97, "h": 35.05}
TURNED = {"id": "bay-1", "at": [10.0, 5.0], "size": {"w": 35.05, "h": 108.97}, "rotate": 90}
CUT = {"id": "back-1", "at": [402.95, 5.0], "size": [35.05, 108.97], "depth": 431.8}
CENTRE = (402.95 + 35.05 / 2, 5.0 + 108.97 / 2)

SKIN = ('<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
        'viewBox="0 0 {w} {h}"><rect x="0" y="0" width="{w}" height="{h}" '
        'fill="#2a2d31"/></svg>\n')


def component(root, ref, data):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    d = root / "components" / ns / name / f"v{major}"
    (d / "skins").mkdir(parents=True)
    (d / "contract.yaml").write_text(yaml.safe_dump(
        {"format": 1, "kind": "component", "name": name, "version": f"{major}.0.0",
         "description": "test stand-in", **data, "skins": ["default"]}, sort_keys=False))
    (d / "skins" / "default.svg").write_text(SKIN.format(**data["size"]))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rear-turn")
    extra = tmp / "lib"
    component(extra, ODD, {
        "class": "adapter-panel", "size": dict(PLATE),
        "body": {"depth": 60.0, "footprint": ODD_FP}, "faces": {"rear": {"ref": ODD_BACK}}})
    component(extra, ODD_BACK, {"class": "adapter-panel", "size": {"w": 60.0, "h": 30.0}})
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp / "fhd") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    H = 120.0
    d["chassis"]["height"] = H
    for v in d["views"].values():
        v["size"]["h"] = H
        for dec in (v.get("panel") or {}).get("decor") or []:
            dec["size"][1] = H
    front = d["views"]["front"]["components"]
    first = front["bays"][0]
    front["bays"] = [
        {**first, **TURNED, "default": None, "accepts": [CASSETTE, ODD],
         "rear": {"view": "rear", "cutout": "back-1"}},
        {**first, "id": "bay-2", "at": [60.0, 5.0], "rel-pos": 2, "default": None,
         "accepts": [CASSETTE], "rear": {"view": "rear", "cutout": "back-2"}}]
    front["bays"][0].pop("rel-pos", None)
    front["bays"][0]["rel-pos"] = 1
    d["views"]["rear"]["panel"]["cutouts"] = [
        dict(CUT), {"id": "back-2", "at": [279.03, 5.0], "size": [108.97, 35.05], "depth": 431.8}]
    d["configurations"] = {
        "base": {"kind": "base", "default": True, "description": "empty"},
        "cas": {"kind": "example", "description": "c", "bays": {"bay-1": CASSETTE}},
        "odd": {"kind": "example", "description": "o", "bays": {"bay-1": ODD}}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / "o"
    r = warmrender.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--library", str(extra), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return {c: ET.parse(out / f"fhd-1ufce.{c}.rear.svg").getroot() for c in ("base", "cas", "odd")}


def by_id(root, nid):
    hits = [n for n in root.iter() if n.get("id") == nid]
    assert len(hits) == 1, (nid, len(hits))
    return hits[0]


def pose(el):
    m = re.fullmatch(r"translate\(([-\d.]+),\s*([-\d.]+)\)(?: rotate\(([-\d.]+) ([-\d.]+) ([-\d.]+)\))?",
                     el.get("transform") or "")
    assert m, el.get("transform")
    x, y, r, px, py = (float(g) if g is not None else None for g in m.groups())
    return x, y, r, px, py


def turned_box(x, y, w, h, deg):
    """The box a w x h drawing at (x, y), turned `deg` about its own centre, covers."""
    cx, cy = x + w / 2, y + h / 2
    w2, h2 = (h, w) if deg % 180 == 90 else (w, h)
    return cx - w2 / 2, cy - h2 / 2, cx + w2 / 2, cy + h2 / 2


def test_the_turn_is_the_bays_own_the_other_way_round():
    assert rear_turn(TURNED) == 270
    assert rear_turn({"rotate": 270}) == 90
    assert rear_turn({"rotate": 180}) == 180
    assert rear_turn({}) == 0


def test_an_unturned_bay_places_a_back_as_rear_at_does():
    bay = {"size": {"w": 100.0, "h": 40.0}}
    cut = {"at": [10.0, 5.0]}
    c = {"size": {"w": 100.0, "h": 40.0}, "body": {"footprint": {"at": [0, 3], "size": [60, 30]}}}
    assert rear_place(bay, cut, c, {"w": 60, "h": 30}) == {"at": rear_at(bay, cut, c), "rotate": 0}


def test_a_turned_back_keeps_its_body_at_the_end_the_module_turned_it_to():
    # a 100 x 40 module turned 90 into a 40 x 100 bay, its body at the plate's
    # LEFT end: turned clockwise at the front that end is at the TOP, and it
    # stays at the top from behind - touching the hole's top edge, 2 mm left
    # of its centre line (the body's 3 mm drop, turned and mirrored)
    bay = {"size": {"w": 40.0, "h": 100.0}, "rotate": 90}
    cut = {"at": [10.0, 5.0]}
    c = {"size": {"w": 100.0, "h": 40.0}, "body": {"footprint": {"at": [0, 3], "size": [60, 30]}}}
    p = rear_place(bay, cut, c, {"w": 60, "h": 30})
    assert p == {"at": [-2.0, 20.0], "rotate": 270}
    x0, y0, x1, y1 = turned_box(*p["at"], 60, 30, p["rotate"])
    assert (x0, y0, x1, y1) == pytest.approx((13.0, 5.0, 43.0, 65.0))
    # no drawing to measure: the footprint's own size stands in for it
    assert rear_place(bay, cut, c, {}) == p


def test_a_back_with_no_footprint_fills_the_turned_hole():
    bay = {"size": {"w": 40.0, "h": 100.0}, "rotate": 90}
    p = rear_place(bay, {"at": [10.0, 5.0]}, {"size": {"w": 100.0, "h": 40.0}}, {"w": 100, "h": 40})
    assert turned_box(*p["at"], 100, 40, p["rotate"]) == pytest.approx((10.0, 5.0, 50.0, 105.0))


@pytest.mark.parametrize("config, back", [("cas", (99.0, 31.0)), ("odd", (60.0, 30.0))])
def test_the_rendered_back_is_turned_and_lies_inside_its_hole(built, config, back):
    el = by_id(built[config], "bay-1-rear")
    x, y, r, px, py = pose(el)
    assert r == 270 and (px, py) == (back[0] / 2, back[1] / 2), el.get("transform")
    x0, y0, x1, y1 = turned_box(x, y, *back, r)
    cx0, cy0 = CUT["at"]
    cx1, cy1 = cx0 + CUT["size"][0], cy0 + CUT["size"][1]
    assert cx0 - 1e-6 <= x0 and x1 <= cx1 + 1e-6 and cy0 - 1e-6 <= y0 and y1 <= cy1 + 1e-6, \
        ((x0, y0, x1, y1), (cx0, cy0, cx1, cy1))
    hole = by_id(built[config], "cutout--back-1")
    assert hole.get("data-rear-rotate") == "270"
    assert tuple(map(float, hole.get("data-rear-at").split(","))) == pytest.approx((x, y))


def test_the_cassettes_centred_body_is_centred_in_the_hole(built):
    x, y, r, _, _ = pose(by_id(built["cas"], "bay-1-rear"))
    assert (x + 99.0 / 2, y + 31.0 / 2) == pytest.approx(CENTRE)


def test_the_off_centre_body_stays_at_the_top_end(built):
    # the stand-in's body is at its plate's left end, turned to the top at the
    # front and still at the top from behind: its turned box meets the hole's
    # top edge and runs 60 down it, 0.475 right of the centre line
    x, y, r, _, _ = pose(by_id(built["odd"], "bay-1-rear"))
    x0, y0, x1, y1 = turned_box(x, y, 60.0, 30.0, r)
    assert (x0, y0, x1, y1) == pytest.approx(
        (CENTRE[0] + 0.475 - 15.0, 5.0, CENTRE[0] + 0.475 + 15.0, 65.0))


def test_an_empty_turned_hole_still_says_its_turn(built):
    hole = by_id(built["base"], "cutout--back-1")
    assert hole.get("data-rear-rotate") == "270", "a swap into it would lie the back flat"
    assert hole.get("data-rear-at") is None
    # and an unturned hole says nothing about a turn
    assert by_id(built["base"], "cutout--back-2").get("data-rear-rotate") is None


def run_js(inp):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    script = SPEC / "tests/js/rear-turn.mjs"
    p = subprocess.run(["node", str(script), json.dumps(inp)], capture_output=True, text=True,
                       cwd=str(script.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


CASES = [
    # (bay, cutout at, contract, back)
    ({"size": {"w": 40.0, "h": 100.0}, "rotate": 90}, [10.0, 5.0],
     {"size": {"w": 100.0, "h": 40.0}, "body": {"footprint": {"at": [0, 3], "size": [60, 30]}}},
     {"w": 60.0, "h": 30.0}),
    ({"size": {"w": 40.0, "h": 100.0}, "rotate": 270}, [10.0, 5.0],
     {"size": {"w": 100.0, "h": 40.0}, "body": {"footprint": {"at": [0, 3], "size": [60, 30]}}},
     {"w": 60.0, "h": 30.0}),
    ({"size": {"w": 100.0, "h": 40.0}, "rotate": 180}, [10.0, 5.0],
     {"size": {"w": 100.0, "h": 40.0}, "body": {"footprint": {"at": [0, 3], "size": [60, 30]}}},
     {"w": 60.0, "h": 30.0}),
    ({"size": {"w": 35.05, "h": 108.97}, "rotate": 90}, CUT["at"],
     {"size": dict(PLATE), "body": {"footprint": {"at": [4.985, 2.025], "size": [99.0, 31.0]}}},
     {"w": 99.0, "h": 31.0}),
    ({"size": {"w": 108.97, "h": 35.05}}, [332.97, 4.475],
     {"size": dict(PLATE), "body": {"footprint": {"at": [10.485, 0.125], "size": [88.0, 34.8]}}},
     {"w": 88.0, "h": 34.8}),
]


def test_a_swap_places_a_turned_back_where_the_build_does():
    places = [{"box": f"{at[0]},{at[1]},{bay['size']['w']},{bay['size']['h']}",
               "comp": c, "turn": rear_turn(bay), "back": back} for bay, at, c, back in CASES]
    got = run_js({"places": places})["places"]
    want = [rear_place(bay, {"at": at}, c, back)["at"] for bay, at, c, back in CASES]
    assert got == [pytest.approx(w) for w in want]


def test_a_swapped_in_back_is_drawn_turned_about_its_own_centre():
    bay, at, c, back = CASES[0]
    out = run_js({"hole": {"box": "10,5,40,100", "turn": 270, "ref": "test/mod@1",
                           "comp": c, "back": back}})["hole"]
    assert out == {"transform": "translate(-2,20) rotate(270 30 15)", "at": "-2,20"}


def test_the_3d_body_turns_with_its_module():
    fp = {"at": [0, 3], "size": [60, 30]}
    rot90 = {"a": 0, "b": 1, "c": -1, "d": 0, "e": 50, "f": 0}
    half = {"a": -1, "b": 0, "c": 0, "d": -1, "e": 100, "f": 40}
    plain = {"a": 1, "b": 0, "c": 0, "d": 1, "e": 5, "f": 5}
    mirrored = {"a": -1, "b": 0, "c": 0, "d": 1, "e": 100, "f": 0}
    body = {"depth": 60, "footprint": fp}
    p90, p180, p0, pm = run_js({"poses": [{"m": m, "body": body}
                                          for m in (rot90, half, plain, mirrored)]})["poses"]
    # turned 90 clockwise on the drawing, the body stands 30 wide and 60 tall,
    # at the top - the face's y runs down and the scene's up, so -pi/2 in 3D
    assert p90["r"] == {"x": 17, "y": 0, "w": 30, "h": 60}
    assert p90["turn"] == pytest.approx(-1.5707963267948966)
    assert abs(abs(p180["turn"]) - 3.141592653589793) < 1e-9
    assert p180["r"] == {"x": 40, "y": 7, "w": 60, "h": 30}
    # unturned and mirrored modules are placed from their drawn box, as before
    assert p0 is None and pm is None


def test_a_turned_body_with_no_footprint_is_placed_from_its_drawn_box():
    # a body with no footprint fills its face, and the kit sizes that face from
    # the DRAWN box, already turned - through the module's frame it was turned
    # twice. An ASR 9006 slot-2 card (41.4 x 395.7, rotate 90 into a 395.7 x
    # 41.4 slot) and a Dell R740xd rear drive (rotate 270) keep the drawn-box
    # path, exactly as before the turn existed
    rot90 = {"a": 0, "b": 1, "c": -1, "d": 0, "e": 435.08, "f": 247.05}
    rot270 = {"a": 0, "b": -1, "c": 1, "d": 0, "e": 10, "f": 110}
    bare = {"depth": 300.0}
    out = run_js({"poses": [{"m": rot90, "body": bare}, {"m": rot270, "body": bare},
                            {"m": rot90, "body": None}]})["poses"]
    assert out == [None, None, None]

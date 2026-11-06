"""The two AC inlets of the MikroTik CRS312-4C+8XG-RM are drawn on its rear and offered as places a power cord lands.

The device used to leave its rear empty and say that no held document showed it, although the brochure's rear photograph shows
two IEC C14 inlets printed POWER 1 and POWER 2. The rear now places the library's std/c14-inlet@1 twice, where the photograph
puts them (the places are estimates read off a photograph taken slightly from above, good to about 2 mm):

  - the rear places two C14 inlets, `ac-inlet-1` and `ac-inlet-2`, each with a cut-out of its own size and a printed legend;
  - the two inlets stand on the chassis and do not overlap;
  - the export names two power ports of type iec-60320-c14 in both flavours, and a device that states AC power offers one;
  - the lock agrees with the sources and the finding of the part-conformance runner has no row left.

These read the device's sources, the committed exports and the records file. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FOLDER = LIB / "devices" / "mikrotik" / "crs312-4c-plus-8xg-rm"
INLET = "std/c14-inlet@1"
IDS = ["ac-inlet-1", "ac-inlet-2"]
INLET_W, INLET_H = 28.0, 20.0


def source(name):
    return yaml.safe_load((FOLDER / name).read_text())


@pytest.fixture(scope="module", params=["layout.yaml", "device.yaml"])
def rear(request):
    return source(request.param)["views"]["rear"]


def placements(rear):
    return {p["id"]: p for p in rear["components"]["placements"] if p.get("ref") == INLET}


def test_the_rear_is_drawn_and_places_two_c14_inlets(rear):
    assert "empty" not in rear
    assert sorted(placements(rear)) == IDS
    for p in placements(rear).values():
        assert p["group"] == "inlets"


def test_each_inlet_has_a_cutout_of_the_parts_size_where_it_stands(rear):
    cutouts = {c["id"]: c for c in rear["panel"]["cutouts"]}
    for i, p in placements(rear).items():
        assert cutouts[i]["at"] == p["at"] and cutouts[i]["size"] == [INLET_W, INLET_H]


def test_the_inlets_stand_on_the_rear_and_do_not_overlap(rear):
    size = rear["size"]
    boxes = sorted((p["at"][0], p["at"][1]) for p in placements(rear).values())
    for x, y in boxes:
        assert 0 <= x and x + INLET_W <= size["w"] and 0 <= y and y + INLET_H <= size["h"]
    assert boxes[0][0] + INLET_W < boxes[1][0]


def test_each_inlet_carries_the_legend_the_photograph_prints(rear):
    texts = {}
    for s in (s for s in rear["silkscreen"] if "text" in s):
        texts.setdefault(s["for"], []).append(s["text"])
    assert texts["ac-inlet-1"] == ["POWER 1", "100-240 V~1.5 A MAX 50/60 Hz"]
    assert texts["ac-inlet-2"] == ["POWER 2", "100-240 V~1.5 A MAX 50/60 Hz"]


SCREW = "common/screw-head@1"
FRONT_SHA = {
    "layout.yaml": "93529a70c14aa07b4caa5ec8921ac469cdbecf2aa6ca660d8c5c825f87553881",
    "device.yaml": "db4cc6460e639a76727c28596f85d3079d4ffcaa65556eac985b2bdbf3ae9dfe",
}


def centre(item, size=None):
    w, h = size or item["size"]
    return item["at"][0] + w / 2, item["at"][1] + h / 2


def test_the_rear_draws_four_fan_grilles_left_to_right_as_the_photograph_shows(rear):
    fans = sorted((d for d in rear["panel"]["decor"] if d.get("kind") == "fan-grille"), key=lambda d: d["at"][0])
    assert len(fans) == 4
    assert all(d.get("pattern") == "motif" and d.get("vent") for d in fans)
    xs = [centre(d)[0] for d in fans]
    inlets = sorted(centre(p, (INLET_W, INLET_H))[0] for p in placements(rear).values())
    # the first stands between the two inlets, the other three are to the right of the second
    assert inlets[0] < xs[0] < inlets[1] < xs[1] < xs[2] < xs[3]
    # the last two stand together, and the first of those two is nearer them than the one before
    assert xs[3] - xs[2] < xs[2] - xs[1] and xs[3] - xs[2] < 45
    for d in fans:
        assert d["size"][0] == d["size"][1] and 0 <= d["at"][1] and d["at"][1] + d["size"][1] <= rear["size"]["h"]


def test_the_fan_grilles_are_hexagon_rings_round_a_solid_hub_as_the_photograph_shows(rear):
    decor = rear["panel"]["decor"]
    fans = sorted((d for d in decor if d.get("kind") == "fan-grille"), key=lambda d: d["at"][0])
    hubs = sorted((d for d in decor if d.get("kind") == "fan-hub"), key=lambda d: d["at"][0])
    assert len(hubs) == 4
    for fan, hub in zip(fans, hubs):
        # the tile's origin is the fan's centre, where a hexagon of the lattice stands under the hub
        assert fan["pattern-offset"] == pytest.approx(centre(fan), abs=0.05)
        assert centre(hub) == pytest.approx(centre(fan), abs=0.05)
        assert 20 <= hub["size"][0] <= 24 and hub["rx"] == hub["size"][0] / 2
        # hexagons about 5.4 mm across, read at 3.38 px per mm on the photograph
        tw, th = fan["pattern-pitch"]
        hexagon = [c for c in fan["pattern-cells"] if len(c) == 6]
        assert len(hexagon) == 1
        xs = [p[0] for p in hexagon[0]]
        assert 5.0 <= max(xs) - min(xs) <= 5.8 and th == pytest.approx(5.88, abs=0.2) and tw == pytest.approx(2 * 5.092, abs=0.2)


def clip_paths(rear):
    return sorted((s for s in rear["silkscreen"] if "path" in s), key=lambda s: s["at"][0])


def test_each_inlet_has_a_wire_bale_clip_over_it_with_its_legs_outside_the_housing(rear):
    paths = clip_paths(rear)
    assert len(paths) == 6
    for inlet in placements(rear).values():
        mine = [s for s in paths if s["for"] == inlet["id"]]
        assert len(mine) == 3 and all(s["filled"] is False and s["stroke-width"] <= 0.8 for s in mine)
        # a bar over the top of the inlet with a bump up at its middle (a loop of wire)...
        (top,) = [s for s in mine if " C " in s["path"]]
        assert top["at"][1] < inlet["at"][1]
        assert top["at"][0] < inlet["at"][0] and top["at"][0] + 30.8 > inlet["at"][0] + INLET_W
        # ...and a leg down each side of the housing, outside it
        legs = sorted(s["at"][0] for s in mine if s is not top)
        assert legs[0] < inlet["at"][0] and legs[1] > inlet["at"][0] + INLET_W


def test_each_clip_has_a_white_pivot_tab_and_a_pin_each_side_of_its_inlet(rear):
    decor = rear["panel"]["decor"]
    tabs = sorted((d for d in decor if d.get("kind") == "clip-tab"), key=lambda d: d["at"][0])
    pins = sorted((d for d in decor if d.get("kind") == "clip-pin"), key=lambda d: d["at"][0])
    inlets = sorted(placements(rear).values(), key=lambda p: p["at"][0])
    assert len(tabs) == 4 and len(pins) == 4
    for n, inlet in enumerate(inlets):
        left, right = tabs[2 * n], tabs[2 * n + 1]
        assert left["at"][0] + left["size"][0] <= inlet["at"][0] + 0.5 and right["at"][0] >= inlet["at"][0] + INLET_W - 0.5
        for tab in (left, right):
            assert inlet["at"][1] < tab["at"][1] and tab["at"][1] + tab["size"][1] < inlet["at"][1] + INLET_H
        # each pin runs out from its tab to the side, level with the tab's middle
        assert pins[2 * n]["at"][0] + pins[2 * n]["size"][0] <= left["at"][0] + 0.2
        assert pins[2 * n + 1]["at"][0] >= right["at"][0] + right["size"][0] - 0.2


# Read from the brochure's rear photograph away from text and ports (median of a patch, or the darkest few percent of a thin line)
COLOURS = {
    "clip wire": "#666667",
    "pivot tab": "#e9eaf0",
    "pin": "#f7f7f9",
    "legend": "#363633",
}


def test_the_rear_colours_are_the_ones_read_from_the_photograph(rear):
    decor = rear["panel"]["decor"]
    assert {s["fill"] for s in clip_paths(rear)} == {COLOURS["clip wire"]}
    assert {d["fill"] for d in decor if d.get("kind") == "clip-tab"} == {COLOURS["pivot tab"]}
    assert {d["fill"] for d in decor if d.get("kind") == "clip-pin"} == {COLOURS["pin"]}
    assert {s["fill"] for s in rear["silkscreen"] if "text" in s} == {COLOURS["legend"]}


def test_the_body_colour_stays_the_face_colour_on_the_rear(rear):
    source = source_of_rear_colour()
    assert source == "#c4c4ca"
    for d in rear["panel"]["decor"]:
        if d.get("kind") == "fan-hub":
            assert d["fill"] == source


def source_of_rear_colour():
    return source("layout.yaml")["chassis"]["color"]


def test_the_rear_carries_twelve_crosshead_screws_from_the_screw_part(rear):
    screws = [p for p in rear["components"]["placements"] if p.get("ref") == SCREW]
    assert len(screws) == 12
    assert [p["rel-pos"] for p in screws] == list(range(1, 13))
    xs = [p["at"][0] for p in screws]
    assert xs == sorted(xs)
    assert {p["group"] for p in screws} == {"furniture"}
    for p in screws:
        assert 0 <= p["at"][0] and p["at"][0] <= rear["size"]["w"] and 0 <= p["at"][1] <= rear["size"]["h"]


def test_the_only_printing_is_the_two_legends_under_the_inlets_in_order(rear):
    lines = sorted((s for s in rear["silkscreen"] if "text" in s), key=lambda s: (s["at"][0], s["at"][1]))
    assert [s["text"] for s in lines] == [
        "POWER 1",
        "100-240 V~1.5 A MAX 50/60 Hz",
        "POWER 2",
        "100-240 V~1.5 A MAX 50/60 Hz",
    ]
    inlets = {p["id"]: p for p in placements(rear).values()}
    for s in lines:
        inlet = inlets[s["for"]]
        assert s["at"][1] > inlet["at"][1] + INLET_H
        assert abs(s["at"][0] - (inlet["at"][0] + INLET_W / 2)) < 0.5


@pytest.mark.parametrize("name", ["layout.yaml", "device.yaml"])
def test_the_front_is_unchanged(name):
    import hashlib
    import json

    front = json.dumps(source(name)["views"]["front"], sort_keys=True)
    assert hashlib.sha256(front.encode()).hexdigest() == FRONT_SHA[name]


def test_the_inlets_group_is_declared():
    for name in ("layout.yaml", "device.yaml"):
        assert "inlets" in source(name)["groups"], name


def test_the_rear_gap_no_longer_says_the_inlets_are_not_placed():
    for name in ("layout.yaml", "device.yaml"):
        for gap in source(name)["gaps"]:
            assert "no AC inlet is placed" not in " ".join(str(gap.get("note", "")).split()), (name, gap["what"])
            assert gap["what"] not in ("rear-face", "rear-fans-and-screws"), name


@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
def test_the_export_names_two_c14_power_ports(flavour):
    path = LIB / "exports" / flavour / "device-types" / "MikroTik" / "CRS312-4C+8XG-RM.yaml"
    doc = yaml.safe_load(path.read_text())
    assert [(p["name"], p["type"]) for p in doc["power-ports"]] == [(i, "iec-60320-c14") for i in IDS]


@pytest.mark.heavy
def test_the_lock_agrees_with_the_sources():
    from portrayal import devicelock

    assert [f for f in devicelock.check(LIB) if f[0] == "mikrotik/crs312-4c-plus-8xg-rm"] == []


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == "crs312-4c-plus-8xg-rm"] == []

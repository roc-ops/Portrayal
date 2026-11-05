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
    for s in rear["silkscreen"]:
        texts.setdefault(s["for"], []).append(s["text"])
    assert texts["ac-inlet-1"] == ["POWER 1", "100-240 V~1.5 A MAX 50/60 Hz"]
    assert texts["ac-inlet-2"] == ["POWER 2", "100-240 V~1.5 A MAX 50/60 Hz"]


def test_the_inlets_group_is_declared():
    for name in ("layout.yaml", "device.yaml"):
        assert "inlets" in source(name)["groups"], name


def test_the_rear_gap_no_longer_says_the_inlets_are_not_placed():
    for name in ("layout.yaml", "device.yaml"):
        for gap in source(name)["gaps"]:
            assert "no AC inlet is placed" not in " ".join(str(gap.get("note", "")).split()), (name, gap["what"])
            assert gap["what"] != "rear-face", name


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

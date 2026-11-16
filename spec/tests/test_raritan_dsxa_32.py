"""The Raritan Dominion SX DSXA-32: the first-generation 32-port serial console server.

Sources: the Dominion SX data sheet (V1008R3) for the model table and the labelled rear photograph.
The Quick Setup Guide v3.5 gives the connection figure, and the User Guide v3.5 gives the port numbering and the dimension table.
No drawing is held, so every position is an estimate. The tests hold counts, ids, roles and declarations, not a coordinate.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/raritan/dsxa-32"
PITCH = 13.97


@pytest.fixture(scope="module")
def dev():
    return yaml.safe_load((DEVICE / "device.yaml").read_text())


def placements(d, view):
    return {p["id"]: p for p in d["views"][view]["components"].get("placements", [])}


def test_the_device_is_the_part_number_the_data_sheet_orders(dev):
    assert dev["name"] == "dsxa-32"
    assert dev["model"] == "DSXA-32"
    assert list(dev["configurations"]["base"]["part-numbers"]) == ["DSXA-32"]


def test_the_body_is_the_data_sheets_440_by_290_by_44_millimetres(dev):
    chassis = dev["chassis"]
    assert (chassis["width"], chassis["depth"], chassis["height"], chassis["ru"]) == (440, 290, 44, 1)


def test_the_rear_carries_one_numbered_serial_port_for_each_of_the_32_ports(dev):
    rear = placements(dev, "rear")
    serial = {i: p for i, p in rear.items() if p.get("group", "").startswith("serial-")}
    assert set(serial) == {f"serial-{n}" for n in range(1, 33)}
    assert sorted(p["rel-pos"] for p in serial.values()) == list(range(1, 33))


def test_each_group_of_four_is_numbered_along_the_lower_row_and_then_the_upper_row(dev):
    rear = placements(dev, "rear")
    for first in (1, 9, 17, 25):
        lower = [rear[f"serial-{first + c}"]["at"] for c in range(4)]
        upper = [rear[f"serial-{first + 4 + c}"]["at"] for c in range(4)]
        assert [round(b[0] - a[0], 2) for a, b in zip(lower, lower[1:])] == [PITCH] * 3
        assert [p[0] for p in lower] == [p[0] for p in upper]
        assert max(p[1] for p in upper) < min(p[1] for p in lower)


def test_the_rear_carries_two_inlets_with_switches_a_modem_a_db9_and_one_ethernet_jack(dev):
    rear = placements(dev, "rear")
    assert {"inlet-1", "inlet-2", "power-switch-1", "power-switch-2", "modem", "console", "lan-1", "reset"} <= set(rear)
    assert rear["inlet-1"]["ref"] == "std/c14-inlet@1"
    assert rear["modem"]["ref"] == "common/rj11-jack@1"
    assert rear["console"]["ref"] == "std/db9@1"
    assert not [i for i in rear if i.startswith("lan-") and i != "lan-1"]


def test_every_lamp_is_drawn_off_and_has_a_lit_state(dev):
    lamps = [p for v in ("front", "rear") for p in placements(dev, v).values() if p["ref"].startswith("common/led-dot")]
    assert len(lamps) == 4
    assert len(placements(dev, "rear")) and sum(p["ref"].startswith("common/led-dot") for p in placements(dev, "rear").values()) == 3
    assert [p["id"] for p in placements(dev, "front").values() if p["ref"].startswith("common/led-dot")] == ["led-front"]
    for p in lamps:
        assert p["states"][0] == "off" and len(p["states"]) > 1
        assert "behavior" not in str(p["states"])


def test_the_front_and_the_sides_declare_their_source_and_the_missing_photograph(dev):
    assert "front-photo" in {g["what"] for g in dev["gaps"]}


def front_rows(d):
    return [x for x in d["views"]["front"]["panel"]["decor"] if x["id"].startswith("bezel-row-")]


def test_the_three_vents_are_drawn_as_patterns_and_declared_as_air(dev):
    assert len(front_rows(dev)) == 7
    for row in front_rows(dev):
        assert (row["pattern"], row["pattern-pitch"], row["vent"]) == ("holes", [5.63, 4.3], 1.0)
        assert "fill" not in row
    right = {d["id"]: d for d in dev["views"]["right"]["panel"]["decor"]}["side-vent"]
    left = {d["id"]: d for d in dev["views"]["left"]["panel"]["decor"]}["side-vent"]
    assert (right["pattern"], right["pattern-pitch"], right["vent"]) == ("slots-h", [12.0, 5.6], 1.0)
    assert (left["pattern"], left["pattern-pitch"], left["vent"]) == ("holes", [9.6, 5.6], 1.0)
    for side in (left, right):
        assert side["size"][1] == 16.8 and "fill" not in side
    assert right["at"] == [45.5, 16.9] and left["at"] == [17.0, 18.6]
    assert right["size"][0] == 204.0 and left["size"][0] == 228.0


def test_the_two_side_walls_are_drawn_from_their_own_pictures_and_not_mirrored(dev):
    left = {d["id"]: d for d in dev["views"]["left"]["panel"]["decor"]}["side-vent"]
    right = {d["id"]: d for d in dev["views"]["right"]["panel"]["decor"]}["side-vent"]
    assert (left["pattern"], left["pattern-pitch"], left["at"]) != (right["pattern"], right["pattern-pitch"], right["at"])
    assert left["pattern"] != right["pattern"]
    text = (str(dev["gaps"]) + str(dev["provenance"])).lower()
    assert "no picture shows the left wall" not in text and "no document shows this one" not in text


def test_the_front_holes_are_a_staggered_lattice_drawn_one_pattern_per_row(dev):
    # first hole centre and hole count of each row, counted by pixel runs on the oblique photograph
    expected = [(48.8, 12.1, 9), (52.3, 16.4, 9), (50.6, 20.7, 56), (53.4, 25.0, 55), (56.2, 29.3, 54), (59.2, 33.6, 54), (67.7, 37.9, 50)]
    rows = front_rows(dev)
    assert [r["id"] for r in rows] == [f"bezel-row-{n}" for n in range(1, 8)]
    for row, (x, y, holes) in zip(rows, expected):
        assert row["at"] == [x, y] and row["size"][1] == 4.2
        assert round(row["size"][0] / 5.63) == holes
        assert row["pattern-offset"][0] == x
    # the full-length rows 3 to 6 are offset by half a pitch (2.8 mm) from the row above, never by none
    firsts = [r["at"][0] for r in rows[2:6]]
    for a, b in zip(firsts, firsts[1:]):
        assert (b - a) % 5.63 == pytest.approx(2.8, abs=0.3)
    gap = next(g for g in dev["gaps"] if g["what"] == "front-holes")
    assert "square" not in gap["note"].lower() and "7 rows" not in gap["note"]


def test_the_one_front_lamp_sits_where_the_photograph_shows_the_blue_mark(dev):
    lamp = placements(dev, "front")["led-front"]
    assert lamp["at"] == [366.0, 11.0]


def test_the_three_lid_tabs_are_drawn_on_the_top_edge_of_the_rear(dev):
    tabs = [d for d in dev["views"]["rear"]["panel"]["decor"] if d["id"].startswith("lid-tab-")]
    assert [t["id"] for t in tabs] == ["lid-tab-1", "lid-tab-2", "lid-tab-3"]
    assert [t["at"] for t in tabs] == [[85.6, 1.7], [215.4, 1.7], [345.3, 1.7]]
    assert all(t["size"] == [10.0, 1.7] for t in tabs)
    assert tabs[1]["at"][0] - tabs[0]["at"][0] == pytest.approx(tabs[2]["at"][0] - tabs[1]["at"][0], abs=0.2)


def test_no_legend_is_drawn_that_the_pictures_of_this_model_cannot_read(dev):
    texts = [s.get("text") for s in dev["views"]["rear"].get("silkscreen", []) if "text" in s]
    assert "TERMINAL" not in texts and "RESET" not in texts
    assert "printed TERMINAL" not in str(dev["groups"])


def test_every_feature_left_out_has_a_gap_row(dev):
    assert {"front-holes", "side-slot-rows", "legends", "lid-tabs", "top-and-bottom", "db9-colour"} <= {g["what"] for g in dev["gaps"]}
    tabs = next(g for g in dev["gaps"] if g["what"] == "lid-tabs")
    assert "none is placed" not in tabs["note"] and "too small" not in tabs["note"]

"""The SRCABLEDUCT1UHD is drawn from the photographs on its spec sheet: ten pockets in each wall and the
cover's four tabs and label plate. What the test reads is the library's own files, so it needs no build."""
import re
from pathlib import Path

import yaml

LIB = Path(__file__).resolve().parents[2] / "library"
PARTS = LIB / "components/eaton"
DEVICE = LIB / "devices/eaton/srcableduct1uhd/device.yaml"

POCKETS, GAP, PITCH, FIELD = 10, 34.0, 40.9, 402.1
DIVIDER = 6.9
WINDOW = [16.0, 8.0]
WALL_X, DUCT_W, COVER_H = 25.4, 431.8, 51.82


def load(path):
    return yaml.safe_load(Path(path).read_text())


def device():
    return load(DEVICE)


def part(name):
    return load(PARTS / f"tripplite-duct-1uhd-{name}/v1/contract.yaml")


def test_each_wall_has_ten_pockets_on_one_pitch():
    doc = device()
    for view in ("top", "bottom"):
        slots = [d for d in doc["views"][view]["panel"]["decor"] if re.fullmatch(r"slot-\d+", d["id"])]
        slots.sort(key=lambda d: d["at"][0])
        assert len(slots) == POCKETS, view
        assert all(d["size"][0] == GAP for d in slots), view
        assert [round(b["at"][0] - a["at"][0], 3) for a, b in zip(slots, slots[1:])] == [PITCH] * (POCKETS - 1), view
        # closed pockets inside the wall, as drawn before
        assert slots[0]["at"][0] > WALL_X and slots[-1]["at"][0] + GAP < WALL_X + DUCT_W
    guide = doc["views"]["front"]["guides"][0]
    assert guide["finger-pitch"] == PITCH and guide["finger-gap"] == GAP


def test_the_fingers_part_draws_eleven_dividers_and_ten_pockets():
    c = part("fingers")
    fingers = sorted((e for k, e in c["elements"].items() if re.fullmatch(r"f\d+", k)), key=lambda e: e["at"][0])
    assert len(fingers) == POCKETS + 1
    # the end dividers run to the ends, the pockets between dividers are the 34.0 mm gap on the 40.9 pitch
    gaps = [round(b["at"][0] - (a["at"][0] + a["size"][0]), 3) for a, b in zip(fingers, fingers[1:])]
    assert gaps == [GAP] * POCKETS
    assert round(fingers[0]["at"][0] + 0, 3) == 0 and round(fingers[-1]["at"][0] + fingers[-1]["size"][0], 3) == DUCT_W
    skin = (PARTS / "tripplite-duct-1uhd-fingers/v1/skins/default.svg").read_text()
    assert sorted(re.findall(r'id="(f\d+)"', skin), key=lambda s: int(s[1:])) == [f"f{i}" for i in range(POCKETS + 1)]
    assert "ten pockets" in c["provenance"]["pitch"].lower()


def test_the_cover_draws_four_tabs_and_a_label_plate_inside_its_plate():
    c = part("cover")
    size_w, size_h = c["size"]["w"], c["size"]["h"]
    wanted = ["tab-1", "tab-1-strap", "tab-2", "tab-3", "tab-4", "label"]
    assert all(k in c["elements"] for k in wanted)
    for k in wanted:
        x, y = c["elements"][k]["at"]
        w, h = c["elements"][k]["size"]
        assert 0 <= x and x + w <= size_w and 0 <= y and y + h <= size_h + 1e-6, k
    skin = (PARTS / "tripplite-duct-1uhd-cover/v1/skins/default.svg").read_text()
    for k in wanted:
        assert f'id="{k}"' in skin, k
    text = yaml.safe_dump(c["provenance"]).lower()
    assert "estimated" in text and "photograph" in text
    # The parts of the cover run left to right: a high tab, a low tab, the label plate, a low tab, a high tab.
    # A larger y is lower on the plate. So tab 1 is above tab 2, and tab 4 is above tab 3.
    ys = [c["elements"][f"tab-{i}"]["at"][1] for i in (1, 2, 3, 4)]
    assert ys[0] < ys[1] and ys[1] > ys[2] and ys[2] > ys[3]
    xs = [c["elements"][k]["at"][0] for k in ("tab-1", "tab-2", "label", "tab-3", "tab-4")]
    assert xs == sorted(xs)


def test_the_device_says_how_the_pockets_and_tabs_were_found():
    notes = device()["provenance"]
    assert "ten" in notes["guides"]["note"].lower() and "photograph" in notes["guides"]["note"].lower()
    assert "tab" in notes["cover"]["note"].lower()
    assert "nine pockets" not in notes["guides"]["note"].lower().replace("not nine", "")


def test_the_dividers_are_six_point_nine_wide_wherever_they_are_given():
    c = part("fingers")
    fingers = sorted((e for k, e in c["elements"].items() if re.fullmatch(r"f\d+", k)), key=lambda e: e["at"][0])
    assert [e["size"][0] for e in fingers[1:-1]] == [DIVIDER] * (POCKETS - 1)
    assert round(PITCH - GAP, 3) == DIVIDER
    assert "6.9 mm" in device()["provenance"]["guides"]["note"]
    assert "6.9 mm" in c["provenance"]["pitch"]
    assert "12.0 mm divider" not in yaml.safe_dump(device()) + yaml.safe_dump(c)


def test_the_right_end_draws_its_see_through_window_and_the_left_end_does_not():
    doc = device()
    right = doc["views"]["right"]
    w, h = right["size"]["w"], right["size"]["h"]
    outline = [d for d in right["panel"]["decor"] if d["id"] == "window-outline"]
    assert len(outline) == 1 and outline[0]["size"] == WINDOW
    x, y = outline[0]["at"]
    assert 0 <= x and x + WINDOW[0] <= w and 0 <= y and y + WINDOW[1] <= h
    assert "window-outline" not in str(doc["views"]["left"])
    # the sheet shows no cable crossing it, so no pass-through is declared
    assert "passes" not in right["panel"]
    note = doc["provenance"]["right"]
    assert note["confidence"] == "estimated" and "window" in note["note"].lower()


def test_what_cannot_be_counted_or_was_left_out_is_said_with_its_figures():
    notes = device()["provenance"]
    guides = " ".join(notes["guides"]["note"].split())
    assert "cover-off front shows faint ticks only" in guides and "is not counted" in guides
    cover = " ".join(notes["cover"]["note"].split())
    assert "notch" in cover and "3 px" in cover
    text = " ".join(yaml.safe_dump(device(), width=10000).split())
    assert "user manual" not in text.lower() and "owner" not in text.lower()
    assert "SRCABLEDUCT1UHD manual" in text

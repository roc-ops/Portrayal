"""The MX240 normal-capacity AC supply's face follows its hardware guide's Figure 14.

The first drawing of the face carried the DC unit's lamp row and a vent field that covered only the upper left, so the C20
inlet had no place beside the input switch where the figure puts it. The face is redrawn as a new major, `v2`, and the old
major is kept, superseded:

  - the inlet stands beside the input switch, at the same height, and clear of every other box;
  - the three lamps stand in a column at the right edge, labelled as the guide's AC power supply LED table labels them;
  - the vent slots run across the face, in five columns, and leave the switch, inlet, handle and lamps clear;
  - the pull handle lies along the foot of the face, under the inlet;
  - every colour is one the first drawing already used, and the face says where each position comes from and how it was read;
  - the MX240 seats the new major in its four supply bays and its `ac` configuration.

These parse the contracts, the skins and the device file. They render nothing and read no library/dist.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
PSU = LIB / "components" / "juniper" / "mx240-psu-ac"
INLET = LIB / "components" / "std" / "c20-inlet" / "v1" / "contract.yaml"
DEVICE = LIB / "devices" / "juniper" / "mx240" / "device.yaml"
SVG = "{http://www.w3.org/2000/svg}"


def contract(major):
    return yaml.safe_load((PSU / f"v{major}" / "contract.yaml").read_text())


def skin(major):
    return ET.fromstring((PSU / f"v{major}" / "skins" / "default.svg").read_text())


def group(root, ident):
    found = [g for g in root.iter(f"{SVG}g") if g.get("id") == ident]
    assert len(found) == 1, ident
    return found[0]


def box(el):
    return (float(el.get("x")), float(el.get("y")), float(el.get("width")), float(el.get("height")))


def circle_box(el):
    cx, cy, r = float(el.get("cx")), float(el.get("cy")), float(el.get("r"))
    return (cx - r, cy - r, 2 * r, 2 * r)


def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def boxes():
    """The drawn boxes of v2 by name: elements, the composed inlet, and the skin's own groups."""
    d = contract(2)
    inlet = yaml.safe_load(INLET.read_text())["size"]
    x, y = d["parts"][0]["at"]
    out = {"inlet": (x, y, inlet["w"], inlet["h"])}
    out.update({k: (*v["at"], *v["size"]) for k, v in d["elements"].items()})
    return out


def lamps():
    return [(c.get("id"), float(c.get("cx")), float(c.get("cy")), float(c.get("r")))
            for c in group(skin(2), "lamps").iter(f"{SVG}circle")]


def legends():
    return [(t.text, float(t.get("x")), float(t.get("y"))) for t in group(skin(2), "silkscreen").iter(f"{SVG}text")]


def slots():
    return [box(r) for r in group(skin(2), "vents").iter(f"{SVG}rect")]


def test_the_face_is_a_new_major_and_the_old_major_is_kept_superseded():
    assert (PSU / "v1" / "contract.yaml").is_file() and (PSU / "v2" / "contract.yaml").is_file()
    assert contract(1)["superseded-by"] == "juniper/mx240-psu-ac@2"
    assert "superseded-by" not in contract(2)
    assert contract(2)["version"].startswith("2.")
    assert contract(1)["version"].startswith("1.") and "parts" not in contract(1)


def test_the_inlet_stands_beside_the_input_switch_at_the_same_height():
    b = boxes()
    inlet, switch = b["inlet"], b["breaker"]
    assert 0 <= inlet[0] - (switch[0] + switch[2]) <= 3.0
    shared = min(inlet[1] + inlet[3], switch[1] + switch[3]) - max(inlet[1], switch[1])
    assert shared >= 0.8 * inlet[3]


def test_the_lamps_stand_in_a_column_at_the_right_edge_with_the_guides_legends():
    w = contract(2)["size"]["w"]
    found = lamps()
    assert len(found) == 3
    xs = {round(cx, 2) for _, cx, _, _ in found}
    ys = [cy for _, _, cy, _ in found]
    assert len(xs) == 1 and min(xs) >= 0.9 * w
    assert ys == sorted(ys) and len({round(b - a, 1) for a, b in zip(ys, ys[1:])}) == 1
    text = legends()
    assert [t for t, _, _ in text] == ["AC OK", "DC OK", "PS FAIL"]
    for (_, cx, cy, _), (_, x, y) in zip(found, text):
        assert x < cx and abs(y - cy) <= 1.0


def test_the_vent_slots_run_across_the_face_and_leave_every_other_box_clear():
    d = contract(2)
    w, h = d["size"]["w"], d["size"]["h"]
    found = slots()
    assert min(x for x, _, _, _ in found) <= 0.2 * w
    assert max(x + sw for x, _, sw, _ in found) >= 0.8 * w
    assert len({round(x) for x, _, _, _ in found if x < 0.9 * w}) >= 5
    others = list(boxes().values()) + [circle_box(c) for c in group(skin(2), "lamps").iter(f"{SVG}circle")]
    for slot in found:
        assert 0 <= slot[0] and slot[0] + slot[2] <= w and 0 <= slot[1] and slot[1] + slot[3] <= h
        for other in others:
            assert not overlap(slot, other), (slot, other)


def test_the_handle_lies_along_the_foot_of_the_face_under_the_inlet():
    b = boxes()
    handle, inlet = b["handle"], b["inlet"]
    w, h = contract(2)["size"]["w"], contract(2)["size"]["h"]
    assert handle[1] >= inlet[1] + inlet[3] and handle[0] <= 0.5 * w and handle[0] + handle[2] >= 0.9 * w
    assert handle[1] + handle[3] <= h


def test_every_drawn_shape_lies_inside_the_face_and_clear_of_the_other_boxes():
    d = contract(2)
    w, h = d["size"]["w"], d["size"]["h"]
    b = boxes()
    names = list(b)
    for i, a in enumerate(names):
        assert 0 <= b[a][0] and b[a][0] + b[a][2] <= w and 0 <= b[a][1] and b[a][1] + b[a][3] <= h, a
        for other in names[i + 1:]:
            assert not overlap(b[a], b[other]), (a, other)
    for c in group(skin(2), "lamps").iter(f"{SVG}circle"):
        for name, other in b.items():
            assert not overlap(circle_box(c), other), (c.get("id"), name)


def test_every_colour_is_one_the_first_drawing_used():
    colours = lambda major: set(re.findall(r"#[0-9a-fA-F]{6}", (PSU / f"v{major}" / "skins" / "default.svg").read_text()))
    assert colours(2) <= colours(1)


def test_the_face_names_its_figure_and_says_how_the_positions_were_read():
    text = contract(2)["provenance"]
    face = text["face"]
    assert "Figure 14" in face and face.startswith("ESTIMATED") and "400 dpi" in face and "share" in face
    assert "Figure 14" in text["inlet"] and "ESTIMATE" in text["inlet"]
    assert "AC OK" in text["leds"] and "Table 17" in text["leds"]


def test_the_mx240_seats_the_new_major_in_its_ac_configuration_and_its_bays_accept_it():
    text = DEVICE.read_text()
    assert len(re.findall(r"pem\d: juniper/mx240-psu-ac@2\n", text)) == 4
    assert len(re.findall(r"accepts: \[[^\]]*juniper/mx240-psu-ac@2", text)) == 4

"""The DVI-D jack has a cable end: `generic/dvi-d-plug@1` mates the `dvi-d` key.

What is true of the library once it is in it: the plug mates the key the jack presents, it states the
figures the Digital Display Working Group's Digital Visual Interface specification, Revision 1.0, prints
for a digital plug (Figure 5-5, page 47) as numbers in the contract and the skin, it declares which figures
it estimates, and its skin is the plug seen from the cable end.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"

KEY = "dvi-d"
PLUG_DIR = LIB / "components/generic/dvi-d-plug/v1"


def contract():
    return yaml.safe_load((PLUG_DIR / "contract.yaml").read_text())


def skin():
    root = ET.parse(PLUG_DIR / "skins/default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def standards():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def features():
    return {f["node"]: f for f in contract()["relief"]["features"]}


def test_the_plug_mates_the_key_the_jack_presents():
    c = contract()
    jack = yaml.safe_load((LIB / "components/std/dvi-d-jack/v1/contract.yaml").read_text())
    assert c["class"] == "port" and c["mates"] == KEY and jack["interface"] == KEY
    assert c["attrs"]["media"] == jack["attrs"]["media"] == KEY
    assert c["attrs"]["gender"] == "male"
    assert c["connection-points"]["mate"]["direction"] == "front"


def shell_box(ids=None):
    """The bounding box of the shell path: the end point of every M, L and A segment."""
    tokens = re.findall(r"[MLAZ]|-?\d+\.?\d*", (ids or skin())["shell"].get("d"))
    xs, ys, i = [], [], 0
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == "Z":
            continue
        n = 7 if cmd == "A" else 2
        args = [float(t) for t in tokens[i:i + n]]
        i += n
        xs.append(args[-2])
        ys.append(args[-1])
    return min(xs), min(ys), max(xs), max(ys)


def test_the_plug_conforms_to_its_standards_entry_at_the_outline_the_figure_prints():
    c = contract()
    entry = standards()[c["conforms"]]
    assert (c["size"]["w"], c["size"]["h"]) == (entry["w"], entry["h"]) == (39.5, 15.13)
    assert c["size-confidence"] == {"w": "drawing", "h": "drawing"}
    assert entry["confidence"] == "drawing"


def test_the_skin_draws_the_outline_the_contract_states():
    ids = skin()
    hood = ids["hood"]
    assert (float(hood.get("width")), float(hood.get("height"))) == (39.5, 15.13)
    assert (float(hood.get("x")), float(hood.get("y"))) == (0, 0)
    size = contract()["size"]
    assert (size["w"], size["h"]) == (39.5, 15.13)


def test_the_shell_is_24_16_by_7_90_and_centred_on_the_mate_point():
    x0, y0, x1, y1 = shell_box()
    assert abs((x1 - x0) - 24.16) < 0.005 and abs((y1 - y0) - 7.90) < 0.005
    mate = contract()["connection-points"]["mate"]["at"]
    assert mate == [19.75, 7.565]
    assert abs((x0 + x1) / 2 - mate[0]) < 0.005 and abs((y0 + y1) / 2 - mate[1]) < 0.005
    assert features()["shell"]["out"] == 6.5


def test_the_jackscrews_are_32_51_apart_level_and_centred_on_the_mate_point():
    ids = skin()
    left, right = ids["screw-l"], ids["screw-r"]
    assert abs(float(right.get("cx")) - float(left.get("cx")) - 32.51) < 0.005
    assert float(left.get("cy")) == float(right.get("cy")) == 7.565
    mate = contract()["connection-points"]["mate"]["at"]
    assert abs((float(left.get("cx")) + float(right.get("cx"))) / 2 - mate[0]) < 0.005
    assert float(left.get("r")) == float(right.get("r")) == 1.6


def test_the_stub_leaves_from_the_mate_point():
    ids = skin()
    mate = contract()["connection-points"]["mate"]["at"]
    stub = ids["stub"]
    assert [float(stub.get("cx")), float(stub.get("cy"))] == mate
    assert float(stub.get("r")) * 2 == contract()["fields"]["cable-od"]["default"]
    assert features()["stub"]["cyl"] == 30
    cable = contract()["connection-points"]["cable"]
    assert cable["at"] == mate and cable["on"] == "stub"


def test_the_cable_end_draws_no_contacts_and_the_contract_records_them():
    c = contract()
    assert "contacts" in c["provenance"]
    assert not [i for i in skin() if i.startswith(("pin-", "cell-", "blade"))]


MATING_DIR = LIB / "components/generic/dvi-d-plug-mating/v1"


def mating_contract():
    return yaml.safe_load((MATING_DIR / "contract.yaml").read_text())


def mating_skin():
    root = ET.parse(MATING_DIR / "skins/default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def centre(e):
    return (float(e.get("x")) + float(e.get("width")) / 2, float(e.get("y")) + float(e.get("height")) / 2)


def pins():
    ids = mating_skin()
    return {n: centre(ids[f"pin-{n}"]) for n in range(1, 25)}


def test_the_plug_shows_its_mating_face_as_the_rear_face_component():
    c = contract()
    assert c["faces"] == {"rear": {"ref": "generic/dvi-d-plug-mating@1"}}
    m = mating_contract()
    assert (m["name"], m["version"]) == ("dvi-d-plug-mating", "1.0.0")
    assert m["size"] == c["size"] == {"w": 39.5, "h": 15.13}


def test_the_mating_face_has_24_contacts_in_three_rows_of_eight():
    ids = mating_skin()
    assert sorted(i for i in ids if i.startswith("pin-")) == sorted(f"pin-{n}" for n in range(1, 25))
    rows = sorted({round(y, 3) for _, y in pins().values()})
    assert len(rows) == 3
    for ry in rows:
        assert len([1 for _, y in pins().values() if round(y, 3) == ry]) == 8


def test_the_contacts_are_numbered_as_the_figure_numbers_them():
    p = pins()
    top, mid, bot = (sorted(y for _, y in p.values())[i] for i in (0, 8, 16))
    for n in range(1, 25):
        row = (n - 1) // 8 if n <= 8 else 1 if n <= 16 else 2
        assert abs(p[n][1] - (top, mid, bot)[row]) < 0.005, n
    # top row 8..1, middle 16..9, bottom 24..17, left to right: pin 1 upper right, pin 24 lower left
    for first in (1, 9, 17):
        xs = [p[first + k][0] for k in range(8)]
        assert xs == sorted(xs, reverse=True)
    assert p[1][0] == max(x for x, _ in p.values()) and p[1][1] == top
    assert p[24][0] == min(x for x, _ in p.values()) and p[24][1] == bot


def test_the_contact_grid_is_the_pitch_and_the_field_the_size_the_figure_prints():
    p = pins()
    xs = [p[n][0] for n in range(1, 9)]
    assert all(abs((a - b) - 1.91) < 0.01 for a, b in zip(xs, xs[1:]))
    assert abs(p[1][0] - p[8][0] - 13.34) < 0.01
    assert abs(p[17][1] - p[1][1] - 3.81) < 0.01
    assert abs((p[9][1] - p[1][1]) - 1.91) < 0.01 and abs((p[17][1] - p[9][1]) - 1.91) < 0.01
    for n in (8, 16, 24):
        assert p[n][0] == p[8][0]
    assert abs(p[8][0] - 15.93) < 0.005


def test_the_contacts_are_the_estimated_size_and_sit_in_the_shell():
    ids = mating_skin()
    x0, y0, x1, y1 = shell_box(mating_skin())
    for n in range(1, 25):
        r = ids[f"pin-{n}"]
        assert (float(r.get("width")), float(r.get("height"))) == (1.4, 0.5)
        cx, cy = pins()[n]
        assert x0 < cx < x1 and y0 < cy < y1


def test_the_blade_slot_is_one_flat_slot_left_of_the_field_level_with_the_middle_row():
    ids = mating_skin()
    slot = ids["blade-slot"]
    assert (float(slot.get("width")), float(slot.get("height"))) == (2.57, 0.44)
    cx, cy = centre(slot)
    assert abs(cx - 11.47) < 0.005
    assert abs(cy - pins()[9][1]) < 0.005 and abs(cy - 7.565) < 0.005
    assert cx + 1.285 < pins()[8][0] - 0.7
    assert not [i for i in ids if re.fullmatch(r"c[1-5]|cross.*", i)]


def test_the_mating_face_has_the_outline_shell_and_jackscrews_of_the_cable_end():
    ids = mating_skin()
    hood = ids["hood"]
    assert (float(hood.get("width")), float(hood.get("height"))) == (39.5, 15.13)
    assert shell_box(ids) == shell_box(skin())
    left, right = ids["screw-l"], ids["screw-r"]
    assert abs(float(right.get("cx")) - float(left.get("cx")) - 32.51) < 0.005
    assert float(left.get("cy")) == float(right.get("cy")) == 7.565
    assert float(left.get("r")) == float(right.get("r")) == float(skin()["screw-l"].get("r")) == 1.6


def path_numbers(d):
    return [float(t) for t in re.findall(r"-?\d+\.?\d*", d)]


def test_the_jackscrews_carry_the_crosshairs_the_figure_draws():
    ids = mating_skin()
    for side in ("l", "r"):
        screw = ids[f"screw-{side}"]
        cx, cy = float(screw.get("cx")), float(screw.get("cy"))
        x1, y1, x2, y2, x3, y3, x4, y4 = path_numbers(ids[f"screw-hair-{side}"].get("d"))
        assert (y1, y2) == (cy, cy) and (x3, x4) == (cx, cx)
        assert abs((x1 + x2) / 2 - cx) < 0.005 and abs((y3 + y4) / 2 - cy) < 0.005
        assert abs((x2 - x1) - 0.6) < 0.005 and abs((y4 - y3) - 0.6) < 0.005


def test_the_figures_second_outline_line_is_drawn_1_3_inside_the_outline():
    ids = mating_skin()
    inner, hood = ids["hood-inner"], ids["hood"]
    inset = float(inner.get("x"))
    assert inset == float(inner.get("y")) == 1.3
    assert abs(float(inner.get("width")) - (float(hood.get("width")) - 2 * inset)) < 0.005
    assert abs(float(inner.get("height")) - (float(hood.get("height")) - 2 * inset)) < 0.005
    assert inner.get("fill") == "none"


def test_the_shells_lip_line_is_25_3_by_9_0_around_the_printed_edge():
    ids = mating_skin()
    x0, y0, x1, y1 = shell_box(ids)
    lx0, ly0, lx1, ly1 = shell_box({"shell": ids["shell-lip"]})
    assert abs((lx1 - lx0) - 25.3) < 0.005 and abs((ly1 - ly0) - 9.0) < 0.005
    assert abs((lx0 + lx1) / 2 - (x0 + x1) / 2) < 0.005 and abs((ly0 + ly1) / 2 - (y0 + y1) / 2) < 0.005
    assert ids["shell-lip"].get("fill") == "none"


def test_the_numerals_1_to_24_stand_above_each_contact_as_the_figure_prints_them():
    ids = mating_skin()
    for n, (cx, cy) in pins().items():
        t = ids[f"num-{n}"]
        assert t.text == str(n)
        assert abs(float(t.get("x")) - cx) < 0.005
        assert 0.6 < cy - float(t.get("y")) < 0.9, n


def test_every_slant_crosses_its_contact_box_about_0_3_above_and_below():
    ids = mating_skin()
    segs = re.findall(r"M(-?[\d.]+) (-?[\d.]+) L(-?[\d.]+) (-?[\d.]+)", ids["slants"].get("d"))
    assert len(segs) == 24
    boxes = [(float(ids[f"pin-{n}"].get("x")), float(ids[f"pin-{n}"].get("y"))) for n in range(1, 25)]
    for x0, y0, x1, y1 in ((float(v) for v in s) for s in segs):
        bx, by = next(b for b in boxes if b[0] < (x0 + x1) / 2 < b[0] + 1.4 and by_row(b[1], (y0 + y1) / 2))
        assert bx < x0 < x1 < bx + 1.4
        assert abs((y1 - y0) - 1.2) < 0.005
        assert 0.25 < by - y0 < 0.45 and 0.25 < (y1 - (by + 0.5)) < 0.45


def by_row(box_y, slant_mid_y):
    return abs(box_y + 0.25 - slant_mid_y) < 0.005


def test_the_mating_face_states_what_is_printed_and_what_is_estimated_in_short_sentences():
    prov = mating_contract()["provenance"]
    for key in ("size", "contacts", "blade", "shell", "jackscrews", "method"):
        assert key in prov, key
    assert "2.57" in prov["blade"] and "3.3" not in prov["blade"] and "key" in prov["blade"]
    assert "ESTIMATED" in prov["contacts"] and "ESTIMATED" in prov["blade"]
    assert "INNER line" in prov["shell"] and "lip" in prov["shell"] and "1.3" in prov["shell"]
    assert "3.2" in prov["jackscrews"] and "3.4" not in prov["jackscrews"]
    texts = list(prov.items()) + [("plug-shell", contract()["provenance"]["shell"])]
    texts += [("description", mating_contract()["description"]), ("plug-description", contract()["description"])]
    for key, text in texts:
        for sentence in re.split(r"(?<=[.;:])\s+", " ".join(text.split())):
            assert len(sentence.split()) <= 25, (key, sentence)


def test_every_estimate_of_the_plug_is_declared():
    prov = contract()["provenance"]
    for key in ("size", "contacts", "shell", "depth", "hood", "stub", "cable-od", "colour"):
        assert key in prov, key
    assert features()["stub"]["confidence"] == "estimated"
    assert features()["shell"]["confidence"] == "estimated"


def test_the_registry_entry_of_the_key_is_mated_by_the_plug():
    entry = render_mod._connector_registry()[KEY]
    assert "unmated" not in entry
    assert contract()["mates"] == KEY

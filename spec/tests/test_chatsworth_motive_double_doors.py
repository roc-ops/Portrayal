"""The two doors of a double-sided Chatsworth Motive vertical cable manager are two parts.

The installation instructions say the front door has the logo at the top.
They say the rear door of a double-sided manager is a plain flat door with no logo.
The front door draws a latch tip at each edge on every width.
The seams, the plate and the reserved logo place are drawn on the 12 in width only (32623).
The data sheet's photograph reads as 12 in, and no held picture reads another width.
Every figure is in millimetres at a scale the door contract states.
The rear door is its own component, plain, with a latch tip at each edge.
The device places the front door on its front and the rear door on its rear.
It draws the latch housing and handle of each door on its left and right faces.
The gaps keep the hook and the frame features, which each device's own frame part draws later.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
HEIGHT = 2133.6
WIDTHS = {0: 150.0, 1: 200.0, 2: 250.0, 3: 300.0, 4: 380.0}
PARTS = [f"3262{w}-{c}" for w in WIDTHS for c in ("703", "e03")]
FEATURE_PARTS = [p for p in PARTS if p[4] == "3"]
OTHER_PARTS = [p for p in PARTS if p[4] != "3"]
FEATURE_IDS = {"seam-left", "seam-right", "door-plate", "logo-zone"}
TIP_IDS = {"latch-tip-left", "latch-tip-right"}
FRAME_GAPS = {"end-caps", "feet", "door-hinge-tabs", "side-plate-holes", "track-rungs", "centre-plate"}
SENTENCE_LIMIT = 25


def width(part):
    return WIDTHS[int(part[4])]


def comp_dir(part, rear):
    name = f"motive-{part}-rear-door" if rear else f"motive-{part}-door"
    return LIB / "components" / "chatsworth" / name / "v1"


def contract(part, rear):
    return yaml.safe_load((comp_dir(part, rear) / "contract.yaml").read_text())


def skin_shapes(part, rear):
    text = (comp_dir(part, rear) / "skins" / "default.svg").read_text()
    out = {}
    for m in re.finditer(r"<(rect|path) id=\"([^\"]+)\"([^>]*)>", text):
        out[m.group(2)] = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(3)))
    return out


def device(part):
    return yaml.safe_load((LIB / "devices" / "chatsworth" / part / "device.yaml").read_text())


def placements(doc, view):
    return {p["id"]: p for p in doc["views"][view]["components"]["placements"]}


def decor(doc, view):
    return {d["id"]: d for d in doc["views"][view]["panel"]["decor"]}


def sentences(text):
    out = []
    for block in re.split(r"\n\s*\n|\n\s*[-*] ", text):
        block = " ".join(block.split())
        out += [s for s in re.split(r"(?<=[.!?;:])\s+(?=[A-Z0-9`(\"'])", block) if s.strip()]
    return out


def centre(rect):
    return float(rect["x"]) + float(rect["width"]) / 2


@pytest.mark.parametrize("part", FEATURE_PARTS)
def test_the_12_in_front_door_draws_the_seams_and_the_plate_in_millimetres(part):
    shapes = skin_shapes(part, rear=False)
    assert FEATURE_IDS | TIP_IDS <= set(shapes)
    zone = shapes["logo-zone"]
    assert zone["fill"] == "none" and "stroke" not in zone, "the maker's mark is reserved, never painted"
    plate = contract(part, rear=False)["elements"]["door-plate"]
    assert plate["at"] == [pytest.approx(134, abs=0.5), pytest.approx(257, abs=1)]
    assert plate["size"] == [pytest.approx(67, abs=0.5), pytest.approx(551, abs=1)]
    assert float(zone["width"]) == pytest.approx(67, abs=0.5) and float(zone["height"]) == pytest.approx(76, abs=1)
    assert zone["x"] == f"{plate['at'][0]:g}" and zone["y"] == f"{plate['at'][1]:g}"
    left, right = centre(shapes["seam-left"]), centre(shapes["seam-right"])
    assert left == pytest.approx(123, abs=0.6) and right == pytest.approx(203.5, abs=0.6)
    assert left < plate["at"][0] and plate["at"][0] + plate["size"][0] < right + 3, "the plate sits between the seams"


@pytest.mark.parametrize("part", OTHER_PARTS)
def test_no_other_width_draws_the_seams_or_the_plate_and_says_why(part):
    assert not FEATURE_IDS & set(skin_shapes(part, rear=False))
    assert not FEATURE_IDS & set(contract(part, rear=False)["elements"])
    note = contract(part, rear=False)["provenance"]["door-geometry"]
    assert "reads as 12 in" in note and "no held picture reads this width" in note


@pytest.mark.parametrize("part", PARTS)
def test_every_front_door_has_a_tip_at_each_edge_and_declares_it(part):
    doc = contract(part, rear=False)
    shapes = skin_shapes(part, rear=False)
    w = width(part)
    assert doc["size"]["w"] == w
    assert TIP_IDS <= set(doc["elements"]) and TIP_IDS <= set(shapes)
    left, right = shapes["latch-tip-left"], shapes["latch-tip-right"]
    assert (float(left["x"]), float(left["width"]), float(left["height"])) == (0, 2, 45)
    assert float(right["x"]) + float(right["width"]) == w
    assert float(left["y"]) + float(left["height"]) / 2 == pytest.approx(0.473 * HEIGHT, abs=2)
    for key in ("logo-zone", "seams", "door-geometry", "latches", "hook"):
        assert key in doc["provenance"]


@pytest.mark.parametrize("part", FEATURE_PARTS)
def test_the_12_in_door_states_its_scale_and_pixel_points(part):
    note = contract(part, rear=False)["provenance"]["logo-zone"]
    assert "estimated" in note
    for text in ("2.624 mm per px", "2.679 mm per px", "rows 72 to 885", "rows 170 to 380", "columns 205 to 230", "reads as 12 in"):
        assert text in note or text.replace("reads", "read") in note
    assert "columns 201 and 231" in contract(part, rear=False)["provenance"]["seams"]


@pytest.mark.parametrize("part", PARTS)
def test_the_rear_door_is_its_own_plain_part(part):
    doc = contract(part, rear=True)
    assert doc["name"] == f"motive-{part}-rear-door"
    assert set(doc["elements"]) == {"plate"} | TIP_IDS
    assert doc["size"]["w"] == width(part)
    shapes = skin_shapes(part, rear=True)
    assert {"plate"} | TIP_IDS <= set(shapes)
    assert not FEATURE_IDS & set(shapes), "the rear door is plain"
    back = doc["provenance"]["door-back"]
    assert "central rib" in back and "two cross bars" in back and "four hinge tabs" in back
    assert contract(part, rear=False)["name"] != doc["name"]


@pytest.mark.parametrize("part", PARTS)
def test_the_device_places_the_front_door_in_front_and_the_rear_door_in_the_rear(part):
    doc = device(part)
    assert placements(doc, "front")["front-door"]["ref"] == f"chatsworth/motive-{part}-door@1"
    assert placements(doc, "rear")["rear-door"]["ref"] == f"chatsworth/motive-{part}-rear-door@1"


@pytest.mark.parametrize("part", PARTS)
def test_each_side_face_draws_one_latch_of_each_door_at_four_point_seven_to_one(part):
    doc = device(part)
    for view in ("left", "right"):
        d = decor(doc, view)
        for end in ("rear", "front"):
            housing, handle = d[f"{end}-latch-housing"], d[f"{end}-latch-handle"]
            assert housing["size"][1] / housing["size"][0] == pytest.approx(4.7, abs=0.05)
            assert housing["at"][1] + housing["size"][1] / 2 == pytest.approx(0.473 * HEIGHT, abs=2)
            assert handle["at"][1] + handle["size"][1] / 2 == pytest.approx(0.473 * HEIGHT, abs=2)


@pytest.mark.parametrize("part", PARTS)
def test_each_side_view_puts_the_rear_end_and_the_front_end_on_the_right_sides(part):
    doc = device(part)
    # The rear is on the left of the left view and on the right of the right view.
    rear_is_left = {"left": True, "right": False}
    for view, rear_left in rear_is_left.items():
        d = decor(doc, view)
        for kind in ("latch-housing", "latch-handle", "arm-1", "head-1", "arm-48", "head-48"):
            rear_x, front_x = d[f"rear-{kind}"]["at"][0], d[f"front-{kind}"]["at"][0]
            if rear_left:
                assert rear_x < 300 < front_x, f"{view} view: the rear {kind} is on the left"
            else:
                assert front_x < 300 < rear_x, f"{view} view: the front {kind} is on the left"
        for n in range(1, 49):
            rear_x, front_x = d[f"rear-arm-{n}"]["at"][0], d[f"front-arm-{n}"]["at"][0]
            assert (rear_x < front_x) == rear_left, f"{view} view: arm {n}"


@pytest.mark.parametrize("part", PARTS)
def test_the_side_latch_note_says_only_the_end_of_the_handle_shows(part):
    note = device(part)["provenance"]["door"]["note"]
    assert "only the end of each handle shows" in note and "housing stands behind the arms" in note
    for rear in (False, True):
        text = contract(part, rear)["provenance"]["latches"]
        assert "only the end of each handle shows" in text


@pytest.mark.parametrize("part", PARTS)
def test_the_gaps_keep_the_hook_and_the_frame_features_each_with_its_own_frame_part(part):
    gaps = {g["what"]: g for g in device(part)["gaps"]}
    assert "door-features" not in gaps
    assert gaps["door-hook"]["scope"] == ["front"]
    assert "No held picture shows the hook" in gaps["door-hook"]["note"]
    assert FRAME_GAPS <= set(gaps)
    assert all(g["reason"] == "vendor-silent" for g in gaps.values())
    for name in FRAME_GAPS - {"door-hinge-tabs"}:
        assert "this device's own frame part, which a following change draws" in gaps[name]["note"]
    tabs = gaps["door-hinge-tabs"]
    assert tabs["scope"] == ["rear"], "the rib, bars and tabs are on the rear door's back"
    assert "the rear door's own part, which a following change draws" in tabs["note"]
    assert "two feet at its front corners" in gaps["feet"]["note"]


@pytest.mark.parametrize("part", PARTS)
def test_no_note_speaks_of_a_shared_frame(part):
    texts = [yaml.safe_dump(device(part)["gaps"]), yaml.safe_dump(contract(part, rear=False)), yaml.safe_dump(contract(part, rear=True))]
    banned = [" ".join(words) for words in (("shared", "frame"), ("frame", "for", "the", "family"),
                                            ("next", "part", "for", "this", "family"))] + ["twen" + "ty"]
    for text in texts:
        flat = " ".join(text.lower().split())
        for phrase in banned:
            assert phrase not in flat, "a banned phrase is in a note"


@pytest.mark.parametrize("part", PARTS)
def test_no_door_note_gives_a_fraction_down_or_a_percent(part):
    for rear in (False, True):
        for key, text in contract(part, rear)["provenance"].items():
            flat = " ".join(text.split())
            assert not re.search(r"\b0\.\d+ down|percent|a quarter|a fifth", flat), f"{part} {key}"


@pytest.mark.parametrize("part", FEATURE_PARTS)
def test_the_12_in_notes_state_the_rows_of_the_seam_and_the_plate_and_the_widths(part):
    notes = contract(part, rear=False)["provenance"]
    assert "not the same width" in notes["door-geometry"]
    for text in ("67 mm", "61 mm", "81 mm", "55 mm"):
        assert text in notes["door-geometry"], text
    for text in ("#e8e2de", "(232,226,222)", "#4d4f52", "(77,79,82)", "#5d5d5d", "later touch"):
        assert text in notes["logo-zone"], text
    assert "row 280" in notes["seams"] and "row 450" in notes["seams"] and "8 mm" in notes["seams"]
    assert "two blue handles" in notes["latches"] and "rows 331 to 337" in notes["latches"]
    assert "Each unseen edge is built as the edge shown" in notes["latches"]
    assert "columns 231 to 233" in notes["seams"] and "step down at column 234" in notes["seams"]
    assert "rows 482 to 487" in notes["latches"] and "1009.5" in notes["latches"] and "stand-in" in notes["latches"]


@pytest.mark.parametrize("part", PARTS)
def test_the_far_edge_handle_of_the_render_is_the_rear_doors_and_no_front_door_claims_it(part):
    rear = " ".join(contract(part, rear=True)["provenance"]["latches"].split())
    for text in ("far-edge handle", "columns 190 to 199", "rows 257 to 269", "917 mm", "4.267 mm per px",
                 "is the rear door's handle"):
        assert text in rear, f"{part}: the rear door contract lacks '{text}'"
    front = yaml.safe_dump(contract(part, rear=False), width=10**6)
    front += yaml.safe_dump(device(part), width=10**6)
    flat = " ".join(front.split())
    for text in ("far-edge handle", "columns 190 to 199", "rows 257 to 269", "917 mm", "is the rear door's handle"):
        assert text not in flat, f"{part}: a front door contract or a device note claims '{text}'"
    latches = " ".join(contract(part, rear=False)["provenance"]["latches"].split())
    assert "second handle on the rear door's far edge" in latches, f"{part}: the front door contract lacks the pointer"


def test_every_added_sentence_of_the_notes_is_at_most_25_words():
    for part in PARTS:
        for rear in (False, True):
            for text in contract(part, rear)["provenance"].values():
                for s in sentences(text):
                    assert len(s.split()) <= SENTENCE_LIMIT, s
        for g in device(part)["gaps"]:
            if g["what"] not in FRAME_GAPS | {"door-hook"}:
                continue
            for s in sentences(g["note"]):
                assert len(s.split()) <= SENTENCE_LIMIT, s


@pytest.mark.parametrize("part", PARTS)
def test_no_note_line_ends_in_a_hyphen(part):
    paths = [comp_dir(part, False) / "contract.yaml", comp_dir(part, True) / "contract.yaml",
             LIB / "devices" / "chatsworth" / part / "device.yaml"]
    for path in paths:
        for n, line in enumerate(path.read_text().splitlines(), 1):
            assert not re.search(r"[A-Za-z]-$", line), f"{path.name}:{n} folds into a word with a space: {line}"


def test_this_module_follows_its_own_sentence_rule():
    doc = pathlib.Path(__file__).read_text().split('"""')[1]
    assert not any(line.rstrip().endswith(":") for line in doc.splitlines()), "no line ends in a colon"
    assert not re.search(r"(?m)^\s*[-*] ", doc), "no bullet list"
    for s in sentences(doc):
        assert len(s.split()) <= SENTENCE_LIMIT, s

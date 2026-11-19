"""The APC NetShelter AP9571A basic 1U rack PDU, and the two parts it needed.

It carries ten IEC C13 outlets in two banks of five on one face. A fixed input cord leaves the left end of that
face, and a rocker circuit breaker stands before each bank in the photograph. The other face is plain. What is true of the library
once it is in:

  - it is a device of the maker, with the width, height, depth and weight the data sheet gives, and six views;
  - the outlet face carries ten numbered C13 outlets, the input cord and two breakers, one before each bank;
  - the unit has no display, no network port and no switching;
  - every position read off a photograph is declared an estimate;
  - the two new parts say where each figure came from and are parts of the maker.

These read the contracts and the device source and render nothing. One test, marked heavy, runs the DCIM exporter
on the built device and reads the files it writes.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

VIEWS = ["front", "rear", "top", "bottom", "left", "right"]
ALLOWED = {"drawing", "datasheet", "photo-measured", "measured", "estimated", "borrowed", "registry"}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def dev():
    return yaml.safe_load((LIB / "devices" / "apc" / "ap9571a" / "device.yaml").read_text())


def placements(dev, view):
    comps = dev["views"][view].get("components") or {}
    return {p["id"]: p for p in (comps.get("placements") or [])}


def test_it_is_a_device_of_the_maker_the_size_the_data_sheet_gives(dev):
    assert (dev["manufacturer"], dev["model"]) == ("APC", "AP9571A")
    c = dev["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (445, 44, 77, 1)
    assert c["weight-kg"] == 2.55


def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched(dev):
    assert sorted(dev["views"]) == sorted(VIEWS)
    for name, v in dev["views"].items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor") or v.get("regions")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{name}: neither drawn nor an `empty:` sentence"


def test_ten_c13_outlets_and_the_fixed_cord_stand_on_the_outlet_face(dev):
    rear = placements(dev, "rear")
    outlets = {i: p for i, p in rear.items() if i.startswith("outlet-")}
    assert sorted(outlets, key=lambda i: int(i.split("-")[1])) == [f"outlet-{n}" for n in range(1, 11)]
    assert {p["ref"] for p in outlets.values()} == {"std/c13-outlet@1"}
    assert rear["input"]["ref"] == "apc/pdu-cord-l6-30p@1"


def test_each_bank_of_five_sits_behind_its_own_breaker(dev):
    rear = placements(dev, "rear")
    assert {rear["breaker-1"]["ref"], rear["breaker-2"]["ref"]} == {"apc/pdu-breaker-rocker@1"}
    for n in range(1, 11):
        want = "breaker-1" if n <= 5 else "breaker-2"
        assert rear[f"outlet-{n}"]["through"] == want, n
    assert rear["breaker-1"]["at"][0] < rear["outlet-1"]["at"][0] < rear["outlet-5"]["at"][0]
    assert rear["outlet-5"]["at"][0] < rear["breaker-2"]["at"][0] < rear["outlet-6"]["at"][0]


def test_the_outlets_are_named_one_to_ten(dev):
    rules = {r["physical"]: r for r in dev["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}"
    assert rules["outlet-{n}"]["range"] == "1-10"


def test_the_unit_has_no_display_no_network_port_and_no_switching(dev):
    mgmt = dev["attrs"]["management"]
    assert mgmt["outlet-switching"] is False
    assert mgmt["metering-scope"] == "none"
    refs = {p["ref"] for v in dev["views"] for p in placements(dev, v).values()}
    assert not any("display" in r or "rj45" in r for r in refs)


def test_every_position_read_off_a_photograph_is_declared_an_estimate(dev):
    for key in ("front", "rear", "breakers"):
        assert dev["provenance"][key]["confidence"] == "estimated", key
    assert "photograph" in dev["provenance"]["rear"]["note"]
    gaps = {g["what"] for g in dev["gaps"]}
    assert {"face-positions", "breaker-banks", "ears", "sides"} <= gaps


def test_every_view_that_draws_a_mark_declares_it_estimated(dev):
    for name, v in dev["views"].items():
        for d in (v.get("panel") or {}).get("decor") or []:
            assert d.get("confidence") == "estimated", f"{name}/{d['id']}"
            assert d.get("source"), f"{name}/{d['id']}"


def test_the_ten_outlets_stand_on_a_24_mm_pitch_in_two_groups_of_five(dev):
    rear = placements(dev, "rear")
    xs = [rear[f"outlet-{n}"]["at"][0] for n in range(1, 11)]
    assert {round(b - a, 1) for a, b in zip(xs[:4], xs[1:5])} == {24.0}
    assert {round(b - a, 1) for a, b in zip(xs[5:9], xs[6:10])} == {24.0}
    assert xs[5] - xs[4] > 90


def decor(dev, view="rear"):
    return {d["id"]: d for d in dev["views"][view]["panel"]["decor"]}


def gap(dev, name):
    return next(g for g in dev["gaps"] if g["what"] == name)


def test_both_breakers_stand_in_the_upper_half_of_the_face_level_with_the_upper_round_mark(dev):
    """The photographs put each breaker block between the face top and about half way down."""
    rear, marks = placements(dev, "rear"), decor(dev)
    height = contract("apc/pdu-breaker-rocker@1")["size"]["h"]
    for pid, upper, lower in (("breaker-1", "screw-1", "screw-2"), ("breaker-2", "screw-5", "screw-6")):
        top = rear[pid]["at"][1]
        mid_of_pair = (marks[upper]["at"][1] + marks[lower]["at"][1]) / 2 + 1.5
        assert 3.0 <= top <= 5.0, pid
        assert top + height / 2 < mid_of_pair - 6, pid
        assert top < marks[upper]["at"][1], pid


def test_the_method_note_states_the_breaker_figure_and_its_tolerance(dev):
    note = " ".join(dev["provenance"]["breakers"]["note"].split())
    assert "mm from the face top" in note
    assert "good to about" in note


def test_the_cord_end_is_a_round_base_and_a_round_cord_seen_straight_on():
    svg = (LIB / "components/apc/pdu-cord-l6-30p/v1/skins/default.svg").read_text()
    assert svg.count("<circle") == 2 and '<circle id="relief"' in svg and '<circle id="cord"' in svg
    for gone in ("<polygon", "<ellipse", "<rect", "<path", "<line", "shank", "boss-edge", "cord-end"):
        assert gone not in svg, gone
    assert svg.count("<radialGradient") == 2 and 'fill="url(#cord-shade)"' in svg and 'fill="url(#base-shade)"' in svg
    c = contract("apc/pdu-cord-l6-30p@1")
    text = " ".join(str(c["description"]).split()).lower()
    assert "round base" in text and "round cord" in text and "squared" not in text and "left" in text
    assert "perpendicular to the face" in text


def test_the_cord_beyond_the_face_and_the_cord_end_are_named_as_a_gap_with_the_reason(dev):
    g = gap(dev, "cord")
    assert g["reason"] and "left" in g["scope"]
    note = " ".join(g["note"].split()).lower()
    assert "no held picture" in note and "kit" in note


def test_the_light_strip_left_of_breaker_one_is_named_with_the_same_size_as_the_other_strip(dev):
    note = " ".join(gap(dev, "marks")["note"].split())
    assert "left of the first breaker" in note and "beside the second breaker" in note
    assert "2 px wide" in note and "good to about" in note
    assert "one pixel" not in str(dev)


def test_no_note_calls_a_round_mark_a_screw(dev):
    prose = [n["note"] for n in dev["provenance"].values()] + [g["note"] for g in dev["gaps"]]
    prose.append(dev["description"])
    assert not [t for t in prose if "screw" in t.lower()]
    assert all(d["kind"] == "end-screw" for i, d in decor(dev).items() if i.startswith(("screw-", "end-screw-")))


def test_each_quoted_figure_is_cited_to_the_data_sheet_copy_that_prints_it(dev):
    chassis = " ".join(dev["provenance"]["chassis"]["note"].split())
    inputs = " ".join(dev["provenance"]["input"]["note"].split())
    for note in (chassis, inputs):
        assert "8f932e6e" in note and "d8ed048a" in note
    assert dev["datasheet"]["sha256"].startswith("8f932e6e")
    assert "5 Nov copy" in chassis and "10 Nov copy" in chassis
    assert "10 Nov copy" in inputs


def test_the_breaker_says_its_two_states_are_estimated_and_draw_alike():
    c = contract("apc/pdu-breaker-rocker@1")
    assert c["elements"]["rocker"]["states"] == ["on", "off"]
    text = " ".join(str(c["provenance"]["states"]).split()).lower()
    assert "estimated" in text and "alike" in text


def test_the_two_thin_strips_beside_the_breakers_are_drawn_as_decor_by_measurement(dev):
    marks, rear = decor(dev), placements(dev, "rear")
    for sid, pid, side in (("strip-right-of-breaker-2", "breaker-2", "right"), ("strip-left-of-breaker-1", "breaker-1", "left")):
        s = marks[sid]
        assert s["confidence"] == "estimated" and "px" in s["source"] and "mm" in s["source"], sid
        width = contract("apc/pdu-breaker-rocker@1")["size"]["w"]
        bx = rear[pid]["at"][0]
        assert 2.0 <= s["size"][0] <= 4.0 and 8.0 <= s["size"][1] <= 22.0, sid
        if side == "right":
            assert bx + width < s["at"][0] < bx + width + 8, sid
        else:
            assert bx - 14 < s["at"][0] < bx - s["size"][0], sid
    assert "shelf-left-of-breaker-1" in marks
    note = " ".join(gap(dev, "marks")["note"].split())
    assert "too small to place" not in note and "is the tolerance, not a reason to leave them out" in note


def test_each_breaker_is_drawn_the_measured_width_and_stays_centred_on_its_round_marks(dev):
    c = contract("apc/pdu-breaker-rocker@1")
    assert 12.0 <= c["size"]["w"] <= 14.0
    assert c["elements"]["rocker"]["size"][0] == c["size"]["w"]
    skin = (LIB / "components/apc/pdu-breaker-rocker/v1/skins/default.svg").read_text()
    assert f'width="{c["size"]["w"]:g}mm"' in skin
    text = " ".join(str(c["provenance"]["size"]).split())
    assert "16 by 19" not in text and "good to about" in text
    rear, marks = placements(dev, "rear"), decor(dev)
    for pid, left, right in (("breaker-1", "screw-1", "screw-3"), ("breaker-2", "screw-5", "screw-7")):
        centre = rear[pid]["at"][0] + c["size"]["w"] / 2
        mid = (marks[left]["at"][0] + marks[right]["at"][0]) / 2 + 1.5
        assert abs(centre - mid) <= 1.0, pid


def test_no_description_or_attr_names_the_material_or_the_colour_as_fact(dev):
    assert "metal" not in " ".join(str(dev["description"]).split()).lower()
    assert "chassis material" in " ".join(dev["provenance"]["chassis"]["note"].split())
    assert "black" not in str(dev["description"]).lower()
    assert "metal" not in str(dev["attrs"]["physical"].get("construction", "")).lower()


@pytest.mark.heavy
def test_the_export_gives_a_nema_l6_30p_power_port_feeding_ten_outlets(tmp_path):
    """Runs the DCIM exporter on the built device and reads what it wrote."""
    from portrayal import dcim_export
    from portrayal.artifacts import Dist

    assert (LIB / "dist").is_dir(), "this test reads the built device: run ./build.sh first"
    dcim_export.export_device(Dist(LIB / "dist"), "ap9571a", str(tmp_path), None)
    written = sorted(tmp_path.glob("*/device-types/APC/AP9571A.yaml"))
    assert len(written) == 2
    for path in written:
        doc = yaml.safe_load(path.read_text())
        ports = doc["power-ports"]
        assert [p["type"] for p in ports] == ["nema-l6-30p"]
        outlets = doc["power-outlets"]
        assert len(outlets) == 10
        assert {o["power_port"] for o in outlets} == {ports[0]["name"]}
        assert {o["type"] for o in outlets} == {"iec-60320-c13"}


CORD_SKIN = LIB / "components/apc/pdu-cord-l6-30p/v1/skins/default.svg"
LIMIT = (
    "every position on the outlet face is an estimate read from the 369 px photograph. "
    "the cord end is read from the 1500 px photograph. "
    "it is good to about 3 mm unless a gap says otherwise. each figure names its own scale"
)


def skin_el(tag, eid):
    m = re.search(rf'<{tag} id="{eid}"([^>]*)/>', CORD_SKIN.read_text())
    assert m, eid
    return {k: float(v) for k, v in re.findall(r'(?<![-\w])(x|y|cx|cy|r|rx|ry|width|height)="(-?[\d.]+)"', m.group(1))}


def words(text):
    return " ".join(str(text).split())


def cord_texts(dev):
    c = contract("apc/pdu-cord-l6-30p@1")
    return (("contract", words(c["provenance"]["base"])), ("gap", words(gap(dev, "cord")["note"])))


OBLIQUE = (
    "Some features belong only to the oblique view and are not seen straight on. "
    "The shank's top and side faces and the lit vertical edge are not drawn. "
    "The bright arc on the boss's rim, the cord's highlight stripes and the nub on the boss are not drawn."
)


def test_the_features_only_the_oblique_view_shows_are_named_as_not_drawn_and_none_is_in_the_skin(dev):
    svg = CORD_SKIN.read_text()
    for source, text in cord_texts(dev):
        assert OBLIQUE in text, source
        assert "photograph is a perspective view from the front left" in text, source
        assert "angle the cord shows in it belongs to the camera" in text, source
        assert "The photograph shows a straight-sided shank, like a nut" in text, source
        assert "dark opening in a lighter ring" in text and "no inner circle is drawn" in text, source
    assert svg.count("fill=") == 2 and "highlight" not in svg and "nub" not in svg


def test_the_cord_is_drawn_the_one_diameter_and_the_centre_the_contract_and_the_gap_state(dev):
    cord, base = skin_el("circle", "cord"), skin_el("circle", "relief")
    top = placements(dev, "rear")["input"]["at"][1]
    assert (cord["cx"], cord["cy"]) == (base["cx"], base["cy"]), "the two end-on circles share one centre"
    for source, text in cord_texts(dev):
        stated = re.findall(r"The cord is (\d+) mm across, good to about 2 mm", text)
        assert len(stated) == 1 and float(stated[0]) == 2 * cord["r"], source
        assert f"the cord is drawn at {top + cord['cy']:.1f} mm below the face top" in text, source
        assert "That is an offset of 3.5 mm, inside the 5 mm that the cord's 2 mm and the boss's 3 mm add up to" in text, source
        assert "The picture's angle explains it. The two end-on circles share one centre" in text, source
    assert abs(top + cord["cy"] - 29.5) <= 3.6, "the drawn centre against the cord's reading at the face edge"
    assert abs((top + cord["cy"] - cord["r"]) - 18.5) <= 5.6 and abs((top + cord["cy"] + cord["r"]) - 40.5) <= 5.6


def test_the_rear_note_gives_the_base_circle_the_skin_draws_and_says_it_stands_perpendicular(dev):
    base = skin_el("circle", "relief")
    note = words(dev["provenance"]["rear"]["note"])
    m = re.search(r"round cord base is a circle (\d+) mm across, centred (\d+(?:\.\d+)?) mm from the face edge and (\d+(?:\.\d+)?) mm below the face top", note)
    assert m
    top = placements(dev, "rear")["input"]["at"]
    assert float(m.group(1)) == 2 * base["r"]
    assert float(m.group(2)) == top[0] + base["cx"] and float(m.group(3)) == top[1] + base["cy"]
    assert "stand perpendicular to the face" in note and "seen only in the oblique photograph and are not drawn" in note
    assert "ellipse" not in note and "shank's right side stands at" not in note and "cut at the face edge" not in note


def test_the_marks_gap_states_the_device_wide_limit_once_and_the_shelf_doubt(dev):
    note = words(gap(dev, "marks")["note"]).lower()
    assert LIMIT in note
    assert "top-edge highlight" in note
    every = [words(n["note"]).lower() for n in dev["provenance"].values()] + [words(g["note"]).lower() for g in dev["gaps"]]
    assert sum(LIMIT in n for n in every) == 1


def test_the_two_front_regions_stand_where_the_plain_face_photograph_reads_the_logo_and_the_label(dev):
    regions = {r["id"]: r for r in dev["views"]["front"]["regions"]}
    for rid, (x0, x1, y0, y1) in (("logo-zone", (412.5, 439.0, 10.5, 22.0)), ("label-zone", (416.0, 435.0, 22.0, 32.0))):
        r = regions[rid]
        x, y = r["at"]
        assert abs(x - x0) <= 1.0 and abs(x + r["size"]["w"] - x1) <= 1.0, rid
        assert abs(y - y0) <= 1.0 and abs(y + r["size"]["h"] - y1) <= 1.0, rid
    assert "not drawn" in str(regions["logo-zone"]["label"]) and "not drawn" in str(regions["label-zone"]["label"])


def test_three_thin_strips_are_drawn_the_second_light_one_left_of_the_second_breaker(dev):
    marks, rear = decor(dev), placements(dev, "rear")
    strips = {i for i in marks if i.startswith("strip-")}
    assert strips == {"strip-right-of-breaker-2", "strip-left-of-breaker-1", "strip-left-of-breaker-2"}
    s = marks["strip-left-of-breaker-2"]
    bx = rear["breaker-2"]["at"][0]
    assert s["confidence"] == "estimated" and "px" in s["source"] and "mm" in s["source"]
    assert s["fill"] == marks["strip-left-of-breaker-1"]["fill"]
    assert 2.0 <= s["size"][0] <= 4.0 and 8.0 <= s["size"][1] <= 12.0
    assert bx - 14 < s["at"][0] < bx - s["size"][0]
    note = words(gap(dev, "marks")["note"])
    assert "light strip stands left of the second" in note and "All three" in note
    assert "A second thin light strip" in words(dev["provenance"]["rear"]["note"])


def test_the_base_is_a_circle_of_the_one_diameter_the_contract_and_the_gap_state(dev):
    base = skin_el("circle", "relief")
    c = contract("apc/pdu-cord-l6-30p@1")
    assert c["size"]["w"] == c["size"]["h"] == 2 * base["r"] == c["elements"]["relief"]["size"][0] == c["elements"]["relief"]["size"][1]
    for source, text in cord_texts(dev):
        stated = re.findall(r"So the base is a circle (\d+) mm across, centred", text)
        assert len(stated) == 1 and float(stated[0]) == 2 * base["r"], source
        assert "good to about 3 mm" in text and "2 px at each end, 0.9 mm each, plus 1 mm for the dark lower arc" in text, source
    assert "71 px high" in words(c["provenance"]["size"])


def test_the_base_circle_stands_on_the_footprint_the_picture_reads_and_is_not_cut(dev):
    base = skin_el("circle", "relief")
    c = contract("apc/pdu-cord-l6-30p@1")
    at = placements(dev, "rear")["input"]["at"]
    assert c["elements"]["relief"]["at"] == [0, 0] and at == [0.0, 9.5], "the part starts at the face edge, 9.5 mm below the top"
    assert base["cx"] - base["r"] == 0.0 and base["cx"] + base["r"] == 33.0, "the circle reaches the face edge and does not pass it"
    assert (base["cx"], base["cy"]) == (16.5, 16.5)
    assert abs(base["cx"] + base["r"] - 32.7) <= 3.5, "the footprint's right side, column 448.5"
    assert abs(at[1] + base["cy"] - 26.1) <= 3.5, "the footprint's centre down the face, rows 673.5 to 744.3"
    for source, text in cord_texts(dev):
        assert "centred 16.5 mm from the face edge and 26.0 mm below the face top. Each is good to about 3.5 mm" in text, source
        assert "so it is not cut" in text, source
        assert "2 px, 1.3 mm, plus 2.0 mm for the scale spread" in text, source
        assert "The flat top is at row 673.5, 9.7 mm below the face top, good to about 1 mm: 2 px" in text, source
        assert "The right side is at column 448.5, 33 mm from the face edge, read on rows 695 to 720, good to about 3.5 mm" in text, source
        assert "42.5 mm below the face top" in text and "is dark on dark" in text, source
        assert "a shift of 13.5 mm" in text and "19.5 mm" in text and "shifted by its depth" in text, source
        assert abs(6.7 / 1.506 - 4.5) <= 0.1, source


def test_the_notes_state_that_the_base_and_the_cord_stand_perpendicular_to_the_face(dev):
    for source, text in cord_texts(dev):
        assert "The base and the cord are taken to stand perpendicular to the face. Straight on, they show as a circle and an end-on circle." in text, source
        assert "21.4 mm" in text and "22.9 mm" in text, source
        assert "drawn round" not in text and "looks faceted" not in text, source
        assert "A round mark stands right of the shank in the photograph" in text, source
        assert "ellipse" not in text, source
        assert "lit bar" not in text and "drawn as a straight chamfer" not in text and "curved upper-right corner" not in text, source
    assert "strain relief" not in words(contract("apc/pdu-cord-l6-30p@1")).lower()
    for f in [DEVICE_FILE, FRAGMENT, *PART_FILES]:
        assert not re.search(r"\b21\.5 mm|\b23\.0 mm", f.read_text()), f.name


def test_no_drawn_shank_lit_bar_or_24_by_33_ellipse_stands_in_the_notes_or_the_skin(dev):
    svg = CORD_SKIN.read_text().lower()
    for gone in ("polygon", "ellipse", "shank", "boss-edge", "<rect"):
        assert gone not in svg, gone
    for source, text in cord_texts(dev):
        assert "24 mm wide" not in text and "drawn as a straight chamfer" not in text, source
        assert "boss shows 0 to 19.5 mm" not in text and "cut there" not in text and "7.5 mm" not in text, source
    note = words(dev["provenance"]["rear"]["note"])
    stated_as_33 = r"boss (?:stands|shows)(?: at)? 0 (?:to|and) 33"
    for f in [DEVICE_FILE, FRAGMENT, *PART_FILES]:
        assert not re.search(stated_as_33, words(f.read_text())), f.name
    assert "ellipse" not in note


def test_each_figure_of_the_cord_end_names_its_scale_method_and_the_cord_tolerance(dev):
    for source, text in cord_texts(dev):
        for needle in (
            "2.17 px per mm across", "95.3 px for 44 mm", "1.506 px per mm along", "0.37 px per mm at 369 px times 4.07",
            "14 times", "rows 673.2 to 744.3", "grey level 200", "46.5 px", "21.4 mm", "49.7 px", "22.9 mm",
            "first and last crossing", "columns 200 to 280",
        ):
            assert needle in text, (source, needle)
    c = contract("apc/pdu-cord-l6-30p@1")
    assert "2.17 px per mm across" in words(c["provenance"]["size"])


def test_the_pictures_say_the_small_one_cannot_tell_round_from_squared_and_no_text_says_squared(dev):
    c = contract("apc/pdu-cord-l6-30p@1")
    for source, text in cord_texts(dev):
        assert "369 px" in text and "cannot tell round from squared" in text, source
    prose = words(c) + " " + words(dev["provenance"]) + " " + words(dev["gaps"]) + " " + words(dev["views"]["rear"]["components"])
    for stale in ("squared boot", "boot", "cord-line", "two flat", "good to about 4.5 mm","11.36 px", "20.3 mm", "170.89", "compression ringing"):
        assert stale not in prose, stale


DEVICE_FILE = LIB / "devices/apc/ap9571a/device.yaml"
PART_FILES = [
    LIB / f"components/apc/{p}/v1/{f}"
    for p in ("pdu-cord-l6-30p", "pdu-breaker-rocker")
    for f in ("contract.yaml", "skins/default.svg")
]
FRAGMENT = ROOT / "changelog.d/apc-ap9571a-pdu.md"


def test_no_notch_is_drawn_and_one_gap_says_the_lower_edge_is_a_smooth_slope(dev):
    assert not [d for d in dev["views"]["rear"]["panel"]["decor"] if "notch" in d["id"].lower()]
    lines = DEVICE_FILE.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "- what: face-positions")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("- what:"))
    assert not [n for n, ln in enumerate(lines) if "notch" in ln.lower() and not start <= n < end]
    for path in PART_FILES + [FRAGMENT]:
        assert "notch" not in path.read_text().lower(), path.name
    note = words(gap(dev, "face-positions")["note"]).lower()
    assert "smooth slope in both photographs" in note
    assert "no notch is resolved, so none is drawn" in note
    assert "12x crop" in note and "7 pixel" in note


def test_the_breaker_positions_state_the_marks_tolerance_and_the_first_width_figure(dev):
    c = contract("apc/pdu-breaker-rocker@1")
    for source, text in (
        ("device", words(dev["provenance"]["breakers"]["note"])),
        ("contract", words(c["provenance"]["size"])),
    ):
        assert "centred between marks that are good to about 10 mm" in text, source
        assert "at 66.5 and 262 mm, each good to about 10 mm" in text, source
        assert "18 mm read, 13 mm drawn" in text and "5 mm" in text, source


def test_no_text_calls_a_panel_recessed_or_a_breaker_standing_proud(dev):
    for path in [DEVICE_FILE, FRAGMENT] + PART_FILES:
        text = " ".join(path.read_text().lower().split())
        assert "recess" not in text and "standing proud" not in text, path.name
    assert "panel plate" in words(dev["provenance"]["rear"]["note"])
    assert "no held picture shows" in words(contract("apc/pdu-breaker-rocker@1")["description"]).lower()


def test_the_breaker_note_reads_one_scale_figure_for_the_first_block(dev):
    note = words(dev["provenance"]["breakers"]["note"])
    m = re.search(r"face reads (\d+) px high at the first breaker, so (0\.\d+) px per mm", note)
    assert m and abs(int(m.group(1)) / 44 - float(m.group(2))) <= 0.01
    assert "22 px" not in note and "0.5 px per mm" not in note and "0.5 and 0.7" not in note
    assert "0.5 px per mm" not in words(contract("apc/pdu-breaker-rocker@1")["provenance"]["size"])


def test_the_shelf_is_drawn_the_one_length_the_marks_gap_states_and_the_part_hides_the_rest(dev):
    note = words(gap(dev, "marks")["note"])
    stated = re.findall(r"It is drawn (\d+(?:\.\d+)?) mm long and 1\.5 mm high", note)
    assert len(stated) == 1
    shelf = decor(dev)["shelf-left-of-breaker-1"]
    assert float(stated[0]) == shelf["size"][0] and shelf["size"][1] == 1.5
    breaker_x = placements(dev, "rear")["breaker-1"]["at"][0]
    visible = breaker_x - shelf["at"][0]
    assert f"{visible:g} mm shows" in note
    assert shelf["at"][0] < breaker_x < shelf["at"][0] + shelf["size"][0]
    assert f"drawn {stated[0]} mm long" in words(shelf["source"]) or f"{stated[0]} mm long" in words(shelf["source"])
    assert "good to about 6 mm" in note and "good to about 4 mm" not in words(shelf["source"])


def test_each_strip_width_is_stated_with_a_tolerance_of_at_least_two_and_a_half_mm(dev):
    note = words(gap(dev, "marks")["note"])
    widths = re.findall(r"The (first light|second light|dark) strip's width is good to about (\d+(?:\.\d+)?) mm", note)
    assert [w[0] for w in widths] == ["dark", "first light", "second light"]
    assert all(float(w[1]) >= 2.5 for w in widths)
    assert "good to about 2 mm" not in note and "1 to 2 px" in note
    for sid in ("strip-right-of-breaker-2", "strip-left-of-breaker-1", "strip-left-of-breaker-2"):
        source = words(decor(dev)[sid]["source"])
        stated = re.findall(r"Width good to about (\d+(?:\.\d+)?) mm", source)
        assert len(stated) == 1 and float(stated[0]) >= 2.5, sid


def test_the_left_end_is_not_drawn_and_the_gap_says_no_held_picture_shows_it(dev):
    note = words(gap(dev, "cord")["note"])
    assert "No held picture shows the left end face" in note and "documented right end" in note
    assert not [d for d in dev["views"]["left"]["panel"]["decor"] if "cord" in d["id"] or "boss" in d["id"]]
    assert "straight-sided shank, like a nut" in note and "drawn round" not in note


@pytest.mark.parametrize("ref,plug", [("apc/pdu-cord-l6-30p@1", "nema-l6-30p"), ("apc/pdu-breaker-rocker@1", None)])
def test_the_new_parts_say_where_each_figure_came_from_and_which_are_estimates(ref, plug):
    c = contract(ref)
    assert "size" in c["provenance"]
    conf = c.get("size-confidence") or {}
    assert conf and set(conf.values()) <= ALLOWED
    if plug:
        assert c["attrs"]["plug"] == plug
    ns, part = ref.split("@")[0].split("/")
    assert (LIB / "components" / ns / part / "v1" / "skins" / "default.svg").is_file()


RUN_IS_ANGLE = "the cord's run in the photograph is the camera's angle and is not drawn"
STALE_RUN = (
    "beyond the face edge",
    "beyond the unit",
    "beyond it",
    "face view ends",
    "view ends at the unit",
    "leaving the boss to the left",
    "leaves the boss to the left",
    "runs out of it to the left",
)


def run_texts(dev):
    """Each place that names the cord's run: the gap, the contract's two notes, the fragment, the rear note."""
    c = contract("apc/pdu-cord-l6-30p@1")
    return (
        ("gap", words(gap(dev, "cord")["note"])),
        ("not-drawn", words(c["provenance"]["not-drawn"])),
        ("plug", words(c["provenance"]["plug"])),
        ("base", words(c["provenance"]["base"])),
        ("description", words(c["description"])),
        ("rear", words(dev["provenance"]["rear"]["note"])),
        ("fragment", words(FRAGMENT.read_text())),
    )


def test_no_text_says_the_cord_leaves_the_boss_to_the_left_or_runs_beyond_the_face_edge(dev):
    for source, text in run_texts(dev):
        low = text.lower()
        for stale in STALE_RUN:
            assert stale not in low, (source, stale)


def test_the_gap_the_not_drawn_text_and_the_plug_text_say_the_cords_run_is_the_cameras_angle(dev):
    texts = dict(run_texts(dev))
    for source in ("gap", "not-drawn", "plug"):
        assert RUN_IS_ANGLE in texts[source].lower(), source

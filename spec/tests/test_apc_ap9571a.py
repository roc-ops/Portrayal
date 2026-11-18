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


def test_the_notches_along_the_lower_edge_of_the_outlet_face_are_drawn(dev):
    decor = dev["views"]["rear"]["panel"]["decor"]
    notches = sorted((d for d in decor if d["id"].startswith("notch-")), key=lambda d: d["at"][0])
    assert len(notches) == 23
    assert {d["at"][1] for d in notches} == {41.6}
    pitch = {round(b["at"][0] - a["at"][0], 1) for a, b in zip(notches, notches[1:])}
    assert pitch == {19.0}


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


def test_the_cord_boot_is_squared_with_two_flat_cord_lines_leaving_to_the_left():
    svg = (LIB / "components/apc/pdu-cord-l6-30p/v1/skins/default.svg").read_text()
    assert "<circle" not in svg
    assert '<rect id="relief"' in svg
    assert 'id="cord-line-1"' in svg and 'id="cord-line-2"' in svg
    c = contract("apc/pdu-cord-l6-30p@1")
    text = " ".join(str(c["description"]).split()).lower()
    assert "round" not in text and "squared" in text and "left" in text


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


def test_the_two_cord_lines_leave_the_middle_and_lower_part_of_the_boot():
    import re

    svg = (LIB / "components/apc/pdu-cord-l6-30p/v1/skins/default.svg").read_text()
    height = contract("apc/pdu-cord-l6-30p@1")["size"]["h"]
    lines = []
    for rid in ("cord-line-1", "cord-line-2"):
        m = re.search(rf'<rect id="{rid}"[^>]*? y="([\d.]+)"[^>]*? height="([\d.]+)"', svg)
        assert m, rid
        lines.append((float(m.group(1)), float(m.group(2))))
    top, bottom = min(y for y, h in lines), max(y + h for y, h in lines)
    assert (top + bottom) / 2 > height / 2, "the pair stands below the boot's middle"
    assert top >= 6.0 and bottom <= height


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
    "every position on the outlet face and the cord is an estimate read at about 0.5 pixel per millimetre. "
    "it is good to about 3 mm unless a gap says otherwise"
)


def skin_rect(rid):
    m = re.search(rf'<rect id="{rid}"([^>]*)/>', CORD_SKIN.read_text())
    assert m, rid
    return {k: float(v) for k, v in re.findall(r'(?<![-\w])(x|y|width|height)="([\d.]+)"', m.group(1))}


def words(text):
    return " ".join(str(text).split())


def test_the_boots_light_edge_stands_at_the_measured_fraction_of_the_boot_width():
    boot, edge = skin_rect("relief"), skin_rect("boot-edge")
    drawn = (edge["x"] + edge["width"] / 2 - boot["x"]) / boot["width"]
    assert 0.37 <= drawn <= 0.43, "the edge reads about 40 percent across the boot, from its left"
    c = contract("apc/pdu-cord-l6-30p@1")
    text = words(c["description"]) + " " + words(c["provenance"]["boot"])
    stated = re.findall(r"about (\d+) percent across the boot", text)
    assert len(stated) == 1 and abs(int(stated[0]) - drawn * 100) <= 2
    assert "on its right" not in text


def test_the_cord_pair_is_drawn_the_one_height_the_contract_and_the_gap_state(dev):
    lines = [skin_rect("cord-line-1"), skin_rect("cord-line-2")]
    drawn = max(r["y"] + r["height"] for r in lines) - min(r["y"] for r in lines)
    c = contract("apc/pdu-cord-l6-30p@1")
    for source, text in (("contract", words(c["provenance"]["boot"])), ("gap", words(gap(dev, "cord")["note"]))):
        stated = re.findall(r"pair is (\d+) mm high", text)
        assert len(stated) == 1 and float(stated[0]) == drawn, source
        assert "16 to 20 mm" not in text and "about 17 mm" not in text, source


def test_the_cord_pair_and_its_boot_stand_where_the_photograph_reads_them(dev):
    top = placements(dev, "rear")["input"]["at"][1]
    lines = [skin_rect("cord-line-1"), skin_rect("cord-line-2")]
    first, last = top + min(r["y"] for r in lines), top + max(r["y"] + r["height"] for r in lines)
    assert abs(first - 17.6) <= 3.0 and abs(last - 37.2) <= 3.0


def test_the_rear_note_gives_the_boot_extent_the_skin_draws(dev):
    boot = skin_rect("relief")
    m = re.search(r"cord boot stands at (\d+) to (\d+)", words(dev["provenance"]["rear"]["note"]))
    assert m
    assert (float(m.group(1)), float(m.group(2))) == (boot["x"], boot["x"] + boot["width"])


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


def test_the_boot_is_drawn_the_one_height_the_contract_and_the_gap_state(dev):
    boot = skin_rect("relief")
    c = contract("apc/pdu-cord-l6-30p@1")
    assert c["size"]["h"] == boot["height"] and c["elements"]["relief"]["size"][1] == boot["height"]
    for source, text in (
        ("contract", words(c["description"]) + " " + words(c["provenance"]["size"]) + " " + words(c["provenance"]["boot"])),
        ("gap", words(gap(dev, "cord")["note"])),
    ):
        stated = re.findall(r"boot is (\d+) mm high", text)
        assert len(stated) == 1 and float(stated[0]) == boot["height"], source
        assert "14 px" not in text and "25 mm" not in text, source
    assert "16 px high" in words(c["provenance"]["size"])


def test_the_edge_position_has_its_own_tolerance_in_the_contract_and_the_gap(dev):
    c = contract("apc/pdu-cord-l6-30p@1")
    drawn = (skin_rect("boot-edge")["x"] + skin_rect("boot-edge")["width"] / 2 - skin_rect("relief")["x"]) / skin_rect("relief")["width"]
    for source, text in (("contract", words(c["provenance"]["boot"])), ("gap", words(gap(dev, "cord")["note"]))):
        stated = re.findall(r"edge stands (\d+) percent across the boot, plus or minus (\d+) points", text)
        assert len(stated) == 1, source
        centre, tol = (int(v) for v in stated[0])
        assert 3 <= tol <= 8 and abs(centre - drawn * 100) <= 2, source


def test_the_boot_stands_where_the_face_edge_datum_puts_it_and_skin_and_contract_agree(dev):
    boot = skin_rect("relief")
    c = contract("apc/pdu-cord-l6-30p@1")
    assert c["elements"]["relief"]["at"][0] == boot["x"]
    assert c["size"]["w"] == boot["x"] + boot["width"]
    assert placements(dev, "rear")["input"]["at"][0] == 0.0, "the part starts at the face's left edge"
    want = [(str(int(boot["x"])), str(int(boot["x"] + boot["width"])))]
    sentence = r"boot stands (\d+) to (\d+) mm from the face's left edge, good to about 3 mm"
    for source, text in (("contract", words(c["provenance"]["boot"])), ("gap", words(gap(dev, "cord")["note"]))):
        assert re.findall(sentence, text) == want, source
    assert "5 px and 12.5 px at 2.7 mm per px" in words(c["provenance"]["boot"])
    assert abs(boot["x"] - 5 * 2.7) <= 3.0 and abs(boot["x"] + boot["width"] - 12.5 * 2.7) <= 3.0


def test_the_cord_lines_run_from_the_face_edge_to_the_boot_and_no_text_says_four_mm(dev):
    boot = skin_rect("relief")
    for rid in ("cord-line-1", "cord-line-2"):
        r = skin_rect(rid)
        assert r["x"] == 0.0 and r["x"] + r["width"] >= boot["x"], rid
    c = contract("apc/pdu-cord-l6-30p@1")
    prose = words(c) + " " + words(dev)
    assert "first 4 mm" not in prose and "4 to 23" not in prose and "FIRST 4 MM" not in prose


NOTCHES = "about 12 to 26, drawn as 23 at a 19 mm pitch"


def test_one_notch_count_and_one_tolerance_stand_in_the_device_the_gap_and_the_sources(dev):
    notches = [d for i, d in decor(dev).items() if i.startswith("notch-")]
    assert len(notches) == 23
    for d in notches:
        assert NOTCHES in words(d["source"])
    assert NOTCHES in words(dev["provenance"]["rear"]["note"])
    assert NOTCHES in words(gap(dev, "face-positions")["note"])
    assert "good to 4" not in words(dev)


def test_the_breaker_note_reads_one_scale_figure_for_the_first_block(dev):
    note = words(dev["provenance"]["breakers"]["note"])
    m = re.search(r"face reads (\d+) px high at the first breaker, so (0\.\d+) px per mm", note)
    assert m and abs(int(m.group(1)) / 44 - float(m.group(2))) <= 0.01
    assert "22 px" not in note and "0.5 px per mm" not in note and "0.5 and 0.7" not in note
    assert "0.5 px per mm" not in words(contract("apc/pdu-breaker-rocker@1")["provenance"]["size"])


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

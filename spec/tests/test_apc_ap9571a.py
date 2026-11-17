"""The APC NetShelter AP9571A basic 1U rack PDU, and the two parts it needed.

It carries ten IEC C13 outlets in two banks of five on one face. A fixed input cord leaves the left end of that
face, and a rocker circuit breaker stands beside each bank. The other face is plain. What is true of the library
once it is in:

  - it is a device of the maker, with the width, height, depth and weight the data sheet gives, and six views;
  - the outlet face carries ten numbered C13 outlets, the input cord and two breakers, each bank behind its own;
  - the unit has no display, no network port and no switching;
  - every position read off a photograph is declared an estimate;
  - the two new parts say where each figure came from and are parts of the maker.

These read the contracts and the device source and render nothing. One test, marked heavy, runs the DCIM exporter
on the built device and reads the files it writes.
"""
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
    assert "about 2 px" in note and "too small to place" in note
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


@pytest.mark.heavy
def test_the_export_gives_a_nema_l6_30p_power_port_feeding_ten_outlets(tmp_path):
    """Runs the DCIM exporter on the built device and reads what it wrote."""
    from portrayal import dcim_export
    from portrayal.artifacts import Dist

    if not (LIB / "dist").is_dir():
        pytest.skip("not built - run ./build.sh")
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

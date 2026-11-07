"""An outlet run can repeat a pattern of outlet kinds, and a bank can name its own outlets.

A segment of an outlet run is one kind of outlet on one pitch. A strip whose
outlets alternate (Eaton's G4 PDUs put a C13, then a C39, then a C13 again, seven
to a section) is not that, and its sections are lettered, so an outlet's id
carries its section's letter. A segment takes a `pattern`: the kinds in the order
they repeat, each with the small shift of its own seat from the pitch. A bank
takes an `id-format` of its own.

These tests hold both rules on a small run made up for the purpose, and hold the
one device authored this way to the shape its sources give it.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import expand as E

LIB = ROOT / "library"
STD = E.load_standards(ROOT / "spec/schemas")
DEVICE = LIB / "devices/eaton/evmi2130x"

C13 = "std/c13-outlet@1"
C39 = "eaton/c39-outlet@1"


def _run():
    return {
        "kind": "outlet-run", "id": "outlets", "id-format": "outlet-{n}",
        "number-from": 1, "fed-by": "input",
        "banks": [{"id-format": "outlet-a{n}", "through": "breaker-a"},
                  {"id-format": "outlet-b{n}", "shift": [0, -200.0],
                   "through": "breaker-b"}],
        "segments": [
            {"count": 5, "at": [9.0, 100.0], "pitch": [0, -25.0],
             "pattern": [{"ref": C13},
                         {"ref": C39, "shift": [-2.5, -2.0]}]},
        ],
    }


def _outlets(block=None):
    placements, decor, silks = E.run_items(block or _run())
    return placements


def test_a_pattern_repeats_its_kinds_in_order_down_the_segment():
    kinds = [p["ref"] for p in _outlets()]
    assert kinds == [C13, C39, C13, C39, C13] * 2


def test_each_kind_sits_on_the_pitch_plus_its_own_shift():
    by_id = {p["id"]: p for p in _outlets()}
    assert by_id["outlet-a1"]["at"] == [9.0, 100.0]
    assert by_id["outlet-a2"]["at"] == [6.5, 73.0]
    assert by_id["outlet-a3"]["at"] == [9.0, 50.0]
    assert by_id["outlet-a4"]["at"] == [6.5, 23.0]
    assert by_id["outlet-a5"]["at"] == [9.0, 0.0]


def test_a_bank_moves_the_whole_pattern_and_names_its_own_outlets():
    outlets = _outlets()
    assert [p["id"] for p in outlets] == [
        "outlet-a1", "outlet-a2", "outlet-a3", "outlet-a4", "outlet-a5",
        "outlet-b6", "outlet-b7", "outlet-b8", "outlet-b9", "outlet-b10"]
    by_id = {p["id"]: p for p in outlets}
    # the second bank repeats the pattern from its own start, not from where the
    # first left off
    assert by_id["outlet-b6"]["ref"] == C13 and by_id["outlet-b6"]["at"] == [9.0, -100.0]
    assert by_id["outlet-b7"]["ref"] == C39 and by_id["outlet-b7"]["at"] == [6.5, -127.0]
    assert [p["rel-pos"] for p in outlets] == list(range(1, 11))
    assert [p["through"] for p in outlets] == ["breaker-a"] * 5 + ["breaker-b"] * 5


def test_a_bank_without_an_id_format_uses_the_blocks():
    block = _run()
    for bank in block["banks"]:
        bank.pop("id-format")
    assert [p["id"] for p in _outlets(block)][:2] == ["outlet-1", "outlet-2"]


def test_a_segment_with_a_ref_and_no_pattern_is_what_it_was():
    block = _run()
    block["banks"] = [{}]
    block["segments"] = [{"ref": C13, "count": 3, "at": [1.0, 1.0], "pitch": [0, 10.0]}]
    outlets = _outlets(block)
    assert [p["ref"] for p in outlets] == [C13] * 3
    assert [p["at"] for p in outlets] == [[1.0, 1.0], [1.0, 11.0], [1.0, 21.0]]


def test_a_pattern_with_the_pattern_kinds_rotated_keeps_the_outlet_rotation():
    block = _run()
    block["banks"] = [{}]
    block["segments"][0]["rotate"] = 180
    block["segments"][0]["pattern"][1]["rotate"] = 90
    rot = [p.get("rotate") for p in _outlets(block)]
    assert rot == [180, 90, 180, 90, 180]


def test_a_segment_needs_a_ref_or_a_pattern_and_not_both():
    block = _run()
    block["segments"][0]["ref"] = C13
    with pytest.raises(SystemExit) as e:
        E.run_items(block)
    assert "pattern" in str(e.value)
    block = _run()
    del block["segments"][0]["pattern"]
    with pytest.raises(SystemExit) as e:
        E.run_items(block)
    assert "ref" in str(e.value)


def test_an_empty_or_misspelt_pattern_stops_the_run_and_names_it():
    block = _run()
    block["segments"][0]["pattern"] = []
    with pytest.raises(SystemExit) as e:
        E.run_items(block)
    assert "pattern" in str(e.value)
    block = _run()
    block["segments"][0]["pattern"][1]["shfit"] = [1, 1]
    with pytest.raises(SystemExit) as e:
        E.run_items(block)
    assert "shfit" in str(e.value)
    block = _run()
    del block["segments"][0]["pattern"][0]["ref"]
    with pytest.raises(SystemExit) as e:
        E.run_items(block)
    assert "ref" in str(e.value)


# ---- the device authored this way


def _front(path):
    return yaml.safe_load(path.read_text())["views"]["front"]


def test_the_evmi2130x_is_authored_as_a_layout_with_a_pattern():
    layout = DEVICE / "layout.yaml"
    assert layout.exists(), "the EVMI2130X has no layout.yaml"
    front = _front(layout)
    blocks = front["components"]["blocks"]
    assert [b["kind"] for b in blocks] == ["outlet-run"]
    assert "pattern" in blocks[0]["segments"][0]
    hand = [p["id"] for p in front["components"]["placements"] if "block" not in p]
    assert not [i for i in hand if i.startswith("outlet-")]


def test_the_expanded_evmi2130x_has_the_outlets_its_drawing_gives_it():
    dev = yaml.safe_load((DEVICE / "device.yaml").read_text())
    placements = dev["views"]["front"]["components"]["placements"]
    outlets = [p for p in placements if p.get("group") == "outlets"]
    assert len(outlets) == 42
    kinds = [p["ref"] for p in outlets]
    assert kinds.count(C13) == 24 and kinds.count(C39) == 18
    # six sections of seven, each C13 first and last, the kinds alternating
    for s in range(6):
        section = kinds[s * 7:(s + 1) * 7]
        assert section == [C13, C39, C13, C39, C13, C39, C13]
    # a section's outlets answer to its breaker, and its letter is in the id
    for outlet, letter in zip(outlets, "aaaaaaabbbbbbbcccccccaaaaaaabbbbbbbccccccc"):
        assert outlet["through"] == f"breaker-{letter}"
        assert outlet["id"].startswith(f"outlet-{letter}")
    # one inch between outlets in a section, kind to kind
    first = outlets[:7]
    for a, b in zip(first, first[1:]):
        assert abs(abs(b["at"][1] - a["at"][1]) - 25.4) < 2.51


def test_the_expanded_evmi2130x_is_in_step_with_its_layout():
    layout = yaml.safe_load((DEVICE / "layout.yaml").read_text())
    assert E.expand(layout, LIB, STD) == yaml.safe_load((DEVICE / "device.yaml").read_text())

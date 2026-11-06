"""An outlet run repeats a PDU's outlets, and what sits with each one, from a pitch.

A strip PDU is hand-typed four lines to an outlet: the placement, the bezel
moulding round it, its printed numeral and its lamp. `expand.py` repeats ports
from a `layout.yaml` for most of the library's switches, and an `outlet-run`
block does the same for a strip: segments (a run of one outlet kind on one
pitch), banks (the same segments again, shifted), and the keys a power outlet
carries that a port does not (`fed-by`, `through`, `states`).

These tests hold the block's rules on a small run made up for the purpose, and
hold the one device authored this way to the shape its sources give it.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import expand as E

LIB = ROOT / "library"
STD = E.load_standards(ROOT / "spec/schemas")
DEVICE = LIB / "devices/eaton/pdumv20hvnetlx"


def _run():
    return {
        "kind": "outlet-run", "id": "outlets", "id-format": "outlet-{n}",
        "number-from": 1, "fed-by": "input", "states": ["on", "off"],
        "numerals": {"font-size": 5.0, "anchor": "middle", "rotate": 270},
        "led": {"ref": "eaton/tripplite-led@1", "id-format": "led-{n}",
                "group": "outlet-leds"},
        "moulding": {"fill": "#262729", "kind": "outlet-moulding"},
        "banks": [{"through": "breaker-a"},
                  {"shift": [0, 200], "through": "breaker-b"}],
        "segments": [
            {"ref": "std/c19-outlet@1", "count": 2, "at": [10.0, 20.0],
             "pitch": [0, 40.0], "rotate": 270,
             "numerals": {"offset": [-5.0, 10.0]}, "led": {"offset": [-3.0, 8.0]},
             "moulding": {"id-format": "big-{m}", "offset": [1.0, -6.0],
                          "size": [30.0, 38.0], "rx": 1.2,
                          "by-pos": [{}, {"offset": [1.0, -5.0], "size": [30.0, 36.0]}]}},
            {"ref": "std/c13-outlet@1", "count": 3, "at": [12.0, 110.0],
             "pitch": [0, 30.5], "rotate": 180,
             "numerals": {"offset": [14.0, -4.0]}, "led": {"offset": [16.0, -9.0]},
             "moulding": {"id-format": "small-{m}", "offset": [-2.0, -3.0],
                          "size": [20.0, 25.0], "rx": 1.0}},
        ],
    }


def _items(block=None):
    return E.run_items(block or _run())


def test_the_run_gives_every_outlet_its_four_things():
    placements, decor, silks = _items()
    outlets = [p for p in placements if p["group"] == "outlets"]
    lamps = [p for p in placements if p["group"] == "outlet-leds"]
    # two banks of two big and three small outlets
    assert [p["id"] for p in outlets] == [f"outlet-{n}" for n in range(1, 11)]
    assert [p["id"] for p in lamps] == [f"led-{n}" for n in range(1, 11)]
    assert len(decor) == 10 and len(silks) == 10
    # a lamp and a numeral answer for their own outlet
    assert [p["for"] for p in lamps] == [p["id"] for p in outlets]
    assert [s["for"] for s in silks] == [p["id"] for p in outlets]
    assert [s["text"] for s in silks] == [str(n) for n in range(1, 11)]


def test_the_pitch_the_offsets_and_the_bank_shift_set_the_positions():
    placements, decor, silks = _items()
    by_id = {p["id"]: p for p in placements}
    assert by_id["outlet-1"]["at"] == [10.0, 20.0]
    assert by_id["outlet-2"]["at"] == [10.0, 60.0]
    assert by_id["outlet-5"]["at"] == [12.0, 171.0]
    # the second bank is the first moved 200 down
    assert by_id["outlet-6"]["at"] == [10.0, 220.0]
    assert by_id["outlet-10"]["at"] == [12.0, 371.0]
    assert by_id["led-1"]["at"] == [7.0, 28.0]
    assert by_id["led-4"]["at"] == [28.0, 131.5]
    silk = {s["for"]: s for s in silks}
    assert silk["outlet-1"]["at"] == [5.0, 30.0]
    assert silk["outlet-1"]["rotate"] == 270
    assert silk["outlet-1"]["font-size"] == 5.0
    assert "fill" not in silk["outlet-1"]


def test_a_moulding_takes_its_position_from_the_outlet_and_its_own_per_position_change():
    _, decor, _ = _items()
    mould = {d["id"]: d for d in decor}
    assert mould["big-1"]["at"] == [11.0, 14.0] and mould["big-1"]["size"] == [30.0, 38.0]
    # the second of a pair is a different box, not the first moved by the pitch
    assert mould["big-2"]["at"] == [11.0, 55.0] and mould["big-2"]["size"] == [30.0, 36.0]
    assert mould["small-1"]["at"] == [10.0, 107.0]
    assert mould["small-1"]["fill"] == "#262729"
    assert mould["small-1"]["kind"] == "outlet-moulding"
    assert mould["small-1"]["rx"] == 1.0 and mould["big-1"]["rx"] == 1.2


def test_a_moulding_is_numbered_in_its_own_family_across_the_banks():
    _, decor, _ = _items()
    # four big ones over two banks, six small: each family counts on
    assert [d["id"] for d in decor if d["id"].startswith("big-")] == [
        "big-1", "big-2", "big-3", "big-4"]
    assert [d["id"] for d in decor if d["id"].startswith("small-")] == [
        f"small-{n}" for n in range(1, 7)]
    # and the order is the order of the faces: bank 1's two kinds, then bank 2's
    assert [d["id"] for d in decor] == [
        "big-1", "big-2", "small-1", "small-2", "small-3",
        "big-3", "big-4", "small-4", "small-5", "small-6"]


def test_fed_by_states_and_the_bank_breaker_ride_on_every_outlet():
    placements, _, _ = _items()
    outlets = [p for p in placements if p["group"] == "outlets"]
    assert all(p["fed-by"] == "input" for p in outlets)
    assert all(p["states"] == ["on", "off"] for p in outlets)
    assert [p["through"] for p in outlets] == ["breaker-a"] * 5 + ["breaker-b"] * 5
    # a lamp is not fed and runs through nothing
    lamps = [p for p in placements if p["group"] == "outlet-leds"]
    assert not any(k in p for p in lamps for k in ("fed-by", "through", "states"))


def test_a_run_with_no_breaker_states_no_through():
    block = _run()
    for bank in block["banks"]:
        bank.pop("through")
    outlets = [p for p in _items(block)[0] if p["group"] == "outlets"]
    assert not any("through" in p for p in outlets)


def test_the_numbering_follows_number_from():
    block = _run()
    block["number-from"] = 7
    placements, _, silks = _items(block)
    assert placements[0]["id"] == "outlet-7" and placements[0]["rel-pos"] == 7
    assert silks[0]["text"] == "7" and silks[-1]["text"] == "16"


def test_an_unknown_key_stops_the_run_and_names_it():
    block = _run()
    block["pitch"] = 30
    with pytest.raises(SystemExit) as e:
        E.run_items(block)
    assert "pitch" in str(e.value)
    block = _run()
    block["segments"][0]["cuouts"] = True
    with pytest.raises(SystemExit) as e:
        E.run_items(block)
    assert "cuouts" in str(e.value)


def test_a_segment_without_a_pitch_or_count_stops_the_run():
    for key in ("pitch", "count", "at", "ref"):
        block = _run()
        del block["segments"][0][key]
        with pytest.raises(SystemExit) as e:
            E.run_items(block)
        assert key in str(e.value)


def test_expand_puts_a_run_at_its_markers_in_all_three_lists():
    layout = {
        "views": {"front": {
            "panel": {"decor": [{"block": "outlets"}, {"id": "screw", "at": [0, 0]}]},
            "silkscreen": [{"block": "outlets"}, {"at": [1, 1], "text": "X"}],
            "components": {
                "blocks": [_run()],
                "placements": [{"block": "outlets"}, {"id": "meter", "ref": "a/b@1", "at": [2, 2]}],
            }}}}
    front = E.expand(layout, LIB, STD)["views"]["front"]
    assert front["panel"]["decor"][0]["id"] == "big-1"
    assert front["panel"]["decor"][-1]["id"] == "screw"
    assert len(front["panel"]["decor"]) == 11
    assert front["silkscreen"][0]["for"] == "outlet-1" and front["silkscreen"][-1]["text"] == "X"
    ids = [p["id"] for p in front["components"]["placements"]]
    assert ids[:10] == [f"outlet-{n}" for n in range(1, 11)]
    assert ids[10:20] == [f"led-{n}" for n in range(1, 11)]
    assert ids[-1] == "meter"
    assert "blocks" not in front["components"]


# ---- the device authored this way


def _front(path):
    return yaml.safe_load(path.read_text())["views"]["front"]


def test_the_pdumv20hvnetlx_is_authored_as_a_layout():
    layout = DEVICE / "layout.yaml"
    assert layout.exists(), "the PDUMV20HVNETLX has no layout.yaml"
    front = _front(layout)
    blocks = front["components"]["blocks"]
    assert [b["kind"] for b in blocks] == ["outlet-run"]
    # no outlet, lamp, bezel or numeral is typed by hand beside the run
    hand = [p["id"] for p in front["components"]["placements"] if "block" not in p]
    assert not [i for i in hand if i.startswith(("outlet-", "led-"))]
    assert not [d for d in front["panel"]["decor"] if str(d.get("id", "")).startswith(
        ("c13-moulding", "c19-moulding"))]


def test_the_expanded_device_has_the_outlets_its_sources_give_it():
    dev = yaml.safe_load((DEVICE / "device.yaml").read_text())
    front = dev["views"]["front"]
    outlets = [p for p in front["components"]["placements"] if p.get("group") == "outlets"]
    assert [p["id"] for p in outlets] == [f"outlet-{n}" for n in range(1, 25)]
    kinds = [p["ref"] for p in outlets]
    assert kinds.count("std/c19-outlet@1") == 4 and kinds.count("std/c13-outlet@1") == 20
    # two C19 then ten C13 in each bank
    assert kinds[:2] == ["std/c19-outlet@1"] * 2 and kinds[12:14] == ["std/c19-outlet@1"] * 2
    assert all(p["fed-by"] == "input" and p["states"] == ["on", "off"] for p in outlets)
    # one pitch down a run of C13, the same in both banks
    ys = [p["at"][1] for p in outlets[2:12]]
    assert all(abs((b - a) - 35.616) < 0.011 for a, b in zip(ys, ys[1:]))
    assert abs(outlets[14]["at"][1] - outlets[2]["at"][1] - 718.4) < 0.011
    # a numeral, a lamp and a bezel for each outlet
    silks = [s for s in front["silkscreen"] if str(s.get("for", "")).startswith("outlet-")]
    assert [s["text"] for s in silks] == [str(n) for n in range(1, 25)]
    lamps = [p for p in front["components"]["placements"] if p.get("group") == "outlet-leds"]
    assert [p["for"] for p in lamps] == [f"outlet-{n}" for n in range(1, 25)]
    mould = [d for d in front["panel"]["decor"] if d.get("kind") == "outlet-moulding"]
    assert len(mould) == 24


def test_the_expanded_device_is_in_step_with_its_layout():
    layout = yaml.safe_load((DEVICE / "layout.yaml").read_text())
    assert E.expand(layout, LIB, STD) == yaml.safe_load((DEVICE / "device.yaml").read_text())

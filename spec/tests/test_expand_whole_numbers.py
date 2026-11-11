"""A layout may ask for its generated coordinates to be written as whole numbers.

`expand.py` computes every coordinate it writes with `round(..., 2)`, so a
position of 14 comes out as `14.0`. A hand-written `device.yaml` says `14`. The
two parse equal, and `render.source_bytes` hashes `json.dumps(device,
sort_keys=True)`, which does not: the source hash, every compiled face's
`<metadata>` and every output hash move although the drawing did not. A layout
that opts in with `whole-numbers: true` writes an integral coordinate as an
integer, so a hand-written device can be converted without that change.

Changing the writer for every layout was not done: a layout that does not carry
the key must expand exactly as it did, and the first test holds that over the
whole library.
"""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import expand as E

LIB = ROOT / "library"
STD = E.load_standards(ROOT / "spec/schemas")
TOOL = ROOT / "spec/tools/portrayal/expand.py"
LAYOUTS = sorted(LIB.glob("devices/*/*/layout.yaml"))


def _source(doc):
    """What `render.source_bytes` hashes: the document as sorted JSON."""
    return json.dumps(doc, sort_keys=True)


def _layout(**top):
    """A small face: four SFP cages on two rows, each with a lamp and a numeral,
    and one hand-written placement whose coordinates are floats on purpose."""
    block = {"id": "sfp", "ref": "std/sfp-ganged@1", "at": [14, 3], "count": 4,
             "rows": 2, "pitch": 14.25, "row-pitch": 14.6, "number-from": 1,
             "led": {"ref": "common/led-dot@1", "id-format": "led-{n}",
                     "dx": 2, "dy-top": 10, "dy-bottom": -3.7, "group": "port-leds"},
             "numerals": {"dx": 0, "dy": 6, "font-size": 2.0}}
    run = {"kind": "outlet-run", "id": "outlets", "group": "outlets",
           "segments": [{"ref": "std/iec-c13@1", "count": 2, "at": [10, 5],
                         "pitch": [20, 0],
                         "moulding": {"id-format": "bezel-{m}", "offset": [-1, -1],
                                      "size": [20, 6]}}]}
    return {"format": 1, "chassis": {"size": {"w": 44.0, "h": 440.0}}, **top,
            "views": {"front": {"components": {
                "placements": [{"id": "hand", "ref": "std/rj45@1", "at": [3.0, 4.0]},
                               {"block": "sfp"}, {"block": "outlets"}],
                "blocks": [block, run]},
                "panel": {"decor": [{"block": "outlets"}]},
                "silkscreen": [{"at": [1.0, 2.0], "text": "A"}, {"block": "sfp"}]}}}


def _placements(doc):
    return doc["views"]["front"]["components"]["placements"]


def _generated_pairs(doc):
    """Every `at` and `size` the generator wrote on the front face."""
    view = doc["views"]["front"]
    items = [p for p in _placements(doc) if p["id"] != "hand"]
    items += [s for s in view["silkscreen"] if s["text"] != "A"]
    items += view.get("panel", {}).get("decor", [])
    return [v for it in items for k in ("at", "size") if k in it for v in it[k]]


# ------------------------------------------------- layouts without the key ---

def test_there_are_layouts_to_hold():
    assert LAYOUTS, "no layout.yaml found - the walk is broken or they were removed"


@pytest.mark.heavy
def test_a_layout_without_the_key_expands_to_the_same_source_as_its_device():
    """The byte bar. Every layout in the library carries no `whole-numbers` key,
    and its expansion must hash, as `render.source_bytes` does, to exactly what
    the device beside it hashes to. `expand.py --check` cannot say this: it
    compares parsed values, and 14 equals 14.0."""
    wrong = []
    for lp in LAYOUTS:
        lay = yaml.safe_load(lp.read_text())
        assert "whole-numbers" not in lay, f"{lp.parent.name} already opts in"
        doc = E.expand(lay, LIB, STD)
        dev = yaml.safe_load((lp.parent / "device.yaml").read_text())
        if _source(doc) != _source(dev):
            wrong.append(f"{lp.parent.parent.name}/{lp.parent.name}")
    assert not wrong, f"{len(wrong)} layout(s) no longer expand to their device: {wrong}"


def test_without_the_key_a_whole_coordinate_is_still_written_as_a_float():
    """The behaviour the key leaves alone, stated so a change to it is seen."""
    out = E.expand(_layout(), LIB, STD)
    first = next(p for p in _placements(out) if p["id"] == "port-1")
    assert first["at"] == [14.0, 3.0]
    assert [type(v) for v in first["at"]] == [float, float]
    assert '"at": [14.0, 3.0]' in _source(out)


# ----------------------------------------------------- layouts with the key ---

def test_with_the_key_an_integral_coordinate_is_an_integer():
    out = E.expand(_layout(**{"whole-numbers": True}), LIB, STD)
    by_id = {p["id"]: p for p in _placements(out)}
    assert by_id["port-1"]["at"] == [14, 3]
    assert [type(v) for v in by_id["port-1"]["at"]] == [int, int]
    assert '"at": [14, 3]' in _source(out)
    # the lamp's x is 14 + 2 and its y 3 + 10: whole as well
    assert by_id["led-1"]["at"] == [16, 13]
    assert [type(v) for v in by_id["led-1"]["at"]] == [int, int]


def test_with_the_key_a_fractional_coordinate_stays_a_float():
    out = E.expand(_layout(**{"whole-numbers": True}), LIB, STD)
    by_id = {p["id"]: p for p in _placements(out)}
    # port-2 is the lower row of the first column: y = 3 + 14.6
    assert by_id["port-2"]["at"] == [14, 17.6]
    assert [type(v) for v in by_id["port-2"]["at"]] == [int, float]
    assert by_id["port-3"]["at"] == [28.25, 3]
    assert [type(v) for v in by_id["port-3"]["at"]] == [float, int]
    # 17.6 - 3.7 is not whole
    assert by_id["led-2"]["at"] == [16, 13.9]


def test_with_the_key_every_whole_coordinate_the_generator_wrote_is_an_integer():
    out = E.expand(_layout(**{"whole-numbers": True}), LIB, STD)
    pairs = _generated_pairs(out)
    assert pairs, "nothing was generated"
    assert not [v for v in pairs if isinstance(v, float) and v.is_integer()]
    assert any(type(v) is int for v in pairs), "no whole number was written as one"


def test_the_key_changes_no_value_only_how_a_whole_one_is_written():
    plain = E.expand(_layout(), LIB, STD)
    whole = E.expand(_layout(**{"whole-numbers": True}), LIB, STD)
    assert plain == whole           # 14 == 14.0 in Python, which is the trap
    assert _source(plain) != _source(whole)


def test_an_outlet_runs_moulding_size_is_written_whole_too():
    out = E.expand(_layout(**{"whole-numbers": True}), LIB, STD)
    decor = out["views"]["front"]["panel"]["decor"]
    assert [d["size"] for d in decor] == [[20, 6], [20, 6]]
    assert [type(v) for v in decor[0]["size"]] == [int, int]
    assert [type(v) for v in decor[0]["at"]] == [int, int]
    plain = E.expand(_layout(), LIB, STD)["views"]["front"]["panel"]["decor"]
    assert [type(v) for v in plain[0]["size"]] == [float, float]


def test_the_key_leaves_what_the_author_wrote_as_the_author_wrote_it():
    """Only what the generator computed is normalised. A longhand placement, a
    longhand mark, a chassis figure and a numeral's font size are the author's
    numbers, copied from a device that already hashes the way it does."""
    out = E.expand(_layout(**{"whole-numbers": True}), LIB, STD)
    hand = next(p for p in _placements(out) if p["id"] == "hand")
    assert [type(v) for v in hand["at"]] == [float, float]
    assert [type(v) for v in out["views"]["front"]["silkscreen"][0]["at"]] == [float, float]
    assert type(out["chassis"]["size"]["w"]) is float
    numeral = next(s for s in out["views"]["front"]["silkscreen"] if s.get("for") == "port-1")
    assert type(numeral["font-size"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_the_key_is_a_layout_key_and_is_not_written_to_the_device(value):
    out = E.expand(_layout(**{"whole-numbers": value}), LIB, STD)
    assert "whole-numbers" not in out


@pytest.mark.parametrize("value", ["yes please", 1, 2.0, [True], None])
def test_a_value_that_is_not_true_or_false_is_refused(value):
    with pytest.raises(SystemExit, match="whole-numbers"):
        E.expand(_layout(**{"whole-numbers": value}), LIB, STD)


def test_a_layout_that_opts_in_is_written_and_checked_by_the_tool(tmp_path):
    folder = tmp_path / "vendor" / "model"
    folder.mkdir(parents=True)
    (folder / "layout.yaml").write_text(yaml.safe_dump(_layout(**{"whole-numbers": True})))
    args = [sys.executable, str(TOOL), "--library", str(LIB),
            "--schemas", str(ROOT / "spec/schemas")]
    written = subprocess.run(args + [str(folder / "layout.yaml")],
                             capture_output=True, text=True)
    assert written.returncode == 0, written.stdout + written.stderr
    text = (folder / "device.yaml").read_text()
    assert "at: [14, 3]" in text and "14.0" not in text
    assert "whole-numbers" not in text
    checked = subprocess.run(args + ["--check", str(folder / "layout.yaml")],
                             capture_output=True, text=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr

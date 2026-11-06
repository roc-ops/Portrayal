"""A display says which kind it is, and so what a rack file may put on it.

`class: display` said how wide a display was (`characters`) and nothing about
what sort of display it was, so a rack file could not say what one showed
(docs/display-content-design.md). The library now marks the window and the
kind, from the drawings and the contracts, for the displays that can be marked
and for no others:

  - **L98** asks the kind to fit the numbers: `rows` only on a character
    display, a segment cell one character, `kind` only on a display.
  - **the build** publishes the kind, the rows and the window on the node of
    the drawing, and `displays` in configs.json and components.json.
  - **the corpus** marks exactly the parts it is sure of, and this list is a
    number meant to be changed on purpose.
"""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml

from portrayal import lint
from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FAKE = pathlib.Path("contract.yaml")

# what the library marks, and where: one line for each display it is sure of
MARKED = {
    ("eaton/g4-enmc", "lcd"): "pixel",
    ("ufispace/seg7-status-2", "digit-1"): "segment",
    ("ufispace/seg7-status-2", "digit-2"): "segment",
}


def _l98(doc):
    with lint.collecting() as found:
        lint.lint_component_display(FAKE, doc)
        return [m for m in found.errors if "L98" in m], list(found.warnings)


# --- the rule ----------------------------------------------------------------

def test_a_display_with_a_kind_that_fits_its_numbers_passes():
    errs, warns = _l98({"elements": {
        "lcd": {"class": "display", "kind": "pixel", "characters": 19},
        "grid": {"class": "display", "kind": "character", "characters": 16, "rows": 2},
        "digit": {"class": "display", "kind": "segment", "characters": 1}}})
    assert not errs and not warns


def test_rows_belong_to_a_character_display_only():
    errs, _ = _l98({"elements": {"lcd": {"class": "display", "kind": "pixel",
                                         "characters": 19, "rows": 4}}})
    assert len(errs) == 1 and "Only a character display has rows" in errs[0]
    errs, _ = _l98({"elements": {"lcd": {"class": "display", "characters": 19, "rows": 4}}})
    assert len(errs) == 1


def test_a_segment_cell_is_one_character():
    errs, _ = _l98({"elements": {"digit": {"class": "display", "kind": "segment",
                                           "characters": 2}}})
    assert len(errs) == 1 and "`characters: 1`" in errs[0]


def test_a_lamp_has_no_window_to_set():
    errs, _ = _l98({"elements": {"lamp": {"class": "led", "kind": "pixel",
                                          "states": ["off", "on"]}}})
    assert len(errs) == 1 and "Only a display" in errs[0]


# --- the corpus --------------------------------------------------------------

def _elements():
    for cf in libwalk.iter_components([LIB]):
        d = yaml.safe_load(cf.read_text()) or {}
        ref = f"{cf.parent.parent.parent.name}/{cf.parent.parent.name}"
        for eid, spec in (d.get("elements") or {}).items():
            if isinstance(spec, dict) and spec.get("kind") is not None:
                yield ref, eid, spec


def test_the_library_marks_the_displays_it_is_sure_of_and_no_others():
    got = {(ref, eid): spec["kind"] for ref, eid, spec in _elements()}
    assert got == MARKED, (
        "a display that now says its kind (or stopped saying it) changes what a "
        "rack file can set; list it here on purpose, and say in "
        "docs/display-content-design.md where its window and kind come from")


def test_every_marked_display_is_a_display_with_a_window_and_a_width():
    for ref, eid, spec in _elements():
        where = f"{ref}:{eid}"
        assert spec.get("class") == "display", where
        assert spec.get("at") and spec.get("size"), f"{where}: no window"
        assert spec.get("characters"), f"{where}: no width"
        if spec["kind"] == "segment":
            assert spec["characters"] == 1, where
            assert any(s.get("lights") for s in spec["states"]), (
                f"{where}: a segment cell's states name the segments they light")


# --- the build ---------------------------------------------------------------

def _render(tmp_path, device):
    r = subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/render.py"),
         str(LIB / f"devices/{device}/device.yaml"),
         "--library", str(LIB), "--out", str(tmp_path)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def test_the_pdu_lcd_is_published_on_its_node_with_its_window(tmp_path):
    _render(tmp_path, "eaton/evma8365x")
    front = (tmp_path / "evma8365x.front.svg").read_text()
    node = next(line for line in front.splitlines()
                if 'id="network-module--module--lcd"' in line)
    assert 'data-display-kind="pixel"' in node and 'data-characters="19"' in node
    assert 'data-display-window="8.95 52.15 31.1 30.9"' in node
    assert "data-display-rows" not in node, "a pixel display has no rows and none is invented"
    # the window is in the frame of its part, and the node is that window
    for a, v in (("x", "8.95"), ("y", "52.15"), ("width", "31.1"), ("height", "30.9")):
        assert f' {a}="{v}"' in node
    # the other elements of the module say nothing of a kind
    assert front.count("data-display-kind=") == 1
    configs = json.loads((tmp_path / "evma8365x.configs.json").read_text())
    assert all("displays" not in c for c in configs["configs"]), (
        "the module in the bay is the module's to publish, not the device's")


@pytest.mark.heavy
def test_the_status_digits_are_published_as_one_display_of_the_part(tmp_path):
    for device, part in (("ufispace/s9700-53dx", "status-display"),
                         ("ufispace/s9705-48d", "beacon")):
        name = device.split("/")[1]
        _render(tmp_path / name, device)
        outdir = tmp_path / name
        face = next(outdir.glob(f"{name}.*.front.svg")).read_text()
        for digit in ("digit-1", "digit-2"):
            node = next(line for line in face.splitlines()
                        if f'data-path="{part}/{digit}"' in line)
            assert 'data-display-kind="segment"' in node and 'data-characters="1"' in node
            assert 'data-display-window="' in node
        configs = json.loads((outdir / f"{name}.configs.json").read_text())
        for c in configs["configs"]:
            shown = c["displays"][part]
            assert sorted(shown) == ["digit-1", "digit-2"]
            assert shown["digit-1"]["kind"] == "segment"
            assert shown["digit-1"]["glyphs"][:3] == ["0", "1", "2"]
            assert shown["digit-1"]["glyphs"][-1] == "blank"
            assert shown["digit-1"]["at"] != shown["digit-2"]["at"]


def test_a_device_without_a_marked_display_publishes_none(tmp_path):
    _render(tmp_path, "cisco/asr-9901")
    assert "data-display-kind=" not in (tmp_path / "asr-9901.front.svg").read_text()
    configs = json.loads((tmp_path / "asr-9901.configs.json").read_text())
    assert all("displays" not in c for c in configs["configs"])
    # the matrix still publishes its width and its readings, as it did
    assert 'data-characters="4"' in (tmp_path / "asr-9901.front.svg").read_text()


def test_the_components_index_lists_the_displays_of_a_part():
    comps = ROOT / "library/dist/components.json"
    if not comps.exists():
        pytest.skip("library/dist not built - run ./build.sh")
    entries = {f"{c['ns']}/{c['name']}": c for c in json.loads(comps.read_text())["components"]}
    assert entries["eaton/g4-enmc"]["displays"] == {
        "lcd": {"kind": "pixel", "characters": 19, "at": [8.95, 52.15], "size": [31.1, 30.9]}}
    digits = entries["ufispace/seg7-status-2"]["displays"]
    assert sorted(digits) == ["digit-1", "digit-2"]
    assert digits["digit-1"]["glyphs"][0] == "0"
    marked = {k for k, c in entries.items() if c.get("displays")}
    assert marked == {ref for ref, _ in MARKED}

"""A display says how wide it is, and what it is able to say.

`class: display` existed for a year carrying a description and nothing else.
Thirty elements across nineteen components were visibly displays and could
answer no question at all: not how many characters they showed, and not what any
of those characters could spell. The ASR 9901 wrote it down as a gap in so many
words - "`class: led` takes states, and a four-character display takes strings" -
and Cisco tabulates the strings, twenty-eight of them, in Tables 25 and 26 of the
fixed-port hardware installation guide.

Three things hold that shut, and this file tests all three:

  - **L98** asks every display for `characters`, refuses `messages` on anything
    that is not a display, and rejects a reading longer than the display it sits
    on. The capacity is what makes the vocabulary checkable: PSEQ on a
    four-character matrix is right and PSEQX is a transcription error nobody
    catches by eye.
  - **render.py** publishes both on their own attributes, never on `data-states`,
    because `statesOfEl` silently drops a value that is not a list of lowercase
    tokens - so INIT BOOT IMEM put there would arrive as nothing at all.
  - **the corpus** carries no silent display any more, which is a number meant to
    stay at zero rather than to go up.
"""
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


def _run(doc):
    with lint.collecting() as found:
        lint.lint_component_display(FAKE, doc)
        return [m for m in found.errors if "L98" in m], list(found.warnings)


# --- the rule ----------------------------------------------------------------

def test_a_display_that_does_not_say_how_wide_it_is_warns():
    errs, warns = _run({"elements": {"led-matrix": {"class": "display"}}})
    assert not errs
    assert len(warns) == 1 and "led-matrix" in warns[0]


def test_a_display_that_says_how_wide_it_is_passes():
    errs, warns = _run({"elements": {"led-matrix": {
        "class": "display", "characters": 4,
        "messages": [{"text": "INIT"}, {"text": "RMN"}]}}})
    assert not errs and not warns


def test_a_reading_longer_than_the_display_is_an_error():
    """The one defect a reader cannot see and a rule can."""
    errs, _ = _run({"elements": {"led-matrix": {
        "class": "display", "characters": 4,
        "messages": [{"text": "INIT"}, {"text": "ROMMON"}]}}})
    assert len(errs) == 1
    assert "'ROMMON'" in errs[0] and "which is 6" in errs[0]


def test_messages_on_a_lamp_is_an_error():
    """A lamp's vocabulary is colours. Putting words in it is a class mistake,
    not a missing number, so it is reported as itself and not as "no
    characters"."""
    errs, warns = _run({"elements": {"lamp": {
        "class": "led", "states": ["off", "on"],
        "messages": [{"text": "INIT"}]}}})
    assert len(errs) == 1 and "class 'led'" in errs[0]
    assert not warns


def test_the_rule_does_not_ask_for_a_vocabulary():
    """A seven-segment cell's vocabulary is per-cell glyphs and lives in
    `states`; the window that frames two of them has no vocabulary of its own at
    all. Requiring `messages` would push both into inventing one."""
    errs, warns = _run({"elements": {
        "window": {"class": "display", "characters": 2},
        "digit-1": {"class": "display", "characters": 1,
                    "states": [{"name": "0", "lights": ["a", "b"]}]},
    }})
    assert not errs and not warns


# --- the corpus --------------------------------------------------------------

def _displays():
    """(ref, element id, spec) for every `class: display` in the library."""
    for cf in libwalk.iter_components([LIB]):
        d = yaml.safe_load(cf.read_text()) or {}
        ref = f"{cf.parent.parent.parent.name}/{cf.parent.parent.name}"
        for eid, spec in (d.get("elements") or {}).items():
            if isinstance(spec, dict) and spec.get("class") == "display":
                yield ref, eid, spec


def test_the_library_has_displays_to_talk_about():
    assert len(list(_displays())) >= 31


def test_no_display_in_the_library_is_silent_about_its_width():
    """A number meant to stay at zero. Every one of the thirty displays that
    predate `characters:` was given one from the document that describes it -
    Cisco's "one row of four characters", a seven-segment cell's single glyph -
    so a new display arriving without one is new work, not inherited silence."""
    silent = [f"{ref}:{eid}" for ref, eid, spec in _displays()
              if not spec.get("characters")]
    assert silent == [], (
        f"{len(silent)} display(s) do not say how many characters they show: "
        f"{silent}. L98 says the same thing as a warning; this says it as a "
        "line that has to be deliberately changed")


def test_every_reading_in_the_library_fits_its_display():
    over = [(ref, eid, m["text"], spec["characters"])
            for ref, eid, spec in _displays()
            for m in (spec.get("messages") or [])
            if len(m["text"]) > spec.get("characters", 0)]
    assert over == [], over


def test_the_asr_9901_can_be_asked_what_its_matrix_says():
    """The gap this closes, stated as the question it could not answer."""
    d = yaml.safe_load(
        (LIB / "components/cisco/led-matrix-4/v1/contract.yaml").read_text())
    msgs = d["elements"]["matrix"]["messages"]
    assert d["elements"]["matrix"]["characters"] == 4
    assert len(msgs) == 28, "Table 25 is twenty-five readings and Table 26 three"
    texts = [m["text"] for m in msgs]
    assert texts[:5] == ["INIT", "BOOT", "IMEM", "IGEN", "ICBC"]
    assert texts[-3:] == ["PST1", "PST2", "PST3"]
    assert all(m.get("meaning") for m in msgs), "a reading without its meaning"
    assert len(set(texts)) == len(texts), "a reading listed twice"


@pytest.mark.parametrize("ref,eid,spec", list(_displays()))
def test_no_reading_carries_whitespace(ref, eid, spec):
    """The compiled drawing publishes the whole vocabulary on one attribute and
    a consumer splits it on spaces, so a reading with a space in it would arrive
    as two. The schema's pattern says so; this says it about the corpus."""
    for m in (spec.get("messages") or []):
        assert m["text"].split() == [m["text"]], f"{ref}:{eid} {m['text']!r}"


# --- the compiled drawing ----------------------------------------------------

def test_the_vocabulary_reaches_the_drawing_on_its_own_attribute(tmp_path):
    """Both facts have to arrive, and NEITHER may arrive on `data-states`.

    `statesOfEl` throws away a data-states whose tokens are not lowercase
    `[a-z0-9-]` - it was written that way because several contracts had put a
    sentence where the state names go, and offering a chip called "=" sets a
    class nothing paints. INIT BOOT IMEM fails the same test, so a display whose
    vocabulary rode data-states would read as a display that knows nothing, with
    no error anywhere.
    """
    r = subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/render.py"),
         str(LIB / "devices/cisco/asr-9901/device.yaml"),
         "--library", str(LIB), "--out", str(tmp_path)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    front = (tmp_path / "asr-9901.front.svg").read_text()

    assert 'data-characters="4"' in front
    assert ('data-messages="INIT BOOT IMEM IGEN ICBC SCPI STID PSEQ DBPO KPWR '
            'LGNP LGNI IPNP IPNI RMN LOAD RRST MVB MBI IOXR LDG INCP OOSM ACT '
            'AUTH PST1 PST2 PST3"') in front
    assert "INIT" not in front.split('data-messages="')[0], (
        "a reading turned up somewhere other than data-messages")
    assert 'data-class="display"' in front


def test_a_seven_segment_cell_publishes_its_width_and_no_vocabulary(tmp_path):
    """The other shape of display: capacity from `characters`, glyphs from
    `states`, and no `messages` anywhere."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/render.py"),
         str(LIB / "devices/edgecore/cor580/device.yaml"),
         "--library", str(LIB), "--out", str(tmp_path)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    front = (tmp_path / "cor580.front.svg").read_text()

    assert front.count('data-characters="1"') == 4      # two digits, two points
    assert front.count('data-characters="2"') == 1      # the window over them
    assert "data-messages" not in front

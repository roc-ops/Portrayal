"""A configuration's description must not state a power draw its export contradicts.

A configuration takes its own `attrs` and its own `export-description`, and
`manifest.config_attrs` is the one answer the exporters read. A configuration
that says in words "maximum system consumption 1276 W" while the figure it
exports is the device's 1300 W tells a reader two things about one build. This
reads every configuration of every device, takes the draw figures its
`description` and `export-description` state, and compares them with the
resolved `power-*-w` fields.

THE NARROW RULE. A figure is a number followed by `W` or `watts`. It is a DRAW
figure only when a draw word stands within 45 characters of it:

  - `typical`                        -> compared with the resolved `power-typical-w` keys
  - `max` or `maximum`               -> compared with the resolved `power-max-*` keys
  - `power draw`, `consumption`,
    `power budget`, `draws`          -> compared with every resolved `power-*-w` key

The NEAREST draw word gives the role. A figure with a supply, PoE, output or
rating word ("1+1 hot-swap 1500 W PSUs", "PoE budget 740 W")
within 16 characters of the figure is ignored, and so is any unit other than watts (`kW`, `Wh`, `V`, `A`).

A configuration contradicts for a role when it states figures of that role, none
of them equals a resolved key of that role, and the resolved figure does not
appear anywhere else in the same text (a sentence that gives two optics
envelopes, "1263 W with MSA optics, 1534 W with ZR", is not a contradiction of
the 1534 W it exports). A text that states no draw figure is not read.

A contradiction found here is a finding for that device's own change: this test
edits no device and no export. `KNOWN` lists the ones that exist today, one line
each, and a line leaves when its device is fixed; a listed pair that no longer
contradicts fails, so the list cannot go stale.
"""
import functools
import re
from pathlib import Path

import pytest
import yaml

from portrayal import libwalk, manifest

LIB = Path(__file__).resolve().parents[2] / "library"

FIGURE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(?:W|watts?)\b(?!h)")
WORDS = (
    ("typical", re.compile(r"typical", re.I)),
    ("max", re.compile(r"\bmax(?:imum)?\b", re.I)),
    ("any", re.compile(r"power draw|consum\w*|power budget|\bdraws?\b", re.I)),
)
NOT_A_DRAW = re.compile(
    r"PSU|power suppl|supply|supplies|PoE|PSE|output|rated|hot-swap|by SKU|per port|per-port", re.I)
WINDOW = 45
BESIDE = 16  # a supply, PoE or rating word this close to the figure says what the figure is
FIELDS = ("description", "export-description")

# (device, configuration, role) -> where the contradiction is and which change clears it.
KNOWN = {}


def draw_figures(text):
    """[(watts, role)] for every draw figure the text states; see the module doc."""
    text = " ".join(str(text or "").split())
    out = []
    for m in FIGURE.finditer(text):
        lo, hi = max(0, m.start() - WINDOW), m.end() + WINDOW
        best = None
        for role, rx in WORDS:
            for w in rx.finditer(text, lo, hi):
                gap = m.start() - w.end() if w.end() <= m.start() else w.start() - m.end()
                if best is None or gap < best[0]:
                    best = (gap, role)
        beside = text[max(0, m.start() - BESIDE):m.start()] + " " + text[m.end():m.end() + BESIDE]
        if best is None or NOT_A_DRAW.search(beside):
            continue
        out.append((float(m.group(1).replace(",", "")), best[1]))
    return out


def every_watt(text):
    return {float(m.group(1).replace(",", "")) for m in FIGURE.finditer(" ".join(str(text or "").split()))}


def resolved_power(device, cfg):
    """{key: watts} of the configuration's resolved `power` section, as the exporter reads it."""
    section = manifest.config_attrs(device, cfg).get("power") or {}
    out = {}
    for k, v in section.items():
        if k.startswith("power-") and k.endswith("w"):
            try:
                out[k] = float(str(v).replace(",", "").split()[0])
            except (ValueError, IndexError):
                pass
    return out


def contradictions(device, cfg):
    """[role] for each draw role the configuration's text states and the export contradicts."""
    text = " ".join(str((cfg or {}).get(f) or "") for f in FIELDS)
    stated = {}
    for watts, role in draw_figures(text):
        stated.setdefault(role, []).append(watts)
    have = resolved_power(device, cfg)
    elsewhere = every_watt(text)
    bad = []
    for role, figs in sorted(stated.items()):
        keys = [k for k in have if role == "any" or role in k]
        resolved = {have[k] for k in keys}
        if not (resolved & set(figs)) and not (resolved & elsewhere):
            bad.append(role)
    return bad


@functools.lru_cache(maxsize=None)
def found():
    out = {}
    for path in libwalk.iter_devices(LIB):
        device = yaml.safe_load(path.read_text())
        slug = f"{path.parent.parent.name}/{path.parent.name}"
        for name, cfg in (device.get("configurations") or {}).items():
            for role in contradictions(device, cfg):
                out[(slug, name, role)] = True
    return out


# --- the pattern: one good and one bad sentence for each word and unit ---------

@pytest.mark.parametrize("text,expected", [
    ("Typical power 464 W with no optics.", [(464.0, "typical")]),
    ("Typical power 464 kW with no optics.", []),
    ("Maximum 1300 W at 45 C.", [(1300.0, "max")]),
    ("Max 1300 V at 45 C.", []),
    ("System consumption is 685 watts.", [(685.0, "any")]),
    ("System consumption is 685 Wh.", []),
    ("The power draw is 1,234.5 W.", [(1234.5, "any")]),
    ("Mounts 1234.5 W of rack space.", []),
    ("The power budget is 600 W.", [(600.0, "any")]),
    ("The box draws 220 W.", [(220.0, "any")]),
    ("Dual 1600 W AC supplies; maximum draw 1300 W.", [(1300.0, "any")]),
    ("PSU rated 1600 W; maximum draw 1300 W.", [(1300.0, "any")]),
    ("1+1 hot-swap 1500 W PSUs, maximum rating listed.", []),
    ("PoE budget 740 W (maximum for all ports).", []),
    ("Weighs 12 kg and fits in 1U.", []),
])
def test_the_pattern_reads_a_draw_figure_and_ignores_the_rest(text, expected):
    assert draw_figures(text) == expected


def test_the_nearest_draw_word_gives_the_role():
    assert draw_figures("535 W typical and 851 W maximum") == [(535.0, "typical"), (851.0, "max")]


def test_a_second_envelope_in_the_sentence_does_not_contradict():
    device = {"attrs": {"power": {"power-max-w": "1534"}}}
    cfg = {"description": "Maximum system consumption 1263 W under MSA optics, 1534 W with ZR."}
    assert contradictions(device, cfg) == []


def test_a_figure_the_export_does_not_carry_is_a_contradiction():
    device = {"attrs": {"power": {"power-max-w": "1300"}}}
    cfg = {"description": "The maximum system consumption for this build is 1276 W."}
    assert contradictions(device, cfg) == ["any"]
    assert contradictions(device, {"description": "Maximum 1276 W."}) == ["max"]


def test_the_configurations_own_attrs_are_what_it_is_read_against():
    device = {"attrs": {"power": {"power-max-w": "1300"}}}
    cfg = {"description": "Maximum 1276 W.", "attrs": {"power": {"power-max-w": "1276"}}}
    assert contradictions(device, cfg) == []


# --- the library ---------------------------------------------------------------

@pytest.mark.heavy
def test_no_configuration_description_contradicts_its_exported_power():
    now = found()
    new = sorted(k for k in now if k not in KNOWN)
    assert not new, (
        "a configuration's text states a draw its resolved power fields do not carry; "
        "give the configuration its own `attrs.power`, or correct the text: "
        + "; ".join(f"{s}:{c} ({r})" for s, c, r in new))


@pytest.mark.heavy
def test_every_known_contradiction_is_still_one():
    gone = sorted(k for k in KNOWN if k not in found())
    assert not gone, "no longer contradicts, remove it from KNOWN: " + "; ".join(map(str, gone))

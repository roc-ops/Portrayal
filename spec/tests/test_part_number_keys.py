"""L128: a part number has no stray space in it (#731).

A `part-numbers` key is the DCIM model, its slug and the export file name.
#720 was `9716-32D-O-A C-F-UK` beside `-AC-F-US`, `-EU` and `-JP`. A blanket
"no whitespace" rule would fire on names that mean their spaces, so these pin
both halves: what it catches, and the library's own keys it must leave alone.
"""
import pathlib

import pytest
import yaml

import libdata
from portrayal import libwalk
from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]


def run(pns, where="configuration"):
    if where == "configuration":
        doc = {"configurations": {"ac": {"part-numbers": pns}}}
    else:
        doc = {"part-numbers": pns}
    with L.collecting() as found:
        L.lint_part_number_keys("t/device.yaml", doc)
    return ([e for e in found.errors if "[L128]" in e],
            [w for w in found.warnings if "[L128]" in w])


def test_the_720_key_is_caught():
    errors, warnings = run({"9716-32D-O-AC-F-US": {}, "9716-32D-O-A C-F-UK": {}})
    assert errors == []
    assert len(warnings) == 1, warnings
    assert "-A C-" in warnings[0] and "9716-32D-O-A C-F-UK" in warnings[0]


def test_a_split_token_is_found_at_the_top_level_too():
    _errors, warnings = run({"AB-12 34-X": "x"}, where="top")
    assert len(warnings) == 1 and "part-numbers:" in warnings[0], warnings


@pytest.mark.parametrize("key", [
    "AS7535-28XB-O-AC-F V2",            # edgecore/csr440: the vendor's own suffix
    "AS7535-28XB-O-AC-F-UK V2",
    "ASR 9901 Router, AC supplies",     # cisco/asr-99xx: descriptive keys
    "ASR 9001-S Router with 2 x 10 GE",
    "Upgrade license for 120G Bandwidth",
    "7750 SR-12 (pre-2016 chassis)",    # nokia/sr-12
    "LMFS-F AA kit",                    # nokia/lmfs-f
    "9716-32D-O-AC-F-UK",
])
def test_names_that_mean_their_spaces_pass(key):
    assert run({key: {}}) == ([], [])


@pytest.mark.parametrize("ch", [" ", " ", " ", "\t", "​", "﻿"])
def test_whitespace_that_is_not_a_plain_space_is_an_error(ch):
    errors, _warnings = run({f"9716-32D-O-AC-F{ch}UK": {}})
    assert len(errors) == 1, errors
    assert f"U+{ord(ch):04X}" in errors[0]


@pytest.mark.parametrize("key", [" AS7535-28XB", "AS7535-28XB ", "AS7535-28XB "])
def test_leading_or_trailing_whitespace_is_an_error(key):
    errors, _warnings = run({key: {}})
    assert any("leading or trailing" in e for e in errors), errors


def test_the_library_raises_none():
    """Every part-number key in the library, device and listing alike, is
    clean - the rule lands without a baseline entry or a waiver."""
    docs = [(f, d) for _slug, f, d in libdata.library()]
    for f in libwalk.iter_listings([ROOT / "library"]):
        docs.append((f, yaml.safe_load(f.read_text())))
    seen = 0
    with L.collecting() as found:
        for f, d in docs:
            if isinstance(d, dict):
                for cfg in (d.get("configurations") or {}).values():
                    seen += len((cfg or {}).get("part-numbers") or {})
                L.lint_part_number_keys(f, d)
    hits = [m for m in found.errors + found.warnings if "[L128]" in m]
    assert seen > 200, f"measured only {seen} keys - the walk found nothing to check"
    assert hits == [], hits

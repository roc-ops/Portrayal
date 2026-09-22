"""L109: a declared `optical.polarity` is what the paths actually wire.

The patterns are read off FS's own cassette diagrams (the FHD universal-polarity
blog): Type A straight through, AF each duplex pair swapped, universal fibre j
paired with fibre n+1-j. The rule must FAIL a wrong claim, not merely stay quiet
on right ones - so each pattern is also checked under every other name.
"""
import pathlib

import pytest
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = [str(ROOT / "library")]


def cassette(pol, fibres):
    """A six-adapter FHD LC cassette whose port p takes MTP fibre fibres[p-1]."""
    parts = [{"id": f"lc{i}", "ref": "common/lc-duplex-v-adapter@4", "at": [15.81 + 12.9 * (i - 1), 10.66]}
             for i in range(1, 7)]
    paths = [{"from": f"lc{(p - 1) // 2 + 1}.{2 - p % 2}", "to": f"rear:mtp.{fibres[p - 1]}"}
             for p in range(1, 13)]
    return {"parts": parts, "faces": {"rear": {"ref": "fs/fhd-1mtp6lcd-rear@2"}},
            "optical": {"polarity": pol, "paths": paths}}


def l109(data):
    got = []
    real_err = lint.err
    lint.err = lambda path, rule, msg: got.append((rule, msg))
    try:
        lint.lint_component_optical_polarity("t", data, LIB)
    finally:
        lint.err = real_err
    return [m for r, m in got if r == "L109"]


@pytest.mark.parametrize("pol", ["a", "af", "universal"])
def test_each_pattern_passes_under_its_own_name(pol):
    assert l109(cassette(pol, lint.POLARITY_PATTERNS[pol](12))) == []


@pytest.mark.parametrize("claimed,wired", [(c, w) for c in ("a", "af", "universal")
                                           for w in ("a", "af", "universal") if c != w])
def test_each_pattern_fails_under_every_other_name(claimed, wired):
    msgs = l109(cassette(claimed, lint.POLARITY_PATTERNS[wired](12)))
    assert msgs, f"{wired} wiring declared {claimed!r} passed"


def test_the_patterns_are_fs_s_diagrams():
    # port 1, 2, 3, 4 of a 12-fibre cassette
    assert lint.POLARITY_PATTERNS["a"](12)[:4] == [1, 2, 3, 4]
    assert lint.POLARITY_PATTERNS["af"](12)[:4] == [2, 1, 4, 3]
    assert lint.POLARITY_PATTERNS["universal"](12)[:4] == [1, 12, 2, 11]


def test_every_fs_cassette_wires_its_declared_polarity():
    checked = 0
    for f in sorted((ROOT / "library/components/fs").glob("*/v*/contract.yaml")):
        d = yaml.safe_load(f.read_text())
        if not (d.get("optical") or {}).get("polarity"):
            continue
        checked += 1
        assert l109(d) == [], f"{f}: {l109(d)}"
    assert checked >= 9, f"only {checked} FS cassettes declare a polarity"

"""L109: a declared `optical.polarity` is what the paths actually wire.

The patterns are read off FS's own cassette diagrams (the FHD universal-polarity
blog, and the FHD MTP-12/24 Cassettes Datasheet): Type A straight through, AF
each duplex pair swapped - and at 24 fibres the two rows exchanged as well -
universal fibre j paired with fibre n+1-j. The rule must FAIL a wrong claim, not
merely stay quiet on right ones - so each pattern is also checked under every
other name.
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
    return {"parts": parts, "faces": {"rear": {"ref": "fs/fhd-1mtp6lcd-rear@3"}},
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


def test_a_24_fibre_af_exchanges_the_rows_as_well_as_the_pairs():
    # The datasheet, p. 6 (MTP-24 Type AF), Inner Sequence beneath Port Labeling:
    # ports 1, 2, 11, 12 take 14, 13, 24, 23; ports 13, 14, 23, 24 take 2, 1, 12, 11.
    af = lint.POLARITY_PATTERNS["af"](24)
    assert [af[p - 1] for p in (1, 2, 11, 12)] == [14, 13, 24, 23]
    assert [af[p - 1] for p in (13, 14, 23, 24)] == [2, 1, 12, 11]
    assert sorted(af) == list(range(1, 25))


AF24 = ROOT / "library/components/fs/fhd-1mtp24-lc-os2-af/v3/contract.yaml"


def rewired(contract, fibres):
    """The contract with port p (lcNN.1 odd, lcNN.2 even) wired to fibres[p-1]."""
    d = yaml.safe_load(contract.read_text())
    order = d["optical"]["front-order"]
    d["optical"]["paths"] = [
        {"from": f"{order[(p - 1) // 2]}.{2 - p % 2}", "to": f"rear:mtp.{fibres[p - 1]}"}
        for p in range(1, 25)]
    return d


def test_the_pair_swap_alone_fails_a_24_fibre_af():
    # What the part wired until 3.0.1: right for an MTP-12, wrong for this one.
    pair_swap = [p + 1 if p % 2 else p - 1 for p in range(1, 25)]
    msgs = l109(rewired(AF24, pair_swap))
    assert msgs and "port 1 takes mtp fibre 2 where 'af' puts fibre 14" in msgs[0], msgs


@pytest.mark.parametrize("wired", ["a", "universal"])
def test_other_wirings_fail_a_24_fibre_af(wired):
    assert l109(rewired(AF24, lint.POLARITY_PATTERNS[wired](24)))


def test_every_fs_cassette_wires_its_declared_polarity():
    checked = 0
    for f in sorted((ROOT / "library/components/fs").glob("*/v*/contract.yaml")):
        d = yaml.safe_load(f.read_text())
        if not (d.get("optical") or {}).get("polarity"):
            continue
        checked += 1
        assert l109(d) == [], f"{f}: {l109(d)}"
    assert checked >= 9, f"only {checked} FS cassettes declare a polarity"

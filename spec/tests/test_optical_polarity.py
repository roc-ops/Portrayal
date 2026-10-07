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
AF24 = ROOT / "library/components/fs/fhd-1mtp24-lc-os2-af/v4/contract.yaml"


def paths_for(order, fibres):
    """Port p takes MTP fibre fibres[p-1]; port p is bore 1 (odd p) or 2 (even p)
    of adapter order[(p-1)//2] - FS's printed numbering, the lower bore odd."""
    return [{"from": f"{order[(p - 1) // 2]}.{2 - p % 2}", "to": f"rear:mtp.{fibres[p - 1]}"}
            for p in range(1, len(fibres) + 1)]


def cassette(pol, fibres):
    """A six-adapter FHD LC cassette whose port p takes MTP fibre fibres[p-1]."""
    parts = [{"id": f"lc{i}", "ref": "common/lc-duplex-v-adapter@6", "at": [15.81 + 12.9 * (i - 1), 10.66]}
             for i in range(1, 7)]
    return {"parts": parts, "faces": {"rear": {"ref": "fs/fhd-1mtp6lcd-rear@3"}},
            "optical": {"polarity": pol, "paths": paths_for([p["id"] for p in parts], fibres)}}


def rewired(contract, fibres, pol=None):
    """The real contract, its paths replaced and (if given) its polarity claim."""
    d = yaml.safe_load(contract.read_text())
    d["optical"]["paths"] = paths_for(d["optical"]["front-order"], fibres)
    if pol:
        d["optical"]["polarity"] = pol
    return d


def wired(n, pol, fibres):
    """An n-fibre cassette claiming `pol`: the synthetic MTP-12, or the real MTP-24 AF."""
    return cassette(pol, fibres) if n == 12 else rewired(AF24, fibres, pol)


def l109_both(data):
    """(errors, warnings) that L109 raises on one contract."""
    got = []
    real_err, real_warn = lint.err, lint.warn
    lint.err = lambda path, rule, msg: got.append(("err", rule, msg))
    lint.warn = lambda path, rule, msg: got.append(("warn", rule, msg))
    try:
        lint.lint_component_optical_polarity("t", data, LIB)
    finally:
        lint.err, lint.warn = real_err, real_warn
    return ([m for k, r, m in got if r == "L109" and k == "err"],
            [m for k, r, m in got if r == "L109" and k == "warn"])


def l109(data):
    return l109_both(data)[0]


# Each pattern at each width a held source draws it at (#524); universal at 24
# is not one of them, and is tested as unjudged below.
SOURCED = [(pol, n) for pol, widths in lint.POLARITY_WIDTHS.items() for n in widths]


@pytest.mark.parametrize("pol,n", SOURCED)
def test_each_pattern_passes_under_its_own_name(pol, n):
    assert l109_both(wired(n, pol, lint.POLARITY_PATTERNS[pol](n))) == ([], [])


@pytest.mark.parametrize("claimed,wiring,n", [(c, w, n) for c, n in SOURCED
                                              for w in ("a", "af", "universal") if c != w])
def test_each_pattern_fails_under_every_other_name(claimed, wiring, n):
    msgs = l109(wired(n, claimed, lint.POLARITY_PATTERNS[wiring](n)))
    assert msgs, f"{n}-fibre {wiring} wiring declared {claimed!r} passed"


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


def test_the_pair_swap_alone_fails_a_24_fibre_af():
    # What the part wired until 3.0.1: right for an MTP-12, wrong for this one.
    pair_swap = [p + 1 if p % 2 else p - 1 for p in range(1, 25)]
    msgs = l109(rewired(AF24, pair_swap))
    assert msgs and "port 1 takes mtp fibre 2 where 'af' puts fibre 14" in msgs[0], msgs


def test_every_fs_cassette_wires_its_declared_polarity():
    checked = 0
    for f in sorted((ROOT / "library/components/fs").glob("*/v*/contract.yaml")):
        d = yaml.safe_load(f.read_text())
        if not (d.get("optical") or {}).get("polarity"):
            continue
        checked += 1
        assert l109(d) == [], f"{f}: {l109(d)}"
    assert checked >= 9, f"only {checked} FS cassettes declare a polarity"


# THE WIDTH IS THE CONNECTOR'S (#524). Until then the pattern was chosen by how
# many paths reached the connector, so an MTP-24 with fibres unused, or wired
# to twelve ports, was judged as a narrower connector.
AF24_ROWS = lint.POLARITY_PATTERNS["af"](24)
PAIR_SWAP = [p + 1 if p % 2 else p - 1 for p in range(1, 25)]


def test_an_mtp24_af_with_fibres_unused_is_judged_at_24():
    # ports 1-20 wired, the last four declared unused: still an MTP-24
    assert l109_both(rewired(AF24, AF24_ROWS[:20])) == ([], [])
    msgs = l109(rewired(AF24, PAIR_SWAP[:20]))
    assert msgs and "port 1 takes mtp fibre 2 where 'af' puts fibre 14" in msgs[0], msgs
    assert "24-fibre connector" in msgs[0]


def test_an_mtp24_wired_to_twelve_ports_is_not_judged_as_an_mtp12():
    assert l109(rewired(AF24, AF24_ROWS[:12])) == []
    # the MTP-12 AF, which a path count of 12 used to ask for, is wrong here
    msgs = l109(rewired(AF24, lint.POLARITY_PATTERNS["af"](12)))
    assert msgs and "where 'af' puts fibre 14" in msgs[0], msgs


def test_unused_ports_at_the_start_of_a_block_keep_their_numbers():
    # ports 1-4 unused: port 5 is still the MTP-24's fifth, fibre 18 under af
    d = rewired(AF24, AF24_ROWS)
    d["optical"]["paths"] = d["optical"]["paths"][4:]
    assert l109(d) == []
    d["optical"]["paths"] = rewired(AF24, PAIR_SWAP)["optical"]["paths"][4:]
    msgs = l109(d)
    assert msgs and "port 5 takes mtp fibre 6 where 'af' puts fibre 18" in msgs[0], msgs


# A WIDTH NO SOURCE DRAWS IS NOT JUDGED (#524): a warning that says so, never a
# pass and never a fail, whatever the paths wire.
@pytest.mark.parametrize("wiring", ["a", "af", "universal"])
def test_a_24_fibre_universal_is_not_judged(wiring):
    assert 24 not in lint.POLARITY_WIDTHS["universal"]
    errors, warnings = l109_both(rewired(AF24, lint.POLARITY_PATTERNS[wiring](24), "universal"))
    assert errors == []
    assert len(warnings) == 1 and "polarity not judged at this width" in warnings[0]
    assert "24-fibre connector(s) mtp," in warnings[0], warnings


def test_the_mtp16_panel_is_not_judged_at_16():
    # The one library part at a width no held source draws: FS's polarity white
    # paper draws a 16-fibre trunk Type B only. One warning for its twelve MTPs.
    d = yaml.safe_load((ROOT / "library/components/fs/fhd-fap12mtp16-a/v1/contract.yaml").read_text())
    errors, warnings = l109_both(d)
    assert errors == [] and len(warnings) == 1, warnings
    assert "'a' on 16-fibre connector(s) b01, b02" in warnings[0]


# A TRUNK-STATED SINGLE-FACED MODULE (#246) is judged like a cassette: its trunk
# is the part `optical.trunk` names, not a `rear:` endpoint.
def single_faced(pol, fibres):
    """An MPO-12 trunk left of six LC duplexes, all on one face. The LC ports
    are numbered 13-24: the trunk's twelve positions are counted first."""
    parts = [{"id": "mpo", "ref": "common/mpo-adapter@2", "at": [2.0, 10.0]}]
    parts += [{"id": f"lc{i}", "ref": "common/lc-duplex-v-adapter@6",
               "at": [30.0 + 12.9 * (i - 1), 10.66]} for i in range(1, 7)]
    paths = [{"from": f"lc{(p - 1) // 2 + 1}.{2 - p % 2}", "to": f"mpo.{fibres[p - 1]}"}
             for p in range(1, len(fibres) + 1)]
    return {"parts": parts, "optical": {"polarity": pol, "trunk": ["mpo"], "paths": paths}}


def test_a_trunk_stated_module_is_judged():
    assert l109_both(single_faced("af", lint.POLARITY_PATTERNS["af"](12))) == ([], [])
    msgs = l109(single_faced("af", lint.POLARITY_PATTERNS["a"](12)))
    assert msgs and "port 13 takes mpo fibre 1 where 'af' puts fibre 2" in msgs[0], msgs

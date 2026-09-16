"""The third state: the vendor publishes none, and somebody checked.

A blank in a comparison meant two things that looked identical - the vendor
publishes no figure, or nobody has looked yet. Six ASR 9000 chassis had the
first case written down and unreachable, in a provenance key whose own words
are the distinction this file exists for:

    "Cisco publishes NO chassis-level power draw for any ASR 9000 ... This is
    the vendor being silent, not this model being thin."

It rides on `gaps`, which already carried `vendor-silent` on 190 entries before
any of this, rather than on a new field. A gap claims a fact by scoping itself
`fact:<name>`.
"""
import json
import pathlib
import sys

import yaml

import libdata

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import comparable as C
from portrayal import lint

LIB = ROOT / "library"


def dev(gaps=None, attrs=None):
    return {"kind": "device", "name": "d", "chassis": {}, "groups": {},
            "attrs": attrs or {}, "gaps": gaps or []}


def silent_gap(*facts, what="x", reason="vendor-silent"):
    return {"what": what, "reason": reason,
            "scope": [f"fact:{f}" for f in facts],
            "note": "the guide says use the calculator", "wanted": "a figure"}


# ---- the three states are distinguishable -----------------------------------

def test_a_stated_fact_has_readings():
    r = C.resolve(dev(attrs={"power": {"power-max-w": 280}}))
    assert r["peak-power-w"]["readings"] and "absent" not in r["peak-power-w"]


def test_a_declared_silence_is_present_and_empty():
    r = C.resolve(dev(gaps=[silent_gap("peak-power-w")]))
    assert r["peak-power-w"]["readings"] == []
    assert r["peak-power-w"]["absent"]["reason"] == "vendor-silent"
    assert r["peak-power-w"]["absent"]["note"]


def test_an_unlooked_fact_is_omitted_entirely():
    """The distinction the whole change is for: this must not look like the
    one above."""
    assert "peak-power-w" not in C.resolve(dev())


def test_only_vendor_silent_gaps_count():
    """`needs-drawing` and `sources-disagree` are not the vendor being silent -
    they are our work outstanding, and one of them is not an absence at all."""
    for reason in ("needs-drawing", "sources-disagree", "needs-photo"):
        r = C.resolve(dev(gaps=[silent_gap("peak-power-w", reason=reason)]))
        assert "peak-power-w" not in r, reason


def test_a_gap_scope_without_the_prefix_is_not_a_fact_claim():
    """`scope` already holds group names, view names and component refs. The
    prefix is what keeps those from accidentally claiming a fact."""
    g = silent_gap()
    g["scope"] = ["psus", "front", "cisco/a9k-pwr-3kw-ac@1"]
    assert C.declared_silence(dev(gaps=[g])) == {}


def test_a_declared_silence_never_overwrites_a_reading():
    r = C.resolve(dev(attrs={"power": {"power-max-w": 280}},
                      gaps=[silent_gap("peak-power-w")]))
    assert r["peak-power-w"]["readings"][0]["value"] == 280.0
    assert "absent" not in r["peak-power-w"]


# ---- L70 ---------------------------------------------------------------------

def fire(doc):
    out = []
    re_, rw = lint.err, lint.warn
    lint.err = lambda p, r, m: out.append(("ERR", r, m))
    lint.warn = lambda p, r, m: out.append(("WARN", r, m))
    try:
        lint.lint_device_declared_silence("t.yaml", doc)
    finally:
        lint.err, lint.warn = re_, rw
    return out


def test_a_misspelled_fact_name_is_an_error():
    """The worst outcome, because it is silent: the gap looks discharged in the
    file and the comparison still shows a bare blank, so the work does not
    land."""
    out = fire(dev(gaps=[silent_gap("peak-power")]))
    assert [(k, r) for k, r, _ in out] == [("ERR", "L70")]


def test_stating_a_fact_and_declaring_it_silent_is_an_error():
    """Worse than either state alone. A reader shown a number has no way to
    know a retraction was filed against it, and nothing here can tell which of
    the two is wrong."""
    out = fire(dev(attrs={"power": {"power-max-w": 280}},
                   gaps=[silent_gap("peak-power-w")]))
    assert [(k, r) for k, r, _ in out] == [("ERR", "L70")]
    assert "280" in out[0][2]


def test_a_well_formed_silence_is_quiet():
    assert not fire(dev(gaps=[silent_gap("peak-power-w")]))


# ---- the library -------------------------------------------------------------

def devices():
    """Over the once-parsed library - see libdata."""
    return libdata.devices()


def test_the_asr_chassis_declare_their_power_silence():
    """Six chassis, one vendor statement: Cisco publishes no chassis-level draw
    for the family and points at the Power Calculator instead."""
    got = sorted(slug for slug, d in devices()
                 if "peak-power-w" in C.declared_silence(d))
    assert len(got) == 6 and all(s.startswith("cisco/asr-99") or s == "cisco/asr-9006"
                                 for s in got), got


def test_the_silence_is_published_next_to_the_coverage():
    p = LIB / "dist" / "comparable-facts.json"
    if not p.exists():
        import pytest
        pytest.skip("library/dist not built")
    doc = json.loads(p.read_text())
    assert doc["declared-silent"]["peak-power-w"] == 6
    assert doc["declared-silent"]["typical-power-w"] == 6


def test_the_silence_and_the_provenance_agree():
    """The provenance key is the citation and stays; the gap is what a consumer
    reads. If one is ever removed without the other, the pair disagree."""
    for slug, d in devices():
        has_prov = bool((d.get("provenance") or {}).get("no-chassis-power-figure"))
        has_gap = "peak-power-w" in C.declared_silence(d)
        assert has_prov == has_gap, slug

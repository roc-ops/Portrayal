"""L65: a DC power part that holds nothing says what it can pass.

The rule exists because two parts wore the same claim for opposite reasons. A
power TRAY carries what the supplies seated in it produce, so `power-absent:
not-applicable` is right for it. A power ENTRY module holds nothing, and on a DC
chassis it is the only path power takes into the box - so the same words on it
mean the input capacity is stated nowhere at all.

Both had it, because the argument was written for the tray and inherited by the
PEM. Nothing caught it until somebody opened a chassis in another tool and asked
where the wattage was.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint


def run(doc):
    out = []
    real = lint.warn
    lint.warn = lambda p, r, m: out.append((r, m))
    try:
        lint.lint_component_dc_capacity("t.yaml", doc)
    finally:
        lint.warn = real
    return out


def part(**attrs):
    return {"kind": "module", "name": "t", "class": "power", "attrs": attrs}


def test_a_dc_entry_module_holding_nothing_must_state_what_it_passes():
    hits = run(part(role="dc-power-entry", **{"power-absent": "not-applicable"}))
    assert hits and hits[0][0] == "L65", hits


def test_a_tray_that_holds_supplies_may_defer_to_them():
    """The Cisco a9k trays: four supplies seat in them and each states its own
    output, so watts really are the wrong unit for the tray."""
    hits = run(part(role="dc-power-tray", **{"power-absent": "not-applicable",
                                             "module-bays": 4}))
    assert hits == [], hits


def test_a_stated_ceiling_satisfies_it():
    """A part that neither converts nor regulates can still bound what it passes,
    which is a real answer and the one both Casa PEMs now give."""
    hits = run(part(role="dc-power-entry", **{"power-output-w": 5760,
                                              "power-output-scope": "pass-through-ceiling"}))
    assert hits == [], hits


def test_not_published_is_an_answer_and_is_left_alone():
    """It says the figure was looked for and the vendor does not give it, and L52
    already makes it name the documents. The Edgecore AGR DC supply lists four."""
    hits = run(part(role="dc-psu", **{"power-absent": "not-published"}))
    assert hits == [], hits


def test_an_ac_part_is_not_asked():
    hits = run(part(role="ac-psu", input="ac", **{"power-absent": "not-applicable"}))
    assert hits == [], hits


def test_dc_is_recognised_from_the_input_voltage_too():
    """`role` is free text; the Casa PEMs say what they are in `input-voltage`."""
    hits = run(part(**{"input-voltage": "-42 to -60 VDC (-48 VDC nominal)",
                       "power-absent": "not-applicable"}))
    assert hits and hits[0][0] == "L65", hits


# ---- the library itself ------------------------------------------------------

def test_both_casa_pems_now_state_a_ceiling():
    """The devices that started this.

    THE FIGURE IS NOT THE BREAKER. The first pass took 4 x 30 A x 48 V = 5760 W
    from the PEM breaker ratings, and 30 A is what the branch is PROTECTED at,
    not what it carries - Casa publishes 3900 W for the shelf. Nominal 20 A per
    branch gives 4 x 20 A x 48 V = 3840 W, within 2% of their figure, and the
    C40G PEM 2 x 20 A x 48 V = 1920 W on the same basis.
    """
    import glob
    want = {"pem": 3840, "c40g-pem": 1920}
    for name, watts in want.items():
        p = sorted(glob.glob(str(ROOT / f"library/components/casa/{name}/v*/contract.yaml")))[-1]
        d = yaml.safe_load(open(p))
        a = d.get("attrs") or {}
        assert a.get("power-output-w") == watts, f"{name}: {a.get('power-output-w')}"
        assert a.get("power-output-scope") == "pass-through-ceiling", name
        assert "power-absent" not in a, f"{name} still claims an absence it does not have"
        # and the arithmetic is written down, because a derived figure that does
        # not show its working is indistinguishable from one somebody guessed
        prov = str((d.get("provenance") or {}).get("power") or "")
        assert "x 48 V" in prov and str(watts) in prov, f"{name}: arithmetic not shown"


def test_the_library_is_clean_under_this_rule():
    import glob
    bad = []
    for p in glob.glob(str(ROOT / "library/components/*/*/v*/contract.yaml")):
        d = yaml.safe_load(open(p)) or {}
        if run(d):
            bad.append(p.split("components/")[1])
    assert not bad, bad

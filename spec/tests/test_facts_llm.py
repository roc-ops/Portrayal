"""The verification layer, which is the only part of facts_llm.py worth trusting.

A language model reading a datasheet is useful exactly in proportion to how
mechanically its answers can be checked. These tests hold the two checks that do
that work, and they never call the endpoint - a test that needs a GPU passes or
fails depending on whose machine it runs on, which is not a test.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import facts_llm as F

DOC = [
    "## SPECS",                       # 1
    "",                               # 2
    "Power Consumption",              # 3
    "",                               # 4
    "1300 Watts maximum",             # 5
    "",                               # 6
    "2RU, 436 x 762 x 87. 7 mm",      # 7
    "",                               # 8
    "| 9716-32D-O-AC-F-US | FP5ZZ8632400A | DualACPSUs |",   # 9
]


def test_a_value_on_the_line_it_cites_verifies():
    ok, why = F.verify({"value": "1300 Watts maximum", "line": 5}, DOC)
    assert ok and why == "exact line"


def test_a_value_the_document_does_not_contain_is_rejected():
    """The failure this exists to catch. A model that returns a plausible number
    with a line that does not hold it is indistinguishable from one that read it,
    until the line is resolved."""
    ok, why = F.verify({"value": "1500 Watts maximum", "line": 5}, DOC)
    assert not ok and "not found" in why


def test_a_missing_or_impossible_line_is_rejected():
    """Seen in the first real run: the model returned the right wattage with a
    null line. Right answer, unusable - a fact with no citation cannot be checked
    by the next reader either."""
    assert not F.verify({"value": "1300", "line": None}, DOC)[0]
    assert not F.verify({"value": "1300", "line": 9999}, DOC)[0]


def test_a_value_wrapped_across_lines_still_verifies():
    """A value may start on the line cited and finish on the next. The window is
    deliberately two lines - wider than that is not verification, it is looking
    until you find something."""
    doc = ["Dimensions", "436 x 762 x", "87.7 mm"]
    ok, _ = F.verify({"value": "436 x 762 x 87.7 mm", "line": 2}, doc)
    assert ok


def test_odd_converter_spacing_does_not_break_verification():
    """The converter writes `87. 7 mm`. Normalising to alphanumerics is what lets
    a correctly-read value match the mangled source it came from."""
    ok, _ = F.verify({"value": "436 x 762 x 87.7 mm", "line": 7}, DOC)
    assert ok


def test_a_citation_check_does_not_catch_a_wrong_LABEL():
    """THE GAP THE SHAPE CHECK EXISTS FOR, held here so nobody removes it.

    The first real run returned `ordering-part: '4. 产品标签'` - a numbered callout
    meaning 'product label' - and it verified perfectly, because that string IS
    on that line. Checking the citation catches invention and cannot catch
    misclassification, and in the output the two look identical.
    """
    fact = {"field": "ordering-part", "value": "4. 产品标签", "line": 1}
    assert F.verify(fact, ["4. 产品标签"])[0], "the citation is genuinely good"
    assert not F.shaped(fact)[0], "and the shape check is what rejects it"


def test_shape_accepts_the_real_thing_for_each_field():
    for field, value in (("power-consumption", "1300 Watts maximum"),
                         ("dimensions", "436 x 762 x 87. 7 mm"),
                         ("weight", "19 . 86 kg"),
                         ("ordering-part", "9716-32D-O-AC-F-US"),
                         ("operating-temp", "0° C to 45° C"),
                         ("asic", "Broadcom BCM56980")):
        assert F.shaped({"field": field, "value": value})[0], (field, value)


def test_shape_rejects_a_heading_wearing_a_field_name():
    for field, value in (("power-consumption", "Power Consumption"),
                         ("weight", "Weight"),
                         ("dimensions", "Chassis (W x D x H)")):
        assert not F.shaped({"field": field, "value": value})[0], (field, value)


def test_an_unknown_field_is_not_silently_gated():
    """A field with no declared shape must pass, not fail. Otherwise adding a
    field to the prompt and forgetting the shape table would delete every fact of
    that kind without saying so."""
    ok, why = F.shaped({"field": "compliance", "value": "EN 55032 Class A"})
    assert ok and "no shape" in why


def test_windows_overlap_so_a_split_fact_is_not_lost():
    """A label at the end of one window and its value at the start of the next is
    exactly the shape this tool exists to catch, so the windows must overlap or
    the chunker reintroduces the bug."""
    lines = [f"line {i}" for i in range(300)]
    starts = [s for s, _ in F.chunks(lines, 120, 15)]
    assert starts == [0, 105, 210]
    bodies = [b for _, b in F.chunks(lines, 120, 15)]
    assert "106: line 105" in bodies[0] and "106: line 105" in bodies[1]


def test_parse_tolerates_a_fenced_reply():
    txt = "```yaml\nfacts:\n  - field: weight\n    value: 19 kg\n    line: 3\n```"
    got = F.parse(txt)
    assert got and got[0]["value"] == "19 kg"
    assert F.parse("I could not find anything useful.") == []

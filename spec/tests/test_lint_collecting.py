"""Findings from the rules called inside a block, and nothing else.

The dance this replaces was written out across the suite:

    saved_e, saved_w = lint.ERRORS[:], lint.WARNINGS[:]
    lint.ERRORS.clear(); lint.WARNINGS.clear()
    try:
        ...
    finally:
        lint.ERRORS[:], lint.WARNINGS[:] = saved_e, saved_w

**20 of the 28 files that cleared did not restore.** That works right up until a
rule under test leaves a finding behind and an unrelated test three files later
reads it - a failure that names the wrong test, which is the worst kind to debug.

And two tests were *depending* on the leak: `test_relief_confidence` asserted
`msgs[0] in lint.ERRORS` **after** its helper returned, which only ever passed
because the helper cleared the globals and never put them back. They ask the
helper which stream a message came from now.

NOT A CONTEXT OBJECT THREADED THROUGH THE RULES, and #302 records why: `warn()`
and `err()` are called 208 times across ~95 rule functions, and the review's
justification - that the globals "block testing rules in isolation" - is not
true: 32 files already test rules in isolation, and `pytest -n 4` passes.
"""
import pytest

from portrayal import lint


def test_it_collects_what_the_block_raises():
    with lint.collecting() as got:
        lint.warn("a.yaml", "L61", "a warning")
        lint.err("b.yaml", "L1", "an error")
    assert got.warnings == ["a.yaml: [L61] a warning"]
    assert got.errors == ["b.yaml: [L1] an error"]


def test_it_restores_what_was_there_before():
    """THE HALF THE 20 FILES SKIPPED. A rule under test must not leave a finding
    where the next test will read it."""
    lint.WARNINGS.append("outer: [L0] from an outer run")
    lint.ERRORS.append("outer: [L0] an outer error")
    try:
        with lint.collecting():
            lint.warn("inner.yaml", "L61", "inside")
            lint.err("inner.yaml", "L1", "inside")
        assert lint.WARNINGS == ["outer: [L0] from an outer run"]
        assert lint.ERRORS == ["outer: [L0] an outer error"]
    finally:
        lint.WARNINGS.clear()
        lint.ERRORS.clear()


def test_the_findings_survive_the_block():
    """The lists are handed out, so they are copied on the way out - a caller
    reading `got.warnings` after the block would otherwise be reading whatever
    the OUTER run had collected."""
    with lint.collecting() as got:
        lint.warn("a.yaml", "L61", "one")
    lint.warn("after.yaml", "L2", "afterwards")
    try:
        assert got.warnings == ["a.yaml: [L61] one"]
    finally:
        lint.WARNINGS.clear()


def test_it_restores_even_when_the_rule_raises():
    with pytest.raises(ValueError):
        with lint.collecting():
            lint.warn("a.yaml", "L61", "before the raise")
            raise ValueError("a rule blew up")
    assert lint.WARNINGS == []


def test_it_nests():
    with lint.collecting() as outer:
        lint.warn("o.yaml", "L1", "outer")
        with lint.collecting() as inner:
            lint.warn("i.yaml", "L2", "inner")
        assert inner.warnings == ["i.yaml: [L2] inner"]
        assert lint.WARNINGS == ["o.yaml: [L1] outer"], "the outer run survives"
    assert outer.warnings == ["o.yaml: [L1] outer"]
    assert lint.WARNINGS == []


def test_the_suite_no_longer_hand_rolls_the_dance():
    """Asserted over the tree, because the next copy will not be on a list.

    A file may still clear one list where the shape does not fit a helper - what
    must not come back is the save-and-restore written out by hand.
    """
    import ast
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    offenders = []
    for f in sorted((root / "spec/tests").glob("test_*.py")):
        if f.name == "test_lint_collecting.py":
            continue
        names = {n.id for n in ast.walk(ast.parse(f.read_text()))
                 if isinstance(n, ast.Name)}
        if {"saved_e", "saved_w"} & names:
            offenders.append(f.name)
    assert not offenders, f"these still save and restore by hand: {offenders}"

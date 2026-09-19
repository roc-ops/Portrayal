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
import ast
import pathlib

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


# List methods that write. `clear` is the one that bit us; the rest are here so
# that the next spelling of "reach into the global and change it" is caught by
# the same gate rather than by a test three files away.
MUTATORS = {"clear", "append", "extend", "insert", "pop", "remove", "sort",
            "reverse"}


def writes_to_the_globals(src):
    """Every place `src` mutates `lint.ERRORS`/`lint.WARNINGS` in place.

    READS ARE FINE and several files make them: inside a `collecting()` block
    `lint.ERRORS` *is* the live list, which is the whole mechanism, and
    `test_module_power.py` reads it there deliberately. What must not appear is
    a write, because a write is the dance no matter how it is spelled.
    """
    def is_global(n):
        return isinstance(n, ast.Attribute) and n.attr in ("ERRORS", "WARNINGS")

    def assigned(t):
        """The things one assignment target actually writes to.

        UNPACKED, because the canonical dance puts BOTH lists in one statement:

            lint.ERRORS[:], lint.WARNINGS[:] = saved_e, saved_w

        which is a Tuple target, and a checker that only looks at the target
        itself sees a Tuple, finds no attribute on it, and passes the very line
        this file's own docstring quotes as the thing to stop.
        """
        if isinstance(t, (ast.Tuple, ast.List)):
            for el in t.elts:
                yield from assigned(el)
        elif isinstance(t, ast.Starred):
            yield from assigned(t.value)
        else:
            yield t.value if isinstance(t, ast.Subscript) else t

    hits = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr in MUTATORS and is_global(n.func.value):
            hits.append((n.lineno, f"{n.func.value.attr}.{n.func.attr}()"))
        targets = (n.targets if isinstance(n, ast.Assign)
                   else [n.target] if isinstance(n, (ast.AugAssign, ast.AnnAssign))
                   else [])
        for t in targets:
            for base in assigned(t):
                if is_global(base):
                    hits.append((n.lineno, f"assignment to {base.attr}"))
    return hits


# Every spelling of a write, because the checker above is the only thing standing
# between the suite and the dance, and it is itself just code. The sweep it drives
# runs over files that are all clean today, so a checker that quietly stopped
# recognising a form would keep reporting a green tree - which is the shape of
# failure this whole file exists to object to.
WRITES = [
    "lint.ERRORS.clear()",
    "lint.WARNINGS.clear()",
    "lint.ERRORS.append('x')",
    "lint.ERRORS.extend(['x'])",
    "lint.ERRORS = []",
    "lint.ERRORS[:] = saved",
    "lint.ERRORS += ['x']",
    "L.ERRORS.clear()",                                  # aliased import
    "lint.ERRORS[:], lint.WARNINGS[:] = saved_e, saved_w",   # THE canonical dance
    "lint.ERRORS, lint.WARNINGS = [], []",
    "a, (lint.ERRORS[:], b) = 1, (saved, 2)",            # nested unpacking
]

READS = [
    "x = [e for e in lint.ERRORS if '[L83]' in e]",
    "assert lint.WARNINGS == []",
    "ALLOWED_WARNINGS = set()",                          # a Name, not the global
    "with lint.collecting() as found:\n    pass",
]


@pytest.mark.parametrize("src", WRITES)
def test_the_checker_sees_every_spelling_of_a_write(src):
    assert writes_to_the_globals(src), f"not recognised as a write: {src}"


@pytest.mark.parametrize("src", READS)
def test_the_checker_leaves_reads_alone(src):
    """A read of `lint.ERRORS` inside a `collecting()` block is the mechanism
    working, not an offence. Flagging one would push files back to asserting on
    the helper's copy where the live list is what they mean."""
    assert writes_to_the_globals(src) == [], f"false positive on: {src}"


def test_the_canonical_dance_is_the_one_it_must_never_miss():
    """Pinned on its own because it is the form BOTH docstrings print - this
    file's, at the top, and `lint.collecting()`'s - so it is the copy a reader
    is most likely to paste back in. It is a Tuple target, and the first version
    of this checker looked at the target itself, saw a Tuple, found no attribute
    on it and passed.
    """
    src = ("saved_e, saved_w = lint.ERRORS[:], lint.WARNINGS[:]\n"
           "lint.ERRORS.clear(); lint.WARNINGS.clear()\n"
           "lint.ERRORS[:], lint.WARNINGS[:] = saved_e, saved_w\n")
    what = [w for _, w in writes_to_the_globals(src)]
    assert "ERRORS.clear()" in what and "WARNINGS.clear()" in what
    assert what.count("assignment to ERRORS") == 1, what
    assert what.count("assignment to WARNINGS") == 1, what


def test_the_suite_no_longer_hand_rolls_the_dance():
    """Asserted over the tree, because the next copy will not be on a list.

    WIDENED, because the first version of this gate let the thing it was written
    to stop walk straight past it. It looked for the names `saved_e`/`saved_w`,
    so `test_port_optics.py` - which spelled its save `saved` - was never seen.
    And it said in as many words that a file "may still clear one list where the
    shape does not fit a helper", which is the opposite of true: the bare clear
    is not the mild version of the dance, it is the worse one, because it leaks
    by construction instead of only when somebody forgets the restore.

    What that cost: `test_faces.py` cleared `ERRORS`, left an L83 finding in it,
    and `test_it_restores_what_was_there_before` above failed on that finding
    whenever xdist happened to schedule the two files into one worker. Green on
    one machine, red on the next, naming a test that had done nothing wrong -
    precisely the failure the module docstring opens by describing.

    So the rule is now the simple one: outside this file, nothing writes to the
    globals. Reads are left alone.

    THE TOOLS ARE WALKED TOO, and capability.py is why: the suite went clean
    first, which left the last copy in the tree sitting in `_rule_warnings` -
    the function somebody greps when they want to run a rule and read what it
    found. A gate that only watches the tests leaves the exemplar unguarded.

    `lint.py` needs no exception, which is worth saying out loud rather than
    leaving to be rediscovered: it owns the globals and touches them by bare
    name, and `writes_to_the_globals` only sees attribute access. So this gate
    says nothing about lint.py's own internals, which is right - `collecting()`
    IS the save-and-restore, and something has to write it once.

    `spec/tools/sweeps` is deliberately not walked. sweep_ids.py:95 clears
    per-iteration and never restores, which the checker does flag and which is
    nonetheless right for what it is: a one-shot CLI with no next test to leak
    into. A gate that had to carve it out by name would be arguing about a file
    nobody imports.
    """
    root = pathlib.Path(__file__).resolve().parents[2]
    offenders = []
    for rel, pattern in (("spec/tests", "test_*.py"),
                         ("spec/tools/portrayal", "*.py")):
        files = sorted((root / rel).glob(pattern))
        # A GLOB THAT MATCHES NOTHING RAISES NOTHING - it yields an empty
        # iterator, the loop below never runs, and this gate reports a clean
        # tree it never read. That is one rename of spec/tools/portrayal away,
        # and it is the same green-on-a-tree-that-was-not-checked failure the
        # WRITES list above exists to keep the checker itself out of.
        assert files, f"{rel}/{pattern} matched no files - has the tree moved?"
        for f in files:
            if f.name == "test_lint_collecting.py":
                continue
            for line, what in writes_to_the_globals(f.read_text()):
                offenders.append(f"{rel}/{f.name}:{line} {what}")
    assert not offenders, (
        "these reach into lint.ERRORS/lint.WARNINGS instead of using "
        "lint.collecting():\n  " + "\n  ".join(offenders))

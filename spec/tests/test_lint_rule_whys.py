"""Every lint rule says why it exists, and saying so changes nothing else.

The rule table in lint.py is published three ways: `--list-rules` on the
terminal, docs/lint-rules.md, and lint-rules.json in the dist, which the
site's rule page reads. Four guards hold it.

EVERY RULE HAS A WHY: what the rule prevents and for whom, written to the same
standard as the schema descriptions - no repo paths, sections, steps, issue or
pull request numbers. The citation check is the schema descriptions' own
pattern, imported, so the two standards cannot drift apart.

THE PAGE AND THE DATA ARE ONE TABLE. Both are generated from RULES; this checks
that they list the same codes with the same whys, and that the dist copy is
what the generator writes today.

SEVERITY IS READ OFF THE CODE. Each entry states whether its findings warn or
fail; this reads the err()/warn() calls that raise the code and fails when the
two disagree, so the published severity cannot outlive a change to the rule.

ONLY THE WHY MOVES WITHOUT SAYING SO. Each entry without its why - scope, rule,
fix and severity - is recorded as a short digest per code in
`fixtures/lint-rule-shape.json`. Rewording a why passes; any other change to an
entry fails until it is re-recorded, which makes it a deliberate line in the
diff, one code per line:

    python3 spec/tests/test_lint_rule_whys.py --update

A committed record rather than `git show origin/main:`, for the reason the
schema shape guard gives: a shallow checkout has no `origin/main`, and once a
change merges the comparison is main against itself.
"""
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "spec" / "tools" / "portrayal"
SHAPE = Path(__file__).resolve().parent / "fixtures/lint-rule-shape.json"

from portrayal import lint
from test_schema_descriptions import CITES

# About 170 rules on the day this was written: a walk that saw fewer has not
# read the table, and its clean result would mean nothing.
FLOOR = 165


def _digest(entry):
    scope, rule, fix, _why, severity = entry
    text = json.dumps([scope, rule, fix, severity], ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _shape():
    return {c: _digest(lint.RULES[c]) for c in lint._rule_order(lint.RULES)}


# ---- every rule has a why ---------------------------------------------------

def test_every_rule_has_a_why():
    checked, empty = 0, []
    for code, entry in lint.RULES.items():
        assert len(entry) == 5, code
        why = entry[3]
        checked += 1
        if not isinstance(why, str) or not why.strip():
            empty.append(code)
    assert checked == len(lint.RULES) >= FLOOR, f"checked {checked} rules"
    assert not empty, f"rules with no why: {empty}"


def test_no_why_cites_the_repository():
    seen, bad = 0, []
    for code, entry in lint.RULES.items():
        seen += 1
        for m in CITES.finditer(entry[3]):
            bad.append(f"{code}: {m.group(0)!r} in {entry[3]!r}")
    assert seen >= FLOOR, f"read only {seen} whys"
    assert not bad, "\n".join(bad)


def test_a_why_fits_in_a_table_cell():
    # a `|` ends a Markdown cell and a newline ends the row
    bad = [c for c, e in lint.RULES.items() if "|" in e[3] or "\n" in e[3]]
    assert not bad, bad


# ---- one table, two outputs -------------------------------------------------

def _page_rows():
    page = (ROOT / "docs" / "lint-rules.md").read_text()
    rows = {}
    for line in page.splitlines():
        m = re.match(r"^\| (L\d+) \| ", line)
        if m:
            rows[m.group(1)] = line
    return rows


def test_the_page_and_the_json_list_the_same_codes_and_whys():
    data = lint.rules_json()
    codes = [r["code"] for r in data["rules"]] + [r["code"] for r in data["retired"]]
    rows = _page_rows()
    assert len(codes) >= FLOOR
    assert sorted(codes, key=lambda c: int(c[1:])) == sorted(rows, key=lambda c: int(c[1:]))
    for r in data["rules"]:
        assert f"| {r['why']} |" in rows[r["code"]], r["code"]
        assert rows[r["code"]].endswith(f"| {r['severity']} |"), r["code"]


def test_the_json_carries_every_field():
    data = lint.rules_json()
    assert data["format"] == lint.RULES_FORMAT == 1
    assert len(data["rules"]) == len(lint.RULES) >= FLOOR
    for r in data["rules"]:
        assert set(r) == {"code", "scope", "rule", "why", "fix", "severity",
                          "fails", "warns", "fails-at-verified"}, r["code"]
        assert r["severity"] in data["severities"], r["code"]
        assert r["fails"] or r["warns"], r["code"]


def test_list_rules_json_is_the_table():
    import subprocess
    out = subprocess.run([sys.executable, str(TOOLS / "lint.py"), "--list-rules", "--json"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == lint.rules_json()


def test_the_dist_copy_is_current():
    p = ROOT / "library" / "dist" / "lint-rules.json"
    if not (ROOT / "library" / "dist").is_dir():
        pytest.skip("library/dist not built - run ./build.sh")
    assert p.is_file(), "the build did not write lint-rules.json"
    assert json.loads(p.read_text()) == lint.rules_json(), \
        "library/dist/lint-rules.json is stale; run ./build.sh"


# ---- severity is read off the code ------------------------------------------

# What each callee that receives a literal code does with it. `e` and `w` are
# the group checker's parameters: a device passes (err, warn), a component
# (warn, warn), so `e` can be either. `say` and `loud` are the local names for
# the verified gate, and the test below holds them to that.
_CALLEES = {"err": {"E"}, "warn": {"W"}, "check_segment": {"E"}, "say": {"V"}, "loud": {"V"},
            "e": {"E", "W"}, "w": {"W"}}
_TOKEN = {frozenset("E"): lint.ERROR, frozenset("W"): lint.WARNING,
          frozenset("V"): lint.AT_VERIFIED, frozenset("VW"): lint.AT_VERIFIED,
          frozenset("EW"): lint.MIXED, frozenset("EV"): lint.MIXED_AT_VERIFIED,
          frozenset("EVW"): lint.MIXED_AT_VERIFIED}
_TABLES = ("RULES", "RESERVED", "RETIRED")


def _is_verified_gate(node):
    """`err if <...> == "verified" else warn`."""
    return (isinstance(node, ast.IfExp) and isinstance(node.body, ast.Name) and node.body.id == "err"
            and isinstance(node.orelse, ast.Name) and node.orelse.id == "warn"
            and "'verified'" in ast.unparse(node.test))


def severity_facets(lint_src, labs_src):
    """{code: set of E (fails), W (warns), V (fails at verified)} from the source."""
    facets, unknown = {}, []

    class Walk(ast.NodeVisitor):
        def visit_Assign(self, n):
            if any(isinstance(t, ast.Name) and t.id in _TABLES for t in n.targets):
                return
            self.generic_visit(n)

        def visit_Call(self, n):
            f = n.func
            kind = {"V"} if _is_verified_gate(f) else (
                _CALLEES.get(f.id) if isinstance(f, ast.Name) else None)
            for a in n.args[:3]:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) \
                        and re.fullmatch(r"L\d+", a.value):
                    if kind is None:
                        unknown.append(f"{a.value}: {ast.unparse(f)}")
                    else:
                        facets.setdefault(a.value, set()).update(kind)
            self.generic_visit(n)

    Walk().visit(ast.parse(lint_src))
    for n in ast.walk(ast.parse(labs_src)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id in ("error", "warning") and n.args \
                and isinstance(n.args[0], ast.Constant):
            facets.setdefault(n.args[0].value, set()).add("E" if n.func.id == "error" else "W")
    return facets, unknown


def _sources():
    return (TOOLS / "lint.py").read_text(), (TOOLS / "labs.py").read_text()


def test_say_and_loud_are_the_verified_gate():
    tree = ast.parse(_sources()[0])
    names = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id in ("say", "loud") for t in n.targets)]
    assert names, "no say/loud assignment found - update _CALLEES"
    for n in names:
        assert _is_verified_gate(n.value), ast.unparse(n)


def test_each_severity_is_what_the_code_does():
    facets, unknown = severity_facets(*_sources())
    assert not unknown, ("a code is raised through a callee this test does not know; "
                         f"teach _CALLEES what it does: {unknown}")
    # L53's findings come from devicelock and are raised by lint.py, so it is
    # in the walk like any other.
    checked, wrong = 0, []
    for code, entry in lint.RULES.items():
        got = _TOKEN.get(frozenset(facets.get(code, ())))
        checked += 1
        if entry[4] != got:
            wrong.append(f"{code}: table says {entry[4]!r}, the code raises {got!r}")
    assert checked >= FLOOR
    assert not wrong, "\n".join(wrong)


def test_the_severity_read_tells_a_warning_from_an_error():
    lint_src, labs_src = _sources()
    before, _ = severity_facets(lint_src, labs_src)
    assert before["L18"] == {"W"} and before["L5"] == {"E"} and before["L53"] == {"V"}
    after, _ = severity_facets(lint_src.replace('warn(path, "L18"', 'err(path, "L18"'), labs_src)
    assert after["L18"] == {"E"}


# ---- only the why moves -----------------------------------------------------

def test_only_whys_differ_from_the_recorded_shape():
    want = json.loads(SHAPE.read_text())
    now = _shape()
    moved = sorted(set(want) ^ set(now), key=lambda c: int(c[1:]))
    changed = [c for c in now if c in want and now[c] != want[c]]
    assert len(want) >= FLOOR
    assert not moved and not changed, (
        f"codes added or removed: {moved}; entries changed other than their why: {changed}. "
        "If that is intended, re-record with `python3 spec/tests/test_lint_rule_whys.py "
        "--update` and say in the pull request what changed.")


def test_the_shape_moves_when_anything_but_the_why_moves():
    entry = lint.RULES["L53"]
    before = _digest(entry)
    assert _digest(entry[:3] + ("reworded",) + entry[4:]) == before
    for i in (0, 1, 2, 4):
        moved = list(entry)
        moved[i] = moved[i] + " changed"
        assert _digest(tuple(moved)) != before, i


@pytest.mark.parametrize("text", ["see docs/lint-rules.md", "(#952)", "section 4", "PR 951"])
def test_a_cited_why_is_caught(text):
    assert CITES.search(f"A drawing would go stale, {text}.")


if __name__ == "__main__":
    if sys.argv[1:] != ["--update"]:
        sys.exit("usage: test_lint_rule_whys.py --update")
    SHAPE.write_text(json.dumps(_shape(), indent=1) + "\n")
    print(f"recorded {len(lint.RULES)} rule shapes in {SHAPE.relative_to(ROOT)}")

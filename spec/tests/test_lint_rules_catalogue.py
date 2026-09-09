"""The lint rule catalogue is one table in three places - RULES in lint.py,
`--list-rules` on the terminal, docs/lint-rules.md on the page - and this keeps
them from drifting apart.

A code the linter can raise but the table does not list is a finding a
contributor cannot look up. An entry the code no longer raises is a rule that
reads as live and is not. A page that differs from the generator is a page
somebody edited by hand.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "spec" / "tools" / "portrayal"
sys.path.insert(0, str(TOOLS))
import lint  # noqa: E402

SOURCE = (TOOLS / "lint.py").read_text()
# codes passed to err()/warn() as literals, and codes handed to helpers the same way
RAISED = set(re.findall(r'"(L\d+)"', SOURCE.split("RULES = {", 1)[1].split("def rules_text", 1)[1]))
MENTIONED = set(re.findall(r"\bL\d+\b", SOURCE))


def test_every_code_the_linter_raises_is_in_the_catalogue():
    missing = sorted(RAISED - set(lint.RULES), key=lambda c: int(c[1:]))
    assert not missing, f"raised in lint.py but not in RULES: {missing}"


def test_every_catalogue_entry_is_still_a_rule_the_source_knows():
    stale = sorted(set(lint.RULES) - MENTIONED, key=lambda c: int(c[1:]))
    assert not stale, f"in RULES but nowhere in lint.py: {stale}"


def test_catalogue_codes_are_contiguous_from_L0():
    codes = sorted(int(c[1:]) for c in lint.RULES)
    assert codes == list(range(codes[-1] + 1)), "a gap in the numbering means a rule was deleted without its entry, or vice versa"


def test_every_entry_has_scope_rule_and_fix():
    for code, entry in lint.RULES.items():
        assert len(entry) == 3 and all(isinstance(x, str) and x.strip() for x in entry), code


def test_docs_page_matches_the_generator():
    page = (ROOT / "docs" / "lint-rules.md").read_text()
    assert page == lint.rules_text(markdown=True), (
        "docs/lint-rules.md is stale; regenerate with "
        "`python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md`")


def test_list_rules_needs_no_library():
    r = subprocess.run([sys.executable, str(TOOLS / "lint.py"), "--list-rules"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("L0 ") and "L76 " in r.stdout

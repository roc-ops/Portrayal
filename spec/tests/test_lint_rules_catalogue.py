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
from portrayal import lint

SOURCE = (TOOLS / "lint.py").read_text()
# The RULES literal is the thing under test, so it is cut out of the source
# before the source is searched; otherwise an entry would vouch for itself.
_head, _rest = SOURCE.split("RULES = {", 1)
RULES_LITERAL, _tail = _rest.split("\n}\n", 1)
# The RETIRED table names codes too, and a retired code is one nothing raises.
_tail = re.sub(r"^RETIRED = \{\}\n|^RETIRED = \{\n.*?^\}\n", "", _tail, count=1, flags=re.M | re.S)
CODE = _head + _tail
# codes passed to err()/warn() as literals, and codes handed to helpers the same way
RAISED = set(re.findall(r'"(L\d+)"', CODE))
# every other way the code can name a rule: the header list, a docstring, a comment
MENTIONED = set(re.findall(r"\bL\d+\b", CODE))


def test_every_code_the_linter_raises_is_in_the_catalogue():
    missing = sorted(RAISED - set(lint.RULES) - set(lint.RESERVED), key=lambda c: int(c[1:]))
    assert not missing, f"raised in lint.py but not in RULES: {missing}"


def test_a_retired_code_is_raised_by_nothing():
    revived = sorted(RAISED & set(lint.RETIRED), key=lambda c: int(c[1:]))
    assert not revived, f"retired codes raised again - a new rule takes a new code: {revived}"


def test_every_catalogue_entry_is_still_a_rule_the_source_knows():
    stale = sorted(set(lint.RULES) - MENTIONED, key=lambda c: int(c[1:]))
    assert not stale, f"in RULES but nowhere in lint.py: {stale}"


def test_catalogue_literal_has_no_duplicate_keys():
    keys = re.findall(r'^\s+"(L\d+)":', RULES_LITERAL, re.M)
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, f"RULES declares these codes twice; Python keeps the last silently: {dupes}"
    assert len(keys) == len(lint.RULES)


def test_catalogue_codes_are_contiguous_from_L0():
    # a RESERVED code is a rule being written on another branch, and a RETIRED
    # one is a rule that is gone but whose code is still spent; neither is a gap
    codes = sorted(int(c[1:]) for c in set(lint.RULES) | set(lint.RESERVED) | set(lint.RETIRED))
    assert codes == list(range(codes[-1] + 1)), "a gap in the numbering means a rule was deleted without its entry, or vice versa"


def test_a_reserved_code_leaves_reserved_when_its_rule_lands():
    landed = sorted(set(lint.RULES) & set(lint.RESERVED))
    assert not landed, f"in RULES and still RESERVED - delete the reservation: {landed}"


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
    assert "fix:" in r.stdout, "the terminal listing must carry the remediation, not only the rule"


# EVERY CODE EVER ISSUED, WITH THE SCOPE OF THE RULE IT WAS ISSUED TO. A device
# manifest waives a rule by its code (`lint.waive`), and so does the baseline,
# so a code is an address held outside this file: renumbering one, or handing a
# deleted rule's code to a new rule, silently re-points every waiver that names
# it. That happened once, in pre-release - L117-L119 moved up to L118-L120 when
# two branches took the same numbers - and docs/format-stability.md promises it
# does not happen again. Scope is the pin because it is the part of a rule that
# does not get reworded: a rule's sentence is edited often, but a code that
# moves from a device rule to a component rule is a different rule.
#
# A NEW RULE appends its code here. A rule that WIDENS (a component rule that
# now also reads devices) updates its scope here in the same change. A rule that
# is DELETED keeps its line here and moves to lint.RETIRED; its code is never
# used again.
ISSUED = {
    "L0": "any yaml",
    "L1": "any yaml",
    "L2": "any id",
    "L3": "component",
    "L4": "component",
    "L5": "device",
    "L6": "device",
    "L7": "device",
    "L8": "device",
    "L9": "component",
    "L10": "component",
    "L11": "component",
    "L12": "device",
    "L13": "device",
    "L14": "device",
    "L15": "device",
    "L16": "device",
    "L17": "component, device",
    "L18": "device",
    "L19": "device",
    "L20": "component, device",
    "L21": "device",
    "L22": "component, device",
    "L23": "component, device",
    "L24": "device",
    "L25": "device",
    "L26": "component",
    "L27": "component",
    "L28": "component",
    "L29": "device",
    "L30": "device",
    "L31": "device",
    "L32": "any yaml",
    "L33": "device",
    "L34": "device",
    "L35": "component",
    "L36": "component",
    "L37": "component, device",
    "L38": "component",
    "L39": "device",
    "L40": "device",
    "L41": "device",
    "L42": "device",
    "L43": "device",
    "L44": "device",
    "L45": "device",
    "L46": "component",
    "L47": "component",
    "L48": "component",
    "L49": "device",
    "L50": "component",
    "L51": "component",
    "L52": "component",
    "L53": "device",
    "L54": "device",
    "L55": "library",
    "L56": "listing",
    "L57": "device",
    "L58": "component",
    "L59": "device",
    "L60": "device",
    "L61": "device",
    "L62": "device",
    "L63": "device",
    "L64": "device",
    "L65": "component",
    "L66": "device",
    "L67": "device",
    "L68": "library",
    "L69": "device",
    "L70": "device",
    "L71": "component",
    "L72": "device",
    "L73": "component",
    "L74": "component",
    "L75": "component",
    "L76": "device",
    "L77": "component",
    "L78": "component",
    "L79": "component",
    "L80": "component",
    "L81": "component",
    "L82": "component",
    "L83": "component",
    "L84": "component",
    "L85": "component",
    "L86": "component",
    "L87": "component",
    "L88": "component",
    "L89": "library",
    "L90": "device",
    "L91": "device",
    "L92": "component",
    "L93": "device",
    "L94": "device",
    "L95": "component",
    "L96": "component",
    "L97": "component",
    "L98": "component",
    "L99": "component",
    "L100": "component, device",
    "L101": "component",
    "L102": "component, device",
    "L103": "library",
    "L104": "device",
    "L105": "component, device",
    "L106": "component",
    "L107": "component, device",
    "L108": "component, device",
    "L109": "component",
    "L110": "component, device",
    "L111": "library",
    "L112": "component",
    "L113": "device",
    "L114": "component",
    "L115": "component, device",
    "L116": "component",
    "L117": "component",
    "L118": "device",
    "L119": "device",
    "L120": "device",
    "L121": "component",
    "L122": "component, device",
    "L123": "library",
    "L124": "library",
    "L125": "device",
    "L126": "device",
    "L127": "device",
    "L128": "device, listing",
    "L129": "component",
    "L130": "component",
    "L131": "component",
    "L132": "device",
    "L133": "device",
    "L134": "device",
    "L135": "device",
    "L136": "device",
    "L137": "device",
    "L138": "component, device",
    "L139": "lab",
    "L140": "lab",
    "L141": "lab",
    "L142": "lab",
    "L143": "lab",
}


def test_every_issued_code_is_live_or_retired():
    # a RESERVED code is issued to a rule landing on another branch, and is
    # counted as present until it does (lint.RESERVED)
    gone = sorted(set(ISSUED) - set(lint.RULES) - set(lint.RETIRED) - set(lint.RESERVED),
                  key=lambda c: int(c[1:]))
    assert not gone, (f"issued codes in neither RULES nor RETIRED: {gone}. A deleted rule's "
                      "code moves to lint.RETIRED with a sentence; it is never dropped or reused")


def test_no_code_is_both_live_and_retired():
    both = sorted(set(lint.RULES) & set(lint.RETIRED), key=lambda c: int(c[1:]))
    assert not both, f"in RULES and RETIRED - a retired code is never reassigned: {both}"


def test_every_live_or_retired_code_was_issued():
    unpinned = sorted((set(lint.RULES) | set(lint.RETIRED)) - set(ISSUED), key=lambda c: int(c[1:]))
    assert not unpinned, (f"codes not in ISSUED: {unpinned}. A new rule appends its code and "
                          "scope to ISSUED in this file")
    # A RESERVED code is issued too, to a rule on another branch: that branch
    # pins its scope here when it lands, so until then it is not a skip.
    newest = max(int(c[1:]) for c in ISSUED)
    assert sorted(int(c[1:]) for c in set(ISSUED) | set(lint.RESERVED)) == \
        list(range(newest + 1)), \
        "ISSUED skips a number; codes are issued in order and none is skipped"


def test_no_live_code_was_reassigned_to_a_different_rule():
    moved = {c: (ISSUED[c], lint.RULES[c][0]) for c in set(lint.RULES) & set(ISSUED)
             if lint.RULES[c][0] != ISSUED[c]}
    assert not moved, (f"a code's scope changed (issued, now): {moved}. If the rule widened, "
                       "update ISSUED; if it is a different rule, give it a new code and "
                       "retire this one")


def test_the_pin_is_not_vacuous():
    assert len(ISSUED) >= 125 and "L0" in ISSUED and "L124" in ISSUED

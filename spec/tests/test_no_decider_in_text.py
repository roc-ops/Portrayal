"""Committed prose names no decider (docs/review-standards.md, "Nothing private").

A rack is "the reference rack of #949", and a ruling is "decided <date>" (or
"decided in #<n>"); neither is "the owner's rack" or "owner decision". This
scans `docs/`, `kit/README.md` and `changelog.d/` for "the owner" used to name
whoever decided or supplied something.

What it catches (case-insensitive):

- any possessive "owner's" ("the owner's rack", "for the owner's approval");
- "owner decision" and "owner ruling";
- "the owner" followed by a verb of deciding or asking ("the owner ruled",
  "the owner wants", "the owner reported");
- "for the owner" ("proposed for the owner").

What it lets through, on purpose:

- "the owner of a rack" and "the owner of the bottom": whoever or whatever
  holds a thing. None of the patterns above matches it, and `ALLOWED` shows
  it as a case the test checks.
- the literal comment keyword `OWNER DECISION:` that the merge tooling
  matches (docs/merging.md, a changelog fragment about it). It is a protocol
  token, not prose naming a person, so it is removed before the scan.
- "owner" as a technical term (an element's owner path, `ownerDocument`):
  none of the patterns match it.

docs/merging.md also says "the owner merges" and "the owner is the only one
who does", describing the merge role of the repository. That names a role in a
process and no decision, so it is not matched; reword it with the process, not
here.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

PROTOCOL_TOKEN = re.compile(r"OWNER DECISION:")

DECIDER = re.compile(
    r"\bowner's\b"
    r"|\bowner (?:decision|ruling)\b"
    r"|\bthe owner (?:ruled|decided|kept|chose|wants|prefers|reported|approved|said|asked|set|gave)\b"
    r"|\bfor the owner\b",
    re.IGNORECASE,
)

ALLOWED = [
    "the owner of a rack holds its login",
    "the one owner of the bottom",
    "its single local owner (a placed component)",
    "`OWNER DECISION:` is posted without an id",
]

DECIDERS = [
    "on the owner's rack of #949",
    "(owner decision, 2026-10-09)",
    "as the owner ruled",
    "proposed, for the owner's approval",
    "if the owner wants the sentence",
]


def files():
    out = sorted((ROOT / "docs").rglob("*.md"))
    out += sorted((ROOT / "changelog.d").glob("*.md"))
    out.append(ROOT / "kit" / "README.md")
    return [p for p in out if p.is_file()]


def hits(text):
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if DECIDER.search(PROTOCOL_TOKEN.sub("", line)):
            found.append((n, line.strip()))
    return found


class NoDeciderInText(unittest.TestCase):
    def test_the_patterns_catch_a_decider(self):
        for line in DECIDERS:
            self.assertTrue(hits(line), line)

    def test_the_patterns_leave_other_senses(self):
        for line in ALLOWED:
            self.assertEqual(hits(line), [], line)

    def test_the_text_names_no_decider(self):
        bad = []
        for path in files():
            for n, line in hits(path.read_text(encoding="utf-8")):
                bad.append(f"{path.relative_to(ROOT)}:{n}: {line}")
        self.assertEqual(
            bad, [],
            "name no decider: write 'the reference rack of #949' for a rack and "
            "'decided <date>' (or 'decided in #<n>') for a ruling:\n" + "\n".join(bad))


if __name__ == "__main__":
    unittest.main()

"""Schema descriptions say what a field does, and changing one changes nothing else.

The descriptions in `spec/schemas/*.schema.json` are public: the site's schema
page shows them and so does any editor that reads a published schema. Two
guards hold them there.

ONLY DESCRIPTIONS MOVE WITHOUT SAYING SO. Each schema with every `description`
string removed is recorded as a digest in `fixtures/schema-shape.json`, and
the test compares the schema in the tree against it. A wording change passes;
a change to what validates fails until the digest is re-recorded, so a change
to validation is always a deliberate line in the diff:

    python3 spec/tests/test_schema_descriptions.py --update

The record is a committed fixture rather than `git show origin/main:` at test
time. Reading git needs history and an `origin/main` ref, which a shallow CI
checkout or an unpacked release does not have, and `origin/main` moves: once
a change merges, the comparison is main against itself and proves nothing. A
committed record means the same thing on every machine and every day.

NO DESCRIPTION CITES THE REPOSITORY. A reader of the schema page cannot follow
`docs/...md`, `spec/...`, "section 4.2", "step 5" or `#934`, and the site
does not link them. Where a reason matters it goes in the docs; the
description says what the field does. A lint code is fine: it names what fails.
"""
import hashlib
import json
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "spec/schemas"
SHAPE = pathlib.Path(__file__).resolve().parent / "fixtures/schema-shape.json"
NAMES = ("component", "device", "lab", "listing", "marks", "rack")

# The forms a description may not use. `#\d+\b` is an issue number; a hex
# colour (`#c8cacc`, `#22262a`) has a letter in it and is not matched. `§`
# only before a number: "datasheet §Physical" names a vendor's own heading.
CITES = re.compile(
    r"\.md\b|\bspec/|\bdocs/|\bsections? \d|\bsteps? \d|(?<!&)#\d+\b|§\s*\d"
    r"|\bissues? #?\d|\bPRs? #?\d|\bpull requests? #?\d|\bGH-\d"
    r"|github\.com/[^\s]*/(?:issues|pull)/", re.I)


def _strip(node):
    """The schema with every description STRING removed. A property that is
    itself called `description` is a dict and stays: it is validation."""
    if isinstance(node, dict):
        return {k: _strip(v) for k, v in node.items()
                if not (k == "description" and isinstance(v, str))}
    if isinstance(node, list):
        return [_strip(x) for x in node]
    return node


def _digest(doc):
    text = json.dumps(_strip(doc), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def _load(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def _descriptions(node, path="", out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "description" and isinstance(v, str):
                out.append((path or "/", v))
            _descriptions(v, f"{path}/{k}", out)
    elif isinstance(node, list):
        for i, x in enumerate(node):
            _descriptions(x, f"{path}/{i}", out)
    return out


def test_every_schema_has_a_recorded_shape():
    on_disk = {p.name.split(".")[0] for p in SCHEMAS.glob("*.schema.json")}
    assert on_disk == set(NAMES), f"schemas {sorted(on_disk)} against the guard's {NAMES}"
    assert set(json.loads(SHAPE.read_text())) == set(NAMES)


@pytest.mark.parametrize("name", NAMES)
def test_only_descriptions_differ_from_the_recorded_shape(name):
    want = json.loads(SHAPE.read_text())[name]
    assert _digest(_load(name)) == want, (
        f"{name}.schema.json validates differently from its recorded shape. If that "
        "is intended, re-record it with `python3 spec/tests/test_schema_descriptions.py "
        "--update` and say in the pull request what now validates differently.")


def test_the_strip_keeps_a_property_called_description():
    doc = {"properties": {"description": {"type": "string", "description": "prose"}},
           "description": "prose", "required": ["description"]}
    assert _strip(doc) == {"properties": {"description": {"type": "string"}},
                           "required": ["description"]}


def test_the_shape_moves_when_validation_moves():
    doc = _load("device")
    before = _digest(doc)
    doc["properties"]["version"]["pattern"] = "^.*$"
    assert _digest(doc) != before
    doc = _load("device")
    doc["properties"]["version"]["description"] = "reworded"
    assert _digest(doc) == before


def test_no_description_cites_the_repository():
    seen, bad = 0, []
    for name in NAMES:
        for path, text in _descriptions(_load(name)):
            seen += 1
            for m in CITES.finditer(text):
                bad.append(f"{name}{path}: {m.group(0)!r} in {text[max(0, m.start() - 40):m.end() + 20]!r}")
    # About 553 across the six on the day this was written: the walk has to
    # have read them all for a clean result to mean anything.
    assert seen >= 540, f"read only {seen} descriptions"
    assert not bad, "\n".join(bad)


@pytest.mark.parametrize("text", [
    "see docs/pdu-model-design.md", "spec/DESIGN.md carries it", "README.md",
    "spec/tools/portrayal/bevel.py builds it", "section 4.2", "sections 4.2 and 5",
    "CONTRIBUTING step 5", "(#865)", "roc-ops/Portrayal#934", "Section 9",
    "DESIGN §9", "§ 4.2", "issue 274", "issue #274", "issues 271", "PR 893", "PR #893",
    "pull request 896", "GH-951", "https://github.com/roc-ops/Portrayal/issues/951",
    "github.com/roc-ops/Portrayal/pull/896"])
def test_each_citation_form_is_caught(text):
    assert CITES.search(text), text


@pytest.mark.parametrize("text", [
    "silver (#c8cacc)", "defaulting to #22262a", "lint L53 fails", "Table 11's x8",
    "TE 114-40010 Figure 3", "the cross-section", "steps down", "a markdown file",
    "&#160;", "datasheet §Physical", "an open issue", "the PR body", "a pull request",
    "github.com/roc-ops/Portrayal"])
def test_ordinary_prose_is_not_caught(text):
    assert not CITES.search(text), text


if __name__ == "__main__":
    if sys.argv[1:] != ["--update"]:
        sys.exit("usage: test_schema_descriptions.py --update")
    SHAPE.write_text(json.dumps({n: _digest(_load(n)) for n in NAMES}, indent=1) + "\n")
    print(f"recorded {len(NAMES)} schema shapes in {SHAPE.relative_to(ROOT)}")

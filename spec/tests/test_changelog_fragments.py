"""The changelog's unreleased entries live one file per pull request under
`changelog.d/`, and `changelog.py` folds them into CHANGELOG.md when a version
is cut.

Every pull request used to add its entry at the top of `## Unreleased` /
`### Added`, so any two open pull requests conflicted on the same lines. A
fragment is a new file no other pull request touches. What can go wrong instead
is a fragment the assembly cannot place - an unknown heading, text outside an
entry - which would surface only on the day a version is cut, long after its
author has moved on. So every fragment is checked on every run.
"""
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

from portrayal import changelog   # noqa: E402

PAGE = """# Changelog

Intro.

## Unreleased

### Added
- First added.
  Continued.

### Fixed
- First fixed.

## 0.1.0

### Added
- Released.
"""


def test_every_fragment_in_the_tree_is_well_formed():
    assert (ROOT / "changelog.d" / "README.md").exists(), "changelog.d/ has lost its README"
    errors = changelog.check(ROOT)
    assert not errors, "\n".join(errors)


def test_the_readme_is_not_a_fragment():
    assert all(p.name != "README.md" for p in changelog.fragment_paths(ROOT))


def test_every_fragment_entry_lands_in_unreleased():
    """NON-VACUITY for the folding: every entry of every fragment in the tree
    reaches the `## Unreleased` section of the folded page, and nothing reaches
    a released version. With no fragments this has nothing to say, which is
    the state just after a version is cut."""
    folded = changelog.unreleased(ROOT).split("\n")
    start, end = changelog._unreleased_span(folded)
    section = "\n".join(folded[start:end])
    for p in changelog.fragment_paths(ROOT):
        sections, _ = changelog.parse(p.read_text(encoding="utf-8"))
        for entries in sections.values():
            for entry in entries:
                assert "\n".join(entry) in section, f"{p.name}: {entry[0]}"


def test_fold_appends_after_existing_entries_and_adds_a_missing_heading():
    frag, errors = changelog.parse(
        "### Fixed\n- Second fixed.\n\n### Removed\n- Gone, use `x/y@2`.\n"
        "\n### Added\n- Second added.\n  Its second line.\n")
    assert not errors
    out = changelog.fold(PAGE, [frag])
    unreleased = out.split("## 0.1.0")[0]
    assert unreleased.index("- First added.") < unreleased.index("- Second added.") \
        < unreleased.index("### Fixed")
    assert "  Continued.\n- Second added.\n  Its second line.\n\n### Fixed" in out
    assert "- First fixed.\n- Second fixed.\n" in out
    # the heading the section lacked closes it, before the next version
    assert "- Second fixed.\n\n### Removed\n- Gone, use `x/y@2`.\n\n## 0.1.0" in out
    # nothing moved into the released version
    assert out.split("## 0.1.0")[1] == PAGE.split("## 0.1.0")[1]


def test_fragments_fold_in_the_order_given():
    a, _ = changelog.parse("### Added\n- From a.\n")
    b, _ = changelog.parse("### Added\n- From b.\n")
    out = changelog.fold(PAGE, [a, b])
    assert out.index("- From a.") < out.index("- From b.")


@pytest.mark.parametrize("text, says", [
    ("### Misc\n- Something.\n", "is not one of"),
    ("## 0.2.0\n### Added\n- Something.\n", "only `### <heading>`"),
    ("- An entry with no heading.\n", "before the first"),
    ("### Added\n", "has no entries"),
    ("", "empty fragment"),
    ("### Added\nNot a list item.\n", "starts with `- `"),
    ("### Added\n- One.\n### Added\n- Two.\n", "appears twice"),
])
def test_a_malformed_fragment_is_refused(text, says):
    _, errors = changelog.parse(text)
    assert any(says in e for e in errors), errors


def test_assemble_writes_the_page_and_deletes_only_fragments(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(PAGE)
    d = tmp_path / "changelog.d"
    d.mkdir()
    (d / "README.md").write_text("# not a fragment\n")
    (d / "one.md").write_text("### Fixed\n- Fixed by one.\n")
    assert changelog.main(["--root", str(tmp_path), "--assemble"]) == 0
    assert "- First fixed.\n- Fixed by one.\n" in (tmp_path / "CHANGELOG.md").read_text()
    assert sorted(p.name for p in d.iterdir()) == ["README.md"]


def test_assemble_refuses_and_keeps_everything_when_a_fragment_is_bad(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(PAGE)
    d = tmp_path / "changelog.d"
    d.mkdir()
    (d / "good.md").write_text("### Added\n- Good.\n")
    (d / "bad.md").write_text("### Misc\n- Bad.\n")
    assert changelog.main(["--root", str(tmp_path), "--assemble"]) == 1
    assert (tmp_path / "CHANGELOG.md").read_text() == PAGE
    assert sorted(p.name for p in d.iterdir()) == ["bad.md", "good.md"]

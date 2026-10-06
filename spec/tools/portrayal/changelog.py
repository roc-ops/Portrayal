#!/usr/bin/env python3
"""The changelog's unreleased entries, one file per pull request.

WHY FRAGMENTS. Every pull request used to add its entry at the top of
`## Unreleased` / `### Added` in CHANGELOG.md, so any two open pull requests
edited the same lines and the second to merge had to merge main in again, at
the cost of a full CI run each time. A pull request now adds one new file under
`changelog.d/`, which no other pull request touches, and the file says which
heading each entry belongs under:

    ### Added
    - The new part, what seats it, and what a consumer has to do (#123).

    ### Fixed
    - ...

Until a version is cut the unreleased record is CHANGELOG.md's own
`## Unreleased` section followed by every fragment. Cutting a version folds the
fragments in, each entry after the ones already under its heading, and deletes
the fragment files:

    python3 spec/tools/portrayal/changelog.py --check      # what the test runs
    python3 spec/tools/portrayal/changelog.py --show       # Unreleased, fragments folded in
    python3 spec/tools/portrayal/changelog.py --assemble   # write it, delete the fragments
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# THE FOUR HEADINGS THE CHANGELOG ALREADY USES, in the order a new one is
# appended when `## Unreleased` does not have it yet. A fifth is refused rather
# than invented: a heading only one fragment uses is a section only one reader
# looks for.
HEADINGS = ("Added", "Changed", "Removed", "Fixed")

# `changelog.d/README.md` explains the directory and is not a fragment.
NOT_FRAGMENTS = {"README.md"}

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


def fragment_paths(root=ROOT):
    d = Path(root) / "changelog.d"
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.md") if p.name not in NOT_FRAGMENTS)


def parse(text):
    """`### Heading` -> list of entries, each entry its lines as written.

    Returns (sections, errors). An entry starts at a line beginning `- ` and
    runs, continuation lines and all, to the next entry or heading; blank lines
    between entries are dropped and put back on assembly.
    """
    sections, errors, current = {}, [], None
    for n, line in enumerate(text.splitlines(), 1):
        m = HEADING.match(line)
        if m:
            level, title = m.groups()
            if level != "###":
                errors.append(f"line {n}: only `### <heading>` lines go in a fragment, "
                              f"not {level} (the version headings belong to CHANGELOG.md)")
                current = None
            elif title not in HEADINGS:
                errors.append(f"line {n}: `### {title}` is not one of "
                              f"{', '.join(HEADINGS)}")
                current = None
            elif title in sections:
                errors.append(f"line {n}: `### {title}` appears twice; put its entries together")
                current = sections[title]
            else:
                current = sections[title] = []
            continue
        if not line.strip():
            continue
        if current is None:
            errors.append(f"line {n}: text before the first `### <heading>`")
            continue
        if line.startswith("- "):
            current.append([line])
        elif current and line.startswith("  "):
            current[-1].append(line)
        else:
            errors.append(f"line {n}: an entry starts with `- ` and its continuation lines "
                          f"are indented two spaces")
    for title, entries in sections.items():
        if not entries:
            errors.append(f"`### {title}` has no entries")
    if not sections and not errors:
        errors.append("no `### <heading>` and no entries: an empty fragment records nothing")
    return sections, errors


def check(root=ROOT):
    """Every fragment's problems, as `path: message` lines. Empty is clean."""
    out = []
    for p in fragment_paths(root):
        _, errors = parse(p.read_text(encoding="utf-8"))
        out += [f"{p.relative_to(root)}: {e}" for e in errors]
    return out


def _unreleased_span(lines):
    """[start, end) of the `## Unreleased` section's body, by line index."""
    start = next((i for i, l in enumerate(lines) if l.strip() == "## Unreleased"), None)
    if start is None:
        raise ValueError("CHANGELOG.md has no `## Unreleased` section")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
               len(lines))
    return start + 1, end


def fold(changelog, fragments):
    """CHANGELOG.md's text with each fragment's entries folded into
    `## Unreleased`: after the entries already under the same heading, or
    under a new heading at the end of the section when it has none yet.
    `fragments` is a list of parsed sections, in the order to fold them."""
    lines = changelog.split("\n")
    for sections in fragments:
        for title in HEADINGS:
            entries = sections.get(title)
            if not entries:
                continue
            new = [l for e in entries for l in e]
            body_start, body_end = _unreleased_span(lines)
            at = next((i for i in range(body_start, body_end)
                       if lines[i].strip() == f"### {title}"), None)
            if at is None:
                # a new heading closes the section, separated by one blank line
                # on each side the way the existing ones are
                end = body_end
                while end > body_start and not lines[end - 1].strip():
                    end -= 1
                lines[end:end] = ["", f"### {title}"] + new
                continue
            end = next((i for i in range(at + 1, body_end) if lines[i].startswith("#")),
                       body_end)
            while end > at + 1 and not lines[end - 1].strip():
                end -= 1
            lines[end:end] = new
    return "\n".join(lines)


def unreleased(root=ROOT):
    """CHANGELOG.md as it will read once the fragments are folded in. Anything
    that reads the changelog for what is unreleased reads this."""
    root = Path(root)
    body = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    parsed = [parse(p.read_text(encoding="utf-8"))[0] for p in fragment_paths(root)]
    return fold(body, parsed)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="the checkout (default: this one)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate the fragments")
    mode.add_argument("--show", action="store_true",
                      help="print CHANGELOG.md with the fragments folded in")
    mode.add_argument("--assemble", action="store_true",
                      help="write the folded CHANGELOG.md and delete the fragments")
    args = ap.parse_args(argv)
    root = Path(args.root)
    errors = check(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.check:
        print(f"{len(fragment_paths(root))} changelog fragment(s), all well formed")
        return 0
    text = unreleased(root)
    if args.show:
        sys.stdout.write(text)
        return 0
    # THE PAGE IS WRITTEN BEFORE A FRAGMENT IS DELETED, and only once every
    # fragment has parsed clean above: an entry that did not reach the page
    # would otherwise go with its file
    paths = fragment_paths(root)
    (root / "CHANGELOG.md").write_text(text, encoding="utf-8")
    for p in paths:
        p.unlink()
    print(f"folded {len(paths)} fragment(s) into CHANGELOG.md and deleted them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

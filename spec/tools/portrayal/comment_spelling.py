#!/usr/bin/env python3
"""American spellings in the COMMENTS of the kit's rack modules - prose there is
the project's own, and the project writes British. Code, identifiers, data keys
and strings are not looked at: renaming those would break their callers.

    comment_spelling.py [kit/rack]          exit 1 and list each finding

A word inside backticks is an identifier being quoted, and is left alone.
"""
import argparse
import re
import sys
from pathlib import Path

WORDS = {
    "color": "colour", "colors": "colours", "colored": "coloured", "center": "centre",
    "centered": "centred", "centers": "centres", "meter": "metre", "meters": "metres",
    "millimeter": "millimetre", "millimeters": "millimetres", "behavior": "behaviour",
    "gray": "grey", "favor": "favour", "neighbor": "neighbour", "neighbors": "neighbours",
    "catalog": "catalogue", "analyze": "analyse", "organize": "organise", "recognize": "recognise",
    "fiber": "fibre", "labeled": "labelled", "modeled": "modelled", "canceled": "cancelled",
}
WORD = re.compile(r"\b(" + "|".join(WORDS) + r")\b", re.I)
QUOTED = re.compile(r"`[^`]*`")


def comments(text):
    """(line number, comment text) for every comment in a JS source."""
    out, block = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if block:
            end = line.find("*/")
            out.append((n, line if end < 0 else line[:end]))
            block = end < 0
            continue
        # a // or /* outside a string: good enough for these files, whose
        # strings hold no comment markers - checked by the test
        m = re.search(r"(?<![:'\"`])//(.*)$", line)
        if m:
            out.append((n, m.group(1)))
        s = line.find("/*")
        if s >= 0 and not m:
            end = line.find("*/", s + 2)
            out.append((n, line[s + 2:] if end < 0 else line[s + 2:end]))
            block = end < 0
    return out


def findings(root):
    for p in sorted(Path(root).rglob("*.js")):
        for n, c in comments(p.read_text()):
            for w in WORD.findall(QUOTED.sub("", c)):
                yield f"{p}:{n}: {w} -> {WORDS[w.lower()]}"


def main(argv=None):
    ap = argparse.ArgumentParser(description="American spellings in the comments of the kit's rack modules.")
    ap.add_argument("root", nargs="?", default="kit/rack", help="directory of .js files (default kit/rack)")
    bad = list(findings(ap.parse_args(argv).root))
    print("\n".join(bad) or "comment spelling: clean")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

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
    """(line number, comment text) for every comment in a JS source.

    A small scanner, string-aware: '...', "..." and `...` spans (with escapes)
    are skipped, so a comment marker inside one starts nothing. A block comment
    is reported line by line; a // after a closed /* */ on one line is read too.
    Regex literals are not understood - none of these files hide a marker in one.
    """
    out, n, i, quote = [], 1, 0, None
    while i < len(text):
        c, two = text[i], text[i:i + 2]
        if quote:
            if c == "\\":
                i += 1
                n += text[i:i + 1] == "\n"
            elif c == quote:
                quote = None
            elif c == "\n":
                n += 1
                if quote != "`":
                    quote = None  # an unterminated ' or " ends at the line
        elif c in "'\"`":
            quote = c
        elif two == "//":
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            out.append((n, text[i + 2:end]))
            i = end
            continue
        elif two == "/*":
            end = text.find("*/", i + 2)
            end = len(text) if end < 0 else end
            chunk = text[i + 2:end]
            for k, part in enumerate(chunk.split("\n")):
                out.append((n + k, part))
            n += chunk.count("\n")
            i = end + 2
            continue
        elif c == "\n":
            n += 1
        i += 1
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

#!/usr/bin/env python3
"""L62 sweep: spell every port lamp `led-port-N`.

THE REPLACEMENT COMES FROM THE RULE, not from a second implementation of it.
Two spellings of the same intent is exactly the divergence L62 exists to stop,
and a sweep that re-derives the target name would be the third.

The rewrite is TEXTUAL. These files carry paragraphs of provenance prose as
block scalars, and a yaml.safe_load/safe_dump round-trip discards every comment,
reflows every block and rewrites the flow-style placement lines - a diff of
100,000 lines in which the rename is invisible. So: a boundary-anchored token
substitution over the file's bytes, which touches the names and nothing else.

Boundaries matter here more than usual: `led-p1` is a prefix of `led-p10`, and a
naive replace renames sixteen lamps to `led-port-10` on any device with more
than nine ports.

A lamp id is referenced from six places (measured across the corpus, not
recalled): silkscreen/for, placements/for, panel/cutouts/id, regions/members,
gaps/scope and attrs/combo-with. A file-wide token substitution covers all six
at once. It also covers the prose, which is the right answer - a provenance
sentence naming an id that no longer exists is a dangling reference a human
reads.

`group: port-leds` and `role: port-leds` are NOT lamp ids and do not match the
token pattern, so they are safe by construction rather than by exclusion.
"""
import glob
import pathlib
import re
import sys

import argparse
import yaml
from portrayal import lint as L
from portrayal import libwalk
# A GUARD, BECAUSE THIS FILE DOES ITS WORK AT MODULE SCOPE. It is a script and
# reads as one, which was harmless while nothing could import it - and #179 made
# the sweeps a package, so `import portrayal_sweeps.sweep_ids` RAN THE SWEEP.
# A module-level `if` opens no scope, so everything below is still a global and
# the script path is unchanged; only the import path is.
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", default="library")
    ap.add_argument("--schemas", default="spec/schemas")
    ap.add_argument("--apply", action="store_true",
                    help="write the renames; without it, report only")
    ap.add_argument("only", nargs="*", help="limit to devices matching these fragments")
    ARGS = ap.parse_args()
    APPLY, LIB = ARGS.apply, ARGS.library

    if not L.STANDARDS:
        L.STANDARDS.update(yaml.safe_load(
            (pathlib.Path(ARGS.schemas) / "standards.yaml").read_text())['standards'])

    # BOTH HALVES OF THE RULE, and only where it commits to a replacement.
    #
    #   `{vname}/{pid}: a port lamp is spelled ... Rename it 'led-port-3'`
    #   `{vname}/{pid}: the id opens with 'smb' ... use 'clk-1pps-in', which is ...`
    #
    # The connector half was left out while the rule could still propose a name the
    # device already used or a leftover that named nothing; both of those now report
    # without offering a replacement, so a message that says `use '...'` is one the
    # rule is prepared to stand behind and this can apply it.
    RENAME = re.compile(
        r"\[L62\] ([a-z]+)/([\w.-]+): (?:a port lamp .*?Rename it|the id opens with .*? - use) "
        r"'([\w.-]+)'", re.S)


    def token(name):
        """The id as a whole word - not as the head of a longer one, and NEVER as
        the name of a component.

        `micro-usb` is both a placement id and half of `std/micro-usb@1`, so a
        file-wide substitution renamed the PART as well as the placement and wrote
        `ref: std/console-usb@1` into eleven devices - a ref to a component that
        does not exist, which is the one thing an id sweep must never produce. The
        lamp half never hit this because no lamp id is also a component name.

        A component ref is `<namespace>/<name>@<major>`, and the `@` is what tells
        it apart from a cross-view reference like `for: rear/fan-3`, which IS a
        placement id and does have to be renamed. So: a match followed by `@` is a
        part, not a placement, and is left alone.
        """
        return re.compile(r"(?<![A-Za-z0-9-])" + re.escape(name) + r"(?![A-Za-z0-9-])(?!@)")


    total_files = total_ids = total_edits = 0
    skipped = []

    for path in libwalk.iter_devices([LIB]):
        if ARGS.only and not any(o in path for o in ARGS.only):
            continue
        data = yaml.safe_load(open(path))
        L.WARNINGS.clear()
        L.lint_device_id_convention(path, data, [LIB])

        pairs = {}
        for w in L.WARNINGS:
            m = RENAME.search(w)
            if m:
                pairs[m.group(2)] = m.group(3)
        if not pairs:
            continue

        # A rename that lands on a name already in use would MERGE two placements
        # into one id, which the schema forbids and which no rule would attribute
        # back to this sweep. Refuse the file rather than the pair.
        taken = set()
        for view in (data.get("views") or {}).values():
            for q in (((view or {}).get("components") or {}).get("placements") or []):
                taken.add(str(q.get("id")))
        clash = {o: n for o, n in pairs.items() if n in taken and n != o}
        if clash:
            skipped.append((path, clash))
            continue

        text = original = pathlib.Path(path).read_text()
        # LONGEST FIRST, so `led-p1` cannot consume part of `led-p12` even though
        # the boundary already forbids it. Belt and braces on the one hazard that
        # would be silent.
        edits = 0
        for old in sorted(pairs, key=len, reverse=True):
            text, n = token(old).subn(pairs[old], text)
            edits += n

        total_files += 1
        total_ids += len(pairs)
        total_edits += edits
        print(f"{path.split('devices/')[1]:44s} {len(pairs):4d} ids  {edits:5d} occurrences")
        if APPLY and text != original:
            pathlib.Path(path).write_text(text)

    print(f"\n{total_files} devices, {total_ids} lamp ids, {total_edits} occurrences "
          f"({'WRITTEN' if APPLY else 'dry run'})")
    for path, clash in skipped:
        print(f"SKIPPED {path}: rename would collide with an existing id: {clash}")

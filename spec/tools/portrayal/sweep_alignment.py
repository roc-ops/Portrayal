#!/usr/bin/env python3
"""L61 sweep: centre the marks that are visibly reaching for something.

The rule decides; this only applies the arithmetic it already printed. Every
slip carries `axis`, `got` and `want`, so the correction is `want - got` on one
coordinate of one item. Nothing here re-derives which axis should line up - see
`alignment_slips`, which exists so that the rule and its remedy cannot drift
apart.

TWO THINGS MAKE THIS SAFE TO RUN ACROSS SIXTY DEVICES UNATTENDED.

FIRST, THE EDIT IS LINE-SCOPED. Placements and marks are written one per line in
flow style, so the change is a substitution of `at: [x, y]` within a single
known line - the provenance prose, the block scalars and the comments in the
rest of the file are never re-serialised. The line is found by parsing a second
time with a loader that records where each mapping started, in lockstep with the
parse the rule reads, rather than by searching the text for a mark that has no
unique textual signature.

SECOND, CENTRING IS NOT ALWAYS RIGHT, AND THE ACCEPTANCE TEST SAYS SO. The rule
itself offers two remedies - centre it, or move it somewhere it is plainly not
trying to line up - and only a person can choose the second. A mark that was
deliberately nudged off centre to clear its neighbour will, when centred,
collide with that neighbour; that is a fact another rule already checks. So the
device is linted before and after, and if the correction introduces ANY warning
that is not L61, the whole device is put back and reported for a person. Lint
getting quieter is the only accepted outcome.

Moving a placement moves a box other marks are measured against, so a single
pass can expose a slip that was previously out of range. Iterate to a fixpoint.

WHAT IS LEFT AFTER THIS IS NOT SWEEPABLE, AND A SECOND PASS WAS TRIED AND
REJECTED. The residue is columns - a numeral and its lamp beside one port - where
no member can move alone because it would land on its neighbour. Shifting the
whole SET by one delta, so its midpoint lands on the target, looks like the
obvious answer: the members keep their spacing, so nothing inside the set can
collide, and it took L61 from 656 warnings to 36.

IT MADE THE DRAWINGS WORSE. Measured across the corpus, 704 items moved closer
to what they name and 626 moved FURTHER away - on most devices an exact one for
one trade, 84 better and 84 worse, 66 and 66, 50 and 50. That is the signature
of centring a two-member set: one member improves and the other degrades by the
same amount. On the S9705-48D a lamp sitting 0.30mm off its port was dragged to
1.44mm off so that its numeral could meet it in the middle.

The reason it is not a fix is that the members are not always meant to straddle.
That device's numerals sit near the top of each port and its lamps at the middle,
by design; the S9720-56ED's numerals and lamps straddle. Nothing in the file says
which, so no tool can tell them apart - and the acceptance test cannot catch the
damage either, because once a set straddles evenly L61 goes quiet and the sweep
reads its own vandalism as success.

A rule going quiet is not the same as a drawing getting better. What the residue
needs is a reader with the figure open.

    sweep_alignment.py --library library --schemas spec/schemas [device ...]
    sweep_alignment.py --library library --schemas spec/schemas --apply

Without --apply nothing is written: every device is corrected, judged, and put
back, and the report is what would have happened.
"""
import argparse
import glob
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import yaml
from portrayal import lint as L
ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("--library", default="library")
ap.add_argument("--schemas", default="spec/schemas")
ap.add_argument("--apply", action="store_true",
                help="write the corrections; without it, report only")
ap.add_argument("only", nargs="*", help="limit to devices matching these fragments")
ARGS = ap.parse_args()
APPLY = ARGS.apply
LIB = ARGS.library
MAX_PASSES = 6

if not L.STANDARDS:
    L.STANDARDS.update(yaml.safe_load(
        (pathlib.Path(ARGS.schemas) / "standards.yaml").read_text())['standards'])

LINES = {}


class LineLoader(yaml.SafeLoader):
    """A SafeLoader that remembers which line each mapping opened on."""


def _construct_mapping(loader, node, deep=False):
    m = yaml.SafeLoader.construct_mapping(loader, node, deep=deep)
    LINES[id(m)] = node.start_mark.line
    return m


LineLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def num(v):
    """2dp, minimally written, matching how the corpus writes coordinates.

    The rounding error is at most 0.005mm against a rule that ignores anything
    under 0.08, so it can never leave a mark still reported.
    """
    s = f"{round(v, 2):.2f}".rstrip("0").rstrip(".")
    return s or "0"


AT = re.compile(r"(at:\s*\[\s*)(-?[\d.]+)(\s*,\s*)(-?[\d.]+)(\s*\])")


def shift_line(line, axis_index, delta):
    """Move one coordinate of the single `at:` on this line."""
    if len(AT.findall(line)) != 1:
        return None
    def sub(m):
        vals = [float(m.group(2)), float(m.group(4))]
        vals[axis_index] += delta
        return f"{m.group(1)}{num(vals[0])}{m.group(3)}{num(vals[1])}{m.group(5)}"
    return AT.sub(sub, line, count=1)


def warnings_for(path):
    """Every warning and error this device raises, as a multiset of codes.

    THE REAL LINTER, as a subprocess, rather than a hand-picked list of rule
    functions called in-process. A sweep judged by a subset of the rules is
    judged by the rules that happened to come to mind while writing it, and the
    one it forgot is the one that would have caught the damage. This costs a
    second and a half per device and removes the question.
    """
    frag = path.split('devices/')[1].replace('/device.yaml', '')
    out = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).with_name('lint.py')),
         '--schemas', ARGS.schemas, '--library', LIB, '--device', frag],
        capture_output=True, text=True).stdout
    # THE SUMMARY LINES, NOT THE EXAMPLES. The linter prints at most five
    # examples per rule, so counting the printed lines caps every code at five -
    # a rule that went from twenty to forty would have read 5 -> 5 and passed.
    #
    # AND ERRORS SUMMARISE IN A DIFFERENT SHAPE FROM WARNINGS. Warnings are
    # totalled per code, `LINT: 45 warning(s) [L61]`; errors are totalled ONCE
    # for the whole run, `LINT: 49 error(s) across 22 file(s)`, with no code in
    # the line. A reader who matches only the first shape sees a device that
    # raises forty-nine errors as raising nothing at all - which is how this
    # sweep first came to pass fifty-seven devices while breaking one of them.
    counts = {}
    for line in out.split("\n"):
        line = line.strip()
        m = re.match(r"LINT: (\d+) warning\(s\) \[([LE]\d+)\]", line)
        if m:
            counts[m.group(2)] = int(m.group(1))
        m = re.match(r"LINT: (\d+) error\(s\)", line)
        if m:
            counts["ERRORS"] = int(m.group(1))
    return counts


def sweep_once(path, excluded=()):
    """One pass. Returns how many coordinates moved."""
    LINES.clear()
    data = yaml.load(open(path), Loader=LineLoader)
    slips = list(L.alignment_slips(data, [LIB]))

    # A MEMBER OF A SPREAD SET IS NOT A LONE LEGEND, and centring it as though
    # it were is how this sweep first proposed to stack two lamps on one point.
    #
    # The AS5912 puts ports 49 and 50 one above the other and lays FOUR lamps in
    # the gap between them, told apart by x alone. L61 reads each as sitting
    # `above or below` its own port and asks for both to be centred on the same
    # 381.5 - which is not a correction, it is a collision, and the 2.00x2.00mm
    # overlap it produces is the whole of a 2mm lamp.
    #
    # So: when two or more items want the SAME coordinate on the centring axis
    # AND sit in the same band across it, their offsets along that axis are what
    # distinguish them, and the set is left exactly as its author placed it. The
    # rule still reports them; choosing between centring the set as a group and
    # leaving it alone is a judgement about the drawing, and nothing here is
    # entitled to make it.
    #
    # THE BAND TEST IS WHAT KEEPS THIS FROM SWALLOWING THE HONEST CASES. A
    # numeral above a port and a lamp below it also share the port's x, and both
    # SHOULD be centred on it - they can never collide, because they are 10mm
    # apart across the axis. Only items already sharing a row (or a column) are
    # competing for the same place.
    # AND THE COMPANION MAY NOT ITSELF BE A SLIP. On the S8901 every port
    # carries two arrow lamps straddling its centre, one 1.38mm out and one
    # 2.22mm; only the first is inside L61's window. A guard that compares slips
    # against slips sees a lone lamp beside a port, centres it, and drives it
    # into a partner that was never reported. So compare against every item that
    # names a target, reported or not.
    BAND = 2.5
    everything = list(L.alignment_targets(data, [LIB]))
    kept = []
    for s in slips:
        centre_key = "tcx" if s["axis"] == "horizontally" else "tcy"
        perp = "cy" if s["axis"] == "horizontally" else "cx"
        company = [t for t in everything
                   if t["view"] == s["view"]
                   and (t["kind"], t["index"]) != (s["kind"], s["index"])
                   and abs(t[centre_key] - s["want"]) <= 0.001
                   and abs(t[perp] - s[perp]) < BAND]
        if not company:
            kept.append(s)
    slips = kept

    slips = [s for s in slips
             if (s["view"], s["kind"], s["index"]) not in excluded]
    if not slips:
        return 0

    # A PART AND THE HOLE IT SITS IN ARE ONE FEATURE. Moving a lamp without its
    # cutout leaves the part 0.42mm off-centre in its own opening, which L39 and
    # L63 both report - and correctly, because sheet metal is punched where the
    # lamp goes. If the lamp is misaligned against its port then so is the hole,
    # and they move together or not at all.
    cut_line = {}
    for view in (data.get("views") or {}).values():
        for c in (((view or {}).get("panel") or {}).get("cutouts") or []):
            if c.get("id") and c.get("at"):
                cut_line[str(c["id"])] = LINES.get(id(c))

    text = pathlib.Path(path).read_text()
    lines = text.split("\n")
    moved = skipped = 0
    for s in slips:
        ln = LINES.get(id(s["item"]))
        if ln is None or ln >= len(lines):
            skipped += 1
            continue
        axis = 0 if s["axis"] == "horizontally" else 1
        delta = s["want"] - s["got"]
        new = shift_line(lines[ln], axis, delta)
        if new is None:
            skipped += 1
            continue

        # the hole, when this is a part that has one
        hole = None
        if s["kind"] == "placement":
            cl = cut_line.get(str(s["item"].get("id")))
            if cl is not None:
                hole = shift_line(lines[cl], axis, delta)
                if hole is None:
                    skipped += 1
                    continue
                lines[cl] = hole
        lines[ln] = new
        moved += 1
    if moved:
        pathlib.Path(path).write_text("\n".join(lines))
    return moved


total_moved = 0
reverted = []
touched = []

only = ARGS.only

for path in sorted(glob.glob(f'{LIB}/devices/*/*/device.yaml')):
    if only and not any(o in path for o in only):
        continue
    LINES.clear()
    data = yaml.safe_load(open(path))
    if not list(L.alignment_slips(data, [LIB])):
        continue

    before = warnings_for(path)
    backup = pathlib.Path(tempfile.mkstemp(suffix=".yaml")[1])
    shutil.copy(path, backup)

    moved = 0
    for _ in range(MAX_PASSES):
        n = sweep_once(path)
        moved += n
        if not n:
            break

    after = warnings_for(path)
    # ANY new warning that is not L61 means centring was the wrong remedy here.
    new = {k: v for k, v in after.items()
           if k != "L61" and v > before.get(k, 0)}
    name = path.split('devices/')[1].replace('/device.yaml', '')
    if new:
        # WHICH rule, and an example. A bare count says a person is needed
        # without saying what for.
        out = subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).with_name('lint.py')),
             '--schemas', ARGS.schemas, '--library', LIB, '--device', name],
            capture_output=True, text=True).stdout
        why = ""
        for line in out.split("\n"):
            m = re.search(r"\[(L\d+)\] (.*)", line)
            if m and name in line and m.group(1) != "L61" and (
                    m.group(1) in new or m.group(1) not in before):
                why = f"{m.group(1)}: {m.group(2)[:110]}"
                break
        shutil.copy(backup, path)
        reverted.append((name, new, moved, why))
        print(f"REVERT {name:26s} centring raised {new}\n       ^ {why}")
    else:
        total_moved += moved
        touched.append((name, moved, before.get("L61", 0), after.get("L61", 0)))
        print(f"       {name:26s} {moved:5d} moved   L61 "
              f"{before.get('L61', 0)} -> {after.get('L61', 0)}")
    if not APPLY:
        shutil.copy(backup, path)
    backup.unlink()

print(f"\n{len(touched)} devices corrected, {total_moved} coordinates moved "
      f"({'WRITTEN' if APPLY else 'dry run - all restored'})")
if reverted:
    print(f"{len(reverted)} devices left alone for a person:")
    for name, new, moved, why in reverted:
        print(f"  {name}: {new}\n      {why}")

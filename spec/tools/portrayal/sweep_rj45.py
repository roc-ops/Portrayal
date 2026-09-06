#!/usr/bin/env python3
"""#125 sweep: every RJ45 onto the four-part family, lamps into the jack.

THE RULE DECIDES, NOT THIS FILE. Which part a jack takes comes from
lint.rj45_wants_lamps - the same test L76 counts with - so the sweep cannot
disagree with the census that checks it.

THE REWRITE IS TEXTUAL, like sweep_ids.py and sweep_jack_lamps.py: these files
carry paragraphs of provenance as block scalars, and a yaml round-trip reflows
all of it. A placement is the line carrying `id: X` and `ref:`, through balanced
braces; only that span is edited.

EVERY JACK HOLDS ITS CENTRE. The new part is a different size from the old; the
anchor moves by half the difference so the plug interface does not move on any
faceplate.

    sweep_rj45.py --library library [--devices DIR] [--components] [--apply] [fragment ...]
"""
import argparse
import collections
import glob
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import yaml
import lint as L

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("--library", default="library")
ap.add_argument("--devices", help="device tree to sweep (default: <library>/devices)")
ap.add_argument("--schemas", default="spec/schemas")
ap.add_argument("--components", action="store_true", help="sweep parts: in component contracts instead")
ap.add_argument("--apply", action="store_true")
ap.add_argument("only", nargs="*")
ARGS = ap.parse_args()
LIB = ARGS.library
ROOTS = [LIB]
if not L.STANDARDS:
    L.STANDARDS.update(yaml.safe_load(
        (pathlib.Path(ARGS.schemas) / "standards.yaml").read_text())["standards"])

SINGLE = {"std/rj45@1", "common/rj45-port@4", "common/rj45-bezel@2", "common/rj45-shielded@1",
          "common/rj45-shielded@2", "common/rj45-jack@2"}
GANGED = {"std/rj45-ganged@1", "common/rj45-hd@1", "common/rj45-hd-plain@1"}

# Controller ruling (fix round 4): all four NEW parts are pins-up, keyway-down
# when unrotated. Two OLD parts drew the OTHER way up: common/rj45-port@4
# composes its inner std/rj45@1 with an internal `rotate: 180` (its own
# description says "stepped keyway up"), and common/rj45-jack@2 is "pins
# down, clip notch up". The sweep only ever edits ref/at/skin/states - it
# never touches a placement's own `rotate:` - so a placement moved off either
# of these two now presents the flipped face at the SAME rotate value it
# always had. Flip it: new_rotate = (old_rotate + 180) % 360, so the part
# underneath turns over and the jack keeps its original, verified orientation
# on the faceplate.
FLIP_ORIGIN = {"common/rj45-port@4", "common/rj45-jack@2"}

# Controller ruling (ufispace s9* batch): a lamp drawn within this many mm of
# the jack's footprint counts as INSIDE it. The vendor drawings place some
# lamps right on the jack's drawn edge - that is a statement about where the
# lamp sits on the faceplate, not a coordinate-rounding artefact, so the
# inside/outside test tolerates it rather than reporting it unresolved.
LAMP_EDGE_TOL = 1.0

# A `\b` boundary treats `-` as a word break, so `led-oob-left\b` matches the
# PREFIX of `led-oob-left-2` too. Require instead that the next character
# actually ends the id: a list/scalar delimiter, whitespace, or end of line.
BOUND = r"(?=[,\]}\s]|$)"

# These contracts are retired wrappers, deleted whole in a later task; their
# internal `jack:` part must not be swept out from under them first. Matched
# by path segment (any version), not by ref, so `--components` skips the
# contract entirely and reports nothing for it.
RETIRED_COMPONENT_DIRS = {
    "common/rj45-port", "common/rj45-bezel", "common/rj45-hd", "common/rj45-hd-plain",
    "common/rj45-shielded", "common/rj45-jack",
    "std/rj45", "std/rj45-ganged",
}


def is_retired_wrapper(path):
    return any(f"/components/{d}/v" in path for d in RETIRED_COMPONENT_DIRS)


def target(ref, lamps):
    if ref in SINGLE:
        return "common/rj45-eth@1" if lamps else "std/rj45@2"
    if ref in GANGED:
        return "common/rj45-ganged-eth@1" if lamps else "std/rj45-ganged@2"
    return None


def size(ref):
    s = L.contract_size(ref, ROOTS)
    return (s["w"], s["h"])


def cls(ref):
    cp = L.resolve_component(ref, ROOTS) if ref else None
    return (L.load_yaml(cp) or {}).get("class") if cp else None


def _item_bounds(rows, i):
    """The (start, end) of the list item line i sits inside, by YAML indentation:
    an item runs from its own `- ` marker to just before the next line at the
    same or lesser indent. Handles both a flow placement on one row (`- {...}`,
    where the next sibling `- ` sits at the same indent and end == start), a
    flow placement wrapped onto a more-indented continuation line, and a block
    placement written one `key: value` per line (no braces at all, so brace
    counting never finds the end) - all three shapes appear in the library."""
    start = i
    while start > 0 and not re.match(r"^\s*-\s", rows[start]):
        start -= 1
    indent = len(rows[start]) - len(rows[start].lstrip(" "))
    end = start
    for j in range(start + 1, len(rows)):
        line = rows[j]
        depth = len(line) - len(line.lstrip(" "))
        if line.strip() and depth <= indent:
            break
        end = j
    return start, end


def view_bounds(rows, vname):
    """(start, end) line indexes of the `  <vname>:` view block under `views:`,
    running from its own header to just before the next sibling view (or end
    of file). An id repeated across views (variant views do this today for 68
    non-RJ45 ids) must only ever be found inside its OWN view - otherwise the
    whole-file search finds view 1's placement twice and view 2's never."""
    start = None
    for i, l in enumerate(rows):
        if re.match(rf"^  {re.escape(vname)}:\s*$", l):
            start = i
            break
    if start is None:
        return 0, len(rows)
    end = len(rows)
    for j in range(start + 1, len(rows)):
        if re.match(r"^  \S", rows[j]):  # next sibling view, same 2-space indent
            end = j
            break
    return start, end


def span(rows, pid, lo=0, hi=None):
    """(start, end) line indexes of the placement carrying id: pid, flow or
    block, searched only within rows[lo:hi] (default: the whole file)."""
    hi = len(rows) if hi is None else hi
    for i in range(lo, hi):
        l = rows[i]
        if not re.search(rf"\bid: {re.escape(pid)}(?:[,}}\s]|$)", l):
            continue
        start, end = _item_bounds(rows, i)
        if "ref:" in "\n".join(rows[start:end + 1]):
            return start, end
    return None


def cutout_span(rows, pid, lo=0, hi=None):
    hi = len(rows) if hi is None else hi
    for i in range(lo, hi):
        l = rows[i]
        if re.search(rf"\bid: {re.escape(pid)}(?:[,}}\s]|$)", l) and "ref:" not in l and "size:" in l:
            return i, i
    return None


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def edit_at(text, dx, dy):
    m = re.search(r"at: \[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]", text)
    x, y = float(m.group(1)) + dx, float(m.group(2)) + dy
    return text[:m.start()] + f"at: [{fmt(round(x, 2))}, {fmt(round(y, 2))}]" + text[m.end():]


def read_at(text):
    """The (x, y) an `at: [x, y]` in text currently reads, after any edit_at."""
    m = re.search(r"at: \[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]", text)
    return float(m.group(1)), float(m.group(2))


def flip_rotate(block, old_rotate, new_rotate):
    """Rewrite a placement/part block's `rotate:` from old_rotate to the
    FLIPPED new_rotate the caller already computed (only 0 -> 180 or
    180 -> 0 ever arise here, from FLIP_ORIGIN). Flow style (`- {...}`, one
    row or wrapped over several) gets `rotate: 180` spliced in right after
    `at: [...]`, or the existing entry - and its comma - removed. Block
    style (one `key: value` per line, no braces) gets a new `rotate: 180`
    line inserted right after the `at:` line, or that line deleted."""
    if new_rotate == old_rotate:
        return block
    lines = block.split("\n")
    flow = bool(re.match(r"^\s*-\s*\{", lines[0]))
    if new_rotate == 180:
        if flow:
            return re.sub(r"(at: \[[^\]\n]*\])", r"\1, rotate: 180", block, count=1)
        indent = (len(lines[1]) - len(lines[1].lstrip(" ")) if len(lines) > 1
                  else len(lines[0]) - len(lines[0].lstrip(" ")) + 2)
        for i, l in enumerate(lines):
            if re.search(r"\bat:\s*\[", l):
                lines.insert(i + 1, " " * indent + "rotate: 180")
                break
        return "\n".join(lines)
    if flow:
        new = re.sub(r",\s*rotate: 180\b", "", block, count=1)
        if new == block:
            new = re.sub(r"rotate: 180,\s*", "", block, count=1)
        return new
    return "\n".join(l for l in lines if not re.match(r"^\s*rotate:\s*180\s*$", l))


def derived_aperture(ref, jack_at, rot):
    """The (at, size) the aperture ref presents when placed at jack_at, via
    lint's own `_aperture_of` - the same recipe L63 uses to say what a cutout
    should be. None if the ref declares no aperture, or if rot is a rotation
    this tool has not verified: L63 folds w/h for 90/270 because the standard
    aperture is centred in its part; this tool does not attempt that fold for
    an arbitrary composed offset, so it reports rather than guesses."""
    if rot not in (0, 180):
        return None
    ap = L._aperture_of(ref, ROOTS)
    if not ap:
        return None
    (aw, ah), (ax, ay) = ap
    return (round(jack_at[0] + ax, 2), round(jack_at[1] + ay, 2)), (round(aw, 2), round(ah, 2))


def skins_of(ref):
    cp = L.resolve_component(ref, ROOTS)
    return (L.load_yaml(cp) or {}).get("skins") or []


def _drop_skin(text, value):
    """Remove a ` skin: <value>` entry from a flow mapping, keeping the
    remaining commas valid whether it sat mid-list (comma before it, the
    common case) or was the mapping's first field (comma after it instead)."""
    new = re.sub(rf",\s*skin: {re.escape(value)}\b", "", text, count=1)
    if new == text:
        new = re.sub(rf"skin: {re.escape(value)},\s*", "", text, count=1)
    return new


def _squote(text):
    """Single-quoted YAML scalar, doubling any embedded single quote."""
    return "'" + text.replace("'", "''") + "'"


def _set_description(block, quoted):
    """Write `quoted` as the item's `description:` field: extend the
    existing single-quoted scalar in place if there is one (it may wrap
    several lines, per house style), else add a new field next to where
    `states:` is spliced in - before the item's own closing `}` for a flow
    mapping, or as a new line at the item's field indent for a block one."""
    m = re.search(r"description:\s*'(?:[^']|'')*'", block, flags=re.DOTALL)
    if m:
        return block[:m.start()] + f"description: {quoted}" + block[m.end():]
    lines = block.split("\n")
    if re.match(r"^\s*-\s*\{", lines[0]):
        idx = block.rstrip().rfind("}")
        return block[:idx] + f", description: {quoted}" + block[idx:]
    field_indent = (len(lines[1]) - len(lines[1].lstrip(" "))
                    if len(lines) > 1 else
                    len(lines[0]) - len(lines[0].lstrip(" ")) + 2)
    lines.append(" " * field_indent + f"description: {quoted}")
    return "\n".join(lines)


def bump(version, level):
    a, b, c = (int(x) for x in version.split("."))
    return f"{a + 1}.0.0" if level == "major" else f"{a}.{b + 1}.0"


def sweep_device(path):
    data = yaml.safe_load(open(path))
    rows = pathlib.Path(path).read_text().split("\n")
    groups = data.get("groups") or {}
    report = collections.Counter()
    removed_ids, unresolved, moved_ids = [], [], []
    lifted_lamp_groups = set()          # groups a lifted lamp belonged to - ruling C
    for vname, view in (data.get("views") or {}).items():
        pl = (((view or {}).get("components") or {}).get("placements")) or []
        by_id = {str(q["id"]): q for q in pl}
        moves = {}
        for q in pl:
            ref = str(q.get("ref") or "")
            new = target(ref, L.rj45_wants_lamps(q, groups))
            if new:
                moves[str(q["id"])] = (ref, new)
        # A jack's lamps may be drawn INSIDE its footprint (composed into the
        # part - lift them) or BESIDE it (separate placements drawn next to a
        # bare jack, e.g. edgecore/as5912-54x mgmt-eth on rj45-bezel@2 with
        # led-mgmt-lnk/led-mgmt-act at fixed points beside it). Deciding by
        # role alone moved such a jack onto the LAMPED part, doubling its
        # lamps on screen. Controller ruling: any lamp OUTSIDE the jack's old
        # footprint forces that jack to the BARE target regardless of role,
        # and nothing is lifted from it; lamps only inside are unchanged
        # (lifted, lamped); lamps both inside and outside are reported by
        # hand rather than guessed at.
        inside = collections.defaultdict(list)          # jack id -> [(x, lamp placement)]
        outside = collections.defaultdict(list)
        for q in pl:
            f = q.get("for")
            targets = f if isinstance(f, list) else [f]
            if cls(str(q.get("ref") or "")) != "led":
                continue
            for t in targets:
                t = str(t)
                if t in moves and t in by_id:
                    jx, jy = by_id[t]["at"]; jw, jh = size(moves[t][0])
                    if (by_id[t].get("rotate") or 0) % 180 == 90:
                        jw, jh = jh, jw
                    x, y = q["at"]
                    tol = LAMP_EDGE_TOL
                    in_box = (jx - tol <= x <= jx + jw + tol) and (jy - tol <= y <= jy + jh + tol)
                    (inside if in_box else outside)[t].append((x, q))
        external_ids = set()
        lifted = {}
        for pid in list(moves):
            has_in, has_out = bool(inside.get(pid)), bool(outside.get(pid))
            if has_out:
                old = moves[pid][0]
                moves[pid] = (old, target(old, False))          # bare, regardless of role
                external_ids.add(pid)
                if has_in:
                    unresolved.append(f"{pid}: lamps both inside and outside the jack - decide by hand")
            elif has_in and moves[pid][1].startswith("common/"):
                lifted[pid] = inside[pid]
        # 1-2. move jacks, holding centres; 3. write lifted states onto them
        failed = set()
        final_rotates = {}          # pid -> rotate AFTER any FLIP_ORIGIN flip
        for pid, (old, new) in moves.items():
            lo, hi = view_bounds(rows, vname)   # recomputed each time: earlier
            s = span(rows, pid, lo, hi)         # edits in this view shift lines
            if not s:
                unresolved.append(f"{vname}/{pid}: no placement line")
                failed.add(pid)
                continue
            (ow, oh), (nw, nh) = size(old), size(new)
            block = "\n".join(rows[s[0]:s[1] + 1])
            block = block.replace(f"ref: {old}", f"ref: {new}", 1)
            block = edit_at(block, (ow - nw) / 2, (oh - nh) / 2)
            # A jack moved off a FLIP_ORIGIN part turns over: the new part's
            # keyway-down default is the OLD part's keyway-up default rotated
            # 180, so the placement's own rotate must gain (or lose) that 180
            # to keep drawing the same, already-verified face.
            old_rotate = (by_id[pid].get("rotate") or 0) % 360
            new_rotate = (old_rotate + 180) % 360 if old in FLIP_ORIGIN else old_rotate
            if new_rotate != old_rotate:
                block = flip_rotate(block, old_rotate, new_rotate)
                report["rotation flipped"] += 1
            final_rotates[pid] = new_rotate
            # B. a skin the new part does not declare cannot be asked for -
            # all four new parts declare skins: [default], so any other skin
            # a swept placement named (e.g. common/rj45-bezel@2's `dark`) is
            # gone with the part it belonged to.
            skin = by_id[pid].get("skin")
            if skin and str(skin) not in skins_of(new):
                block = _drop_skin(block, str(skin))
                report["skin dropped"] += 1
            if lifted.get(pid):
                lamps = sorted(lifted[pid], key=lambda t: t[0])
                # led-a is the component's LOCAL left window. Unrotated, the
                # lower-x lamp maps to led-a. A jack rotated 180 presents that
                # local-left window on screen-right, so the mapping flips:
                # lower-x -> led-b. Any other rotation is outside what the
                # corpus has verified - report it rather than guess. Uses the
                # FINAL rotate (after any FLIP_ORIGIN flip above), since that
                # is the orientation the NEW part actually draws.
                rot = final_rotates.get(pid, (by_id[pid].get("rotate") or 0) % 360)
                if rot == 180:
                    order = ("led-b", "led-a")
                elif rot == 0:
                    order = ("led-a", "led-b")
                else:
                    order = ("led-a", "led-b")
                    unresolved.append(
                        f"{vname}/{pid}: rotate {rot} - lamp handedness not verified for this rotation")
                mapping = {}
                for name, (_, lamp) in zip(order, lamps):
                    if lamp.get("states"):
                        mapping[name] = lamp["states"]
                    elif (lamp.get("attrs") or {}).get("function"):
                        mapping[name] = ["off", {"name": lamp["attrs"]["function"]}]
                if mapping:
                    inline = yaml.safe_dump(mapping, default_flow_style=True, width=10 ** 6).strip()
                    lines = block.split("\n")
                    if re.match(r"^\s*-\s*\{", lines[0]):
                        # flow mapping on one or more rows: splice before the
                        # final closing brace
                        block = block[:block.rstrip().rfind("}")] + f", states: {inline}" + "}"
                    else:
                        # block mapping, one `key: value` per line: append a
                        # new line at the same indent as the item's own fields
                        field_indent = (len(lines[1]) - len(lines[1].lstrip(" "))
                                        if len(lines) > 1 else
                                        len(lines[0]) - len(lines[0].lstrip(" ")) + 2)
                        lines.append(" " * field_indent + f"states: {inline}")
                        block = "\n".join(lines)
                # A lifted lamp's description names the HIG table (or its
                # absence) its states came from - dropping it loses that
                # provenance with no way to recover it from the file. Carry
                # it onto the jack, in ascending-x (not led-a/led-b) order,
                # appended after any description the jack already has.
                descs = [(lamp["id"], lamp["description"]) for _, lamp in lamps if lamp.get("description")]
                if descs:
                    carried = "; ".join(f"{lid}: {text}" for lid, text in descs)
                    existing = by_id[pid].get("description")
                    merged = f"{existing}; {carried}" if existing else carried
                    block = _set_description(block, _squote(merged))
                    report["descriptions carried"] += len(descs)
            rows[s[0]:s[1] + 1] = block.split("\n")
            report["lamped" if new.startswith("common/") else "bare"] += 1
            if pid in external_ids:
                report["external-lamps"] += 1
            moved_ids.append(pid)
        # 3b. remove the lifted lamps - only for jacks whose own move succeeded;
        # a jack we could not rewrite must not lose the lamps it still draws
        for pid, lamps in lifted.items():
            if pid in failed:
                continue
            for _, lamp in lamps:
                lo, hi = view_bounds(rows, vname)
                s = span(rows, str(lamp["id"]), lo, hi)
                if s:
                    del rows[s[0]:s[1] + 1]
                    removed_ids.append(str(lamp["id"])); report["lamps lifted"] += 1
                    g = lamp.get("group")
                    if g is not None:
                        lifted_lamp_groups.add(str(g))
        # 5. cutouts. Most RJ45 cutouts were DERIVED from the old part - `at`
        # is the jack's own `at` plus the old part's aperture offset, `size`
        # is the old aperture's size, both via lint's `_aperture_of` - within
        # 0.15mm of slop. Held to its own centre regardless, such a cutout
        # rides its offset to wherever the OLD part happened to put it; move
        # the jack onto a new part whose aperture offset is (0, 0) and the
        # held centre lands 0.05-0.1mm off the new derived aperture, which
        # trips L63. So a DERIVED cutout is RE-DERIVED from the new part
        # instead: recompute the aperture the new part presents at the jack's
        # new position. A cutout that does not match the old derived aperture
        # is INFORMATIVE (celestica/es1010 port-1: cutout [12.7, 11] already
        # matches the new part even though the old part is [14, 12] - nothing
        # here was ever derived from the old part, so its own centre holds,
        # same as before this ruling).
        for pid, (old, new) in moves.items():
            lo, hi = view_bounds(rows, vname)
            s = cutout_span(rows, pid, lo, hi)
            if not s:
                continue
            nw, nh = size(new)
            line = rows[s[0]]
            m = re.search(r"size: \[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]", line)
            if m:
                cow, coh = float(m.group(1)), float(m.group(2))
            else:
                m = re.search(r"size: \{w: ([\d.]+), h: ([\d.]+)\}", line)
                cow, coh = float(m.group(1)), float(m.group(2))
            cat = read_at(line)
            rot = (by_id[pid].get("rotate") or 0) % 360
            if rot not in (0, 180):
                unresolved.append(f"{vname}/{pid}: rotate {rot} - cutout derivation not verified "
                                   f"for this rotation")
            old_da = derived_aperture(old, tuple(by_id[pid]["at"]), rot)
            derived = (old_da is not None
                       and abs(old_da[0][0] - cat[0]) <= 0.15 and abs(old_da[0][1] - cat[1]) <= 0.15
                       and abs(old_da[1][0] - cow) <= 0.15 and abs(old_da[1][1] - coh) <= 0.15)
            if derived:
                # the jack's own move already landed in rows - read its NEW
                # `at` back off the file rather than re-deriving the arithmetic
                js = span(rows, pid, lo, hi)
                new_jack_at = read_at("\n".join(rows[js[0]:js[1] + 1])) if js else tuple(by_id[pid]["at"])
                new_da = derived_aperture(new, new_jack_at, rot)
                nat, nsz = new_da
                line = re.sub(r"size: \[\s*[\d.]+\s*,\s*[\d.]+\s*\]", f"size: [{fmt(nsz[0])}, {fmt(nsz[1])}]", line)
                line = re.sub(r"size: \{w: [\d.]+, h: [\d.]+\}", f"size: [{fmt(nsz[0])}, {fmt(nsz[1])}]", line)
                line = re.sub(r"at: \[\s*-?[\d.]+\s*,\s*-?[\d.]+\s*\]", f"at: [{fmt(nat[0])}, {fmt(nat[1])}]", line)
                rows[s[0]] = line
                report["cutouts re-derived"] += 1
            else:
                line = re.sub(r"size: \[\s*[\d.]+\s*,\s*[\d.]+\s*\]", f"size: [{fmt(nw)}, {fmt(nh)}]", line)
                line = re.sub(r"size: \{w: [\d.]+, h: [\d.]+\}", f"size: [{fmt(nw)}, {fmt(nh)}]", line)
                rows[s[0]] = edit_at(line, (cow - nw) / 2, (coh - nh) / 2)
                report["cutouts held"] += 1
    text = "\n".join(rows)
    # 4. legends: a `for:` naming a removed lamp names the jack instead. The
    # lamp's `for:` said which jack it belonged to; read it off the ORIGINAL
    # data (the rewritten text no longer has the lamp placement to ask).
    if removed_ids:
        owner = {}
        for view in (data.get("views") or {}).values():
            for q in (((view or {}).get("components") or {}).get("placements") or []):
                if str(q.get("id")) in removed_ids:
                    f = q.get("for"); owner[str(q["id"])] = str(f[0] if isinstance(f, list) else f)
        # A `\b` boundary treats `-` as a word break, so `led-oob-left\b`
        # matches the PREFIX of `led-oob-left-2` too. Require instead that the
        # next character actually end the id: a list/scalar delimiter,
        # whitespace, or end of line.
        for lid, jack in owner.items():
            n = len(re.findall(rf"for: {re.escape(lid)}{BOUND}", text, flags=re.M))
            text = re.sub(rf"for: {re.escape(lid)}{BOUND}", f"for: {jack}", text, flags=re.M)
            text = re.sub(rf"(for: \[[^\]]*?){re.escape(lid)}{BOUND}", rf"\1{jack}", text)
            report["legends re-pointed"] += n
            for key in ("members", "scope", "combo-with"):
                if re.search(rf"{key}:[^\n]*\b{re.escape(lid)}\b", text):
                    unresolved.append(f"{key} still names removed lamp {lid}")
        # Two lifted lamps that both belonged to the same jack now name that
        # jack twice in a `for: [...]` list (e.g. `for: [mgmt-eth, mgmt-eth]`);
        # collapse to one entry.
        def _dedup_for_list(m):
            seen = []
            for item in m.group(1).split(","):
                item = item.strip()
                if item not in seen:
                    seen.append(item)
            return "for: [" + ", ".join(seen) + "]"
        text = re.sub(r"for: \[([^\]]*)\]", _dedup_for_list, text)
    # C. a group emptied by lifting is reported, not removed - dropping a
    # group id is its own major bump (devicelock's "ids or groups" rule) and
    # a human should choose whether the group goes or gains a new member,
    # not this tool.
    for name in sorted(lifted_lamp_groups):
        if name in groups and not re.search(rf"group: {re.escape(name)}{BOUND}", text):
            unresolved.append(f"group {name} has no members after lifting - remove it by "
                               f"hand (a group removal is a major bump)")
    # 6. version
    if removed_ids or report["lamped"] or report["bare"]:
        level = "major" if removed_ids else "minor"
        text = re.sub(r"^version: (\S+)$", lambda m: f"version: {bump(m.group(1), level)}", text, count=1, flags=re.M)
        report[f"bump {level}"] = 1
    return text, report, unresolved, moved_ids


def sweep_component(path):
    data = yaml.safe_load(open(path))
    rows = pathlib.Path(path).read_text().split("\n")
    report = collections.Counter()
    moved_ids, unresolved = [], []
    for p in data.get("parts") or []:
        ref = str(p.get("ref") or "")
        new = target(ref, L.rj45_wants_lamps({"id": p.get("id"), "attrs": p.get("attrs")}, {},
                                      data.get("name")))
        if not new:
            continue
        s = span(rows, str(p["id"]))
        if not s:
            # matches sweep_device's own behaviour: a part that should move but
            # whose placement line couldn't be found is reported, not silently
            # dropped - otherwise the report would understate what's left to do.
            unresolved.append(f"{p['id']}: no parts line")
            continue
        (ow, oh), (nw, nh) = size(ref), size(new)
        block = "\n".join(rows[s[0]:s[1] + 1]).replace(f"ref: {ref}", f"ref: {new}", 1)
        block = edit_at(block, (ow - nw) / 2, (oh - nh) / 2)
        # Same FLIP_ORIGIN turnover as sweep_device, for a `parts:` entry.
        old_rotate = (p.get("rotate") or 0) % 360
        new_rotate = (old_rotate + 180) % 360 if ref in FLIP_ORIGIN else old_rotate
        if new_rotate != old_rotate:
            block = flip_rotate(block, old_rotate, new_rotate)
            report["rotation flipped"] += 1
        rows[s[0]:s[1] + 1] = block.split("\n")
        report["parts moved"] += 1
        moved_ids.append(str(p["id"]))
    text = "\n".join(rows)
    if report["parts moved"]:
        text = re.sub(r"^version: (\S+)$", lambda m: f"version: {bump(m.group(1), 'minor')}", text, count=1, flags=re.M)
    return text, report, unresolved, moved_ids


files = (sorted(glob.glob(f"{LIB}/components/*/*/v*/contract.yaml")) if ARGS.components
         else sorted(glob.glob(f"{ARGS.devices or LIB + '/devices'}/*/*/device.yaml")))
for path in files:
    if ARGS.only and not any(o in path for o in ARGS.only):
        continue
    if ARGS.components and is_retired_wrapper(path):
        # These wrapper contracts are deleted whole in a later task; sweeping
        # their internal jack now would move it out from under the file
        # that's about to disappear. Skip entirely - report nothing.
        continue
    text, report, unresolved, moved_ids = (sweep_component if ARGS.components else sweep_device)(path)
    if not report and not unresolved:
        continue
    ids = f" [{', '.join(moved_ids)}]" if moved_ids else ""
    print(f"{path}:{ids} " + ", ".join(f"{k} {v}" for k, v in sorted(report.items())))
    for u in unresolved:
        print(f"  ! {u}")
    if ARGS.apply:
        pathlib.Path(path).write_text(text)

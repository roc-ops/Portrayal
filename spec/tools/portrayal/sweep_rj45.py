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


def bump(version, level):
    a, b, c = (int(x) for x in version.split("."))
    return f"{a + 1}.0.0" if level == "major" else f"{a}.{b + 1}.0"


def sweep_device(path):
    data = yaml.safe_load(open(path))
    rows = pathlib.Path(path).read_text().split("\n")
    groups = data.get("groups") or {}
    report = collections.Counter()
    removed_ids, unresolved, moved_ids = [], [], []
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
                    (inside if jx <= x <= jx + jw and jy <= y <= jy + jh else outside)[t].append((x, q))
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
            if lifted.get(pid):
                lamps = sorted(lifted[pid], key=lambda t: t[0])
                # led-a is the component's LOCAL left window. Unrotated, the
                # lower-x lamp maps to led-a. A jack rotated 180 presents that
                # local-left window on screen-right, so the mapping flips:
                # lower-x -> led-b. Any other rotation is outside what the
                # corpus has verified - report it rather than guess.
                rot = (by_id[pid].get("rotate") or 0) % 360
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
        # 5. cutouts. The anchor holds the CUTOUT's own centre, not the jack
        # part's: read the cutout's own old size off its `size:` field before
        # rewriting it, and shift by (old cutout size - new part size) / 2. A
        # cutout can be a different size than the part it houses (bezel
        # clearance, etc) - using the part's old/new sizes here would move a
        # hole whose size never changes at all (celestica/es1010 port-1:
        # cutout [12.7, 11] already matches the new part even though the old
        # part is [14, 12] - the hole must not move).
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
            line = re.sub(r"size: \[\s*[\d.]+\s*,\s*[\d.]+\s*\]", f"size: [{fmt(nw)}, {fmt(nh)}]", line)
            line = re.sub(r"size: \{w: [\d.]+, h: [\d.]+\}", f"size: [{fmt(nw)}, {fmt(nh)}]", line)
            rows[s[0]] = edit_at(line, (cow - nw) / 2, (coh - nh) / 2)
            report["cutouts resized"] += 1
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
        BOUND = r"(?=[,\]}\s]|$)"
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
        new = target(ref, L.rj45_wants_lamps({"id": p.get("id"), "attrs": p.get("attrs")}, {}))
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
        rows[s[0]:s[1] + 1] = edit_at(block, (ow - nw) / 2, (oh - nh) / 2).split("\n")
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

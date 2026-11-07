#!/usr/bin/env python3
"""Measure which longhand devices `expand.py` could write, and why the rest cannot.

WHY THIS EXISTS. A hand-kept count of "longhand devices" goes stale within a day
and says nothing about WHY a block does not fit the generator. This reads every
`device.yaml` and, for each view, each block of eight or more placements that
share a `ref` and a `group`, asks the questions `expand.py`'s `block_items` asks of
a layout: is it a full grid of columns by rows, with at most two x gaps (the
pitch, and the pitch plus a gutter on a regular gang), one row gap, a rotation that
is constant along a row and that differs only between the top row and the others,
numbered column-major from a first number, with `rel-pos` equal to the number in
its id, and written in the order `block_items` emits.

A LAMP BLOCK (placements carrying `for:`) is first folded into the port block it
names, because `expand.py` writes lamps from that port block's `led:` key
(`dx-by-col`, `dx-by-row`, `rel-pos-stride`, `rel-pos-offset`).

It decides nothing about a drawing: a fit here is a hint about where to look, and a
conversion is real only when `expand.py` reproduces the parsed device (and
`expand.py --check` says so). Tolerance is 0.015 mm, the rounding the files carry.

    python3 spec/tools/dev/layout_fit.py                  # the summary tables
    python3 spec/tools/dev/layout_fit.py --device ufispace/s9110-32x
    python3 spec/tools/dev/layout_fit.py --json           # one record per device
"""
import argparse
import collections
import json
import pathlib
import re
import statistics
import sys

import yaml

from portrayal import libwalk

try:
    _Loader = yaml.CSafeLoader
except AttributeError:  # pragma: no cover - libyaml absent
    _Loader = yaml.SafeLoader

TOL = 0.015
MIN_BLOCK = 8
EXTRA = collections.Counter()   # placement keys expand.py does not write, by count
PORT_KEYS = {"ref", "id", "at", "rotate", "group", "rel-pos", "attrs"}
LAMP_KEYS = {"ref", "id", "at", "group", "rel-pos", "for", "states", "skin"}

# What each optional extension of expand.py would cure. A block is cured by a set of
# extensions when every one of its reasons is in the union they cover.
EXTENSIONS = {
    "row-list": {"row-gaps", "rotation"},        # a per-row pitch and rotation list
    "row-major": {"row-major"},                  # row-major numbering
    "id-offset": {"relpos-offset"},              # an id offset independent of rel-pos
    # lamps (and numerals) as blocks of their own: a lamp block is no longer emitted
    # inside its port block, so the file order of the two may differ, and a lamp
    # block may carry the keys a lamp has beyond what `led:` writes
    "lamp-blocks": {"lamp-after-port", "lamp-extra-keys"},
}


def _num(pid):
    m = re.search(r"(\d+)\D*$", str(pid))
    return int(m.group(1)) if m else None


def _cluster(values, tol=TOL):
    """Sorted distinct values, merging any that sit within `tol` of the last."""
    out = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [statistics.fmean(c) for c in out]


def _index(centres, v):
    return min(range(len(centres)), key=lambda i: abs(centres[i] - v))


def _gaps(centres):
    return [b - a for a, b in zip(centres, centres[1:])]


def _distinct(gaps, tol=0.03):
    return _cluster(gaps, tol)


def _fit_x(cols):
    """pitch / gutter / gang for column centres, or None if two gaps do not do."""
    if len(cols) < 2:
        return {"gaps": 0}
    gaps = _gaps(cols)
    kinds = _distinct(gaps)
    if len(kinds) > 2:
        return None
    if len(kinds) == 1:
        return {"gaps": 1, "pitch": kinds[0]}
    pitch = min(kinds)
    gutter = max(kinds) - pitch
    big = [i for i, g in enumerate(gaps) if g - pitch > gutter / 2]
    gang = big[0] + 1
    if big != [gang - 1 + k * gang for k in range(len(big))]:
        return None
    span = cols[-1] - cols[0]
    pitch = (span - len(big) * gutter) / (len(cols) - 1)
    for c, x in enumerate(cols):
        if abs(cols[0] + c * pitch + (c // gang) * gutter - x) > TOL:
            return None
    return {"gaps": 2, "pitch": pitch, "gutter": gutter, "gang": gang}


def port_block(items):
    """items: [(file_index, placement)] -> (reasons, facts) for one port block."""
    reasons, facts = set(), {}
    pls = [p for _, p in items]
    if any(set(p) - PORT_KEYS for p in pls):
        reasons.add("extra-keys")
        for p in pls:
            EXTRA.update(("port:" + k) for k in set(p) - PORT_KEYS)
    nums = [_num(p["id"]) for p in pls]
    if None in nums:
        reasons.add("no-number")
    xs = _cluster(p["at"][0] for p in pls)
    ys = _cluster(p["at"][1] for p in pls)
    cell = collections.defaultdict(list)
    for p in pls:
        cell[(_index(xs, p["at"][0]), _index(ys, p["at"][1]))].append(p)
    if len(cell) != len(xs) * len(ys) or any(len(v) != 1 for v in cell.values()):
        reasons.add("not-full-grid")
    fx = _fit_x(xs)
    if fx is None:
        reasons.add("x-gaps")
    if len(_distinct(_gaps(ys))) > 1:
        reasons.add("row-gaps")
    rows, cols = len(ys), len(xs)
    facts.update(cols=cols, rows=rows)
    # rotation: constant along each row, and top vs the rest only
    per_row = collections.defaultdict(set)
    for (c, r), v in cell.items():
        for p in v:
            per_row[r].add(p.get("rotate", 0))
    if any(len(s) > 1 for s in per_row.values()):
        reasons.add("rot-varies")
    else:
        rot = [next(iter(per_row[r])) for r in range(rows)]
        if len(set(rot[1:])) > 1:
            reasons.add("rotation")
    if "no-number" not in reasons and "not-full-grid" not in reasons:
        first = min(nums)
        colmaj = all(_num(v[0]["id"]) == first + c * rows + r for (c, r), v in cell.items())
        rowmaj = all(_num(v[0]["id"]) == first + r * cols + c for (c, r), v in cell.items())
        if colmaj:
            where = {id(p): fi for fi, p in items}
            seq = [where[id(cell[k][0])] for k in sorted(cell)]
            facts["gen"] = seq
            if seq != list(range(seq[0], seq[0] + len(seq))):
                reasons.add("file-order")
        elif rowmaj:
            reasons.add("row-major")
        else:
            reasons.add("numbering-neither")
        offs = {p.get("rel-pos") - _num(p["id"]) if isinstance(p.get("rel-pos"), int)
                else None for p in pls}
        if offs != {0}:
            reasons.add("relpos-offset" if len(offs) == 1 and None not in offs
                        else "relpos-other")
        facts["first"] = first
        if fx and rows >= 1:
            # a first guess at the block's keys, to be checked by expand.py and not trusted
            sg = {"at": [min(p["at"][0] for p in pls), min(p["at"][1] for p in pls)],
                  "count": len(pls), "rows": rows, "number-from": first}
            if fx.get("pitch") is not None:
                sg["pitch"] = round(fx["pitch"], 3)
            if fx.get("gang"):
                sg.update(gang=fx["gang"], gutter=round(fx["gutter"], 3))
            if rows > 1:
                sg["row-pitch"] = round((ys[-1] - ys[0]) / (rows - 1), 3)
            if "rot" in locals() and "rotation" not in reasons and "rot-varies" not in reasons:
                rt = {k: v for k, v in (("top", rot[0]), ("bottom", rot[-1])) if v}
                if rt:
                    sg["rotate"] = rt
            facts["suggest"] = sg
    return reasons, facts


def lamp_fold(lamps, port_items):
    """Can this lamp block (list of (file_index, lamp)) be written by a port block's
    `led:` key? -> set of reasons (empty means it folds)."""
    reasons, suggest = set(), []
    ports = {p["id"]: p for _, p in port_items}
    pls = [p for _, p in lamps]
    if any(set(p) - LAMP_KEYS for p in pls):
        reasons.add("lamp-extra-keys")
        for p in pls:
            EXTRA.update(("lamp:" + k) for k in set(p) - LAMP_KEYS)
    if any(p.get("for") not in ports for p in pls):
        return {"lamp-for-outside-block"}, []
    if len({json.dumps(p.get("states"), sort_keys=True) for p in pls}) > 1:
        reasons.add("lamp-states-vary")
    # one `led:` entry per lamp of a port: split the block by the lamp's place in its port
    seen = collections.Counter()
    sub = collections.defaultdict(list)
    for p in pls:
        sub[seen[p["for"]]].append(p)
        seen[p["for"]] += 1
    pxs = _cluster(p["at"][0] for p in ports.values())
    pys = _cluster(p["at"][1] for p in ports.values())
    for j, lp in sub.items():
        if len(lp) != len(ports) and len(lp) < len({p["for"] for p in lp}):
            reasons.add("lamp-count")
        dx, dy = {}, collections.defaultdict(set)
        strides = set()
        fmts = set()
        for p in lp:
            port = ports[p["for"]]
            n = _num(port["id"])
            ln = _num(p["id"])
            if n is None or ln != n:
                reasons.add("lamp-id-number")
                continue
            fmts.add(re.sub(r"(\d+)(\D*)$", r"{n}\2", str(p["id"])))
            c, r = _index(pxs, port["at"][0]), _index(pys, port["at"][1])
            dx[(c, r)] = p["at"][0] - port["at"][0]
            dy[0 if r == 0 else 1].add(round(p["at"][1] - port["at"][1], 2))
            strides.add(p.get("rel-pos", 0) - 0 * n)
        if len(fmts) > 1:
            reasons.add("lamp-id-number")
        if any(max(v) - min(v) > TOL for v in dy.values()):
            reasons.add("lamp-dy")
        # dx = by_col[c % L] + by_row[r % Lr]: take rows against row 0
        rowset = sorted({r for _, r in dx})
        base = {c: dx[(c, rowset[0])] for c, r in dx if r == rowset[0]}
        for r in rowset[1:]:
            ds = {round(dx[(c, r)] - base[c], 2) for c in base if (c, r) in dx}
            if len(ds) > 1 and max(ds) - min(ds) > TOL:
                reasons.add("lamp-dx")
        seq = [base[c] for c in sorted(base)]
        period = next((L for L in range(1, max(1, len(seq) // 2) + 1)
                       if all(abs(seq[i] - seq[i % L]) <= TOL for i in range(len(seq)))), None)
        if seq and period is None:
            reasons.add("lamp-dx")
        if seq and period:
            by_row = [0.0] + [round(statistics.fmean([dx[(c, r)] - base[c] for c in base
                                                      if (c, r) in dx] or [0.0]), 2)
                              for r in rowset[1:]]
            sg = {"ref": lp[0]["ref"], "id-format": next(iter(fmts)) if fmts else None,
                  "group": lp[0].get("group"),
                  "dx-by-col": [round(v, 2) for v in seq[:period]],
                  "dy-top": round(statistics.fmean(dy[0]), 2) if dy[0] else None}
            if any(by_row):
                sg["dx-by-row"] = by_row
            if dy[1]:
                sg["dy-bottom"] = round(statistics.fmean(dy[1]), 2)
            if lp[0].get("states"):
                sg["states"] = "same as the lamps"
            suggest.append(sg)
        # rel-pos = n * stride + offset, same for every lamp of the block
        pairs = {(_num(ports[p["for"]]["id"]), p.get("rel-pos")) for p in lp}
        pairs = sorted(pairs)
        if len(pairs) > 1 and all(isinstance(b, int) for _, b in pairs):
            stride = pairs[1][1] - pairs[0][1]
            dn = pairs[1][0] - pairs[0][0]
            if dn == 0 or stride % dn or any(
                    b - (a - pairs[0][0]) * (stride // dn) != pairs[0][1] for a, b in pairs):
                reasons.add("lamp-rel-pos")
            elif suggest and len(pairs) > 1:
                suggest[-1]["rel-pos-stride"] = stride // dn
                suggest[-1]["rel-pos-offset"] = pairs[0][1] - pairs[0][0] * (stride // dn)
    return reasons, suggest


def measure_device(doc):
    """-> list of block records for one device."""
    out = []
    for vname, view in (doc.get("views") or {}).items():
        pls = ((view.get("components") or {}).get("placements")) or []
        groups = collections.defaultdict(list)
        for i, p in enumerate(pls):
            if isinstance(p, dict) and "ref" in p and "at" in p:
                groups[(p["ref"], p.get("group"))].append((i, p))
        blocks = {k: v for k, v in groups.items() if len(v) >= MIN_BLOCK}
        lamp_keys = {k for k, v in blocks.items() if all("for" in p for _, p in v)}
        port_of = {}
        for k, v in blocks.items():
            if k in lamp_keys:
                continue
            for _, p in v:
                port_of[p["id"]] = k
        recs = {}
        for k, v in blocks.items():
            rec = {"view": vname, "ref": k[0], "group": k[1], "count": len(v)}
            if k in lamp_keys:
                owners = {port_of.get(p["for"]) if isinstance(p["for"], str) else None
                          for _, p in v}
                if len(owners) == 1 and None not in owners:
                    owner = owners.pop()
                    rec["kind"] = "lamp"
                    rec["folds-into"] = list(owner)
                    why, suggest = lamp_fold(v, blocks[owner])
                    rec["reasons"] = sorted(why)
                    rec["facts"] = {"order": _lamp_order(v, blocks[owner]),
                                    "suggest-led": suggest}
                    recs[k] = rec
                    out.append(rec)
                    continue
                rec["kind"] = "lamp-unfolded"
            else:
                rec["kind"] = "port"
            reasons, facts = port_block(v)
            rec["reasons"] = sorted(reasons)
            rec["facts"] = facts
            recs[k] = rec
            out.append(rec)
        # `expand.py` writes a port block's lamps right after its ports, so a lamp
        # run must follow the port run in the file (and be one run, in port order)
        folded = collections.defaultdict(list)
        for rec in recs.values():
            if rec["kind"] == "lamp":
                folded[tuple(rec["folds-into"])].append(rec)
        for owner, lamps in folded.items():
            gen = recs[owner]["facts"].get("gen")
            if not gen:
                continue
            for rec in lamps:
                seq = rec["facts"]["order"]
                if seq != list(range(seq[0], seq[0] + len(seq))):
                    rec["reasons"] = sorted(set(rec["reasons"]) | {"lamp-file-order"})
                elif len(lamps) > 1 or seq[0] != gen[-1] + 1 or gen != list(range(gen[0], gen[-1] + 1)):
                    rec["reasons"] = sorted(set(rec["reasons"]) | {"lamp-after-port"})
    return out


def _lamp_order(lamps, port_items):
    """File indices of a lamp block in the order `expand.py` writes them: by port
    number, then by the lamp's place within its port."""
    num = {p["id"]: _num(p["id"]) for _, p in port_items}
    seen = collections.Counter()
    keyed = []
    for i, p in lamps:
        keyed.append(((num.get(p["for"]) or 0, seen[p["for"]]), i))
        seen[p["for"]] += 1
    return [i for _, i in sorted(keyed)]


IGNORE = set()


def classify(blocks, covered=frozenset(), fold_lamps=True):
    """'all' | 'part' | 'none' | 'no-blocks' for a device's block records.

    Without folding, a lamp block is judged as a port block on its own, and a
    lamp block that is not a regular grid fails for it."""
    if not blocks:
        return "no-blocks"
    ok = []
    for b in blocks:
        rs = set(b["reasons"]) - IGNORE
        if b["kind"] == "lamp" and not fold_lamps:
            rs = {r for r in rs if not r.startswith("lamp-")} | {"x-gaps"}
        ok.append(rs <= covered)
    if all(ok):
        return "all"
    return "part" if any(ok) else "none"


def load_devices(library):
    devs = {}
    for dp in libwalk.iter_devices([library]):
        key = f"{dp.parts[-3]}/{dp.parts[-2]}"
        devs[key] = (yaml.load(dp.read_text(), Loader=_Loader),
                     (dp.parent / "layout.yaml").exists())
    return devs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", default="library", type=pathlib.Path)
    ap.add_argument("--device", help="vendor/model: print its blocks and reasons")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lenient", action="store_true",
                    help="ignore extra keys and file order: the grid, gap, rotation, "
                         "numbering and rel-pos tests only")
    ap.add_argument("--only", help="comma-separated extension sets to print, e.g. "
                                   "'lamp-blocks,row-list+lamp-blocks' ('' is as it stands)")
    ap.add_argument("--names", action="store_true",
                    help="list the devices each extension converts in full")
    a = ap.parse_args()

    if a.lenient:
        IGNORE.update({"extra-keys", "file-order"})
    devs = load_devices(a.library)
    if a.device:
        blocks = measure_device(devs[a.device][0])
        for b in blocks:       # the file indices are for the order check, not for reading
            (b.get("facts") or {}).pop("gen", None)
            (b.get("facts") or {}).pop("order", None)
        print(json.dumps(blocks, indent=1, default=str))
        return 0
    rec = {k: {"layout": lay, "blocks": measure_device(doc)} for k, (doc, lay) in devs.items()}
    if a.json:
        print(json.dumps(rec, indent=1, default=str))
        return 0

    longhand = {k: v for k, v in rec.items() if not v["layout"]}
    withlay = [k for k, v in rec.items() if v["layout"]]
    print(f"devices {len(rec)}; with layout.yaml {len(withlay)}; without {len(longhand)}")
    rep = {k: v for k, v in longhand.items() if v["blocks"]}
    print(f"longhand devices with at least one block of {MIN_BLOCK}+: {len(rep)}")
    for fold in (False, True):
        c = collections.Counter(classify(v["blocks"], fold_lamps=fold) for v in rep.values())
        print(f"as it stands, lamps {'folded' if fold else 'not folded'}: "
              f"all fit {c['all']}, part {c['part']}, none {c['none']}")
    why = collections.Counter(r for v in rep.values() for b in v["blocks"] for r in b["reasons"])
    whyp = collections.Counter(r for v in rep.values() for b in v["blocks"]
                               if b["kind"] != "lamp" for r in b["reasons"])
    print("reasons, in blocks (lamps folded into their port blocks):")
    for r, n in why.most_common():
        print(f"  {r:24} {n:4}   (port and unfolded blocks only: {whyp[r]})")
    print("keys on a placement that expand.py does not write (placements):")
    for k, n in EXTRA.most_common(12):
        print(f"  {k:24} {n:5}")
    print("devices converted in full, by extension (lamps folded):")
    names = list(EXTENSIONS)
    import itertools
    for size in range(0, len(names) + 1):
        for combo in itertools.combinations(names, size):
            if a.only is not None and "+".join(combo) not in a.only.split(","):
                continue
            cov = set().union(*(EXTENSIONS[n] for n in combo)) if combo else set()
            c = collections.Counter(classify(v["blocks"], frozenset(cov)) for v in rep.values())
            print(f"  {'+'.join(combo) or 'none (as it stands)':32} all {c['all']:3}  part {c['part']:3}  none {c['none']:3}")
            if a.names:
                for k, v in rep.items():
                    if classify(v["blocks"], frozenset(cov)) == "all":
                        print(f"      {k}  ({', '.join(str(b['count']) for b in v['blocks'])} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

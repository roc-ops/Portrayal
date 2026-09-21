"""Belly-to-belly cage stacks: which cages pair, and which way each one faces.

ONE IMPLEMENTATION, READ BY LINT L108 AND BY ITS TESTS, so the rule and the
census that checks the rule cannot disagree about what a pair is.

THE CONVENTION (docs/pluggables-3d-design.md, the stacked-cage decisions of
2026-09-21). A pluggable cage's `rotate: 0` means the module seats upright:
bail / pull tab at the top, belly and cage latch at the bottom. Every std cage
skin draws its `cage-lip` at the bottom of the opening to say so. In a real
belly-to-belly stack the two modules' bellies face each other across the band
between them and both bails face OUTWARD, where a thumb reaches them. So:

    a row pair    (cages turned 0/180)   upper 0,   lower 180
    a column pair (cages turned 90/270)  left 270,  right 90

`rotate: 90` turns an upright cage's bail from the top to the right (SVG turns
clockwise), 270 to the left - which is why a left/right pair on a card drawn on
its side is 270 beside 90, and not 90 beside 90.

WHAT PAIRS. Two cages of one face family whose bellies face each other: turned
the same way round the belly axis, overlapping across it, and the nearest such
cage along it. A row pair stacks in y, a column pair in x. A cage turned 90
beside a cage turned 0 is not a pair - they have no common belly axis, and a
card whose cages sit side by side for some other reason is not forced into
one. Pairing is greedy from the top-left, which is right for every stack the
library has: two-high rows and two-wide columns, repeated.

QSFP AND QSFP-DD ARE ONE FACE FAMILY - they share the bezel opening, and a QSFP
cage over a QSFP-DD cage (cisco/asr-9902) stacks belly-to-belly like any other.

OSFP IS NOT CHECKED. std/osfp@1's skin draws a latch slot at the bottom and its
lip at the top, which may be a different convention from the other cages', and
no OSFP generic exists to seat in one. It is left as drawn until that is
settled, and `SKIPPED` says so wherever it matters.

AN EXCEPTION IS DECLARED BY THE PAIR, with a reason, in `stack-exceptions:` - a
top-level list in a device manifest (or the layout.yaml it is generated from)
and in a component contract:

    stack-exceptions:
      - pair: [port-2, port-3]
        reason: >-
          both lamps point up, so neither cage is turned ...

Several pairs that share one reason go in one entry as `pairs: [[a, b], [c, d]]`.
A device may add `view:` where the same ids pair in more than one view. An
entry naming ids that are not a checked pair is itself a finding, so an
exception cannot outlive the stack it excused.
"""

# face family by presented interface; anything not here is out of scope
FAMILY = {"sfp": "sfp", "qsfp": "qsfp", "qsfp-dd": "qsfp"}
# interfaces a stack of which is deliberately not checked, and why
SKIPPED = {"osfp": "std/osfp@1 draws its latch slot at the bottom and its lip at "
                   "the top, which may be a different convention, and no OSFP "
                   "generic exists to seat; OSFP stacks are left as drawn"}

EPS = 0.05          # mm - touching neighbours in adjacent columns are not overlapping
OVERLAP = 0.6       # of the smaller cage's extent across the belly axis
REACH = 2.2         # a partner lies within this many cage depths along it

WANT = {"row": (0, 180), "column": (270, 90)}


def _inner(contract, resolve, depth=0):
    """(interface, extra rotation) a placed part presents, looked through the
    one composed aperture of a wrapper the way manifest.presented_interface is."""
    if contract.get("interface"):
        return contract["interface"], 0
    if depth > 3:
        return None, 0
    found = []
    for part in contract.get("parts") or []:
        core = resolve(part.get("ref")) if part.get("ref") else None
        if not core:
            continue
        iface, rot = _inner(core, resolve, depth + 1)
        if iface:
            found.append((iface, (int(part.get("rotate") or 0) + rot) % 360))
    return found[0] if len(found) == 1 else (None, 0)


def cages(items, resolve):
    """The cages among `items` (view placements, or a contract's parts), each
    as a dict with its drawn footprint and effective rotation.

    `resolve(ref)` returns a contract or None."""
    out = []
    for p in items or []:
        ref = p.get("ref")
        if not ref or not p.get("id") or not p.get("at"):
            continue
        c = resolve(ref)
        if not c or not c.get("size"):
            continue
        iface, inner = _inner(c, resolve)
        if iface not in FAMILY and iface not in SKIPPED:
            continue
        w, h = float(c["size"]["w"]), float(c["size"]["h"])
        rot = (int(p.get("rotate") or 0) + inner) % 360
        cx, cy = float(p["at"][0]) + w / 2, float(p["at"][1]) + h / 2
        dw, dh = (h, w) if rot in (90, 270) else (w, h)
        out.append({"id": p["id"], "ref": ref, "interface": iface,
                    "family": FAMILY.get(iface, iface), "rotate": rot,
                    "mirror": bool(p.get("mirror")),
                    "x0": cx - dw / 2, "y0": cy - dh / 2, "w": dw, "h": dh})
    return out


def _overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def pairs(found):
    """Belly-to-belly pairs among `cages()` output.

    Returns a list of dicts: kind ('row' | 'column'), first (upper / left),
    second (lower / right), each a cage dict. Skipped families pair too, so a
    census can count them; `checked(pair)` says whether L108 holds one."""
    out, used = [], set()
    for a in sorted(found, key=lambda c: (round(c["x0"], 2), round(c["y0"], 2))):
        if a["id"] in used or a["rotate"] % 90:
            continue
        kind = "row" if a["rotate"] in (0, 180) else "column"
        best, best_d = None, None
        for b in found:
            if b is a or b["id"] in used or b["family"] != a["family"]:
                continue
            if (b["rotate"] in (0, 180)) != (kind == "row"):
                continue
            if kind == "row":
                ov = _overlap(a["x0"], a["x0"] + a["w"], b["x0"], b["x0"] + b["w"])
                span, d, depth = min(a["w"], b["w"]), b["y0"] - a["y0"], a["h"]
            else:
                ov = _overlap(a["y0"], a["y0"] + a["h"], b["y0"], b["y0"] + b["h"])
                span, d, depth = min(a["h"], b["h"]), b["x0"] - a["x0"], a["w"]
            if ov < OVERLAP * span - EPS or not (EPS < d < REACH * depth):
                continue
            if best is None or d < best_d:
                best, best_d = b, d
        if best is not None:
            used |= {a["id"], best["id"]}
            out.append({"kind": kind, "first": a, "second": best})
    return out


def checked(pair):
    return pair["first"]["interface"] not in SKIPPED and \
        pair["second"]["interface"] not in SKIPPED


def conforms(pair):
    return (pair["first"]["rotate"], pair["second"]["rotate"]) == WANT[pair["kind"]]


def state(pair):
    """A census label for the pair's current turn."""
    a, b = pair["first"]["rotate"], pair["second"]["rotate"]
    if pair["kind"] == "row":
        return {(0, 0): "both upright", (0, 180): "lower turned",
                (180, 0): "upper turned", (180, 180): "both turned"}.get(
                    (a, b), f"{a}/{b}")
    return {(270, 90): "bails out", (90, 270): "bails in",
            (90, 90): "both right", (270, 270): "both left"}.get((a, b), f"{a}/{b}")


def exceptions(doc):
    """{frozenset(ids): entry} for a manifest's or contract's `stack-exceptions`."""
    out = {}
    for e in (doc or {}).get("stack-exceptions") or []:
        for ids in ([e["pair"]] if e.get("pair") else []) + list(e.get("pairs") or []):
            if len(ids or []) == 2:
                out[(e.get("view"), frozenset(ids))] = e
    return out


def excepted(exc, pair, view=None):
    key = frozenset((pair["first"]["id"], pair["second"]["id"]))
    return exc.get((view, key)) or exc.get((None, key))


def lamp_directions(items):
    """{port id: 'up' | 'down' | ...} from `common/led-arrow*` lamps `for:` a port."""
    from .manifest import targets
    out = {}
    for p in items or []:
        if "led-arrow" in (p.get("ref") or "") and p.get("for"):
            for t in targets(p["for"]):
                out[str(t).split("/")[-1]] = p.get("skin") or "default"
    return out


def device_pairs(doc, resolve):
    """(view, pair) for every pair in a device manifest's views."""
    from .manifest import view_parts
    for vname, view in (doc.get("views") or {}).items():
        for pr in pairs(cages(view_parts(view)["placements"], resolve)):
            yield vname, pr


def component_pairs(doc, resolve):
    """(None, pair) for every pair among a component contract's `parts`."""
    for pr in pairs(cages(doc.get("parts") or [], resolve)):
        yield None, pr


def findings(doc, resolve, is_device):
    """L108's messages for one manifest or contract: [(message)]."""
    exc = exceptions(doc)
    msgs, hit = [], set()
    walk = device_pairs if is_device else component_pairs
    for vname, pr in walk(doc, resolve):
        if not checked(pr):
            continue
        key = frozenset((pr["first"]["id"], pr["second"]["id"]))
        e = excepted(exc, pr, vname)
        if e is not None:
            hit.add((vname, key) if (vname, key) in exc else (None, key))
            continue
        if conforms(pr):
            continue
        a, b = pr["first"], pr["second"]
        want = WANT[pr["kind"]]
        where = f"{vname}: " if vname else ""
        pos = ("upper", "lower") if pr["kind"] == "row" else ("left", "right")
        msgs.append(
            f"{where}{a['id']} over {b['id']} is a belly-to-belly {pr['kind']} pair "
            f"turned {a['rotate']}/{b['rotate']} ({state(pr)}); the convention is "
            f"{pos[0]} {want[0]}, {pos[1]} {want[1]} - both bails outward. Turn them, or "
            f"declare the pair in `stack-exceptions:` with the reading that says otherwise")
    for key, e in exc.items():
        if key not in hit:
            msgs.append(f"stack-exceptions names {sorted(key[1])}, which is not "
                        f"a checked belly-to-belly pair here (OSFP stacks are not checked) - "
                        f"remove the stale entry or fix the ids")
    return msgs

#!/usr/bin/env python3
"""Expand a device's `layout.yaml` into its `device.yaml`.

WHY THIS EXISTS. 41% of every device.yaml in this library is repeated
single-line items - one placement, one cutout, one numeral and one lamp per
port - and none of it carries a decision. A 64-port face is 400-odd lines that
say the same thing sixty-four times, and they are written by hand, which is why
the failures they produce are the ones no rule catches: a numbering that stops
four ports short of the end, fans that come out unevenly spaced because one
edge was measured wrong, a lamp pattern carried across one block and not its
neighbour. A loop does not get tired near the end of a face.

WHAT IT DOES NOT DO. It does not decide anything. Every number it emits comes
from the layout the author wrote or from the standards registry: the pitch of a
ganged cage is `standards.yaml`'s business and has been all along, and re-deriving
it from a 520-pixel render was always the wrong way to get it. Where a block is
not regular - and six blocks in this library are not - the author writes the
placements out longhand and this passes them through untouched. A generator that
insists on covering everything is a generator that starts inventing.

    layout.yaml   authored, reviewable, ~40 lines for a face
    device.yaml   generated, committed, what every consumer already reads

Consumers change nothing: render.py, lint.py, dcim_export, devicelock and the
viewer keep reading device.yaml exactly as before. `--check` re-expands and
compares, so the pair cannot drift.

MEASURED AGAINST THE LIBRARY BEFORE IT WAS WRITTEN: the bank/rows/pitch/gang/
gutter model reproduces 39 of 56 existing port blocks to the 0.01mm the files
carry, and 48 of 56 to within 0.11mm - the residue being independent rounding in
hand-authored numbers rather than disagreement about the shape.
"""
import argparse
import copy
import pathlib
import sys

import yaml


# ---------------------------------------------------------------- registry ---

def load_standards(schemas: pathlib.Path):
    return yaml.safe_load((schemas / "standards.yaml").read_text())["standards"]


def contract_for(library: pathlib.Path, ref: str):
    """`std/qsfp-dd@1` -> its contract, or None."""
    try:
        ns, rest = ref.split("/", 1)
        name, major = rest.split("@")
    except ValueError:
        return None
    hits = sorted((library / "components" / ns / name).glob(f"v{major}/contract.yaml"))
    return yaml.safe_load(hits[-1].read_text()) if hits else None


def aperture_of(library, standards, ref, depth=0):
    """The opening a part presents, forwarding through a composed cage.

    Mirrors the rule the cutout tests hold: a cutout restates the aperture the
    component already declares, so the hole is never a second measurement.
    """
    ct = contract_for(library, ref)
    if not ct or depth > 3:
        return None
    conf = ct.get("conforms")
    if conf in standards:
        st = standards[conf]
        return (st["w"], st["h"]), (0.0, 0.0)
    found = []
    for part in (ct.get("parts") or []):
        sub = aperture_of(library, standards, part.get("ref", ""), depth + 1)
        if sub:
            off = part.get("at") or [0, 0]
            found.append((sub[0], (off[0] + sub[1][0], off[1] + sub[1][1])))
    if len(found) == 1:
        return found[0]
    size = ct.get("size") or {}
    if size.get("w"):
        return (size["w"], size["h"]), (0.0, 0.0)
    return None


def _pitch_of(std):
    """A standard states its pitch one of two ways, and the difference matters.

    `qsfp-ganged` carries an explicit `pitch: 19.0` beside an 18.5 opening: the
    cages share a wall, so the pitch is wider than the hole. `sfp-ganged` carries
    no pitch key at all, because for that family `w` IS the pitch - 14.25 Basic,
    with adjacent instances abutting exactly - and the registry says so in its
    own provenance. Reading only the `pitch` key finds one and misses the other;
    reading only `w` silently narrows every ganged QSFP block by half a
    millimetre per port, which over 32 columns is most of a port.
    """
    if std.get("pitch"):
        return std["pitch"], "pitch"
    if std.get("w"):
        return std["w"], "w (instances abut)"
    return None, None


def standard_of(library, standards, ref):
    """The standard a part conforms to, following a single composed part down."""
    ct = contract_for(library, ref)
    seen = []
    while ct:
        conf = ct.get("conforms")
        if conf in standards:
            return conf
        parts = ct.get("parts") or []
        if len(parts) != 1 or parts[0].get("ref") in seen:
            return None
        seen.append(parts[0].get("ref"))
        ct = contract_for(library, parts[0]["ref"])
    return None


def _single_opening(library, standards, ref):
    """Does this part present ONE opening, or several?

    `aperture_of` answers 'how big is the opening' and falls back to the whole
    body when it cannot find one - which is right for sizing and dangerous for
    punching. A part holding four lamps in a column has a body and four windows,
    and a hole the size of the body is a statement about the sheet metal that
    nobody has verified. Ask the different question here: how many openings does
    the contract actually declare?
    """
    ct = contract_for(library, ref)
    if not ct:
        return False
    if ct.get("conforms") in standards:
        return True
    els = [e for e in (ct.get("elements") or {}).values()] \
        if isinstance(ct.get("elements"), dict) else (ct.get("elements") or [])
    holes = [e for e in els
             if isinstance(e, dict) and e.get("class") in ("cutout", "led", "window")]
    if holes:
        return len(holes) == 1
    return len(ct.get("parts") or []) <= 1


def registry_pitch(library, standards, ref, named=None):
    """The pitch a ganged block is built on - a LOOKUP, not a measurement.

    This is the single most re-derived number in the whole modelling process,
    and it has been sitting in the registry with a confidence token and a
    paragraph of derivation the entire time.

    `named` exists because a part and the block it sits in are not the same
    thing: `std/qsfp-dd` conforms to `qsfp-dd`, which describes ONE cage and
    states no pitch, while a row of them abutting is `qsfp-ganged`. The author
    names which standard governs the block rather than the tool guessing from a
    suffix.
    """
    key = named or standard_of(library, standards, ref)
    if not key or key not in standards:
        return None, None
    return _pitch_of(standards[key])


def registry_row_pitch(library, standards, ref, named=None):
    """Belly-to-belly row spacing, where the registry states it."""
    key = named or standard_of(library, standards, ref)
    if not key or key not in standards:
        return None
    return standards[key].get("row-pitch")


# -------------------------------------------------------------- expansion ---

def block_items(block, library, standards):
    """One regular block -> its placements, cutouts, numerals and lamps.

    The layout says how the block REPEATS; everything else follows.
    """
    ref = block["ref"]
    at = block["at"]
    count = int(block["count"])
    rows = int(block.get("rows", 1))
    gang = int(block.get("gang", 0))
    gutter = float(block.get("gutter", 0.0))

    # `pitch: registry` | `pitch: {registry: qsfp-ganged}` | `pitch: 19.0`
    spec = block.get("pitch", "registry")
    named = spec.get("registry") if isinstance(spec, dict) else None
    if spec == "registry" or named:
        pitch, how = registry_pitch(library, standards, ref, named)
        if pitch is None:
            raise SystemExit(
                f"block {block.get('id')}: pitch from the registry, but "
                f"{named or ref} names no standard that states one. Either name the "
                f"ganged standard - pitch: {{registry: qsfp-ganged}} - or give a "
                f"number and say in provenance where it was measured.")
    else:
        pitch = spec
    pitch = float(pitch)

    rp = block.get("row-pitch", "registry" if rows > 1 else 0.0)
    if rp == "registry":
        rp = registry_row_pitch(library, standards, ref, named)
        if rp is None:
            raise SystemExit(
                f"block {block.get('id')}: row-pitch from the registry, but "
                f"{named or ref} names no standard that states one. Belly-to-belly "
                f"spacing is specified nowhere for most families - measure it and "
                f"give a number.")
    row_pitch = float(rp)

    first = int(block.get("number-from", 0))
    idfmt = block.get("id-format", "port-{n}")
    rot = block.get("rotate") or {}
    rot_by_row = [rot.get("top", 0) if r == 0 else rot.get("bottom", 0)
                  for r in range(rows)]

    ap = aperture_of(library, standards, ref) if block.get("cutouts") else None
    ct = contract_for(library, ref) or {}
    csize = ct.get("size") or {}

    placements, cutouts, silks, lamps = [], [], [], []
    led = block.get("led")
    num = block.get("numerals")

    for i in range(count):
        col, row = divmod(i, rows)
        x = round(at[0] + col * pitch + (col // gang if gang else 0) * gutter, 2)
        y = round(at[1] + row * row_pitch, 2)
        n = first + i
        pid = idfmt.format(n=n)

        p = {"ref": ref, "id": pid, "at": [x, y]}
        if rot_by_row[row]:
            p["rotate"] = rot_by_row[row]
        p["group"] = block["id"]
        p["rel-pos"] = n
        placements.append(p)

        if ap:
            (aw, ah), (ax, ay) = ap
            deg = rot_by_row[row] % 360
            cw = csize.get("w", aw)
            ch = csize.get("h", ah)
            # a placement turns about the WRAPPER's centre, not the hole's
            if deg == 180:
                hx, hy = cw - ax - aw, ch - ay - ah
            elif deg == 90:
                hx, hy = (cw - ay - ah), ax
            elif deg == 270:
                hx, hy = ay, (ch - ax - aw)
            else:
                hx, hy = ax, ay
            sw, sh = (ah, aw) if deg in (90, 270) else (aw, ah)
            cutouts.append({"id": pid, "at": [round(x + hx, 2), round(y + hy, 2)],
                            "size": [round(sw, 2), round(sh, 2)],
                            "shape": block.get("cutout-shape", "rect")})

        if num:
            # numerals bracket a ganged shell the same way lamps do, because on
            # these faces the numeral is printed with its lamp rather than over
            # its cage - so it takes the same per-column offset list
            nby = num.get("dx-by-col")
            ndx = nby[col % len(nby)] if nby else num.get("dx", 0.0)
            silks.append({
                "at": [round(x + ndx, 2),
                       round(y + (num.get("dy-top", num.get("dy", 0.0)) if row == 0
                                  else num.get("dy-bottom", num.get("dy", 0.0))), 2)],
                "text": str(n), "font-size": num.get("font-size", 1.8),
                "anchor": num.get("anchor", "middle"),
                "fill": num.get("fill", "#1a1d1f"), "for": pid})

        if led:
            # A LAMP IS NOT ALWAYS OFFSET FROM ITS OWN PORT. On a ganged block
            # the lamps commonly BRACKET the shell - the left column's lamp
            # sitting outside it to the left, the right column's outside to the
            # right - so the offset depends on where the port falls within its
            # gang, not on the port alone. `dx-by-col` is that list, indexed by
            # the column's position in its shell; a plain `dx` is the degenerate
            # case of one value for every column.
            by_col = led.get("dx-by-col")
            dx = by_col[col % len(by_col)] if by_col else led.get("dx", 0.0)
            lp = {"ref": led["ref"], "id": led.get("id-format", "led-{n}").format(n=n),
                  "at": [round(x + dx, 2),
                         round(y + (led.get("dy-top", led.get("dy", 0.0)) if row == 0
                                    else led.get("dy-bottom", led.get("dy", 0.0))), 2)]}
            skin = led.get("skin-top") if row == 0 else led.get("skin-bottom")
            if skin:
                lp["skin"] = skin
            lp["for"] = pid
            lp["group"] = led.get("group", "port-leds")
            lp["rel-pos"] = n
            lamps.append(lp)

            # A LAMP IS A HOLE TOO - but ONLY WHERE THE PART DECLARES ONE HOLE.
            #
            # The first face this tool generated punched 32 ports and left 32
            # lamps unpunched, and the obvious fix - derive the lamp's opening
            # the way the port's is derived - was written, run, and was WRONG.
            # The lamp component there is a COLUMN OF FOUR: a 1.7 x 10.7 body
            # holding four 1.7mm windows. With no single aperture to resolve,
            # the derivation fell back to the body size and emitted one
            # 1.7 x 10.7 hole, described as a circle. That is a 1:6 round hole,
            # and worse, it is a claim - that the metal has one long slot rather
            # than four windows - which the images at 10 px/mm cannot settle
            # either way. It silenced 32 warnings by drawing something false.
            #
            # So the tool punches a lamp only when the component declares
            # exactly one opening. Where it declares several, the geometry is a
            # question for a person: the warning stands, and standing is the
            # correct outcome until somebody reads the metal.
            if ap and _single_opening(library, standards, led["ref"]):
                lap = aperture_of(library, standards, led["ref"])
                (lw, lh), (lax, lay) = lap
                cutouts.append({
                    "id": lp["id"],
                    "at": [round(lp["at"][0] + lax, 2),
                           round(lp["at"][1] + lay, 2)],
                    "size": [round(lw, 2), round(lh, 2)],
                    # a lamp aperture is round unless the author says otherwise
                    "shape": led.get("cutout-shape", "circle")})

    return placements + lamps, cutouts, silks


# --------------------------------------------------------------- marks ---
#
# WHY NOT JUST WRITE `▲`? It is one character and this is a dozen numbers, so
# the question deserves a real answer rather than a rule.
#
# A text glyph is resolved by whatever font the RENDERER picks. This library's
# drawings are read by browsers, by cairosvg, by Inkscape and by a 3D viewer,
# and each resolves fonts differently - U+25B2 came out as an empty box in the
# first tool that met it, and an empty box is a defect nobody notices until a
# reviewer zooms in. Worse for this project: a glyph's SIZE AND POSITION inside
# its em box are the typeface's business, so the same mark lands differently in
# two renderers. Every finding in this review has been a fraction of a
# millimetre; a symbol whose position is a font's opinion cannot be aligned.
# And lint estimates text width as characters x 0.62em, which is meaningless
# for a triangle, so a glyph is invisible to the rule that checks for overlap.
#
# But the pain is real, and it has a cost the pain hides: the library carries
# 593 hand-written path marks, 116 of them distinct, 468 of which are plain
# triangles - the same two symbols drawn hundreds of times at six different
# sizes. Hand-authoring is how a letter E became three strokes with no spine.
#
# So: keep paths, stop writing them. A named mark expands here, in the authored
# file, and the generated device.yaml still carries the explicit path every
# consumer already reads. Nothing downstream changes.
#
# The named marks are CENTRED ON THEIR `at`, which the hand-written ones were
# not - the existing arrow pairs sit 0.3mm below their anchor, which is exactly
# how a legend row came to be centred on nothing.

def _tri(w, h, up, cx=0.0):
    y0, y1 = -h / 2, h / 2
    if up:
        return (f"M {cx - w / 2:g} {y1:g} L {cx + w / 2:g} {y1:g} "
                f"L {cx:g} {y0:g} Z")
    return (f"M {cx - w / 2:g} {y0:g} L {cx + w / 2:g} {y0:g} "
            f"L {cx:g} {y1:g} Z")


def _ground(w):
    """IEC 60417-5019 earth: three stacked bars, each shorter, on a stem."""
    s, out = w / 2, [f"M 0 {-w * 0.55:g} L 0 {-w * 0.10:g}"]
    for i, (frac, y) in enumerate(((1.00, -0.10), (0.62, 0.12), (0.28, 0.34))):
        out.append(f"M {-s * frac:g} {w * y:g} L {s * frac:g} {w * y:g}")
    return " ".join(out)


def _usb(w):
    """USB trident: the shaft, the arrowhead, and the two branch terminals.

    Drawn rather than described because a reviewer found this symbol
    hand-authored several different ways across one vendor's devices, one of
    them clearly an attempt at a shape whose author had not worked out what it
    was meant to be.
    """
    s = w / 2
    return (f"M 0 {s:g} L 0 {-s * 0.55:g} "                     # shaft
            f"M {-s * 0.28:g} {-s * 0.55:g} L {s * 0.28:g} {-s * 0.55:g} "
            f"L 0 {-s:g} Z "                                    # arrowhead
            f"M 0 {s * 0.10:g} L {-s * 0.55:g} {-s * 0.30:g} "  # left branch
            f"M 0 {-s * 0.10:g} L {s * 0.55:g} {s * 0.20:g}")   # right branch


def _bolt(w):
    """IEC 60417-5036 hazardous voltage: the flash, filled."""
    s = w / 2
    return (f"M {s * 0.35:g} {-s:g} L {-s * 0.55:g} {s * 0.15:g} "
            f"L {-s * 0.05:g} {s * 0.15:g} L {-s * 0.35:g} {s:g} "
            f"L {s * 0.55:g} {-s * 0.15:g} L {s * 0.05:g} {-s * 0.15:g} Z")


# name -> (path builder, is the ink enclosed by the path or traced along it)
MARKS = {
    "arrow-up":   (lambda w, g: _tri(w, w * 0.889, True), True),
    "arrow-down": (lambda w, g: _tri(w, w * 0.889, False), True),
    "arrow-pair": (lambda w, g: "%s %s" % (
        _tri(w, w * 0.889, True, -(w + g) / 2),
        _tri(w, w * 0.889, False, (w + g) / 2)), True),
    "ground":     (lambda w, g: _ground(w), False),
    "usb":        (lambda w, g: _usb(w), False),
    "bolt":       (lambda w, g: _bolt(w), True),
}


def mark_path(name, size=1.8, gap=None):
    """Canonical geometry for a named silkscreen mark, centred on its anchor.

    Returns (path, filled). `size` is the mark's WIDTH in mm; an arrow's height
    follows the 0.889 ratio the library's most common hand-drawn ones use.
    """
    if name not in MARKS:
        raise SystemExit(f"unknown silkscreen mark {name!r} - known: "
                         + ", ".join(sorted(MARKS)))
    w = float(size)
    g = w * 0.45 if gap is None else float(gap)
    build, filled = MARKS[name]
    return build(w, g), filled


def _expand_marks(seq):
    out = []
    for m in seq or []:
        if isinstance(m, dict) and m.get("mark"):
            m = dict(m)
            path, filled = mark_path(m.pop("mark"), m.pop("size", 1.8),
                                     m.pop("gap", None))
            m["path"] = path
            # a solid symbol says so, so the renderer fills it instead of
            # tracing its outline and leaving a pinhole in the middle
            if filled:
                m["filled"] = True
            elif "stroke-width" not in m:
                m["stroke-width"] = 0.28
        out.append(m)
    return out


def _splice(seq, made):
    """Replace each `{block: <name>}` marker with that block's items, in place.

    ORDER IS THE AUTHOR'S TO CHOOSE, not the tool's, for two reasons. Paint order
    is meaning - a later item draws over an earlier one - so appending generated
    ports after a hand-written cluster silently changes what covers what. And the
    device fingerprint in devices.lock.json is order-sensitive, so a tool that
    reorders a converted device reports a MAJOR change on a file whose content
    did not move at all, which would make every conversion look like a
    geometry break.
    """
    out = []
    for item in seq or []:
        if isinstance(item, dict) and set(item) == {"block"}:
            out += made.get(item["block"], [])
        else:
            out.append(item)
    return out


def expand(layout, library, standards):
    """layout.yaml -> the device dict a consumer reads."""
    doc = copy.deepcopy(layout)
    doc.pop("layout-format", None)
    for view in (doc.get("views") or {}).values():
        # named marks expand on every view, whether or not it has blocks
        if view.get("silkscreen"):
            view["silkscreen"] = _expand_marks(view["silkscreen"])
        comps = view.get("components") or {}
        blocks = comps.pop("blocks", None)
        if not blocks:
            continue
        made_p, made_c, made_s = {}, {}, {}
        for b in blocks:
            key = b.get("as") or b["id"]
            p, c, s = block_items(b, library, standards)
            made_p.setdefault(key, []).extend(p)
            made_c.setdefault(key, []).extend(c)
            made_s.setdefault(key, []).extend(s)

        panel = view.setdefault("panel", {})
        named = set()
        for seq in (comps.get("placements"), view.get("silkscreen"),
                    panel.get("cutouts")):
            for item in seq or []:
                if isinstance(item, dict) and set(item) == {"block"}:
                    named.add(item["block"])

        comps["placements"] = _splice(comps.get("placements"), made_p)
        view["silkscreen"] = _splice(view.get("silkscreen"), made_s)
        if panel.get("cutouts"):
            panel["cutouts"] = _splice(panel.get("cutouts"), made_c)

        # A block nobody placed appends, so a layout that names no markers still
        # works - but say which, because a silent append is how paint order goes
        # wrong without anybody choosing it.
        for key in made_p:
            if key not in named:
                comps["placements"] = comps["placements"] + made_p[key]
                if made_s[key]:
                    view["silkscreen"] = (view.get("silkscreen") or []) + made_s[key]
                if made_c[key]:
                    panel["cutouts"] = (panel.get("cutouts") or []) + made_c[key]
                print(f"  note: block {key!r} had no {{block: {key}}} marker; "
                      f"appended at the end of its lists")
        if not view.get("silkscreen"):
            view.pop("silkscreen", None)
        view["components"] = comps
    return doc


# ------------------------------------------------------------------- emit ---

class Dumper(yaml.SafeDumper):
    """House style, which is not decoration - it is what makes a diff readable.

    A placement is ONE LINE: `- {ref: std/qsfp-dd@1, id: port-0, at: [85.7, 9.65]}`.
    Written as PyYAML's default block mapping it becomes five lines, and a
    64-port face that should read as a table of ports turns into 2000 lines of
    scrolling - longer than the hand-written file it replaces, which is the
    opposite of the point. Leaf maps and coordinate pairs go flow; prose folds.
    """


def _is_leaf(data):
    """A map with nothing nested in it and no prose - safe to put on one line."""
    for v in data.values():
        if isinstance(v, dict):
            return False
        if isinstance(v, list) and any(isinstance(i, (dict, list)) for i in v):
            return False
        if isinstance(v, str) and (len(v) > 60 or "\n" in v):
            return False
    return True


def _dict(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data,
                                    flow_style=_is_leaf(data))


def _list(dumper, data):
    flow = all(isinstance(i, (int, float)) for i in data) and len(data) <= 4
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


def _str(dumper, data):
    if "\n" in data or len(data) > 88:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


Dumper.add_representer(dict, _dict)
Dumper.add_representer(list, _list)
Dumper.add_representer(str, _str)


def dump(doc):
    return yaml.dump(doc, Dumper=Dumper, sort_keys=False, width=100,
                     default_flow_style=False, allow_unicode=True)


# ------------------------------------------------------------------- main ---

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", default="library", type=pathlib.Path)
    ap.add_argument("--schemas", default="spec/schemas", type=pathlib.Path)
    ap.add_argument("--check", action="store_true",
                    help="re-expand every layout.yaml and report any that "
                         "disagrees with its committed device.yaml")
    ap.add_argument("layout", nargs="*", type=pathlib.Path)
    a = ap.parse_args()

    standards = load_standards(a.schemas)
    paths = a.layout or sorted((a.library / "devices").glob("*/*/layout.yaml"))
    if not paths:
        print("expand: no layout.yaml found - nothing to do")
        return 0

    bad = 0
    for lp in paths:
        layout = yaml.safe_load(lp.read_text())
        doc = expand(layout, a.library, standards)
        dp = lp.with_name("device.yaml")
        if a.check:
            if not dp.exists():
                print(f"{dp}: MISSING - layout.yaml has never been expanded")
                bad += 1
                continue
            if yaml.safe_load(dp.read_text()) != doc:
                print(f"{dp}: DIFFERS from its layout.yaml - re-run expand.py")
                bad += 1
            continue
        dp.write_text(dump(doc))
        n = sum(len((v.get("components") or {}).get("placements") or [])
                for v in (doc.get("views") or {}).values())
        print(f"{dp}: {n} placements from {len(lp.read_text().splitlines())} "
              f"lines of layout")
    if a.check:
        print(f"expand: {len(paths) - bad}/{len(paths)} in step with their layout")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

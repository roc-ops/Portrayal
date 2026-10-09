"""A generic L-bracket rack ear, drawn from `chassis.ears` (#909).

WHAT IT IS. A rack device is modelled between its ear folds - the body, not the
rack face - and its ears were drawn, when at all, by `common/rack-ear@1`: a
14 x 43.5 decoration placed by hand under `optional: ears`, the same size on a
1U switch and a 13U chassis. A real ear's height follows the chassis, or what
`chassis.ears` says of it (docs/rack-mounting-design.md section 3: `h` is the
height the ears span, `y` the bottom of the ears above the bottom of the
chassis), and its flange reaches from the body's side out to the 482.6 mm rack
face. This module says what that ear is - one plan, read by render.py for the
2D faces and mirrored by the kit's `genericEars` (kit/relief.js) for the 3D
scene, and a test holds the two to the same numbers.

DRAWN ONLY WHEN ASKED FOR. The library draws devices without their ears, and
the published faces stay that way: the ear is part of a face only under
`render.py --with ears`, the include tag `common/rack-ear@1` has always been
drawn under, and in 3D only when a host asks the viewer for `ears`. So nothing
published moves, and no device lock does (see `CHASSIS_SURFACE` in
devicelock.py for why `h` and `y` stay a patch).

NO DEVICE GETS A SECOND PAIR. A device gets no generic ear when:
  - it is not a `rack` device - a `rack-face` part is its ears, a `rack-side`
    duct and a desktop box have none;
  - it states `ears: behind` (or `{behind: true}`), whose face is the part;
  - its front is as wide as the rack face (L43's 480-487 mm), so its ears are
    already in the drawing - the R740xd, whose ears carry its VGA;
  - it still places `common/rack-ear@1`, or anything under `optional: ears`,
    which draws its own pair under the same tag. Those move over to this ear
    as each next takes a major (#910).

THE NUMBERS THAT ARE NOT THE DEVICE'S are EIA-310's (the 482.6 mm face, the
465.1 mm between the rail holes' centres, the holes 6.35 and 38.1 mm up each U)
and two estimates of a sheet-metal bracket nobody has measured: the 2 mm it is
folded from and the 30 mm its side leg runs back along the body. They are
constants here so the 2D and the 3D draw the same bracket.
"""

import math

RACK_FACE = 482.6       # EIA-310 panel width: the flange reaches out to it
HOLE_SPAN = 465.1       # EIA-310, centre to centre of the rail holes across the rack
U = 44.45               # one rack unit
HOLES_IN_U = (6.35, 38.1)   # the outer two of a U's three holes, from its bottom
THICKNESS = 2.0         # the sheet the bracket is folded from (estimated)
LEG = 30.0              # how far the side leg runs back along the body (estimated)
MIN_FLANGE = 3.0        # narrower than this is no flange to draw
SLOT = (8.0, 5.0)       # a rail-hole slot, long across the rack for the tolerance
EAR_WIDE = 480.0        # L43's lower bound: a face this wide has its ears in it
FILL, EDGE, HOLE = "#2b2f33", "#171a1d", "#0d0f11"   # common/rack-ear@1's colours
IDS = ("ear-left", "ear-right")


def _places_own_ears(node):
    """Whether anything under `node` draws ears of its own: a placement under
    the `ears` include tag, or a `common/rack-ear@1` however it is tagged."""
    if isinstance(node, dict):
        if node.get("optional") == "ears":
            return True
        if str(node.get("ref") or "").startswith("common/rack-ear@"):
            return True
        if node.get("id") in IDS:
            return True
        return any(_places_own_ears(v) for v in node.values())
    if isinstance(node, list):
        return any(_places_own_ears(v) for v in node)
    return False


def _behind(ears):
    if isinstance(ears, dict):
        return ears.get("behind") is True
    return ears == "behind"


def _default_at(ears):
    """The default position's `at`, else 0: flush, the way most gear ships."""
    for pos in (ears.get("positions") or []) if isinstance(ears, dict) else []:
        if (pos or {}).get("default") is True and pos.get("at") is not None:
            return float(pos["at"])
    return 0.0


def plan(device):
    """The generic ear this device draws, or None when it draws none.

    `w`, `h_body` and `d` are the body's front width, height and depth; `flange`
    the width each flange reaches past the body; `h` and `y` the height the ear
    spans and its bottom above the chassis bottom; `at` the default position's
    setback (the flange's back face, which bolts to the rail, `at` behind the
    faceplate's front); `slots` each slot's centre above the ear's bottom, and
    `slot_x` its centre out from the body's side."""
    ch = device.get("chassis") or {}
    if ch.get("mount", "rack") != "rack" or ch.get("shell"):
        return None
    ears = ch.get("ears")
    if _behind(ears) or _places_own_ears(device.get("views") or {}):
        return None
    front = ((device.get("views") or {}).get("front") or {}).get("size") or {}
    w = float(front.get("w", ch.get("width") or 0))
    h_body = float(front.get("h", ch.get("height") or 0))
    if not w or not h_body or w >= EAR_WIDE:
        return None
    flange = round((RACK_FACE - w) / 2, 4)
    if flange < MIN_FLANGE:
        return None
    ears = ears if isinstance(ears, dict) else {}
    # absent, they are the chassis: from its bottom, or `y`, up to its top
    y = float(ears["y"]) if ears.get("y") is not None else 0.0
    h = float(ears["h"]) if ears.get("h") is not None else h_body - y
    units = max(1, math.floor(h / U + 0.5))     # half up, as the kit's Math.round
    unit = h / units
    slots = [round(i * unit + hole * unit / U, 4)
             for i in range(units) for hole in HOLES_IN_U]
    sw = min(SLOT[0], flange - 1.0)
    slot_x = min(max(HOLE_SPAN / 2 - w / 2, sw / 2 + 0.5), flange - sw / 2 - 0.5)
    return {"w": w, "h_body": h_body, "d": float(ch.get("depth") or 0),
            "flange": flange, "h": h, "y": y, "at": _default_at(ears),
            "t": THICKNESS, "leg": LEG, "slots": slots,
            "slot_x": round(slot_x, 4), "slot": [round(sw, 4), SLOT[1]]}


def leg_span(p):
    """Where the side leg runs, in mm back from the faceplate's front: from the
    flange's back face to `LEG` onto the body. A bracket reaching forward
    (`at` < 0) still bolts `LEG` of itself to the body."""
    return p["at"], max(p["at"], 0.0) + p["leg"]


def rects(p, view, vw, vh):
    """The ear's outlines on one face, in that face's own coordinates:
    `[(id, kind, x, y, w, h)]`, `kind` being `flange`, `slot`, `leg` or `edge`.

    `vw` and `vh` are the face's declared size. The front and rear show each
    flange face-on beyond the body's sides; the sides show the leg on the body
    and the flange edge-on; the top and the underside show both edge-on.
    The rear is seen from behind and the underside is authored mirrored in both
    axes, so on both the device's left ear is at the right of the drawing. On
    the sides the front is at the left end of the right view and the right end
    of the left view; on the top and the underside it is the bottom edge."""
    fl, t, h = p["flange"], p["t"], p["h"]
    top = vh - p["y"] - h            # SVG y of the ear's top edge
    z0, z1 = leg_span(p)             # the leg, back from the faceplate front
    zf0, zf1 = p["at"] - t, p["at"]  # the flange's thickness, ahead of its plane
    out = []
    if view in ("front", "rear"):
        mirrored = view == "rear"
        for i, side in enumerate(IDS):
            left = (i == 0) != mirrored
            x = -fl if left else vw
            out.append((side, "flange", x, top, fl, h))
            sx = (x + fl - p["slot_x"]) if left else (x + p["slot_x"])
            sw, sh = p["slot"]
            for cy in p["slots"]:
                out.append((side, "slot", sx - sw / 2, top + h - cy - sh / 2, sw, sh))
    elif view in ("left", "right"):
        side = IDS[0] if view == "left" else IDS[1]
        # distance back from the front -> x on this face
        at_x = (lambda z: vw - z) if view == "left" else (lambda z: z)
        xs = sorted((at_x(z0), at_x(z1)))
        out.append((side, "leg", xs[0], top, xs[1] - xs[0], h))
        xs = sorted((at_x(zf0), at_x(zf1)))
        out.append((side, "edge", xs[0], top, xs[1] - xs[0], h))
    elif view in ("top", "bottom"):
        mirrored = view == "bottom"
        for i, side in enumerate(IDS):
            left = (i == 0) != mirrored
            # the leg stands t off the body's side, the flange reaches fl past it
            out.append((side, "leg", -t if left else vw, vh - z1, t, z1 - z0))
            out.append((side, "edge", -fl if left else vw, vh - zf1, fl, t))
    return out

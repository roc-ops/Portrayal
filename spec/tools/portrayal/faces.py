"""Where a part keeps its other drawings.

A component's face is its own art. Seen from ANOTHER direction it is a different
drawing at a different size, so it is a different part: a riser's face is a
bracket plate, and from above it is a thin PCB with connectors. The library has
said that for a long time with a top-level `plan: {ref}`.

`faces:` is the same idea with room in it. A bare `rear:` sibling would handle
one more direction and then stop, and the third one would be a third top-level
key nobody thinks to look for. Readers go through `face_ref` so that adding a
direction is a change to this file rather than a hunt through render.py and
lint.py for the places that spell it out.

`plan:` stays legal and means exactly `faces.plan`. 11 components still need the
sugar - the count of things naming a plan drawing is 13, but two have migrated
to `faces.plan` and no longer touch this fallback. 11 is the number the
end-of-life question turns on: when it reaches zero, nothing in the library
still needs `plan:` to mean `faces.plan`, and the fallback can go. Nothing else
in the codebase tracks that number, so it has to be kept correct here by hand.
"""
import math

# THE LIST THE SCHEMA'S `faces.properties` DECLARES. A reader that spells the
# directions out instead of iterating this tuple silently drops whichever one
# it forgot - `components_index.py` did exactly that until this constant
# existed, checking "plan" and "rear" as a literal instead of importing them,
# so a third direction would pass lint, render fine, and vanish from the
# published index with nothing to say why.
DIRECTIONS = ("plan", "rear")

# WHICH FACES CARRY OPTICAL HARDWARE OF THEIR OWN.
#
# A rear face is the OTHER SIDE of the module: a cassette's MTP is drawn there
# and nowhere else, so its twelve positions are twelve endpoints the front does
# not have. A plan face is the SAME module seen from above - a riser's plan
# redraws the PCIe slots that are already its own - and anything optical drawn
# there would be the front's ports at a different angle, not new ones. Counting
# those again turns one physical port into two endpoints and obliges L80 to
# demand a path for a fibre that is already routed, leaving the author a
# duplicate path or an `unused` entry as the only ways out, both untrue about
# the hardware.
#
# THIS IS DELIBERATELY NOT `DIRECTIONS`. A direction added there gets a drawing
# for free; whether it also carries fibres of its own is a judgement about
# hardware rather than about drawings, and optics in this corpus live on the
# front and the back. L85 REPORTS a face outside this tuple that draws a
# connector rather than dropping it, because silently dropping a fibre is no
# better than silently counting it twice.
OPTICAL_FACES = ("rear",)

# `plan` is the only direction with a legacy spelling, because it is the only
# one that existed before `faces`. A new direction added here gets no fallback
# and needs none.
LEGACY = {"plan": "plan"}


def face_ref(contract, name):
    """The component ref for this part seen from `name`, or None.

    `name` is a key of `faces:` - "plan" or "rear" today. Reads the new spelling
    first so that a contract carrying both is resolved consistently with
    whatever L82 reports about it, rather than differently in each reader.
    """
    ref = (((contract.get("faces") or {}).get(name) or {}).get("ref"))
    if ref:
        return ref
    legacy = LEGACY.get(name)
    if legacy:
        return ((contract.get(legacy) or {}).get("ref")) or None
    return None


def rear_at(bay, cutout, contract):
    """Where `contract`'s back lands in a rear view, seated in `bay` and seen
    through `cutout`: the top-left of its `faces.rear` drawing, in that view's mm.

    THE BACK OF A MODULE IS THE BACK OF ITS BODY, and the body is the
    occupant's own: `body.footprint` says where it stands behind the faceplate
    (a cassette's 99 x 31 centred behind its 108.97 x 35.05 plate, an adapter
    panel's 88 x 34.8 hard against the plate's top). So the bay cannot say
    where the back lands - two modules the same bay accepts put theirs in two
    places - and the answer is read from whichever one is seated. Seen from
    behind, left and right swap, so the footprint is MIRRORED across the bay:
    the cutout is the bay's own hole from the other side. A body with no
    footprint fills the face, as the 3D viewer builds it.
    """
    size = contract.get("size") or {}
    fp = (contract.get("body") or {}).get("footprint") or {
        "at": [0, 0], "size": [float(size.get("w") or 0), float(size.get("h") or 0)]}
    cx, cy = cutout["at"]
    bw = float(bay["size"]["w"])
    return [round(cx + (bw - fp["at"][0] - fp["size"][0]), 4), round(cy + fp["at"][1], 4)]


def rear_turn(bay):
    """How far a back seen through `bay`'s rear cutout is turned in the rear
    view, in degrees: the bay's own `rotate`, negated, in [0, 360).

    A MODULE ON ITS SIDE SHOWS ITS BACK ON ITS SIDE, AND THE OTHER WAY ROUND.
    A bay's `rotate` turns its occupant clockwise as seen from the front; seen
    from behind, left and right swap and the same turn reads anticlockwise.
    So there is no second number for a device to state and get wrong: the
    back turns with the module, and the mirror decides which way.
    """
    return (-float(bay.get("rotate") or 0)) % 360


def rear_place(bay, cutout, contract, back):
    """Where `contract`'s back is drawn through `cutout`, seated in `bay`:
    ``{"at": [x, y], "rotate": deg}`` for a placement of its `faces.rear`
    drawing, whose size is `back` ({w, h}). `at` is that drawing's unturned
    top-left and `rotate` turns it about its own centre, which is how a
    placement is drawn.

    UNTURNED, THIS IS `rear_at`. A turned bay's `size` is the module's box
    after the turn - an FHD module on edge is a 35.05 x 108.97 bay holding a
    108.97 x 35.05 plate - and a footprint is in the module's own frame, so
    the footprint is found in the unturned bay (the bay's size with its axes
    swapped back, centred on the same hole) and the back's centre is then
    turned about the hole's centre by `rear_turn`, the whole module turning
    about its own middle as instance_group turns it at the front.
    """
    turn = rear_turn(bay)
    if not turn:
        return {"at": rear_at(bay, cutout, contract), "rotate": 0}
    bw, bh = float(bay["size"]["w"]), float(bay["size"]["h"])
    cx, cy = cutout["at"][0] + bw / 2, cutout["at"][1] + bh / 2
    uw, uh = (bh, bw) if turn in (90.0, 270.0) else (bw, bh)
    tl = rear_at({"size": {"w": uw, "h": uh}}, {"at": [cx - uw / 2, cy - uh / 2]}, contract)
    # no drawing to measure: the back is the body's, so it is the footprint's
    # size, or the module's own with no footprint (as swap.js's rearAt reads it)
    size = contract.get("size") or {}
    fp = (contract.get("body") or {}).get("footprint") or {
        "size": [float(size.get("w") or uw), float(size.get("h") or uh)]}
    dw = float((back or {}).get("w") or fp["size"][0])
    dh = float((back or {}).get("h") or fp["size"][1])
    vx, vy = tl[0] + dw / 2 - cx, tl[1] + dh / 2 - cy
    c, s = {90.0: (0, 1), 180.0: (-1, 0), 270.0: (0, -1)}.get(
        turn, (math.cos(math.radians(turn)), math.sin(math.radians(turn))))
    px, py = cx + vx * c - vy * s, cy + vx * s + vy * c
    return {"at": [round(px - dw / 2, 4), round(py - dh / 2, 4)], "rotate": turn}

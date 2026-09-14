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

# THE LIST THE SCHEMA'S `faces.properties` DECLARES. A reader that spells the
# directions out instead of iterating this tuple silently drops whichever one
# it forgot - `components_index.py` did exactly that until this constant
# existed, checking "plan" and "rear" as a literal instead of importing them,
# so a third direction would pass lint, render fine, and vanish from the
# published index with nothing to say why.
DIRECTIONS = ("plan", "rear")

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

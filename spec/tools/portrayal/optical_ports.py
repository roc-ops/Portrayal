"""A module's fibre graph, projected into DCIM ports and fibre-map rows.

PURE. Everything here takes an index entry and returns data; nothing opens a
file or writes one. That is what lets the projection be unit-tested without a
build, and it is why the naming rules live here rather than inside
`dcim_export.py`, which is already 900 lines of I/O.

See docs/optical-paths-design.md section C.
"""

# WHICH CONNECTOR FAMILY EACH PART IS. The ref is the fact; the family is what
# the port-type enum is keyed on. A part absent from this table carries no
# fibre as far as the projection is concerned, which is the same answer
# `optical.capacities` gives for a part with no `optical.positions`.
FAMILY = {
    "common/lc-duplex-adapter": "lc",
    "common/lc-duplex-v-adapter": "lc",
    "common/sc-duplex-adapter": "sc",
    "common/mpo-adapter": "mpo",
    "common/st-simplex-adapter": "st",
    "common/fc-simplex-adapter": "fc",
    "common/lsh-simplex-adapter": "lsh",
    "common/mdc-adapter": "mdc",
}

# WHICH FAMILIES THE ENUM SPELLS TWO WAYS. Section C's enum is `lc-upc, lc-apc,
# sc-upc, sc-apc, mpo, st, fc-apc, lsh-apc, mdc, splice`. So `lc` and `sc` need
# a polish to name a type at all; `fc` and `lsh` appear only as APC, and the
# rest have one form. A contract states the polish only where it changes the
# answer - demanding it everywhere would be noise, and inventing it where the
# enum has no second form would be a fact nobody asked for.
POLISHED = ("lc", "sc")
FIXED_POLISH = {"fc": "apc", "lsh": "apc"}


def family_of(ref):
    """`common/mpo-adapter@1` -> `mpo`, or None for a part that is not fibre."""
    return FAMILY.get(str(ref).split("@")[0])


def port_type(family, polish):
    """The DCIM port type for a family, or None when the family is unknown."""
    if family is None:
        return None
    if family in POLISHED:
        return f"{family}-{polish}" if polish else None
    if family in FIXED_POLISH:
        return f"{family}-{FIXED_POLISH[family]}"
    return family

"""A module's fibre graph, projected into DCIM ports and fibre-map rows.

PURE. Everything here takes an index entry and returns data; nothing opens a
file or writes one. That is what lets the projection be unit-tested without a
build, and it is why the naming rules live here rather than inside
`dcim_export.py`, which is already 900 lines of I/O.

See docs/optical-paths-design.md section C.
"""
from portrayal import optical
# WHICH CONNECTOR FAMILY EACH PART IS. The ref is the fact; the family is what
# the port-type enum is keyed on. A part absent from this table carries no
# fibre as far as the projection is concerned, which is the same answer
# `optical.capacities` gives for a part with no `optical.positions`.
FAMILY = {
    "common/lc-duplex-adapter": "lc",
    "common/lc-duplex-v-adapter": "lc",
    "common/lc-duplex-shuttered-adapter": "lc",
    "common/sc-duplex-adapter": "sc",
    "common/mpo-adapter": "mpo",
    "common/mpo-flange-adapter": "mpo",
    "common/mpo24-flange-adapter": "mpo",
    # DCIM has one MPO port type; the fibre count is the port's `positions`
    "common/mpo16-adapter": "mpo",
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
    """`common/mpo-adapter@2` -> `mpo`, or None for a part that is not fibre."""
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


def _front_parts(entry):
    """This module's own fibre parts, in front-port numbering order.

    ORDER IS THE NUMBERING, but position is only SOMETIMES where that order
    comes from. For a single row of connectors, `at.x` left to right IS the
    vendor's own numbering - a safe derivation, not a guess, and every
    single-row module in this library is projected that way with nothing
    stated about it. A face with more than one row is a different question:
    whether the vendor numbers row then row or column then column, and which
    row comes first, is a fact about the SILKSCREEN, not a fact `at.x` and
    `at.y` can be sorted into - GEOMETRY CANNOT DETERMINE A SILKSCREEN, and
    guessing a rule from the one multi-row sample this library happens to
    hold is exactly how the 12.90-vs-13.2 pitch confusion started. So a
    module states `optical.front-order` explicitly where geometry cannot
    answer (L88 requires it), and this reads that order in preference to
    `at.x` whenever it is present, falling through to the position-based
    derivation otherwise. A test checks the single-row derivation against the
    numbering the contract states, rather than trusting that they agree.
    """
    parts = {}
    for part in (entry.get("parts") or []):
        if not isinstance(part, dict) or not part.get("id"):
            continue
        if family_of(part.get("ref") or "") is None:
            continue
        parts[str(part["id"])] = part

    front_order = (entry.get("optical") or {}).get("front-order")
    if front_order:
        return [(float(i), pid, parts[pid]["ref"])
                for i, pid in enumerate(front_order) if pid in parts]

    out = [(float((p.get("at") or [0, 0])[0]), pid, p["ref"])
           for pid, p in parts.items()]
    return sorted(out)


def front_label(entry, endpoint, load_ref):
    """The vendor's number for a front endpoint, as a string.

    `load_ref` IS NOT OPTIONAL. `capacities` learns a connector's width by
    resolving its ref, so a lookup that answers None makes every width zero and
    every label off by the whole face - silently, because the result is still a
    plausible string.
    """
    face, part, pos = optical.split_endpoint(endpoint)
    if face:
        return None                      # a rear endpoint has no front label
    caps = optical.capacities(entry, load_ref)
    n = 0
    for _x, pid, ref in _front_parts(entry):
        width = caps.get(pid) or 0
        if pid == part:
            return str(n + pos)
        n += width
    return None


def ports(entry, load_ref):
    """`{"front": [...], "rear": [...]}` for one module entry.

    A REAR CONNECTOR IS ONE PORT CARRYING MANY POSITIONS; a front fibre is one
    port carrying one. That asymmetry is section C1, and it is what makes the
    projection lossless for a cassette whose front and rear do not correspond
    one to one.
    """
    caps = optical.capacities(entry, load_ref)
    polish = (entry.get("optical") or {}).get("polish")
    rear_kind = (entry.get("optical") or {}).get("rear-kind")

    front, n = [], 0
    for _x, pid, ref in _front_parts(entry):
        t = port_type(family_of(ref), polish)
        for i in range(1, (caps.get(pid) or 0) + 1):
            n += 1
            front.append({"name": str(n), "type": t, "positions": 1})

    rear = []
    names = rear_port_names(entry, load_ref)
    for key in sorted(k for k in caps if ":" in k):
        face, pid = key.split(":", 1)
        ref = _face_part_ref(entry, face, pid, load_ref)
        t = port_type(family_of(ref), polish) or rear_kind
        rear.append({"name": names[pid], "type": t, "positions": caps[key]})
    return {"front": front, "rear": rear}


def rear_port_names(entry, load_ref):
    """`{part id: port name}` for this module's rear connectors.

    BUILT ONCE AND SHARED, because the fibre map needs the same mapping and the
    obvious way to get it there - splitting the port name back on "-" - is wrong
    for a part id that contains one. `optical.py`'s own docstring uses `mtp-1.3`
    as its example endpoint, so hyphenated ids are not hypothetical, and
    `"MTP-1-1".split("-")[0]` recovers `mtp` rather than `mtp-1`: every row for
    such a part would name a rear port that does not exist.
    """
    caps = optical.capacities(entry, load_ref)
    out, seen = {}, {}
    for key in sorted(k for k in caps if ":" in k):
        pid = key.split(":", 1)[1]
        seen[pid] = seen.get(pid, 0) + 1
        out[pid] = f"{pid.upper()}-{seen[pid]}"
    return out


def _face_part_ref(entry, face, pid, load_ref):
    """The component ref of a part drawn on one of this module's faces."""
    ref = ((entry.get("faces") or {}).get(face) or {}).get("ref")
    doc = load_ref(ref) if ref else None
    for part in ((doc or {}).get("parts") or []):
        if isinstance(part, dict) and str(part.get("id")) == pid:
            return part.get("ref")
    return None


def fibre_map(entry, load_ref, model):
    """The per-instance front-to-rear bindings, as a flat row list.

    THE DEVICE-TYPE YAML NO LONGER CARRIES THIS. netbox#20564 replaced the
    FrontPort->RearPort FK with a bidirectional M2M, and the front-port schema
    is `{name, type, positions}` with `additionalProperties: false` and no
    `rear_port` key - so the mapping has nowhere to live in the type format and
    ships beside it instead.

    THERE IS NO UPSTREAM SCHEMA FOR THIS ARTEFACT, so this defines one. It is
    generated only and never hand-edited, which keeps the contracts the single
    source; and it is deliberately boring - a flat row list, no nesting - so
    feeding it to a script or an API is a five-line job.
    """
    opt = entry.get("optical") or {}
    rear_name = rear_port_names(entry, load_ref)

    rows = []
    for path in (opt.get("paths") or []):
        legs = optical.endpoints(path)
        src, _ = legs[0]
        for dst, ratio in legs[1:]:
            rows.append(_row(entry, src, dst, ratio, rear_name, load_ref))
    rows = [r for r in rows if r]
    rows.sort(key=lambda r: (r["rear"], r["rear_position"]))
    out = {"model": model}
    if opt.get("media"):
        out["media"] = opt["media"]
    if opt.get("polarity"):
        out["polarity"] = opt["polarity"]
    out["rows"] = rows
    return out


def _row(entry, a, b, ratio, rear_name, load_ref):
    """One leg as a row, whichever end of it is the rear."""
    fa, pa, na = optical.split_endpoint(a)
    fb, pb, nb = optical.split_endpoint(b)
    if fa and not fb:
        rear_ep, front_ep = (fa, pa, na), (fb, pb, nb)
    elif fb and not fa:
        rear_ep, front_ep = (fb, pb, nb), (fa, pa, na)
    else:
        return None                      # front-to-front or rear-to-rear
    _f, rpid, rpos = rear_ep
    _g, _fpid, _fpos = front_ep
    label = front_label(entry, f"{_fpid}.{_fpos}", load_ref)
    row = {"front": label, "front_position": 1,
           "rear": rear_name.get(rpid, rpid.upper()), "rear_position": rpos}
    if ratio is not None:
        row["ratio"] = ratio
    return row

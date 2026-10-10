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
    "common/sc-simplex-adapter": "sc",
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
# A LATENT GAP, NOT A LIVE ONE: Nautobot's PortTypeChoices has no `mdc` and no
# `fc-apc` (nautobot cb08ef68, dcim/choices.py ~1229), where NetBox has both
# (netbox a6e0fa03, v4.7.2, dcim/choices.py ~1673). Nothing exported today
# composes either family, so no committed Nautobot file carries one; the first
# module that does will need a Nautobot answer before it ships.


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
        # an entry may name one position (`lc07.2`, see `bore_order`); the
        # PARTS are numbered in the order each is first named
        out, seen = [], set()
        for item in front_order:
            pid = split_order_item(item)[0]
            if pid in parts and pid not in seen:
                seen.add(pid)
                out.append((float(len(out)), pid, parts[pid]["ref"]))
        return out

    out = [(float((p.get("at") or [0, 0])[0]), pid, p["ref"])
           for pid, p in parts.items()]
    return sorted(out)


def split_order_item(item):
    """`(part id, position or None)` for one `optical.front-order` entry.

    A bare part id means the part, its positions counted 1 upward. `lc07.2`
    means one position of it. Part ids are segments and hold no dot, so the
    split is unambiguous; a suffix that is not a whole number from 1 leaves the
    item as a part id nothing will match, which L88 reports.
    """
    s = str(item)
    pid, dot, pos = s.rpartition(".")
    if dot and pos.isdigit() and int(pos) >= 1:
        return pid, int(pos)
    return s, None


def bore_order(entry):
    """`{part id: [positions, in numbering order]}` where a module states one.

    WITHIN A CONNECTOR, POSITION ORDER IS USUALLY THE NUMBERING, AND NOT ALWAYS.
    A duplex adapter's positions are its own - bore 1, bore 2 - and counting
    them in that order is right wherever the adapter stands the way it was
    drawn. Turn it over, as the lower row of a belly-to-belly holder is, and
    bore 1 is on the other hand: the fibres still enter the bores they enter,
    but a reader counting ports along the row meets bore 2 first. That is a
    fact about the face, like the order of the parts themselves, so it is
    stated in the same place: `front-order` names the positions one by one,
    `lc07.2, lc07.1`, for a part whose numbering does not run 1 upward. A part
    named bare is absent from the result and counts as it always did.
    """
    out = {}
    for item in ((entry.get("optical") or {}).get("front-order") or []):
        pid, pos = split_order_item(item)
        if pos is not None:
            out.setdefault(pid, []).append(pos)
    return out


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
    order = bore_order(entry)
    n = 0
    for _x, pid, ref in _front_parts(entry):
        width = caps.get(pid) or 0
        if pid == part:
            if pid in order:
                # the position's place in the stated order, not its own number
                return str(n + order[pid].index(pos) + 1) if pos in order[pid] else None
            return str(n + pos)
        n += width
    return None


# WHICH FAMILIES ARE ONE PORT PER CONNECTOR ON THE FRONT. A front LC or SC bore
# is one fibre and one DCIM port, which is why the front numbering counts
# fibres. An MPO adapter on a panel's FRONT is one connector a 12- or 16-fibre
# trunk plugs into whole - twelve one-fibre "mpo" ports would be a port nobody
# can cable. So an MPO front is one port with a position per fibre, exactly as
# a rear connector already is. `front_label` keeps counting fibres: it is the
# explorer's and L109's number, not a DCIM port name.
GROUPED_FRONT = ("mpo",)


def front_port(entry, endpoint, load_ref):
    """`(port name, position)` for a front endpoint in the DCIM export, or None.

    A fibre-per-port family names its port with the fibre's `front_label` at
    position 1; a GROUPED_FRONT family names one port per connector, counted in
    front order, and the fibre is a position on it. Both counters advance over
    the same front order, so a module mixing the two numbers each kind on.
    """
    face, part, pos = optical.split_endpoint(endpoint)
    if face:
        return None
    for name, pid, _ref, grouped in _front_port_names(entry, load_ref):
        if pid == part:
            return (name, pos) if grouped else (front_label(entry, endpoint, load_ref), 1)
    return None


def _front_port_names(entry, load_ref):
    """[(first port name, part id, ref, grouped)] in front order."""
    caps = optical.capacities(entry, load_ref)
    out, n = [], 0
    for _x, pid, ref in _front_parts(entry):
        grouped = family_of(ref) in GROUPED_FRONT
        out.append((str(n + 1), pid, ref, grouped))
        n += 1 if grouped else (caps.get(pid) or 0)
    return out


def trunk_positions(entry, load_ref):
    """`{part id: [positions, ascending]}` that `optical.trunk` names.

    THE TRUNK IS STATED, NOT INFERRED (roc-ops/Portrayal#246). A single-faced
    module - a PPM coupler, a DCM, an add/drop filter - has no rear face to
    make one end the network side, and neither its part ids nor its paths'
    direction say which end it is: a cassette's paths run FROM the front, a
    coupler's FROM the common port. So the contract names it, in
    `front-order`'s grammar: a bare part id is every position of the part, and
    `dcm.2` is one. Parts are returned in the order the list first names them,
    which is the order their rear ports are listed in.
    """
    caps = optical.capacities(entry, load_ref)
    out = {}
    for item in ((entry.get("optical") or {}).get("trunk") or []):
        pid, pos = split_order_item(item)
        want = range(1, (caps.get(pid) or 0) + 1) if pos is None else [pos]
        have = out.setdefault(pid, [])
        have.extend(p for p in want if p not in have)
    return {pid: sorted(v) for pid, v in out.items()}


def is_trunk(entry, endpoint):
    """Is this endpoint the module's common end - the side a DCIM calls rear?

    A face-prefixed endpoint (`rear:mtp.3`) is, by construction: the rear
    face IS the trunk. Otherwise it is exactly when `optical.trunk` names the
    position, or names its part bare - which covers whatever positions the
    part has, so no lookup is needed to answer.
    """
    face, part, pos = optical.split_endpoint(endpoint)
    if face:
        return True
    for item in ((entry.get("optical") or {}).get("trunk") or []):
        pid, p = split_order_item(item)
        if pid == part and (p is None or p == pos):
            return True
    return False


def projects(entry):
    """Does the DCIM projection export this module's glass at all?

    It needs paths, and it needs a trunk: a declared rear face, or a stated
    `optical.trunk`. Without either there is nothing to put on a rear port,
    and front ports with no rear port are the shape netbox#21830 rejected.
    THE ONE GATE, asked by `build_module` and `export_modules` alike, so the
    port lists and the fibre map cannot disagree about which modules project.
    """
    from portrayal.faces import face_ref
    opt = entry.get("optical") or {}
    return bool(opt.get("paths")) and bool(face_ref(entry, "rear") or opt.get("trunk"))


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

    # A TRUNK POSITION LEAVES THE FRONT LIST AND THE NUMBERING DOES NOT SKIP
    # IT. Front ports are named as `front_label` counts, every position along
    # the face, so an OCU whose common adapter is the trunk exports its legs as
    # `3` and `4` - the faceplate's own count, with an honest gap - and no
    # published number changes meaning.
    trunk = trunk_positions(entry, load_ref)
    front, n = [], 0
    for _x, pid, ref in _front_parts(entry):
        t = port_type(family_of(ref), polish)
        width = caps.get(pid) or 0
        kept = [i for i in range(1, width + 1) if i not in trunk.get(pid, ())]
        if family_of(ref) in GROUPED_FRONT:
            n += 1
            if kept:
                front.append({"name": str(n), "type": t, "positions": len(kept)})
            continue
        for i in range(1, width + 1):
            n += 1
            if i in kept:
                front.append({"name": str(n), "type": t, "positions": 1})

    rear = []
    names = rear_port_names(entry, load_ref)
    for key in sorted(k for k in caps if ":" in k):
        face, pid = key.split(":", 1)
        ref = _face_part_ref(entry, face, pid, load_ref)
        t = port_type(family_of(ref), polish) or rear_kind
        rear.append({"name": names[pid], "type": t, "positions": caps[key]})
    refs = {str(p["id"]): p.get("ref") for p in (entry.get("parts") or [])
            if isinstance(p, dict) and p.get("id")}
    for pid, positions in trunk.items():
        rear.append({"name": names[pid],
                     "type": port_type(family_of(refs.get(pid) or ""), polish),
                     "positions": len(positions)})
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
    # A STATED TRUNK PART IS NAMED THE SAME WAY, so a PPM coupler's common
    # adapter is `COMMON-1` beside a cassette's `MTP-1`. L129 keeps a trunk off
    # a module whose rear face carries fibre, so the two never share a name.
    for pid in trunk_positions(entry, load_ref):
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

    THE DEVICE-TYPE YAML THIS PROJECT WRITES DOES NOT CARRY THIS. netbox#20564
    replaced the FrontPort->RearPort FK with a bidirectional M2M, and the
    front-port schema is `{name, type, positions}` with no `rear_port` key, so
    the binding ships beside the type instead. That is no longer the only place
    it could go: NetBox >= 4.6 has type-level `port-mappings`
    (PortTemplateMapping), which a type document can carry. Adopting them is
    tracked separately; until then this map is where the binding lives.

    THERE IS NO UPSTREAM SCHEMA FOR THIS ARTEFACT, so this defines one. It is
    generated only and never hand-edited, which keeps the contracts the single
    source; and it is deliberately boring - a flat row list, no nesting - so
    feeding it to a script or an API is a five-line job.
    """
    opt = entry.get("optical") or {}
    rear_name = rear_port_names(entry, load_ref)
    trunk = trunk_positions(entry, load_ref)

    rows = []
    for path in (opt.get("paths") or []):
        # ONE ROW PER LEG, WHATEVER THE PATH'S SHAPE. `optical.legs` answers a
        # two-ended path, a split and a combine alike, and a row is a binding,
        # not a direction: a combine onto a trunk position writes the rows the
        # same glass would write as legs off it.
        for leg in optical.legs(path):
            row = _row(entry, leg["from"], leg["to"], leg["ratio"], rear_name,
                       load_ref, trunk)
            # A BANDED LEG SAYS WHICH BAND, the way a split leg says its ratio:
            # an add/drop filter puts two front ports on one rear position, and
            # without the band the map would read as a split of no stated ratio.
            # A combine's band is its source's own.
            if row and leg["band"]:
                row["band"] = dict(leg["band"])
            rows.append(row)
    rows = [r for r in rows if r]
    rows.sort(key=lambda r: (r["rear"], r["rear_position"]))
    out = {"model": model}
    if opt.get("media"):
        out["media"] = opt["media"]
    if opt.get("polarity"):
        out["polarity"] = opt["polarity"]
    out["rows"] = rows
    return out


def _row(entry, a, b, ratio, rear_name, load_ref, trunk=None):
    """One leg as a row, whichever end of it is the rear.

    THE REAR END IS THE TRUNK END, which `is_trunk` answers: a rear-face
    endpoint, or a position `optical.trunk` names. A stated trunk position is
    renumbered within its own rear port - `dcm.2` alone is position 1 of
    `DCM-1` - because that rear port carries only the trunk positions.
    """
    fa, pa, na = optical.split_endpoint(a)
    fb, pb, nb = optical.split_endpoint(b)
    ta, tb = is_trunk(entry, a), is_trunk(entry, b)
    if ta and not tb:
        rear_ep, front_ep = (fa, pa, na), (fb, pb, nb)
    elif tb and not ta:
        rear_ep, front_ep = (fb, pb, nb), (fa, pa, na)
    else:
        return None                      # front-to-front or trunk-to-trunk: L130
    rface, rpid, rpos = rear_ep
    if not rface:
        rpos = (trunk or {}).get(rpid, [rpos]).index(rpos) + 1
    _g, _fpid, _fpos = front_ep
    label, fpos = front_port(entry, f"{_fpid}.{_fpos}", load_ref) or (None, 1)
    row = {"front": label, "front_position": fpos,
           "rear": rear_name.get(rpid, rpid.upper()), "rear_position": rpos}
    if ratio is not None:
        row["ratio"] = ratio
    return row

#!/usr/bin/env python3
"""Resolve the optical graph a contract declares.

WHY A MODULE AND NOT A LINT RULE. Five rules and, later, the DCIM exporter all
need the same three things: turn `<part-id>.<n>` into a part and a position, ask
that part's own contract how many positions it has, and walk the paths. Written
once here, that is a hundred lines; written per consumer it is the same hundred
lines diverging.

Nothing here validates. These functions answer questions; lint decides which
answers are errors. That split is what lets the exporter reuse them without
inheriting lint's opinions.
"""
import re

from faces import OPTICAL_FACES, face_ref

# The optional `<face>:` prefix is what lets one module's paths reach a part
# drawn on another of its faces - a cassette's rear MTP lives in the rear face
# component's `parts:`, not in the cassette's own. Unprefixed means THIS face
# and is the spelling every contract written before faces existed uses, so the
# group is optional rather than the pattern being replaced.
ENDPOINT = re.compile(r"^(?:([a-z0-9-]+):)?([a-z0-9-]+)\.([1-9][0-9]*)$")


def split_endpoint(ep):
    """`rear:mtp.3` -> `('rear', 'mtp', 3)`; `lc1.1` -> `(None, 'lc1', 1)`.

    Raises ValueError on anything else. The face comes back separately rather
    than glued to the part id because the DCIM export's whole job is to say
    which side a port is on, and deriving that from a string later is how it
    gets derived differently in two places.
    """
    m = ENDPOINT.match(ep or "")
    if not m:
        raise ValueError(f"not an optical endpoint: {ep!r}")
    return m.group(1), m.group(2), int(m.group(3))


def part_key(face, part):
    """How `capacities` spells a part, so a caller need not reassemble it."""
    return f"{face}:{part}" if face else str(part)


def capacities(contract, load_ref):
    """Part key -> fibre positions, across this module and all of its faces.

    A part with no `optical.positions` is not a connector - a lamp, a latch, a
    silkscreen - and is absent from the result rather than present with zero.
    The difference matters: absent means "not a connector", zero would mean "a
    connector with no fibres", and only one of those is a thing.

    Only the faces that are ANOTHER SIDE of the module contribute - see
    `faces.OPTICAL_FACES`. A rear face's MTP is hardware the front does not
    have; a plan face is the same module from above, and counting a connector
    drawn there as well would make one port two endpoints. L85 reports a
    non-contributing face that draws one rather than letting it vanish.

    Faces are walked ONE LEVEL. A face is a drawing of this part from another
    direction, so its parts are this module's parts seen from there; a face of a
    face is not a thing, and L83 already rejects one.
    """
    out = {}

    def collect(doc, face):
        for part in doc.get("parts") or []:
            if not isinstance(part, dict) or not part.get("id"):
                continue
            ref = load_ref(part["ref"]) or {}
            n = (ref.get("optical") or {}).get("positions")
            if n:
                out[part_key(face, part["id"])] = int(n)

    collect(contract, None)
    # A face has two legal spellings - `faces.rear` and, for `plan` only, the
    # legacy top-level `plan:` - and `face_ref` is the one place that knows
    # both, so going through it here (rather than reading `faces` directly)
    # is what keeps a legacy-spelled contract's rear capacities visible.
    for face in OPTICAL_FACES:
        ref = face_ref(contract, face)
        if ref:
            collect(load_ref(ref) or {}, face)
    return out


def endpoints(path):
    """Every endpoint a path touches, source first, as `(endpoint, ratio)`.

    The source carries ratio None because it is not a share of anything; a
    two-ended path's destination carries None for the same reason.
    """
    out = [(path["from"], None)]
    to = path["to"]
    if isinstance(to, str):
        out.append((to, None))
    else:
        out += [(d["at"], d["ratio"]) for d in to]
    return out


def reached(contract):
    """Every endpoint any path in this contract touches."""
    out = set()
    for path in ((contract.get("optical") or {}).get("paths") or []):
        out.update(ep for ep, _ in endpoints(path))
    return out

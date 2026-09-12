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

ENDPOINT = re.compile(r"^([a-z0-9-]+)\.([1-9][0-9]*)$")


def split_endpoint(ep):
    """`mtp-1.3` -> `('mtp-1', 3)`. Raises ValueError on anything else."""
    m = ENDPOINT.match(ep or "")
    if not m:
        raise ValueError(f"not an optical endpoint: {ep!r}")
    return m.group(1), int(m.group(2))


def capacities(contract, load_ref):
    """Composed part id -> fibre positions, for parts that declare them.

    A part with no `optical.positions` is not a connector - a lamp, a latch, a
    silkscreen - and is absent from the result rather than present with zero.
    The difference matters: absent means "not a connector", zero would mean "a
    connector with no fibres", and only one of those is a thing.
    """
    out = {}
    for part in contract.get("parts") or []:
        if not isinstance(part, dict) or not part.get("id"):
            continue
        ref = load_ref(part["ref"]) or {}
        n = (ref.get("optical") or {}).get("positions")
        if n:
            out[str(part["id"])] = int(n)
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

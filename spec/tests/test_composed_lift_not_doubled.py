"""A composed part's lift must be counted once, not twice.

relief.js reads `data-z-out` as an ABSOLUTE distance from the panel and SUMS
`data-z-lift` up the ancestor chain (kit/relief.js `liftOf`). render.py's
`_inset_feature` therefore has to fold a part's `lift` into the `out` values of
the features inside it - which are absolute - and must NOT fold it into their
`lift` values, which the ancestor already supplies.

It folded it into both. Composing common/lc-duplex-adapter@5 onto
smartoptics/dcp-f-a22's plate at `lift: 44` put 44 on the adapter's group AND
rewrote each dust cap's own 3.175 lift to 47.175, so relief.js summed 91.175
against an `out` of 50.35 and built each cap as a box whose front face was 40mm
BEHIND its back. They rendered as white spikes standing off the faceplate.

It has a second shape, found in review on the fix's own PR and confirmed by
seating the other occupant the A22 accepts: a module in a bay that carries a lift
got the lift on its group and its own relief left panel-relative, so every
feature on smartoptics/ppm-ad1-1510@2 went 40mm negative in the A22's raised
block. That went unseen because the bay's DEFAULT is ppm-dummy, which declares no
relief at all - so `dcp-2`'s `ila-node` configuration exists partly to give this
a live subject. The invariant is general, so this is:

    a feature's own extent is `out` minus the summed lift under it, and a solid
    cannot have negative extent.

IT NOW SWEEPS EVERY SOLID, not only the composed ones. It was scoped to nodes
with an ancestor contributing lift, because a second and unrelated defect held
three nodes below zero - common/qsfp-pull-tab@1's crossbar wrote `out` as a
THICKNESS rather than a distance from the panel, so the same arithmetic caught it
for a reason this test was not about. That contract is fixed, so the scope comes
off: a solid cannot have negative extent, whatever put it there.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"


def negative_boxes(path):
    """(id, own lift, out, summed lift) for every solid with negative extent."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    parent = {c: p for p in root.iter() for c in p}
    out = []
    for el in root.iter():
        raw = el.get("data-z-out")
        if raw is None:
            continue
        # EVERY SOLID, not only the composed ones. This was scoped to nodes with
        # an ancestor contributing lift, because the library still held three
        # that failed for a different reason - common/qsfp-pull-tab@1's crossbar
        # wrote `out` as a thickness. That is fixed, the sweep now finds nothing
        # anywhere, and a scoped invariant is only as good as the reason it was
        # scoped.
        lift, node = 0.0, el
        while node is not None:
            lift += float(node.get("data-z-lift") or 0)
            node = parent.get(node)
        try:
            box = float(raw) - lift
        except ValueError:
            continue
        if box < -1e-6:
            out.append((el.get("id"), el.get("data-z-lift"), raw, lift, box))
    return out


def test_no_solid_has_negative_extent():
    if not DIST.exists():
        pytest.skip("library/dist not built")
    files = sorted(DIST.rglob("*.svg"))
    assert files, "no compiled drawings to check"
    bad = []
    for f in files:
        for i, own, out, lift, box in negative_boxes(f):
            bad.append(
                f"{f.name}: {i} has out={out} under a summed lift of {lift:g} "
                f"(its own data-z-lift is {own}), so its extent is {box:+.3f}. "
                "Either a lift carried by an ancestor group was folded into "
                "this node's own lift as well (see _inset_feature's group_lift), "
                "or the contract wrote `out` as a thickness rather than as a "
                "distance from the panel."
            )
    assert not bad, "features built inside out:\n  " + "\n  ".join(bad)


def test_the_a22s_adapters_stand_the_same_height_as_they_do_alone():
    """The case that found it, pinned to the number rather than to a sign.

    An LC adapter's bezel stands 3.175 proud of its face. Composed onto a plate
    44 off the chassis it must still stand 3.175 proud of that plate - lifting
    the carrier moves a part, it does not stretch it. (This measured the dust
    caps until they left the adapter to become occupants of the bores; the
    bezel is the same kind of raised feature on the same composed part.)
    """
    a22 = DIST / "components" / "smartoptics--dcp-f-a22--v1--default.svg"
    lone = DIST / "components" / "common--lc-duplex-adapter--v4--default.svg"
    if not (a22.exists() and lone.exists()):
        pytest.skip("components not built")

    def extents(path, want):
        root = ET.parse(path).getroot()
        parent = {c: p for p in root.iter() for c in p}
        got = {}
        for el in root.iter():
            i = el.get("id") or ""
            if not i.endswith(want) or el.get("data-z-out") is None:
                continue
            # the ADAPTER's bezel: a lamp has a `--bezel` of its own
            host = parent.get(el)
            if path == a22 and not (host is not None and
                                    (host.get("data-ref") or "").startswith("common/lc-duplex-adapter@")):
                continue
            lift, node = 0.0, el
            while node is not None:
                lift += float(node.get("data-z-lift") or 0)
                node = parent.get(node)
            got[i] = round(float(el.get("data-z-out")) - lift, 4)
        return got

    alone = extents(lone, "--bezel")
    assert alone, "the bare adapter draws no raised bezel; this test asserts nothing"
    ref = next(iter(alone.values()))
    composed = extents(a22, "--bezel")
    assert composed, "the A22 composes no adapter bezel"
    for i, v in composed.items():
        assert v == ref, (
            f"{i} stands {v} proud where the same bezel on a bare adapter stands "
            f"{ref}. Lifting the carrier moved the part; it must not have "
            "resized it."
        )

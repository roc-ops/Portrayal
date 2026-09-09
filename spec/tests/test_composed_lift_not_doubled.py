"""A composed part's lift must be counted once, not twice.

relief.js reads `data-z-out` as an ABSOLUTE distance from the panel and SUMS
`data-z-lift` up the ancestor chain (kit/relief.js `liftOf`). render.py's
`_inset_feature` therefore has to fold a part's `lift` into the `out` values of
the features inside it - which are absolute - and must NOT fold it into their
`lift` values, which the ancestor already supplies.

It folded it into both. Composing common/lc-duplex-adapter@3 onto
smartoptics/dcp-f-a22's plate at `lift: 44` put 44 on the adapter's group AND
rewrote each dust cap's own 3.175 lift to 47.175, so relief.js summed 91.175
against an `out` of 50.35 and built each cap as a box whose front face was 40mm
BEHIND its back. They rendered as white spikes standing off the faceplate.

It has a second shape, found by CodeRabbit on the fix's own PR and confirmed by
seating the other occupant the A22 accepts: a module in a bay that carries a lift
got the lift on its group and its own relief left panel-relative, so every
feature on smartoptics/ppm-ad1-1510@1 went 40mm negative in the A22's raised
block. That went unseen because the bay's DEFAULT is ppm-dummy, which declares no
relief at all - so `dcp-2`'s `ila-node` configuration exists partly to give this
a live subject. The invariant is general, so this is:

    a feature's own extent is `out` minus the summed lift under it, and a solid
    cannot have negative extent.

Scoped to elements that HAVE an ancestor contributing lift, which is exactly the
composed case this guards. A part that declares `lift` above its own `out` on
one node is a different defect, in a contract rather than in the renderer, and
common/qsfp-pull-tab@1's crossbar is an open example of it.
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
        # only the composed case: something ABOVE this node has to contribute lift
        anc, node = 0.0, parent.get(el)
        while node is not None:
            anc += float(node.get("data-z-lift") or 0)
            node = parent.get(node)
        if not anc:
            continue
        lift = anc + float(el.get("data-z-lift") or 0)
        try:
            box = float(raw) - lift
        except ValueError:
            continue
        if box < -1e-6:
            out.append((el.get("id"), el.get("data-z-lift"), raw, lift, box))
    return out


def test_no_composed_feature_has_negative_extent():
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
                "A lift carried by an ancestor group has been folded into this "
                "node's own lift as well - see _inset_feature's group_lift."
            )
    assert not bad, "features built inside out:\n  " + "\n  ".join(bad)


def test_the_a22s_dust_caps_stand_the_same_height_as_they_do_alone():
    """The case that found it, pinned to the number rather than to a sign.

    A dust cap on a bare adapter stands 3.175 proud of its bezel. Composed onto
    a plate 44 off the chassis it must still stand 3.175 proud of that plate -
    lifting the carrier moves a part, it does not stretch it.
    """
    a22 = DIST / "components" / "smartoptics--dcp-f-a22--v1--default.svg"
    lone = DIST / "components" / "common--lc-duplex-adapter--v3--default.svg"
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
            lift, node = 0.0, el
            while node is not None:
                lift += float(node.get("data-z-lift") or 0)
                node = parent.get(node)
            got[i] = round(float(el.get("data-z-out")) - lift, 4)
        return got

    alone = extents(lone, "--cap-tx")
    assert alone, "the bare adapter draws no cap-tx; this test asserts nothing"
    ref = next(iter(alone.values()))
    composed = extents(a22, "--cap-tx")
    assert composed, "the A22 composes no cap-tx"
    for i, v in composed.items():
        assert v == ref, (
            f"{i} stands {v} proud where the same cap on a bare adapter stands "
            f"{ref}. Lifting the carrier moved the part; it must not have "
            "resized it."
        )

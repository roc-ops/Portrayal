"""A `sink` measures down from a cavity floor, so it needs a cavity above it.

relief.js collects `data-z-sink` in exactly ONE place - inside the map over
cavity nodes, as a feature of the recess it sits in:

    const features = [...el.querySelectorAll('[data-z-top],[data-z-sink]')]

where `el` carries `data-depth`. A sink with no cavity above it is collected by
nothing and drawn by nothing, and nothing says so. It is not a rendering bug: the
contract used a key that only means something in a context the node is not in.

WHAT IT COST BEFORE ANYONE LOOKED. 520 nodes across the library were declared and
never built - `common/qsfp-pull-tab@1`'s speed cut through the crossbar, the fan
apertures and vent field on the DCP-2's modules, and 490 copies of the inset
moulded into `common/lc-duplex-adapter@3`'s dust caps. The last one is the reason
this is a test and not a note: the inset sat at 9.525 and the cap it is moulded
into ended at 6.35, so the two disagreed about where the cap's front was for as
long as they both existed, and the disagreement was invisible BECAUSE the inset
was never drawn. A feature nothing builds is a feature nothing checks. (#230)

`pocket` is the key for a recess in an otherwise solid face. It compiles to
`data-depth` - the cavity relief.js already knows how to build, floor taken from
the node's own art - so the fix is a word, not geometry.

Two sweeps, because the defect has two ends. L77 catches it in a contract before
it compiles; this catches it in the compiled drawing, where a renderer could put
one back without any contract asking for it.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"


def _parents(root):
    return {c: p for p in root.iter() for c in p}


def _ancestor_with(parent, el, attr):
    n = parent.get(el)
    while n is not None:
        if n.get(attr) is not None:
            return n
        n = parent.get(n)
    return None


def test_no_sink_is_drawn_outside_a_cavity():
    if not DIST.exists():
        pytest.skip("library/dist not built")
    files = sorted(DIST.rglob("*.svg"))
    assert files, "no compiled drawings to check"
    orphans = {}
    seen = 0
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        parent = _parents(root)
        for el in root.iter():
            if el.get("data-z-sink") is None:
                continue
            seen += 1
            if _ancestor_with(parent, el, "data-depth") is None:
                orphans.setdefault(el.get("id") or "<no id>", []).append(f.name)

    assert seen, (
        "no drawing carries a data-z-sink at all, so this sweep asserts nothing. "
        "Either the library stopped using sinks or the attribute was renamed.")
    assert not orphans, (
        "sinks with no cavity above them - declared, collected by nothing, drawn "
        "by nothing:\n  " + "\n  ".join(
            f"{i} in {len(fs)} drawing(s), e.g. {fs[0]}"
            for i, fs in sorted(orphans.items())))


def test_a_pocket_does_not_swallow_the_cavity_it_sits_in():
    """The trap on the other side of the fix, which is why it is checked.

    `cavities` takes only the INNERMOST recess of a nest:

        [...q('[data-depth]')].filter(el => !el.querySelector('[data-depth]'))

    so a pocket that lands inside an existing cavity does not add a recess - it
    DELETES the one it landed in, and the port cage or aperture that was being
    drawn there vanishes. Turning 520 sinks into pockets is exactly the change
    that could do that, and none of them did. Anything nested here is a real
    composition - a jack inside a port cage - not a feature of one part.
    """
    if not DIST.exists():
        pytest.skip("library/dist not built")
    bad, nested = [], 0
    for f in sorted(DIST.rglob("*.svg")):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        parent = _parents(root)
        for el in root.iter():
            if el.get("data-depth") is None:
                continue
            host = _ancestor_with(parent, el, "data-depth")
            if host is None:
                continue
            nested += 1
            # A COMPOSED INSTANCE IS NOT A FEATURE. A jack inside a port cage is
            # two parts, and the outer one yielding its recess to the inner one is
            # how the library has always drawn a seated port - all 2094 nested
            # cavities in the dist are of that kind. What must never appear is an
            # inner cavity that is a node of the OUTER part's own skin, because
            # that one is a feature of the recess and has just deleted it.
            if el.get("data-ref") is None:
                bad.append(f"{f.name}: {el.get('id')} sits inside "
                           f"{host.get('id')} and is not a composed part, so "
                           "relief.js builds this one and drops that one")
    assert nested, (
        "no drawing nests a cavity inside a cavity, so this sweep asserts "
        "nothing - it can no longer tell a safe nest from a buried one")
    assert not bad, ("a feature-level pocket buried the cavity it was pressed "
                     "into:\n  " + "\n  ".join(sorted(set(bad))[:20]))

"""A component's base plate must never be raised over its own skin.

render.py raises a relief node carrying `out` (or cyl/bar/uhandle/dome) to the
end of the instance group, so that a bezel standing proud paints over the parts
the component composes. That is right for a bezel and catastrophic for a BASE
PLATE, which is the thing every other mark in the skin is drawn on.

The guard for it read "only when there ARE composed parts - otherwise this
reorders the skin's own draw order and a raised base plate paints over its own
detail". It named the failure and then guarded only half of it. With parts, the
raise fired anyway: smartoptics/dcp-404 declares `out: 2.5` on `body`, composes
cages, lamps and warning triangles, and shipped with its plate moved to the end
of the group - covering every vent and every silkscreen line on the faceplate.

It was invisible to every gate. Lint passed, devicelock passed, the whole suite
passed, and the component's own skin file was correct all along; only the
compiled output was wrong, and only a person looking at the picture caught it.
Hence this test, which looks at the compiled output.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"

# id suffix of the first drawable element in each skin, i.e. its base plate
BASE_PLATE = {
    "smartoptics--dcp-404--v1--default.svg": "body",
    "common--lc-duplex-adapter--v6--default.svg": "bezel",
}

NONDRAWING = ("title", "defs", "style", "desc", "metadata")


def top_level(text):
    """(id, attrs) of the instance group's direct children, in draw order."""
    out = []
    for m in re.finditer(r"\n    <(\w+)([^>]*?)/?>", text):
        tag, attrs = m.group(1), m.group(2)
        if tag in NONDRAWING:
            continue
        idm = re.search(r'id="([^"]+)"', attrs)
        if idm:
            out.append((idm.group(1), attrs))
    return out


@pytest.mark.parametrize("fname,plate", sorted(BASE_PLATE.items()))
def test_the_base_plate_is_drawn_first(fname, plate):
    f = DIST / fname
    if not f.exists():
        pytest.skip(f"{fname} not built")
    kids = top_level(f.read_text())
    ids = [i for i, _ in kids]
    assert ids, f"{fname}: no drawable children found"
    want = [i for i in ids if i.endswith(f"--{plate}")]
    assert want, f"{fname}: no element ending --{plate}; ids were {ids}"
    at = ids.index(want[0])
    # A COMPOSED PART PLACED `behind: true` IS DRAWN BEFORE THE PLATE ON
    # PURPOSE, and shows through a hole cut in it: lc-duplex-adapter@3 put its
    # bores there so its dust caps painted over them (@4 has no caps and no
    # longer does). That is the one thing
    # allowed ahead of the plate - a composed part (it carries data-ref) under
    # a plate that has holes (evenodd) to show it through. Anything else there
    # is the skin's own art, painted over.
    ahead = kids[:at]
    plate_attrs = kids[at][1]
    skin_ahead = [i for i, a in ahead if "data-ref=" not in a]
    assert not skin_ahead, (
        f"{fname}: base plate {want[0]} is drawn at index {at} of {len(ids)} "
        f"instead of first, after the skin's own {skin_ahead}. Everything "
        f"before it is painted over. Draw order: {ids}"
    )
    if ahead:
        assert 'fill-rule="evenodd"' in plate_attrs, (
            f"{fname}: composed parts {[i for i, _ in ahead]} are drawn behind "
            f"base plate {want[0]}, which has no evenodd holes to show them "
            f"through, so they are painted over. Draw order: {ids}"
        )


def test_the_dcp_404_face_is_inside_the_node_that_carries_its_relief():
    """The symptom, stated as the user saw it: the printing went missing.

    It went missing TWICE, by two different mechanisms, and this test now guards
    the second because the first can no longer happen.

    In 2D the plate was raised over its own art by the renderer, which is fixed
    above and in render.py. In 3D the same contract mistake surfaced differently:
    relief's profile path builds "a height field with the node's art on it", so a
    `body` naming only the gradient rect gives a raised surface textured with a
    bare gradient and every vent and silkscreen line disappears.

    The fix is structural - `body` is a GROUP wrapping the whole face - so the
    invariant worth asserting is nesting, not draw order: the face art has to be
    INSIDE the node that carries the relief. A sibling renders in 2D and vanishes
    in 3D, which is the failure that is easy to ship and hard to see.
    """
    f = DIST / "smartoptics--dcp-404--v1--default.svg"
    if not f.exists():
        pytest.skip("dcp-404 not built")
    text = f.read_text()

    m = re.search(r'<g id="dcp-404--body"[^>]*>', text)
    assert m, "dcp-404--body is not a group; the relief node cannot carry the face art"

    # the group's own extent, by tag depth from where it opens
    depth, i, end = 0, m.start(), None
    for tok in re.finditer(r"<(/?)g\b[^>]*?(/?)>", text[m.start():]):
        if tok.group(2) == "/":
            continue
        depth += -1 if tok.group(1) else 1
        if depth == 0:
            end = m.start() + tok.end()
            break
    assert end, "dcp-404--body group never closes"
    inside = text[m.start():end]

    face = set(re.findall(r'id="(dcp-404--(?:vent|[a-z-]*silkscreen)[a-z0-9-]*)"', text))
    assert face, (
        "no vent or silkscreen element found on the DCP-404 at all; this test "
        "cannot say anything about where the face lives"
    )
    outside = sorted(i for i in face if ('id="%s"' % i) not in inside)
    assert not outside, (
        "these face elements are OUTSIDE dcp-404--body, the node that carries "
        "`out`/`profile-y`. They will draw in 2D and vanish from the 3D height "
        "field: %s" % outside
    )


def test_the_relief_node_and_the_lifted_parts_agree():
    """A part lifted less than the plate it sits on is inside the plate."""
    f = DIST / "smartoptics--dcp-404--v1--default.svg"
    if not f.exists():
        pytest.skip("dcp-404 not built")
    text = f.read_text()
    out = re.search(r'<g id="dcp-404--body"[^>]*data-z-out="([\d.]+)"', text)
    if not out:
        pytest.skip("dcp-404 body declares no out")
    plate = float(out.group(1))
    lifts = {float(v) for v in re.findall(r'data-z-lift="([\d.]+)"', text)}
    assert lifts, "the plate stands proud and no composed part is lifted onto it"
    low = sorted(v for v in lifts if v < plate)
    assert not low, (
        "parts lifted %s sit below a plate standing %s proud, so the plate "
        "swallows them" % (low, plate)
    )

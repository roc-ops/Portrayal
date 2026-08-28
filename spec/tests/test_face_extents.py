"""Every box face knows how far INTO the box it looks, and it is not the same
number on every face.

`buildFaceRelief` clamped cavity depth and FRU travel against the device's DEPTH
on all faces. That is right for front and rear and wrong for the other four:
into a top or a bottom you go the chassis HEIGHT, into a side its WIDTH. Nothing
caught it because the parts on those faces are shallow - a ground lug does not
test a depth clamp - but on a 1U server, H 44 and D 700, a top-face cavity was
free to sink 698 mm into a 44 mm box and come out of the underside.

Checked at the source, because the alternative is a WebGL context: the numbers
live in one table and the failure mode is somebody adding a face without a
`deep`, or giving it the convenient one.
"""
import re
from pathlib import Path

VIEWER = Path(__file__).resolve().parents[1].parent / "kit/viewer3d.js"

# what each face looks into: front/rear the depth, sides the width, lid and
# underside the height
EXPECTED = {"front": "D", "rear": "D", "right": "W", "left": "W",
            "top": "H", "bottom": "H"}


def _faces():
    src = VIEWER.read_text()
    body = src[src.index("const FACES = COMP"):src.index("const built = {}")]
    return {m.group(1): m.group(2) for m in
            re.finditer(r"\{view: '(\w+)',[^}]*?deep: \(\) => (\w+)", body)}


def test_every_face_declares_what_it_looks_into():
    faces = _faces()
    for view, axis in EXPECTED.items():
        assert view in faces, f"{view} has no `deep` - it will fall back to the depth"
        assert faces[view] == axis, \
            f"{view} looks into {faces[view]}, expected {axis}"


def test_the_underside_gets_a_relief_pass():
    """It was the one face left flat while 70 components sat on it - more than on
    the top. Its art is authored mirrored in both axes, which is what flipLX and
    flipLY carry through, and `flipLY` sat unused until the bottom needed it."""
    faces = _faces()
    assert "bottom" in faces, "the underside is not in FACES"
    src = VIEWER.read_text()
    body = src[src.index("const FACES = COMP"):src.index("const built = {}")]
    bottom = re.search(r"\{view: 'bottom',.*?\}", body, re.S).group(0)
    assert "flipLX: true" in bottom and "flipLY: true" in bottom, \
        "the underside is authored mirrored in both axes"


def test_the_relief_builder_uses_the_face_extent_not_the_depth():
    src = (VIEWER.parent / "relief.js").read_text()
    assert "const INTO = ctx.deep ?? D;" in src
    assert "D - 2" not in src and "D - 10" not in src, \
        "a clamp still measures against the device depth on every face"

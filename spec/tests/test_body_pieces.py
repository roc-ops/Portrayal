"""A body piece that shows a drawing paints it as it paints any other, and a
piece built where the host's frame is not the part's own is a plain box.

The kit's node tests do not draw, so the page's three.js is replaced by a
small stand-in that records what the kit asks of it (spec/tests/js/
body-pieces.mjs). The tests here read what it reports, and the lint rule that
asks a shown drawing to cover the piece.
"""
import json
import pathlib
import shutil
import subprocess

import pytest
import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]
KIT = SPEC.parent / "kit"
from portrayal import lint

node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.fixture(scope="module")
def built():
    script = SPEC / "tests/js/body-pieces.mjs"
    p = subprocess.run(["node", str(script)], capture_output=True, text=True, cwd=str(script.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@node
def test_a_round_piece_fills_its_envelope_on_every_axis(built):
    for shape, kind in (("cylinder", "cylinder"), ("ring", "extrude")):
        for axis in "xyz":
            s = built["solids"][f"{shape}-{axis}"]
            assert s["kind"] == kind and s["single"], (shape, axis)
            assert s["extents"] == [10, 20, 30], (shape, axis, s["extents"])
    assert built["boxes"] == {"kind": "box", "extents": [10, 20, 30], "color": "#123456", "single": True}


@node
def test_a_painted_box_carries_art_on_its_top_and_back_only(built):
    assert built["faces"] == ["#123456", "#123456", "art", "#123456", "#123456", "art"]


@node
def test_transparent_parts_of_a_shown_drawing_are_not_painted_black(built):
    """A drawing with clear regions was a map on a material with neither
    `transparent` nor `alphaTest`, so the clear regions came out black. It is
    given the alpha handling the kit's other canvas materials have."""
    for crop in ("a1", "a2"):
        for which, mat in built[crop].items():
            assert mat["kind"] == "basic", (crop, which)
            assert mat["transparent"] is True and mat["alphaTest"] == 0.1, (crop, which, mat)


@node
def test_a_crop_is_read_under_clamped_wrapping(built):
    """A negative repeat with an offset inside 0..1 reads backwards under the
    default clamp, so repeat wrapping is not needed - and with it a crop that
    reaches the drawing's edge can bleed the opposite edge in."""
    for crop in ("a1", "a2"):
        for which, mat in built[crop].items():
            assert (mat["wrapS"], mat["wrapT"]) == (1001, 1001), (crop, which, mat)
            assert mat["cloned"], (crop, which)
    # and the crop is where the piece stands: a piece inside the drawing...
    plan, rear = built["a1"]["plan"], built["a1"]["rear"]
    assert [round(v, 6) for v in plan["repeat"] + plan["offset"]] == [-0.15, -0.4, 0.45, 0.8]
    assert [round(v, 6) for v in rear["repeat"] + rear["offset"]] == [0.3, 0.5, 0.6, 0.4]
    # ...and one that spans it, whose crop ends on 0 and 1 and no further
    plan, rear = built["a2"]["plan"], built["a2"]["rear"]
    assert [round(v, 6) for v in plan["repeat"] + plan["offset"]] == [-0.5, -1.0, 0.5, 1.0]
    assert [round(v, 6) for v in rear["repeat"] + rear["offset"]] == [1.0, 1.0, 0.0, 0.0]


@node
def test_a_drawing_is_rasterised_once_per_build(built):
    assert built["sharedCanvas"] is True
    assert built["reloaded"] == 0


@node
def test_a_drawing_that_will_not_load_is_said_once_and_leaves_the_piece_plain(built):
    assert built["failed"] == [[], [], []]
    assert built["warned"] == 1


@node
def test_a_piece_on_a_flipped_face_is_a_plain_box(built):
    """`flipLX` and `flipLY` mirror where a face places its parts, and the
    transform the piece reads does not say so: a mirrored face judged straight
    put the art on the wrong side. A host turned or mirrored by its bay was
    already refused."""
    f = built["flips"]
    assert f["none"] is True and f["noneExplicit"] is True
    assert f["flipLX"] is False and f["flipLY"] is False and f["both"] is False
    assert f["noHostFlipped"] is False
    assert f["bayMirror"] is False


def test_the_part_view_resolves_a_piece_s_art_before_it_swaps_the_scene():
    """The art of a shown drawing is an image load. Awaited between disposing
    the old body and adding the new, it left one frame with neither."""
    src = (KIT / "viewer3d.js").read_text()
    art = src.index("await pieceArt(")
    dispose = src.index("disposeTree(box)")
    add = src.index("scene.add(box)", dispose)
    assert art < dispose < add
    # nothing is awaited between the disposal and the add
    assert "await" not in src[dispose:add]


def _part(box, faces=None, size=(100.0, 20.0, 100.0)):
    d = {"size": {"w": size[0], "h": size[1], "d": size[2]},
         "body": {"depth": size[2], "boxes": [{"id": "t", "at": [0, 0], "depth": 10.0,
                                                "confidence": "estimated", **box}]}}
    if faces:
        d["faces"] = faces
    return d


def _caught(path, data, roots=None):
    with lint.collecting() as got:
        lint.lint_component_body_boxes(path, data, roots)
    return [m for m in got.warnings + got.errors if "[L71]" in m]


def test_a_shown_axis_outside_the_enum_is_a_finding_not_a_crash():
    box = {"size": [10, 10], "shape": "cylinder", "axis": "w"}
    hits = _caught(pathlib.Path("x.yaml"), _part(box))
    assert any("`axis`" in m and "x, y or z" in m for m in hits), hits


def _library(tmp_path, w=200.0, h=100.0):
    f = tmp_path / "components/mk/part-plan/v1/contract.yaml"
    f.parent.mkdir(parents=True)
    f.write_text(yaml.safe_dump({"name": "part-plan", "size": {"w": w, "h": h, "d": 1.0}}))
    r = tmp_path / "components/mk/part-rear/v1/contract.yaml"
    r.parent.mkdir(parents=True)
    r.write_text(yaml.safe_dump({"name": "part-rear", "size": {"w": 100.0, "h": 20.0, "d": 1.0}}))
    return [str(tmp_path)]


def test_a_piece_shows_a_patch_that_lies_inside_the_plan_and_the_rear(tmp_path):
    roots = _library(tmp_path)
    faces = {"plan": {"ref": "mk/part-plan@1"}, "rear": {"ref": "mk/part-rear@1"}}
    # a 30 x 10 piece at 10, 2 and 20 deep: plan x 60..90, y 20..30; rear x 60..90, y 2..12
    ok = {"size": [30, 10], "at": [10, 2], "from": 20.0, "depth": 10.0, "shows": ["plan", "rear"]}
    assert not _caught(pathlib.Path("x.yaml"), _part(ok, faces), roots)
    # past the plan's far edge (100 deep here): the crop would tile
    far = {**ok, "from": 195.0}
    hits = _caught(pathlib.Path("x.yaml"), _part(far, faces, size=(100.0, 20.0, 250.0)), roots)
    assert any("`plan`" in m and "0..200 x 0..100" in m for m in hits), hits
    # past the rear's lower edge (20 tall)
    low = {**ok, "at": [10, 15]}
    hits = _caught(pathlib.Path("x.yaml"), _part(low, faces), roots)
    assert any("`rear`" in m and "0..100 x 0..20" in m for m in hits), hits
    # lint run on a part alone, with no library to read a drawing from, asks nothing more
    assert not _caught(pathlib.Path("x.yaml"), _part(far, faces, size=(100.0, 20.0, 250.0)))

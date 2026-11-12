"""The frame of a Chatsworth Motive vertical cable manager leaves the space its guides stand in clear.

The data sheet says the left and right side assemblies carry the T-shaped cable guides, and the
installation instructions draw the guides standing out of the centre section. No held page dimensions
a side assembly, so a frame draws each as a thin plate under its guides and not as a solid the depth
of the channel: a solid of that depth lies where the guides stand, and the 3D view draws two faces
of two solids on one plane, which shimmer.

Two things are held here, for the 20 parts (32610 to 32614 single-sided and 32620 to 32624
double-sided, each in -703 and -E03):

- a side assembly is no thicker than a plate (the door of the same part is 3 mm);
- on the built face of a part, no two solids that stand out of it have a face on one plane, facing
  the same way, over a patch they share.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

from portrayal.rack_solids import _shapes, _walk

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
PLATE_MAX = 3.0
EPS = 1e-6
PARTS = [f"{s}{w}-{c}" for s in ("3261", "3262") for w in range(5) for c in ("703", "e03")]
FACES = [(p, face) for p in PARTS for face in (("front", "rear") if p.startswith("3262") else ("front",))]

needs_dist = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")


def newest_frame(part):
    folder = LIB / "components" / "chatsworth" / f"motive-{part}-frame"
    newest = max(folder.glob("v*"), key=lambda p: int(p.name[1:]))
    return yaml.safe_load((newest / "contract.yaml").read_text())


def raised(path):
    """Each node that stands out of a built face as (id, x0, x1, y0, y1, z0, z1), z behind the outer face."""
    out = []
    for el, m, lift, _guide, _mounts in _walk(ET.parse(path).getroot()):
        if el.get("data-z-out") is None:
            continue
        o = float(el.get("data-z-out"))
        if -o >= -lift:
            continue
        for x, y, w, h in _shapes(el, m):
            out.append((el.get("id") or "", x, x + w, y, y + h, -o, -lift))
    return out


def shared_planes(boxes):
    """Pairs of boxes with a face on one plane, the same way round, over a patch they share."""
    found = []
    spans = lambda b: {"x": (b[1], b[2]), "y": (b[3], b[4]), "z": (b[5], b[6])}
    for i, a in enumerate(boxes):
        sa = spans(a)
        for b in boxes[i + 1:]:
            sb = spans(b)
            for axis in "xyz":
                if any(min(sa[k][1], sb[k][1]) - max(sa[k][0], sb[k][0]) <= EPS for k in "xyz" if k != axis):
                    continue
                for end in (0, 1):
                    if abs(sa[axis][end] - sb[axis][end]) < EPS:
                        found.append((a[0], b[0], axis, round(sa[axis][end], 3)))
    return found


@pytest.mark.parametrize("part", PARTS)
def test_a_side_assembly_is_a_plate(part):
    features = {f["node"]: f for f in newest_frame(part)["relief"]["features"]}
    for side in ("side-left", "side-right"):
        thick = features[side]["out"] - features[side].get("lift", 0)
        assert 0 < thick <= PLATE_MAX, (part, side, thick)
        assert features[side]["confidence"] == "estimated"


@needs_dist
@pytest.mark.parametrize("part,face", FACES)
def test_no_two_solids_of_a_face_share_a_plane(part, face):
    boxes = raised(DIST / f"{part}.{face}.svg")
    heads = [b for b in boxes if b[0].endswith("--head")]
    assert len(heads) == 96, "the guides are drawn: a face with none would pass for nothing"
    assert any(b[0].endswith("side-left") for b in boxes) and any(b[0].endswith("side-right") for b in boxes)
    assert shared_planes(boxes) == []

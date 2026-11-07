"""The 3D viewer's opening view holds the whole chassis box in the frame (P-0181).

A 7 ft vertical manager (PR2VD08, WMPVHC45E) opened cut off at the top and the
bottom: the old opening view put the eye two spans out - 4260 mm - and
OrbitControls pulled it back to its 2500 mm maxDistance on the first update,
where a 40 degree lens sees 1820 mm of a 2130 mm part. `kit/camera-fit.js`
takes the distance from the box, the lens and the frame's aspect instead.

The projection is re-done here, in Python and in the OpenGL convention
(camera looking down -z), and not read back from the module that is being
tested: a fit checked by its own arithmetic agrees with itself.
"""
import json
import math
import pathlib
import shutil
import subprocess

import pytest

import libdata

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
VIEWER = KIT / "viewer3d.js"
FIT = KIT / "camera-fit.js"
DIR = (0.9, 0.8, 1.6)
FOV = 40.0
# a wide stage (the explorer's 1400 x 700), a square one, and a tall phone
ASPECTS = (2.0, 1.0, 0.6)
OLD_MAX_DISTANCE = 2500.0   # controls.maxDistance before the fit moved it

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

SCRIPT = """
import {openingView} from %s;
const cases = JSON.parse(process.argv[2]);
console.log(JSON.stringify(cases.map(c => openingView(c))));
"""


def fit(cases, tmp, module=FIT):
    script = tmp / "fit-run.mjs"
    script.write_text(SCRIPT % json.dumps(module.as_uri()))
    p = subprocess.run(["node", str(script), json.dumps(cases)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def ndc(box, eye, aspect, fov=FOV):
    """Every corner of a box centred on the origin, seen from `eye` looking at the
    origin with y up, as (x, y, depth) - x and y in -1..1 inside the frame. The
    camera looks down its own -z, as a GL camera does."""
    W, H, D = box
    n = math.sqrt(sum(c * c for c in eye))
    z = [c / n for c in eye]                  # the camera's +z points back at the eye
    x = (z[2], 0.0, -z[0])                    # up x z, up = (0, 1, 0)
    n = math.hypot(x[0], x[2])
    x = (x[0] / n, 0.0, x[2] / n)
    y = (z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0])
    tv = math.tan(math.radians(fov) / 2)
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                v = (sx * W / 2 - eye[0], sy * H / 2 - eye[1], sz * D / 2 - eye[2])
                cz = sum(a * b for a, b in zip(v, z))
                cx = sum(a * b for a, b in zip(v, x))
                cy = sum(a * b for a, b in zip(v, y))
                depth = -cz
                out.append((cx / (depth * tv * aspect), cy / (depth * tv), depth))
    return out


def inside(corners, limit=1.0):
    return all(d > 0 and abs(x) <= limit and abs(y) <= limit for x, y, d in corners)


def holds(v, box, aspect):
    """The frame holds the box AND the camera can stay where the fit put it:
    OrbitControls pulls the eye in to maxDistance on its first update, and the
    far plane has to reach the back of the box from there."""
    return (inside(ndc(box, v["position"], aspect))
            and v["distance"] <= v["maxDistance"]
            and v["far"] > v["distance"] + math.sqrt(sum(c * c for c in box)) / 2)


def chassis(slug):
    doc = dict(libdata.devices())[slug]["chassis"]
    return (float(doc["width"]), float(doc["height"]), float(doc["depth"]))


TALL = ("panduit/pr2vd08", "panduit/wmpvhc45e")


def test_the_old_opening_view_cut_the_tall_parts_off():
    """The failing case, stated: the eye the old rule asked for (two spans) is
    pulled in to 2500 mm, and from there a 2130 mm part does not fit a 2:1 frame.
    If this stops being true the tests below no longer test anything."""
    for slug in TALL:
        box = chassis(slug)
        unit = [c / math.sqrt(sum(d * d for d in DIR)) for c in DIR]
        eye = [c * OLD_MAX_DISTANCE for c in unit]
        assert not inside(ndc(box, eye, 2.0)), slug


@needs_node
@pytest.mark.parametrize("slug", TALL)
@pytest.mark.parametrize("aspect", ASPECTS)
def test_a_tall_part_sits_inside_the_frame(slug, aspect, tmp_path):
    box = chassis(slug)
    [v] = fit([{"W": box[0], "H": box[1], "D": box[2], "fov": FOV, "aspect": aspect}], tmp_path)
    corners = ndc(box, v["position"], aspect)
    assert inside(corners), (slug, aspect, [(round(x, 2), round(y, 2)) for x, y, _ in corners])
    assert math.dist(v["position"], (0, 0, 0)) == pytest.approx(v["distance"])
    assert holds(v, box, aspect)


@needs_node
def test_every_chassis_in_the_library_sits_inside_the_frame(tmp_path):
    """Not only the two that were seen cut off: any box, from a 1U switch to a
    7 ft manager, at the explorer's own 2:1 stage and at a square one."""
    cases, slugs = [], []
    for slug, doc in libdata.devices():
        c = doc.get("chassis") or {}
        if not all(isinstance(c.get(k), (int, float)) and c[k] > 0 for k in ("width", "height", "depth")):
            continue
        for aspect in (2.0, 1.0):
            cases.append({"W": c["width"], "H": c["height"], "D": c["depth"], "fov": FOV, "aspect": aspect})
            slugs.append((slug, aspect))
    assert len(cases) > 200
    bad = []
    for (slug, aspect), case, v in zip(slugs, cases, fit(cases, tmp_path)):
        if not holds(v, (case["W"], case["H"], case["D"]), aspect):
            bad.append((slug, aspect))
    assert not bad, bad[:10]


@needs_node
def test_a_box_that_was_framed_keeps_the_opening_view_it_had(tmp_path):
    """A 1U switch was framed at two spans - span * (0.9, 0.8, 1.6) - and still
    is, to the digit, with the dolly limit and far plane it always had."""
    box = (438.4, 43.5, 515.0)
    [v] = fit([{"W": box[0], "H": box[1], "D": box[2], "fov": FOV, "aspect": 2.0}], tmp_path)
    span = max(box)
    assert v["position"] == pytest.approx([span * c for c in DIR])
    assert v["maxDistance"] == 2500 and v["far"] == 3000


@needs_node
def test_the_fit_is_the_nearest_not_just_a_far_one(tmp_path):
    """A box that needs more than two spans (a wide one in a narrow frame) gets
    the nearest distance that holds it, not an arbitrary one: a hair nearer and
    a corner is out of the frame."""
    box = (1000.0, 300.0, 300.0)
    [v] = fit([{"W": box[0], "H": box[1], "D": box[2], "fov": FOV, "aspect": 0.5}], tmp_path)
    assert v["distance"] > 1000 * math.hypot(*DIR)       # further out than the old two spans
    assert holds(v, box, 0.5)
    near = [c * 0.995 for c in v["position"]]
    assert not inside(ndc(box, near, 0.5), 0.92 + 1e-9)


@needs_node
def test_a_fit_that_ignores_the_dolly_limit_is_caught(tmp_path):
    """The mutant that fits the box but leaves maxDistance at 2500, which is how
    this was first fixed in the head and still cut the part off in the page."""
    src = FIT.read_text()
    old = "maxDistance: Math.max(BASE_MAX_DISTANCE, dist * 1.25),"
    assert src.count(old) == 1
    mutant = tmp_path / "camera-fit.js"
    mutant.write_text(src.replace(old, "maxDistance: BASE_MAX_DISTANCE,"))
    box = chassis("panduit/pr2vd08")
    [v] = fit([{"W": box[0], "H": box[1], "D": box[2], "fov": FOV, "aspect": 2.0}], tmp_path, module=mutant)
    assert not holds(v, box, 2.0)



def test_the_viewer_opens_both_loads_through_the_fit():
    """What the viewer does with the answer: both the device path and the
    component path place the eye with `openOn`, which applies the fit's own
    dolly limit and far plane - never a bare multiple of the span."""
    src = VIEWER.read_text()
    assert "import { openingView } from './camera-fit.js';" in src
    assert src.count("openOn(W, H, D") == 2
    assert "controls.maxDistance = v.maxDistance;" in src and "camera.far = v.far;" in src
    assert "camera.position.set(span * 0.9" not in src

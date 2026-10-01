"""A face is drawn at its own size, not at the size of the plane it sits on.

The R740xd is the first device in this library whose front is wider than its
body: Dell builds the mounting flanges into the faceplate and puts the VGA, the
power button and the health lamp in them, so the front view is the 482.6 mm rack
face over a 434 mm chassis. lint and the grader both accept that pair
(capability 6fb914d); the 3D pipeline never learned it.

Two symptoms, both visible in a render, and this file pins the second:

    the artwork was SQUASHED - a 482.6 mm drawing rasterised into a 434 mm canvas

    the relief FLOATED - `LX = x + w/2 - fw/2` with fw taken from the chassis put
    the VGA at +258.1 against a box edge at +217, hanging 41 mm off the end in
    mid-air

The arithmetic needs no browser, so it is checked in node the way relief-scope
and swap-url-refs are. The geometry half - the plate the ears stand on - needs
WebGL and is not covered here; what is covered is that the ports land on the
face and that every other face in the library keeps its plane's width.
"""
import json
import pathlib
import re
import shutil
import subprocess

import pytest

SPEC = pathlib.Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
SCRIPT = SPEC / "tests/js/rack-face-width.mjs"

# the pattern kit/relief.js reads a face's own size with
VB = re.compile(r'viewBox\s*=\s*"\s*[-\d.eE+]+\s+[-\d.eE+]+\s+([\d.eE+-]+)\s+([\d.eE+-]+)')


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_rack_face_is_placed_at_its_own_width():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["drawn"] == [482.6, 86.8], "the drawing states its size; believe it"
    assert out["ordinaryFaceUnchanged"], \
        "a face already matching its plane must not move"

    # the bug, and the fix, in one line each
    assert out["vga"]["wrong"] > out["bodyEdge"] + 40, \
        "the old maths put the VGA 40+ mm off the end of the box"
    assert out["bodyEdge"] < out["vga"]["right"] <= out["faceEdge"], \
        "the new maths puts it in the flange: outboard of the body, on the face"


def test_the_regex_reads_every_compiled_drawing():
    """A pattern that silently fails to match falls back to the plane's width -
    which is the OLD behaviour, so a bad regex would look like 'the fix did
    nothing' rather than like an error. Check it against the real drawings."""
    dist = ROOT / "library" / "dist"
    svgs = sorted(dist.glob("*.svg"))
    if not svgs:
        pytest.skip("library/dist not built")
    bad = []
    for f in svgs:
        head = f.read_text()[:600]
        m = VB.search(head)
        if not m:
            bad.append(f"{f.name}: no viewBox matched")
            continue
        dec = re.search(r'width="([\d.]+)mm"\s+height="([\d.]+)mm"', head)
        if dec and (abs(float(dec.group(1)) - float(m.group(1))) > 0.01
                    or abs(float(dec.group(2)) - float(m.group(2))) > 0.01):
            bad.append(f"{f.name}: viewBox disagrees with the declared mm size")
    assert not bad, f"{len(bad)} drawing(s) the face-size read would get wrong: {bad[:5]}"


def test_only_a_rack_face_is_wider_than_its_plane():
    """If a second device ever draws a face wider than its plane, it should be
    because it has integral ears too - not because a view was mis-sized. This
    names the exception rather than letting one accumulate quietly."""
    import yaml
    wide = []
    for p in sorted((ROOT / "library" / "devices").glob("*/*/device.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        ch = d.get("chassis") or {}
        cw, cd = ch.get("width"), ch.get("depth")
        for vn, v in (d.get("views") or {}).items():
            s = (v or {}).get("size") or {}
            face = (v or {}).get("face") or vn
            want = {"front": cw, "rear": cw, "top": cw, "bottom": cw,
                    "left": cd, "right": cd}.get(face)
            if want and s.get("w") and s["w"] > want + 0.5:
                wide.append(f"{p.parent.name}:{vn}")
    # fhd-1ufmt-n: FS's fixed 1U FHD enclosure is one flat 482.6 front plate
    # with the rack holes at its ends, and its four FHD modules mount on it
    # across 440 - wider than the 430 body - so its front is the whole plate.
    # r660: the R740xd's case in 1U - both control panels sit in the ears.
    assert set(wide) <= {"r740xd:front", "r740xd:front-lff-12", "fhd-1ufmt-n:front",
                         "r660:front", "r660:front-sff8sf", "r660:front-nobp",
                         "r660:front-e3s16", "r660:front-e3s14"}, \
        f"a face is wider than its plane and is not a known rack face: {wide}"

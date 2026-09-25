"""kit/relief.js tiltFrame / unproject / facetZ (docs/superpowers/specs/2026-09-24-tilted-facets-design.md)."""
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "js/tilt-frame.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_tilt_frame():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    o = json.loads(p.stdout.strip().splitlines()[-1])

    c30, s30 = math.cos(math.radians(30)), math.sin(math.radians(30))
    c45, s45 = math.cos(math.radians(45)), math.sin(math.radians(45))

    # Anchor stays at anchor for all facings
    assert o["up"]["anchorPt"] == [10, 50, 2]
    assert o["down"]["anchorPt"] == [10, 50, 0]
    assert o["left"]["anchorPt"] == [10, 50, 0]
    assert o["right"]["anchorPt"] == [10, 50, 0]

    # Axis step: 10 mm along the tilted axis
    # up: 10 mm down (y+10) compresses y and lifts z
    assert o["up"]["axisStep"][1] == pytest.approx(50 + 10 * c30, abs=1e-3)
    assert o["up"]["axisStep"][2] == pytest.approx(2 + 10 * s30, abs=1e-3)

    # down: 10 mm up (y-10) compresses y and lowers z
    assert o["down"]["axisStep"][1] == pytest.approx(50 + 10 * c30, abs=1e-3)
    assert o["down"]["axisStep"][2] == pytest.approx(0 - 10 * s30, abs=1e-3)

    # left: 10 mm right (x+10) compresses x and lifts z
    assert o["left"]["axisStep"][0] == pytest.approx(10 + 10 * c45, abs=1e-3)
    assert o["left"]["axisStep"][2] == pytest.approx(0 + 10 * s45, abs=1e-3)

    # right: 10 mm right (x+10) compresses x and lowers z
    assert o["right"]["axisStep"][0] == pytest.approx(10 + 10 * c45, abs=1e-3)
    assert o["right"]["axisStep"][2] == pytest.approx(0 - 10 * s45, abs=1e-3)

    # Local z: 1 mm out of part's face equals normal vector
    # up: normal = (0, -s, c), so at anchor+local_z = anchor + (0, -s30, c30)
    assert o["up"]["localZ"] == [10, round(50 - s30, 3), round(2 + c30, 3)]

    # down: normal = (0, s, c)
    assert o["down"]["localZ"] == [10, round(50 + s30, 3), round(0 + c30, 3)]

    # left: normal = (-s, 0, c), so (10-s45, 50, 0+c45)
    assert o["left"]["localZ"] == [round(10 - s45, 3), 50, round(0 + c45, 3)]

    # right: normal = (s, 0, c), so (10+s45, 50, 0+c45)
    assert o["right"]["localZ"] == [round(10 + s45, 3), 50, round(0 + c45, 3)]

    # Orthonormality: all columns unit length and orthogonal
    for facing in ['up', 'down', 'left', 'right']:
        f = o[facing]
        assert f["col0Mag"] == pytest.approx(1.0, abs=1e-3)
        assert f["col1Mag"] == pytest.approx(1.0, abs=1e-3)
        assert f["col2Mag"] == pytest.approx(1.0, abs=1e-3)
        assert f["dot01"] == pytest.approx(0.0, abs=1e-3)
        assert f["dot02"] == pytest.approx(0.0, abs=1e-3)
        assert f["dot12"] == pytest.approx(0.0, abs=1e-3)

    # Unprojection
    assert o["unprojUp"]["y"] == pytest.approx(60) and o["unprojUp"]["h"] == pytest.approx(10)
    assert o["unprojUp"]["x"] == 12 and o["unprojUp"]["w"] == 5

    # facetZ: distance from root edge times tan(deg)
    # up: root at y=40, proud edge at y=70; at py=70, d = py - r.y = 70-40 = 30
    assert o["facetZUp"] == pytest.approx(30 * math.tan(math.radians(30)), abs=1e-3)

    # down: root at y=70, proud edge at y=40; height h=30
    # at py=40 (proud edge), d = r.y + r.h - py = 40 + 30 - 40 = 30
    assert o["facetZDown"]["atProudEdge"] == pytest.approx(30 * math.tan(math.radians(30)), abs=1e-3)
    # at py=70 (root edge), d = r.y + r.h - py = 40 + 30 - 70 = 0
    assert o["facetZDown"]["atRootEdge"] == pytest.approx(0, abs=1e-3)

    # left: root at x=0, proud edge at x=25; at px=25, d = px - r.x = 25-0 = 25
    assert o["facetZLeft"] == pytest.approx(25 * math.tan(math.radians(45)), abs=1e-3)

    # right: root at x=25, proud edge at x=0; at px=0, d = r.x + r.w - px = 25+0-0 = 25
    assert o["facetZRight"] == pytest.approx(25 * math.tan(math.radians(45)), abs=1e-3)

    # tiltOf: the nearest tilted group wins over an outer one; the group itself
    # answers for itself; a node on no facet answers null
    assert o["tiltOf"] == {"deg": 30, "facing": "up", "on": "card--housing", "hostIsOptic": True}
    assert o["tiltOfSelf"] == "card--housing"
    assert o["tiltOfNone"] is None

    # faceFacing: rotate(90) turns the component clockwise on the face, so its
    # `up` looks right; a mirror in x swaps left and right only
    assert o["faceFacing"]["r90"] == ["right", "left", "up", "down"]
    assert o["faceFacing"]["mirror"] == ["up", "down", "right", "left"]
    assert o["faceFacing"]["identity"] == ["up", "down", "left", "right"]

    # tiltTools: the facet's root lift is its profile's; the anchor is the tilted
    # group's projected corner and z0 the facet's height there
    t = o["tools"]
    assert t["facetLift"] == 2
    assert t["cage"]["tilt"]["anchor"] == [20, 30] and t["cage"]["tilt"]["facing"] == "up"
    assert t["cage"]["tilt"]["z0"] == pytest.approx(2 + 10 * math.tan(math.radians(30)), abs=1e-3)
    assert t["cage"]["base"] == 5
    # a mate-to seat drawn outside the card, whose own lift is the host's whole
    # chain, stands on the facet exactly as a nested seat does - not 6 off it.
    # Its `data-for` names the untilted card, as render.py writes it.
    assert t["seat"]["base"] == 5 and t["seatLiftFromFacet"] == 1
    assert t["nestedLiftFromFacet"] == 1
    # a seat on that seat (data-for names a host tilted on the same facet)
    assert t["chained"] == 2
    # render.py's shape for a card sunk in a well: the optic's host-lift folds
    # in the card's -6.73, so it takes the card's lift as base and stands 3 off
    # the facet like its cage, not 3.73 into it
    s = o["sunk"]
    assert s["opticBase"] == pytest.approx(-6.73, abs=1e-3)
    assert s["opticFromFacet"] == pytest.approx(s["cageFromFacet"], abs=1e-3) == 3
    assert t["r90Facing"] == "right"
    assert t["noFacet"] is None

    # the facet's footprint punch, and a rect punch in a plane's pixels
    assert o["facetPunch"] == {"kind": "rect", "x": 10, "y": 20, "w": 60, "h": 40, "facet": "card--housing"}
    assert o["punchPx"] == [20, 20, 240, 160]

    # tiltGroupIn: memoised per parent and key; the same key inside an already
    # tilted group adds nothing; a different key nested there lands where it
    # would alone, so a chained optic is not tilted twice
    g = o["group"]
    assert g["memo"] and g["sameKeyInside"] and g["autoOff"]
    assert g["userData"]["anchor"] == [20, 30] and g["userData"]["on"] == "card--housing"
    assert g["nestedB"] == pytest.approx(g["aloneB"], abs=1e-3)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_out_height_at_reads_the_neighbouring_solid():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    o = json.loads(p.stdout.strip().splitlines()[-1])["outHeight"]
    assert o["pastApex"] == pytest.approx(14.25, abs=1e-3)   # the return is as tall as the apex
    assert o["midReturn"] == pytest.approx(7.125, abs=1e-3)
    assert o["flat"] == 3
    assert o["outside"] == 0


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_skirt_suppression_is_facet_to_facet():
    """A skirt wall is dropped only between two facets of one owner, against a
    neighbour with no outline standing from no higher a base. A plain profiled
    neighbour (smartoptics dcp's ramp beside its body) suppresses nothing, so a
    face without facets builds every skirt it did before."""
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    o = json.loads(p.stdout.strip().splitlines()[-1])["skirt"]
    assert o["facets"] is True
    assert o["plain"] is False and o["plainNeighbours"] == 0
    assert o["facetBesidePlain"] is False
    assert o["otherOwner"] is False
    assert o["shaped"] is False
    assert o["lifted"] is False

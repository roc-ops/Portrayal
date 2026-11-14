"""What `plan.py` computes for the closed body of two made-up boxes, kept in a file the kit reads.

`fixtures/plan_outline/body-cases.json` holds, for the synthetic three-band box and for one more
asymmetric box, the chassis, the snapped bands, the section's rows and, for every band and row, the
pieces and the loops of what the plan leaves of the body, then the outline of the union. The kit's
JavaScript (`kit/plan.js`, read by `test_plan_js.py`) must reproduce every number, so the two
implementations of the sweep cannot drift apart. This test fails when the file differs from what
`plan.py` computes. To regenerate it, from the repository root:

    PYTHONPATH=spec/tools python3 spec/tests/test_plan_body_cases.py --write
"""
import json
import pathlib
import sys

import yaml

from portrayal import plan as P

ROOT = pathlib.Path(__file__).resolve().parents[2]
FILE = ROOT / "spec/tests/fixtures/plan_outline/body-cases.json"
THREE_BAND = ROOT / "spec/tests/fixtures/plan_outline/lib/devices/fixture/rounded/device.yaml"

# a box 90 wide, 40 high and 60 deep whose end is not symmetric: an upper casting carrying a lobe on
# its left end, a flange with a lobe on its right end and chamfered corners, and a lower casting
# inset from the flange and from the rear. Every number is chosen for the tests.
ASYMMETRIC = {
    "width": 90.0, "height": 40.0, "depth": 60.0,
    "section": [[0, 0], [48, 0], [48, 14], [60, 14], [60, 24], [40, 24], [40, 40], [8, 40], [8, 24], [0, 24]],
    "plan-outline": [
        {"heights": [0, 14], "points": [[6, 14], [30, 12], [84, 12], [88, 20], [88, 56], [82, 60],
                                        [6, 60], [0, 36]]},
        {"heights": [14, 24], "points": [[2, 4], [20, 0], [70, 0], [84, 4], [84, 22], [90, 26], [90, 34],
                                         [84, 38], [84, 56], [78, 60], [10, 60], [0, 48], [0, 14]]},
        {"heights": [24, 40], "points": [[14, 24], [20, 22], [70, 22], [76, 26], [76, 46], [70, 52],
                                         [20, 52], [14, 46]]},
    ],
}


def three_band():
    ch = yaml.safe_load(THREE_BAND.read_text())["chassis"]
    return {k: ch[k] for k in ("width", "height", "depth", "section", "plan-outline")}


def sources():
    return {"the synthetic three-band box": three_band(), "an asymmetric box with a lobe on a flange": ASYMMETRIC}


def _pts(poly):
    return [[x, y] for x, y in poly]


def computed(chassis):
    """What the file holds for one chassis, all of it from `plan.py`."""
    plan = P.Plan(chassis)
    solid = []
    for s in plan.solid:
        solid.append({"band": s["band"], "heights": list(s["heights"]),
                      "pieces": [list(p) for p in s["pieces"]],
                      "loops": [_pts(lp) for lp in P.loops(s["pieces"])]})
    return {
        "chassis": chassis,
        "snaps": [list(s) for s in plan.snaps],
        "bands": [{"heights": list(b["heights"]), "points": _pts(b["points"])} for b in plan.bands],
        "rows": [[y0, y1, [list(iv) for iv in ivs]] for y0, y1, ivs in plan.rows],
        "solid": solid,
        "outline": [_pts(lp) for lp in plan.outline()],
    }


def build():
    return {
        "about": "What portrayal.plan computes for the closed body of two made-up boxes: the snapped bands, "
                 "the section's rows in the plan's frame, the pieces and loops of each band and row, and the "
                 "outline of the union. kit/plan.js reads this file and must give the same numbers. "
                 "Regenerate with: PYTHONPATH=spec/tools python3 spec/tests/test_plan_body_cases.py --write",
        "cases": [{"name": name, **computed(ch)} for name, ch in sources().items()],
    }


def test_the_body_cases_file_is_what_plan_py_computes():
    want = json.loads(json.dumps(build()))
    have = json.loads(FILE.read_text())
    assert have == want, ("fixtures/plan_outline/body-cases.json is not what portrayal.plan computes; "
                          "regenerate it with: PYTHONPATH=spec/tools python3 spec/tests/test_plan_body_cases.py --write")


def test_the_three_band_case_is_the_fixture_device():
    case = next(c for c in json.loads(FILE.read_text())["cases"] if "three-band" in c["name"])
    assert case["chassis"] == json.loads(json.dumps(three_band()))
    assert len(case["bands"]) == 3 and case["outline"]


def test_the_second_box_is_not_symmetric_and_has_lobes_on_both_ends():
    case = next(c for c in json.loads(FILE.read_text())["cases"] if "asymmetric" in c["name"])
    xs = [x for b in case["bands"] for x, _ in b["points"]]
    assert min(xs) == 0 and max(xs) == 90
    left = [y for b in case["bands"][:1] for x, y in b["points"] if x == 0]
    right = [y for b in case["bands"][1:2] for x, y in b["points"] if x == 90]
    assert left == [36] and right == [26, 34]       # a lobe tip on the left end, a flat lobe on the right


if __name__ == "__main__":
    if "--write" in sys.argv:
        FILE.write_text(json.dumps(build(), indent=1) + "\n")
        print("wrote", FILE)
    else:
        print(__doc__)

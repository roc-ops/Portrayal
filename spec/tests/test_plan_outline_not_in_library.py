"""No library device states `chassis.plan-outline` yet.

The schema accepts the key, and a device that states it would put a plan the drawings and the
3D body do not follow on the site and in the lock. A kit that has the compiled faces but not the
3D body shows holes in the top and bottom of the box, and one that predates both shows a
rectangle, so a device may state the key only after the 3D body follows it and the site has
re-vendored the kit.

THIS GUARD IS REMOVED BY THE REDRAW ORDER, the one that first gives a library device a plan
outline, after the site has re-vendored the kit. Until then the test device is synthetic and
lives in `spec/tests/fixtures/plan_outline`, never in the library.
"""
import pathlib

import yaml

from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def test_no_library_device_states_a_plan_outline():
    walked, stating = 0, []
    for f in libwalk.iter_devices([LIB]):
        walked += 1
        text = f.read_text()
        if "plan-outline" not in text:
            continue                # the cheap test first: only a file that names the key is parsed
        chassis = (yaml.safe_load(text) or {}).get("chassis") or {}
        if "plan-outline" in chassis:
            stating.append(str(f.relative_to(ROOT)))
    assert walked > 50, f"walked {walked} devices: the walk did not read the library"
    assert not stating, (
        f"{stating} state `chassis.plan-outline`; no device may until the 3D body follows it and "
        "the site has re-vendored the kit")

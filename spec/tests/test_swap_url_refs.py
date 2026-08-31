"""A seated module's `url(#...)` references follow its ids into the bay.

`render.py` has always done this in two passes - collect the renames, then
rewrite every `url(#...)` it can see - because a definition and the reference to
it are two halves of one name. `swap.js` did the first pass only, so a runtime
swap moved `<clipPath id="drive-carrier-25--w0">` to `drive-r0--module--w0` and
left `clip-path="url(#drive-carrier-25--w0)"` behind, dangling.

SVG does not fail a dangling clip-path. It draws the element UNCLIPPED, so the
symptom was a drive carrier rendering its honeycomb vents across the whole face
instead of through three windows - with nothing in the console and no broken
id anywhere a reader would look. 47 of the library's component skins carry a
`url(#...)` reference and every one of them swaps through this path.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/swap-url-refs.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_seated_module_keeps_its_references_pointing_at_its_own_ids():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["ids"] == ["drive-r0--module--w0", "drive-r0--module--hex"], out["ids"]
    assert not out["dangling"], (
        f"{out['dangling']} named by a reference that nothing defines - "
        "SVG draws that unclipped rather than failing")
    assert out["refs"] == [
        "url(#drive-r0--module--w0)",
        "url(#drive-r0--module--hex)",
        # a reference to something outside the component is left alone
        "url(#portrayal-vent)",
    ], out["refs"]

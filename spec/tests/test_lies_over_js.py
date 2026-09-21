"""An occupant sits IN what it is for; a cover sits OVER it.

shell.js's `over()` decides what `reveal()` pulls when a part is selected, and
it read every element with a `data-behaviour` and a `data-for` naming the part
as a cover. A seated optic is `data-behaviour="occupies"` `data-for="<port>"`,
so every cage swap - which ends by selecting the port - pulled the optic just
chosen and counted it in the removed chip. The predicate is now a pure function
in swap.js; this holds it to both halves of the distinction, including the
C40G's filter cover, which is `for` all four PSU bays and must still come off.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/lies-over.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_an_occupant_is_not_a_cover_of_its_host():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])
    assert out["opticOverItsPort"] is False, "a seated optic was read as a lid over its port"
    assert out["coverOverPsu1"] is True and out["coverOverPsu4"] is True, \
        "a mounts cover must still lie over every bay it is for"
    assert out["coverOverOther"] is False
    assert out["fillerOverSlot"] is True
    assert out["lampNoBehaviour"] is False
    assert out["notItself"] is False
    assert out["nullSafe"] == [False, False]

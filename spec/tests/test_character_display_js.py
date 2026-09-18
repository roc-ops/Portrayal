"""The kit reads a display's two facts, and never through the lamp path.

`statesOfEl` drops a `data-states` whose tokens are not lowercase - written that
way because several contracts put a sentence where the state names go, and a chip
called "=" sets a class nothing paints. INIT BOOT IMEM fails that same test, so
if a display's vocabulary rode `data-states` it would be dropped in silence and a
matrix that knows twenty-eight readings would read as one that knows none. Two
attributes, two readers, and this holds them apart from the JavaScript side.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/character-display.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_kit_reads_a_display_without_going_through_the_lamp_path():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["readings"] == ["INIT", "BOOT", "IMEM", "PSEQ", "PST1"]
    assert out["cells"] == 4
    assert out["matrixStates"] == [], (
        "a display's readings must not come back as a state vocabulary - "
        "they would be applied as `state-INIT` classes nothing paints")

    # the seven-segment shape: glyphs in states, capacity in characters
    assert out["digitStates"] == ["0", "1", "2", "blank"]
    assert out["digitReadings"] == []
    assert out["digitCells"] == 1

    # a lamp answers neither display question, and nothing throws on an
    # element - or a null - carrying neither
    assert out["lampReadings"] == [] and out["lampCells"] == 0
    assert out["bareReadings"] == [] and out["bareCells"] == 0
    assert out["nullCells"] == 0
    assert out["junk"] == [0, 0, 0, 0]

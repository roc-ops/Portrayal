"""The animated export must keep the colour that carries the meaning.

A GIF exists here for one reason: a blinking lamp cannot be shown in a still
picture without lying about which state the device is in. "Blinking green -
learning" and "blinking amber - fault" are different conditions, so an animated
export that keeps the blink and loses the colour has solved half the problem and
kept the wrong half.

`gif.js` is DOM-free - it takes raw frames and returns bytes - so this runs the
real encoder under node rather than asserting anything about its source text.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SPEC = Path(__file__).resolve().parents[1]
SCRIPT = SPEC / "tests/js/gif-palette.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_dominant_background_does_not_eat_the_palette():
    """Regression for the median cut that returned empty boxes.

    The weighted-median scan never adds the LAST bucket's count, so a colour
    holding more than half the pixels and sorting last in every channel is never
    reached: `cut` runs off the end and the split yields the whole box plus an
    empty one. Empty boxes still count toward the 256 budget and each takes the
    [0, 0, 0] palette branch. Measured on the S9510-28DC before the fix: 1642
    colours in, FOUR out, and not one green pixel left of the lamp the export
    was made to show.

    Without the clamp this frame encodes to 255 black entries and 2 distinct
    colours; with it, 256 distinct and none black.
    """
    out = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                         cwd=SPEC.parent, check=True)
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["entries"] == 256
    assert got["black"] == 0, f"{got['black']} of 256 palette entries are black"
    assert got["distinct"] > 200, got

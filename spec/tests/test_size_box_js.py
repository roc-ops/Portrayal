"""The 3D module view keeps the part's size box as its face.

A part that declares `head:` publishes a standalone preview whose viewBox also
holds the head and its composed parts (Task 9b, components_index.preview_box),
so the 2D module view shows the overhang. kit/relief.js reads a face drawing
from an origin of 0 0 at the face's own w x h, so the comp face crops the
preview back to the size box (`toSizeBox`), which is what it drew before the
preview grew. A preview already at its size box passes through untouched.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "spec/tests/js/size-box.mjs"
DIST = REPO / "library/dist/components"
CASES = [
    ("rj45", "generic--sfp-rj45--v1--default", "generic/sfp-rj45/v1"),
    ("qsfp", "generic--qsfp-lc--v2--default", "generic/qsfp-lc/v2"),
    ("plain", "generic--sfp-lc--v1--default", "generic/sfp-lc/v1"),
]


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    args = []
    for key, stem, ref in CASES:
        f = DIST / f"{stem}.svg"
        if not f.exists():
            pytest.skip(f"needs a build: {f.name}")
        size = yaml.safe_load((REPO / "library/components" / ref / "contract.yaml")
                              .read_text())["size"]
        args.append([key, str(f), size["w"], size["h"]])
    p = subprocess.run(["node", str(SCRIPT), json.dumps(args)], capture_output=True,
                       text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_grown_preview_is_cropped_back_to_its_size_box(out):
    assert out["rj45"]["viewBox"] == "0 0 13.55 8.55"
    assert (out["rj45"]["width"], out["rj45"]["height"]) == ("13.55mm", "8.55mm")
    assert out["qsfp"]["viewBox"] == "0 0 18.35 8.5"
    assert (out["qsfp"]["width"], out["qsfp"]["height"]) == ("18.35mm", "8.5mm")
    assert out["rj45"]["bodySame"] and out["qsfp"]["bodySame"]


def test_a_preview_at_its_size_box_is_untouched(out):
    assert out["plain"]["unchanged"]


def test_the_comp_face_asks_for_its_size_box():
    src = (REPO / "kit/viewer3d.js").read_text()
    comp = re.search(r"\{view: 'comp',.*?\}", src, re.S).group(0)
    assert "sizeBox: true" in comp
    assert "F.sizeBox ? toSizeBox(" in (REPO / "kit/relief.js").read_text()

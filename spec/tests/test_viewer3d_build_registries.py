"""A scene is cut from a document that already carries the viewer's state (#850).

viewer3d.js holds what a host has written - lamp states, pulled parts, fields -
and relief.js paints each from a per-viewer registry when a face is extracted.
A setter called before the first scene exists has nothing to repaint, so it
returns early, and the value reaches the registry only if build() puts it
there before extracting. States and pulls were; fields were not. A link's latch
colour, handed to the viewer as it was created, was kept in FIELDS and drawn
grey, and a second setFields with the same map saw nothing changed.

The viewer needs THREE and a WebGL context, so these read build() itself:
every registry is loaded, and before the first face is fetched.
"""
import re
from pathlib import Path

import pytest

VIEWER = Path(__file__).resolve().parents[2] / "kit/viewer3d.js"


def build_body():
    src = VIEWER.read_text()
    start = src.index("async function build(cfg) {")
    return src[start:src.index("\n  }\n", start)]


@pytest.mark.parametrize("load", [
    "setNodeStates(STATES, SCOPE);",
    "setReliefPulled(PULLED, SCOPE);",
    "setNodeFields(FIELDS, SCOPE);",
])
def test_build_loads_each_registry_before_the_first_face(load):
    body = build_body()
    assert load in body, f"build() never loads the registry: {load}"
    first = re.search(r"\b(svgSource|extractRelief|extractFace)\(", body)
    assert first, "build() fetches no face - the anchor this test reads has moved"
    assert body.index(load) < first.start(), f"{load} comes after the first face is fetched"

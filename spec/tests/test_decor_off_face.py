"""L44: decor whose box misses its view entirely is reported (#878).

render.py clips the panel at the view and does not grow the drawing for decor,
so a rect wholly off the face is never drawn. The EPS122's 90 W band sat at
x 601.74 on a 440 mm face, measured in a doubled frame, and nothing said so.
Decor that only runs past an edge is clipped to the metal and stays quiet.
"""
from pathlib import Path

from portrayal import lint

LIB = Path(__file__).resolve().parents[2] / "library"


def _off(decor):
    view = {"size": {"w": 440.0, "h": 44.45}, "panel": {"decor": decor}}
    with lint.collecting() as got:
        lint.lint_device_decor("t", "front", view, [str(LIB)])
    return [w for w in got.warnings if "[L44]" in w and "wholly outside" in w]


def test_decor_wholly_off_the_face_is_reported():
    assert len(_off([{"id": "band", "at": [601.74, 10.1], "size": [110.81, 1.4]}])) == 1
    assert len(_off([{"id": "low", "at": [10, 45.0], "size": [5, 2]}])) == 1
    assert len(_off([{"id": "ear", "at": [-22.65, 0], "size": [22.5, 43.7]}])) == 1


def test_decor_on_or_across_the_edge_is_not():
    assert _off([{"id": "band", "at": [301.76, 8.35], "size": [56.74, 3.19]}]) == []
    assert _off([{"id": "plate", "at": [-0.15, 0], "size": [440.3, 44.45]}]) == []

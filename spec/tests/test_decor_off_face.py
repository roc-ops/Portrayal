"""L44: decor whose box misses its view entirely is reported (#878).

render.py sizes the viewBox to the face and grows it only for the placements
the default build draws, never for decor, so a rect wholly outside is never seen. The EPS122's 90 W band sat at
x 601.74 on a 440 mm face, measured in a doubled frame, and nothing said so.
Decor that only runs past an edge, or sits where a drawn placement has grown
the drawing, is seen and stays quiet.
"""
from pathlib import Path

from portrayal import lint

LIB = Path(__file__).resolve().parents[2] / "library"


def _off(decor, placements=(), size=None):
    view = {"size": size or {"w": 440.0, "h": 44.45}, "panel": {"decor": decor},
            "components": {"placements": list(placements)}}
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


JACK = "common/rj45-ganged-eth@1"


def test_decor_where_a_drawn_part_grows_the_drawing_is_seen():
    beyond = [{"id": "ring", "ref": JACK, "at": [445.0, 10.0]}]
    band = [{"id": "behind-ring", "at": [446.0, 12.0], "size": [5, 5]}]
    assert _off(band, beyond) == []
    # an optional part is not in the default build, so it opens nothing
    assert len(_off(band, [dict(beyond[0], optional="ears")])) == 1


def test_a_view_without_a_height_is_named_by_its_width():
    got = _off([{"id": "band", "at": [601.74, 10.1], "size": [110.81, 1.4]}],
               size={"w": 440.0})
    assert len(got) == 1 and "440.0 wide face" in got[0] and "None" not in got[0]

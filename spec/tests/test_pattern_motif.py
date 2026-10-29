"""`pattern: motif` - a decor rect draws its own tile from `pattern-cells`.

A vent that is a row of separate slanted slots, or alternating V and lambda openings, is no
lattice of the fixed tiles the renderer ships. The face states the tile (`pattern-pitch`) and the
dark cells in it (`pattern-cells`, closed polygons in mm from the tile's top-left corner), and the
renderer writes them as one `<pattern>` and nothing else.

The tile's size is `pattern-pitch` and nowhere else: a motif has no base tile, so nothing is scaled.
"""
import hashlib
import json
import re
from pathlib import Path

import jsonschema
import pytest

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
SCHEMA = json.loads((SPEC / "schemas" / "device.schema.json").read_text())

from portrayal import render

# one V opening and one lambda opening in a 10 x 6 tile
CELLS = [[[0.5, 0.5], [2.0, 0.5], [3.0, 3.0], [4.0, 0.5], [5.5, 0.5], [3.0, 5.5]],
         [[6.0, 5.5], [9.5, 5.5], [8.0, 2.0]]]
PITCH = [10.0, 6.0]


def _svg(decor):
    view = {"size": {"w": 200.0, "h": 50.0}, "panel": {"decor": decor}}
    d = {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
         "chassis": {"width": 200.0, "height": 50.0, "depth": 100.0},
         "views": {"front": view}}
    out = render.render_view(d, "front", view, render.Library([str(LIB)]), config={})
    return out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")


def _motif(id_="m", at=(10.0, 10.0), cells=CELLS, pitch=PITCH, **extra):
    return {"id": id_, "at": list(at), "size": [100.0, 20.0], "pattern": "motif",
            "pattern-cells": cells, "pattern-pitch": pitch, **extra}


def _fill_id(svg, rect_id):
    m = re.search(rf'<(?:rect|path) id="{rect_id}"[^>]*fill="url\(#([^)]+)\)"', svg)
    assert m, f"{rect_id} is not filled from a pattern:\n{svg[:1200]}"
    return m.group(1)


def _pattern(svg, pid):
    m = re.search(rf'<pattern [^>]*id="{re.escape(pid)}".*?</pattern>', svg, re.S)
    assert m, f"pattern {pid} was referenced but never defined"
    return m.group(0)


def _hash(cells, pitch):
    canon = json.dumps({"cells": cells, "pitch": pitch}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()[:10]


def test_a_motif_rect_is_filled_from_a_pattern_the_size_of_its_pitch():
    svg = _svg([_motif()])
    pat = _pattern(svg, _fill_id(svg, "m"))
    assert re.search(r'<pattern [^>]*width="10"', pat), pat
    assert re.search(r'<pattern [^>]*height="6"', pat), pat
    assert 'patternUnits="userSpaceOnUse"' in pat


def test_the_motif_pattern_id_is_the_first_ten_hex_digits_of_the_hash_of_cells_and_pitch():
    svg = _svg([_motif()])
    assert _fill_id(svg, "m") == f"portrayal-motif-{_hash(CELLS, PITCH)}"


def test_each_cell_is_a_closed_polygon_filled_17191c_with_no_stroke():
    svg = _svg([_motif()])
    pat = _pattern(svg, _fill_id(svg, "m"))
    paths = re.findall(r"<path [^>]*/>", pat)
    assert len(paths) == len(CELLS), pat
    for path, cell in zip(paths, CELLS):
        expected = "M " + " L ".join(f"{x:g} {y:g}" for x, y in cell) + " Z"
        assert f'd="{expected}"' in path, path
        assert 'fill="#17191c"' in path and "stroke" not in path, path


def test_two_rects_with_the_same_cells_and_pitch_share_one_pattern():
    svg = _svg([_motif("a", at=(10.0, 10.0)), _motif("b", at=(120.0, 10.0))])
    a, b = _fill_id(svg, "a"), _fill_id(svg, "b")
    assert a == b
    assert len(re.findall(rf'<pattern [^>]*id="{re.escape(a)}"', svg)) == 1


def test_a_different_cell_list_makes_another_pattern():
    other = [[[1.0, 1.0], [4.0, 1.0], [2.5, 4.0]]]
    svg = _svg([_motif("a"), _motif("b", cells=other)])
    assert _fill_id(svg, "a") != _fill_id(svg, "b")
    assert len(re.findall(r'<pattern [^>]*id="portrayal-motif-', svg)) == 2


def test_a_different_pitch_with_the_same_cells_makes_another_pattern():
    svg = _svg([_motif("a"), _motif("b", pitch=[12.0, 6.0])])
    assert _fill_id(svg, "a") != _fill_id(svg, "b")


def test_an_offset_gives_a_translate_only_clone_and_the_tile_is_never_scaled():
    svg = _svg([_motif("a"), _motif("b", **{"pattern-offset": [2.5, 1.25]})])
    base = _fill_id(svg, "a")
    clone = _fill_id(svg, "b")
    assert clone != base and clone.startswith(base)
    head = re.search(rf'<pattern [^>]*id="{re.escape(clone)}"[^>]*>', svg).group(0)
    assert 'patternTransform="translate(2.5 1.25)"' in head, head
    assert "scale" not in head
    assert re.search(r'width="10"', head) and re.search(r'height="6"', head)
    assert "patternTransform" not in re.search(
        rf'<pattern [^>]*id="{re.escape(base)}"[^>]*>', svg).group(0)


def test_two_rects_with_the_same_offset_share_one_clone():
    off = {"pattern-offset": [2.5, 1.25]}
    svg = _svg([_motif("a", **off), _motif("b", at=(120.0, 10.0), **off)])
    a = _fill_id(svg, "a")
    assert a == _fill_id(svg, "b")
    assert len(re.findall(rf'<pattern [^>]*id="{re.escape(a)}"', svg)) == 1


def test_a_point_outside_the_tile_is_refused_naming_the_id_and_the_point():
    bad = [[[0.5, 0.5], [3.0, 0.5], [10.5, 3.0]]]
    with pytest.raises(ValueError) as e:
        _svg([_motif("louvres", cells=bad)])
    msg = str(e.value)
    assert "louvres" in msg and "10.5" in msg and "10" in msg and "6" in msg, msg


def test_a_point_below_the_tile_is_refused_naming_the_index_when_the_rect_has_no_id():
    bad = [[[0.5, 0.5], [3.0, 0.5], [2.0, -0.1]]]
    decor = _motif(cells=bad)
    del decor["id"]
    with pytest.raises(ValueError) as e:
        _svg([{"at": [0.0, 0.0], "size": [5.0, 5.0], "fill": "#222"}, decor])
    assert "-0.1" in str(e.value) and "1" in str(e.value), str(e.value)


def test_points_on_the_tile_edge_are_allowed():
    edge = [[[0.0, 0.0], [10.0, 0.0], [10.0, 6.0], [0.0, 6.0]]]
    _svg([_motif(cells=edge)])


def test_with_a_vent_depth_the_rect_is_a_vent_field_carrying_air_aperture():
    svg = _svg([_motif(vent=20)])
    m = re.search(r'<rect id="m"[^>]*>', svg).group(0)
    assert 'data-kind="vent-field"' in m and 'data-aperture="air"' in m, m


def test_without_a_vent_depth_the_rect_is_a_motif_field_and_not_an_aperture():
    svg = _svg([_motif()])
    m = re.search(r'<rect id="m"[^>]*>', svg).group(0)
    assert 'data-kind="motif-field"' in m and "data-aperture" not in m, m


# ---- the schema -------------------------------------------------------------------------------

def _device(decor):
    return {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
            "chassis": {"width": 200.0, "height": 50.0, "depth": 100.0},
            "views": {"front": {"panel": {"decor": [decor]}}}}


def _errors(decor):
    # the stub device omits the top-level keys a real one states; only the decor entry is under test
    return [e for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(_device(decor))
            if list(e.absolute_path)[:1] == ["views"]]


def _refused(decor):
    """The errors that come from the motif rules, not from an unknown key or an unknown value."""
    return [e for e in _errors(decor) if e.validator not in ("additionalProperties", "enum")]


def _plain(**extra):
    return {"at": [0.0, 0.0], "size": [10.0, 5.0], **extra}


def test_the_schema_accepts_a_motif_with_cells_and_pitch():
    assert _errors(_plain(pattern="motif", **{"pattern-cells": CELLS, "pattern-pitch": PITCH})) == []


def test_the_schema_refuses_motif_without_pattern_cells():
    assert _refused(_plain(pattern="motif", **{"pattern-pitch": PITCH}))


def test_the_schema_refuses_motif_without_pattern_pitch():
    assert _refused(_plain(pattern="motif", **{"pattern-cells": CELLS}))


@pytest.mark.parametrize("pattern", ["vent", "holes", "grille", "slots", "slots-h", "ribs", "brush"])
def test_the_schema_refuses_pattern_cells_on_any_other_pattern(pattern):
    assert _refused(_plain(pattern=pattern, **{"pattern-cells": CELLS, "pattern-pitch": PITCH}))


def test_the_schema_refuses_pattern_cells_with_no_pattern():
    assert _refused(_plain(**{"pattern-cells": CELLS, "pattern-pitch": PITCH}))


def test_the_schema_refuses_a_cell_of_fewer_than_three_points():
    assert _refused(_plain(pattern="motif", **{"pattern-cells": [[[0, 0], [1, 1]]], "pattern-pitch": PITCH}))


def test_the_schema_refuses_an_empty_cell_list():
    assert _refused(_plain(pattern="motif", **{"pattern-cells": [], "pattern-pitch": PITCH}))


# ---- no existing tile moves -------------------------------------------------------------------

# Captured once from origin/main's renderer: a plain 100 x 20 rect of each pattern on a 200 x 50 face.
MAIN = {
    "vent": '<pattern id="portrayal-vent" width="8.86" height="5.11" patternUnits="userSpaceOnUse"><path d="M 2.55 0 L 1.275 2.208 L -1.275 2.208 L -2.55 0 L -1.275 -2.208 L 1.275 -2.208 Z" fill="#17191c" /><path d="M 11.41 0 L 10.135 2.208 L 7.585 2.208 L 6.31 0 L 7.585 -2.208 L 10.135 -2.208 Z" fill="#17191c" /><path d="M 6.98 2.555 L 5.705 4.763 L 3.155 4.763 L 1.88 2.555 L 3.155 0.347 L 5.705 0.347 Z" fill="#17191c" /><path d="M 2.55 5.11 L 1.275 7.318 L -1.275 7.318 L -2.55 5.11 L -1.275 2.902 L 1.275 2.902 Z" fill="#17191c" /><path d="M 11.41 5.11 L 10.135 7.318 L 7.585 7.318 L 6.31 5.11 L 7.585 2.902 L 10.135 2.902 Z" fill="#17191c" /></pattern>',
    "holes": '<pattern id="portrayal-holes" width="5" height="5" patternUnits="userSpaceOnUse"><circle cx="2.5" cy="2.5" r="1.1" fill="#3c4046" /></pattern>',
    "grille": '<pattern id="portrayal-grille" width="12" height="12" patternUnits="userSpaceOnUse"><rect x="0.9" y="0.9" width="10.2" height="10.2" rx="1.2" fill="#15181b" /></pattern>',
    "slots": '<pattern id="portrayal-slots" width="8" height="14" patternUnits="userSpaceOnUse"><rect x="2.9" y="2.5" width="2.2" height="9" rx="1.1" fill="#3c4046" /></pattern>',
    "slots-h": '<pattern id="portrayal-slots-h" width="14" height="8" patternUnits="userSpaceOnUse"><rect x="2.5" y="2.9" width="9" height="2.2" rx="1.1" fill="#3c4046" /></pattern>',
    "ribs": '<pattern id="portrayal-ribs" width="7.2" height="6" patternUnits="userSpaceOnUse"><rect x="0" y="0" width="4.8" height="6" fill="#e8eaed" /><rect x="5.4" y="0" width="1.8" height="6" fill="#6a7075" /></pattern>',
    "brush": '<pattern id="portrayal-brush-vertical" width="1.6" height="9" patternUnits="userSpaceOnUse"><rect x="0" y="0" width="1.6" height="9" fill="#121315" /><rect x="0.25" y="0" width="0.35" height="9" fill="#24272b" /><rect x="1" y="2.5" width="0.25" height="6.5" fill="#1c1e21" /></pattern>',
}


@pytest.mark.parametrize("pattern", sorted(MAIN))
def test_an_existing_pattern_tile_is_written_as_it_was(pattern):
    svg = _svg([{"id": "v", "at": [10.0, 10.0], "size": [100.0, 20.0], "pattern": pattern}])
    assert re.search(r"<pattern .*?</pattern>", svg, re.S).group(0) == MAIN[pattern]


def test_a_motif_does_not_change_the_tile_written_for_another_pattern_beside_it():
    svg = _svg([_motif(), {"id": "v", "at": [10.0, 40.0], "size": [100.0, 5.0], "pattern": "vent"}])
    assert MAIN["vent"] in svg

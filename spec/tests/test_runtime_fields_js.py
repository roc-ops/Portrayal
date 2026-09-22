"""A colour field is painted at runtime, not only at build time (#481).

render.py's `fill_from_attrs` paints `data-fill-from` and `data-stroke-from`
nodes when a drawing is built. The two runtime paths that apply a field after
that - kit/shell.js `setFields` (the 2D drawing) and kit/relief.js
`applyNodeFields` (the documents the 3D scene rasterises) - wrote text and
nothing else, so a latch colour set from a host page arrived on the group as
`data-latch-color` and painted nowhere. Both now go through kit/fields.js.

The rule is the build's, with one thing the build never needs: a runtime change
can be undone, so an empty value RESTORES the drawn colour, which the first
paint stashed on the node.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "spec/tests/js/runtime-fields.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_colour_is_painted_and_the_drawn_one_remembered(out):
    assert out["set"]["bail"]["fill"] == "#c22f2f"
    assert out["set"]["bail"]["data-portrayal-fill"] == "#6f6f6f"
    assert out["set"]["bail"]["stroke"] == "#444444", "a fill field moved the outline"
    assert out["set"]["group"] == "#c22f2f"


def test_a_change_keeps_the_drawn_colour_not_the_last_one(out):
    assert out["changed"]["fill"] == "#2255aa", "the value is trimmed, as the build trims"
    assert out["changed"]["data-portrayal-fill"] == "#6f6f6f"


def test_clearing_restores_what_was_drawn(out):
    for k in ("cleared", "nulled"):
        assert out[k]["fill"] == "#6f6f6f", k
        assert "data-portrayal-fill" not in out[k], f"{k}: the stash was left behind"
    assert out["strokeCleared"]["stroke"] == "#8c1f1f"
    assert out["stroke"]["stroke"] == "#3d7bd6"


def test_a_node_drawn_with_no_fill_goes_back_to_none(out):
    assert out["bareSet"]["fill"] == "#101010"
    assert "fill" not in out["bareCleared"], "restoring wrote fill=\"\" instead of removing it"


def test_text_fields_still_work(out):
    assert out["set"]["label"] == "uplink-A"
    assert out["labelHidden"] == ["", "none"]
    assert out["labelShown"] == ["uplink-B", None]


def test_a_key_that_matches_no_node_does_nothing(out):
    assert out["noMatch"]


def test_unpaint_restores_every_colour(out):
    bail, ring, bare = out["unpainted"]
    assert bail["fill"] == "#6f6f6f" and ring["stroke"] == "#8c1f1f" and "fill" not in bare
    assert not any(k.startswith("data-portrayal-") for n in out["unpainted"] for k in n)


def test_the_3d_registry_paints_the_part_and_its_projection(out):
    assert out["relief"]["bail"]["fill"] == "#c22f2f"
    assert out["relief"]["plan"]["fill"] == "#c22f2f"
    assert out["relief"]["label"] == "uplink-A"
    assert out["reliefChanged"]["fill"] == "#2255aa"


def test_a_part_left_out_of_the_map_goes_back_to_its_drawing(out):
    """The LOD records repaint from their own last output, so the drawn colour
    has to survive serialising, and a path dropped from the map is a change."""
    for n in out["reliefDropped"]:
        assert n["fill"] == "#6f6f6f", n
        assert "data-portrayal-fill" not in n


def test_an_inner_part_keeps_its_own_value(out):
    assert out["nested"] == ["#c22f2f", "#2255aa"]


def test_a_repaint_recolours_a_derived_body(out):
    """The bail is a `bar` tube with no face texture: its whole colour is the
    material's, so a repaint that only redrew textures left it grey (#481)."""
    assert out["recolour"] == "rgb(194,47,47)"
    assert out["recolourSeen"] == ["rgb(194,47,47)"] * 2
    assert out["recolourStated"] == [None, None], "a data-z-color was overridden"
    assert out["recolourNone"] is None


def test_the_repaint_path_recolours_and_every_body_material_is_collected():
    """STATIC, because the geometry half needs WebGL: in buildFaceRelief's loop
    over raised nodes, the repaint registered with `reg` calls recolourBody, and
    no material is built from `o.color` except through bodyMat (or sideMats,
    which is collected) - a new branch that built its own would never repaint."""
    text = (ROOT / "kit/relief.js").read_text()
    start = text.index("for (const o of outs) {")
    end = text.index("for (const f of frus) {", start)
    loop = text[start:end]
    reg = loop[loop.index("reg(o.svgText,"):]
    reg = reg[:reg.index("{mat: faceTex")]
    assert "recolourBody(derived, bodyMats," in reg, "the repaint no longer recolours the body"
    built = re.findall(r"MeshLambertMaterial\(\{\s*color:\s*o\.color[^}]*\}", loop)
    assert built == ["MeshLambertMaterial({color: o.color, ...extra}"], (
        f"a material is built from o.color outside bodyMat: {built}")
    assert "bodyMats.push(...mats" in loop, "the box's side materials are not collected"


def test_both_runtime_paths_use_the_one_rule():
    for name in ("shell.js", "relief.js"):
        text = (ROOT / "kit" / name).read_text()
        assert re.search(r"import \{[^}]*\bpaintFields\b[^}]*\} from './fields\.js'", text), name
        assert "[data-from=" not in text, f"{name} carries its own copy of the field rule"

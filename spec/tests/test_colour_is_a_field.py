"""A colour is a field, not a second drawing of the same part.

roc-ops/Portrayal#177. Ten parts carried a `blue.svg` beside `default.svg`, and
the difference between them was one to four fills: `ufispace/psu-751-ac` differed
in a single line. Every one was a copy that had to be kept in step by hand, and
choosing it was a name written on each placement - which is how three Edgecore
chassis that share one documented convention ended up with one drawing its
back-to-front build in blue and two in red.

`data-fill-from` already existed for exactly this and says so in its own
docstring: "a skin apiece would be four near-copies per finish and a name to
choose on each of 758 placements; an attr is one word on the ones that differ."
What it could not do was the other half of a coloured part. Every red latch here
is `fill="#c22f2f" stroke="#8c1f1f"` and the blue variant moved both, so
`data-stroke-from` joins it - without it the conversion would have produced blue
handles wearing dark red edges, a drawing nobody would write by hand arrived at
by a mechanism that could only say half of what the art said.

THE DEFAULT DRAWING DOES NOT MOVE. Each node keeps the fill it had; the attribute
only names a field that may override it. The rendered `as5912-54x.rear.svg` still
paints `#c22f2f`, and the `as7726-32x.ac-b2f.rear.svg` paints `#3d7bd6` - which
before this change came from a second file.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"

CONVERTED = ["common/fan-module", "common/fan-module-46", "common/psu-ac-1300",
             "common/psu-ac-650", "common/psu-dc-650", "ufispace/fan-405637",
             "ufispace/fan-805616", "ufispace/psu-751-ac", "ufispace/psu-751-dc"]


def contract(ref):
    ns, name = ref.split("/")
    v = sorted((LIB / "components" / ns / name).glob("v*"))[-1]
    return v, yaml.safe_load((v / "contract.yaml").read_text())


@pytest.mark.parametrize("ref", CONVERTED)
def test_the_blue_skin_is_gone_and_a_field_took_its_place(ref):
    v, d = contract(ref)
    assert not (v / "skins" / "blue.svg").exists(), f"{ref} still has a blue skin"
    assert "blue" not in (d.get("skins") or []), f"{ref} still declares one"
    fields = d.get("fields") or {}
    assert any(k.endswith("-finish") for k in fields), f"{ref} has no colour field: {list(fields)}"


@pytest.mark.parametrize("ref", CONVERTED)
def test_the_art_is_wired_to_every_field_it_declares(ref):
    """L73 asks this of the whole library; here it is asked of the parts this
    change touched, so a later edit to one of these skins cannot quietly drop
    the wiring and leave a field that moves nothing."""
    v, d = contract(ref)
    art = (v / "skins" / "default.svg").read_text()
    wired = set(re.findall(r'data-(?:from|fill-from|stroke-from)="([^"]+)"', art))
    missing = sorted(set(d.get("fields") or {}) - wired)
    assert not missing, f"{ref}: fields wired to nothing: {missing}"


@pytest.mark.parametrize("ref", CONVERTED)
def test_the_node_keeps_the_colour_it_had(ref):
    """The safety property of the whole conversion: a node names a field AND
    still carries its own value, so a part drawn with no attrs at all is the
    drawing it was before."""
    v, d = contract(ref)
    art = (v / "skins" / "default.svg").read_text()
    for tag in re.findall(r'<[a-z]+[^>]*data-fill-from="[^"]+"[^>]*>', art):
        assert re.search(r'\bfill="[^"]+"', tag), f"{ref}: a painted node lost its own fill"
    for tag in re.findall(r'<[a-z]+[^>]*data-stroke-from="[^"]+"[^>]*>', art):
        assert re.search(r'\bstroke="[^"]+"', tag), f"{ref}: an outlined node lost its own stroke"


def test_nothing_selects_a_blue_skin_any_more():
    """The other end. A configuration naming a skin that no longer exists is a
    render-time crash, which is how the first pass of this was caught."""
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("skin", "skins"):
                    assert v != "blue", k
                    if isinstance(v, dict):
                        assert "blue" not in v.values(), v
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    n = 0
    for p in sorted(LIB.glob("devices/**/*.yaml")):
        walk(yaml.safe_load(p.read_text()))
        n += 1
    assert n > 80, f"only {n} manifests walked"


@pytest.mark.skipif(not (DIST / "as7726-32x.ac-b2f.rear.svg").exists(),
                    reason="needs a build")
def test_the_drawing_still_comes_out_red_by_default_and_blue_where_asked():
    """END TO END, and the only check that proves the colour still reaches a
    pixel. Before #177 the blue came from a second file; now it comes from two
    words on a configuration."""
    def finishes(name, field):
        t = (DIST / name).read_text()
        return set(re.findall(rf'data-fill-from="{field}"[^>]*?fill="([^"]+)"', t)) | \
               set(re.findall(rf'fill="([^"]+)"[^>]*?data-fill-from="{field}"', t))
    assert finishes("as7726-32x.ac-f2b.rear.svg", "handle-finish") == {"#c22f2f"}
    assert finishes("as7726-32x.ac-b2f.rear.svg", "handle-finish") == {"#3d7bd6"}
    assert finishes("as7726-32x.ac-b2f.rear.svg", "latch-finish") == {"#3d7bd6"}


def test_the_wattage_skins_are_gone_and_the_field_remains():
    """Three skins differing from `default.svg` only in the text of a node that
    already carried `data-from="watts"` - the thing `fields` replaced, left
    behind beside it."""
    v, d = contract("dell/psu-1100w-ac-14g")
    assert d["skins"] == ["default"], d["skins"]
    assert "watts" in (d.get("fields") or {})
    for s in ("w495", "w750", "w1600"):
        assert not (v / "skins" / f"{s}.svg").exists()

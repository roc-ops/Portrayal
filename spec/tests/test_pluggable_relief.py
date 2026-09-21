"""Pluggables D task 1: the four generic transceivers' relief, re-sourced.

Every generic transceiver in the library (sfp-lc, sfp-lc-simplex, qsfp-lc,
qsfp-dd-lc) carries a `body` relief feature that stands the module proud of
its cage, and a bail (SFP) or tab (QSFP, QSFP-DD) that stands proud further
still. Two things about that pair were wrong before this task:

1. The bail/tab carried a hard-coded `color` in the contract, which render.py
   writes onto the compiled node as `data-z-color` (~render.py:823, :916).
   kit/relief.js reads that attribute FIRST and only falls back to
   `dominantColor()` of the node's own art when it is absent (~relief.js:1410)
   - so a hard-coded relief colour overrides whatever `latch-color` painted
   the art via `data-fill-from`, and a red latch in 2D stood in 3D wearing the
   *contract's* fixed colour instead. Removing `color` from the feature is
   what lets 3D follow the art.

2. The SFP bail's `source` asserted nothing SFF-8432 actually gives: D2 (see
   docs/pluggables-3d-design.md, "Decisions taken in D") found
   Table 4-3 designator A dimensions the *body*, not the bail, and Figure 4-2
   ("Latch Post Detail") is the cage-retention post, not the wire bail - so
   the bail's 14.3 reach stays `estimated` but the sentence has to say what
   was checked and came up empty, not just that nothing was checked.

This file compiles each generic the way `components_index.py` compiles
`library/dist/components/*.svg` - `render.instance_group`, the same call, not
a reimplementation - and reads the `data-z-*` attributes and skin fill straight
off the result, per docs/pluggables-3d-design.md's own instruction that
verification is "compiled and counted", not reasoned about.

Every assertion here fails on at least one of today's four contracts: the two
SFP generics still carry a hard-coded `data-z-color` on `bail` before this
task's edit.
"""
import pathlib

import pytest
import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

from portrayal import render

# (ref, the node the pull latch is drawn as, the body's `out`, substrings the
# body's `source` sentence must cite verbatim - the MSA designator the plan's
# D2 reading rests on)
GENERICS = [
    ("generic/sfp-lc@1", "bail", 10.0,
     ["SFF-8432", "Table 4-3 designator A"]),
    ("generic/sfp-lc-simplex@1", "bail", 10.0,
     ["SFF-8432", "Table 4-3 designator A"]),
    ("generic/qsfp-lc@1", "tab", 20.0,
     ["SFF-8661", "Figure 5-1"]),
    ("generic/qsfp-dd-lc@1", "tab", 20.0,
     ["QSFP-DD HW", "Figure 52"]),
]


def _contract_path(ref):
    nsname, major = ref.split("@")
    ns, name = nsname.split("/")
    return LIB / "components" / ns / name / f"v{major}" / "contract.yaml"


def _contract(ref):
    return yaml.safe_load(_contract_path(ref).read_text())


def _relief_feature(ref, node):
    data = _contract(ref)
    for feat in data["relief"]["features"]:
        if feat["node"] == node:
            return feat
    raise AssertionError(f"{ref} has no relief feature named {node!r}")


def _compiled_nodes(ref, attrs=None):
    """The standalone-component compile path, `render.instance_group` -
    the same function `components_index.py` calls to write
    `library/dist/components/*.svg` - not a reimplementation of it.

    `attrs` stands in for what a placement's `fields` become by the time they
    reach `instance_group` (see render.py's `merged` in that function): a
    device placement's `fields.latch-color` arrives here exactly the same way,
    through the `attrs` positional argument, so passing it directly exercises
    the real field-to-fill path without needing a device or a config.
    """
    lib = render.Library([str(LIB)])
    g, _ = render.instance_group(lib, ref, "t", [0, 0], None, attrs, None, None,
                                  skin_name="default", palette={}, resolved={})
    return {n.get("id"): n for n in g.iter() if n.get("id")}


@pytest.mark.parametrize("ref,latch_node,body_out,markers", GENERICS,
                          ids=[g[0] for g in GENERICS])
def test_body_out_and_source_cite_the_msa_designator(ref, latch_node, body_out, markers):
    nodes = _compiled_nodes(ref)
    body = nodes["t--body"]
    assert float(body.get("data-z-out")) == body_out, \
        f"{ref} body data-z-out: {body.get('data-z-out')!r}"
    src = _relief_feature(ref, "body")["source"]
    for marker in markers:
        assert marker in src, f"{ref} body source is missing {marker!r}: {src!r}"


@pytest.mark.parametrize("ref,latch_node,body_out,markers", GENERICS,
                          ids=[g[0] for g in GENERICS])
def test_latch_carries_no_hardcoded_relief_color(ref, latch_node, body_out, markers):
    """A `color` on the bail/tab feature would out-rank the art's own fill in
    3D (relief.js prefers `data-z-color` over `dominantColor()`), so 3D would
    never see a `latch-color` field change. Fails today for both SFP generics,
    whose `bail` feature still carries `color: '#2f5fa8'`."""
    nodes = _compiled_nodes(ref)
    latch = nodes[f"t--{latch_node}"]
    assert latch.get("data-z-color") is None, (
        f"{ref} {latch_node} still carries data-z-color="
        f"{latch.get('data-z-color')!r}; relief.js will use it instead of "
        "the node's own art")


@pytest.mark.parametrize("ref,latch_node,body_out,markers", GENERICS,
                          ids=[g[0] for g in GENERICS])
def test_latch_fill_follows_the_latch_color_field(ref, latch_node, body_out, markers):
    """The colour test: a placement's `latch-color` field reaches the bail/tab
    node's `fill` through the skin's own `data-fill-from="latch-color"`
    (already wired on all four skins), so once the feature carries no
    `data-z-color`, relief.js's `dominantColor()` of this node's own art
    reads red here, not a hard-coded blue."""
    nodes = _compiled_nodes(ref, attrs={"latch-color": "#c03030"})
    latch = nodes[f"t--{latch_node}"]
    assert latch.get("fill") == "#c03030", \
        f"{ref} {latch_node} fill: {latch.get('fill')!r}"


# ---------------------------------------------------------------- Task 4
#
# The plugs and boots (pluggables D Task 4). Each row is (ref, node, the
# compiled data-z-out, the compiled data-z-lift or None, the contract
# confidence, substrings its source sentence must carry). Read off the
# standalone compile, the same call components_index.py makes.
PLUGS_AND_BOOTS = [
    ("generic/lc-plug@1", "body", 12.5, None, "estimated",
     ["DS-LC-000004", "12.2 MIN", "(42)", "REFERENCE"]),
    ("generic/lc-plug@1", "tip", 6.6, None, "estimated", ["8.6", "19.70"]),
    ("generic/lc-plug@1", "shoulder", 6.6, None, "estimated", ["19.70"]),
    ("generic/lc-plug@1", "stem", 6.6, None, "estimated", ["19.70"]),
    ("generic/rj45-plug@1", "body", 13.0, None, "estimated",
     ["22.48 - 9.5", "TE 1734264", "std/rj45"]),
    ("common/lc-boot@1", "body", 15.1, None, "drawing", ["DS-LC-000023", "15.1"]),
    ("common/rj45-boot@1", "body", 26.4, None, "drawing", ["J0072", "26.4"]),
]


@pytest.mark.parametrize("ref,node,out,lift,conf,markers", PLUGS_AND_BOOTS,
                          ids=[f"{r[0]}:{r[1]}" for r in PLUGS_AND_BOOTS])
def test_plugs_and_boots_stand_off(ref, node, out, lift, conf, markers):
    el = _compiled_nodes(ref)[f"t--{node}"]
    assert float(el.get("data-z-out")) == out, f"{ref} {node}: {el.get('data-z-out')!r}"
    assert el.get("data-z-lift") == lift
    feat = _relief_feature(ref, node)
    assert feat["confidence"] == conf
    for m in markers:
        assert m in feat["source"], f"{ref} {node} source is missing {m!r}"


@pytest.mark.parametrize("ref", ["generic/lc-plug@1", "generic/rj45-plug@1"])
def test_a_plug_presents_at_its_boot_on_its_body(ref):
    """`interface-at: boot`, `boot` and `cable` both `on: body` - and `mate`
    exactly as it was: the plug still seats INTO its receptacle by `mate`."""
    d = _contract(ref)
    cps = d["connection-points"]
    assert d["interface-at"] == "boot"
    assert cps["boot"]["on"] == "body" and cps["cable"]["on"] == "body"
    assert set(cps["mate"]) == {"at", "direction"} and cps["mate"]["direction"] == "front"
    assert cps["mate"]["at"] == cps["boot"]["at"], "a boot drawn over the plug in 2D"


@pytest.mark.parametrize("ref", ["common/lc-boot@1", "common/rj45-boot@1"])
def test_a_boots_cable_leaves_its_rear(ref):
    cps = _contract(ref)["connection-points"]
    assert cps["cable"]["on"] == "body"
    assert "on" not in cps["mate"]


def test_the_lc_boot_rear_carries_its_cable_exit():
    """The LC boot's bore is its cable-exit I.D., the end the viewer sees, so
    it is inside the extruded `body` node and paints on the far face rather
    than being buried at the plug joint (relief-full-face-slab-buries-detail)."""
    nodes = _compiled_nodes("common/lc-boot@1")
    body = nodes["t--body"]
    assert any(n.get("id") == "t--bore" for n in body.iter())


# ------------------------------------------------- the neutral latch default
#
# Decided 2026-09-21. SFF-8432 Rev 5.2a Note 13 codes an exposed SFP feature's
# colour by mode (black or beige multi-mode, blue single mode) and QSFP-DD HW
# Rev 6.3 section 6.3 codes a pull tab by wavelength (beige 850 nm, blue 1310
# nm, white 1550 nm). A generic that defaults to any of those claims a per-SKU
# fact (L99), so every generic's default is an unsaturated grey that is neither
# black nor white - and the skin's literal fill, the colour a compile with no
# field shows, is that same default, so the two cannot drift apart.

def _hex_rgb(value):
    v = value.strip().lstrip("#")
    assert len(v) == 6, f"not a #rrggbb colour: {value!r}"
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


@pytest.mark.parametrize("ref,latch_node,body_out,markers", GENERICS,
                          ids=[g[0] for g in GENERICS])
def test_latch_default_is_a_neutral_grey_the_skin_draws(ref, latch_node, body_out, markers):
    default = _contract(ref)["fields"]["latch-color"]["default"]
    # the skin's literal fill, read off a compile given NO field value
    latch = _compiled_nodes(ref)[f"t--{latch_node}"]
    assert latch.get("data-fill-from") == "latch-color", latch.attrib
    assert latch.get("fill").lower() == default.lower(), (
        f"{ref}: the skin draws {latch.get('fill')!r} but latch-color defaults "
        f"to {default!r}")
    r, g, b = _hex_rgb(default)
    # ACHROMATIC, MEASURED AS SATURATION. #6b6f73 is the value decided, and it
    # is a grey with a cool cast (107, 111, 115: a spread of 8, saturation
    # 0.07), so a literal r == g == b within 2 would refuse the decided
    # colour. What the test is for is that no default reads as a hue - blue
    # is the one in both codes - and 0.08 admits that grey while refusing
    # anything with a colour in it (the old blue #2f5fa8 is 0.72).
    saturation = (max(r, g, b) - min(r, g, b)) / max(r, g, b)
    assert saturation <= 0.08, (
        f"{ref}: {default} is chromatic (saturation {saturation:.2f}); a "
        f"coloured default is a mode or wavelength claim")
    assert 0x20 < r < 0xe0, (
        f"{ref}: {default} is too near black or white - both are in an MSA "
        f"colour code (black multi-mode, white 1550 nm)")

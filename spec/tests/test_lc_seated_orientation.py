"""A seated LC plug faces its bore, with its latch compressed into the keyway
(B3, docs/pluggables-caps-design.md, "Seated plugs").

THREE FAULTS, ONE GEOMETRY. `std/lc-bore@3` is drawn tongue DOWN unrotated and
`generic/lc-plug@1` latch UP, and `render.solve_seat` turns an occupant by
exactly its host's turn - so every simplex LC plug seated 180 degrees out, its
latch standing off the side OPPOSITE the keyway. SENKO DS-LC-000004's 10.43
front silhouette is the plug's FREE state, and seated the latch is compressed
into the adapter's keyway; and the bulkhead adapters drew the transceiver
receptacle's 1.60 keyway, which is shorter than their own hardware's.

WHAT IS CHECKED, AND WHERE. Everything below is measured on REAL BUILDS of
copies in `tmp_path` - the FS FHD enclosure with an LC cassette in bay-1 and
bay-4, and the Smartoptics DCP-R-34D-CS - through every ancestor's transform,
so a turn applied anywhere in the chain (device placement, cassette, adapter,
bore, spanning axis, duplex half) is in the answer:

  (a) a seated plug's latch lies on the same side of its mate as the host
      bore's keyway, for every simplex plug in a bore and every half of a
      duplex plug in an adapter slot;
  (b) on a bulkhead aperture, the seated plug reaches no further along the
      latch axis than the bore's own outline does, to 0.05;
  (c) the same latch-side check for the SC plug in its bore - a guard, since
      both are drawn key-left and already agree;
  (d) L112's latch-side arm: the axis a duplex host derives puts a duplex
      part's latches (drawn up) on its bores' keyway side (drawn down).

EACH IS PROVED NON-VACUOUS HERE, not only in a report: the same measurement is
run against the shapes that were wrong - a plug drawn latch UP (the retired
`generic/lc-plug@1`'s orientation), one with its latch FREE (its 10.43
silhouette), a duplex plug whose halves are not turned, the v-adapter with its
bores in the pre-#496 order - each rebuilt as a tmp copy of the current part,
and each has to be found.
"""
import math
import re
import shutil
import xml.etree.ElementTree as ET

import pytest
import yaml

from test_nested_occupants import LIB, device_matrix, device_point
from test_slot_defaults import _copy, build

from portrayal import lint
from portrayal.manifest import load_yaml

LC = "generic/lc-plug@2"
DUPLEX = "generic/lc-duplex-plug@2"
SC = "generic/sc-plug@1"
BULKHEAD = "std/lc-bulkhead-bore@1"
RECEPTACLE = "std/lc-bore@3"
H_ADAPTER = "common/lc-duplex-adapter@4"        # Smartoptics, side by side
V_ADAPTER = "common/lc-duplex-v-adapter@5"      # FS FHD cassettes, stacked
LC_CASSETTE = "fs/fhd-2mtp12-lc-os2-a@3"
SC_CASSETTE = "fs/fhd-1mtp12-sc-os2-a@2"

# what a seated plug can land in, and what is a plug
BORES = ("std/lc-bore@", "std/lc-bulkhead-bore@", "std/sc-bore@")
PLUGS = ("generic/lc-plug@", "generic/sc-plug@", "test/")

TOL = 0.05

# (keys on the FHD, keys on the DCP). The DCP's xc18/xc19 are on the row it
# places at rotate 180; port-1510 and xc01 are on the unturned row. The FHD's
# bay-1 and bay-4 are the enclosure's two ends.
LC_SIMPLEX_KEYS = {"fhd": ["bay-1/lc01/tx", "bay-1/lc01/rx", "bay-4/lc12/tx"],
                   "dcp": ["port-1510/tx", "port-1510/rx", "xc18/rx"]}
LC_DUPLEX_KEYS = {"fhd": ["bay-1/lc02", "bay-4/lc07"], "dcp": ["xc01", "xc19"]}
# every simplex plug, and BOTH halves of every duplex plug
EXPECTED = {k: len(LC_SIMPLEX_KEYS[k]) + 2 * len(LC_DUPLEX_KEYS[k])
            for k in LC_SIMPLEX_KEYS}


def contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return load_yaml(LIB / "components" / ns / name / f"v{major}" / "contract.yaml")


# --- the two real devices, copied --------------------------------------------------

def fhd(tmp_path, cassette, occupants):
    """fs/fhd-1ufce with `cassette` in bay-1 AND bay-4 and `occupants` in its
    base configuration."""
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp_path / "fhd") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"]["base"]
    cfg["bays"] = {**(cfg.get("bays") or {}), "bay-1": cassette, "bay-4": cassette}
    cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev, "fhd-1ufce", "base"


def dcp(tmp_path, occupants):
    """smartoptics/dcp-r-34d-cs, which places its bottom row of adapters at
    `rotate: 180` - one device carrying both turns of the same adapter."""
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-r-34d-cs",
                          tmp_path / "dcp") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    assert not d.get("configurations"), "the device now ships its own; rewrite this"
    d["configurations"] = {"default": {"kind": "base", "default": True,
                                       "occupants": occupants}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev, "dcp-r-34d-cs", "default"


def front(tmp_path, made, root=LIB):
    dev, name, config = made
    out = build(dev, tmp_path / "o", root)
    svg = ET.parse(out / f"{name}.{config}.front.svg").getroot()
    return svg, {c: p for p in svg.iter() for c in p}


def build_lc(tmp_path, which, simplex=LC, duplex=DUPLEX, root=LIB):
    occ = {**{k: simplex for k in LC_SIMPLEX_KEYS[which]},
           **{k: duplex for k in LC_DUPLEX_KEYS[which]}}
    made = fhd(tmp_path, LC_CASSETTE, occ) if which == "fhd" else dcp(tmp_path, occ)
    return front(tmp_path, made, root)


# --- measuring a build -------------------------------------------------------------

def _ref(el):
    return (el.get("data-ref") or "").rsplit(":", 1)[0]


def _resolve(ref, root=LIB):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    for base in (root, LIB):
        f = base / "components" / ns / name / f"v{major}" / "contract.yaml"
        if f.exists():
            return load_yaml(f)
    raise FileNotFoundError(ref)


def _pt(m, x, y):
    return (m[0][0] * x + m[0][1] * y + m[0][2], m[1][0] * x + m[1][1] * y + m[1][2])


def _rect_corners(parents, rect):
    m = device_matrix(parents, rect)
    x, y = float(rect.get("x") or 0), float(rect.get("y") or 0)
    w, h = float(rect.get("width")), float(rect.get("height"))
    return [_pt(m, x + dx, y + dy) for dx in (0, w) for dy in (0, h)]


def _unit(v):
    n = math.hypot(*v)
    assert n > 1e-9, "a zero-length direction measures nothing"
    return (v[0] / n, v[1] / n)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _groups(svg, prefixes):
    return [el for el in svg.iter()
            if el.tag.split("}")[-1] == "g" and el.get("data-path") is not None
            and _ref(el).startswith(prefixes)]


def bores(svg, parents, root=LIB):
    """Every part a plug seats into: (element, device mate, keyway direction,
    keyway reach). The keyway side is read off the part's own OUTLINE - the
    side its box runs furthest from its mate - so an SC bore, whose key slot is
    a notch in its outline with no element of its own, is measured exactly as
    an LC bore is, and the direction comes out through every ancestor."""
    out = []
    for el in _groups(svg, BORES):
        c = _resolve(_ref(el), root)
        mate = device_point(parents, el, c["connection-points"]["mate"]["at"])
        m = device_matrix(parents, el)
        w, h = c["size"]["w"], c["size"]["h"]
        corners = [_pt(m, x, y) for x in (0, w) for y in (0, h)]
        reach = {d: max(_dot((p[0] - mate[0], p[1] - mate[1]), d) for p in corners)
                 for d in ((1, 0), (-1, 0), (0, 1), (0, -1))}
        side = max(reach, key=reach.get)
        ranked = sorted(reach.values())
        assert ranked[-1] - ranked[-2] > 0.1, ("no keyed side", el.get("data-path"), reach)
        out.append((el, mate, side, reach[side]))
    return out


def plugs(svg, parents, root=LIB):
    """Every seated simplex plug body - a simplex occupant, or one half of a
    duplex one: (element, device mate, latch direction, silhouette corners).
    The latch direction runs from the mate to the centre of the part's own
    `latch` elements; the silhouette is every rect it draws."""
    out = []
    for el in _groups(svg, PLUGS):
        c = _resolve(_ref(el), root)
        if c.get("parts"):
            continue                    # a duplex plug: its halves are measured
        mate = device_point(parents, el, c["connection-points"]["mate"]["at"])
        rects = [r for r in el if r.tag.split("}")[-1] == "rect"]
        latch = [p for r in rects if "latch" in (r.get("class") or "").split()
                 for p in _rect_corners(parents, r)]
        assert latch, f"{el.get('data-path')} draws no latch element"
        cx = sum(p[0] for p in latch) / len(latch)
        cy = sum(p[1] for p in latch) / len(latch)
        corners = [p for r in rects for p in _rect_corners(parents, r)]
        out.append((el, mate, _unit((cx - mate[0], cy - mate[1])), corners))
    return out


def seated_pairs(svg, parents, root=LIB):
    """Each plug paired with the one bore whose mate it landed on."""
    bs = bores(svg, parents, root)
    pairs = []
    for plug in plugs(svg, parents, root):
        hit = [b for b in bs if math.dist(b[1], plug[1]) < 1e-6]
        assert len(hit) == 1, (plug[0].get("data-path"), len(hit))
        pairs.append((plug, hit[0]))
    return pairs


def wrong_side(pairs):
    """The plugs whose latch does not point along their bore's keyway."""
    return sorted(p[0].get("data-path") for p, b in pairs if _dot(p[2], b[2]) < 0.99)


def overrun(pairs, bore_prefix):
    """{plug path: how far its silhouette runs past its bore's outline along
    the bore's latch axis}, for the plugs seated in bores `bore_prefix` names."""
    out = {}
    for (el, _mate, _latch, corners), (bel, bmate, side, reach) in pairs:
        if _ref(bel).startswith(bore_prefix):
            got = max(_dot((p[0] - bmate[0], p[1] - bmate[1]), side) for p in corners)
            out[el.get("data-path")] = round(got - reach, 4)
    return out


# --- (a) the latch faces the keyway ------------------------------------------------

@pytest.mark.parametrize("which", ["fhd", "dcp"])
def test_every_seated_lc_plug_faces_its_bores_keyway(tmp_path, which):
    svg, parents = build_lc(tmp_path, which)
    pairs = seated_pairs(svg, parents)
    assert len(pairs) == EXPECTED[which] > 0, len(pairs)
    assert wrong_side(pairs) == []


def _plug_copy(root, name, skin_edit, contract_edit):
    """A tmp copy of generic/lc-plug@2 at test/<name>@1 with its skin rewritten
    by `skin_edit` - the build draws the skin, so that is what has to change."""
    f = _copy(root, "generic/lc-plug", 2, name, contract_edit)
    svg = f.parent / "skins" / "default.svg"
    svg.write_text(skin_edit(svg.read_text()))
    return f"test/{name}@1"


def _latch_up(root):
    """generic/lc-plug@2 turned over in its own frame - latch UP, the way the
    retired @1 was drawn - by reflecting every y in the 8.535 box."""
    h = contract(LC)["size"]["h"]

    def skin(text):
        def rect(m):
            y, ht = float(m.group(2)), float(m.group(4))
            return f'{m.group(1)}y="{round(h - y - ht, 4)}"{m.group(3)}height="{ht}"'
        text = re.sub(r'(<rect [^>]*?)y="([\d.]+)"([^>]*?)height="([\d.]+)"', rect, text)
        return re.sub(r'cy="([\d.]+)"', lambda m: f'cy="{round(h - float(m.group(1)), 4)}"', text)

    def flip(c):
        for p in c["connection-points"].values():
            p["at"] = [p["at"][0], round(h - p["at"][1], 4)]
    return _plug_copy(root, "latch-up-plug", skin, flip)


def _free_latch(root):
    """generic/lc-plug@2 with its latch FREE - the three tiers at SENKO's free
    heights (2.66 / 0.79 / 1.33, below the 5.65 body), the 10.43 silhouette."""
    tiers = {"stem": (5.65, 1.33), "shoulder": (6.98, 0.79), "tip": (7.77, 2.66)}

    def skin(text):
        for tid, (y, ht) in tiers.items():
            text = re.sub(rf'(<rect id="{tid}"[^>]*?)y="[\d.]+"([^>]*?)height="[\d.]+"',
                          rf'\g<1>y="{y}"\g<2>height="{ht}"', text)
        return text.replace('height="8.535mm"', 'height="10.43mm"').replace(
            "0 0 5.58 8.535", "0 0 5.58 10.43")

    def free(c):
        c["size"] = {"w": 5.58, "h": 10.43}
    return _plug_copy(root, "free-plug", skin, free)


@pytest.mark.parametrize("which", ["fhd", "dcp"])
def test_a_latch_up_plug_is_caught_facing_away(tmp_path, which):
    """THE FAULT THIS TASK FIXES, found by the same code: a plug drawn latch
    UP - the retired @1's orientation - seats with its latch opposite the
    keyway in every bore. The duplex halves beside it are NOT caught, which
    shows the measurement discriminating rather than failing everything."""
    root = tmp_path / "lib"
    ref = _latch_up(root)
    svg, parents = build_lc(tmp_path, which, simplex=ref, root=root)
    pairs = seated_pairs(svg, parents, root)
    assert len(pairs) == EXPECTED[which]
    bad = wrong_side(pairs)
    assert len(bad) == len(LC_SIMPLEX_KEYS[which]) > 0, bad
    # a half's path ends in its part id under the duplex seat: `.../lc02-occupant/a`
    assert all(p.endswith("-occupant") for p in bad), bad


def test_a_duplex_plug_with_unturned_halves_is_caught(tmp_path):
    """The duplex arm's own non-vacuity: `generic/lc-duplex-plug@2` with the
    `rotate: 180` taken off its halves draws both latches DOWN, off the
    canonical axis, and every half is then found facing away. The copy's mate
    and clip follow the unturned bodies, so each half still lands on its bore
    and only the latch side differs."""
    root = tmp_path / "lib"

    def unturned(c):
        for q in c["parts"]:
            q.pop("rotate", None)
        c["connection-points"]["mate"]["at"] = [5.915, 2.825]
        c["elements"]["clip"]["at"] = [5.58, 0.0]
    _copy(root, "generic/lc-duplex-plug", 2, "unturned-duplex", unturned)
    svg, parents = build_lc(tmp_path, "fhd", duplex="test/unturned-duplex@1", root=root)
    bad = wrong_side(seated_pairs(svg, parents, root))
    assert len(bad) == 2 * len(LC_DUPLEX_KEYS["fhd"]) > 0, bad


# --- (b) the seated latch stays inside the bulkhead keyway -------------------------

def test_a_seated_plug_stays_inside_the_bulkhead_bores_outline(tmp_path):
    """On the FS cassettes, whose adapter composes the bulkhead aperture: the
    compressed latch runs no further along the latch axis than the keyway
    does. Measured on the plug's whole drawn silhouette, not only its tip."""
    svg, parents = build_lc(tmp_path, "fhd")
    got = overrun(seated_pairs(svg, parents), "std/lc-bulkhead-bore@")
    assert len(got) == EXPECTED["fhd"] > 0, got
    assert all(v <= TOL for v in got.values()), got


def test_a_free_latch_overruns_the_bulkhead_keyway(tmp_path):
    """Non-vacuity for (b): a plug drawn with its latch FREE reaches 7.605
    from its axis, 1.9 past the bulkhead keyway, and the same measurement finds
    every one while the seated duplex halves beside them stay inside."""
    root = tmp_path / "lib"
    svg, parents = build_lc(tmp_path, "fhd", simplex=_free_latch(root), root=root)
    got = overrun(seated_pairs(svg, parents, root), "std/lc-bulkhead-bore@")
    simplex = {k: v for k, v in got.items() if k.endswith("-occupant")}
    assert len(simplex) == len(LC_SIMPLEX_KEYS["fhd"]) > 0, got
    assert all(v == pytest.approx(7.605 - 5.71, abs=0.01) for v in simplex.values()), got
    assert all(v <= TOL for k, v in got.items() if k not in simplex), got


def test_the_seated_latch_reaches_exactly_the_bulkhead_keyway_end():
    """The contract-level half of (b): the plug is drawn compressed TO the
    keyway's end, not merely inside it. Both reaches are read from each
    part's own `mate` - the ferrule axis - down the latch."""
    plug, bore = contract(LC), contract(BULKHEAD)
    pm = plug["connection-points"]["mate"]["at"]
    bm = bore["connection-points"]["mate"]["at"]
    assert plug["size"]["h"] - pm[1] == pytest.approx(bore["size"]["h"] - bm[1], abs=1e-9)
    assert plug["size"]["h"] - pm[1] > pm[1], "the plug is not drawn latch down"


def test_in_the_transceiver_receptacle_the_latch_overruns_the_drawn_keyway():
    """Recorded, not hidden: std/lc-bore@3's 1.60 stack is a known
    understatement (its own `short-keyway`), so the seated latch runs past it,
    and the plug says so."""
    plug, bore = contract(LC), contract(RECEPTACLE)
    reach = plug["size"]["h"] - plug["connection-points"]["mate"]["at"][1]
    keyway = bore["size"]["h"] - bore["connection-points"]["mate"]["at"][1]
    assert reach - keyway > 1.0
    assert "std/lc-bore@3" in plug["provenance"]["receptacle"]


# --- (c) the SC guard --------------------------------------------------------------

def test_the_sc_plugs_key_faces_its_bores_key_slot(tmp_path):
    made = fhd(tmp_path, SC_CASSETTE,
               {"bay-1/sc1/tx": SC, "bay-1/sc1/rx": SC, "bay-4/sc6/tx": SC})
    svg, parents = front(tmp_path, made)
    pairs = seated_pairs(svg, parents)
    assert len(pairs) == 3
    assert wrong_side(pairs) == []


# --- (d) L112's latch-side arm -----------------------------------------------------

def l112(root, ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    f = root / "components" / ns / name / f"v{major}" / "contract.yaml"
    with lint.collecting() as got:
        lint.lint_component_spanned_geometry(f, yaml.safe_load(f.read_text()),
                                             [str(root), str(LIB)])
    return [e for e in got.errors if "[L112]" in e]


@pytest.mark.parametrize("ref", [H_ADAPTER, V_ADAPTER])
def test_both_duplex_adapters_put_the_latch_on_the_keyway_side(ref):
    assert l112(LIB, ref) == []


def test_the_v_adapter_with_its_bores_reversed_is_caught(tmp_path):
    """Main's pre-#496 polarity bug, caught from the geometry: compose the
    UPPER bore first and the derived axis is 90, which swings a duplex part's
    latch to the RIGHT while every bore's keyway faces LEFT."""
    root = tmp_path / "lib"

    def reversed_order(c):
        c["parts"] = list(reversed(c["parts"]))
    _copy(root, "common/lc-duplex-v-adapter", 5, "reversed-v-adapter", reversed_order)
    got = l112(root, "test/reversed-v-adapter@1")
    assert len(got) == 1 and "latch" in got[0], got


def test_bores_at_two_different_turns_are_caught(tmp_path):
    """The arm's other refusal: a duplex connector is one moulding, so bores
    whose keyways face different ways cannot take one whichever way it turns."""
    root = tmp_path / "lib"

    def split_turn(c):
        next(q for q in c["parts"] if q["id"] == "rx")["rotate"] = 270
    _copy(root, "common/lc-duplex-v-adapter", 5, "split-v-adapter", split_turn)
    got = l112(root, "test/split-v-adapter@1")
    # turning one bore also swings its mate off the pitch, which the pitch arm
    # reports on its own; the latch arm's finding is the one asked for here
    assert sum("one `rotate`" in e for e in got) == 1, got


def test_the_arm_measures_a_side_on_both_library_adapters():
    """Non-vacuity at the rule's level: the helper the arm uses answers a
    direction for both hosts rather than skipping them, and the two hosts'
    answers differ - so it is not a constant."""
    got = {}
    for ref in (H_ADAPTER, V_ADAPTER):
        sides = lint._spanning_latch_sides(contract(ref), _resolve)
        assert sides is not None, ref
        latch, keyway = sides
        assert latch == keyway, (ref, latch, keyway)
        got[ref] = latch
    assert got[H_ADAPTER] != got[V_ADAPTER], got


def test_both_lc_bores_are_drawn_tongue_down():
    """The convention the arm relies on, held on the parts themselves: each
    bore's outline runs further BELOW its mate than above it."""
    for ref in (RECEPTACLE, BULKHEAD):
        c = contract(ref)
        my = c["connection-points"]["mate"]["at"][1]
        assert c["size"]["h"] - my > my + 1.0, ref

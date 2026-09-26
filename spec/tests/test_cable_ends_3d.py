"""The cable ends build as solids: the four generics and the six vendor wrappers,
all seated at once on a copy of the AGR560 (SFP+, QSFP28 and QSFP-DD cages, upright
and turned), read off the compiled SVG the way kit/relief.js reads it
(docs/pluggables-cables-design.md; the helpers are test_head_3d's).

The per-part files already pin each generic's own chain seated (head, boot, stub,
strap, ring lifts and outs) and each wrapper's stub `r` and colours. This file is
the cross-part check those leave out:

- (a) the `cable` point resolves, as cablePoints/resolveCablePoint does it, to a
  DEPTH at the stub's far end - for every generic and every wrapper, seated;
- (b) the stub's diameter AS THE KIT BUILDS IT (a cyl's radius is half the short
  side of its face box, `mmRect`) is the cable-od in force: the wrapper's, else the
  generic's default;
- (c) no solid is built inside out, on every seated cable end, wrappers included;
- (d) each generic's and each wrapper's standalone preview holds its overhangs
  (every relief node);
- (e) end-on paint order: where two features overlap on the face, the nearer one
  (the larger front z) is drawn after the farther one it covers;
- and the strap's solid ends where its ring's begins, so the two never share a
  front face for the kit to z-fight over.
"""
import shutil
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import warmrender
from test_cable_wrappers import GENERICS, LIB, ROOT, WRAPPERS, doc, field_value
from test_head_3d import DIST, _inside, _viewbox, apply, box, lift_of, rect_corners
from test_nested_occupants import by_path, device_matrix

EPS = 1e-6
NODES = ("head", "relief-boot", "stub", "strap", "strap-ring")

# every cable end, and the agr560 cage it seats in; the generics take cages the
# wrappers leave free, two of them turned (port-1 and qsfp28-3 are rotate 180)
GENERIC_CAGES = {
    "generic/sfp-cable@1": "port-1",
    "generic/qsfp-cable@1": "qsfp28-3",
    "generic/qsfp-dd-cable@1": "qsfpdd-2",
    "generic/qsfp-dd-cable-type2@1": "qsfpdd-3",
}
CAGES = {**GENERIC_CAGES, **{ref: w[4] for ref, w in WRAPPERS.items()}}
EVERY = pytest.mark.parametrize("ref", sorted(CAGES))


def generic_of(ref):
    return WRAPPERS[ref][0] if ref in WRAPPERS else ref


def cable_od(ref):
    """The cable-od in force: the wrapper's own, else the generic's default."""
    if ref in WRAPPERS:
        return field_value(ref, "cable-od")
    return doc(ref)["fields"]["cable-od"]["default"]


def features(ref):
    return {f["node"]: f for f in doc(generic_of(ref))["relief"]["features"]}


def front(parents, el):
    """Where relief.js builds the node's face nearest the viewer: an `out` node's
    absolute data-z-out, a `cyl`'s summed lift plus its length."""
    if el.get("data-z-out") is not None:
        return float(el.get("data-z-out"))
    return lift_of(parents, el) + float(el.get("data-z-cyl"))


def face_box(parents, el):
    """The node's box on the face, as mmRect sees it: its own box through every
    transform between it and the drawing."""
    if el.tag.endswith("circle"):
        cx, cy, r = (float(el.get(k)) for k in ("cx", "cy", "r"))
        pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    else:
        pts = rect_corners(el)
    return box(apply(device_matrix(parents, el), pts))


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cableends3d")
    dev = tmp / "agr560" / "device.yaml"
    shutil.copytree(LIB / "devices/edgecore/agr560", dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["base"]["occupants"] = {cage: ref for ref, cage in CAGES.items()}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(tmp / "o")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(tmp / "o" / "agr560.base.front.svg").getroot()
    return root, {c: p for p in root.iter() for c in p}


def occupant(seated, ref):
    root, parents = seated
    occ = by_path(root, f"{CAGES[ref]}-occupant")
    assert occ.get("data-ref", "").startswith(ref), (ref, occ.get("data-ref"))
    return occ


def nodes(occ):
    """The five relief nodes of the cable end, by their skin id. A wrapper's are
    its composed generic's, under `<occupant>--body--`."""
    got = {}
    for e in occ.iter():
        eid = e.get("id") or ""
        for n in NODES:
            if eid.endswith(f"--{n}"):
                assert n not in got, (n, got[n].get("id"), eid)
                got[n] = e
    assert set(got) == set(NODES), sorted(got)
    return got


# --- (a) the cable point's depth ------------------------------------------------

def resolve_cable_z(parents, mk):
    """kit/relief.js's cablePoints + resolveCablePoint, for a marker `on:` a cyl:
    the marker's ancestors' lifts, plus the feature's own lift summed up to (not
    including) the marker's parent, plus the feature's data-z-cyl. The feature is
    looked up by id inside the marker's own parent, as the kit scopes it."""
    host = parents[mk]
    feat = [e for e in host.iter() if e.get("id") == mk.get("data-cp-on")]
    assert len(feat) == 1, (mk.get("data-cp-on"), len(feat))
    feat = feat[0]
    assert feat.get("data-z-out") is None, "a cyl carries no out; the kit would read it first"
    own, n = 0.0, feat
    while n is not host:
        own += float(n.get("data-z-lift") or 0)
        n = parents[n]
    return lift_of(parents, host) + own + float(feat.get("data-z-cyl")), feat


@EVERY
def test_the_cable_point_resolves_to_the_stubs_far_end(seated, ref):
    """ONE `cable` marker per cable end (a wrapper does not restate it), on the
    stub, and the depth the kit resolves for it is the head's base plus the
    contract's stub lift plus its cyl - the far end, not the head's face and not
    the stub's start. Measured from the head's base, so the cage's seat depth
    drops out; the absolute value is checked against the stub's own build too."""
    _, parents = seated
    occ = occupant(seated, ref)
    marks = [e for e in occ.iter() if e.get("data-cp") == "cable"]
    assert len(marks) == 1, [m.get("data-cp-on") for m in marks]
    mk = marks[0]
    el = nodes(occ)
    assert mk.get("data-cp-on") == el["stub"].get("id")
    z, feat = resolve_cable_z(parents, mk)
    assert feat is el["stub"]
    f = features(ref)
    base = float(el["head"].get("data-z-out")) - f["head"]["out"]
    assert z - base == pytest.approx(f["stub"]["lift"] + f["stub"]["cyl"], abs=EPS)
    assert z == pytest.approx(lift_of(parents, el["stub"]) + float(el["stub"].get("data-z-cyl")))
    # and it stands proud of the head's face: the cable leaves behind the head
    assert z > float(el["head"].get("data-z-out")) + EPS


# --- (b) the stub's diameter ----------------------------------------------------

@EVERY
def test_the_stub_builds_at_the_cable_od_in_force(seated, ref):
    """relief.js builds a cyl of radius min(w, h) / 2 from the node's face box
    (mmRect), so the diameter checked is the compiled circle through every
    transform down to the face - turned cages included - not the skin's `r`."""
    _, parents = seated
    stub = nodes(occupant(seated, ref))["stub"]
    x0, y0, x1, y1 = face_box(parents, stub)
    assert min(x1 - x0, y1 - y0) == pytest.approx(cable_od(ref), abs=1e-6)
    assert max(x1 - x0, y1 - y0) == pytest.approx(cable_od(ref), abs=1e-6)


def test_both_a_wrapper_set_and_a_default_cable_od_are_measured():
    """Not vacuous: the set is not all defaults, nor all overrides."""
    set_by_wrapper = [r for r in WRAPPERS if "cable-od" in (doc(r)["parts"][0].get("attrs") or {})]
    defaults = [r for r in CAGES if r not in set_by_wrapper]
    assert set_by_wrapper and defaults
    # and at least one wrapper sets a value its generic's default is not
    assert any(cable_od(r) != doc(generic_of(r))["fields"]["cable-od"]["default"]
               for r in set_by_wrapper)


# --- (c) no solid is built inside out -------------------------------------------

@EVERY
def test_no_solid_is_built_inside_out(seated, ref):
    """relief.js: a raised node runs from its summed lift to its ABSOLUTE out; a
    cyl from its summed lift for its length. Every raised node under the cable
    end, not only the five named ones."""
    _, parents = seated
    occ = occupant(seated, ref)
    seen = 0
    for el in occ.iter():
        if el.get("data-z-out") is not None:
            seen += 1
            assert float(el.get("data-z-out")) - lift_of(parents, el) > EPS, el.get("id")
        elif el.get("data-z-cyl") is not None:
            seen += 1
            assert float(el.get("data-z-cyl")) > EPS, el.get("id")
    assert seen >= len(NODES), seen


@EVERY
def test_the_head_stands_its_length_and_the_lifts_chain(seated, ref):
    """The head's extent is head.size.d; the boot starts on the head's face and
    the stub on the boot's end. Pinned per generic already; here it covers the
    wrappers too, whose chain runs through the composed `body` group."""
    _, parents = seated
    el = nodes(occupant(seated, ref))
    d = doc(generic_of(ref))["head"]["size"]["d"]
    head_out = float(el["head"].get("data-z-out"))
    assert head_out - lift_of(parents, el["head"]) == pytest.approx(d, abs=EPS)
    assert lift_of(parents, el["relief-boot"]) == pytest.approx(head_out, abs=EPS)
    boot_end = lift_of(parents, el["relief-boot"]) + float(el["relief-boot"].get("data-z-cyl"))
    assert lift_of(parents, el["stub"]) == pytest.approx(boot_end, abs=EPS)
    assert lift_of(parents, el["strap"]) >= head_out - EPS


# --- (d) the standalone preview -------------------------------------------------

@pytest.mark.parametrize("ref", GENERICS + sorted(WRAPPERS))
def test_the_standalone_preview_holds_every_overhang(ref):
    """The Explorer's module preview: a part that declares `head:` gets a root
    viewBox that is the union of its size, its head, its own relief nodes' art and
    its composed parts' own previews (components_index.preview_box), so every
    relief node - the head's overhang above and below the face, the strap and its
    ring lying above it - is inside the drawing. A wrapper declares no `head:`;
    it holds them because it composes its generic's preview whole."""
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    path = DIST / f"{ns}--{name}--v{major}--default.svg"
    if not path.exists():
        pytest.skip(f"needs a build: {path.name}")
    root = ET.parse(path).getroot()
    parents = {c: p for p in root.iter() for c in p}
    size = doc(ref)["size"]
    vb = _viewbox(root)
    # it grew: the head overhangs the size box, so the preview cannot be 0 0 w h
    assert vb != (0.0, 0.0, size["w"], size["h"]), vb
    if root.get("overflow") == "visible":
        return
    el = nodes(root)
    for n, e in el.items():
        assert _inside(face_box(parents, e), vb), (ref, n, face_box(parents, e), vb)


@pytest.mark.parametrize("rotate", [None, 0, 90, 180, 270, -90])
@pytest.mark.parametrize("mirror", [False, True])
def test_a_composed_preview_box_is_placed_as_render_places_it(rotate, mirror):
    """components_index._placed_box: a composed part's own preview box through the
    chain render.py writes. With the part's size box as the preview it is exactly
    facets.projected_box, so a part composing no head-declaring part is unchanged;
    an off-centre box turns about the SIZE centre (180 sends a box standing above
    the part to below it)."""
    from portrayal import components_index as ci, facets
    size = {"w": 18.35, "h": 8.5}
    assert ci._placed_box([3, 4], size, (0.0, 0.0, 18.35, 8.5), rotate, mirror, None) == \
        pytest.approx(facets.projected_box([3, 4], 18.35, 8.5, rotate, None))
    got = ci._placed_box([0, 0], size, (0.0, -3.4, 18.35, 8.5), rotate, mirror, None)
    want = {None: (0, -3.4, 18.35, 8.5), 0: (0, -3.4, 18.35, 8.5),
            180: (0, 0, 18.35, 11.9)}
    if rotate in want:
        assert got == pytest.approx(want[rotate])
    else:           # a quarter turn: 8.5 + 3.4 wide, 18.35 tall, about the centre
        assert got[2] - got[0] == pytest.approx(11.9) and got[3] - got[1] == pytest.approx(18.35)


# --- (e) end-on paint order -----------------------------------------------------

def _overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 1e-3 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-3


@EVERY
def test_a_nearer_feature_is_drawn_after_a_farther_one_it_covers(seated, ref):
    """2D is the view end-on, and document order is paint order. Where two relief
    features overlap on the face, the one whose front stands nearer the viewer
    covers the other, so it must be drawn later - or the 2D drawing shows the
    farther part on top of the nearer one."""
    root, parents = seated
    el = nodes(occupant(seated, ref))
    order = {e: i for i, e in enumerate(root.iter())}
    pairs = 0
    for a in NODES:
        for b in NODES:
            ea, eb = el[a], el[b]
            fa, fb = front(parents, ea), front(parents, eb)
            if fa <= fb + EPS or not _overlap(face_box(parents, ea), face_box(parents, eb)):
                continue
            pairs += 1
            assert order[ea] > order[eb], (
                f"{a} (front {fa:g}) covers {b} (front {fb:g}) but is drawn before it")
    assert pairs >= 2, pairs            # at least boot over head and stub over boot


# --- no shared front face -------------------------------------------------------

@EVERY
def test_the_strap_ends_where_its_ring_begins(seated, ref):
    """The strap and its ring overlap on the face. Had they the same `out` over
    overlapping depths, the ring's front cap and the strap's would be coplanar and
    the kit's depth test would z-fight between them. The strap's solid stops where
    the ring's starts instead; the picture end-on is the same, since the ring
    covers the strap there."""
    _, parents = seated
    el = nodes(occupant(seated, ref))
    assert front(parents, el["strap"]) == pytest.approx(lift_of(parents, el["strap-ring"]), abs=EPS)
    assert front(parents, el["strap-ring"]) > front(parents, el["strap"]) + EPS

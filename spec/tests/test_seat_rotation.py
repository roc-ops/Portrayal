"""A seated part turns with its host (docs/pluggables-slotting-design.md, D3).

941 of the library's 3,326 cages are drawn rotated - 940 at 180, one at 90 on
juniper/mx304 - and until this the build seated an occupant in every one of
them as if it were upright: `at = host.at + host_mate - occupant_mate`, with no
`rotate` carried. On the S9510-28DC's port-2 (then a `common/qsfp-cage@2` at
rotate 180) that put the optic at `translate(230.45,9.94)` with no rotate, the
same offset from its cage as the upright port-0's - so its mate point missed
the cage's turned one, and the optic was drawn the wrong way up. Since the
stacked-cage convention (docs/pluggables-3d-design.md, S3) the pair is upper 0
over lower 180, so the turned cage these tests seat in is port-3.

The fix is two helpers, `seat_point` (where a placement-frame point lands in
the device frame) and `seat_at` (its inverse for the occupant). These tests pin
them by hand arithmetic, prove they reduce EXACTLY to the old formula at
rotate 0 (so every unrotated seat is byte-identical), and then check the real
build on a fitted COPY of the device: both occupants' mate points land on
their host's presented mate point, in the device frame, with the transforms
parsed as numbers (Python writes `9.0` where JS writes `9`).
"""
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
RENDER = SPEC / "tools/portrayal/render.py"
SRC = LIB / "devices/ufispace/s9510-28dc"

from portrayal import render as render_mod
from portrayal.manifest import presented_interface
from portrayal.render import seat_at, seat_point

BOX = {"w": 10, "h": 4}   # centre (5, 2)
LOCAL = [8, 1]            # off-centre: (+3, -1) from the centre


# --- the helpers, by hand -------------------------------------------------

@pytest.mark.parametrize("rotate, want", [
    # (3,-1) turned clockwise on screen (SVG, y down):
    (0, [108, 51]),     # ( 3, -1)
    (90, [106, 55]),    # ( 1,  3)
    (180, [102, 53]),   # (-3,  1)
    (270, [104, 49]),   # (-1, -3)
])
def test_seat_point_by_hand(rotate, want):
    assert seat_point([100, 50], BOX, rotate, LOCAL) == want


@pytest.mark.parametrize("rotate, want", [
    # at = point - centre - turned offset, point (20, 30)
    (0, [12, 29]),
    (90, [14, 25]),
    (180, [18, 27]),
    (270, [16, 31]),
])
def test_seat_at_by_hand(rotate, want):
    assert seat_at([20, 30], rotate, BOX, LOCAL) == want


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
def test_seat_at_puts_the_mate_on_the_point(rotate):
    point = [123.45, 67.8]
    at = seat_at(point, rotate, BOX, LOCAL)
    got = seat_point(at, BOX, rotate, LOCAL)
    assert abs(got[0] - point[0]) < 1e-9 and abs(got[1] - point[1]) < 1e-9


@pytest.mark.parametrize("rotate", [0, None])
def test_unrotated_seat_is_the_old_formula_exactly(rotate):
    """The no-change guarantee: at rotate 0 or None the two helpers compose to
    `host.at + host_mate - occupant_mate`, which is what every unrotated seat
    in the corpus was placed by before this."""
    at, hs, hm = [177.4, 26.2], {"w": 19.5, "h": 10.18}, [9.75, 5.09]
    os_, om = {"w": 18.35, "h": 8.5}, [9.175, 4.25]
    got = seat_at(seat_point(at, hs, rotate, hm), rotate, os_, om)
    assert got == [round(at[0] + hm[0] - om[0], 4), round(at[1] + hm[1] - om[1], 4)]


# --- the real build, on a fitted copy ------------------------------------

def fitted_copy(tmp_path, occupants, edit=None):
    dev = tmp_path / "s9510-28dc" / "device.yaml"
    shutil.copytree(SRC, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["dc"]["occupants"] = occupants
    if edit:
        edit(d)
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def run_render(dev, out):
    return subprocess.run([sys.executable, str(RENDER), str(dev),
                           "--library", str(LIB), "--out", str(out)],
                          capture_output=True, text=True)


def parse_transform(tf):
    """`translate(x,y)` optionally followed by `rotate(deg cx cy)`, as numbers."""
    m = re.fullmatch(r"translate\(([^,]+),([^)]+)\)(?: rotate\(([^ ]+) ([^ ]+) ([^)]+)\))?", tf)
    assert m, tf
    tx, ty = float(m.group(1)), float(m.group(2))
    rot = tuple(float(v) for v in m.group(3, 4, 5)) if m.group(3) else None
    return tx, ty, rot


def apply(tf, pt):
    """A point in a group's own frame, in the device frame: rotate about the
    given centre first, then translate - SVG applies a list right to left."""
    tx, ty, rot = parse_transform(tf)
    x, y = pt
    if rot:
        deg, cx, cy = rot
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        x, y = cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c
    return x + tx, y + ty


def transform_of(svg, path):
    m = re.search(rf'<g[^>]*data-path="{path}"[^>]*transform="([^"]+)"', svg)
    assert m, path
    return m.group(1)


LIBRARY = render_mod.Library([str(LIB)])


def contract(ref):
    return LIBRARY.resolve(ref)[0]


def device_frame_mates(svg, port, host_ref, occ_ref):
    """(host's presented mate, occupant's own mate), both in the device frame."""
    _, hm, _ = presented_interface(contract(host_ref), lambda r: contract(r))
    om = contract(occ_ref)["connection-points"]["mate"]["at"]
    return (apply(transform_of(svg, port), hm),
            apply(transform_of(svg, f"{port}-occupant"), om))


def test_both_optics_mate_on_their_cages(tmp_path):
    occ = "generic/qsfp-lc@1"
    r = run_render(fitted_copy(tmp_path, {"port-3": occ, "port-2": occ}), tmp_path / "o")
    assert r.returncode == 0, r.stderr[-600:]
    svg = (tmp_path / "o" / "s9510-28dc.dc.front.svg").read_text()
    # THE ROTATED ONE TURNS WITH ITS HOST, the upright one does not turn.
    assert parse_transform(transform_of(svg, "port-3"))[2][0] == 180
    assert parse_transform(transform_of(svg, "port-3-occupant"))[2][0] == 180
    assert parse_transform(transform_of(svg, "port-2-occupant"))[2] is None
    for port in ("port-2", "port-3"):
        host_pt, occ_pt = device_frame_mates(svg, port, "common/qsfp-cage@2", occ)
        assert abs(host_pt[0] - occ_pt[0]) < 1e-6, (port, host_pt, occ_pt)
        assert abs(host_pt[1] - occ_pt[1]) < 1e-6, (port, host_pt, occ_pt)


def _front_placements(d):
    return d["views"]["front"]["components"]["placements"]


def test_a_seated_part_that_turns_away_from_its_host_is_an_error(tmp_path):
    def edit(d):
        _front_placements(d).append({"ref": "generic/qsfp-lc@1", "id": "opt-x",
                                     "mate-to": "port-3", "rotate": 90})
    r = run_render(fitted_copy(tmp_path, {}, edit), tmp_path / "o")
    assert r.returncode != 0
    assert "turns with its host" in r.stderr


def test_a_seated_part_that_states_its_hosts_turn_is_fine(tmp_path):
    def edit(d):
        _front_placements(d).append({"ref": "generic/qsfp-lc@1", "id": "opt-x",
                                     "mate-to": "port-3", "rotate": 180})
    r = run_render(fitted_copy(tmp_path, {}, edit), tmp_path / "o")
    assert r.returncode == 0, r.stderr[-600:]


def test_a_mirrored_host_cannot_seat(tmp_path):
    def edit(d):
        for p in _front_placements(d):
            if p.get("id") == "port-0":
                p["mirror"] = True
    r = run_render(fitted_copy(tmp_path, {"port-0": "generic/qsfp-lc@1"}, edit),
                   tmp_path / "o")
    assert r.returncode != 0
    assert "mirrored" in r.stderr


# --- a chained seat in a rotated cage -------------------------------------

CSR310 = LIB / "devices/edgecore/csr310"


def test_a_chained_seat_turns_with_the_whole_stack(tmp_path):
    """A plug in an optic's bore, and a boot on the plug, with the optic in a
    rotate-180 cage (csr310 `m1-1`). The optic's seated dict carries the turn,
    `hosts` hands that dict to the plug, and the plug's to the boot - so each
    link must land its own mate on its host's TURNED mate point, and each must
    be drawn at 180 too. `generic/sfp-lc-simplex@2` is the optic because it
    composes ONE `std/lc-bore@3`, so it presents a single `lc-plug` mate for
    the plug to seat in (the duplex generics present none)."""
    dev = tmp_path / "csr310" / "device.yaml"
    shutil.copytree(CSR310, dev.parent)
    d = yaml.safe_load(dev.read_text())
    cage = next(p for p in _front_placements(d) if p.get("id") == "m1-1")
    assert cage.get("rotate") == 180, cage
    # every configuration renders the same view, so every one seats the optic
    # the hand-written links below mate to
    for cfg in d["configurations"].values():
        cfg["occupants"] = {"m1-1": "generic/sfp-lc-simplex@2"}
    _front_placements(d).extend([
        {"ref": "generic/lc-plug@1", "id": "plug1", "mate-to": "m1-1-occupant"},
        {"ref": "common/lc-boot@1", "id": "boot1", "mate-to": "plug1"}])
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = run_render(dev, tmp_path / "o")
    assert r.returncode == 0, r.stderr[-600:]
    svg = next((tmp_path / "o").glob("csr310.*.front.svg")).read_text()

    chain = [("m1-1", cage["ref"]), ("m1-1-occupant", "generic/sfp-lc-simplex@2"),
             ("plug1", "generic/lc-plug@1"), ("boot1", "common/lc-boot@1")]
    for (host, host_ref), (occ, occ_ref) in zip(chain, chain[1:]):
        assert parse_transform(transform_of(svg, occ))[2][0] == 180, occ
        _, hm, _ = presented_interface(contract(host_ref), lambda r: contract(r))
        om = contract(occ_ref)["connection-points"]["mate"]["at"]
        hp = apply(transform_of(svg, host), hm)
        op = apply(transform_of(svg, occ), om)
        assert abs(hp[0] - op[0]) < 1e-6 and abs(hp[1] - op[1]) < 1e-6, (occ, hp, op)

    # AND THE PLUG LANDS IN THE BORE, not merely on whatever point
    # presented_interface forwards. The optic's own `optical` point is the
    # bore's centre, declared independently of the composition, so the plug's
    # mate must land on it in the device frame too. Before the forwarded point
    # went through the composed bore's rotate: 180, it sat 1.6 mm off it.
    optical = contract("generic/sfp-lc-simplex@2")["connection-points"]["optical"]["at"]
    want = apply(transform_of(svg, "m1-1-occupant"), optical)
    got = apply(transform_of(svg, "plug1"), contract("generic/lc-plug@1")["connection-points"]["mate"]["at"])
    assert abs(want[0] - got[0]) < 1e-6 and abs(want[1] - got[1]) < 1e-6, (want, got)


# --- a plug seats in the bore's centre, for every generic ------------------

from portrayal import libwalk  # noqa: E402

LC_BORE = "std/lc-bore@3"


def _generics_with_a_rotated_lc_bore():
    """Every generic contract composing std/lc-bore@3 at a non-zero rotate, as
    (ref, part, the optical point that part is the bore of). Walked, not
    listed: a generic added later joins by composing the bore."""
    out = []
    for f in libwalk.iter_components([str(LIB)]):
        ref = libwalk.ref_of(f)
        if not ref.startswith("generic/"):
            continue
        c = contract(ref)
        bores = [q for q in (c.get("parts") or [])
                 if q.get("ref") == LC_BORE and float(q.get("rotate") or 0) % 360]
        cps = c.get("connection-points") or {}
        for q in bores:
            # one bore is the part's `optical`; a pair is optical-<id>
            name = "optical" if len(bores) == 1 else f"optical-{q['id']}"
            out.append((ref, q, cps[name]["at"]))
    return out


ROTATED_BORES = _generics_with_a_rotated_lc_bore()


def test_the_walk_found_the_rotated_bores():
    """Not vacuous: the four generic transceivers compose seven, all at 180."""
    refs = {r for r, _, _ in ROTATED_BORES}
    assert {"generic/sfp-lc@1", "generic/sfp-lc-simplex@2", "generic/qsfp-lc@1",
            "generic/qsfp-dd-lc@1"} <= refs, refs
    assert len(ROTATED_BORES) >= 7, ROTATED_BORES


@pytest.mark.parametrize("ref,part,optical", ROTATED_BORES,
                         ids=[f"{r}:{q['id']}" for r, q, _ in ROTATED_BORES])
def test_a_plug_in_a_rotated_bore_lands_on_its_optical_point(ref, part, optical):
    """presented_interface on a host holding just this one bore - the case a
    single-bore host is, and the one a plug seats by - must forward the bore's
    centre, which the generic declares as its optical point."""
    _, at, _ = presented_interface({"parts": [part]}, lambda r: contract(r))
    assert at == pytest.approx(optical, abs=1e-6), (
        f"{ref} {part['id']}: a plug seated in this bore lands at {at}, but the "
        f"bore's optical point is {optical}")

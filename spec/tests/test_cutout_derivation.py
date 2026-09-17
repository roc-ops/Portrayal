"""A cutout restates an aperture the component already declares (#5).

Backfilling 437 holes across twelve devices was only safe because it invents
nothing: the position is the placement's own `at`, already measured, and the
size is the registry entry the component `conforms:` to, or the component's own
size when it conforms to nothing. These tests hold that rule, because the moment
a cutout can drift from its component it becomes a second place to record one
fact - and the drawing will believe whichever is wrong.
"""
import functools
import glob
import math
import pathlib

import yaml
from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]
STD = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]
DEVICES = [str(p) for p in libwalk.iter_devices([ROOT / "library"])]


@functools.lru_cache(maxsize=None)
def contract(ref):
    try:
        ns, rest = ref.split("/", 1); name, major = rest.split("@")
    except Exception:
        return None
    g = sorted(glob.glob(str(ROOT / f"library/components/{ns}/{name}/v{major}/contract.yaml")))
    return yaml.safe_load(open(g[-1])) if g else None


def aperture(ref, depth=0):
    """Forwards through a composed cage, as `presented_interface` does for mates.

    `common/qsfp28-cage@3` declares no `conforms` and wraps `std/qsfp-ganged@1`
    at [0.25, 4.2]. Reading only the wrapper reported the AS7726-32X - a 32-port
    switch - as having no derivable aperture at all.

    Returns `(size, offset)` where `size` is a `(w, h)` pair - the registry entry
    a part `conforms:` to, or that part's own `size` when it conforms to nothing
    (the same fallback `expected()` applies at the top level, applied at every
    depth: `std/rj45@1` and `std/rj45-ganged@1` stopped conforming in #125 and are
    still composed inside bezels like `common/rj45-hd@1`, so the rule has to hold
    wherever a leaf part sits, not only where a device places one directly).
    """
    ct = contract(ref)
    if not ct or depth > 3:
        return None
    if ct.get("conforms") in STD:
        st = STD[ct["conforms"]]
        return (st["w"], st["h"]), [0.0, 0.0]
    found = []
    for part in (ct.get("parts") or []):
        sub = aperture(part.get("ref", ""), depth + 1)
        if sub:
            o = part.get("at") or [0, 0]
            found.append((sub[0], [o[0] + sub[1][0], o[1] + sub[1][1]]))
    # Mirrors `_aperture_of` in spec/tools/portrayal/lint.py: only a single
    # resolved sub-aperture is trusted; zero or multiple fall back to the
    # composing contract's own size.
    if len(found) == 1:
        return found[0]
    sz = ct.get("size") or {}
    if sz.get("w") and sz.get("h"):
        return (sz["w"], sz["h"]), [0.0, 0.0]
    return None


def pairs():
    """Every cutout that shares its id with a placement, across the library."""
    for path in DEVICES:
        d = yaml.safe_load(open(path)) or {}
        for vn, v in (d.get("views") or {}).items():
            cuts = {c["id"]: c for c in ((v or {}).get("panel") or {}).get("cutouts") or []}
            for it in (((v or {}).get("components") or {}).get("placements") or []):
                c = cuts.get(it.get("id"))
                if c and it.get("at"):
                    yield path.split("devices/")[1], vn, it, c


def test_the_corpus_is_worth_checking():
    assert sum(1 for _ in pairs()) > 400


def expected(it):
    """Where the aperture lands, honouring rotation the way the renderer does.

    A placement is drawn `translate(at) rotate(deg, cw/2, ch/2)` - it turns about
    the WRAPPER's centre, not the hole's. With an aperture that sits off-centre
    inside its wrapper that matters at 180 as well as at 90, which is the bug
    this caught: sixteen QSFP28 ports on the AS7726-32X were written 3.48mm high
    because `common/qsfp28-cage@3` holds its aperture at [0.25, 4.2] in a
    19 x 14.5 body, and a half turn puts it at [0.25, 0.72].
    """
    ct = contract(str(it.get("ref") or ""))
    if not ct:
        return None
    a = aperture(str(it["ref"]))
    if a:
        (aw, ah), (ax, ay) = a
    else:
        sz = ct.get("size") or {}
        aw, ah, ax, ay = sz.get("w"), sz.get("h"), 0.0, 0.0
    if not aw:
        return None
    cw = (ct.get("size") or {}).get("w", aw)
    ch = (ct.get("size") or {}).get("h", ah)
    r = math.radians((it.get("rotate") or 0) % 360)
    c, s_ = math.cos(r), math.sin(r)
    cx, cy = cw / 2, ch / 2
    pts = [((cx + (px - cx) * c - (py - cy) * s_), (cy + (px - cx) * s_ + (py - cy) * c))
           for px in (ax, ax + aw) for py in (ay, ay + ah)]
    xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
    return ([it["at"][0] + min(xs), it["at"][1] + min(ys)],
            [max(xs) - min(xs), max(ys) - min(ys)])


# Hand-authored cutouts that predate this rule and sit a fraction off their
# component, or size it differently - 0.2mm off on an MX104 lamp, a 2.0mm LED
# given a 2.4mm hole, 7mm studs through 6mm ones. Frozen rather
# than fixed: they are within what L39 accepts and nobody has re-measured them,
# and a list that cannot grow is worth more than a tolerance that hides the next
# one. Shrink it when a device is next opened; never add to it.
PRE_EXISTING = {
    "juniper/mx104/device.yaml:front:btn-online",
    "juniper/mx104/device.yaml:front:led-sys-ok",
    "juniper/mx104/device.yaml:rear:ground-stud-0",
    "juniper/mx104/device.yaml:rear:ground-stud-1",
    "juniper/mx150/device.yaml:front:led-beacon",
    "juniper/mx150/device.yaml:front:port-10",
    "juniper/mx150/device.yaml:front:port-11",
    "juniper/mx150/device.yaml:front:xe-0",
    "juniper/mx150/device.yaml:front:xe-1",
    "juniper/mx150/device.yaml:rear:fan-0",
    "juniper/mx150/device.yaml:rear:fan-1",
    "juniper/mx150/device.yaml:rear:ground-stud-0",
    "juniper/mx150/device.yaml:rear:ground-stud-1",
    "juniper/mx204/device.yaml:front:led-alm",
    "juniper/mx204/device.yaml:front:led-ok-fail",
    "juniper/mx204/device.yaml:front:led-online",
    "juniper/mx204/device.yaml:front:led-ssd0",
    "juniper/mx204/device.yaml:front:led-ssd1",
    "juniper/mx80/device.yaml:front:btn-online",
    "juniper/mx80/device.yaml:front:led-re",
    "juniper/mx80/device.yaml:front:led-sys-ok",
    "juniper/mx80/device.yaml:rear:ground-stud-0",
    "juniper/mx80/device.yaml:rear:ground-stud-1",
}


def test_a_cutout_sits_where_its_component_sits():
    """`at` is never re-derived, so a hole cannot drift from the part in it."""
    bad = []
    for dev, vn, it, c in pairs():
        e = expected(it)
        if not e:
            continue
        if any(abs(x - y) > 0.02 for x, y in zip(e[0], c["at"])):
            bad.append(f"{dev}:{vn}:{it['id']}")
    assert set(bad) <= PRE_EXISTING, \
        f"cutouts adrift from their component: {sorted(set(bad) - PRE_EXISTING)[:6]}"


def test_a_cutout_is_the_size_of_its_aperture():
    bad = []
    for dev, vn, it, c in pairs():
        e = expected(it)
        if not e:
            continue
        if any(abs(x - y) > 0.02 for x, y in zip(e[1], c["size"])):
            bad.append(f"{dev}:{vn}:{it['id']}")
    assert set(bad) <= PRE_EXISTING, \
        f"cutouts disagreeing with their aperture: {sorted(set(bad) - PRE_EXISTING)[:6]}"


def test_the_rotated_ones_are_actually_exercised():
    """Rotation is where this went wrong twice, so the corpus has to contain it."""
    n = sum(1 for _, _, it, _ in pairs() if (it.get("rotate") or 0) % 360)
    assert n >= 50, f"only {n} rotated cutouts; this proves little"


def test_no_bay_is_given_a_cutout():
    """A bay declares its own opening, so a cutout would be a second place to
    record the same hole. The ASR 9001 has 17 cutouts and gives none of them to
    its five bays - which is also why the four big MX chassis, which are all
    bays, are not part of this backfill."""
    bad = []
    for path in DEVICES:
        d = yaml.safe_load(open(path)) or {}
        for vn, v in (d.get("views") or {}).items():
            cuts = {c["id"] for c in ((v or {}).get("panel") or {}).get("cutouts") or []}
            for b in (((v or {}).get("components") or {}).get("bays") or []):
                if b.get("id") in cuts:
                    bad.append((path.split("devices/")[1], vn, b["id"]))
    assert not bad, f"bays given cutouts: {bad[:4]}"

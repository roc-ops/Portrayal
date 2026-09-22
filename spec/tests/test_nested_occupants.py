"""An optic in a cage on a card seated in a chassis bay (#484, R2).

A configuration's `occupants:` may key a cage inside a seated module by the
manifest's MODULE-LESS path - `front-6/xg0`, the convention nested `bays:`
keys already use (kit/swap.js configBayPath, #440). The occupant is drawn
INSIDE the module's instance group, at `front-6/module/xg0-occupant`, so it
inherits the bay transform (translate + rotate) instead of having it solved a
second time, and it is positioned by the card-frame mate points - the same
seat_point / seat_at the device-level seat uses.

Portrayal ships no populated device, so every test seats on a COPY in
tmp_path (the test_occupants.py idiom). Positions are checked numerically:
every ancestor transform of the optic and of the cage is composed into one
affine map, and the optic's own `mate` must land on the cage's `mate` in the
device frame to 1e-6. The component's PUBLISHED cage `mate` (components.json,
component_cages) is held to the same device point through the card's
ancestors, so the build and what the kit will read cannot drift apart.
"""
import math
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

from portrayal.manifest import presented_interface
from portrayal.render import (Library, component_cages, _pluggable_families,
                              _pluggable_candidates)

_lib = Library([str(LIB)])


def _contract(ref):
    return _lib.resolve(ref)[0]


def fitted_copy(tmp_path, name, config, bays, occupants):
    """casa/<name> with `bays` merged into `config` and `occupants` injected."""
    dev = tmp_path / name / "device.yaml"
    shutil.copytree(LIB / "devices/casa" / name, dev.parent)
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"][config]
    cfg["bays"] = {**(cfg.get("bays") or {}), **bays}
    cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def run(dev, out):
    return subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                           "--library", str(LIB), "--out", str(out)],
                          capture_output=True, text=True)


def render(dev, out, name, config):
    r = run(dev, out)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / f"{name}.{config}.front.svg").getroot()
    return root, {c: p for p in root.iter() for c in p}


# --- transforms, parsed numerically -----------------------------------------

def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _op(name, args):
    if name == "translate":
        tx, ty = (args + [0.0])[:2]
        return [[1, 0, tx], [0, 1, ty], [0, 0, 1]]
    if name == "scale":
        sx = args[0]
        sy = args[1] if len(args) > 1 else sx
        return [[sx, 0, 0], [0, sy, 0], [0, 0, 1]]
    if name == "rotate":
        deg = args[0]
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        r = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
        if len(args) == 3:
            cx, cy = args[1], args[2]
            return _mul(_mul(_op("translate", [cx, cy]), r), _op("translate", [-cx, -cy]))
        return r
    raise AssertionError(f"unexpected transform op {name}")


def _matrix(tf):
    m = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for name, body in re.findall(r"(\w+)\(([^)]*)\)", tf or ""):
        m = _mul(m, _op(name, [float(v) for v in re.split(r"[ ,]+", body.strip())]))
    return m


def device_matrix(parents, el):
    """Every transform from `el` up to the root, composed into one affine map."""
    chain = []
    node = el
    while node is not None:
        chain.append(node)
        node = parents.get(node)
    m = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for node in reversed(chain):
        m = _mul(m, _matrix(node.get("transform")))
    return m


def device_point(parents, el, local):
    """`local`, a point in `el`'s own frame, in the device frame."""
    m = device_matrix(parents, el)
    x, y = local
    return (m[0][0] * x + m[0][1] * y + m[0][2], m[1][0] * x + m[1][1] * y + m[1][2])


def by_path(root, path):
    hits = [n for n in root.iter() if n.get("data-path") == path]
    assert len(hits) == 1, (path, len(hits))
    return hits[0]


def is_inside(parents, el, ancestor):
    node = parents.get(el)
    while node is not None:
        if node is ancestor:
            return True
        node = parents.get(node)
    return False


def own_mate(el):
    ref = el.get("data-ref").rsplit(":", 1)[0]
    return _contract(ref)["connection-points"]["mate"]["at"]


def cage_mate(el):
    ref = el.get("data-ref").rsplit(":", 1)[0]
    _, at, _ = presented_interface(_contract(ref), _contract)
    return at


_pluggables = []


def published_cage(card_ref, cage_id):
    if not _pluggables:
        _pluggables.extend([_pluggable_families(), _pluggable_candidates([str(LIB)])])
    families, candidates = _pluggables
    return next(c for c in component_cages(_contract(card_ref), _lib, families, candidates)
                if c["id"] == cage_id)


def assert_seated(root, parents, card_path, card_ref, cage):
    card = by_path(root, card_path)
    host = by_path(root, f"{card_path}/{cage}")
    occ = by_path(root, f"{card_path}/{cage}-occupant")
    assert is_inside(parents, occ, card), "the optic is not inside the module group"
    assert occ.get("data-for") == f"{card_path}/{cage}"
    assert occ.get("id") == f"{card.get('id')}--{cage}-occupant"
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, ((hx, hy), (ox, oy))
    # AND IT TURNS WITH ITS CAGE. The generic optics put `mate` at their own
    # centre, so a landing check alone cannot see orientation: an optic drawn
    # upright in a turned cage lands its centre on the same point. The linear
    # part of the composed map (rotation, and any mirror) must be the cage's.
    assert_same_turn(parents, occ, host)
    # and what the component publishes for the kit lands on the same point
    pub = published_cage(card_ref, cage)
    px, py = device_point(parents, card, pub["mate"])
    assert abs(px - hx) < 1e-6 and abs(py - hy) < 1e-6, ((px, py), (hx, hy))
    return (hx, hy), (ox, oy)


def assert_same_turn(parents, occ, host):
    mo, mh = device_matrix(parents, occ), device_matrix(parents, host)
    for i in range(2):
        for j in range(2):
            assert abs(mo[i][j] - mh[i][j]) < 1e-9, ("turn", mo, mh)


def effective_lift(parents, el):
    """relief.js's liftOf: data-z-lift summed up the ancestor chain."""
    total, node = 0.0, el
    while node is not None:
        total += float(node.get("data-z-lift") or 0)
        node = parents.get(node)
    return total


C100G_OCC = {"front-6/xg0": "generic/sfp-lc@1", "front-6/cg0": "generic/qsfp-lc@1"}


def test_an_optic_seats_in_a_cage_on_a_card_in_a_bay(tmp_path):
    dev = fitted_copy(tmp_path, "c100g", "base", {"front-6": "casa/smm-300gm@1"}, C100G_OCC)
    root, parents = render(dev, tmp_path / "o", "c100g", "base")
    for cage in ("xg0", "cg0"):
        assert_seated(root, parents, "front-6/module", "casa/smm-300gm@1", cage)
    # exactly the two optics named, and nothing at device level
    refs = [n.get("data-ref") for n in root.iter() if n.get("data-path", "").endswith("-occupant")]
    assert sorted(r.split(":")[0] for r in refs) == ["generic/qsfp-lc@1", "generic/sfp-lc@1"]


def test_the_same_on_a_card_in_a_rotated_bay(tmp_path):
    """The C40G's cards are seated at rotate 90 - the bay transform the optic
    inherits is a turn, not only a shift."""
    dev = fitted_copy(tmp_path, "c40g", "base", {"front-2": "casa/smm-8x10g@1"},
                      {"front-2/xg0": "generic/sfp-lc@1"})
    root, parents = render(dev, tmp_path / "o", "c40g", "base")
    card = by_path(root, "front-2/module")
    assert "rotate(90" in card.get("transform")
    assert_seated(root, parents, "front-2/module", "casa/smm-8x10g@1", "xg0")


def test_a_chained_seat_on_a_nested_optic(tmp_path):
    """A plug in the nested optic, a boot on that plug: the same fixed point
    as at device level, keyed by the card-local occupant id."""
    dev = fitted_copy(tmp_path, "c100g", "base", {"front-6": "casa/smm-300gm@1"},
                      {"front-6/xg0": "generic/sfp-lc-simplex@2",
                       "front-6/xg0-occupant": "generic/lc-plug@1",
                       "front-6/xg0-occupant-occupant": "common/lc-boot@1"})
    root, parents = render(dev, tmp_path / "o", "c100g", "base")
    card = by_path(root, "front-6/module")
    for host_p in ("front-6/module/xg0-occupant", "front-6/module/xg0-occupant-occupant"):
        host = by_path(root, host_p)
        occ = by_path(root, f"{host_p}-occupant")
        assert is_inside(parents, occ, card)
        assert occ.get("data-for") == host_p
        _, hm, _ = presented_interface(_contract(host.get("data-ref").rsplit(":", 1)[0]), _contract)
        hx, hy = device_point(parents, host, hm)
        ox, oy = device_point(parents, occ, own_mate(occ))
        assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, (host_p, (hx, hy), (ox, oy))
        assert_same_turn(parents, occ, host)
    # the chain carries the stack of lifts, as a device-level chain does: the
    # plug stands on what the optic presents, the boot on the plug body AND on
    # what the plug already stands at. Both non-zero, so neither passes by
    # being 0 == 0.
    lift = lambda p: float(by_path(root, p).get("data-z-lift") or 0)
    presents = lambda r: float(presented_interface(_contract(r), _contract)[2] or 0)
    optic, body = presents("generic/sfp-lc-simplex@2"), presents("generic/lc-plug@1")
    assert optic and body
    assert lift("front-6/module/xg0-occupant") == 0
    assert lift("front-6/module/xg0-occupant-occupant") == pytest.approx(optic)
    assert lift("front-6/module/xg0-occupant-occupant-occupant") == pytest.approx(optic + body)


@pytest.mark.parametrize("key, why", [
    ("front-6/xg99", "names no cage"),           # no such cage on the card
    ("front-7/xg0", "names no cage"),            # the bay holds a blank plate
    ("front-99/xg0", "no bay"),                  # no such bay anywhere
])
def test_a_key_naming_no_cage_is_an_error(tmp_path, key, why):
    dev = fitted_copy(tmp_path, "c100g", "base", {"front-6": "casa/smm-300gm@1"},
                      {key: "generic/sfp-lc@1"})
    r = run(dev, tmp_path / "o")
    assert r.returncode != 0
    assert key in r.stderr and why in r.stderr, r.stderr[-800:]


def test_an_empty_bay_seats_no_nested_optic(tmp_path):
    dev = fitted_copy(tmp_path, "c100g", "base", {"front-6": ""},
                      {"front-6/xg0": "generic/sfp-lc@1"})
    r = run(dev, tmp_path / "o")
    assert r.returncode != 0 and "front-6/xg0" in r.stderr, r.stderr[-800:]


def test_a_raised_cage_on_a_card_lifts_its_optic(tmp_path):
    """smartoptics/dcp-404's cages are composed at `lift: 44` - the raised
    shelf. The optic sits BESIDE the cage group, not in it, so it takes that
    raise only through its own data-z-lift: the published cage `lift`, and
    its effective lift is the card's plus that, where the cage's own is."""
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-2", tmp_path / "dcp-2") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["dcp-404-x1"]["occupants"] = {"slot-1/c1": "generic/qsfp-lc@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    root, parents = render(dev, tmp_path / "o", "dcp-2", "dcp-404-x1")
    assert_seated(root, parents, "slot-1/module", "smartoptics/dcp-404@1", "c1")
    pub = published_cage("smartoptics/dcp-404@1", "c1")
    assert pub["lift"] == 44.0
    occ = by_path(root, "slot-1/module/c1-occupant")
    card = by_path(root, "slot-1/module")
    assert float(occ.get("data-z-lift")) == pub["lift"]
    assert effective_lift(parents, occ) == pytest.approx(effective_lift(parents, card) + pub["lift"])


def test_a_bay_only_on_an_unbound_variant_face_is_reported(tmp_path):
    """The R740xd's LFF drive bays live on the `front-lff-12` variant, which
    the default configuration does not bind: no drawing shows them, so a key
    naming one is an error, not a silent skip."""
    dev = shutil.copytree(LIB / "devices/dell/r740xd", tmp_path / "r740xd") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = next(n for n, c in d["configurations"].items() if c.get("default"))
    assert "front-lff-12" not in (d["configurations"][cfg].get("views") or {}).values()
    d["configurations"][cfg]["occupants"] = {"lff-drive-0/port": "generic/sfp-lc@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = run(dev, tmp_path / "o")
    assert r.returncode != 0
    assert "lff-drive-0/port" in r.stderr and "no bay in any view" in r.stderr, r.stderr[-800:]


def test_a_spec_without_a_ref_names_its_key(tmp_path):
    dev = fitted_copy(tmp_path, "c100g", "base", {"front-6": "casa/smm-300gm@1"},
                      {"front-6/xg0": {"attrs": {"speed": "10G"}}})
    r = run(dev, tmp_path / "o")
    assert r.returncode != 0
    assert "occupants/front-6/xg0: names no component" in r.stderr, r.stderr[-800:]
    assert "KeyError" not in r.stderr


# --- lint L12 reaches a nested key -------------------------------------------

from portrayal import lint


def l12(dev):
    data = yaml.safe_load(dev.read_text())
    with lint.collecting() as got:
        lint.lint_device_occupants(dev, data, [str(LIB)])
    return [e for e in got.errors if "[L12]" in e]


def test_lint_a_valid_nested_key_and_its_chain_lint_clean(tmp_path):
    dev = fitted_copy(tmp_path, "c100g", "base", {"front-6": "casa/smm-300gm@1"},
                      {"front-6/xg0": "generic/sfp-lc-simplex@2",
                       "front-6/xg0-occupant": "generic/lc-plug@1",
                       "front-6/xg0-occupant-occupant": "common/lc-boot@1",
                       "front-6/cg0": "generic/qsfp-lc@1"})
    assert l12(dev) == []


@pytest.mark.parametrize("occ, why", [
    ({"front-6/xg0": "generic/qsfp-lc@1"}, "presents 'sfp'"),      # wrong optic
    ({"front-6/xg99": "generic/sfp-lc@1"}, "names no cage"),        # no such cage
    ({"front-7/xg0": "generic/sfp-lc@1"}, "names no cage"),         # blank plate
    ({"front-99/xg0": "generic/sfp-lc@1"}, "no bay in any view"),  # no such bay
    ({"front-6/xg0": "generic/sfp-lc@1",
      "front-6/xg0-occupant": "generic/lc-plug@1"},                 # the chain reaches the optic,
     "host generic/sfp-lc@1 presents no 'interface'"),              # which presents nothing
])
def test_lint_a_bad_nested_key_is_an_l12_error(tmp_path, occ, why):
    dev = fitted_copy(tmp_path, "c100g", "base", {"front-6": "casa/smm-300gm@1"}, occ)
    got = l12(dev)
    assert got and any(why in e for e in got), got

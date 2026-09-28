"""The generic coax plugs (#650, docs/connectors-coax-design.md section 5).

Each is the #621 cable-end shape seen from the face: a coupling part, a
strain relief `cyl`, and a 30 mm stub `cyl` sized by `cable-od`, with the
`cable` point on the stub's far end.
"""
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal.artifacts import face_file
from test_nested_occupants import by_path, cage_mate, device_point, own_mate

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# plug -> (interface it mates, default cable-od, the jack it seats in)
PLUGS = {
    "generic/sma-plug@1": ("sma", 2.49, "std/sma@1"),
    "generic/smb-plug@1": ("smb", 2.49, "std/smb@1"),
    "generic/mcx-plug@1": ("mcx", 2.49, "std/mcx@1"),
    "generic/f-type-plug@1": ("f-type", 6.96, "std/f-type@1"),
    "generic/bnc-plug@1": ("bnc", 4.90, "std/bnc@1"),
    "generic/din-1-0-2-3-plug@1": ("din-1-0-2-3", 2.54, "std/din-1-0-2-3@1"),
}
EACH = pytest.mark.parametrize("ref", sorted(PLUGS))

# plug -> where it is seated: (device, configuration, view, bays merged into the
# configuration, the host's data-path). The occupant key is the host's path
# with `/module` dropped (a card port is keyed `<bay>/<port>`); the occupant is
# drawn at `<host path>-occupant`. SMA and SMB seat in a device placement; MCX
# has no device-level port in the library, so it seats in a card port through
# the card's nested occupant key; so does F (casa/rfd@1). 1.0/2.3 seats in a
# real Cisco T3/E3 SPA port (a common/din-1-0-2-3-jack@1 placement), two bays
# deep: an A9K-SIP-700 in slot-0 and the SPA in its bay-2. No device or card
# places a BNC jack, so BNC seats in a device copy whose placement at the host
# path is REPLACED by the bezel named in SWAPS.
SEATS = {
    "generic/sma-plug@1": ("ufispace/s9500-30xs", "base", "front", {}, "pps-in"),
    "generic/smb-plug@1": ("juniper/mx304", "base", "rear", {}, "clk-1pps-in"),
    "generic/mcx-plug@1": ("casa/c100g", "base", "rear", {"rear-0": "casa/ups-32x4@1"},
                           "rear-0/module/p0"),
    "generic/f-type-plug@1": ("casa/c100g", "base", "rear", {"rear-1": "casa/rfd@1"},
                              "rear-1/module/p0"),
    "generic/bnc-plug@1": ("cisco/asr-9901", "base", "front", {}, "gps-1pps"),
    "generic/din-1-0-2-3-plug@1": ("cisco/asr-9010", "base", "front",
                                   {"slot-0": "cisco/a9k-sip-700@2",
                                    "slot-0/bay-2": "cisco/spa-4xt3e3@1"},
                                   "slot-0/module/bay-2/module/p0-tx"),
}
# plug -> the bezel its host places (its composed core is the jack in PLUGS).
BEZELS = {
    "generic/bnc-plug@1": "common/bnc-jack@1",
    "generic/din-1-0-2-3-plug@1": "common/din-1-0-2-3-jack@1",
}
# plug -> the bezel that REPLACES the placement at its host path in a tmp
# device copy, because nothing in the library places that jack (see SEATS).
SWAPS = {"generic/bnc-plug@1": BEZELS["generic/bnc-plug@1"]}
NODES = ("coupling", "relief-boot", "stub")


def doc(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / f"components/{ns}/{name}/v{major}/contract.yaml").read_text())


def skin(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return (LIB / f"components/{ns}/{name}/v{major}/skins/default.svg").read_text()


@EACH
def test_it_is_a_plug_that_mates_its_interface(ref):
    d = doc(ref)
    assert d["class"] == "port" and "behaviour" not in d
    assert d["mates"] == PLUGS[ref][0]
    assert d["conforms"] == f"{PLUGS[ref][0]}-plug"


@EACH
def test_its_fields_are_the_cable(ref):
    f = doc(ref)["fields"]
    assert set(f) == {"cable-od", "jacket-color"}
    assert f["cable-od"]["default"] == pytest.approx(PLUGS[ref][1], abs=0.1)


@EACH
def test_a_generic_states_no_impedance(ref):
    if PLUGS[ref][0] == "f-type":
        assert doc(ref)["attrs"]["impedance"] == 75
    else:
        assert "impedance" not in (doc(ref).get("attrs") or {})


@EACH
def test_the_stub_is_30_long_from_the_end_of_the_relief(ref):
    feats = {f["node"]: f for f in doc(ref)["relief"]["features"]}
    boot, stub = feats["relief-boot"], feats["stub"]
    assert stub["cyl"] == pytest.approx(30)
    assert stub["lift"] == pytest.approx(boot["lift"] + boot["cyl"])


@EACH
def test_the_relief_boot_starts_where_the_coupling_ends(ref):
    """The coupling -> boot link of the chain the test above checks from boot
    to stub: a coupling written as `out` ends at its `out` (absolute), one
    written as `cyl` at `lift + cyl`. A gap or an overlap between the two fails."""
    feats = {f["node"]: f for f in doc(ref)["relief"]["features"]}
    c = feats["coupling"]
    rear = c["out"] if c.get("out") is not None else (c.get("lift") or 0) + c["cyl"]
    assert feats["relief-boot"]["lift"] == pytest.approx(rear)


@EACH
def test_the_cable_leaves_from_the_stub(ref):
    cps = doc(ref)["connection-points"]
    assert cps["cable"]["on"] == "stub"
    assert "mate" in cps


@EACH
def test_the_stub_circle_is_bound_to_the_fields(ref):
    s = skin(ref)
    for node in NODES:
        assert f'id="{node}"' in s, node
    stub = s[s.index('id="stub"'):].split("/>", 1)[0]
    assert 'data-r-from="cable-od"' in stub
    assert 'data-fill-from="jacket-color"' in stub
    r = float(stub.split('r="', 1)[1].split('"', 1)[0])
    assert r == pytest.approx(PLUGS[ref][1] / 2, abs=0.05)


# --- seated in real devices ------------------------------------------------------

@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    """Each plug in SEATS, seated in a copy of its device and rendered.

    Returns {plug ref: (svg root of the seat's view, parent map, configs.json)}.
    Plugs that share a device and configuration are seated in one render."""
    tmp = tmp_path_factory.mktemp("coaxplugs")
    jobs = {}
    for ref, (device, config, view, bays, host) in SEATS.items():
        jobs.setdefault((device, config), []).append((ref, view, bays, host))
    out = {}
    for (device, config), seats in jobs.items():
        name = device.split("/")[1]
        dev = tmp / name / "device.yaml"
        shutil.copytree(LIB / "devices" / device, dev.parent)
        d = yaml.safe_load(dev.read_text())
        cfg = d["configurations"][config]
        for _ref, _view, bays, _host in seats:
            cfg["bays"] = {**(cfg.get("bays") or {}), **bays}
        for ref, view, _bays, host in seats:
            if ref in SWAPS:
                hits = [p for p in d["views"][view]["components"]["placements"]
                        if p.get("id") == host]
                assert len(hits) == 1, (device, view, host)
                hits[0]["ref"] = SWAPS[ref]
        cfg["occupants"] = {host.replace("/module/", "/"): ref
                            for ref, _view, _bays, host in seats}
        dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
        o = tmp / name / "o"
        r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"),
                            str(dev), "--library", str(LIB), "--out", str(o)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        configs = json.loads((o / f"{name}.configs.json").read_text())
        for ref, view, _bays, _host in seats:
            root = ET.parse(face_file(o, name, config, view)).getroot()
            out[ref] = (root, {c: p for p in root.iter() for c in p}, configs)
    assert set(out) == set(SEATS)
    return out


@EACH
def test_it_renders_seated_on_its_jack(seated, ref):
    root, parents, _ = seated[ref]
    host_path = SEATS[ref][4]
    host = by_path(root, host_path)
    occ = by_path(root, f"{host_path}-occupant")
    assert occ.get("data-ref", "").startswith(ref)
    jack = BEZELS.get(ref, PLUGS[ref][2])
    assert host.get("data-ref", "").startswith(jack)
    if ref in BEZELS:
        assert [p["ref"] for p in doc(jack)["parts"]] == [PLUGS[ref][2]]
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6
    stub = [e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--stub"]
    # a float compare: a seat at a nonzero lift writes its features through
    # the inset path, which spells 30 as "30.0"
    assert len(stub) == 1 and float(stub[0].get("data-z-cyl")) == 30


# jack -> the plane a mated plug's coupling front sits on, in mm in front of
# the jack's own face (docs/connectors-coax-design.md section 5 item 1: the
# coupling overlaps the jack's barrel by the mated engagement, so the front of
# the coupling is the barrel's front less that engagement).
#   SMA 0: the nut covers the whole 5.0 barrel of std/sma (MIL-STD-348B H + C
#     is about 5.3; the nut stops at the panel).
#   SMB 0: the body covers the whole 5.0 barrel of std/smb (MIL-STD-348B
#     3.33-5.21).
#   MCX 2.0: nothing overlaps; the plug shoulder stops at the jack's front
#     face, which is the front of std/mcx's 2.0 barrel (Radiall D1C004XEe
#     p.4-14 item 1), and the jack's mate sits `on:` that barrel.
#   F 7.8: the 13.0 thread front less SCTE 123 D 4.29-6.10, the midpoint of
#     6.90-8.71; std/f-type states it as `seat-out`.
#   BNC 3.7: the 12.2 collar front less the 8.5 engagement (MIL-STD-348B G +
#     F); std/bnc states it as `seat-out`, and common/bnc-jack forwards it.
#   1.0/2.3 3.85: the 9.4 front less H+S plug A 5.40-5.70, the midpoint of
#     3.70-4.00; std/din-1-0-2-3 states it, and its bezel forwards it.
MATED_PLANE = {
    "generic/sma-plug@1": 0.0,
    "generic/smb-plug@1": 0.0,
    "generic/mcx-plug@1": 2.0,
    "generic/f-type-plug@1": 7.8,
    "generic/bnc-plug@1": 3.7,
    "generic/din-1-0-2-3-plug@1": 3.85,
}
# plug -> the jack node whose compiled front IS the mated plane, where the jack
# draws a face there (a plane of 0 is the jack's own face).
MATED_FACE = {"generic/mcx-plug@1": "barrel"}


def _z_base(parents, el):
    """The summed `data-z-lift` of `el` and every ancestor: where a feature of
    `el` with no lift of its own starts, in the device frame."""
    z = 0.0
    while el is not None:
        z += float(el.get("data-z-lift") or 0)
        el = parents.get(el)
    return z


def _jack_group(host, ref):
    """The group drawing the jack PLUGS names: the host itself, or the core
    the SWAPS bezel composes."""
    core = PLUGS[ref][2]
    if host.get("data-ref", "").startswith(core):
        return host
    hits = [n for n in host.iter() if n is not host
            and n.get("data-ref", "").startswith(core)]
    assert len(hits) == 1, (ref, core, len(hits))
    return hits[0]


@pytest.mark.parametrize("ref", sorted(MATED_PLANE))
def test_the_coupling_front_sits_on_the_jacks_mated_plane(seated, ref):
    root, parents, _ = seated[ref]
    host_path = SEATS[ref][4]
    host = by_path(root, host_path)
    occ = by_path(root, f"{host_path}-occupant")
    coupling = [e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--coupling"]
    assert len(coupling) == 1, ref
    got = _z_base(parents, coupling[0])
    jack = _jack_group(host, ref)
    want = _z_base(parents, jack) + MATED_PLANE[ref]
    assert got == pytest.approx(want, abs=0.05), (ref, got, want)
    face = MATED_FACE.get(ref)
    if face:
        node = [e for e in jack.iter() if e.get("id") == f"{jack.get('id')}--{face}"]
        assert len(node) == 1, (ref, face)
        n = node[0]
        front = (float(n.get("data-z-out")) if n.get("data-z-out") is not None
                 else float(n.get("data-z-cyl") or 0))
        assert _z_base(parents, n) + front == pytest.approx(got, abs=0.05), (ref, face)

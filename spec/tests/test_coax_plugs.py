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
from test_nested_occupants import by_path, cage_mate, device_point, own_mate

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# plug -> (interface it mates, default cable-od, the jack it seats in)
PLUGS = {
    "generic/sma-plug@1": ("sma", 2.49, "std/sma@1"),
    "generic/smb-plug@1": ("smb", 2.49, "std/smb@1"),
    "generic/mcx-plug@1": ("mcx", 2.49, "std/mcx@1"),
}
EACH = pytest.mark.parametrize("ref", sorted(PLUGS))

# plug -> where it is seated: (device, configuration, view, bays merged into the
# configuration, the host's data-path). The occupant key is the host's path
# with `/module` dropped (a card port is keyed `<bay>/<port>`); the occupant is
# drawn at `<host path>-occupant`. SMA and SMB seat in a device placement; MCX
# has no device-level port in the library, so it seats in a card port through
# the card's nested occupant key. Task 5 adds its rows here.
SEATS = {
    "generic/sma-plug@1": ("ufispace/s9500-30xs", "base", "front", {}, "pps-in"),
    "generic/smb-plug@1": ("juniper/mx304", "base", "rear", {}, "clk-1pps-in"),
    "generic/mcx-plug@1": ("casa/c100g", "base", "rear", {"rear-0": "casa/ups-32x4@1"},
                           "rear-0/module/p0"),
}
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
            root = ET.parse(o / f"{name}.{config}.{view}.svg").getroot()
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
    assert host.get("data-ref", "").startswith(PLUGS[ref][2])
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6
    stub = [e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--stub"]
    assert len(stub) == 1 and stub[0].get("data-z-cyl") == "30"

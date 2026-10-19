"""`<device>.configs.json` says which configurations have a bay (#1022).

A bay or placement marked `only-in: [...]` in device.yaml exists in those
configurations only, and render.py's drawing already skips it in the others.
The index publishes the list on the bay's entry (and on a cage's) exactly as
the device states it, and leaves the key out where the device states none, so
the kit can read a bay the configuration does not have as no bay
(kit/rack/slots.js, spec/tests/js/rack-only-in.mjs). Additive: a reader that
does not know the key ignores it.

The CommScope CH3000's double-width `slot-15-16` exists only in
`redundant-power` and `ht3584h-x48`.
"""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/commscope/ch3000/device.yaml"


def _stated(node, out):
    """{id: only-in list} of every mapping in the device that names both."""
    if isinstance(node, dict):
        if "id" in node and node.get("only-in"):
            out[node["id"]] = node["only-in"]
        for v in node.values():
            _stated(v, out)
    elif isinstance(node, list):
        for v in node:
            _stated(v, out)
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("only-in") / "dist"
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(DEVICE),
                        "--library", str(ROOT / "library"), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return json.loads((out / "ch3000.configs.json").read_text())


def _entries(built, kind):
    return [e for view in built[kind].values() for e in view]


def test_a_bay_published_with_the_configurations_that_have_it(built):
    slot = next(b for b in _entries(built, "bays") if b["id"] == "slot-15-16")
    assert slot["only-in"] == ["redundant-power", "ht3584h-x48"]
    assert slot["only-in"] == _stated(yaml.safe_load(DEVICE.read_text()), {})["slot-15-16"]


def test_a_bay_that_states_none_carries_none(built):
    stated = _stated(yaml.safe_load(DEVICE.read_text()), {})
    bays = _entries(built, "bays")
    plain = [b for b in bays if b["id"] not in stated]
    assert plain, "ch3000 has bays that state no only-in"
    assert all("only-in" not in b for b in plain)
    # and every bay that states one carries it unchanged
    assert all(b["only-in"] == stated[b["id"]] for b in bays if b["id"] in stated)


def _placement(node, pid):
    if isinstance(node, dict):
        if node.get("id") == pid and "ref" in node:
            return node
        for v in node.values():
            found = _placement(v, pid)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _placement(v, pid)
            if found:
                return found
    return None


def test_a_cage_carries_only_in_where_its_placement_states_it(tmp_path):
    """No device in the library states `only-in` on a cage today, so one placement
    of a copy of the AS7726-32X is given it."""
    device = ROOT / "library/devices/edgecore/as7726-32x/device.yaml"
    src = yaml.safe_load(device.read_text())
    first = tmp_path / "first"
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(device),
                        "--library", str(ROOT / "library"), "--out", str(first)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    built = json.loads((first / "as7726-32x.configs.json").read_text())
    cages = _entries(built, "cages")
    assert cages, "as7726-32x publishes cages"
    pid = cages[0]["id"]
    placed = _placement(src, pid)
    assert placed is not None and "only-in" not in placed
    placed["only-in"] = [built["default"]]
    dev = tmp_path / "device.yaml"
    dev.write_text(yaml.safe_dump(src, sort_keys=False))
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(ROOT / "library"), "--out", str(tmp_path / "dist")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    again = json.loads((tmp_path / "dist" / "as7726-32x.configs.json").read_text())
    for cage in _entries(again, "cages"):
        if cage["id"] == pid:
            assert cage["only-in"] == [built["default"]]
        else:
            assert "only-in" not in cage


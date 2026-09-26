"""Coax jacks are connector slots (#650, docs/connectors-coax-design.md).

A presented interface becomes a SLOT only when spec/schemas/connectors.yaml
lists it. These run against the real library and a components.json / device
build made here, never a possibly stale dist.

KNOWN mixes two kinds of real placement. `std/sma@1` and `std/smb@1` are each
placed directly on a device face (ufispace/s9500-30xs `pps-in`, juniper/mx304
`clk-1pps-in`), so those two go through render.py like the RJ45 device tests.
`std/f-type@1` and `std/mcx@1` are NOT placed directly on any device today -
every use found by
`grep -rn "ref: std/f-type@1\\|ref: std/mcx@1" library/devices/*/*/device.yaml`
is empty, and the real placements are inside bay-seated line cards
(casa/rfd@1, casa/ups-32x4@1), whose ports never reach a device's top-level
`cages` (a seated card's own ports are not expanded into its host's cages,
same as a bay's `bays` dict names only the seated ref). Those two go through
the indexer's components.json instead, same as the RJ45 census's `_card_slot`.
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
INDEXER = ROOT / "spec/tools/portrayal/components_index.py"

EXISTING = {"f-type": "std/f-type", "sma": "std/sma", "smb": "std/smb", "mcx": "std/mcx"}


def test_each_existing_coax_interface_is_a_connector_with_a_standard():
    reg = render_mod._connector_registry()
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]
    for iface in EXISTING:
        assert iface in reg, iface
        assert reg[iface]["standard"] in std, (iface, reg[iface])


def test_each_existing_jack_presents_its_interface():
    for iface, part in EXISTING.items():
        doc = yaml.safe_load((LIB / f"components/{part}/v1/contract.yaml").read_text())
        assert doc["interface"] == iface
        assert "mate" in doc["connection-points"]


@pytest.fixture(scope="module")
def comps(tmp_path_factory):
    out = tmp_path_factory.mktemp("components")
    r = warmrender.run([sys.executable, str(INDEXER), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads((out / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


def _device_configs(device, tmp_path):
    src = LIB / f"devices/{device}/device.yaml"
    r = warmrender.run([sys.executable, str(RENDER), str(src), "--library", str(LIB),
                        "--out", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    name = src.parent.name
    return json.loads((tmp_path / f"{name}.configs.json").read_text())


def _device_slot(device, view, cage_id, tmp_path):
    cfg = _device_configs(device, tmp_path)
    return next(c for c in cfg["cages"][view] if c["id"] == cage_id)


def _card_slot(comps, ref, cage_id):
    return next(c for c in comps[ref]["cages"] if c["id"] == cage_id)


# One real placement per existing family. sma/smb are direct device
# placements (view, placement id); f-type/mcx are card ports (component ref,
# port id) - see the module docstring for why.
KNOWN_DEVICE = {
    "sma": ("ufispace/s9500-30xs", "front", "pps-in"),
    "smb": ("juniper/mx304", "rear", "clk-1pps-in"),
}
KNOWN_CARD = {
    "f-type": ("casa/rfd@1", "p0"),
    "mcx": ("casa/ups-32x4@1", "p0"),
}


@pytest.mark.parametrize("iface", sorted(EXISTING))
def test_a_known_coax_port_publishes_a_connector_slot(iface, comps, tmp_path):
    if iface in KNOWN_DEVICE:
        device, view, pid = KNOWN_DEVICE[iface]
        slot = _device_slot(device, view, pid, tmp_path)
    else:
        ref, cage_id = KNOWN_CARD[iface]
        slot = _card_slot(comps, ref, cage_id)
    assert slot["kind"] == "connector"
    assert slot["interface"] == iface

"""A slot at any depth: a bore on an adapter in a cassette in a bay (B3, deep
addressing - docs/pluggables-caps-design.md).

A configuration's `occupants:` keys a slot by the path of PART IDS from the
device's placement or bay down to the slot, with the `module` step of every
seated bay dropped (manifest.slot_key_prefix): `bay-1/lc01/tx` is the TX bore
of adapter `lc01` in the cassette seated in `bay-1`. The occupant is drawn
inside the innermost instance group holding the slot, at
`bay-1/module/lc01/tx-occupant`, so it inherits every transform above it and
nothing is solved twice.

Every test seats on a COPY in tmp_path. Positions are held numerically, by
composing every ancestor transform (the helpers in test_nested_occupants.py):
the plug's own `mate` must land on the bore's `mate` to 1e-6.
"""
import shutil

import pytest
import yaml

from test_nested_occupants import (LIB, _contract, assert_same_turn, by_path,
                                   device_point, is_inside, own_mate, render, run)
from test_slot_defaults import SHIPPED_CAPS

from portrayal import lint
from portrayal import manifest
from portrayal.manifest import occupant_spec, presented_interface

CASSETTE = "fs/fhd-1mtp24-lc-os2-a@3"
PLUG = "generic/lc-plug@2"


def copy_with(tmp_path, src, config, occupants, bays=None, make_config=False):
    dev = shutil.copytree(LIB / "devices" / src, tmp_path / src.split("/")[-1]) / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    if make_config:
        assert not d.get("configurations"), "the device already has configurations"
        d["configurations"] = {config: {"kind": "base", "default": True}}
    cfg = d["configurations"][config]
    if bays:
        cfg["bays"] = {**(cfg.get("bays") or {}), **bays}
    cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def fhd(tmp_path, occupants):
    return copy_with(tmp_path, "fs/fhd-1ufce", "base", occupants, {"bay-1": CASSETTE})


def a22(tmp_path, occupants):
    return copy_with(tmp_path, "smartoptics/dcp-2", "ila-node", occupants)


def direct(tmp_path, occupants):
    return copy_with(tmp_path, "smartoptics/dcp-r-34d-cs", "default", occupants,
                     make_config=True)


def part(contract_ref, part_id):
    return next(q for q in _contract(contract_ref)["parts"] if q["id"] == part_id)


def assert_seated_on_bore(root, parents, holder_path, bore_id, adapter_ref, key):
    """The plug is drawn inside the group holding its bore, lands its own mate
    on the bore's to 1e-6, turns with it, and stands at the bore's lift."""
    holder = by_path(root, holder_path)
    bore = by_path(root, f"{holder_path}/{bore_id}")
    occ = by_path(root, f"{holder_path}/{bore_id}-occupant")
    assert is_inside(parents, occ, holder), "the plug is not inside the adapter's group"
    assert occ.get("data-for") == f"{holder_path}/{bore_id}"
    assert occ.get("data-ref").split(":")[0] == PLUG
    bore_ref = bore.get("data-ref").rsplit(":", 1)[0]
    _, bm, blift = presented_interface(_contract(bore_ref), _contract)
    hx, hy = device_point(parents, bore, bm)
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, (key, (hx, hy), (ox, oy))
    assert_same_turn(parents, occ, bore)
    # the bore's composed lift on its adapter, read from the contract
    want = float(part(adapter_ref, bore_id).get("lift") or 0) + float(blift or 0)
    assert want > 0, "a zero lift would pass by 0 == 0"
    assert float(occ.get("data-z-lift")) == pytest.approx(want)


def occupant_paths(root):
    """Every occupant a configuration seated - bar the caps the real adapters
    ship (B3 task 8, test_shipped_caps.py), which every unkeyed port draws."""
    return sorted(n.get("data-path") for n in root.iter()
                  if (n.get("data-path") or "").endswith("-occupant")
                  and (n.get("data-ref") or "").rsplit(":", 1)[0] not in SHIPPED_CAPS)


# --- the key ------------------------------------------------------------------

@pytest.mark.parametrize("path, key", [
    ("bay-1/module/lc01", "bay-1/lc01"),
    ("front-6/module", "front-6"),
    ("riser-1/module/slot-1/module", "riser-1/slot-1"),
    ("port-3", "port-3"),
    ("port-3/tx", "port-3/tx"),
    (None, None),
    ("", None),
])
def test_the_slot_key_drops_every_module_step(path, key):
    assert manifest.slot_key_prefix(path) == key


def test_an_empty_string_empties():
    assert occupant_spec("bay-1/lc01/tx", "") is None
    assert occupant_spec("bay-1/lc01/tx", PLUG) == {"ref": PLUG}


# --- depth three: bay, cassette, adapter, bore ----------------------------------

def test_a_plug_seats_on_a_bore_in_a_cassette_in_a_bay(tmp_path):
    adapter = part(CASSETTE, "lc01")
    assert adapter["at"] == [17.24, 18.66]
    # the adapter ships a duplex cap on its own slot, emptied first (L115)
    root, parents = render(fhd(tmp_path, {"bay-1/lc01": "", "bay-1/lc01/tx": PLUG}),
                           tmp_path / "o", "fhd-1ufce", "base")
    assert_seated_on_bore(root, parents, "bay-1/module/lc01", "tx", adapter["ref"],
                          "bay-1/lc01/tx")
    assert occupant_paths(root) == ["bay-1/module/lc01/tx-occupant"]


def test_the_same_at_depth_four_on_a_raised_carrier(tmp_path):
    """dcp-f-a22's adapters are composed at lift 44 on the raised block, in a
    card seated in the DCP-2's slot: bay, card, adapter, bore."""
    edfa = part("smartoptics/dcp-f-a22@1", "edfa")
    assert edfa["lift"] == 44.0
    root, parents = render(a22(tmp_path, {"slot-1/edfa/tx": PLUG}), tmp_path / "o",
                           "dcp-2", "ila-node")
    assert_seated_on_bore(root, parents, "slot-1/module/edfa", "tx", edfa["ref"],
                          "slot-1/edfa/tx")
    assert occupant_paths(root) == ["slot-1/module/edfa/tx-occupant"]


def test_a_plug_seats_on_a_directly_placed_adapter(tmp_path):
    """Three Smartoptics devices place an adapter as a device placement, so
    `<placement>/tx` is a live key: seated inside that placement's group."""
    root, parents = render(direct(tmp_path, {"port-1510/tx": PLUG}), tmp_path / "o",
                           "dcp-r-34d-cs", "default")
    assert_seated_on_bore(root, parents, "port-1510", "tx", "common/lc-duplex-adapter@5",
                          "port-1510/tx")
    assert occupant_paths(root) == ["port-1510/tx-occupant"]


def test_an_empty_string_seats_nothing(tmp_path):
    root, _ = render(fhd(tmp_path, {"bay-1/lc01/tx": ""}), tmp_path / "o",
                     "fhd-1ufce", "base")
    by_path(root, "bay-1/module/lc01/tx")       # the bore is drawn, and
    assert occupant_paths(root) == []           # nothing is seated on it


@pytest.mark.parametrize("make, key, why", [
    (fhd, "bay-1/lc01/tx/nope", "bay-1/lc01/tx/nope"),     # deeper than anything
    (fhd, "bay-1/lc99/tx", "'lc99'"),                       # no such adapter
    (a22, "slot-1/edfa/tx/nope", "slot-1/edfa/tx/nope"),
    (a22, "slot-1/nope/tx", "'nope'"),
    (direct, "port-1510/nope", "port-1510/nope"),           # no such bore
])
def test_a_key_reaching_nothing_is_an_error(tmp_path, make, key, why):
    r = run(make(tmp_path, {key: PLUG}), tmp_path / "o")
    assert r.returncode != 0
    assert f"occupants/{key}" in r.stderr and why in r.stderr, r.stderr[-800:]


# --- L12, through the same resolver --------------------------------------------

def l12(dev):
    data = yaml.safe_load(dev.read_text())
    with lint.collecting() as got:
        lint.lint_device_occupants(dev, data, [str(LIB)])
    return [e for e in got.errors if "[L12]" in e]


@pytest.mark.parametrize("make, occ", [
    (fhd, {"bay-1/lc01/tx": PLUG, "bay-1/lc01/tx-occupant": "common/lc-boot@1"}),
    (fhd, {"bay-1/lc01/tx": ""}),
    (a22, {"slot-1/edfa/tx": PLUG}),
    (direct, {"port-1510/tx": PLUG}),
])
def test_lint_the_same_keys_lint_clean(tmp_path, make, occ):
    assert l12(make(tmp_path, occ)) == []


@pytest.mark.parametrize("make, occ, why", [
    (fhd, {"bay-1/lc01/tx": "common/lc-boot@1"}, "mates 'lc-plug' but std/lc-bulkhead-bore@1 presents 'lc'"),
    (direct, {"port-1510/tx": "common/lc-boot@1"}, "mates 'lc-plug' but std/lc-bulkhead-bore@1 presents 'lc'"),
    (fhd, {"bay-1/lc01/tx/nope": PLUG}, "occupants/bay-1/lc01/tx/nope"),
    (fhd, {"bay-1/lc99/tx": PLUG}, "'lc99'"),
    (a22, {"slot-1/nope/tx": PLUG}, "'nope'"),
])
def test_lint_a_bad_deep_key_is_an_l12_error(tmp_path, make, occ, why):
    got = l12(make(tmp_path, occ))
    assert got and any(why in e for e in got), got

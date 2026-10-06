"""The connector slot (B3, docs/pluggables-caps-design.md): one core, two registries.

A part presenting a pluggables family is a CAGE; a part presenting a connector
interface named in spec/schemas/connectors.yaml is a SLOT. Both are answered by
`render.slot_entry` and published in the same `cages` list, told apart by `kind`.

These run against the real library and a components.json built here by the
indexer the build runs, never a fixture and never a possibly stale dist.
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

import onebuild
import warmrender
from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
INDEXER = ROOT / "spec/tools/portrayal/components_index.py"


def _ref(entry):
    return f"{entry['ns']}/{entry['name']}@{entry['major'][1:]}"


@pytest.fixture(scope="module")
def comps(tmp_path_factory):
    """components.json keyed by ref - the file itself is `{components: [...]}`."""
    # the indexer the build runs, over this tree, once per session (onebuild)
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {_ref(e): e for e in doc["components"]}
    assert len(got) > 0, "the indexer published no component at all"
    return got


def _entries(comps):
    return [c for comp in comps.values() for c in comp.get("cages") or []]


def test_the_connector_registry_is_not_vacuous():
    reg = render_mod._connector_registry()
    # mpo16: the MTP-16 opening, keyed apart from mpo (std/mpo16@1)
    # rj45: the copper jack, so generic/rj45-plug@1 has somewhere to go (#610)
    # f-type/sma/smb/mcx: the existing coax jacks, made slots (#650)
    # bnc/din-1-0-2-3: the two new coax jacks, std/bnc@1 and std/din-1-0-2-3@1 (#650)
    # iec-c14/iec-c20/saf-d-grid: the AC inlets, made slots for their cord ends (#785)
    # usb-a/micro-usb-b/usb-c: the USB receptacles, made slots for their cable plugs (#786)
    # db9/hd15/da15/db25: the D-sub and VGA connectors, made slots for their hooded plugs (#787)
    # terminal-508-2/-5f/-6: the pluggable 5.08 mm terminal headers, made slots for their
    # screw-clamp plugs (#789)
    assert set(reg) == {"lc", "lc-duplex", "sc", "mpo", "mpo16", "rj45",
                         "f-type", "sma", "smb", "mcx", "bnc", "din-1-0-2-3",
                         "iec-c14", "iec-c20", "saf-d-grid",
                         "usb-a", "micro-usb-b", "usb-c",
                         "db9", "hd15", "da15", "db25",
                         "terminal-508-2", "terminal-508-5f", "terminal-508-6"}
    # No connector interface is also a cage family's: one core, two registries,
    # and an interface must not be answered by both.
    fam_ifaces = {f.get("interface") for f in render_mod._pluggable_families().values()}
    assert len(fam_ifaces) > 0 and not (fam_ifaces & set(reg))


def test_every_connector_presenting_part_is_a_connector_slot(comps):
    entries = [c for c in _entries(comps) if c.get("kind") == "connector"]
    assert len(entries) > 0, "measured no connector slot at all"
    assert all(c["interface"] in {"lc", "lc-duplex", "sc", "mpo", "mpo16", "rj45",
                                   "f-type", "sma", "smb", "mcx", "bnc", "din-1-0-2-3",
                                   "iec-c14", "iec-c20", "saf-d-grid",
                                   "usb-a", "micro-usb-b", "usb-c",
                                   "db9", "hd15", "da15", "db25",
                                   "terminal-508-2", "terminal-508-5f", "terminal-508-6"}
               for c in entries)
    # a slot has no rate ladder, so no media ceiling
    assert all(c["media"] is None for c in entries)


def test_an_lc_slot_accepts_the_plug_and_no_boot(comps):
    lc = next(c for c in _entries(comps) if c.get("interface") == "lc")
    assert "generic/lc-plug@2" in lc["accepts"]
    assert not any("boot" in r for r in lc["accepts"])


def test_every_cage_entry_says_its_kind(comps):
    entries = _entries(comps)
    assert len(entries) > 0
    kinds = {c.get("kind") for c in entries}
    assert kinds <= {"cage", "connector"} and "cage" in kinds


def test_std_mpo_presents_mpo_at_its_centre():
    from portrayal.manifest import presented_interface
    c = yaml.safe_load((LIB / "components/std/mpo/v2/contract.yaml").read_text())
    iface, at, lift = presented_interface(c, lambda r: None)
    assert (iface, at, lift) == ("mpo", [6.45, 4.0], 0.0)


def test_a_wrappers_aperture_is_not_a_second_slot(comps):
    # P2: mpo-adapter forwards its bore; the bore is not published separately
    key = next(k for k in comps if k.startswith("common/mpo-adapter"))
    assert not any(c["id"] == "bore" for c in comps[key].get("cages") or [])


def test_the_wrapper_is_the_slot_where_it_is_composed(comps):
    """The other half of P2: the forwarded aperture is not lost, it is
    published once - as the wrapper's own placement, in its composer's frame.

    ON A COMPOSER BUILT HERE, because the library has no composer of the
    wrapper: the FHD cassette rears that composed common/mpo-adapter@1 moved
    to the flanged bulkhead on main (#497, #499), which presents `mpo` itself
    (common/mpo-flange-adapter@2) rather than forwarding a std/mpo, and
    mpo-adapter (@2 since the aperture was corrected) is `unplaced`. So the
    forwarding is exercised on the real wrapper contract, and every mpo slot
    the library does publish - one per bulkhead on each cassette back - is
    held to the same shape."""
    lib = render_mod.Library([str(LIB)])
    composer = {"size": {"w": 80.0, "h": 30.0},
                "parts": [{"id": "mtp1", "ref": "common/mpo-adapter@2",
                           "at": [20.0, 12.0]}]}
    [slot] = render_mod.component_cages(composer, lib,
                                        render_mod._pluggable_families(),
                                        render_mod._pluggable_candidates([str(LIB)]),
                                        render_mod._connector_registry())
    assert (slot["id"], slot["kind"], slot["interface"]) == ("mtp1", "connector", "mpo")
    assert slot["mate"] is not None and slot["bores"] == []
    mpo = [(ref, c) for ref, comp in comps.items() for c in comp.get("cages") or []
           if c.get("interface") == "mpo"]
    assert all(c["kind"] == "connector" and c["mate"] is not None for _r, c in mpo)


def test_a_part_presenting_its_own_interface_keeps_its_composed_slots():
    """P2 is about FORWARDING only. A contract that declares its own
    interface and point forwards nothing (manifest.presented_interface), so a
    composed aperture of it is still its own slot - the shape a duplex LC
    adapter presenting `lc-duplex` over its two `lc` bores takes."""
    lib = render_mod.Library([str(LIB)])
    families = render_mod._pluggable_families()
    connectors = render_mod._connector_registry()
    candidates = render_mod._pluggable_candidates([str(LIB)])
    bore = {"ref": "std/mpo@2", "id": "bore", "at": [0.45, 0.7]}
    forwarding = {"size": {"w": 13.8, "h": 9.4}, "parts": [bore]}
    own = {"size": {"w": 13.8, "h": 9.4}, "interface": "mpo",
           "connection-points": {"mate": {"at": [6.9, 4.7]}}, "parts": [bore]}
    assert render_mod.component_cages(forwarding, lib, families, candidates,
                                      connectors) == []
    [slot] = render_mod.component_cages(own, lib, families, candidates, connectors)
    assert (slot["id"], slot["kind"], slot["interface"]) == ("bore", "connector", "mpo")

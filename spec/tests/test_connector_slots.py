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
    # iec-c13: the C13 outlet of a rack PDU, std/c13-outlet@1 (the Eaton EVMI2130X);
    # generic/c14-plug@1 is the cord end that mates it
    # iec-c19: the C19 outlet of a PDU, a slot for a C20 jumper end (#933)
    # usb-a/micro-usb-b/usb-c: the USB receptacles, made slots for their cable plugs (#786)
    # mini-usb-b: the Mini-B receptacle, registered from Molex 54819-0519;
    # std/mini-usb@1 presents it (the Catalyst 9300 and 3650 console) and no cable
    # plug mates it yet
    # db9/hd15/da15/db25: the D-sub and VGA connectors, made slots for their hooded plugs (#787)
    # terminal-508-2/-5/-6: the pluggable 5.08 mm terminal headers, made slots for their
    # screw-clamp plugs (#789)
    # dc-barrel: the DC barrel jack, one nominal connector by ruling (#789)
    # terminal-stud: a screw or stud terminal a lug lands on, one nominal connector by
    # ruling (#789)
    # mrj21/vhdci/rj11: the high-density Ethernet, the timing fan-out and the telephone
    # jacks, made slots for their cable plugs (#790)
    # breaker-1ru-guard: NOT A CONNECTOR. The face of a 1RU plug-in breaker, where its
    # touch guard screws on. It is here because a cover that ships on a part and comes
    # off is the slot mechanism with nothing to plug in: one host, one occupant, a
    # default. The registry marks it `cover: true` (#807)
    # p40: the two-pole output connector of the Amphenol NS connectorized power panels,
    # made a slot for its plug, amphenol-ns/p40-plug@1; a vendor connector citing no
    # standard (docs/connectors-dc-terminal-design.md section 14)
    # stud-pair-5-8/-3-4/-1: a pair of studs one two-hole lug lands across, each
    # spanning two terminal-stud seats, the pitch in the key (#828)
    # pdu-button: NOT A CONNECTOR - the rack PDU mounting interface (#934). A keyhole
    # in a bracket or a channel presents it and eaton/g4-mounting-button@1 mates it;
    # nothing presents it yet, so it is in the registry and in no slot below
    # nema-5-15r/nema-5-20r/eaton-c39: the NEMA straight-blade receptacles and the
    # Eaton combination outlet, made slots for a cord end (#1045). std/nema-5-20r@1
    # and eaton/c39-outlet@1 present two of them. No part presents nema-5-15r yet:
    # it is registered because a 5-15P names it in `mates`, and it is in no slot below
    # flexstack/stackwise-480/stackpower: the Cisco stacking and power-stacking
    # connectors; ex4200-vcp: the Juniper EX4200 Virtual Chassis port;
    # cisco-rps2300/ex3300-rps: the two redundant-power connectors. Vendor connectors
    # citing no standard; no part presents any of them yet, so the later change that
    # gives a part its interface and its mate never edits this list
    assert set(reg) == {"lc", "lc-duplex", "sc", "mpo", "mpo16", "rj45",
                         "f-type", "sma", "smb", "mcx", "bnc", "din-1-0-2-3",
                         "iec-c13", "iec-c14", "iec-c20", "iec-c19", "saf-d-grid",
                         "nema-5-15r", "nema-5-20r", "eaton-c39",
                         "usb-a", "micro-usb-b", "mini-usb-b", "usb-c",
                         "db9", "hd15", "da15", "db25",
                         "terminal-508-2", "terminal-508-5", "terminal-508-6",
                         "dc-barrel", "terminal-stud",
                         "stud-pair-5-8", "stud-pair-3-4", "stud-pair-1",
                         "mrj21", "vhdci", "rj11",
                         "breaker-1ru-guard", "p40", "pdu-button",
                         # GPU power and NVLink (P-0028): presented by parts no
                         # device places yet, so none is a slot below
                         "eps12v-8pin", "pcie-8pin", "pcie-12vhpwr", "pcie-12v-2x6",
                         "nvlink-a100-pcie",
                         # the two PCIe slot forms (docs/cards-by-interface-design.md):
                         # a riser bay states one as its `interface`, so no part
                         # presents either and neither is a slot below
                         "pcie-fh", "pcie-lp",
                         # stack, virtual-chassis and redundant-power connectors:
                         # presented by no part yet
                         "flexstack", "stackwise-480", "stackpower", "ex4200-vcp",
                         "cisco-rps2300", "ex3300-rps"}
    # No connector interface is also a cage family's: one core, two registries,
    # and an interface must not be answered by both.
    fam_ifaces = {f.get("interface") for f in render_mod._pluggable_families().values()}
    assert len(fam_ifaces) > 0 and not (fam_ifaces & set(reg))


def test_every_connector_presenting_part_is_a_connector_slot(comps):
    entries = [c for c in _entries(comps) if c.get("kind") == "connector"]
    assert len(entries) > 0, "measured no connector slot at all"
    assert all(c["interface"] in {"lc", "lc-duplex", "sc", "mpo", "mpo16", "rj45",
                                   "f-type", "sma", "smb", "mcx", "bnc", "din-1-0-2-3",
                                   "iec-c13", "iec-c14", "iec-c20", "iec-c19", "saf-d-grid",
                                   "usb-a", "micro-usb-b", "usb-c",
                                   "db9", "hd15", "da15", "db25",
                                   "terminal-508-2", "terminal-508-5", "terminal-508-6",
                                   "dc-barrel", "terminal-stud",
                                   "stud-pair-5-8", "stud-pair-3-4", "stud-pair-1",
                                   "mrj21", "vhdci", "rj11",
                                   # a cover mount, not a connector - see the registry test above
                                   "breaker-1ru-guard",
                                   # the A100's faces compose these (P-0072)
                                   "eps12v-8pin", "nvlink-a100-pcie",
                                   # the H100 PCIe's, H100 NVL's and L40S's east ends
                                   "pcie-12vhpwr", "pcie-12v-2x6",
                                   # the A10's east end
                                   "pcie-8pin",
                                   # the Mini-B console of the Catalyst 9300 and 3650,
                                   # so a part composing std/mini-usb@1 never edits this
                                   "mini-usb-b",
                                   # registered ahead of the parts that present them,
                                   # so those changes never edit this list
                                   "flexstack", "stackwise-480", "stackpower",
                                   "ex4200-vcp", "cisco-rps2300", "ex3300-rps"}
               for c in entries)
    # a slot has no rate ladder, so no media ceiling
    assert all(c["media"] is None for c in entries)


STACK_AND_RPS_KEYS = ("flexstack", "stackwise-480", "stackpower", "ex4200-vcp",
                      "cisco-rps2300", "ex3300-rps")


@pytest.mark.parametrize("key", STACK_AND_RPS_KEYS)
def test_a_stack_or_rps_connector_key_has_a_note_and_no_standard(key):
    entry = render_mod._connector_registry().get(key)
    assert entry is not None, f"{key} is not registered"
    assert str(entry.get("note") or "").strip(), f"{key} has no note"
    assert "standard" not in entry, f"{key} cites a standard; these are vendor connectors"


def _header(name):
    text = (ROOT / "spec/schemas" / name).read_text()
    return text.split("\nformat: 1", 1)[0]


def test_the_connectors_header_documents_unmated_and_turns():
    head = _header("connectors.yaml")
    keys = head.split("AN ENTRY is", 1)[1]
    for word in ("unmated", "turns", "40 characters", "C21"):
        assert word in keys, f"the entry-key list does not mention {word}"


def test_the_pluggables_header_documents_unmated_as_a_map_from_a_rate():
    head = _header("pluggables.yaml")
    assert "unmated" in head
    tail = head.split("unmated", 1)[1]
    for word in ("map", "rate", "sentence", "40 characters", "C21"):
        assert word in tail, f"the unmated paragraph does not mention {word}"


def test_the_mini_usb_b_note_says_what_presents_it():
    note = render_mod._connector_registry()["mini-usb-b"]["note"]
    assert "No part presents it" not in note
    assert "std/mini-usb@1" in note
    assert "no cable plug mates it yet" in note


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

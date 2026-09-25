"""What the CH3000's back plates export, and what they drop on purpose.

A CH3000 back plate is single-faced: its optical ports face the rear with no
trunk behind them, the case NOT_A_DCIM_PORT records for common/lc-duplex-adapter
and std/sc-bore. The register is keyed by part REF and is only asked about refs
that export nowhere in the library - and common/lc-duplex-v-adapter exports on
the FS cassettes, which have a rear face. So nothing else notices when one of
these plates drops its optics, and nothing would notice if one started exporting
them. This pins both halves: the RF jacks export, the optics are dropped, and the
drop is the builder's (it reaches `dropped`), not a missing part.

The BP3400C is the other way round: its SFP cages ARE its optical inputs and do
export, one interface per cage, each cage carrying two of a receiver's inputs.
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export

LIB = Path(__file__).resolve().parents[2] / "library" / "components"

F_OUTPUTS = {f"rf-out-{n}" for n in range(1, 5)}
PLATES = {
    # plate: (interfaces that export, optical part refs that are dropped, how many)
    "bp-a10": (F_OUTPUTS, {"common/lc-duplex-v-adapter": 2}),
    "bp-a5": ({"rf-out"}, {"std/sc-bore": 1}),
    "bp-f2": (set(), {"std/sc-bore": 2}),
    "bp-f4": (set(), {"std/sc-bore": 4}),
    "bp-f2-al": (set(), {"common/lc-duplex-v-adapter": 1}),
}


def _export(name):
    c = yaml.safe_load((LIB / "commscope" / name / "v1" / "contract.yaml").read_text())
    dropped = Counter()
    doc = dcim_export.build_module({**c, "ns": "commscope"}, "CommScope", dropped=dropped)
    return doc, dropped


@pytest.mark.parametrize("name", sorted(PLATES))
def test_a_single_faced_plate_exports_its_rf_and_drops_its_optics(name):
    exports, drops = PLATES[name]
    doc, dropped = _export(name)
    assert {i["name"] for i in doc.get("interfaces") or []} == exports
    for ref, n in drops.items():
        assert ref in dcim_export.NOT_A_DCIM_PORT or ref == "common/lc-duplex-v-adapter", ref
        assert dropped.get(ref, 0) == n, (ref, dict(dropped))


def test_the_bp3400c_exports_every_receiver_input_cage():
    doc, _ = _export("bp3400c")
    names = {i["name"] for i in doc.get("interfaces") or []}
    cages = {f"in-{r}-{p}" for r in "abcd" for p in ("1-2", "3-4")}
    assert cages <= names, sorted(cages - names)
    assert {f"rf-{r}-{n}" for r in "abcd" for n in range(1, 5)} <= names
    assert "data-port" in names
    by = {i["name"]: i for i in doc["interfaces"]}
    for cage in cages:
        assert by[cage]["type"] == "other", by[cage]
        assert by[cage].get("label") == "Digital return", by[cage]


def test_the_cx3002_management_ports_export_as_10_100():
    """The CX3002's IN and OUT ports are 10BASE-T by its data sheet; with no `10m` row
    they fell through to 1000base-t, as a 10/100 jack once did (#511). Neither NetBox nor
    Nautobot defines 10base-t, so they take 100base-tx, labelled 10/100ME upstream."""
    doc, _ = _export("cx3002")
    by = {i["name"]: i for i in doc["interfaces"]}
    assert {n: by[n]["type"] for n in ("eth-in", "eth-out")} == {"eth-in": "100base-tx", "eth-out": "100base-tx"}
    assert all(by[n]["mgmt_only"] for n in ("eth-in", "eth-out"))


def test_the_cx3033n_sfp_exports_as_its_proprietary_network_port():
    """2.125 Gb/s with CommScope's own network-port transceivers is not 1000BASE-X
    (1.25 Gb/s), so the cage declares a proprietary link rather than a 1G rate."""
    doc, _ = _export("cx3033n")
    by = {i["name"]: i for i in doc["interfaces"]}
    assert by["sfp"]["type"] == "other", by["sfp"]
    assert by["sfp"].get("label") == "2.125 Gb/s network port", by["sfp"]


SC, LC = "std/sc-bore", "common/lc-duplex-v-adapter"
HALF_DEPTH_DROPS = {
    # half-depth passives and the optical switch: single-faced optics, all dropped -
    # SC/APC bores, or duplex LC adapters (APC, and the NP34B10S's blue UPC)
    "np35f01": (SC, 3), "np35f04s": (SC, 4), "np35m04": (SC, 7), "np35d04": (SC, 7),
    "np35m08": (SC, 9), "np35d08": (SC, 9), "os32m2b": (SC, 6),
    "np34c01": (SC, 8), "np34f01d": (SC, 6), "op34f1d": (SC, 6),
    "np34m05": (SC, 9), "op34m5x": (SC, 9), "op34d5x": (SC, 9),
    "np34m08": (LC, 6), "op34m8c": (LC, 6), "op34m10c": (LC, 7), "np34b10s": (LC, 6),
    "np33f01": (SC, 3), "op33f1x": (SC, 3), "np34s04": (SC, 8), "op34s4s": (SC, 8),
    "np35c0x": (SC, 6), "op31m2d": (SC, 8), "op35f1": (SC, 3), "op35f1d": (SC, 6),
    "op35f4s": (SC, 4), "op35d4x": (SC, 7), "op35d8cf": (SC, 9),
}


@pytest.mark.parametrize("name", sorted(HALF_DEPTH_DROPS))
def test_a_half_depth_optical_module_exports_nothing_and_drops_its_optics(name):
    ref, n = HALF_DEPTH_DROPS[name]
    doc, dropped = _export(name)
    assert not doc.get("interfaces"), doc.get("interfaces")
    assert dropped.get(ref, 0) == n, dict(dropped)
    assert ref in dcim_export.NOT_A_DCIM_PORT or ref == LC


@pytest.mark.parametrize("name", ["ab32s1g", "ab32s1t"])
def test_the_ab_switch_exports_its_three_rf_ports(name):
    doc, _ = _export(name)
    by = {i["name"]: i["type"] for i in doc["interfaces"]}
    assert by == {"rf-in-a": "docsis", "rf-in-b": "docsis", "rf-out": "docsis"}

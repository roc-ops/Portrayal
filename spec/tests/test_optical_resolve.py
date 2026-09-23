"""The optical graph, resolved from a contract.

A connector states how many fibre positions it presents, ONCE, and every module
that composes it inherits that. The alternative - restating capacity per module -
is 77 chances to type 12 as 21 on the FS line alone.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def contract(ref):
    """`common/lc-duplex-adapter@5` -> its parsed contract."""
    name, major = ref.split("@")
    return yaml.safe_load(
        (LIB / "components" / name / f"v{major}" / "contract.yaml").read_text())


def test_the_lc_duplex_adapter_presents_two_fibre_positions():
    c = contract("common/lc-duplex-adapter@5")
    assert (c.get("optical") or {}).get("positions") == 2, (
        "an LC DUPLEX adapter is two bores. If this is absent, every module "
        "composing it has no capacity to check its paths against")


from portrayal import optical


def test_an_endpoint_splits_into_a_part_id_and_a_position():
    assert optical.split_endpoint("mtp-1.3") == (None, "mtp-1", 3)
    assert optical.split_endpoint("common.12") == (None, "common", 12)


def test_the_adapters_parts_are_positions_1_then_2_in_that_order():
    """The order is a comment today, and four DCM contracts depend on it.

    `common/lc-duplex-adapter@5`'s own `optical` block says position order is
    the order its bores are composed below - bore `1` first, bore `2` second -
    stated in a comment nothing enforces. Every ppm-dcm-* contract declares its
    pass-through as `dcm.2 -> dcm.1`, which is only Rx-into-Tx if bore `1` (the
    faceplate's Tx) really is position 1 and bore `2` (its Rx) really is
    position 2. Swap the two entries under `parts:` and every one of those four
    DCMs silently inverts - `optical.positions: 2` still holds, L78/L79/L80
    still pass, and the suite stays green while the signal direction on every
    DCM in the library is now backwards.
    """
    c = contract("common/lc-duplex-adapter@5")
    ids = [p["id"] for p in c["parts"]]
    assert ids == ["1", "2"], (
        "lc-duplex-adapter's parts order encodes position 1 = bore `1`, "
        "position 2 = bore `2`; the DCM contracts' dcm.2 -> dcm.1 pass-through "
        "depends on it")


def test_capacities_come_from_the_composed_parts_contracts():
    """The module names parts; the PARTS know how many fibres they hold."""
    c = {"parts": [{"ref": "common/lc-duplex-adapter@5", "id": "common"},
                   {"ref": "common/lc-duplex-adapter@5", "id": "split"},
                   {"ref": "common/led-dot@1", "id": "lamp"}]}
    loaded = {"common/lc-duplex-adapter@5": {"optical": {"positions": 2}},
              "common/led-dot@1": {}}
    assert optical.capacities(c, loaded.get) == {"common": 2, "split": 2}, (
        "a part with no optical block is not a connector and must not appear")


def test_a_two_ended_path_yields_its_two_endpoints():
    p = {"from": "dcm.2", "to": "dcm.1"}
    assert optical.endpoints(p) == [("dcm.2", None), ("dcm.1", None)]


def test_a_split_path_yields_every_destination_with_its_ratio():
    p = {"from": "common.1",
         "to": [{"at": "split.1", "ratio": 97}, {"at": "split.2", "ratio": 3}]}
    assert optical.endpoints(p) == [
        ("common.1", None), ("split.1", 97), ("split.2", 3)]


def test_reached_is_every_endpoint_any_path_touches():
    c = {"optical": {"paths": [
        {"from": "common.1", "to": [{"at": "split.1", "ratio": 50},
                                    {"at": "split.2", "ratio": 50}]}]}}
    assert optical.reached(c) == {"common.1", "split.1", "split.2"}


def test_the_97_3_coupler_splits_its_common_port_in_that_ratio():
    """The part's function, which was the string `coupling-ratio: '97/3'`."""
    c = contract("smartoptics/ppm-ocu-97-3@2")
    paths = (c.get("optical") or {}).get("paths") or []
    assert len(paths) == 1, paths
    dests = {d["at"]: d["ratio"] for d in paths[0]["to"]}
    assert paths[0]["from"] == "common.1"
    assert dests == {"split.1": 97, "split.2": 3}


def test_the_couplers_dead_bore_is_a_declared_claim_not_a_sentence():
    c = contract("smartoptics/ppm-ocu-97-3@2")
    unused = (c.get("optical") or {}).get("unused") or {}
    assert "common.2" in unused and len(unused["common.2"]) >= 20


def test_the_50_50_coupler_splits_evenly():
    c = contract("smartoptics/ppm-ocu-50-50@2")
    dests = {d["at"]: d["ratio"] for d in c["optical"]["paths"][0]["to"]}
    assert dests == {"split.1": 50, "split.2": 50}


@pytest.mark.parametrize("km", [10, 20, 40, 80])
def test_each_dcm_passes_rx_through_to_tx(km):
    """ds-ppm-r4.0's own flow figure: Rx in, dispersion applied, Tx out.

    Bore 1 is Tx and bore 2 is Rx, which is the order the faceplate captions
    them and the order lc-duplex-adapter composes its bores.
    """
    c = contract(f"smartoptics/ppm-dcm-{km}@2")
    paths = c["optical"]["paths"]
    assert len(paths) == 1
    assert paths[0]["from"] == "dcm.2" and paths[0]["to"] == "dcm.1"


@pytest.mark.parametrize("km", [10, 20, 40, 80])
def test_a_dcm_declares_no_unused_positions(km):
    """Both bores carry light, so `unused` would be a false claim."""
    c = contract(f"smartoptics/ppm-dcm-{km}@2")
    assert not (c["optical"].get("unused") or {})


def test_the_adapters_bore_pitch_matches_the_verified_standard():
    """The library held two numbers for one physical quantity.

    `standards.yaml`'s `lc-duplex-receptacle` carries `pitch: 6.25` at
    `pitch-confidence: verified`, from IEC 61754-20 / TIA-604-10 FOCIS 10.
    The adapter composed its two bores 6.60 apart, from the Smartoptics DCP-R
    stencil. Nothing compared them, so they disagreed by 5.6% in silence.

    The standard wins: `verified` against a published interface standard
    outranks `measured` off one vendor's Visio artwork.
    """
    import yaml as _yaml
    std = _yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    want = std["standards"]["lc-duplex-receptacle"]["pitch"]

    c = contract("common/lc-duplex-adapter@5")
    bore_w = contract("std/lc-bore@3")["size"]["w"]
    xs = [p["at"][0] for p in c["parts"] if p["ref"] == "std/lc-bore@3"]
    assert len(xs) == 2, xs
    centres = sorted(x + bore_w / 2 for x in xs)
    assert round(centres[1] - centres[0], 4) == want, (
        f"bores are {centres[1] - centres[0]:.2f} apart; the standard says {want}")

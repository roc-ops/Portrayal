"""The optical graph, resolved from a contract.

A connector states how many fibre positions it presents, ONCE, and every module
that composes it inherits that. The alternative - restating capacity per module -
is 77 chances to type 12 as 21 on the FS line alone.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))


def contract(ref):
    """`common/lc-duplex-adapter@3` -> its parsed contract."""
    name, major = ref.split("@")
    return yaml.safe_load(
        (LIB / "components" / name / f"v{major}" / "contract.yaml").read_text())


def test_the_lc_duplex_adapter_presents_two_fibre_positions():
    c = contract("common/lc-duplex-adapter@3")
    assert (c.get("optical") or {}).get("positions") == 2, (
        "an LC DUPLEX adapter is two bores. If this is absent, every module "
        "composing it has no capacity to check its paths against")


import optical  # noqa: E402


def test_an_endpoint_splits_into_a_part_id_and_a_position():
    assert optical.split_endpoint("mtp-1.3") == ("mtp-1", 3)
    assert optical.split_endpoint("common.12") == ("common", 12)


def test_capacities_come_from_the_composed_parts_contracts():
    """The module names parts; the PARTS know how many fibres they hold."""
    c = {"parts": [{"ref": "common/lc-duplex-adapter@3", "id": "common"},
                   {"ref": "common/lc-duplex-adapter@3", "id": "split"},
                   {"ref": "common/led-dot@1", "id": "lamp"}]}
    loaded = {"common/lc-duplex-adapter@3": {"optical": {"positions": 2}},
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
